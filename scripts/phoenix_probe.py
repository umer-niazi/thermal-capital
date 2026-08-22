"""Phoenix TCM Heatmap Probe Script.

Makes a live API call to FortyGuard Temperature API for a small AOI in Phoenix, AZ,
to verify endpoint response structure, field names, and statistics.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

# Ensure repository root is on sys.path
ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
load_dotenv(ROOT_DIR / ".env")

from fortyguard import FortyGuardClient

# Target Date & Parameters
STUDY_DATE = "2024-07-15"
GRANULARITY_M = 100
FILTER_TYPE = 3  # Single-day 24h aggregate
ANALYTIC_TYPE = "tcm"

# Bounding box in Phoenix, AZ (Central / Downtown Phoenix industrial corridor)
# Span: ~1.85 km (lon) x ~1.66 km (lat) ~= 3.07 km² (~1.18 mi²)
PHOENIX_AOI = {
    "type": "FeatureCollection",
    "features": [
        {
          "type": "Feature",
          "properties": {
              "name": "Phoenix Central Probe AOI"
          },
          "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-112.0850, 33.4400],
                [-112.0650, 33.4400],
                [-112.0650, 33.4550],
                [-112.0850, 33.4550],
                [-112.0850, 33.4400],
            ]],
          },
        }
    ],
}


def run_probe() -> dict:
    print("=" * 70)
    print("FortyGuard API Live Probe — Phoenix, Arizona")
    print("=" * 70)

    client = FortyGuardClient()
    masked_key = (
        client.api_key[:6] + "…" + client.api_key[-4:]
        if client.api_key and len(client.api_key) > 10
        else "***"
    )
    print(f"Base URL      : {client.base_url}")
    print(f"API Key       : {masked_key}")
    print(f"Study Date    : {STUDY_DATE}")
    print(f"Filter Type   : {FILTER_TYPE} (Single day daily aggregates)")
    print(f"Granularity   : {GRANULARITY_M} m")
    print(f"Analytic Type : {ANALYTIC_TYPE}")
    print(f"AOI           : Phoenix Central bounding box (~3.07 km²)")
    print("-" * 70)
    print("Submitting heatmap request and polling for completion...")

    response = client.create_heatmap(
        polygon_aoi=PHOENIX_AOI,
        start_date=STUDY_DATE,
        filter_type=FILTER_TYPE,
        granularity=GRANULARITY_M,
        analytic_type=ANALYTIC_TYPE,
        verbose=True,
    )

    activity_id = response.get("activity_id")
    result = response.get("result", {})
    map_data = result.get("map_data", {})
    features = map_data.get("features", [])
    stats_data = result.get("stats_data", {})

    print("=" * 70)
    print("PROBE RESULTS")
    print("=" * 70)
    print(f"Activity ID   : {activity_id}")
    print(f"Result Keys   : {list(result.keys())}")
    print(f"Cell Count    : {len(features)} tiles")
    print("\nStats Data:")
    print(json.dumps(stats_data, indent=2))

    if features:
        print("\nRepresentative Tile Properties (First 3 Tiles):")
        for i, feat in enumerate(features[:3]):
            print(f"  Tile #{i} (ID: {feat.get('id', feat.get('properties', {}).get('tile_id'))}):")
            print(f"    Properties: {feat.get('properties')}")
            coords = feat.get("geometry", {}).get("coordinates", [[]])[0]
            if coords:
                print(f"    Sample Coord: [{coords[0][0]:.5f}, {coords[0][1]:.5f}]")

        # Summary calculations across tile properties
        avg_temps = [f["properties"]["average_temperature"] for f in features if "average_temperature" in f.get("properties", {})]
        max_temps = [f["properties"]["max_temperature"] for f in features if "max_temperature" in f.get("properties", {})]
        min_temps = [f["properties"]["min_temperature"] for f in features if "min_temperature" in f.get("properties", {})]

        if avg_temps and max_temps and min_temps:
            print("\nDerived Tile Temperature Distribution (All °C):")
            print(f"  Daily Max (Peak) : min={min(max_temps):.2f}°C, mean={sum(max_temps)/len(max_temps):.2f}°C, max={max(max_temps):.2f}°C")
            print(f"  Daily Average    : min={min(avg_temps):.2f}°C, mean={sum(avg_temps)/len(avg_temps):.2f}°C, max={max(avg_temps):.2f}°C")
            print(f"  Daily Min        : min={min(min_temps):.2f}°C, mean={sum(min_temps)/len(min_temps):.2f}°C, max={max(min_temps):.2f}°C")

    # Output directory setup
    probes_dir = ROOT_DIR / "data" / "probes"
    probes_dir.mkdir(parents=True, exist_ok=True)

    json_path = probes_dir / f"phoenix_tcm_{STUDY_DATE}.json"
    geojson_path = probes_dir / f"phoenix_tcm_{STUDY_DATE}.geojson"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(response, f, indent=2)
    print(f"\nSaved raw response to : {json_path}")

    if map_data:
        with open(geojson_path, "w", encoding="utf-8") as f:
            json.dump(map_data, f, indent=2)
        print(f"Saved GeoJSON map data to : {geojson_path}")

    print("=" * 70)
    print("Probe completed successfully.")
    print("=" * 70)
    return response


if __name__ == "__main__":
    run_probe()

"""Controlled Texas coverage and data-quality feasibility probe script.

Probes 4 contrasting Texas regions:
1. Dallas-Fort Worth (TX-DFW-01)
2. Houston (TX-HOU-01)
3. Austin (TX-AUS-01)
4. El Paso (TX-ELP-01)

Executes TCM, Exceedance, Persistence, and Env Params using CachedFortyGuardClient.
"""

from __future__ import annotations

import json
import pathlib
import sys
from typing import Any
from dotenv import load_dotenv

# Ensure project root is in python path
ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
load_dotenv(ROOT_DIR / ".env")

from backend.cache.cached_client import CachedFortyGuardClient
from backend.models.thermal import CandidateSite
from backend.services.cooling_burden import calculate_cooling_burden
from backend.services.geo import build_unified_aoi, clip_analysis_layer_to_site, clip_heatmap_to_site
from backend.services.scoring_config import ScoringConfig
from backend.services.thermal_metrics import (
    extract_analysis_metrics,
    extract_environmental_metrics,
    extract_tcm_metrics,
)
from backend.services.thermal_scoring import calculate_thermal_risk_score

PROBES_DIR = ROOT_DIR / "data" / "probes"
CANDIDATES_FILE = PROBES_DIR / "texas_candidate_sites.json"

START_DATE = "2024-07-15"
END_DATE = "2024-07-21"
GRANULARITY = 100
EXCEEDANCE_THRESH = 40.0
PERSISTENCE_THRESH = 35.0


def main() -> None:
    print("=" * 80)
    print("FORTYGUARD TEXAS FEASIBILITY & DATA-QUALITY PROBE")
    print(f"Study Window: {START_DATE} to {END_DATE} (7-Day Heatwave Window)")
    print("=" * 80)

    if not CANDIDATES_FILE.exists():
        print(f"Error: Candidate file not found at {CANDIDATES_FILE}")
        sys.exit(1)

    with open(CANDIDATES_FILE, "r", encoding="utf-8") as f:
        all_candidates = json.load(f)

    # Focus on the 4 primary contrasting climate test regions
    target_ids = ["TX-DFW-01", "TX-HOU-01", "TX-AUS-01", "TX-ELP-01"]
    probe_candidates = [c for c in all_candidates if c["site_id"] in target_ids]

    client = CachedFortyGuardClient()
    results: dict[str, Any] = {}

    for cand in probe_candidates:
        site_id = cand["site_id"]
        city = cand["city"]
        submarket = cand["submarket"]
        site_name = cand["display_name"]
        geom = cand["geometry"]
        lat = cand["latitude"]
        lon = cand["longitude"]

        print(f"\n[{site_id}] Probing {city} ({submarket}): {site_name}...")

        # 1. Build buffered AOI around candidate polygon
        aoi_geojson, aoi_area = build_unified_aoi([geom], buffer_m=400.0)
        print(f"  • Buffered AOI Area: {aoi_area:.2f} km²")

        # 2. TCM Heatmap
        print(f"  • Fetching TCM Heatmap ({START_DATE})...")
        tcm_resp = client.create_heatmap(
            polygon_aoi=aoi_geojson,
            start_date=START_DATE,
            filter_type=3,
            granularity=GRANULARITY,
            analytic_type="tcm",
        )
        tcm_file = PROBES_DIR / f"texas_tcm_{site_id}_{START_DATE}.json"
        with open(tcm_file, "w", encoding="utf-8") as f:
            json.dump(tcm_resp, f, indent=2)

        tcm_stats = extract_tcm_metrics(tcm_resp)
        tcm_clip = clip_heatmap_to_site(
            tcm_resp.get("result", {}).get("map_data", {}).get("features", []),
            geom,
            site_id=site_id,
        )
        print(f"    -> Returned {tcm_stats.tile_count} tiles. Peak max_temp: {tcm_stats.max_max_temp_c:.2f}°C, Mean avg: {tcm_stats.mean_average_temp_c:.2f}°C, Min: {tcm_stats.mean_min_temp_c:.2f}°C")

        # 3. Exceedance Heatmap (>40°C)
        print(f"  • Fetching Exceedance Heatmap (>40°C, {START_DATE}..{END_DATE})...")
        exc_resp = client.create_heatmap(
            polygon_aoi=aoi_geojson,
            start_date=START_DATE,
            end_date=END_DATE,
            filter_type=4,
            granularity=GRANULARITY,
            analytic_type="exceedance",
            threshold=EXCEEDANCE_THRESH,
            direction="above",
        )
        exc_file = PROBES_DIR / f"texas_exceedance_{site_id}_{START_DATE}_{END_DATE}.json"
        with open(exc_file, "w", encoding="utf-8") as f:
            json.dump(exc_resp, f, indent=2)

        exc_stats = extract_analysis_metrics(exc_resp)
        exc_clip = clip_analysis_layer_to_site(
            exc_resp.get("result", {}).get("map_data", {}).get("features", []),
            geom,
            site_id=site_id,
        )
        print(f"    -> Mean hours >40°C: {exc_stats.mean_value:.1f}h (Site weighted: {exc_clip.weighted_value or 0.0:.1f}h)")

        # 4. Persistence Heatmap (>35°C)
        print(f"  • Fetching Persistence Heatmap (>35°C unbroken, {START_DATE}..{END_DATE})...")
        per_resp = client.create_heatmap(
            polygon_aoi=aoi_geojson,
            start_date=START_DATE,
            end_date=END_DATE,
            filter_type=4,
            granularity=GRANULARITY,
            analytic_type="persistence",
            threshold=PERSISTENCE_THRESH,
            direction="above",
        )
        per_file = PROBES_DIR / f"texas_persistence_{site_id}_{START_DATE}_{END_DATE}.json"
        with open(per_file, "w", encoding="utf-8") as f:
            json.dump(per_resp, f, indent=2)

        per_stats = extract_analysis_metrics(per_resp)
        per_clip = clip_analysis_layer_to_site(
            per_resp.get("result", {}).get("map_data", {}).get("features", []),
            geom,
            site_id=site_id,
        )
        print(f"    -> Mean unbroken hours >35°C: {per_stats.mean_value:.1f}h (Site weighted: {per_clip.weighted_value or 0.0:.1f}h)")

        # 5. Point Environmental Parameters (Houston & El Paso priority, plus DFW/Austin)
        print(f"  • Fetching Point Environmental Parameters at ({lat:.4f}, {lon:.4f})...")
        anchor_temp = tcm_clip.weighted_max_temperature_c or 38.0
        env_resp = client.environmental_parameters(
            latitude=lat,
            longitude=lon,
            temperature=anchor_temp,
            start_date=START_DATE,
            filter_type=3,
            analysis=[
                "apparent_temperature_celsius",
                "wet_bulb_temperature_celsius",
                "relative_humidity_percent",
                "heat_index_celsius",
                "air_quality:idx",
                "solar_irradiance",
            ],
        )
        env_file = PROBES_DIR / f"texas_env_params_{site_id}_{START_DATE}.json"
        with open(env_file, "w", encoding="utf-8") as f:
            json.dump(env_resp, f, indent=2)

        env_metrics = extract_environmental_metrics(env_resp)
        print(f"    -> Peak Apparent: {env_metrics.peak_apparent_temperature_c:.2f}°C (at {env_metrics.peak_apparent_temperature_time}), Peak Wet-Bulb: {env_metrics.peak_wet_bulb_temperature_c:.2f}°C, Hot-Hour HI: {env_metrics.peak_heat_index_c or 0.0:.2f}°C")

        # 6. Scoring & Cooling Burden Calculations
        thermal_metrics = tcm_clip.to_thermal_metrics(
            exceedance_hours=exc_clip.weighted_value,
            persistence_hours=per_clip.weighted_value,
            peak_wet_bulb_c=env_metrics.peak_wet_bulb_temperature_c,
            peak_apparent_c=env_metrics.peak_apparent_temperature_c,
        )
        cooling_burden = calculate_cooling_burden(
            tcm_metrics=thermal_metrics,
            exceedance_hours_40c=exc_clip.weighted_value,
            persistence_hours_35c=per_clip.weighted_value,
            env_metrics=env_metrics,
            window_days=7,
        )
        risk_result = calculate_thermal_risk_score(
            metrics=thermal_metrics,
            cooling_burden=cooling_burden,
            env_metrics=env_metrics,
            window_hours=168,
        )

        results[site_id] = {
            "site_id": site_id,
            "city": city,
            "submarket": submarket,
            "site_name": site_name,
            "aoi_area_km2": aoi_area,
            "tile_count": tcm_stats.tile_count,
            "peak_ambient_c": thermal_metrics.peak_temperature_c,
            "mean_ambient_c": thermal_metrics.mean_temperature_c,
            "overnight_min_c": thermal_metrics.overnight_min_temperature_c,
            "diurnal_swing_c": thermal_metrics.diurnal_swing_c,
            "exceedance_hours_40c": exc_clip.weighted_value,
            "persistence_hours_35c": per_clip.weighted_value,
            "peak_wet_bulb_c": env_metrics.peak_wet_bulb_temperature_c,
            "hot_hour_apparent_c": env_metrics.peak_apparent_temperature_c,
            "hot_hour_apparent_time": env_metrics.peak_apparent_temperature_time,
            "hot_hour_heat_index_c": env_metrics.peak_heat_index_c,
            "cdh_25": cooling_burden.cooling_degree_hours_above_25c,
            "cop_loss_pct": cooling_burden.chiller_cop_degradation_pct,
            "thermal_score": risk_result.total_score,
            "risk_category": risk_result.risk_category,
            "components": {k: v.model_dump() for k, v in risk_result.components.items()},
        }

    # Save summary probe report
    summary_file = PROBES_DIR / "texas_feasibility_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 80)
    print("TEXAS FEASIBILITY PROBE SUMMARY MATRIX")
    print("=" * 80)
    print(f"{'Site ID':<10} | {'City':<12} | {'Peak °C':<8} | {'Mean °C':<8} | {'Min °C':<8} | {'>40°C (h)':<9} | {'>35°C Unbrk':<12} | {'Wet-Bulb':<9} | {'Score':<6} | {'Risk Tier'}")
    print("-" * 105)
    for sid, r in results.items():
        print(f"{sid:<10} | {r['city']:<12} | {r['peak_ambient_c']:<8.2f} | {r['mean_ambient_c']:<8.2f} | {r['overnight_min_c']:<8.2f} | {r['exceedance_hours_40c'] or 0.0:<9.1f} | {r['persistence_hours_35c'] or 0.0:<12.1f} | {r['peak_wet_bulb_c']:<9.2f} | {r['thermal_score']:<6.1f} | {r['risk_category']}")
    print("=" * 80)


if __name__ == "__main__":
    main()

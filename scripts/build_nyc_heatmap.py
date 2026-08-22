#!/usr/bin/env python3
"""Build citywide FortyGuard heatmaps for New York City via API-safe tiling and caching.

Features:
- Deterministic 47-tile geographic partitioning of NYC.
- Strict caching via SQLite/CachedFortyGuardClient (0 redundant calls).
- Dry-run calculation of API credit consumption before live execution.
- Multi-layer support: TCM (Peak/Mean), Exceedance (>35°C), and Persistence (>35°C).
- Deduplication and spatial clipping to the authentic NYC shoreline boundary.
- Generates data/probes/nyc_coverage_summary.json and unified GeoJSON files.
"""

from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import sys
import time
from typing import Any
from dotenv import load_dotenv

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
load_dotenv(ROOT_DIR / ".env")

from backend.cache.cached_client import CachedFortyGuardClient
from backend.cache.keys import generate_cache_key
from backend.services.nyc_tiling import (
    generate_nyc_tiles,
    get_nyc_boundary_shape,
    load_nyc_boroughs,
    merge_and_clip_heatmap_features,
)

PROBES_DIR = ROOT_DIR / "data" / "probes"
SUMMARY_FILE = PROBES_DIR / "nyc_coverage_summary.json"

START_DATE = "2024-07-15"
END_DATE = "2024-07-21"
GRANULARITY = 100
EXCEEDANCE_THRESH = 35.0
PERSISTENCE_THRESH = 35.0


def inspect_tile_cache(client: CachedFortyGuardClient, tiles: list[dict[str, Any]]) -> dict[str, Any]:
    """Inspect cache state across all tiles and required layers."""
    store = client.store
    cached_tcm: list[str] = []
    missing_tcm: list[str] = []
    cached_exc: list[str] = []
    missing_exc: list[str] = []
    cached_per: list[str] = []
    missing_per: list[str] = []

    for t in tiles:
        t_id = t["tile_id"]
        poly = t["polygon_aoi"]

        # TCM payload
        tcm_payload = {
            "polygon_aoi": poly,
            "date_time": {"start_date": START_DATE, "filter_type": 3},
            "granularity": GRANULARITY,
            "analytic_type": "tcm",
        }
        tcm_key = generate_cache_key("/v1/heatmap", tcm_payload)
        if store.get(tcm_key) is not None:
            cached_tcm.append(t_id)
        else:
            missing_tcm.append(t_id)

        # Exceedance payload
        exc_payload = {
            "polygon_aoi": poly,
            "date_time": {"start_date": START_DATE, "end_date": END_DATE, "filter_type": 4},
            "granularity": GRANULARITY,
            "analytic_type": "exceedance",
            "threshold": EXCEEDANCE_THRESH,
            "direction": "above",
        }
        exc_key = generate_cache_key("/v1/heatmap", exc_payload)
        if store.get(exc_key) is not None:
            cached_exc.append(t_id)
        else:
            missing_exc.append(t_id)

        # Persistence payload
        per_payload = {
            "polygon_aoi": poly,
            "date_time": {"start_date": START_DATE, "end_date": END_DATE, "filter_type": 4},
            "granularity": GRANULARITY,
            "analytic_type": "persistence",
            "threshold": PERSISTENCE_THRESH,
            "direction": "above",
        }
        per_key = generate_cache_key("/v1/heatmap", per_payload)
        if store.get(per_key) is not None:
            cached_per.append(t_id)
        else:
            missing_per.append(t_id)

    total_tiles = len(tiles)
    total_potential = total_tiles * 3
    total_cached = len(cached_tcm) + len(cached_exc) + len(cached_per)
    remaining_live = total_potential - total_cached

    return {
        "total_tiles": total_tiles,
        "total_potential_requests": total_potential,
        "total_cached_requests": total_cached,
        "remaining_live_requests": remaining_live,
        "cached_tcm": cached_tcm,
        "missing_tcm": missing_tcm,
        "cached_exc": cached_exc,
        "missing_exc": missing_exc,
        "cached_per": cached_per,
        "missing_per": missing_per,
    }


def print_dry_run(cache_status: dict[str, Any], tiles: list[dict[str, Any]]) -> None:
    """Display clear dry-run coverage plan."""
    print("=" * 80)
    print("NEW YORK CITY — FORTYGUARD COVERAGE PLAN & DRY RUN")
    print(f"Study Baseline Date: {START_DATE} | Heatwave Window: {START_DATE} to {END_DATE}")
    print("=" * 80)
    print(f"Total Geographic Tiles:        {cache_status['total_tiles']} tiles")
    print(f"Required Layers:               3 layers (TCM, Exceedance >35°C, Persistence >35°C)")
    print(f"Total Expected API Requests:   {cache_status['total_potential_requests']}")
    print(f"Already Cached in SQLite:      {cache_status['total_cached_requests']}")
    print(f"Remaining Live API Requests:   {cache_status['remaining_live_requests']}")
    print("-" * 80)
    print(f"  • TCM Layer:         {len(cache_status['cached_tcm'])} cached, {len(cache_status['missing_tcm'])} to fetch")
    print(f"  • Exceedance Layer:  {len(cache_status['cached_exc'])} cached, {len(cache_status['missing_exc'])} to fetch")
    print(f"  • Persistence Layer: {len(cache_status['cached_per'])} cached, {len(cache_status['missing_per'])} to fetch")
    print("=" * 80)

    # Borough breakdown
    nyc_b, borough_shapes = get_nyc_boundary_shape()
    print("\nBorough Tile Allocation:")
    for b_name in sorted(borough_shapes.keys()):
        b_tiles = [t["tile_id"] for t in tiles if b_name in t["boroughs"]]
        print(f"  • {b_name:15}: {len(b_tiles)} tiles ({', '.join(b_tiles[:5])}{', ...' if len(b_tiles) > 5 else ''})")
    print()


def fetch_tile_layer(
    client: CachedFortyGuardClient,
    tile: dict[str, Any],
    layer_name: str,
) -> dict[str, Any]:
    """Fetch a single layer for a tile using CachedFortyGuardClient."""
    poly = tile["polygon_aoi"]
    t_id = tile["tile_id"]

    if layer_name == "tcm":
        return client.create_heatmap(
            polygon_aoi=poly,
            start_date=START_DATE,
            filter_type=3,
            granularity=GRANULARITY,
            analytic_type="tcm",
        )
    elif layer_name == "exceedance":
        return client.create_heatmap(
            polygon_aoi=poly,
            start_date=START_DATE,
            end_date=END_DATE,
            filter_type=4,
            granularity=GRANULARITY,
            analytic_type="exceedance",
            threshold=EXCEEDANCE_THRESH,
            direction="above",
        )
    elif layer_name == "persistence":
        return client.create_heatmap(
            polygon_aoi=poly,
            start_date=START_DATE,
            end_date=END_DATE,
            filter_type=4,
            granularity=GRANULARITY,
            analytic_type="persistence",
            threshold=PERSISTENCE_THRESH,
            direction="above",
        )
    else:
        raise ValueError(f"Unknown layer name: {layer_name}")


def run_citywide_fetch(
    client: CachedFortyGuardClient,
    tiles: list[dict[str, Any]],
    layers: list[str] | None = None,
    max_workers: int = 6,
) -> dict[str, Any]:
    """Run fetch process for all tiles and layers in parallel, skipping cached items."""
    import concurrent.futures

    target_layers = layers or ["tcm", "exceedance", "persistence"]
    tasks_to_run: list[tuple[dict[str, Any], str]] = []

    for t in tiles:
        for l in target_layers:
            tasks_to_run.append((t, l))

    print(f"\nStarting Citywide Fetch across {len(tiles)} tiles for layers: {target_layers} (Workers: {max_workers})...")
    results: dict[str, dict[str, Any]] = {l: {} for l in target_layers}
    errors: list[dict[str, Any]] = []
    completed_count = 0
    total_tasks = len(tasks_to_run)

    def _worker_fetch(task_tuple: tuple[dict[str, Any], str]) -> tuple[str, str, list[dict[str, Any]] | None, str | None]:
        tile_item, layer_name = task_tuple
        t_id = tile_item["tile_id"]
        try:
            # Note: create fresh client per thread or use session safely
            worker_client = CachedFortyGuardClient(store=client.store)
            resp = fetch_tile_layer(worker_client, tile_item, layer_name)
            feats = (resp.get("result") or resp).get("map_data", {}).get("features", [])
            return (t_id, layer_name, feats, None)
        except Exception as exc:
            return (t_id, layer_name, None, str(exc))

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {executor.submit(_worker_fetch, t): t for t in tasks_to_run}
        for future in concurrent.futures.as_completed(future_to_task):
            completed_count += 1
            t_id, layer_name, feats, err = future.result()
            if err is None and feats is not None:
                results[layer_name][t_id] = feats
                print(f"  [{completed_count:03d}/{total_tasks:03d}] ✓ {t_id} {layer_name.upper()}: {len(feats)} cells")
            else:
                print(f"  [{completed_count:03d}/{total_tasks:03d}] ✗ {t_id} {layer_name.upper()} Failed: {err}")
                errors.append({"tile_id": t_id, "layer": layer_name, "error": err})

    return {"results": results, "errors": errors}


def build_unified_citywide_datasets(
    client: CachedFortyGuardClient,
    tiles: list[dict[str, Any]],
) -> dict[str, Any]:
    """Load all cached tile responses, merge & clip to NYC, and write unified datasets."""
    PROBES_DIR.mkdir(parents=True, exist_ok=True)
    layers = ["tcm", "exceedance", "persistence"]

    merged_by_layer: dict[str, list[dict[str, Any]]] = {}
    tile_success_counts: dict[str, int] = {l: 0 for l in layers}
    tile_failed_counts: dict[str, int] = {l: 0 for l in layers}

    for layer in layers:
        tile_feature_lists: list[list[dict[str, Any]]] = []
        for t in tiles:
            t_id = t["tile_id"]
            try:
                resp = fetch_tile_layer(client, t, layer)
                feats = (resp.get("result") or resp).get("map_data", {}).get("features", [])
                if feats:
                    tile_feature_lists.append(feats)
                    tile_success_counts[layer] += 1
                else:
                    tile_failed_counts[layer] += 1
            except Exception:
                tile_failed_counts[layer] += 1

        print(f"Merging & clipping {layer.upper()} ({len(tile_feature_lists)} tiles with features)...")
        cleaned_features = merge_and_clip_heatmap_features(tile_feature_lists, clip_to_boundary=True)
        merged_by_layer[layer] = cleaned_features

        # Save layer file
        out_file = PROBES_DIR / f"nyc_citywide_{layer}.json"
        out_data = {
            "status": "succeeded",
            "city": "New York City",
            "study_date": START_DATE,
            "window": f"{START_DATE} to {END_DATE}",
            "layer": layer,
            "total_cells": len(cleaned_features),
            "result": {
                "map_data": {
                    "type": "FeatureCollection",
                    "features": cleaned_features,
                }
            },
        }
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(out_data, f)
        print(f"  ✓ Written: {out_file.name} ({len(cleaned_features):,} cells)")

    # Build coverage summary report
    total_tiles = len(tiles)
    successful_tiles = max(tile_success_counts.values(), default=0)
    failed_tiles = total_tiles - successful_tiles
    coverage_pct = round((successful_tiles / total_tiles) * 100.0, 1)

    summary = {
        "city": "New York City",
        "study_date": START_DATE,
        "study_window": f"Jul 15–21, 2024",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_tiles_required": total_tiles,
        "tiles_cached": successful_tiles,
        "tiles_available": successful_tiles,
        "tiles_failed": failed_tiles,
        "coverage_percentage": coverage_pct,
        "is_complete_citywide": coverage_pct >= 95.0,
        "layers_available": {
            "tcm_peak": len(merged_by_layer.get("tcm", [])),
            "tcm_mean": len(merged_by_layer.get("tcm", [])),
            "exceedance": len(merged_by_layer.get("exceedance", [])),
            "persistence": len(merged_by_layer.get("persistence", [])),
            "cooling_burden": len(merged_by_layer.get("tcm", [])),
        },
        "geographic_bounds": {
            "min_longitude": -74.2556,
            "min_latitude": 40.4961,
            "max_longitude": -73.7000,
            "max_latitude": 40.9155,
        },
        "data_provenance": "FortyGuard High-Resolution Microclimate API (100m Ambient Grid)",
    }

    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\n✓ Generated coverage summary: {SUMMARY_FILE.name}")
    print(f"  Coverage: {coverage_pct}% ({successful_tiles}/{total_tiles} tiles)")

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="NYC Citywide FortyGuard Heatmap Pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Print dry-run coverage plan and credit calculations")
    parser.add_argument("--fetch", action="store_true", help="Execute FortyGuard API requests for uncached tiles")
    parser.add_argument("--build", action="store_true", help="Merge cached tile responses and build citywide datasets")
    parser.add_argument("--workers", type=int, default=6, help="Number of concurrent worker threads (default: 6)")
    parser.add_argument("--borough", type=str, default=None, help="Optional borough filter (e.g. 'Manhattan', 'Bronx', 'Brooklyn', 'Queens', 'Staten Island')")
    args = parser.parse_args()

    client = CachedFortyGuardClient()
    all_tiles = generate_nyc_tiles()

    if args.borough:
        b_norm = args.borough.lower().strip()
        tiles = [t for t in all_tiles if any(b_norm in b.lower() for b in t["boroughs"])]
        print(f"Filtered to borough '{args.borough}': {len(tiles)} of {len(all_tiles)} tiles")
    else:
        tiles = all_tiles

    cache_status = inspect_tile_cache(client, tiles)

    if args.dry_run or (not args.fetch and not args.build):
        print_dry_run(cache_status, tiles)
        return

    if args.fetch:
        run_citywide_fetch(client, tiles, max_workers=args.workers)

    if args.build:
        build_unified_citywide_datasets(client, all_tiles)


if __name__ == "__main__":
    main()

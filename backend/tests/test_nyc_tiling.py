"""Unit tests for NYC geographic tiling, boundary clipping, deduplication, and coverage reporting."""

import pytest
from backend.services.nyc_tiling import (
    generate_nyc_tiles,
    get_nyc_boundary_shape,
    load_nyc_boroughs,
    merge_and_clip_heatmap_features,
)
from backend.services.assets_data import CITY_CONFIGS, get_city_public_assets
from backend.cache.cached_client import CachedFortyGuardClient
from scripts.build_nyc_heatmap import inspect_tile_cache


def test_nyc_boroughs_geojson_loaded():
    """Verify that official NYC 5-borough GeoJSON loads and contains all 5 boroughs."""
    data = load_nyc_boroughs()
    assert data["type"] == "FeatureCollection"
    borough_names = {f["properties"]["name"] for f in data["features"]}
    expected = {"Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"}
    assert expected.issubset(borough_names)


def test_nyc_boundary_shape():
    """Verify that unified NYC geometry is valid and non-empty."""
    nyc_union, borough_shapes = get_nyc_boundary_shape()
    assert nyc_union.is_valid
    assert not nyc_union.is_empty
    assert len(borough_shapes) == 5
    min_lon, min_lat, max_lon, max_lat = nyc_union.bounds
    # Check NYC coordinate envelope
    assert -74.3 < min_lon < -74.1
    assert 40.4 < min_lat < 40.6
    assert -73.8 < max_lon < -73.6
    assert 40.8 < max_lat < 41.0


def test_generate_nyc_tiles():
    """Verify deterministic tile generation covers NYC and allocates boroughs."""
    tiles = generate_nyc_tiles()
    assert len(tiles) >= 40
    assert len(tiles) <= 60

    # Ensure every tile has valid structure
    for t in tiles:
        assert "tile_id" in t
        assert t["tile_id"].startswith("NYC-T")
        assert len(t["bounds"]) == 4
        assert len(t["boroughs"]) >= 1
        assert t["area_km2"] > 0
        assert t["area_km2"] < 50.0  # Safe for FortyGuard API limits (<130 km2)
        assert t["polygon_aoi"]["type"] == "FeatureCollection"


def test_merge_and_clip_heatmap_features():
    """Verify merging deduplicates cells and clips to NYC boundary."""
    # Create synthetic test features in Manhattan and outside NYC in ocean
    manhattan_feat = {
        "type": "Feature",
        "properties": {"tile_id": 0, "temperature": 32.5, "max_temperature": 36.0, "average_temperature": 31.0, "min_temperature": 25.0},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-73.985, 40.750],
                [-73.984, 40.750],
                [-73.984, 40.751],
                [-73.985, 40.751],
                [-73.985, 40.750],
            ]],
        },
    }
    # Duplicate of manhattan feature (same centroid)
    manhattan_dup = {
        "type": "Feature",
        "properties": {"tile_id": 99, "temperature": 32.5, "max_temperature": 36.0, "average_temperature": 31.0, "min_temperature": 25.0},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-73.985, 40.750],
                [-73.984, 40.750],
                [-73.984, 40.751],
                [-73.985, 40.751],
                [-73.985, 40.750],
            ]],
        },
    }
    # Ocean feature south of Long Island (outside NYC land boundary)
    ocean_feat = {
        "type": "Feature",
        "properties": {"tile_id": 1, "temperature": 28.0},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-73.900, 40.400],
                [-73.899, 40.400],
                [-73.899, 40.401],
                [-73.900, 40.401],
                [-73.900, 40.400],
            ]],
        },
    }

    tile_lists = [[manhattan_feat, manhattan_dup], [ocean_feat]]
    merged = merge_and_clip_heatmap_features(tile_lists, clip_to_boundary=True)

    # Only 1 unique Manhattan feature should remain (dup removed, ocean clipped)
    assert len(merged) == 1
    assert merged[0]["properties"]["borough"] == "Manhattan"
    assert merged[0]["id"] == "0"
    assert merged[0]["properties"]["tile_id"] == 0


def test_nyc_assets_registry():
    """Verify that NYC public asset registry includes assets across all 5 boroughs."""
    assets = get_city_public_assets("nyc")
    assert len(assets) >= 20

    # Ensure all 5 boroughs have assets
    asset_ids = [a.asset_id for a in assets]
    assert any("BX" in aid for aid in asset_ids)  # Bronx
    assert any("MN" in aid for aid in asset_ids)  # Manhattan
    assert any("BK" in aid for aid in asset_ids)  # Brooklyn
    assert any("QN" in aid for aid in asset_ids)  # Queens
    assert any("SI" in aid for aid in asset_ids)  # Staten Island

    # Ensure all assets have valid risk scores and priority reasons
    for a in assets:
        assert a.heat_risk_score > 0
        assert a.observed_heat.peak_temperature_c > 0
        assert len(a.priority_reasons) >= 1
        assert a.city == "New York City"


def test_inspect_tile_cache_dry_run():
    """Verify that dry run cache status inspection executes correctly."""
    client = CachedFortyGuardClient()
    tiles = generate_nyc_tiles()
    status = inspect_tile_cache(client, tiles)

    assert status["total_tiles"] == len(tiles)
    assert status["total_potential_requests"] == len(tiles) * 3
    assert status["total_cached_requests"] >= 0
    assert status["remaining_live_requests"] >= 0

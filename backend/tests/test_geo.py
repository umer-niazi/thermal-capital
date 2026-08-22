"""Tests for geospatial clipping, unified AOI generation, and centroid calculations."""

from __future__ import annotations

import json
import pathlib
import pytest

from backend.services.geo import (
    build_unified_aoi,
    clip_analysis_layer_to_site,
    clip_heatmap_to_site,
    get_site_centroid,
)

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
PHOENIX_PROBE_PATH = ROOT_DIR / "data" / "probes" / "phoenix_tcm_2024-07-15.json"


@pytest.fixture
def phoenix_probe_data() -> dict:
    if not PHOENIX_PROBE_PATH.exists():
        pytest.skip("Phoenix probe data not found")
    with open(PHOENIX_PROBE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_clip_heatmap_to_site(phoenix_probe_data: dict) -> None:
    features = phoenix_probe_data["result"]["map_data"]["features"]

    test_site = {
        "type": "Polygon",
        "coordinates": [[
            [-112.0780, 33.4450],
            [-112.0720, 33.4450],
            [-112.0720, 33.4490],
            [-112.0780, 33.4490],
            [-112.0780, 33.4450],
        ]],
    }

    result = clip_heatmap_to_site(features, test_site, site_id="PHX-DTC-01")
    assert result.site_id == "PHX-DTC-01"
    assert result.coverage_pct > 90.0
    assert result.contributing_tile_count >= 15
    assert 40.40 <= result.weighted_max_temperature_c <= 40.60
    assert 35.50 <= result.weighted_average_temperature_c <= 36.50
    assert 29.00 <= result.weighted_min_temperature_c <= 29.80


def test_clip_heatmap_outside_aoi_fails(phoenix_probe_data: dict) -> None:
    features = phoenix_probe_data["result"]["map_data"]["features"]
    outside_site = {
        "type": "Polygon",
        "coordinates": [[[-121.90, 37.30], [-121.85, 37.30], [-121.85, 37.35], [-121.90, 37.35], [-121.90, 37.30]]],
    }
    with pytest.raises(ValueError, match="does not intersect any heatmap tiles"):
        clip_heatmap_to_site(features, outside_site, site_id="OUTSIDE-01")


def test_build_unified_aoi() -> None:
    """Verify that multiple candidate site polygons are bundled into a buffered convex hull AOI."""
    site1 = {
        "type": "Polygon",
        "coordinates": [[[-112.08, 33.44], [-112.07, 33.44], [-112.07, 33.45], [-112.08, 33.45], [-112.08, 33.44]]],
    }
    site2 = {
        "type": "Polygon",
        "coordinates": [[[-112.05, 33.46], [-112.04, 33.46], [-112.04, 33.47], [-112.05, 33.47], [-112.05, 33.46]]],
    }

    aoi_geojson, aoi_area_km2 = build_unified_aoi([site1, site2], buffer_m=400.0)

    assert aoi_geojson["type"] == "FeatureCollection"
    assert len(aoi_geojson["features"]) == 1
    assert aoi_area_km2 > 0.0
    assert aoi_area_km2 < 130.0  # Within API limit

    # Coordinates ring is closed
    coords = aoi_geojson["features"][0]["geometry"]["coordinates"][0]
    assert coords[0] == coords[-1]


def test_get_site_centroid() -> None:
    """Verify centroid calculation."""
    polygon = {
        "type": "Polygon",
        "coordinates": [[[-112.080, 33.440], [-112.060, 33.440], [-112.060, 33.460], [-112.080, 33.460], [-112.080, 33.440]]],
    }
    lat, lon = get_site_centroid(polygon)
    assert lat == pytest.approx(33.450, abs=0.001)
    assert lon == pytest.approx(-112.070, abs=0.001)

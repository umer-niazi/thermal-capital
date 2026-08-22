"""Tests for FastAPI backend routes supporting New York City adaptation planning and heatmaps."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_api_health() -> None:
    """Verify /api/health endpoint returns NYC as primary geography."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["primary_geography"] == "New York City"
    assert data["active_cities"] == ["nyc"]
    assert "cache" in data


def test_api_coverage_summary() -> None:
    """Verify /api/coverage returns 100% FortyGuard citywide coverage."""
    response = client.get("/api/coverage")
    assert response.status_code == 200
    data = response.json()
    assert data["city"] == "New York City"
    assert data["coverage_percentage"] == 100.0
    assert data["total_tiles_required"] == 47
    assert data["tiles_cached"] == 47
    assert data["is_complete_citywide"] is True
    assert data["layers_available"]["tcm_peak"] == 75380


def test_api_cities_and_boroughs() -> None:
    """Verify /api/cities and /api/boroughs return valid NYC focus areas and boundary polygons."""
    resp_cities = client.get("/api/cities")
    assert resp_cities.status_code == 200
    cities = resp_cities.json()
    assert len(cities) >= 6
    city_keys = [c["city_key"] for c in cities]
    assert "nyc" in city_keys
    assert "manhattan" in city_keys
    assert "brooklyn" in city_keys
    assert "queens" in city_keys
    assert "bronx" in city_keys
    assert "staten_island" in city_keys

    resp_boroughs = client.get("/api/boroughs")
    assert resp_boroughs.status_code == 200
    b_data = resp_boroughs.json()
    assert b_data["type"] == "FeatureCollection"
    assert len(b_data["features"]) == 5


def test_api_assets_list_and_detail() -> None:
    """Verify /api/assets and /api/assets/{id} for NYC public assets."""
    resp = client.get("/api/assets?city=nyc")
    assert resp.status_code == 200
    assets = resp.json()
    assert len(assets) >= 20

    first_asset = assets[0]
    aid = first_asset["asset_id"]

    resp_detail = client.get(f"/api/assets/{aid}?city=nyc")
    assert resp_detail.status_code == 200
    d = resp_detail.json()
    assert d["asset_id"] == aid
    assert d["heat_risk_score"] > 0
    assert d["observed_heat"]["peak_temperature_c"] > 0


def test_api_heatmap_citywide_and_boroughs() -> None:
    """Verify /api/heatmap for all 5 layers across NYC."""
    layers = ["tcm_peak", "tcm_mean", "exceedance", "persistence", "cooling"]
    for layer in layers:
        resp = client.get(f"/api/heatmap?layer={layer}&region=nyc")
        assert resp.status_code == 200
        geo = resp.json()
        assert geo["type"] == "FeatureCollection"
        assert geo["region"] == "nyc"
        assert geo["layer_type"] == layer
        features = geo["features"]
        assert len(features) == 75380

        # Validate feature structure
        f0 = features[0]
        assert f0["type"] == "Feature"
        assert f0["geometry"]["type"] == "Polygon"
        props = f0["properties"]
        assert "color_metric" in props
        assert "display_value" in props
        assert "borough" in props

    # Test borough filter
    resp_bk = client.get("/api/heatmap?layer=tcm_peak&region=nyc&borough=Brooklyn")
    assert resp_bk.status_code == 200
    geo_bk = resp_bk.json()
    assert len(geo_bk["features"]) == 17408


def test_api_methodology() -> None:
    """Verify /api/methodology returns formal data provenance and intervention formulas."""
    response = client.get("/api/methodology")
    assert response.status_code == 200
    data = response.json()
    assert "data_provenance" in data
    assert "FortyGuard" in data["data_provenance"]["observed_baseline"]
    assert "interventions" in data
    assert "tree_canopy" in data["interventions"]
    assert "shade_structure" in data["interventions"]
    assert "cool_pavement" in data["interventions"]


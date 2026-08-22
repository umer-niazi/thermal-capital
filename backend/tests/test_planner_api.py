"""Tests for FastAPI planner endpoints focusing on New York City."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_api_cities() -> None:
    """Verify /api/cities endpoint returns NYC and borough/submarket focus areas."""
    resp = client.get("/api/cities")
    assert resp.status_code == 200
    cities = resp.json()
    assert len(cities) >= 6
    assert cities[0]["city_key"] == "nyc"
    keys = [c["city_key"] for c in cities]
    assert "nyc" in keys
    assert "manhattan" in keys
    assert "brooklyn" in keys
    assert "queens" in keys
    assert "bronx" in keys
    assert "staten_island" in keys


def test_api_assets_list_nyc() -> None:
    """Verify /api/assets for NYC returns 27 enriched assets across all boroughs."""
    resp = client.get("/api/assets?city=nyc")
    assert resp.status_code == 200
    assets = resp.json()
    assert len(assets) == 27
    first = assets[0]
    assert first["city"] == "New York City"
    assert "NYC-" in first["asset_id"]
    assert first["observed_heat"]["peak_temperature_c"] > 30.0
    assert first["observed_heat"]["hours_above_35c"] >= 0.0


def test_api_heatmap_nyc_layers() -> None:
    """Verify /api/heatmap for NYC returns 75,380 citywide FortyGuard cells."""
    for layer in ["tcm_peak", "tcm_mean", "exceedance", "persistence", "cooling"]:
        resp = client.get(f"/api/heatmap?region=nyc&layer={layer}")
        assert resp.status_code == 200
        geo = resp.json()
        assert geo["type"] == "FeatureCollection"
        assert len(geo["features"]) == 75380


def test_api_optimize_endpoint_nyc() -> None:
    """Verify /api/optimize endpoint for NYC generates optimal cooling allocations."""
    resp = client.post(
        "/api/optimize",
        json={
            "city": "nyc",
            "budget": 500000.0,
            "strategy": "vulnerable_populations",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["city"] == "New York City"
    assert data["total_allocated_cost"] <= 500000.0
    assert data["total_trees"] > 0
    assert len(data["asset_allocations"]) > 0


def test_api_report_endpoint_nyc() -> None:
    """Verify /api/report endpoint for NYC produces a complete municipal action brief."""
    resp = client.post(
        "/api/report",
        json={
            "city": "nyc",
            "budget": 500000.0,
            "strategy": "balanced",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "BRIEF-" in data["report_id"] or "PLAN-" in data["report_id"]
    assert "NEW YORK CITY" in data["title"].upper()
    assert len(data["target_assets_table"]) > 0


def test_api_asset_detail() -> None:
    """Verify /api/assets/{asset_id} returns asset details for NYC assets."""
    resp = client.get("/api/assets/NYC-BX-TRN-01?city=nyc")
    assert resp.status_code == 200
    data = resp.json()
    assert data["asset_id"] == "NYC-BX-TRN-01"
    assert data["asset_type"] == "bus_stop"
    assert len(data["recommended_interventions"]) > 0


def test_api_interventions_simulate() -> None:
    """Verify /api/interventions/simulate endpoint for NYC asset."""
    resp = client.post(
        "/api/interventions/simulate",
        json={
            "asset_id": "NYC-BX-TRN-01",
            "city": "nyc",
            "trees_count": 12,
            "shade_structures_count": 2,
            "cool_pavement_m2": 300.0,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_estimated_cost"] > 0
    assert data["modeled_impact"]["peak_reduction_c"] > 0.5
    assert "MODELED ESTIMATE" in data["disclaimer"]

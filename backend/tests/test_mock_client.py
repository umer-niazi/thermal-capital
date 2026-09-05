"""Tests for the FortyGuard offline mock layer and nearest-neighbor spatial matching."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
import pytest

from fortyguard.client import FortyGuardClient
from fortyguard.exceptions import FortyGuardError
from fortyguard.mock import (
    MockFortyGuardStore,
    extract_polygon_centroid,
    get_mock_store,
    haversine_distance_km,
)
from backend.cache.cached_client import CachedFortyGuardClient
from backend.services.thermal_metrics import extract_tcm_metrics, extract_analysis_metrics


def test_client_init_without_key_in_mock_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify FortyGuardClient initializes cleanly without API key when USE_MOCK_API=true."""
    monkeypatch.setenv("USE_MOCK_API", "true")
    monkeypatch.delenv("FORTYGUARD_API_KEY", raising=False)

    client = FortyGuardClient()
    assert client.use_mock is True
    assert client.api_key is None or client.api_key == "offline-mock-key" or client.api_key == ""


def test_client_init_raises_without_key_when_mock_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify FortyGuardClient still raises FortyGuardError when USE_MOCK_API=false and no key is given."""
    monkeypatch.setenv("USE_MOCK_API", "false")
    monkeypatch.delenv("FORTYGUARD_API_KEY", raising=False)

    with pytest.raises(FortyGuardError, match="No API key provided"):
        FortyGuardClient(api_key=None)


def test_haversine_distance_calculation() -> None:
    """Verify great-circle distance between known points."""
    # NYC (40.7128, -74.0060) to Philadelphia (39.9526, -75.1652) is ~130 km
    dist = haversine_distance_km(40.7128, -74.0060, 39.9526, -75.1652)
    assert 120.0 < dist < 145.0

    # Distance to self is 0
    assert haversine_distance_km(33.4484, -112.0740, 33.4484, -112.0740) == 0.0


def test_polygon_centroid_extraction() -> None:
    """Verify extraction of polygon centroid from GeoJSON coordinates."""
    poly = {
        "type": "Polygon",
        "coordinates": [[
            [-112.10, 33.40],
            [-112.00, 33.40],
            [-112.00, 33.50],
            [-112.10, 33.50],
            [-112.10, 33.40],
        ]],
    }
    lat, lon = extract_polygon_centroid(poly)
    assert pytest.approx(lat, abs=0.01) == 33.44
    assert pytest.approx(lon, abs=0.01) == -112.06


def test_nearest_neighbor_region_matching() -> None:
    """Verify nearest-neighbor matching finds the correct geographic regions."""
    store = get_mock_store()

    # Scottsdale / Tempe, AZ -> should match Phoenix
    reg_phx, dist_phx = store.find_nearest_region(33.4151, -111.9093)
    assert reg_phx == "phoenix"
    assert dist_phx < 30.0

    # Brooklyn / Queens, NY -> should match NYC
    reg_nyc, dist_nyc = store.find_nearest_region(40.6782, -73.9442)
    assert reg_nyc == "nyc"
    assert dist_nyc < 20.0

    # Fort Worth, TX -> should match Dallas
    reg_dfw, dist_dfw = store.find_nearest_region(32.7555, -97.3308)
    assert reg_dfw == "dallas"
    assert dist_dfw < 60.0

    # Fort Lauderdale, FL -> should match Miami
    reg_mia, dist_mia = store.find_nearest_region(26.1224, -80.1373)
    assert reg_mia == "miami"
    assert dist_mia < 50.0

    # Sunnyvale / Mountain View, CA -> should match San Jose
    reg_sj, dist_sj = store.find_nearest_region(37.3688, -122.0363)
    assert reg_sj == "san_jose"
    assert dist_sj < 25.0


def test_mock_create_heatmap_offline_isolation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify create_heatmap returns authentic schema offline without network calls."""
    monkeypatch.setenv("USE_MOCK_API", "true")
    # Base URL pointing to an invalid non-routable domain to guarantee offline isolation
    client = FortyGuardClient(base_url="https://offline-invalid.invalid", api_key="dummy-key")

    poly = {
        "type": "Polygon",
        "coordinates": [[
            [-112.08, 33.44],
            [-112.06, 33.44],
            [-112.06, 33.46],
            [-112.08, 33.46],
            [-112.08, 33.44]
        ]],
    }

    # 1. TCM Snapshot
    tcm_resp = client.create_heatmap(poly, "2024-07-15", 3, analytic_type="tcm")
    assert isinstance(tcm_resp, dict)
    assert "activity_id" in tcm_resp
    assert "result" in tcm_resp
    assert "map_data" in tcm_resp["result"]
    assert len(tcm_resp["result"]["map_data"]["features"]) > 0

    # Verify thermal metrics extraction works directly on mock output
    tcm_stats = extract_tcm_metrics(tcm_resp)
    assert tcm_stats.max_max_temp_c > 30.0
    assert tcm_stats.tile_count > 0

    # 2. Exceedance Analysis
    exc_resp = client.create_heatmap(
        poly, "2024-07-15", 4, end_date="2024-07-21",
        analytic_type="exceedance", threshold=40.0, direction="above"
    )
    assert "map_data" in exc_resp["result"]
    exc_metrics = extract_analysis_metrics(exc_resp)
    assert exc_metrics.analytic_type == "exceedance"

    # 3. Persistence Analysis
    per_resp = client.create_heatmap(
        poly, "2024-07-15", 4, end_date="2024-07-21",
        analytic_type="persistence", threshold=35.0, direction="above"
    )
    assert "map_data" in per_resp["result"]
    per_metrics = extract_analysis_metrics(per_resp)
    assert per_metrics.analytic_type == "persistence"


def test_mock_environmental_parameters(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify environmental_parameters returns hourly parameters for July and August."""
    monkeypatch.setenv("USE_MOCK_API", "true")
    client = FortyGuardClient(base_url="https://offline-invalid.invalid", api_key="dummy-key")

    # July query
    resp_july = client.environmental_parameters(33.4484, -112.0740, 40.0, "2024-07-15", 3)
    assert isinstance(resp_july, dict)
    assert "result" in resp_july
    locations = resp_july["result"].get("locations", [])
    assert len(locations) > 0
    params = locations[0]["parameters"]
    assert "heat_index_celsius" in params or "apparent_temperature_celsius" in params or "air_quality:idx" in params

    # August query (multi-temporal)
    resp_aug = client.environmental_parameters(33.4484, -112.0740, 42.0, "2024-08-15", 3)
    assert isinstance(resp_aug, dict)
    assert len(resp_aug["result"].get("locations", [])) > 0


def test_mock_satellite_and_streetview(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify satellite and streetview endpoints return expected mock shapes."""
    monkeypatch.setenv("USE_MOCK_API", "true")
    client = FortyGuardClient(base_url="https://offline-invalid.invalid", api_key="dummy-key")

    # Satellite
    sat_resp = client.satellite_segmentation(37.3382, -121.8863, "2024-07-15", 3)
    assert isinstance(sat_resp, dict)
    assert "result" in sat_resp

    # Streetview
    stv_resp = client.street_view_segmentation(37.3382, -121.8863)
    assert isinstance(stv_resp, dict)
    assert "result" in stv_resp


def test_mock_system_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify mock system usage endpoints return active billing summary."""
    monkeypatch.setenv("USE_MOCK_API", "true")
    client = FortyGuardClient(base_url="https://offline-invalid.invalid", api_key="dummy-key")

    usage = client.fetch_api_key_usage()
    assert isinstance(usage, dict)
    assert "plan_details" in usage or "credit_summary" in usage or "api_key_details" in usage

    custom_usage = client.fetch_api_key_custom_usage("2024-07-01", "2024-08-31")
    assert isinstance(custom_usage, dict)
    assert "date_range" in custom_usage


def test_cached_client_with_mock(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Verify CachedFortyGuardClient seamlessly transparently operates over mock client."""
    monkeypatch.setenv("USE_MOCK_API", "true")
    monkeypatch.setenv("CACHE_DB_PATH", str(tmp_path / "mock_test_cache.db"))

    cached_cl = CachedFortyGuardClient()
    assert cached_cl.client.use_mock is True

    poly = {
        "type": "Polygon",
        "coordinates": [[
            [-96.80, 32.77],
            [-96.78, 32.77],
            [-96.78, 32.79],
            [-96.80, 32.79],
            [-96.80, 32.77]
        ]],
    }
    # Call 1 -> mock store
    r1 = cached_cl.create_heatmap(poly, "2024-07-15", 3)
    assert "map_data" in r1["result"]

    # Call 2 -> SQLite persistent cache
    r2 = cached_cl.create_heatmap(poly, "2024-07-15", 3)
    assert r1 == r2

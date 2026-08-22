"""Tests for thermal metric extraction, environmental hot-hour protection, and satellite parsing."""

from __future__ import annotations

import json
import pathlib
import pytest

from backend.services.thermal_metrics import (
    extract_analysis_metrics,
    extract_environmental_metrics,
    extract_satellite_metrics,
    extract_tcm_metrics,
)

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
PHOENIX_PROBE_PATH = ROOT_DIR / "data" / "probes" / "phoenix_tcm_2024-07-15.json"


@pytest.fixture
def phoenix_probe_data() -> dict:
    """Load verified Phoenix TCM probe response."""
    if not PHOENIX_PROBE_PATH.exists():
        pytest.skip(f"Phoenix probe cache file not found at {PHOENIX_PROBE_PATH}")
    with open(PHOENIX_PROBE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_extract_tcm_metrics_phoenix_probe(phoenix_probe_data: dict) -> None:
    """Verify that extract_tcm_metrics accurately computes spatial metrics from Phoenix tiles."""
    stats = extract_tcm_metrics(phoenix_probe_data)
    expected_count = len(phoenix_probe_data["result"]["map_data"]["features"])

    assert stats.tile_count == expected_count

    raw_stats_max = phoenix_probe_data["result"]["stats_data"]["temperature_stats"]["maximum"]
    assert stats.max_max_temp_c > raw_stats_max
    assert stats.max_max_temp_c == pytest.approx(40.55, abs=0.05)
    assert stats.mean_max_temp_c == pytest.approx(40.48, abs=0.05)
    assert stats.min_max_temp_c == pytest.approx(40.45, abs=0.05)

    assert stats.mean_average_temp_c == pytest.approx(36.05, abs=0.05)
    assert stats.min_average_temp_c == pytest.approx(35.72, abs=0.05)
    assert stats.max_average_temp_c == pytest.approx(36.22, abs=0.05)

    assert stats.mean_min_temp_c == pytest.approx(29.43, abs=0.05)
    assert stats.min_min_temp_c == pytest.approx(29.14, abs=0.05)
    assert stats.mean_diurnal_swing_c == pytest.approx(11.05, abs=0.05)


def test_extract_tcm_metrics_malformed_responses() -> None:
    """Test that extract_tcm_metrics fails explicitly on invalid or missing data."""
    with pytest.raises(ValueError, match="Expected dictionary"):
        extract_tcm_metrics("invalid string")  # type: ignore

    with pytest.raises(ValueError, match="missing required 'map_data'"):
        extract_tcm_metrics({"result": {"other_data": {}}})

    with pytest.raises(ValueError, match="features.*is empty"):
        extract_tcm_metrics({"map_data": {"type": "FeatureCollection", "features": []}})


def test_extract_analysis_metrics() -> None:
    """Test parsing analysis heatmaps (exceedance and persistence)."""
    sample_exceedance = {
        "map_data": {
            "type": "FeatureCollection",
            "features": [
                {"properties": {"tile_id": 0, "value": 18.5}, "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}},
                {"properties": {"tile_id": 1, "value": 24.0}, "geometry": {"type": "Polygon", "coordinates": [[[1, 0], [2, 0], [2, 1], [1, 1], [1, 0]]]}},
                {"properties": {"tile_id": 2, "value": 12.0}, "geometry": {"type": "Polygon", "coordinates": [[[0, 1], [1, 1], [1, 2], [0, 2], [0, 1]]]}},
            ],
        },
        "stats_data": {
            "analytic_type": "exceedance",
            "units": "hour",
            "n_cells": 3,
            "min": 12.0,
            "max": 24.0,
            "mean": 18.17,
        },
    }

    metrics = extract_analysis_metrics(sample_exceedance)
    assert metrics.analytic_type == "exceedance"
    assert metrics.units == "hour"
    assert metrics.tile_count == 3
    assert metrics.min_value == 12.0
    assert metrics.max_value == 24.0
    assert metrics.mean_value == pytest.approx(18.1667, abs=0.01)


def test_extract_environmental_metrics_hot_hour_protection() -> None:
    """Verify that environmental extraction protects against the 2 AM humidity heat-index artifact."""
    # Synthetic 24-hour Phoenix environmental parameter response:
    # Hour 15: True peak apparent temp = 43.0°C, heat index at 15:00 = 45.0°C.
    # Hour 03: Apparent temp = 22.0°C, but due to 85% humidity, raw heat index spikes to 68.0°C (API Quirk).
    timestamps = [f"2024-07-15T{h:02d}:00:00" for h in range(24)]
    apparent = [25.0] * 12 + [40.0, 42.0, 43.0, 41.0] + [30.0] * 8  # Peak at index 14 (14:00)
    wet_bulb = [18.0] * 12 + [23.5, 24.2, 24.0, 22.0] + [19.0] * 8
    rh = [75.0] * 6 + [30.0] * 12 + [60.0] * 6
    heat_index = [68.0] * 6 + [30.0] * 6 + [42.0, 44.0, 45.5, 43.0] + [35.0] * 8  # Hot-hour index 14 = 45.5

    sample_env = {
        "metadata": {
            "timezone": "America/Phoenix",
            "timestamps": timestamps,
        },
        "locations": [
            {
                "lat": 33.4484,
                "lon": -112.0740,
                "parameters": {
                    "apparent_temperature_celsius": apparent,
                    "wet_bulb_temperature_celsius": wet_bulb,
                    "relative_humidity_percent": rh,
                    "heat_index_celsius": heat_index,
                    "air_quality:idx": [55.0] * 24,
                },
                "solar_irradiance": {"clear_sky": {"ghi": 620.5}},
            }
        ],
    }

    env_metrics = extract_environmental_metrics(sample_env)

    # 1. Verify true hot hour is detected at peak apparent temperature (43.0°C at 14:00)
    assert env_metrics.peak_apparent_temperature_c == 43.0
    assert "14:00" in env_metrics.peak_apparent_temperature_time

    # 2. Verify heat index is evaluated AT the 14:00 hot hour (45.5°C), NOT the 03:00 AM artifact (68.0°C)
    assert env_metrics.peak_heat_index_c == 45.5
    assert env_metrics.peak_heat_index_c < 60.0

    # 3. Verify wet-bulb metrics
    assert env_metrics.peak_wet_bulb_temperature_c == 24.2
    assert env_metrics.minimum_wet_bulb_temperature_c == 18.0
    assert env_metrics.solar_irradiance_ghi == 620.5


def test_extract_satellite_metrics() -> None:
    """Verify fuzzy aggregation of satellite land-cover segments."""
    sample_sat = {
        "image_year": "2024",
        "segmentation": {
            "segments": {
                "building": 28.5,
                "road, route": 22.0,
                "sidewalk, pavement": 9.5,
                "tree": 6.0,
                "grass": 4.0,
                "plant": 2.0,
                "earth, ground": 25.0,
                "others": 3.0,
            }
        },
    }

    sat_metrics = extract_satellite_metrics(sample_sat)

    # Impervious = building (28.5) + road (22.0) + pavement (9.5) = 60.0%
    assert sat_metrics.impervious_pct == pytest.approx(60.0, abs=0.1)

    # Vegetation = tree (6.0) + grass (4.0) + plant (2.0) = 12.0%
    assert sat_metrics.vegetation_pct == pytest.approx(12.0, abs=0.1)

    assert sat_metrics.building_pct == 28.5
    assert sat_metrics.road_pct == 22.0
    assert sat_metrics.pavement_pct == 9.5
    assert sat_metrics.tree_pct == 6.0
    assert sat_metrics.bare_ground_pct == 25.0
    assert sat_metrics.image_year == "2024"

"""Offline unit tests for Texas candidate configuration, response parsing, and regional differentiation."""

from __future__ import annotations

import json
import pathlib
import pytest

from backend.models.thermal import CandidateSite, ThermalMetrics
from backend.services.cooling_burden import calculate_cooling_burden
from backend.services.scoring_config import ScoringConfig
from backend.services.thermal_metrics import (
    extract_analysis_metrics,
    extract_environmental_metrics,
    extract_tcm_metrics,
)
from backend.services.thermal_scoring import calculate_thermal_risk_score

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
PROBES_DIR = ROOT_DIR / "data" / "probes"
TEXAS_CANDIDATES_FILE = PROBES_DIR / "texas_candidate_sites.json"


def test_texas_candidate_sites_configuration() -> None:
    """Verify that data/probes/texas_candidate_sites.json contains valid candidate schemas."""
    assert TEXAS_CANDIDATES_FILE.exists()

    with open(TEXAS_CANDIDATES_FILE, "r", encoding="utf-8") as f:
        candidates = json.load(f)

    assert isinstance(candidates, list)
    assert len(candidates) >= 8  # 10 Texas candidates defined

    site_ids = [c["site_id"] for c in candidates]
    assert "TX-DFW-01" in site_ids
    assert "TX-HOU-01" in site_ids
    assert "TX-AUS-01" in site_ids
    assert "TX-ELP-01" in site_ids
    assert "TX-SAT-01" in site_ids

    for c in candidates:
        assert "site_id" in c
        assert "display_name" in c
        assert "city" in c
        assert "submarket" in c
        assert "archetype" in c
        assert "latitude" in c
        assert "longitude" in c
        assert "geometry" in c
        assert "rationale" in c
        assert c["geometry"]["type"] == "Polygon"
        assert len(c["geometry"]["coordinates"][0]) >= 4


def test_texas_tcm_response_parsing_synthetic() -> None:
    """Verify TCM parsing correctly extracts properties.max_temperature rather than stats_data."""
    sample_tcm_response = {
        "result": {
            "map_data": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "properties": {
                            "tile_id": 1,
                            "max_temperature": 39.85,
                            "average_temperature": 32.40,
                            "min_temperature": 26.20,
                        },
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[[-97.31, 32.95], [-97.30, 32.95], [-97.30, 32.96], [-97.31, 32.96], [-97.31, 32.95]]],
                        },
                    },
                    {
                        "properties": {
                            "tile_id": 2,
                            "max_temperature": 40.25,
                            "average_temperature": 32.80,
                            "min_temperature": 26.50,
                        },
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[[-97.30, 32.95], [-97.29, 32.95], [-97.29, 32.96], [-97.30, 32.96], [-97.30, 32.95]]],
                        },
                    },
                ],
            },
            "stats_data": {
                "temperature_stats": {
                    "maximum": 32.80,  # Pitfall field: reflects maximum of AVERAGE temperatures
                    "mean": 32.60,
                    "minimum": 32.40,
                }
            },
        }
    }

    stats = extract_tcm_metrics(sample_tcm_response)
    assert stats.tile_count == 2
    assert stats.max_max_temp_c == 40.25
    assert stats.mean_max_temp_c == pytest.approx(40.05, abs=0.01)
    assert stats.mean_average_temp_c == pytest.approx(32.60, abs=0.01)
    assert stats.mean_min_temp_c == pytest.approx(26.35, abs=0.01)
    assert stats.mean_diurnal_swing_c == pytest.approx(13.70, abs=0.01)


def test_houston_hot_hour_humidity_protection() -> None:
    """Verify Houston environmental parameters protect against overnight humidity artifacts."""
    timestamps = [f"2024-07-15T{h:02d}:00:00-06:00" for h in range(24)]
    apparent = [
        28.0, 27.5, 27.2, 27.0, 26.8, 27.1, 28.5, 30.2, 33.0, 36.5,
        39.2, 41.8, 43.5, 44.8, 45.2, 45.0, 43.2, 40.8, 37.5, 34.0, 31.5, 30.0, 29.2, 28.5
    ]
    wet_bulb = [
        24.5, 24.2, 24.0, 23.8, 23.5, 23.9, 24.8, 25.6, 26.5, 27.4,
        28.2, 28.8, 29.0, 29.2, 29.4, 29.1, 28.5, 27.8, 26.8, 25.9, 25.2, 24.8, 24.6, 24.5
    ]
    heat_index = [
        52.0, 53.5, 54.0, 55.0, 56.5, 55.0, 50.0, 47.0, 45.0, 43.5,
        42.0, 41.5, 41.0, 42.5, 43.8, 43.2, 41.0, 40.0, 42.0, 45.0, 48.0, 50.0, 51.0, 51.5
    ]

    sample_houston_env = {
        "metadata": {
            "timezone": "America/Chicago",
            "timestamps": timestamps,
        },
        "locations": [
            {
                "lat": 29.7400,
                "lon": -95.1400,
                "parameters": {
                    "apparent_temperature_celsius": apparent,
                    "wet_bulb_temperature_celsius": wet_bulb,
                    "heat_index_celsius": heat_index,
                    "relative_humidity_percent": [88.0] * 24,
                    "air_quality:idx": [45.0] * 24,
                },
                "solar_irradiance": {"clear_sky": {"ghi": 580.0}},
            }
        ],
    }

    env_metrics = extract_environmental_metrics(sample_houston_env)

    # Hot hour is at index 14 (14:00 with peak apparent temp 45.2°C)
    assert "14:00" in env_metrics.peak_apparent_temperature_time
    assert env_metrics.peak_apparent_temperature_c == 45.2
    assert env_metrics.peak_wet_bulb_temperature_c == 29.4
    # Hot-hour heat index is evaluated at 14:00 (43.8°C), NOT the nighttime 04:00 artifact (56.5°C)
    assert env_metrics.peak_heat_index_c == 43.8


def test_dry_vs_humid_differentiation_scoring() -> None:
    """Verify that scoring engine properly differentiates humid Gulf heat from arid desert heat."""
    # 1. El Paso Arid Desert profile (High dry-bulb, low wet-bulb, wide diurnal swing)
    el_paso_metrics = ThermalMetrics(
        peak_temperature_c=41.5,
        peak_temperature_f=106.7,
        mean_temperature_c=33.5,
        mean_temperature_f=92.3,
        overnight_min_temperature_c=24.0,
        overnight_min_temperature_f=75.2,
        diurnal_swing_c=17.5,
        diurnal_swing_f=31.5,
        exceedance_hours=35.0,
        persistence_hours=6.0,
        peak_wet_bulb_c=18.5,  # Low wet-bulb (safe for evaporative cooling)
        peak_wet_bulb_f=65.3,
    )
    el_paso_cooling = calculate_cooling_burden(
        tcm_metrics=el_paso_metrics,
        exceedance_hours_40c=35.0,
        persistence_hours_35c=6.0,
        window_days=7,
    )
    el_paso_risk = calculate_thermal_risk_score(
        metrics=el_paso_metrics,
        cooling_burden=el_paso_cooling,
        window_hours=168,
    )

    # 2. Houston Humid Maritime profile (Moderate dry-bulb, severe wet-bulb, high nighttime floor)
    houston_metrics = ThermalMetrics(
        peak_temperature_c=37.5,
        peak_temperature_f=99.5,
        mean_temperature_c=32.0,
        mean_temperature_f=89.6,
        overnight_min_temperature_c=28.5,  # High nighttime floor (poor recovery)
        overnight_min_temperature_f=83.3,
        diurnal_swing_c=9.0,
        diurnal_swing_f=16.2,
        exceedance_hours=0.0,
        persistence_hours=4.0,
        peak_wet_bulb_c=29.2,  # Severe wet-bulb (evaporative economizers fully curtailed)
        peak_wet_bulb_f=84.5,
    )
    houston_cooling = calculate_cooling_burden(
        tcm_metrics=houston_metrics,
        exceedance_hours_40c=0.0,
        persistence_hours_35c=4.0,
        window_days=7,
    )
    houston_risk = calculate_thermal_risk_score(
        metrics=houston_metrics,
        cooling_burden=houston_cooling,
        window_hours=168,
    )

    # Verify meaningful component differentiation
    # Houston has higher wet-bulb burden score
    assert houston_risk.components["cooling_burden"].normalized_score > el_paso_risk.components["cooling_burden"].normalized_score
    # Houston has higher overnight retention score
    assert houston_risk.components["overnight_retention"].normalized_score > el_paso_risk.components["overnight_retention"].normalized_score
    # El Paso has higher extreme heat score
    assert el_paso_risk.components["extreme_heat_exposure"].normalized_score > houston_risk.components["extreme_heat_exposure"].normalized_score

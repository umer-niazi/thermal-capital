"""Tests for deterministic 5-component thermal risk scoring service."""

from __future__ import annotations

import pytest

from backend.models.thermal import EnvironmentalMetrics, ThermalMetrics
from backend.services.scoring_config import ScoringConfig
from backend.services.thermal_scoring import calculate_thermal_risk_score


def test_thermal_scoring_weights_sum_to_one() -> None:
    """Verify that default 5-component scoring weights sum exactly to 1.0 (100%)."""
    cfg = ScoringConfig()
    total_weights = (
        cfg.weight_extreme_heat
        + cfg.weight_duration_share
        + cfg.weight_persistence
        + cfg.weight_wet_bulb_burden
        + cfg.weight_overnight_retention
    )
    assert total_weights == pytest.approx(1.0, abs=0.0001)


def test_thermal_scoring_tcm_preliminary() -> None:
    """Test preliminary score calculation from TCM snapshot metrics with fallbacks."""
    metrics = ThermalMetrics.from_celsius(
        peak_c=40.49,
        mean_c=36.01,
        min_c=29.33,
        diurnal_swing_c=11.16,
    )

    result = calculate_thermal_risk_score(metrics)

    assert result.data_completeness == "preliminary_tcm_only"
    assert 0.0 <= result.total_score <= 100.0
    assert result.risk_category in ("Moderate", "High", "Severe", "Extreme")
    assert len(result.components) == 5

    # Verify fallback flags are set for unmeasured exceedance / persistence / wet-bulb
    assert result.components["extreme_heat_exposure"].is_estimated_or_fallback is True
    assert result.components["exceedance_duration"].is_estimated_or_fallback is True
    assert result.components["heat_persistence"].is_estimated_or_fallback is True
    assert result.components["cooling_burden"].is_estimated_or_fallback is True
    assert result.components["overnight_retention"].is_estimated_or_fallback is False

    sum_contributions = sum(c.weighted_contribution for c in result.components.values())
    assert result.total_score == pytest.approx(sum_contributions, abs=0.1)


def test_thermal_scoring_full_measured_analysis() -> None:
    """Test scoring when full exceedance, persistence, and environmental parameters are provided."""
    metrics = ThermalMetrics.from_celsius(
        peak_c=42.50,
        mean_c=36.50,
        min_c=30.00,
        diurnal_swing_c=12.50,
        exceedance_hours=36.0,  # 36 hours >40°C over 168h
        persistence_hours=14.0,  # 14 hours continuous >35°C
        peak_wet_bulb_c=25.2,  # >24°C severe economizer threshold
    )

    env_metrics = EnvironmentalMetrics(
        peak_apparent_temperature_c=44.0,
        peak_apparent_temperature_f=111.2,
        peak_apparent_temperature_time="15:00",
        peak_wet_bulb_temperature_c=25.2,
        peak_wet_bulb_temperature_f=77.36,
        mean_wet_bulb_temperature_c=20.5,
        mean_wet_bulb_temperature_f=68.9,
        minimum_wet_bulb_temperature_c=17.0,
        minimum_wet_bulb_temperature_f=62.6,
        peak_relative_humidity_percent=65.0,
        peak_heat_index_c=46.5,
        peak_heat_index_f=115.7,
        peak_heat_index_time="15:00",
    )

    result = calculate_thermal_risk_score(metrics, env_metrics=env_metrics, window_hours=168)

    assert result.data_completeness == "full_measured"
    assert result.components["extreme_heat_exposure"].is_estimated_or_fallback is False
    assert result.components["exceedance_duration"].is_estimated_or_fallback is False
    assert result.components["heat_persistence"].is_estimated_or_fallback is False
    assert result.components["cooling_burden"].is_estimated_or_fallback is False
    assert result.components["extreme_heat_exposure"].raw_value == 36.0
    assert result.components["heat_persistence"].raw_value == 14.0
    assert result.risk_category in ("High", "Severe", "Extreme")


def test_thermal_scoring_extreme_boundary_conditions() -> None:
    """Verify scoring behavior at lower and upper thermal extremes."""
    # Low-risk baseline
    cool_metrics = ThermalMetrics.from_celsius(
        peak_c=30.0,
        mean_c=24.0,
        min_c=18.0,
        diurnal_swing_c=12.0,
        exceedance_hours=0.0,
        persistence_hours=0.0,
        peak_wet_bulb_c=14.0,
    )
    cool_res = calculate_thermal_risk_score(cool_metrics)
    assert cool_res.total_score == pytest.approx(0.0, abs=0.01)
    assert cool_res.risk_category == "Low"

    # Extreme worst-case severe conditions
    severe_metrics = ThermalMetrics.from_celsius(
        peak_c=48.0,
        mean_c=39.0,
        min_c=33.0,
        diurnal_swing_c=5.0,
        exceedance_hours=60.0,
        persistence_hours=20.0,
        peak_wet_bulb_c=28.0,
    )
    severe_res = calculate_thermal_risk_score(severe_metrics)
    assert severe_res.total_score == pytest.approx(100.0, abs=0.01)
    assert severe_res.risk_category == "Extreme"

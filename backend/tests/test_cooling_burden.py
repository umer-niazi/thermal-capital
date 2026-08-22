"""Tests for data center cooling burden proxy indicator calculations."""

from __future__ import annotations

import pytest

from backend.models.thermal import EnvironmentalMetrics, ThermalMetrics
from backend.services.cooling_burden import calculate_cooling_burden


def test_calculate_cooling_burden() -> None:
    """Verify calculation of derived data center thermal stress metrics."""
    metrics = ThermalMetrics.from_celsius(
        peak_c=41.0,
        mean_c=36.0,
        min_c=29.0,
        diurnal_swing_c=12.0,
    )

    env_metrics = EnvironmentalMetrics(
        peak_apparent_temperature_c=43.0,
        peak_apparent_temperature_f=109.4,
        peak_apparent_temperature_time="14:00",
        peak_wet_bulb_temperature_c=23.5,
        peak_wet_bulb_temperature_f=74.3,
        mean_wet_bulb_temperature_c=19.0,
        mean_wet_bulb_temperature_f=66.2,
        minimum_wet_bulb_temperature_c=16.0,
        minimum_wet_bulb_temperature_f=60.8,
        peak_relative_humidity_percent=55.0,
    )

    burden = calculate_cooling_burden(
        tcm_metrics=metrics,
        exceedance_hours_40c=28.5,
        persistence_hours_35c=12.0,
        env_metrics=env_metrics,
        window_days=7,
    )

    # 1. Cooling Degree Hours above 25°C: (36.0 - 25.0) * 24 * 7 = 11.0 * 168 = 1848.0 CDH
    assert burden.cooling_degree_hours_above_25c == pytest.approx(1848.0, abs=5.0)

    # 2. Hours above 40°C from exceedance layer
    assert burden.hours_above_40c == 28.5

    # 3. Peak wet-bulb attached
    assert burden.peak_wet_bulb_c == 23.5

    # 4. Overnight min
    assert burden.overnight_min_c == 29.0

    # 5. Chiller COP loss proxy at 41°C (41 - 35) * 1.75% = 10.5%
    assert burden.chiller_cop_degradation_pct == pytest.approx(10.5, abs=0.1)

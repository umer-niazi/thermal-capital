"""Cooling burden and critical data center infrastructure thermal proxy model."""

from __future__ import annotations

from typing import Any
from backend.models.thermal import CoolingBurdenMetrics, EnvironmentalMetrics, ThermalMetrics


def calculate_cooling_burden(
    tcm_metrics: ThermalMetrics,
    exceedance_hours_40c: float | None = None,
    persistence_hours_35c: float | None = None,
    env_metrics: EnvironmentalMetrics | None = None,
    window_days: int = 7,
) -> CoolingBurdenMetrics:
    """Calculate derived data center thermal stress and cooling burden proxy indicators.

    Engineering Background (ASHRAE TC 9.9 & Chiller Plant Mechanics):
    1. High ambient dry-bulb temperature increases chiller condensing temperature,
       raising compressor discharge pressure and degrading Coefficient of Performance (COP).
    2. Air-cooled chillers rated at 35°C (95°F) experience ~1.5% to 2.0% efficiency drop
       per 1°C increase above rating.
    3. Evaporative cooling towers and economizers are governed by Wet-Bulb temperature;
       wet-bulb exceeding 24°C severely curtails evaporative capacity and forces mechanical trim.
    4. Elevated overnight minimums prevent nighttime thermal purging of transformer enclosures.

    Parameters
    ----------
    tcm_metrics:
        Site-level TCM temperature metrics (peak, mean, min, swing).
    exceedance_hours_40c:
        Measured exceedance hours above 40°C from FortyGuard exceedance heatmap.
    persistence_hours_35c:
        Measured persistence hours above 35°C from FortyGuard persistence heatmap.
    env_metrics:
        Optional point-level environmental metrics (wet-bulb, apparent temp).
    window_days:
        Number of days in the multi-day analysis window (default: 7).

    Returns
    -------
    CoolingBurdenMetrics
        Itemized cooling infrastructure strain indicators.
    """
    mean_c = tcm_metrics.mean_temperature_c
    peak_c = tcm_metrics.peak_temperature_c
    min_c = tcm_metrics.overnight_min_temperature_c

    # 1. Cooling Degree Hours above 25°C (77°F) baseline
    # Over 24 hours with mean temperature mean_c:
    daily_cdh_25 = max(0.0, mean_c - 25.0) * 24.0
    total_cdh_25 = round(daily_cdh_25 * window_days, 1)

    # 2. Hours above 35°C (Economizer / High-efficiency cutoff)
    if persistence_hours_35c is not None:
        # If persistence at 35°C is measured, scale to estimated total window hours
        # assuming diurnal repetition
        hours_35 = round(min(float(window_days * 24), persistence_hours_35c * window_days * 0.9), 1)
    else:
        # Synthetic estimation from 24h sinus profile
        if peak_c > 35.0:
            fraction_above_35 = max(0.0, min(1.0, (peak_c - 35.0) / max(0.5, peak_c - min_c)))
            hours_35 = round(fraction_above_35 * 14.0 * window_days, 1)
        else:
            hours_35 = 0.0

    # 3. Hours above 40°C (Severe Chiller Stress)
    if exceedance_hours_40c is not None:
        hours_40 = round(exceedance_hours_40c, 1)
    elif tcm_metrics.exceedance_hours is not None:
        hours_40 = round(tcm_metrics.exceedance_hours, 1)
    else:
        if peak_c > 40.0:
            fraction_above_40 = max(0.0, min(1.0, (peak_c - 40.0) / max(0.5, peak_c - min_c)))
            hours_40 = round(fraction_above_40 * 8.0 * window_days, 1)
        else:
            hours_40 = 0.0

    # 4. Thermal Recovery Hours (hours/day where ambient < 30°C allows cooling)
    if min_c < 30.0:
        recovery_fraction = max(0.0, min(1.0, (30.0 - min_c) / max(0.5, peak_c - min_c)))
        recovery_hours = round(recovery_fraction * 10.0, 1)
    else:
        recovery_hours = 0.0

    # 5. Chiller COP Degradation Proxy (%)
    # Modeled at 1.75% efficiency loss per °C above 35°C ambient design rating
    if peak_c > 35.0:
        cop_loss_pct = round((peak_c - 35.0) * 1.75, 2)
    else:
        cop_loss_pct = 0.0

    peak_wb = env_metrics.peak_wet_bulb_temperature_c if env_metrics else None

    return CoolingBurdenMetrics(
        cooling_degree_hours_above_25c=total_cdh_25,
        hours_above_35c=hours_35,
        hours_above_40c=hours_40,
        peak_wet_bulb_c=peak_wb,
        overnight_min_c=round(min_c, 2),
        thermal_recovery_hours=recovery_hours,
        chiller_cop_degradation_pct=cop_loss_pct,
    )

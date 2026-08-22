"""Transparent, deterministic thermal risk scoring service for candidate development sites."""

from __future__ import annotations

from typing import Any

from backend.models.thermal import (
    CoolingBurdenMetrics,
    EnvironmentalMetrics,
    ScoreComponent,
    ThermalMetrics,
    ThermalRiskResult,
)
from backend.services.scoring_config import ScoringConfig, default_scoring_config


def _normalize(val: float, lower: float, upper: float) -> float:
    """Linearly scale a value between lower (0.0) and upper (100.0), clamped to [0, 100]."""
    if upper <= lower:
        return 0.0
    scaled = (val - lower) / (upper - lower)
    clamped = max(0.0, min(1.0, scaled))
    return round(clamped * 100.0, 2)


def calculate_thermal_risk_score(
    metrics: ThermalMetrics | dict[str, Any],
    cooling_burden: CoolingBurdenMetrics | None = None,
    env_metrics: EnvironmentalMetrics | None = None,
    window_hours: int = 168,  # 7 days * 24h
    config: ScoringConfig | None = None,
    portfolio_score: float | None = None,
) -> ThermalRiskResult:
    """Calculate the comprehensive multi-factor thermal risk score (0–100).

    The model evaluates five distinct dimensions of industrial thermal risk:
    1. Extreme Heat Exposure (30%): Exceedance hours, afternoon heat index, or peak ambient thermal stress.
    2. Heat Exceedance Duration (25%): Sustained duty cycle above threshold or Cooling Degree Hours burden.
    3. Heat Persistence (20%): Longest continuous unbroken heat run without nighttime thermal relief.
    4. Wet-Bulb / Cooling Burden (15%): Evaporative economizer curtailment (ASHRAE ~24°C limit) & chiller lift.
    5. Overnight Thermal Retention (10%): Urban heat island nighttime floor and electrical recovery impediment.

    Parameters
    ----------
    metrics:
        ThermalMetrics model or dictionary matching its schema.
    cooling_burden:
        Optional CoolingBurdenMetrics model.
    env_metrics:
        Optional EnvironmentalMetrics model.
    window_hours:
        Total hours in the analysis window (default: 168h for 7 days).
    config:
        Optional ScoringConfig instance.
    portfolio_score:
        Optional normalized portfolio percentile score.

    Returns
    -------
    ThermalRiskResult
        Total score (0-100), risk category, itemized component breakdown, profile metadata, and explanations.
    """
    cfg = config or default_scoring_config()

    if isinstance(metrics, dict):
        if "peak_temperature_f" not in metrics and "peak_temperature_c" in metrics:
            m = ThermalMetrics.from_celsius(
                peak_c=metrics["peak_temperature_c"],
                mean_c=metrics.get("mean_temperature_c", metrics["peak_temperature_c"]),
                min_c=metrics.get("overnight_min_temperature_c", metrics["peak_temperature_c"]),
                diurnal_swing_c=metrics.get("diurnal_swing_c"),
                exceedance_hours=metrics.get("exceedance_hours"),
                persistence_hours=metrics.get("persistence_hours"),
                peak_wet_bulb_c=metrics.get("peak_wet_bulb_c"),
                peak_apparent_c=metrics.get("peak_apparent_temperature_c"),
            )
        else:
            m = ThermalMetrics.model_validate(metrics)
    else:
        m = metrics

    components: dict[str, ScoreComponent] = {}
    explanations: list[str] = []
    has_proxies = False

    # -------------------------------------------------------------------------
    # Component 1: Extreme Heat Exposure (Weight: 30%)
    # -------------------------------------------------------------------------
    if m.exceedance_hours is not None:
        if m.exceedance_hours > 0.0:
            norm_1 = _normalize(m.exceedance_hours, cfg.exceedance_lower_h, cfg.exceedance_severe_h)
            raw_1 = round(m.exceedance_hours, 1)
            units_1 = "hours > threshold"
            desc_1 = f"Measured {m.exceedance_hours:.1f} hours exceeding threshold over {window_hours}h window"
            source_1 = "FortyGuard Exceedance Heatmap"
        elif env_metrics and env_metrics.peak_heat_index_c is not None and env_metrics.peak_heat_index_c > m.peak_temperature_c:
            # Humid extreme heat: use afternoon hot-hour Heat Index
            hi_val = env_metrics.peak_heat_index_c
            norm_1 = _normalize(hi_val, cfg.heat_index_lower_c, cfg.heat_index_severe_c)
            raw_1 = round(hi_val, 1)
            units_1 = "°C heat index"
            desc_1 = f"Afternoon hot-hour Heat Index of {hi_val:.1f} °C ({env_metrics.peak_heat_index_f or (hi_val * 9/5 + 32):.1f} °F)"
            source_1 = "FortyGuard /v1/env_params (Hot-Hour Heat Index)"
        else:
            norm_1 = _normalize(m.peak_temperature_c, cfg.peak_temp_lower_c, cfg.peak_temp_severe_c)
            raw_1 = round(m.peak_temperature_c, 2)
            units_1 = "°C peak"
            desc_1 = f"Peak ambient temperature of {m.peak_temperature_c:.2f} °C ({m.peak_temperature_f:.1f} °F)"
            source_1 = "FortyGuard TCM Heatmap"
        fallback_1 = False
    else:
        norm_1 = _normalize(m.peak_temperature_c, cfg.peak_temp_lower_c, cfg.peak_temp_severe_c)
        raw_1 = round(m.peak_temperature_c, 2)
        units_1 = "°C peak"
        desc_1 = f"Peak ambient temperature of {m.peak_temperature_c:.2f} °C ({m.peak_temperature_f:.1f} °F) [Snapshot proxy]"
        source_1 = "FortyGuard TCM Heatmap (Peak Proxy)"
        fallback_1 = True
        has_proxies = True

    w1 = cfg.weight_extreme_heat
    c1 = round(norm_1 * w1, 2)
    components["extreme_heat_exposure"] = ScoreComponent(
        name="Extreme Heat Exposure",
        weight=w1,
        raw_value=raw_1,
        raw_units=units_1,
        normalized_score=norm_1,
        weighted_contribution=c1,
        description=desc_1,
        data_source=source_1,
        is_estimated_or_fallback=fallback_1,
    )

    # -------------------------------------------------------------------------
    # Component 2: Heat Exceedance Duration / Duty Cycle (Weight: 25%)
    # -------------------------------------------------------------------------
    if m.exceedance_hours is not None and window_hours > 0:
        if m.exceedance_hours > 0.0:
            exceed_share = (m.exceedance_hours / window_hours) * 100.0
            norm_2 = _normalize(exceed_share, cfg.duration_share_lower_pct, cfg.duration_share_severe_pct)
            raw_2 = round(exceed_share, 1)
            units_2 = "% of window"
            desc_2 = f"{exceed_share:.1f}% of study window operated in severe heat strain condition"
            source_2 = "FortyGuard Exceedance Heatmap"
        elif cooling_burden and cooling_burden.cooling_degree_hours_above_25c > 0:
            cdh = cooling_burden.cooling_degree_hours_above_25c
            norm_2 = _normalize(cdh, cfg.cdh_lower, cfg.cdh_severe)
            raw_2 = round(cdh, 1)
            units_2 = "CDH"
            desc_2 = f"Cumulative Cooling Degree Hours of {cdh:.1f} CDH (>25°C baseline)"
            source_2 = "Derived Cooling Burden Model"
        else:
            norm_2 = _normalize(m.mean_temperature_c, cfg.mean_temp_lower_c, cfg.mean_temp_severe_c)
            raw_2 = round(m.mean_temperature_c, 2)
            units_2 = "°C mean"
            desc_2 = f"24-hour mean temperature of {m.mean_temperature_c:.2f} °C [Daily Mean Baseline]"
            source_2 = "FortyGuard TCM Heatmap"
        fallback_2 = False
    else:
        norm_2 = _normalize(m.mean_temperature_c, cfg.mean_temp_lower_c, cfg.mean_temp_severe_c)
        raw_2 = round(m.mean_temperature_c, 2)
        units_2 = "°C mean"
        desc_2 = f"24-hour mean temperature of {m.mean_temperature_c:.2f} °C [Daily Mean Proxy]"
        source_2 = "FortyGuard TCM Heatmap (Mean Proxy)"
        fallback_2 = True
        has_proxies = True

    w2 = cfg.weight_duration_share
    c2 = round(norm_2 * w2, 2)
    components["exceedance_duration"] = ScoreComponent(
        name="Heat Exceedance Duration",
        weight=w2,
        raw_value=raw_2,
        raw_units=units_2,
        normalized_score=norm_2,
        weighted_contribution=c2,
        description=desc_2,
        data_source=source_2,
        is_estimated_or_fallback=fallback_2,
    )

    # -------------------------------------------------------------------------
    # Component 3: Heat Persistence & Recovery Failure (Weight: 20%)
    # -------------------------------------------------------------------------
    if m.persistence_hours is not None:
        norm_3 = _normalize(m.persistence_hours, cfg.persistence_lower_h, cfg.persistence_severe_h)
        raw_3 = round(m.persistence_hours, 1)
        units_3 = "hours unbroken"
        desc_3 = f"Longest continuous unbroken run of {m.persistence_hours:.1f} hours >35°C without overnight drop"
        source_3 = "FortyGuard Persistence Heatmap"
        fallback_3 = False
    else:
        swing_deficit = max(0.0, cfg.swing_optimal_c - m.diurnal_swing_c)
        swing_span = max(1.0, cfg.swing_optimal_c - cfg.swing_constricted_c)
        norm_3 = _normalize(swing_deficit, 0.0, swing_span)
        raw_3 = round(m.diurnal_swing_c, 2)
        units_3 = "°C swing"
        desc_3 = f"Diurnal swing of {m.diurnal_swing_c:.2f} °C indicates heat retention capacity [Diurnal Proxy]"
        source_3 = "FortyGuard TCM Heatmap (Swing Proxy)"
        fallback_3 = True
        has_proxies = True

    w3 = cfg.weight_persistence
    c3 = round(norm_3 * w3, 2)
    components["heat_persistence"] = ScoreComponent(
        name="Heat Persistence & Recovery Failure",
        weight=w3,
        raw_value=raw_3,
        raw_units=units_3,
        normalized_score=norm_3,
        weighted_contribution=c3,
        description=desc_3,
        data_source=source_3,
        is_estimated_or_fallback=fallback_3,
    )

    # -------------------------------------------------------------------------
    # Component 4: Wet-Bulb / Cooling Infrastructure Burden (Weight: 15%)
    # -------------------------------------------------------------------------
    wb_val = None
    if env_metrics and env_metrics.peak_wet_bulb_temperature_c is not None:
        wb_val = env_metrics.peak_wet_bulb_temperature_c
    elif m.peak_wet_bulb_c is not None:
        wb_val = m.peak_wet_bulb_c

    if wb_val is not None:
        norm_4 = _normalize(wb_val, cfg.wet_bulb_lower_c, cfg.wet_bulb_severe_c)
        raw_4 = round(wb_val, 1)
        units_4 = "°C wet-bulb"
        desc_4 = f"Peak wet-bulb temperature of {wb_val:.1f} °C (ASHRAE evaporative economizer threshold ~24°C)"
        source_4 = "FortyGuard Environmental Parameters (/v1/env_params)"
        fallback_4 = False
    elif cooling_burden and cooling_burden.chiller_cop_degradation_pct is not None:
        cop_loss = cooling_burden.chiller_cop_degradation_pct
        norm_4 = _normalize(cop_loss, cfg.cop_loss_lower_pct, cfg.cop_loss_severe_pct)
        raw_4 = round(cop_loss, 1)
        units_4 = "% COP drop"
        desc_4 = f"Modeled chiller COP efficiency degradation of {cop_loss:.1f}% relative to 35°C rating [Chiller Proxy]"
        source_4 = "Derived Cooling Burden Model"
        fallback_4 = True
        has_proxies = True
    else:
        norm_4 = _normalize(m.peak_temperature_c, 33.0, 43.0)
        raw_4 = round(m.peak_temperature_c, 2)
        units_4 = "°C peak"
        desc_4 = f"Ambient peak {m.peak_temperature_c:.1f} °C used for chiller derating estimate"
        source_4 = "FortyGuard TCM Heatmap (Chiller Proxy)"
        fallback_4 = True
        has_proxies = True

    w4 = cfg.weight_wet_bulb_burden
    c4 = round(norm_4 * w4, 2)
    components["cooling_burden"] = ScoreComponent(
        name="Wet-Bulb & Cooling Plant Burden",
        weight=w4,
        raw_value=raw_4,
        raw_units=units_4,
        normalized_score=norm_4,
        weighted_contribution=c4,
        description=desc_4,
        data_source=source_4,
        is_estimated_or_fallback=fallback_4,
    )

    # -------------------------------------------------------------------------
    # Component 5: Overnight Thermal Retention / UHI Floor (Weight: 10%)
    # -------------------------------------------------------------------------
    norm_5 = _normalize(m.overnight_min_temperature_c, cfg.overnight_min_lower_c, cfg.overnight_min_severe_c)
    w5 = cfg.weight_overnight_retention
    c5 = round(norm_5 * w5, 2)
    components["overnight_retention"] = ScoreComponent(
        name="Overnight Thermal Retention",
        weight=w5,
        raw_value=round(m.overnight_min_temperature_c, 2),
        raw_units="°C",
        normalized_score=norm_5,
        weighted_contribution=c5,
        description=f"Overnight temperature floor of {m.overnight_min_temperature_c:.2f} °C ({m.overnight_min_temperature_f:.1f} °F)",
        data_source="FortyGuard TCM Heatmap",
        is_estimated_or_fallback=False,
    )

    # -------------------------------------------------------------------------
    # Composite Score & Explanations
    # -------------------------------------------------------------------------
    total_score = round(c1 + c2 + c3 + c4 + c5, 1)
    total_score = max(0.0, min(100.0, total_score))
    category = cfg.get_category(total_score)

    if has_proxies:
        explanations.append(
            "Preliminary Score: Partial metrics supplied. Multi-day exceedance, persistence, or wet-bulb were estimated from diurnal proxies."
        )
    else:
        explanations.append(
            f"Full Multi-Dimensional Score: Computed from measured FortyGuard layers under {cfg.profile_name.value} profile."
        )

    explanations.append(
        f"Site overall Thermal Risk Score is categorized as '{category}' ({total_score:.1f}/100)."
    )

    if norm_1 > 60.0:
        explanations.append(
            "High extreme heat exposure indicates frequent operation in chiller high-head pressure trip risk territory."
        )
    if norm_3 > 50.0:
        explanations.append(
            "Elevated persistence indicates site experiences unbroken high-temperature runs, limiting electrical recovery."
        )
    if wb_val and wb_val >= 24.0:
        explanations.append(
            f"Peak wet-bulb temperature ({wb_val:.1f} °C) approaches or exceeds the ASHRAE 24°C evaporative economizer threshold."
        )

    completeness = "preliminary_tcm_only" if (m.exceedance_hours is None and m.persistence_hours is None) else ("enriched" if has_proxies else "full_measured")

    return ThermalRiskResult(
        total_score=total_score,
        risk_category=category,
        components=components,
        explanation=explanations,
        data_completeness=completeness,
        scoring_profile=cfg.profile_name.value,
        portfolio_score=portfolio_score,
    )

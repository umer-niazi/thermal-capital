"""Orchestration service for comprehensive single-site thermal due diligence analysis."""

from __future__ import annotations

from typing import Any

from backend.models.thermal import (
    CandidateSite,
    CoolingBurdenMetrics,
    EnvironmentalMetrics,
    SatelliteMetrics,
    SiteThermalExposure,
    ThermalMetrics,
)
from backend.services.cooling_burden import calculate_cooling_burden
from backend.services.geo import clip_analysis_layer_to_site, clip_heatmap_to_site
from backend.services.scoring_config import ScoringConfig
from backend.services.thermal_metrics import (
    extract_environmental_metrics,
    extract_satellite_metrics,
)
from backend.services.thermal_scoring import calculate_thermal_risk_score


def _extract_features(resp: dict[str, Any]) -> list[dict[str, Any]]:
    """Helper to extract GeoJSON features list from a FortyGuard response."""
    result = resp.get("result", resp)
    map_data = result.get("map_data", result if result.get("type") == "FeatureCollection" else {})
    return map_data.get("features", [])


def analyze_candidate_site(
    site: CandidateSite,
    tcm_raw: dict[str, Any],
    exceedance_raw: dict[str, Any] | None = None,
    persistence_raw: dict[str, Any] | None = None,
    env_raw: dict[str, Any] | None = None,
    sat_raw: dict[str, Any] | None = None,
    window_hours: int = 168,
    scoring_config: ScoringConfig | None = None,
) -> SiteThermalExposure:
    """Analyze a single candidate site across all available FortyGuard layers.

    Parameters
    ----------
    site:
        CandidateSite definition.
    tcm_raw:
        Raw TCM heatmap response.
    exceedance_raw:
        Optional raw exceedance heatmap response (>40°C).
    persistence_raw:
        Optional raw persistence heatmap response (>35°C).
    env_raw:
        Optional raw environmental parameters response (/v1/env_params).
    sat_raw:
        Optional raw satellite land-cover response (/v1/satellite).
    window_hours:
        Analysis window duration in hours (default: 168h for 7 days).
    scoring_config:
        Optional ScoringConfig instance.

    Returns
    -------
    SiteThermalExposure
        Unified site thermal metrics, risk score, cooling burden proxies, and coverage stats.
    """
    # 1. Clip TCM Heatmap
    tcm_features = _extract_features(tcm_raw)
    if not tcm_features:
        raise ValueError("TCM response contains no map_data features to clip")

    tcm_clip = clip_heatmap_to_site(tcm_features, site.geometry, site_id=site.id)

    # 2. Clip Exceedance Layer if available
    exceedance_hours: float | None = None
    if exceedance_raw is not None:
        exc_features = _extract_features(exceedance_raw)
        if exc_features:
            exc_clip = clip_analysis_layer_to_site(exc_features, site.geometry, site_id=site.id)
            exceedance_hours = exc_clip.weighted_value

    # 3. Clip Persistence Layer if available
    persistence_hours: float | None = None
    if persistence_raw is not None:
        per_features = _extract_features(persistence_raw)
        if per_features:
            per_clip = clip_analysis_layer_to_site(per_features, site.geometry, site_id=site.id)
            persistence_hours = per_clip.weighted_value

    # 4. Parse Environmental Metrics if available
    env_metrics: EnvironmentalMetrics | None = None
    if env_raw is not None:
        try:
            env_metrics = extract_environmental_metrics(env_raw)
        except Exception:
            env_metrics = None

    # 5. Parse Satellite Land-Cover Metrics if available
    sat_metrics: SatelliteMetrics | None = None
    if sat_raw is not None:
        try:
            sat_metrics = extract_satellite_metrics(sat_raw)
        except Exception:
            sat_metrics = None

    # 6. Build ThermalMetrics model
    tcm_metrics = tcm_clip.to_thermal_metrics(
        exceedance_hours=exceedance_hours,
        persistence_hours=persistence_hours,
        peak_wet_bulb_c=env_metrics.peak_wet_bulb_temperature_c if env_metrics else None,
        peak_apparent_c=env_metrics.peak_apparent_temperature_c if env_metrics else None,
        vegetation_pct=sat_metrics.vegetation_pct if sat_metrics else None,
        impervious_pct=sat_metrics.impervious_pct if sat_metrics else None,
    )

    # 7. Compute Cooling Burden Proxies
    window_days = max(1, round(window_hours / 24))
    cooling_burden = calculate_cooling_burden(
        tcm_metrics=tcm_metrics,
        exceedance_hours_40c=exceedance_hours,
        persistence_hours_35c=persistence_hours,
        env_metrics=env_metrics,
        window_days=window_days,
    )

    # 8. Compute 5-Component Thermal Risk Score
    risk_result = calculate_thermal_risk_score(
        metrics=tcm_metrics,
        cooling_burden=cooling_burden,
        env_metrics=env_metrics,
        window_hours=window_hours,
        config=scoring_config,
    )

    # 9. Check coverage warning
    coverage_warning: str | None = None
    if tcm_clip.coverage_pct < 85.0:
        coverage_warning = (
            f"Partial tile coverage ({tcm_clip.coverage_pct:.1f}%). "
            "Portions of the parcel extend outside the analyzed heatmap AOI."
        )

    return SiteThermalExposure(
        site_id=site.id,
        site_name=site.name,
        rank=1,
        city=site.city,
        submarket=site.submarket,
        market_cluster=site.market_cluster,
        archetype=site.archetype,
        data_status=site.data_status or "measured",
        data_completeness=risk_result.data_completeness,
        notes=site.notes,
        geometry=site.geometry,
        tcm_metrics=tcm_metrics,
        exceedance_hours=exceedance_hours,
        persistence_hours=persistence_hours,
        environmental_metrics=env_metrics,
        satellite_metrics=sat_metrics,
        cooling_burden=cooling_burden,
        risk_result=risk_result,
        coverage_pct=tcm_clip.coverage_pct,
        contributing_tile_count=tcm_clip.contributing_tile_count,
        coverage_warning=coverage_warning,
    )

"""Multi-day heat analysis service managing FortyGuard TCM, Exceedance, and Persistence requests."""

from __future__ import annotations

from typing import Any

from backend.cache.cached_client import CachedFortyGuardClient
from backend.services.thermal_metrics import extract_analysis_metrics, extract_tcm_metrics


def fetch_shared_heat_layers(
    client: CachedFortyGuardClient,
    polygon_aoi: dict[str, Any],
    start_date: str = "2024-07-15",
    end_date: str = "2024-07-21",
    granularity: int = 100,
    exceedance_threshold: float = 40.0,
    persistence_threshold: float = 35.0,
    bypass_cache: bool = False,
) -> dict[str, Any]:
    """Fetch the three foundational heat layers over a shared AOI using transparent caching.

    Layers fetched:
    1. TCM Daily Aggregate (filter_type=3, start_date): Baseline daily peak, mean, min, swing.
    2. Exceedance Heatmap (filter_type=4, start_date..end_date, threshold=40°C, direction="above"): Total hours >40°C.
    3. Persistence Heatmap (filter_type=4, start_date..end_date, threshold=35°C, direction="above"): Longest continuous run >35°C.

    Parameters
    ----------
    client:
        CachedFortyGuardClient instance.
    polygon_aoi:
        GeoJSON FeatureCollection enclosing the candidate parcels.
    start_date:
        Start date of heatwave window (e.g. '2024-07-15').
    end_date:
        End date of heatwave window (e.g. '2024-07-21').
    granularity:
        Spatial resolution in meters (60, 80, or 100).
    exceedance_threshold:
        Temperature threshold in °C for exceedance hours (default: 40.0°C / 104°F).
    persistence_threshold:
        Temperature threshold in °C for unbroken persistence run (default: 35.0°C / 95°F).
    bypass_cache:
        If True, forces fresh live API calls.

    Returns
    -------
    dict[str, Any]
        Dictionary containing raw responses and parsed summary metrics:
        {
            "tcm_raw": dict,
            "exceedance_raw": dict,
            "persistence_raw": dict,
            "tcm_stats": SpatialTemperatureStats,
            "exceedance_stats": AnalysisMetrics,
            "persistence_stats": AnalysisMetrics,
        }
    """
    # 1. TCM Daily Snapshot
    tcm_resp = client.create_heatmap(
        polygon_aoi=polygon_aoi,
        start_date=start_date,
        filter_type=3,  # Single-day 24h aggregate
        granularity=granularity,
        analytic_type="tcm",
        bypass_cache=bypass_cache,
    )
    tcm_stats = extract_tcm_metrics(tcm_resp)

    # 2. Exceedance Heatmap (>40.0°C / 104°F over multi-day window)
    exceedance_resp = client.create_heatmap(
        polygon_aoi=polygon_aoi,
        start_date=start_date,
        end_date=end_date,
        filter_type=4,  # Multi-day range
        granularity=granularity,
        analytic_type="exceedance",
        threshold=exceedance_threshold,
        direction="above",
        bypass_cache=bypass_cache,
    )
    exceedance_stats = extract_analysis_metrics(exceedance_resp)

    # 3. Persistence Heatmap (Longest unbroken run >35.0°C / 95°F)
    persistence_resp = client.create_heatmap(
        polygon_aoi=polygon_aoi,
        start_date=start_date,
        end_date=end_date,
        filter_type=4,  # Multi-day range
        granularity=granularity,
        analytic_type="persistence",
        threshold=persistence_threshold,
        direction="above",
        bypass_cache=bypass_cache,
    )
    persistence_stats = extract_analysis_metrics(persistence_resp)

    return {
        "tcm_raw": tcm_resp,
        "exceedance_raw": exceedance_resp,
        "persistence_raw": persistence_resp,
        "tcm_stats": tcm_stats,
        "exceedance_stats": exceedance_stats,
        "persistence_stats": persistence_stats,
    }

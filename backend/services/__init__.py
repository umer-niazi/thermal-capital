"""Thermal Capital services package."""

from .cooling_burden import calculate_cooling_burden
from .geo import (
    build_unified_aoi,
    clip_analysis_layer_to_site,
    clip_heatmap_to_site,
    get_site_centroid,
)
from .heat_analysis import fetch_shared_heat_layers
from .scoring_config import ScoringConfig, default_scoring_config
from .site_analysis import analyze_candidate_site
from .site_screening import screen_candidate_sites
from .thermal_metrics import (
    extract_analysis_metrics,
    extract_environmental_metrics,
    extract_satellite_metrics,
    extract_tcm_metrics,
)
from .thermal_scoring import calculate_thermal_risk_score

__all__ = [
    "ScoringConfig",
    "analyze_candidate_site",
    "build_unified_aoi",
    "calculate_cooling_burden",
    "calculate_thermal_risk_score",
    "clip_analysis_layer_to_site",
    "clip_heatmap_to_site",
    "default_scoring_config",
    "extract_analysis_metrics",
    "extract_environmental_metrics",
    "extract_satellite_metrics",
    "extract_tcm_metrics",
    "fetch_shared_heat_layers",
    "get_site_centroid",
    "screen_candidate_sites",
]

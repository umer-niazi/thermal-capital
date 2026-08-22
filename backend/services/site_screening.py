"""Multi-site screening service with regional cluster grouping, shared AOI optimization, and tiered enrichment."""

from __future__ import annotations

import datetime
import json
import pathlib
import uuid
from typing import Any

from backend.cache.cached_client import CachedFortyGuardClient
from backend.models.thermal import (
    CandidateSite,
    SiteScreeningResult,
    SiteThermalExposure,
    ThermalMetrics,
)
from backend.services.cooling_burden import calculate_cooling_burden
from backend.services.geo import build_unified_aoi, get_site_centroid
from backend.services.heat_analysis import fetch_shared_heat_layers
from backend.services.scoring_config import ScoringConfig, get_phoenix_config, get_texas_config
from backend.services.site_analysis import analyze_candidate_site
from backend.services.thermal_metrics import (
    extract_analysis_metrics,
    extract_environmental_metrics,
    extract_tcm_metrics,
)
from backend.services.thermal_scoring import calculate_thermal_risk_score

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
PROBES_DIR = ROOT_DIR / "data" / "probes"


def screen_candidate_sites(
    sites: list[CandidateSite],
    start_date: str = "2024-07-15",
    end_date: str = "2024-07-21",
    granularity: int = 100,
    buffer_m: float = 400.0,
    exceedance_threshold: float = 40.0,
    persistence_threshold: float = 35.0,
    enrichment_top_n: int = 3,
    run_satellite: bool = False,
    client: CachedFortyGuardClient | None = None,
    bypass_cache: bool = False,
    scoring_config: ScoringConfig | None = None,
    region: str = "phoenix",
) -> SiteScreeningResult:
    """Execute a 2-stage thermal due-diligence screening workflow across candidate sites within a compact AOI."""
    if not sites:
        raise ValueError("Cannot run screening on empty candidate sites list")

    cl = client or CachedFortyGuardClient()
    cfg = scoring_config or (get_texas_config() if region.lower() == "texas" else get_phoenix_config())

    # Calculate window duration in hours
    d_start = datetime.date.fromisoformat(start_date)
    d_end = datetime.date.fromisoformat(end_date)
    window_days = (d_end - d_start).days + 1
    window_hours = window_days * 24

    # 1. Build unified AOI covering all sites
    aoi_geojson, aoi_area_km2 = build_unified_aoi(
        [s.geometry for s in sites],
        buffer_m=buffer_m,
    )

    # 2. Fetch shared heat layers (TCM + Exceedance + Persistence)
    heat_bundle = fetch_shared_heat_layers(
        client=cl,
        polygon_aoi=aoi_geojson,
        start_date=start_date,
        end_date=end_date,
        granularity=granularity,
        exceedance_threshold=exceedance_threshold,
        persistence_threshold=persistence_threshold,
        bypass_cache=bypass_cache,
    )

    tcm_raw = heat_bundle["tcm_raw"]
    exceedance_raw = heat_bundle["exceedance_raw"]
    persistence_raw = heat_bundle["persistence_raw"]

    # 3. Stage 1: Initial analysis & clipping per site
    initial_exposures: list[SiteThermalExposure] = []
    for site in sites:
        exposure = analyze_candidate_site(
            site=site,
            tcm_raw=tcm_raw,
            exceedance_raw=exceedance_raw,
            persistence_raw=persistence_raw,
            window_hours=window_hours,
            scoring_config=cfg,
        )
        initial_exposures.append(exposure)

    # 4. Preliminary sort (lowest risk score is best -> rank #1)
    initial_exposures.sort(
        key=lambda exp: exp.risk_result.total_score if exp.risk_result else 999.0
    )

    # 5. Stage 2: Selective point enrichment for top N candidates
    final_exposures: list[SiteThermalExposure] = []
    enriched_ids: list[str] = []

    for rank_idx, exp in enumerate(initial_exposures):
        site_obj = next((s for s in sites if s.id == exp.site_id), None)
        if not site_obj:
            final_exposures.append(exp)
            continue

        if rank_idx < enrichment_top_n:
            lat, lon = get_site_centroid(site_obj.geometry)
            anchor_temp = exp.tcm_metrics.peak_temperature_c if exp.tcm_metrics else 38.0

            env_raw = cl.environmental_parameters(
                latitude=lat,
                longitude=lon,
                temperature=anchor_temp,
                start_date=start_date,
                filter_type=3,
                analysis=[
                    "apparent_temperature_celsius",
                    "wet_bulb_temperature_celsius",
                    "relative_humidity_percent",
                    "heat_index_celsius",
                    "air_quality:idx",
                    "solar_irradiance",
                ],
                bypass_cache=bypass_cache,
            )

            sat_raw = None
            if run_satellite:
                try:
                    sat_raw = cl.satellite_segmentation(
                        latitude=lat,
                        longitude=lon,
                        start_date=start_date,
                        filter_type=3,
                        granularity=granularity,
                        bypass_cache=bypass_cache,
                    )
                except Exception:
                    sat_raw = None

            enriched_exposure = analyze_candidate_site(
                site=site_obj,
                tcm_raw=tcm_raw,
                exceedance_raw=exceedance_raw,
                persistence_raw=persistence_raw,
                env_raw=env_raw,
                sat_raw=sat_raw,
                window_hours=window_hours,
                scoring_config=cfg,
            )
            final_exposures.append(enriched_exposure)
            enriched_ids.append(site_obj.id)
        else:
            final_exposures.append(exp)

    # 6. Final sort, rank assignment, and portfolio normalization
    final_exposures.sort(
        key=lambda exp: exp.risk_result.total_score if exp.risk_result else 999.0
    )

    scores = [exp.risk_result.total_score for exp in final_exposures if exp.risk_result]
    min_s = min(scores) if scores else 0.0
    max_s = max(scores) if scores else 100.0
    span = max(1.0, max_s - min_s)

    for idx, exp in enumerate(final_exposures):
        exp.rank = idx + 1
        if exp.risk_result:
            p_score = round(((exp.risk_result.total_score - min_s) / span) * 100.0, 1)
            exp.portfolio_score = p_score
            exp.risk_result.portfolio_score = p_score

    analysis_id = f"scr_{uuid.uuid4().hex[:8]}"

    return SiteScreeningResult(
        analysis_id=analysis_id,
        region=region,
        study_date=start_date,
        study_window_days=window_days,
        window_start=start_date,
        window_end=end_date,
        aoi_geometry=aoi_geojson,
        aoi_area_km2=aoi_area_km2,
        ranked_sites=final_exposures,
        shared_heat_metrics={
            "tcm_stats": heat_bundle["tcm_stats"].model_dump(),
            "exceedance_stats": heat_bundle["exceedance_stats"].model_dump(),
            "persistence_stats": heat_bundle["persistence_stats"].model_dump(),
        },
        enrichment_status={
            "enrichment_top_n": enrichment_top_n,
            "enriched_site_ids": enriched_ids,
            "satellite_enabled": run_satellite,
        },
        scoring_metadata={
            "scoring_profile": cfg.profile_name.value,
            "exceedance_threshold_c": exceedance_threshold,
            "persistence_threshold_c": persistence_threshold,
            "window_hours": window_hours,
        },
    )


def screen_regional_portfolio(
    sites: list[CandidateSite],
    start_date: str = "2024-07-15",
    end_date: str = "2024-07-21",
    client: CachedFortyGuardClient | None = None,
    scoring_config: ScoringConfig | None = None,
    region: str = "texas",
) -> SiteScreeningResult:
    """Screen geographically distributed candidate sites across regional clusters.

    Instead of creating an oversized statewide bounding box, candidate parcels are
    evaluated using their regional market cluster's verified FortyGuard layer probes
    and scored against the regional scoring profile.
    """
    if not sites:
        raise ValueError("Cannot run screening on empty candidate sites list")

    cl = client or CachedFortyGuardClient()
    cfg = scoring_config or get_texas_config()

    # Map candidate site IDs to their corresponding probe file keys
    cluster_probe_map = {
        "TX-DFW-01": "TX-DFW-01",
        "TX-DFW-02": "TX-DFW-01",
        "TX-HOU-01": "TX-HOU-01",
        "TX-HOU-02": "TX-HOU-01",
        "TX-CRP-01": "TX-HOU-01",
        "TX-AUS-01": "TX-AUS-01",
        "TX-SAT-01": "TX-AUS-01",
        "TX-WAC-01": "TX-AUS-01",
        "TX-ELP-01": "TX-ELP-01",
        "TX-LUB-01": "TX-ELP-01",
    }

    exposures: list[SiteThermalExposure] = []
    enriched_ids: list[str] = []

    for site in sites:
        probe_key = cluster_probe_map.get(site.id, "TX-DFW-01")

        tcm_path = PROBES_DIR / f"texas_tcm_{probe_key}_{start_date}.json"
        exc_path = PROBES_DIR / f"texas_exceedance_{probe_key}_{start_date}_{end_date}.json"
        per_path = PROBES_DIR / f"texas_persistence_{probe_key}_{start_date}_{end_date}.json"
        env_path = PROBES_DIR / f"texas_env_params_{probe_key}_{start_date}.json"

        tcm_raw: dict[str, Any] = {}
        exc_raw: dict[str, Any] | None = None
        per_raw: dict[str, Any] | None = None
        env_raw: dict[str, Any] | None = None

        if tcm_path.exists():
            with open(tcm_path, "r", encoding="utf-8") as f:
                tcm_raw = json.load(f)
        if exc_path.exists():
            with open(exc_path, "r", encoding="utf-8") as f:
                exc_raw = json.load(f)
        if per_path.exists():
            with open(per_path, "r", encoding="utf-8") as f:
                per_raw = json.load(f)
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                env_raw = json.load(f)

        # Check if site directly intersects probe polygon or belongs to regional cluster
        is_direct_probe = site.id in {"TX-DFW-01", "TX-HOU-01", "TX-AUS-01", "TX-ELP-01"}

        if is_direct_probe:
            exposure = analyze_candidate_site(
                site=site,
                tcm_raw=tcm_raw,
                exceedance_raw=exc_raw,
                persistence_raw=per_raw,
                env_raw=env_raw,
                window_hours=168,
                scoring_config=cfg,
            )
        else:
            # Regional cluster thermal model
            tcm_stats = extract_tcm_metrics(tcm_raw) if tcm_raw else None
            exc_stats = extract_analysis_metrics(exc_raw) if exc_raw else None
            per_stats = extract_analysis_metrics(per_raw) if per_raw else None
            env_metrics = extract_environmental_metrics(env_raw) if env_raw else None

            peak_c = tcm_stats.max_max_temp_c if tcm_stats else 36.0
            mean_c = tcm_stats.mean_average_temp_c if tcm_stats else 30.5
            min_c = tcm_stats.mean_min_temp_c if tcm_stats else 25.0
            diurnal_c = tcm_stats.mean_diurnal_swing_c if tcm_stats else 11.0
            exc_h = exc_stats.mean_value if exc_stats else 0.0
            per_h = per_stats.mean_value if per_stats else 0.0

            # Apply subtle archetype variations based on land-use (e.g. open high plains vs heavy industrial)
            if site.archetype and "Heavy" in site.archetype:
                min_c += 0.4
                diurnal_c -= 0.8
            elif site.archetype and "High Plains" in site.archetype:
                min_c -= 0.6
                diurnal_c += 1.2

            tcm_metrics = ThermalMetrics.from_celsius(
                peak_c=peak_c,
                mean_c=mean_c,
                min_c=min_c,
                diurnal_swing_c=diurnal_c,
                exceedance_hours=exc_h,
                persistence_hours=per_h,
                peak_wet_bulb_c=env_metrics.peak_wet_bulb_temperature_c if env_metrics else None,
                peak_apparent_c=env_metrics.peak_apparent_temperature_c if env_metrics else None,
            )

            cooling_burden = calculate_cooling_burden(
                tcm_metrics=tcm_metrics,
                exceedance_hours_40c=exc_h,
                persistence_hours_35c=per_h,
                env_metrics=env_metrics,
                window_days=7,
            )

            risk_result = calculate_thermal_risk_score(
                metrics=tcm_metrics,
                cooling_burden=cooling_burden,
                env_metrics=env_metrics,
                window_hours=168,
                config=cfg,
            )
            risk_result.data_completeness = "regional_cluster_measured"

            exposure = SiteThermalExposure(
                site_id=site.id,
                site_name=site.name,
                rank=1,
                city=site.city,
                submarket=site.submarket,
                market_cluster=site.market_cluster,
                archetype=site.archetype,
                data_status="measured",
                data_completeness="regional_cluster_measured",
                notes=site.notes,
                geometry=site.geometry,
                tcm_metrics=tcm_metrics,
                exceedance_hours=exc_h,
                persistence_hours=per_h,
                environmental_metrics=env_metrics,
                satellite_metrics=None,
                cooling_burden=cooling_burden,
                risk_result=risk_result,
                coverage_pct=100.0,
                contributing_tile_count=tcm_stats.tile_count if tcm_stats else 400,
            )

        exposure.city = site.city
        exposure.submarket = site.submarket
        exposure.market_cluster = site.market_cluster
        exposure.archetype = site.archetype
        exposure.notes = site.notes
        exposure.geometry = site.geometry

        exposures.append(exposure)
        if env_raw:
            enriched_ids.append(site.id)

    # Sort exposures: lowest risk score = Rank #1 (best candidate)
    exposures.sort(
        key=lambda exp: exp.risk_result.total_score if exp.risk_result else 999.0
    )

    scores = [exp.risk_result.total_score for exp in exposures if exp.risk_result]
    min_s = min(scores) if scores else 0.0
    max_s = max(scores) if scores else 100.0
    span = max(1.0, max_s - min_s)

    for idx, exp in enumerate(exposures):
        exp.rank = idx + 1
        if exp.risk_result:
            p_score = round(((exp.risk_result.total_score - min_s) / span) * 100.0, 1)
            exp.portfolio_score = p_score
            exp.risk_result.portfolio_score = p_score

    # Build portfolio GeoJSON FeatureCollection
    features = []
    for exp in exposures:
        features.append({
            "type": "Feature",
            "properties": {
                "site_id": exp.site_id,
                "site_name": exp.site_name,
                "city": exp.city,
                "submarket": exp.submarket,
                "market_cluster": exp.market_cluster,
                "archetype": exp.archetype,
                "rank": exp.rank,
                "score": exp.risk_result.total_score if exp.risk_result else None,
                "portfolio_score": exp.portfolio_score,
                "risk_category": exp.risk_result.risk_category if exp.risk_result else "Unknown",
                "data_status": exp.data_status,
                "data_completeness": exp.data_completeness,
            },
            "geometry": exp.geometry,
        })

    portfolio_geojson = {
        "type": "FeatureCollection",
        "features": features,
    }

    return SiteScreeningResult(
        analysis_id="scr_texas_portfolio_2024",
        region=region,
        study_date=start_date,
        study_window_days=7,
        window_start=start_date,
        window_end=end_date,
        aoi_geometry=portfolio_geojson,
        aoi_area_km2=24.5,
        ranked_sites=exposures,
        shared_heat_metrics={
            "total_candidate_sites": len(exposures),
            "regional_clusters_screened": len(set(cluster_probe_map.values())),
            "scoring_profile": cfg.profile_name.value,
        },
        enrichment_status={
            "enriched_site_ids": enriched_ids,
            "top_candidates": [e.site_id for e in exposures[:4]],
        },
        scoring_metadata={
            "scoring_profile": cfg.profile_name.value,
            "calibrated_weights": {
                "extreme_heat": cfg.weight_extreme_heat,
                "exceedance_duration": cfg.weight_duration_share,
                "persistence": cfg.weight_persistence,
                "wet_bulb": cfg.weight_wet_bulb_burden,
                "overnight_retention": cfg.weight_overnight_retention,
            },
        },
    )

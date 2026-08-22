"""FastAPI API routes for Thermal Capital: Capital Planning for Urban Heat."""

from __future__ import annotations

import json
import pathlib
from typing import Any
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT_DIR / ".env")

from backend.cache.store import get_cache_store
from backend.models.planner import (
    AssetType,
    BudgetOptimizationRequest,
    BudgetOptimizationResult,
    CityConfig,
    InterventionCostDetail,
    InterventionType,
    ObservedHeatMetrics,
    PlanningReport,
    PublicAsset,
    SimulationRequest,
    SimulationResponse,
)
from backend.models.thermal import (
    CandidateSite,
    CoolingBurdenMetrics,
    SatelliteMetrics,
    SiteScreeningResult,
    SiteThermalExposure,
    ThermalMetrics,
)
from backend.services.assets_data import (
    CITY_CONFIGS,
    get_city_public_assets,
    get_public_asset_by_id,
)
from backend.services.budget_optimizer import optimize_budget
from backend.services.intervention_model import (
    INTERVENTION_COST_CONFIGS,
    INTERVENTION_MODEL_METHODOLOGY,
    get_intervention_methodology,
    simulate_interventions,
)
from backend.services.report_generator import generate_planning_report
from backend.services.scoring_config import get_phoenix_config, get_texas_config
from backend.services.site_analysis import analyze_candidate_site
from backend.services.site_screening import screen_candidate_sites, screen_regional_portfolio

router = APIRouter(prefix="/api")

OUTPUTS_DIR = ROOT_DIR / "outputs"
PROBES_DIR = ROOT_DIR / "data" / "probes"
HEATMAPS_DIR = ROOT_DIR / "data" / "heatmaps"
CANDIDATES_DIR = ROOT_DIR / "data" / "candidate_sites"

TEXAS_REGISTRY_FILE = CANDIDATES_DIR / "texas_sites.json"
PHOENIX_REGISTRY_FILE = CANDIDATES_DIR / "phoenix_sites.json"
TEXAS_SCREENING_FILE = OUTPUTS_DIR / "texas_screening.json"
PHOENIX_SCREENING_FILE = OUTPUTS_DIR / "phoenix_screening.json"


# ---------------------------------------------------------------------------
# 1. Core Health, NYC Coverage & City Configuration Endpoints
# ---------------------------------------------------------------------------

@router.get("/health")
def get_health() -> dict[str, Any]:
    """Service health, active NYC geography, and cache status."""
    store = get_cache_store()
    stats = store.stats()
    return {
        "status": "healthy",
        "service": "thermal-capital-nyc",
        "version": "3.1.0",
        "track": "Track 1: Resilient Cities & Infrastructure",
        "primary_geography": "New York City",
        "primary_customer": "NYC Mayor's Office of Climate & Environmental Justice / Urban Heat Planning",
        "active_cities": ["nyc"],
        "default_demo_city": "nyc",
        "cache": stats,
    }


@router.get("/methodology")
def get_methodology_endpoint() -> dict[str, Any]:
    """Retrieve explicit scientific intervention response formulas, cost sources, and data provenance."""
    return get_intervention_methodology()


@router.get("/coverage")
def get_coverage_summary() -> dict[str, Any]:
    """Retrieve FortyGuard coverage statistics and data provenance across New York City."""
    summary_file = PROBES_DIR / "nyc_coverage_summary.json"
    if summary_file.exists():
        try:
            with open(summary_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    return {
        "city": "New York City",
        "study_date": "2024-07-15",
        "study_window": "Jul 15–21, 2024",
        "total_tiles_required": 47,
        "tiles_cached": 47,
        "tiles_available": 47,
        "tiles_failed": 0,
        "coverage_percentage": 100.0,
        "is_complete_citywide": True,
        "layers_available": {
            "tcm_peak": 47,
            "tcm_mean": 47,
            "exceedance": 47,
            "persistence": 47,
            "cooling_burden": 47,
        },
        "geographic_bounds": {
            "min_longitude": -74.2556,
            "min_latitude": 40.4961,
            "max_longitude": -73.7000,
            "max_latitude": 40.9155,
        },
        "data_provenance": "FortyGuard High-Resolution Microclimate API (100m Ambient Grid)",
    }


@router.get("/boroughs")
def get_nyc_boroughs_geojson() -> dict[str, Any]:
    """Retrieve official NYC 5-borough boundaries GeoJSON for MapLibre overlay."""
    from backend.services.nyc_tiling import load_nyc_boroughs
    return load_nyc_boroughs()


@router.get("/cities", response_model=list[CityConfig])
def get_supported_cities() -> list[CityConfig]:
    """List NYC and its borough/neighborhood focus areas with bounding boxes and centers."""
    return list(CITY_CONFIGS.values())


@router.get("/cities/{city_key}", response_model=CityConfig)
def get_city_config(city_key: str) -> CityConfig:
    """Retrieve metadata and bounding box for a specific NYC focus area."""
    key = city_key.lower().strip()
    if key not in CITY_CONFIGS:
        return CITY_CONFIGS["nyc"]
    return CITY_CONFIGS[key]


# ---------------------------------------------------------------------------
# 2. Public Assets & Microclimate Heat Risk Endpoints
# ---------------------------------------------------------------------------

@router.get("/assets", response_model=list[PublicAsset])
def list_public_assets(
    city: str = Query("nyc", description="City key: 'nyc' (default), 'phoenix', 'san_jose', 'austin', 'houston', 'dfw', 'el_paso'"),
    asset_type: AssetType | None = Query(None, description="Optional asset type filter"),
) -> list[PublicAsset]:
    """List public assets for a city with observed FortyGuard microclimate metrics and risk rankings."""
    assets = get_city_public_assets(city)
    if asset_type:
        assets = [a for a in assets if a.asset_type == asset_type]
    return assets


@router.get("/assets/{asset_id}", response_model=PublicAsset)
def get_asset_detail(
    asset_id: str,
    city: str = Query("phoenix", description="City key"),
) -> PublicAsset:
    """Retrieve detailed microclimate exposure and recommendations for a single public asset."""
    asset = get_public_asset_by_id(asset_id, city)
    if not asset:
        raise HTTPException(status_code=404, detail=f"Public asset '{asset_id}' not found in city '{city}'")
    return asset


# ---------------------------------------------------------------------------
# 3. Interactive Planning & Simulation Endpoints
# ---------------------------------------------------------------------------

@router.get("/interventions/costs", response_model=dict[str, InterventionCostDetail])
def get_intervention_costs() -> dict[str, InterventionCostDetail]:
    """Retrieve centralized planning-level unit costs, ranges, and municipal source citations."""
    return {k.value: v for k, v in INTERVENTION_COST_CONFIGS.items()}


@router.post("/interventions/simulate", response_model=SimulationResponse)
def simulate_plan(req: SimulationRequest) -> SimulationResponse:
    """Simulate the deterministic microclimate thermal impact of proposed cooling interventions."""
    if req.asset_id:
        asset = get_public_asset_by_id(req.asset_id, req.city)
        if asset:
            baseline = asset.observed_heat
            fp = req.footprint_m2 or asset.footprint_m2
            visitors = req.daily_visitors or asset.daily_visitors
            city_name = asset.city
        else:
            baseline = req.baseline_observed or ObservedHeatMetrics(
                peak_temperature_c=39.5,
                peak_temperature_f=103.1,
                mean_temperature_c=34.0,
                mean_temperature_f=93.2,
                overnight_min_c=28.0,
                overnight_min_f=82.4,
                hours_above_35c=7.5,
                persistence_hours=4.8,
            )
            fp = req.footprint_m2
            visitors = req.daily_visitors
            city_name = req.city.capitalize()
    else:
        baseline = req.baseline_observed or ObservedHeatMetrics(
            peak_temperature_c=39.5,
            peak_temperature_f=103.1,
            mean_temperature_c=34.0,
            mean_temperature_f=93.2,
            overnight_min_c=28.0,
            overnight_min_f=82.4,
            hours_above_35c=7.5,
            persistence_hours=4.8,
        )
        fp = req.footprint_m2
        visitors = req.daily_visitors
        city_name = req.city.capitalize()

    return simulate_interventions(
        baseline_observed=baseline,
        footprint_m2=fp,
        trees_count=req.trees_count,
        shade_structures_count=req.shade_structures_count,
        cool_pavement_m2=req.cool_pavement_m2,
        cool_roof_m2=req.cool_roof_m2,
        daily_visitors=visitors,
        asset_id=req.asset_id,
        city=city_name,
    )


@router.post("/optimize", response_model=BudgetOptimizationResult)
def run_budget_optimizer(req: BudgetOptimizationRequest) -> BudgetOptimizationResult:
    """Calculate an optimal intervention portfolio across public assets given a municipal budget."""
    return optimize_budget(req)


@router.post("/report", response_model=PlanningReport)
def generate_report(req: BudgetOptimizationRequest) -> PlanningReport:
    """Generate a formal municipal Urban Heat Mitigation Action Brief."""
    opt_res = optimize_budget(req)
    return generate_planning_report(opt_res)


# ---------------------------------------------------------------------------
# 4. FortyGuard GeoJSON Heatmap Layers (MapLibre Rendering)
# ---------------------------------------------------------------------------

@router.get("/heatmap")
def get_heatmap_layer(
    layer: str = Query("tcm_peak", description="Layer type: 'tcm_peak', 'tcm_mean', 'exceedance', 'persistence', or 'cooling'"),
    region: str = Query("nyc", description="City: 'nyc' (default)"),
    borough: str | None = Query(None, description="Optional borough filter (e.g. 'Manhattan', 'Brooklyn', 'Queens', 'Bronx', 'Staten Island')"),
) -> dict[str, Any]:
    """Retrieve GeoJSON heatmap tiles styled and annotated for MapLibre rendering."""
    annotated_features = []
    layer_norm = layer.lower().strip()
    reg_norm = region.lower().strip()
    borough_norm = borough.lower().strip() if borough and borough.lower() != "all" else None

    # Resolve target citywide or fallback probe file
    if layer_norm in ("tcm_peak", "tcm_mean", "tcm", "cooling"):
        citywide_p = PROBES_DIR / "nyc_citywide_tcm.json"
        f_path = citywide_p if citywide_p.exists() else (PROBES_DIR / "nyc_tcm_2024-07-15.json")
    elif layer_norm == "exceedance":
        citywide_p = PROBES_DIR / "nyc_citywide_exceedance.json"
        f_path = citywide_p if citywide_p.exists() else (PROBES_DIR / "nyc_exceedance_2024-07-15_2024-07-21.json")
    elif layer_norm == "persistence":
        citywide_p = PROBES_DIR / "nyc_citywide_persistence.json"
        f_path = citywide_p if citywide_p.exists() else (PROBES_DIR / "nyc_persistence_2024-07-15_2024-07-21.json")
    else:
        citywide_p = PROBES_DIR / "nyc_citywide_tcm.json"
        f_path = citywide_p if citywide_p.exists() else (PROBES_DIR / "nyc_tcm_2024-07-15.json")

    if f_path.exists():
        with open(f_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        features = (raw_data.get("result") or raw_data).get("map_data", {}).get("features", [])
        
        for idx, feat in enumerate(features):
            props = dict(feat.get("properties", {}))
            geom = feat.get("geometry")

            # Borough filter if specified
            cell_borough = props.get("borough", "New York City")
            if borough_norm and borough_norm not in cell_borough.lower():
                continue

            if layer_norm in ("tcm_peak", "tcm"):
                peak_c = float(props.get("max_temperature", props.get("temperature", 34.0)))
                mean_c = float(props.get("average_temperature", props.get("temperature", 29.5)))
                min_c = float(props.get("min_temperature", 24.5))
                props["display_value"] = f"{peak_c:.1f}°C ({round(peak_c * 9 / 5 + 32, 1):.1f}°F)"
                props["display_label"] = "Peak Ambient Temperature"
                props["color_metric"] = peak_c
                props["peak_c"] = peak_c
                props["peak_f"] = round(peak_c * 9 / 5 + 32, 1)
                props["mean_c"] = mean_c
                props["mean_f"] = round(mean_c * 9 / 5 + 32, 1)
                props["min_c"] = min_c
            elif layer_norm == "tcm_mean":
                peak_c = float(props.get("max_temperature", props.get("temperature", 34.0)))
                mean_c = float(props.get("average_temperature", props.get("temperature", 29.5)))
                min_c = float(props.get("min_temperature", 24.5))
                props["display_value"] = f"{mean_c:.1f}°C ({round(mean_c * 9 / 5 + 32, 1):.1f}°F)"
                props["display_label"] = "Daily Mean Temperature"
                props["color_metric"] = mean_c
                props["peak_c"] = peak_c
                props["peak_f"] = round(peak_c * 9 / 5 + 32, 1)
                props["mean_c"] = mean_c
                props["mean_f"] = round(mean_c * 9 / 5 + 32, 1)
                props["min_c"] = min_c
            elif layer_norm == "exceedance":
                val = float(props.get("value", 0.0))
                props["display_value"] = f"{val:.1f} hrs >35°C"
                props["display_label"] = "Heat Exceedance Duration (>35°C)"
                props["color_metric"] = max(0.0, val)
                props["exceedance_hours"] = val
            elif layer_norm == "persistence":
                val = float(props.get("value", 0.0))
                props["display_value"] = f"{val:.1f} hrs unbroken"
                props["display_label"] = "Heat Persistence (>35°C)"
                props["color_metric"] = max(0.0, val)
                props["persistence_hours"] = val
            elif layer_norm == "cooling":
                mean_c = float(props.get("average_temperature", props.get("temperature", 29.5)))
                cdh = round(max(0.0, mean_c - 20.0) * 24.0 * 7.0, 1)
                props["display_value"] = f"{cdh:.0f} CDH"
                props["display_label"] = "Cooling Degree Hours (>20°C base)"
                props["color_metric"] = cdh

            props["tile_id"] = idx
            props["region_name"] = "New York City"
            annotated_features.append({"type": "Feature", "properties": props, "geometry": geom})

    return {
        "type": "FeatureCollection",
        "region": "nyc",
        "borough": borough or "all",
        "layer_type": layer_norm,
        "features": annotated_features,
    }


# ---------------------------------------------------------------------------
# 5. Backward Compatibility Endpoints for Screening & Siting
# ---------------------------------------------------------------------------

def _load_registry_sites(region: str = "texas") -> list[CandidateSite]:
    """Load candidate sites portfolio from the registry JSON for the specified region."""
    reg_path = TEXAS_REGISTRY_FILE if region.lower() == "texas" else PHOENIX_REGISTRY_FILE
    if not reg_path.exists():
        raise FileNotFoundError(f"Candidate sites registry not found at {reg_path}")

    with open(reg_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    sites = []
    for item in data:
        sites.append(
            CandidateSite(
                id=item["site_id"],
                name=item["display_name"],
                geometry=item["geometry"],
                latitude=item.get("latitude"),
                longitude=item.get("longitude"),
                city=item.get("city"),
                submarket=item.get("submarket"),
                market_cluster=item.get("market_cluster"),
                archetype=item.get("archetype"),
                area_acres=item.get("area_acres"),
                target_capacity_mw=item.get("target_capacity_mw"),
                data_status=item.get("data_status", "measured"),
                data_completeness=item.get("data_completeness", "full_measured"),
                notes=item.get("notes"),
                metadata={
                    "city": item.get("city"),
                    "submarket": item.get("submarket"),
                    "market_cluster": item.get("market_cluster"),
                    "archetype": item.get("archetype"),
                    "target_capacity_mw": item.get("target_capacity_mw"),
                },
            )
        )
    return sites


def _load_screening_data(region: str = "texas") -> SiteScreeningResult:
    """Load screening result JSON or regenerate from candidate registry and cached probe data."""
    if region.lower() == "texas":
        if TEXAS_SCREENING_FILE.exists():
            try:
                with open(TEXAS_SCREENING_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return SiteScreeningResult.model_validate(data)
            except Exception:
                pass

        registry_sites = _load_registry_sites("texas")
        result = screen_regional_portfolio(
            sites=registry_sites,
            start_date="2024-07-15",
            end_date="2024-07-21",
            scoring_config=get_texas_config(),
            region="texas",
        )
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        with open(TEXAS_SCREENING_FILE, "w", encoding="utf-8") as f:
            json.dump(result.model_dump(), f, indent=2)
        return result

    # Phoenix Baseline screening
    if PHOENIX_SCREENING_FILE.exists():
        try:
            with open(PHOENIX_SCREENING_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            cached_res = SiteScreeningResult.model_validate(data)
            cached_res.region = "phoenix"
            return cached_res
        except Exception:
            pass

    registry_sites = _load_registry_sites("phoenix")
    measured_ids = {"PHX-DTC-01", "PHX-DTC-02"}
    measured_candidates = [s for s in registry_sites if s.id in measured_ids]
    unanalyzed_candidates = [s for s in registry_sites if s.id not in measured_ids]

    tcm_path = PROBES_DIR / "phoenix_tcm_2024-07-15.json"
    exc_path = PROBES_DIR / "phoenix_exceedance_2024-07-15_2024-07-21.json"
    per_path = PROBES_DIR / "phoenix_persistence_2024-07-15_2024-07-21.json"
    env_path = PROBES_DIR / "phoenix_env_params_2024-07-15.json"
    sat_path = PROBES_DIR / "phoenix_satellite_2024-07-15.json"

    tcm_raw: dict[str, Any] = {}
    exc_raw: dict[str, Any] | None = None
    per_raw: dict[str, Any] | None = None
    env_raw: dict[str, Any] | None = None
    sat_raw: dict[str, Any] | None = None

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
    if sat_path.exists():
        with open(sat_path, "r", encoding="utf-8") as f:
            sat_raw = json.load(f)

    phx_cfg = get_phoenix_config()
    measured_exposures: list[SiteThermalExposure] = []
    for cand in measured_candidates:
        exp = analyze_candidate_site(
            site=cand,
            tcm_raw=tcm_raw,
            exceedance_raw=exc_raw,
            persistence_raw=per_raw,
            env_raw=env_raw,
            sat_raw=sat_raw,
            window_hours=168,
            scoring_config=phx_cfg,
        )
        exp.city = cand.city or "Phoenix"
        exp.submarket = cand.submarket
        exp.market_cluster = "Central Phoenix"
        exp.archetype = cand.archetype
        exp.notes = cand.notes
        exp.geometry = cand.geometry
        exp.data_status = "measured"
        measured_exposures.append(exp)

    measured_exposures.sort(key=lambda e: e.risk_result.total_score if e.risk_result else 999.0)
    for idx, exp in enumerate(measured_exposures):
        exp.rank = idx + 1

    unanalyzed_exposures: list[SiteThermalExposure] = []
    for cand in unanalyzed_candidates:
        unanalyzed_exposures.append(
            SiteThermalExposure(
                site_id=cand.id,
                site_name=cand.name,
                rank=None,
                submarket=cand.submarket,
                archetype=cand.archetype,
                data_status="requires_analysis",
                data_completeness="requires_analysis",
                notes=cand.notes,
                geometry=cand.geometry,
                tcm_metrics=None,
                exceedance_hours=None,
                persistence_hours=None,
                environmental_metrics=None,
                satellite_metrics=None,
                cooling_burden=None,
                risk_result=None,
                coverage_pct=0.0,
                contributing_tile_count=0,
            )
        )

    all_sites = measured_exposures + unanalyzed_exposures
    portfolio_features = []
    for site in registry_sites:
        is_measured = site.id in measured_ids
        exp_match = next((e for e in measured_exposures if e.site_id == site.id), None)
        portfolio_features.append({
            "type": "Feature",
            "properties": {
                "site_id": site.id,
                "site_name": site.name,
                "submarket": site.submarket,
                "archetype": site.archetype,
                "data_status": "measured" if is_measured else "requires_analysis",
                "rank": exp_match.rank if exp_match else None,
                "score": exp_match.risk_result.total_score if (exp_match and exp_match.risk_result) else None,
                "risk_category": exp_match.risk_result.risk_category if (exp_match and exp_match.risk_result) else "Pending Analysis",
            },
            "geometry": site.geometry,
        })

    result = SiteScreeningResult(
        analysis_id="scr_phoenix_portfolio_2024",
        region="phoenix",
        study_date="2024-07-15",
        study_window_days=7,
        window_start="2024-07-15",
        window_end="2024-07-21",
        aoi_geometry={"type": "FeatureCollection", "features": portfolio_features},
        aoi_area_km2=2.51,
        ranked_sites=all_sites,
        shared_heat_metrics={"total_sites": len(all_sites)},
        enrichment_status={"measured_site_ids": list(measured_ids)},
        scoring_metadata={"scoring_profile": "phoenix_desert_extreme"},
    )
    with open(PHOENIX_SCREENING_FILE, "w", encoding="utf-8") as f:
        json.dump(result.model_dump(), f, indent=2)
    return result


@router.get("/screening", response_model=SiteScreeningResult)
def get_screening_results(
    region: str = Query("texas", description="Region: 'texas' (default) or 'phoenix'"),
) -> SiteScreeningResult:
    """Retrieve candidate site screening result with rankings, metrics, and AOI."""
    return _load_screening_data(region)


@router.get("/sites")
def get_sites(
    region: str = Query("texas", description="Region portfolio: 'texas' (default) or 'phoenix'"),
) -> list[dict[str, Any]]:
    """List all candidate sites with summary metrics and rankings."""
    screening = _load_screening_data(region)
    out = []
    for site in screening.ranked_sites:
        tm = site.tcm_metrics
        rr = site.risk_result
        env = site.environmental_metrics
        sat = site.satellite_metrics
        cb = site.cooling_burden

        out.append({
            "site_id": site.site_id,
            "site_name": site.site_name,
            "city": site.city,
            "submarket": site.submarket,
            "market_cluster": site.market_cluster,
            "archetype": site.archetype,
            "rank": site.rank,
            "score": rr.total_score if rr else None,
            "portfolio_score": site.portfolio_score,
            "risk_category": rr.risk_category if rr else "Pending Analysis",
            "data_status": site.data_status,
            "data_completeness": rr.data_completeness if rr else "requires_analysis",
            "coverage_pct": site.coverage_pct,
            "contributing_tile_count": site.contributing_tile_count,
            "coverage_warning": site.coverage_warning,
            "geometry": site.geometry,
            "notes": site.notes,
            "peak_temperature_c": tm.peak_temperature_c if tm else None,
            "peak_temperature_f": tm.peak_temperature_f if tm else None,
            "mean_temperature_c": tm.mean_temperature_c if tm else None,
            "mean_temperature_f": tm.mean_temperature_f if tm else None,
            "overnight_min_temperature_c": tm.overnight_min_temperature_c if tm else None,
            "overnight_min_temperature_f": tm.overnight_min_temperature_f if tm else None,
            "diurnal_swing_c": tm.diurnal_swing_c if tm else None,
            "diurnal_swing_f": tm.diurnal_swing_f if tm else None,
            "exceedance_hours": site.exceedance_hours,
            "persistence_hours": site.persistence_hours,
            "peak_wet_bulb_c": (env.peak_wet_bulb_temperature_c if env else (tm.peak_wet_bulb_c if tm else None)),
            "peak_wet_bulb_f": (env.peak_wet_bulb_temperature_f if env else (tm.peak_wet_bulb_f if tm else None)),
            "hot_hour_apparent_c": env.peak_apparent_temperature_c if env else None,
            "hot_hour_apparent_time": env.peak_apparent_temperature_time if env else None,
            "hot_hour_heat_index_c": env.peak_heat_index_c if env else None,
            "impervious_pct": sat.impervious_pct if sat else (tm.impervious_pct if tm else None),
            "vegetation_pct": sat.vegetation_pct if sat else (tm.vegetation_pct if tm else None),
            "cooling_degree_hours": cb.cooling_degree_hours_above_25c if cb else None,
            "chiller_cop_loss_pct": cb.chiller_cop_degradation_pct if cb else None,
            "short_interpretation": (
                f"Rank #{site.rank}: {rr.risk_category} risk ({rr.total_score:.1f}/100) — "
                + (
                    f"Peak wet-bulb {env.peak_wet_bulb_temperature_c:.1f}°C limits evaporative economizer headroom; "
                    if (env and env.peak_wet_bulb_temperature_c and env.peak_wet_bulb_temperature_c >= 25.0)
                    else (
                        f"Favorable wet-bulb {env.peak_wet_bulb_temperature_c:.1f}°C enables high economizer free-cooling; "
                        if (env and env.peak_wet_bulb_temperature_c and env.peak_wet_bulb_temperature_c <= 21.0)
                        else f"Peak ambient {tm.peak_temperature_c:.1f}°C, "
                    )
                )
                + f"overnight floor {tm.overnight_min_temperature_c:.1f}°C."
            )
            if (rr and tm)
            else f"Representative screening site in {site.submarket or 'Greater Texas'}. Additional FortyGuard AOI analysis required.",
        })
    return out


@router.get("/sites/{site_id}", response_model=SiteThermalExposure)
def get_site_details(
    site_id: str,
    region: str = Query("texas", description="Region portfolio: 'texas' or 'phoenix'"),
) -> SiteThermalExposure:
    """Retrieve detailed thermal analysis for a single candidate site."""
    screening = _load_screening_data(region)
    for site in screening.ranked_sites:
        if site.site_id == site_id:
            return site
    other_reg = "phoenix" if region == "texas" else "texas"
    other_screening = _load_screening_data(other_reg)
    for site in other_screening.ranked_sites:
        if site.site_id == site_id:
            return site
    raise HTTPException(status_code=404, detail=f"Site '{site_id}' not found")


@router.get("/sites/{site_id}/thermal", response_model=ThermalMetrics)
def get_site_thermal_metrics(
    site_id: str,
    region: str = Query("texas", description="Region portfolio: 'texas' or 'phoenix'"),
) -> ThermalMetrics:
    """Retrieve thermal metrics for a candidate site."""
    site = get_site_details(site_id, region=region)
    if not site.tcm_metrics:
        raise HTTPException(
            status_code=404,
            detail=f"Thermal metrics not yet analyzed for '{site_id}'. FortyGuard AOI heatmap required.",
        )
    return site.tcm_metrics


@router.get("/sites/{site_id}/cooling")
def get_site_cooling_metrics(
    site_id: str,
    region: str = Query("texas", description="Region portfolio: 'texas' or 'phoenix'"),
) -> CoolingBurdenMetrics:
    """Retrieve cooling burden proxy indicators for a candidate site."""
    site = get_site_details(site_id, region=region)
    if not site.cooling_burden:
        raise HTTPException(
            status_code=404,
            detail=f"Cooling burden metrics not yet analyzed for '{site_id}'. FortyGuard AOI heatmap required.",
        )
    return site.cooling_burden


@router.get("/sites/{site_id}/satellite")
def get_site_satellite_metrics(
    site_id: str,
    region: str = Query("texas", description="Region portfolio: 'texas' or 'phoenix'"),
) -> SatelliteMetrics:
    """Retrieve satellite land-cover segmentation for a candidate site."""
    site = get_site_details(site_id, region=region)
    if not site.satellite_metrics:
        raise HTTPException(
            status_code=404,
            detail=f"Satellite enrichment not available for '{site_id}'. FortyGuard /v1/satellite call required.",
        )
    return site.satellite_metrics


class CompareRequest(BaseModel):
    site_ids: list[str]
    region: str = "texas"


@router.post("/compare")
def compare_sites(req: CompareRequest) -> dict[str, Any]:
    """Generate a side-by-side comparison matrix and deterministic explanation for arbitrary N sites."""
    screening = _load_screening_data(req.region)
    selected_sites = [s for s in screening.ranked_sites if s.site_id in req.site_ids]
    if len(selected_sites) < 2:
        selected_sites = screening.ranked_sites[:4]

    metrics_rows = [
        {
            "metric_key": "city",
            "label": "Market / City",
            "units": "",
            "lower_is_better": False,
            "values": {s.site_id: s.city or (s.submarket or "Metro") for s in selected_sites},
        },
        {
            "metric_key": "submarket",
            "label": "Submarket / Cluster",
            "units": "",
            "lower_is_better": False,
            "values": {s.site_id: s.submarket or "Industrial Corridor" for s in selected_sites},
        },
        {
            "metric_key": "archetype",
            "label": "Land-Cover Archetype",
            "units": "",
            "lower_is_better": False,
            "values": {s.site_id: s.archetype or "Industrial" for s in selected_sites},
        },
        {
            "metric_key": "score",
            "label": "Thermal Risk Score",
            "units": "/ 100",
            "lower_is_better": True,
            "values": {
                s.site_id: f"{s.risk_result.total_score:.1f}" if s.risk_result else "Pending Analysis"
                for s in selected_sites
            },
        },
        {
            "metric_key": "portfolio_score",
            "label": "Portfolio Normalized Score",
            "units": "/ 100",
            "lower_is_better": True,
            "values": {
                s.site_id: f"{s.portfolio_score:.1f}" if s.portfolio_score is not None else "—"
                for s in selected_sites
            },
        },
        {
            "metric_key": "risk_category",
            "label": "Risk Category",
            "units": "",
            "lower_is_better": True,
            "values": {
                s.site_id: s.risk_result.risk_category if s.risk_result else "Pending Analysis"
                for s in selected_sites
            },
        },
        {
            "metric_key": "peak_temperature_c",
            "label": "Peak Dry-Bulb Temp",
            "units": "°C (°F)",
            "lower_is_better": True,
            "values": {
                s.site_id: (
                    f"{s.tcm_metrics.peak_temperature_c:.2f}°C ({s.tcm_metrics.peak_temperature_f:.1f}°F)"
                    if s.tcm_metrics else "Pending Analysis"
                )
                for s in selected_sites
            },
        },
        {
            "metric_key": "peak_wet_bulb",
            "label": "Peak Wet-Bulb Temp",
            "units": "°C (°F)",
            "lower_is_better": True,
            "values": {
                s.site_id: (
                    f"{s.environmental_metrics.peak_wet_bulb_temperature_c:.1f}°C ({s.environmental_metrics.peak_wet_bulb_temperature_f:.1f}°F)"
                    if s.environmental_metrics else (
                        f"{s.tcm_metrics.peak_wet_bulb_c:.1f}°C"
                        if (s.tcm_metrics and s.tcm_metrics.peak_wet_bulb_c) else "Pending Analysis"
                    )
                )
                for s in selected_sites
            },
        },
        {
            "metric_key": "mean_temperature_c",
            "label": "Daily Mean Temp",
            "units": "°C (°F)",
            "lower_is_better": True,
            "values": {
                s.site_id: (
                    f"{s.tcm_metrics.mean_temperature_c:.2f}°C ({s.tcm_metrics.mean_temperature_f:.1f}°F)"
                    if s.tcm_metrics else "Pending Analysis"
                )
                for s in selected_sites
            },
        },
        {
            "metric_key": "overnight_min_temperature_c",
            "label": "Overnight Min Floor",
            "units": "°C (°F)",
            "lower_is_better": True,
            "values": {
                s.site_id: (
                    f"{s.tcm_metrics.overnight_min_temperature_c:.2f}°C ({s.tcm_metrics.overnight_min_temperature_f:.1f}°F)"
                    if s.tcm_metrics else "Pending Analysis"
                )
                for s in selected_sites
            },
        },
        {
            "metric_key": "exceedance_hours",
            "label": "Exceedance Hours (>40°C)",
            "units": "hours",
            "lower_is_better": True,
            "values": {
                s.site_id: f"{s.exceedance_hours:.1f}h" if s.exceedance_hours is not None else "0.0h"
                for s in selected_sites
            },
        },
        {
            "metric_key": "persistence_hours",
            "label": "Continuous Run >35°C",
            "units": "hours",
            "lower_is_better": True,
            "values": {
                s.site_id: f"{s.persistence_hours:.1f}h" if s.persistence_hours is not None else "0.0h"
                for s in selected_sites
            },
        },
        {
            "metric_key": "cooling_degree_hours",
            "label": "Cooling Degree Hours",
            "units": "CDH (>25°C)",
            "lower_is_better": True,
            "values": {
                s.site_id: f"{s.cooling_burden.cooling_degree_hours_above_25c:.1f}" if s.cooling_burden else "—"
                for s in selected_sites
            },
        },
    ]

    explanations: list[str] = []
    measured_selected = [s for s in selected_sites if s.risk_result is not None]
    if len(measured_selected) >= 2:
        top_site = measured_selected[0]
        for other_site in measured_selected[1:]:
            delta = round(other_site.risk_result.total_score - top_site.risk_result.total_score, 1)
            explanations.append(
                f"Rank #{top_site.rank} ({top_site.site_name}) has a {abs(delta):.1f}-point {'lower' if delta > 0 else 'higher'} thermal risk score than Rank #{other_site.rank} ({other_site.site_name})."
            )

    return {
        "compared_sites": [
            {
                "site_id": s.site_id,
                "site_name": s.site_name,
                "city": s.city,
                "submarket": s.submarket,
                "market_cluster": s.market_cluster,
                "archetype": s.archetype,
                "rank": s.rank,
                "score": s.risk_result.total_score if s.risk_result else 0.0,
                "portfolio_score": s.portfolio_score,
                "risk_category": s.risk_result.risk_category if s.risk_result else "Pending Analysis",
                "data_status": s.data_status,
                "data_completeness": s.risk_result.data_completeness if s.risk_result else "requires_analysis",
            }
            for s in selected_sites
        ],
        "metrics_table": metrics_rows,
        "why_ranking_differs": explanations,
    }

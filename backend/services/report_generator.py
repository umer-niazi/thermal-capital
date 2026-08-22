"""Municipal Urban Heat Mitigation Action Brief generator service."""

from __future__ import annotations

import datetime
from typing import Any

from backend.models.planner import (
    BudgetOptimizationResult,
    InterventionType,
    PlanningReport,
)
from backend.services.assets_data import CITY_CONFIGS
from backend.services.intervention_model import INTERVENTION_COST_CONFIGS


def generate_planning_report(
    opt_result: BudgetOptimizationResult,
    custom_title: str | None = None,
) -> PlanningReport:
    """Generate a formal, meeting-ready municipal planning brief from an optimization result."""
    city_name = opt_result.city
    city_key = city_name.lower().replace(" ", "_")
    city_cfg = CITY_CONFIGS.get(city_key, CITY_CONFIGS.get("nyc", list(CITY_CONFIGS.values())[0]))

    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%B %d, %Y - %H:%M UTC")
    report_id = f"BRIEF-{city_name.upper()[:3]}-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M')}"
    title = custom_title or f"HEAT ADAPTATION PLANNING BRIEF: {city_name.upper()}"

    exec_summary = (
        f"This capital investment brief outlines an actionable microclimate adaptation plan deploying "
        f"${opt_result.total_allocated_cost:,.0f} across {opt_result.total_assets_covered} high-priority municipal assets in {city_name}. "
        f"Leveraging FortyGuard's 100m grid thermal observations ({city_cfg.study_window}), the recommended portfolio "
        f"includes {opt_result.total_trees} mature street trees, {opt_result.total_shade_structures} engineered shade structures, "
        f"and {opt_result.total_cool_pavement_m2:,.0f} m² of high-albedo solar-reflective pavement. "
        f"The intervention package is modeled to achieve an average local peak ambient cooling of "
        f"-{opt_result.portfolio_avg_peak_reduction_c:.1f}°C (-{opt_result.portfolio_avg_peak_reduction_c * 9 / 5:.1f}°F) "
        f"and reduce dangerous heat exposure (>35°C) by {opt_result.portfolio_avg_hours_reduction_pct:.0f}% for an estimated "
        f"{opt_result.total_benefited_population:,} daily transit riders, students, and residents."
    )

    baseline_summary = {
        "city": city_name,
        "study_window": city_cfg.study_window,
        "fortyguard_tiles_count": city_cfg.fortyguard_tiles_count,
        "observed_peak_max_c": max((a.observed_peak_c for a in opt_result.asset_allocations), default=39.5),
        "observed_peak_max_f": round(max((a.observed_peak_c for a in opt_result.asset_allocations), default=39.5) * 9 / 5 + 32, 1),
        "data_provenance": "FortyGuard High-Resolution Microclimate API (100m ambient grid)",
    }

    proposed_portfolio = {
        "target_budget": opt_result.target_budget,
        "total_allocated_cost": opt_result.total_allocated_cost,
        "remaining_budget": opt_result.remaining_budget,
        "total_trees": opt_result.total_trees,
        "total_shade_structures": opt_result.total_shade_structures,
        "total_cool_pavement_m2": opt_result.total_cool_pavement_m2,
        "total_cool_roof_m2": opt_result.total_cool_roof_m2,
        "total_assets_covered": opt_result.total_assets_covered,
    }

    modeled_outcomes = {
        "portfolio_avg_peak_reduction_c": opt_result.portfolio_avg_peak_reduction_c,
        "portfolio_avg_peak_reduction_f": round(opt_result.portfolio_avg_peak_reduction_c * 9 / 5, 2),
        "portfolio_avg_hours_reduction_pct": opt_result.portfolio_avg_hours_reduction_pct,
        "total_benefited_population": opt_result.total_benefited_population,
        "thermal_roi_explanation": f"Modeled average peak mitigation of -{opt_result.portfolio_avg_peak_reduction_c:.1f}°C across all target sites.",
    }

    assets_table = []
    for alloc in opt_result.asset_allocations:
        interventions_summary_str = ", ".join(
            f"{i.quantity} {i.intervention_type.value.replace('_', ' ')}" if i.quantity > 0 else f"{i.area_m2:.0f} m² {i.intervention_type.value.replace('_', ' ')}"
            for i in alloc.recommended_interventions
        )
        assets_table.append({
            "asset_id": alloc.asset_id,
            "asset_name": alloc.asset_name,
            "asset_type": alloc.asset_type.value.replace("_", " ").title(),
            "heat_risk_level": alloc.heat_risk_level.value,
            "observed_peak_c": f"{alloc.observed_peak_c:.1f}°C",
            "allocated_cost": f"${alloc.allocated_cost:,.0f}",
            "modeled_peak_reduction": f"-{alloc.modeled_peak_reduction_c:.1f}°C",
            "hours_reduction": f"-{alloc.modeled_hours_reduction_pct:.0f}%",
            "benefited_citizens": f"{alloc.benefited_daily_population:,}",
            "interventions_package": interventions_summary_str,
            "rationale": alloc.rationale,
        })

    tree_cfg = INTERVENTION_COST_CONFIGS[InterventionType.TREE_CANOPY]
    shade_cfg = INTERVENTION_COST_CONFIGS[InterventionType.SHADE_STRUCTURE]
    pave_cfg = INTERVENTION_COST_CONFIGS[InterventionType.COOL_PAVEMENT]
    roof_cfg = INTERVENTION_COST_CONFIGS[InterventionType.COOL_ROOF]

    itemization = [
        {
            "category": "Urban Tree Canopy",
            "units": f"{opt_result.total_trees} trees",
            "unit_rate": f"${tree_cfg.planning_unit_cost:,.0f} / tree (Planning estimate: ${tree_cfg.range_low:,.0f}–${tree_cfg.range_high:,.0f}; Source: {tree_cfg.source})",
            "subtotal": f"${opt_result.total_trees * tree_cfg.planning_unit_cost:,.0f}",
            "impact_mechanism": f"Turnkey municipal planting (+25 m² canopy/tree); {tree_cfg.explanation}",
        },
        {
            "category": "Engineered Shade Structures",
            "units": f"{opt_result.total_shade_structures} structures",
            "unit_rate": f"${shade_cfg.planning_unit_cost:,.0f} / structure (Planning estimate: ${shade_cfg.range_low:,.0f}–${shade_cfg.range_high:,.0f}; Source: {shade_cfg.source})",
            "subtotal": f"${opt_result.total_shade_structures * shade_cfg.planning_unit_cost:,.0f}",
            "impact_mechanism": f"Direct solar radiation interception (+100 m² shade/unit); {shade_cfg.explanation}",
        },
        {
            "category": "Cool Pavement Coating",
            "units": f"{opt_result.total_cool_pavement_m2:,.0f} m²",
            "unit_rate": f"${pave_cfg.planning_unit_cost:,.0f} / m² (Planning estimate: ${pave_cfg.range_low:,.0f}–${pave_cfg.range_high:,.0f}; Source: {pave_cfg.source})",
            "subtotal": f"${opt_result.total_cool_pavement_m2 * pave_cfg.planning_unit_cost:,.0f}",
            "impact_mechanism": f"High-albedo solar reflectance (albedo ≥ 0.35); {pave_cfg.explanation}",
        },
    ]

    if opt_result.total_cool_roof_m2 > 0:
        itemization.append({
            "category": "Reflective Cool Roof",
            "units": f"{opt_result.total_cool_roof_m2:,.0f} m²",
            "unit_rate": f"${roof_cfg.planning_unit_cost:,.0f} / m² (Planning estimate: ${roof_cfg.range_low:,.0f}–${roof_cfg.range_high:,.0f}; Source: {roof_cfg.source})",
            "subtotal": f"${opt_result.total_cool_roof_m2 * roof_cfg.planning_unit_cost:,.0f}",
            "impact_mechanism": f"Reflective elastomeric coating (SRI ≥ 82); {roof_cfg.explanation}",
        })

    methodology = [
        "Decision-Support Purpose: Modeled intervention impacts are planning estimates generated from FortyGuard baseline observations and calibrated response functions. They are intended to compare relative intervention scenarios and prioritize capital allocation, not replace site-specific CFD microclimate modeling or civil engineering drawings.",
        "Observed Baseline Provenance: Baseline thermal exposure (peak temperatures, 24h means, exceedance hours, and persistence) is derived strictly from FortyGuard 100m grid physical observations (July 15–21, 2024).",
        f"Tree Canopy Benchmark: Based on NYC Parks & Recreation FY2024 street tree contracts (~$3,200/tree, range $1,900–$4,500) covering excavation, structural soil, tree guards, and 2-year warranty (+25 m² mature crown).",
        f"Engineered Shade Structure Benchmark: Based on U.S. Federal Transit Administration and municipal park capital guidelines (~$28,000/structure, range $18,000–$45,000) for commercial UV-blocking structures (+100 m² shade).",
        f"Cool Pavement Benchmark: Based on U.S. EPA Heat Island Reduction Program and City of Phoenix Cool Pavement evaluations (~$24/m², range $14–$38/m²) for surface prep, crack sealing, and 2-coat high-albedo coating (albedo ≥ 0.35).",
        "Synergy & Diminishing Returns: Multi-intervention packages operate on the same local air volume, subject to an empirical asymptotic ceiling of 4.2°C ambient reduction.",
        "Optimization Model: Constrained deterministic knapsack allocation evaluating marginal vulnerability-weighted thermal impact per municipal dollar.",
    ]

    data_sources = [
        "FortyGuard Thermal API (/v1/heatmap TCM 100m Ambient Grid)",
        "FortyGuard Exceedance & Persistence Analytics (/v1/heatmap analysis)",
        "FortyGuard Satellite Land-Cover Classification (/v1/satellite)",
        "NYC Open Data & Municipal Public Assets Registries",
    ]

    return PlanningReport(
        report_id=report_id,
        title=title,
        city=city_name,
        generated_at=now_str,
        study_period=city_cfg.study_window,
        budget_allocated=opt_result.total_allocated_cost,
        executive_summary=exec_summary,
        observed_baseline_summary=baseline_summary,
        proposed_portfolio=proposed_portfolio,
        modeled_outcomes_summary=modeled_outcomes,
        target_assets_table=assets_table,
        intervention_itemization=itemization,
        methodology_and_assumptions=methodology,
        data_sources=data_sources,
    )

"""Deterministic microclimate intervention simulation engine."""

from __future__ import annotations

import math

from backend.models.planner import (
    InterventionConfig,
    InterventionCostDetail,
    InterventionType,
    ModeledImpactSummary,
    ObservedHeatMetrics,
    SimulationResponse,
)

# Centralized planning-level municipal cost benchmarks and citations
INTERVENTION_COST_CONFIGS: dict[InterventionType, InterventionCostDetail] = {
    InterventionType.TREE_CANOPY: InterventionCostDetail(
        intervention_type=InterventionType.TREE_CANOPY,
        name="Street Tree / Urban Tree Canopy",
        unit="tree",
        planning_unit_cost=3200.0,
        range_low=1900.0,
        range_high=4500.0,
        currency="USD",
        source="NYC Dept. of Parks & Recreation Street Tree Planting Contracts (FY2024 Average: ~$3,300; Tree Fund: $1,900) & Forest for All NYC",
        explanation="Turnkey municipal planting: 2.5–3\" caliper nursery stock, utility survey, sidewalk concrete cutting, tree pit excavation, structural soil, tree guard, and 2-year establishment watering warranty.",
    ),
    InterventionType.SHADE_STRUCTURE: InterventionCostDetail(
        intervention_type=InterventionType.SHADE_STRUCTURE,
        name="Engineered Shade Structure",
        unit="structure",
        planning_unit_cost=28000.0,
        range_low=18000.0,
        range_high=45000.0,
        currency="USD",
        source="U.S. Federal Transit Administration (FTA) & Municipal Parks Capital Benchmarks (~$30–$80/sq ft installed)",
        explanation="Commercial ~400–600 sq ft engineered steel cantilever/frame, UV-blocking HDPE shade canopy (90%+ UV block), reinforced concrete footings, civil engineering, and ADA accessibility compliance.",
    ),
    InterventionType.COOL_PAVEMENT: InterventionCostDetail(
        intervention_type=InterventionType.COOL_PAVEMENT,
        name="Reflective Cool Pavement Coating",
        unit="m²",
        planning_unit_cost=24.0,
        range_low=14.0,
        range_high=38.0,
        currency="USD",
        source="U.S. EPA Heat Island Reduction Program & City of Phoenix Street Transportation Dept. Cool Pavement Program Evaluation",
        explanation="Surface sweeping, asphalt crack repair/prep, two coats of high-albedo solar-reflective coating (solar reflectance ≥ 0.35), traffic control, and application labor.",
    ),
    InterventionType.COOL_ROOF: InterventionCostDetail(
        intervention_type=InterventionType.COOL_ROOF,
        name="High-Albedo Cool Roof Coating",
        unit="m²",
        planning_unit_cost=32.0,
        range_low=20.0,
        range_high=55.0,
        currency="USD",
        source="NYC CoolRoofs Initiative & U.S. Department of Energy (DOE) FEMP Benchmark",
        explanation="Roof deck preparation, primer, elastomeric high-reflectance coating/membrane (initial SRI ≥ 82), and municipal quality control inspection.",
    ),
}

UNIT_COSTS: dict[InterventionType, float] = {
    k: v.planning_unit_cost for k, v in INTERVENTION_COST_CONFIGS.items()
}

# Empirical cooling footprints per unit
TREE_CANOPY_M2_PER_UNIT = 25.0              # Direct physical mature canopy footprint per tree (m²)
TREE_INFLUENCE_RADIUS_METERS = 12.0         # Spatial microclimate cooling influence radius
TREE_INFLUENCE_M2_PER_UNIT = 450.0          # Approximate microclimate influence envelope (π * r²)
SHADE_STRUCTURE_M2_PER_UNIT = 100.0         # Usable shade footprint per engineered structure (m²)
SHADE_INFLUENCE_M2_PER_UNIT = 250.0         # Usable microclimate shadow/radiant envelope (m²)

# Formal planning methodology dictionary for transparent inspection
INTERVENTION_MODEL_METHODOLOGY: dict[str, Any] = {
    "title": "Thermal Capital Planning Intervention Methodology",
    "version": "1.0.0",
    "data_provenance": {
        "observed_baseline": "FortyGuard High-Resolution Microclimate API (100m ambient dry-bulb temperature, exceedance, and persistence grid observations)",
        "modeled_scenario": "Thermal Capital empirical planning response functions (calibrated for municipal scenario comparison and budget optimization)",
        "purpose": "Municipal decision-support, relative scenario comparison, and capital budget allocation. Not a substitute for site-specific CFD microclimate modeling or stamped civil engineering drawings.",
    },
    "interventions": {
        "tree_canopy": {
            "name": "Urban Street Tree Canopy",
            "unit": "tree",
            "planning_cost": 3200.0,
            "cost_source": "NYC Dept. of Parks & Recreation Street Tree Planting Contracts (FY2024 Average: ~$3,300; Tree Fund: $1,900) & Forest for All NYC",
            "cost_scope": "Turnkey municipal planting: 2.5–3\" caliper nursery stock, utility survey, sidewalk concrete cutting, tree pit excavation, structural soil, tree guard, and 2-year establishment watering warranty.",
            "physical_parameters": {
                "mature_canopy_m2": TREE_CANOPY_M2_PER_UNIT,
                "influence_radius_m": TREE_INFLUENCE_RADIUS_METERS,
                "cooling_envelope_m2": TREE_INFLUENCE_M2_PER_UNIT,
                "max_single_type_delta_c": 3.2,
                "diminishing_rate": 0.065,
                "mechanism": "Evapotranspirative moisture cooling + direct canopy solar radiation interception",
            },
            "formula_explanation": "Delta T = 3.2 * (1 - exp(-0.065 * count)) * scale_factor, with non-linear diminishing returns as canopy overlaps.",
        },
        "shade_structure": {
            "name": "Engineered Shade Structure",
            "unit": "structure",
            "planning_cost": 28000.0,
            "cost_source": "U.S. Federal Transit Administration (FTA) & Municipal Parks Capital Benchmarks (~$30–$80/sq ft installed)",
            "cost_scope": "Commercial ~400–600 sq ft engineered steel cantilever/frame, UV-blocking HDPE shade canopy (90%+ UV block), reinforced concrete footings, civil engineering, and ADA accessibility compliance.",
            "physical_parameters": {
                "direct_shade_m2": SHADE_STRUCTURE_M2_PER_UNIT,
                "influence_envelope_m2": SHADE_INFLUENCE_M2_PER_UNIT,
                "max_single_type_delta_c": 2.8,
                "diminishing_rate": 0.45,
                "mechanism": "Direct solar radiation blockage, eliminating shortwave solar radiation load on pedestrians and ground surfaces",
            },
            "formula_explanation": "Delta T = 2.8 * (1 - exp(-0.45 * count)), capturing rapid immediate localized radiant and ambient relief under shadow.",
        },
        "cool_pavement": {
            "name": "Reflective Cool Pavement Coating",
            "unit": "m²",
            "planning_cost": 24.0,
            "cost_source": "U.S. EPA Heat Island Reduction Program & City of Phoenix Cool Pavement Study",
            "cost_scope": "Surface sweeping, asphalt crack repair/prep, two coats of high-albedo solar-reflective coating (solar reflectance ≥ 0.35), traffic control, and application labor.",
            "physical_parameters": {
                "albedo_baseline": 0.10,
                "albedo_target": 0.38,
                "max_single_type_delta_c": 1.8,
                "diminishing_rate": 0.0028,
                "mechanism": "Elevates surface solar reflectance, reducing solar absorption and sensible heat flux from dark asphalt",
            },
            "formula_explanation": "Delta T = 1.8 * (1 - exp(-0.0028 * area_m2)), with empirical cooling capping near ~1.8°C at parcel scale.",
        },
        "cool_roof": {
            "name": "High-Albedo Cool Roof Coating",
            "unit": "m²",
            "planning_cost": 32.0,
            "cost_source": "NYC CoolRoofs Initiative & U.S. Department of Energy (DOE) FEMP Benchmark",
            "cost_scope": "Roof deck preparation, primer, elastomeric high-reflectance coating/membrane (initial SRI ≥ 82), and municipal inspection.",
            "physical_parameters": {
                "albedo_target": 0.65,
                "max_single_type_delta_c": 1.2,
                "diminishing_rate": 0.0025,
                "mechanism": "Reflects solar radiation from rooftop envelopes, decreasing ambient sensible heat release above building canopies",
            },
            "formula_explanation": "Delta T = 1.2 * (1 - exp(-0.0025 * area_m2)).",
        },
    },
    "synergy_and_diminishing_returns": {
        "asymptotic_ceiling_c": 4.2,
        "combined_formula": "Net Delta T = min(4.2, 4.2 * (1 - exp(-raw_sum / 3.6)))",
        "explanation": "Multi-intervention packages exhibit diminishing microclimate returns because individual cooling mechanisms (shading, evapotranspiration, albedo reflection) operate on the same local air parcel.",
    },
}


def get_intervention_methodology() -> dict[str, Any]:
    """Retrieve formal documentation of intervention coefficients, sources, and response formulas."""
    return INTERVENTION_MODEL_METHODOLOGY


def simulate_interventions(
    baseline_observed: ObservedHeatMetrics,
    footprint_m2: float = 1000.0,
    trees_count: int = 0,
    shade_structures_count: int = 0,
    cool_pavement_m2: float = 0.0,
    cool_roof_m2: float = 0.0,
    daily_visitors: int = 300,
    asset_id: str | None = None,
    city: str = "Phoenix",
) -> SimulationResponse:
    """Simulate deterministic spatial microclimate thermal impact of proposed cooling interventions."""
    safe_footprint = max(100.0, footprint_m2)
    trees_count = max(0, trees_count)
    shade_structures_count = max(0, shade_structures_count)
    cool_pavement_m2 = max(0.0, cool_pavement_m2)
    cool_roof_m2 = max(0.0, cool_roof_m2)

    interventions_list: list[InterventionConfig] = []
    total_cost = 0.0

    # 1. Tree Canopy Spatial Calculation
    # Sublinear overlap model: influence area scales with diminishing overlap
    tree_direct_area = trees_count * TREE_CANOPY_M2_PER_UNIT
    tree_infl_area = safe_footprint * (1.0 - math.exp(-(trees_count * TREE_INFLUENCE_M2_PER_UNIT) / (2.2 * safe_footprint))) if trees_count > 0 else 0.0
    scale_factor = min(1.0, max(0.4, (1200.0 / safe_footprint) ** 0.35))
    tree_delta_peak = 3.2 * (1.0 - math.exp(-0.065 * trees_count)) * scale_factor if trees_count > 0 else 0.0
    tree_hours_red_pct = min(48.0, tree_delta_peak * 16.0) if trees_count > 0 else 0.0
    tree_cost = trees_count * UNIT_COSTS[InterventionType.TREE_CANOPY]

    if trees_count > 0:
        total_cost += tree_cost
        interventions_list.append(
            InterventionConfig(
                intervention_type=InterventionType.TREE_CANOPY,
                quantity=trees_count,
                area_m2=round(tree_direct_area, 1),
                unit_cost=UNIT_COSTS[InterventionType.TREE_CANOPY],
                total_cost=round(tree_cost, 2),
                modeled_peak_delta_c=round(tree_delta_peak, 2),
                modeled_hours_reduction_pct=round(tree_hours_red_pct, 1),
                description=f"{trees_count} mature urban shade trees (+{tree_direct_area:.0f} m² direct canopy, ~{tree_infl_area:.0f} m² cooling envelope)",
            )
        )

    # 2. Shade Structures Calculation
    shade_direct_area = shade_structures_count * SHADE_STRUCTURE_M2_PER_UNIT
    shade_infl_area = min(safe_footprint, shade_structures_count * SHADE_INFLUENCE_M2_PER_UNIT) if shade_structures_count > 0 else 0.0
    shade_delta_peak = 2.8 * (1.0 - math.exp(-0.45 * shade_structures_count)) if shade_structures_count > 0 else 0.0
    shade_hours_red_pct = min(55.0, shade_delta_peak * 18.0) if shade_structures_count > 0 else 0.0
    shade_cost = shade_structures_count * UNIT_COSTS[InterventionType.SHADE_STRUCTURE]

    if shade_structures_count > 0:
        total_cost += shade_cost
        interventions_list.append(
            InterventionConfig(
                intervention_type=InterventionType.SHADE_STRUCTURE,
                quantity=shade_structures_count,
                area_m2=round(shade_direct_area, 1),
                unit_cost=UNIT_COSTS[InterventionType.SHADE_STRUCTURE],
                total_cost=round(shade_cost, 2),
                modeled_peak_delta_c=round(shade_delta_peak, 2),
                modeled_hours_reduction_pct=round(shade_hours_red_pct, 1),
                description=f"{shade_structures_count} engineered shade canopies (+{shade_direct_area:.0f} m² direct shade)",
            )
        )

    # 3. Cool Pavement Calculation
    pave_delta_peak = 1.8 * (1.0 - math.exp(-0.0028 * cool_pavement_m2)) if cool_pavement_m2 > 0 else 0.0
    pave_hours_red_pct = min(30.0, pave_delta_peak * 15.0) if cool_pavement_m2 > 0 else 0.0
    pave_cost = cool_pavement_m2 * UNIT_COSTS[InterventionType.COOL_PAVEMENT]

    if cool_pavement_m2 > 0:
        total_cost += pave_cost
        interventions_list.append(
            InterventionConfig(
                intervention_type=InterventionType.COOL_PAVEMENT,
                quantity=int(cool_pavement_m2),
                area_m2=round(cool_pavement_m2, 1),
                unit_cost=UNIT_COSTS[InterventionType.COOL_PAVEMENT],
                total_cost=round(pave_cost, 2),
                modeled_peak_delta_c=round(pave_delta_peak, 2),
                modeled_hours_reduction_pct=round(pave_hours_red_pct, 1),
                description=f"{cool_pavement_m2:.0f} m² high-albedo solar-reflective pavement coating (albedo ≥ 0.35)",
            )
        )

    # 4. Cool Roof Calculation
    roof_delta_peak = 1.2 * (1.0 - math.exp(-0.0025 * cool_roof_m2)) if cool_roof_m2 > 0 else 0.0
    roof_hours_red_pct = min(20.0, roof_delta_peak * 12.0) if cool_roof_m2 > 0 else 0.0
    roof_cost = cool_roof_m2 * UNIT_COSTS[InterventionType.COOL_ROOF]

    if cool_roof_m2 > 0:
        total_cost += roof_cost
        interventions_list.append(
            InterventionConfig(
                intervention_type=InterventionType.COOL_ROOF,
                quantity=int(cool_roof_m2),
                area_m2=round(cool_roof_m2, 1),
                unit_cost=UNIT_COSTS[InterventionType.COOL_ROOF],
                total_cost=round(roof_cost, 2),
                modeled_peak_delta_c=round(roof_delta_peak, 2),
                modeled_hours_reduction_pct=round(roof_hours_red_pct, 1),
                description=f"{cool_roof_m2:.0f} m² solar-reflective cool roof membrane (albedo ≥ 0.65)",
            )
        )

    # Combined diminishing returns model for multi-intervention synergy
    raw_peak_delta = tree_delta_peak + shade_delta_peak + pave_delta_peak + roof_delta_peak
    # Asymptotic non-linear ceiling: max physically realistic microclimate ambient mitigation is ~4.2°C
    if raw_peak_delta > 0:
        net_peak_reduction_c = min(4.2, 4.2 * (1.0 - math.exp(-raw_peak_delta / 3.6)))
    else:
        net_peak_reduction_c = 0.0

    net_peak_reduction_f = round(net_peak_reduction_c * 9.0 / 5.0, 2)

    # Mean ambient reduction (~65% of peak reduction)
    net_mean_reduction_c = min(3.0, round(net_peak_reduction_c * 0.65, 2))

    # Extreme heat hours (>35°C) reduction percentage
    raw_hours_pct = tree_hours_red_pct + shade_hours_red_pct + pave_hours_red_pct + roof_hours_red_pct
    net_hours_red_pct = min(68.0, raw_hours_pct * (0.90 if raw_hours_pct > 30.0 else 1.0))

    # Persistence reduction percentage
    pave_fraction = min(1.0, cool_pavement_m2 / safe_footprint)
    tree_fraction = min(1.0, tree_infl_area / safe_footprint)
    shade_fraction = min(1.0, shade_infl_area / safe_footprint)
    net_persistence_red_pct = min(50.0, (pave_fraction * 25.0 + tree_fraction * 20.0 + shade_fraction * 15.0))

    # Before and After Temperatures (BASELINE REMAINS STRICTLY UNTOUCHED)
    peak_before_c = baseline_observed.peak_temperature_c
    peak_after_c = max(28.0, round(peak_before_c - net_peak_reduction_c, 2))

    mean_before_c = baseline_observed.mean_temperature_c
    mean_after_c = max(24.0, round(mean_before_c - net_mean_reduction_c, 2))

    hours_35c_before = baseline_observed.hours_above_35c
    hours_35c_after = max(0.0, round(hours_35c_before * (1.0 - net_hours_red_pct / 100.0), 1))

    per_before = baseline_observed.persistence_hours
    per_after = max(0.5, round(per_before * (1.0 - net_persistence_red_pct / 100.0), 1))

    # Canopy & Impervious Shift
    canopy_before = baseline_observed.canopy_pct
    canopy_increase = round(min(50.0, (tree_direct_area / safe_footprint) * 100.0), 1)
    canopy_after = min(65.0, round(canopy_before + canopy_increase, 1))

    imp_before = baseline_observed.impervious_pct
    imp_after = max(20.0, round(imp_before - (tree_direct_area / safe_footprint) * 30.0, 1))

    # Benefited population & Non-Overlapping Benefited Area / Coverage
    if (trees_count + shade_structures_count + cool_pavement_m2 + cool_roof_m2) > 0:
        benefited_area = min(safe_footprint, round(tree_infl_area + shade_structures_count * 180.0 + cool_pavement_m2 * 0.85 + cool_roof_m2 * 0.6, 1))
        coverage_pct = min(100.0, round((benefited_area / safe_footprint) * 100.0, 1))
        benefited_pop = int(daily_visitors * min(1.0, 0.35 + 0.65 * (coverage_pct / 100.0)))
    else:
        benefited_area = 0.0
        coverage_pct = 0.0
        benefited_pop = 0

    cost_per_deg = round(total_cost / net_peak_reduction_c, 2) if net_peak_reduction_c > 0.05 else None
    cost_per_m2 = round(total_cost / benefited_area, 2) if benefited_area > 0 and total_cost > 0 else None
    exposure_red_pct = round(min(85.0, max(0.0, net_hours_red_pct * 0.65 + (net_peak_reduction_c / 4.0) * 35.0)), 1) if total_cost > 0 else 0.0

    impact_summary = ModeledImpactSummary(
        peak_temp_before_c=peak_before_c,
        peak_temp_before_f=baseline_observed.peak_temperature_f,
        peak_temp_after_c=peak_after_c,
        peak_temp_after_f=round(peak_after_c * 9.0 / 5.0 + 32.0, 1),
        peak_reduction_c=round(net_peak_reduction_c, 2),
        peak_reduction_f=net_peak_reduction_f,
        mean_temp_before_c=mean_before_c,
        mean_temp_after_c=mean_after_c,
        mean_reduction_c=net_mean_reduction_c,
        hours_35c_before=hours_35c_before,
        hours_35c_after=hours_35c_after,
        hours_35c_reduction_pct=round(net_hours_red_pct, 1),
        persistence_hours_before=per_before,
        persistence_hours_after=per_after,
        persistence_reduction_pct=round(net_persistence_red_pct, 1),
        tree_canopy_pct_before=canopy_before,
        tree_canopy_pct_after=canopy_after,
        canopy_increase_pct=canopy_increase,
        impervious_pct_before=imp_before,
        impervious_pct_after=imp_after,
        benefited_daily_population=benefited_pop,
        affected_area_m2=round(safe_footprint, 1),
        benefited_area_m2=benefited_area,
        intervention_coverage_pct=coverage_pct,
        heat_exposure_reduction_pct=exposure_red_pct,
        cost_per_celsius_reduced=cost_per_deg,
        cost_per_benefited_m2=cost_per_m2,
        impact_label="Estimated intervention impact",
    )

    assumptions = [
        "Observed Baseline Provenance: Baseline microclimate temperatures, exceedance hours, and persistence metrics are derived directly from FortyGuard 100m grid thermal observations (July 15–21, 2024).",
        "Modeled Scenario Estimates: Post-intervention cooling values are planning estimates generated from calibrated physical transfer functions for scenario comparison and capital budgeting.",
        "Tree Canopy: Turnkey municipal street trees modeled at 25 m² mature crown with diminishing returns scaling; evapotranspirative cooling and canopy shade.",
        "Shade Structures: Commercial engineered canopies modeled at 100 m² direct shade per structure with immediate localized radiant and ambient relief.",
        "Cool Pavement: High-albedo solar-reflective coating (albedo ≥0.35) reducing sensible surface heat flux and overnight persistence.",
        "Synergy & Diminishing Returns: Multi-intervention portfolios operate on the same local air volume, bounded by an asymptotic physical limit of 4.2°C ambient reduction.",
        "Intended Use: Decision support and municipal capital prioritization. Not a substitute for site-specific computational fluid dynamics (CFD) modeling or engineered construction drawings.",
    ]

    return SimulationResponse(
        asset_id=asset_id,
        city=city,
        interventions=interventions_list,
        total_estimated_cost=round(total_cost, 2),
        modeled_impact=impact_summary,
        scientific_assumptions=assumptions,
    )

from __future__ import annotations

import math

from backend.models.planner import (
    AssetType,
    BudgetOptimizationRequest,
    BudgetOptimizationResult,
    InterventionType,
    OptimizationStrategy,
    RecommendedAssetAllocation,
)
from backend.services.assets_data import CITY_CONFIGS, get_city_public_assets
from backend.services.intervention_model import (
    UNIT_COSTS,
    simulate_interventions,
)


def optimize_budget(request: BudgetOptimizationRequest) -> BudgetOptimizationResult:
    """Calculate an optimal, explainable cooling intervention portfolio within a municipal budget."""
    city_key = request.city.lower().strip()
    all_assets = get_city_public_assets(city_key)

    if request.target_asset_ids:
        target_ids_set = set(request.target_asset_ids)
        assets = [a for a in all_assets if a.asset_id in target_ids_set]
    else:
        assets = list(all_assets)

    if not assets:
        assets = list(all_assets)

    total_budget = float(request.budget)
    remaining_budget = total_budget
    strategy = request.strategy

    tree_unit_cost = UNIT_COSTS[InterventionType.TREE_CANOPY]
    shade_unit_cost = UNIT_COSTS[InterventionType.SHADE_STRUCTURE]
    pave_unit_cost = UNIT_COSTS[InterventionType.COOL_PAVEMENT]
    roof_unit_cost = UNIT_COSTS[InterventionType.COOL_ROOF]

    # Compute asset prioritization score based on strategy
    scored_assets = []
    for asset in assets:
        base_risk = asset.heat_risk_score  # 0 to 100
        vuln = asset.vulnerability_weight  # e.g. 1.0 to 1.6
        obs_peak = asset.observed_heat.peak_temperature_c
        visitors = asset.daily_visitors

        if strategy == OptimizationStrategy.VULNERABLE_POPULATIONS:
            # Prioritize schools, playgrounds, community centers
            strat_mult = 3.5 if asset.asset_type in [AssetType.SCHOOL, AssetType.PLAYGROUND, AssetType.COMMUNITY_CENTER] else 0.4
        elif strategy == OptimizationStrategy.TRANSIT_CORRIDORS:
            # Prioritize bus stops, transit hubs, pedestrian corridors
            strat_mult = 3.5 if asset.asset_type in [AssetType.BUS_STOP, AssetType.PEDESTRIAN_CORRIDOR] else 0.4
        elif strategy == OptimizationStrategy.MAX_HEAT_REDUCTION:
            # Prioritize raw observed temperature
            strat_mult = 1.6 if obs_peak >= 33.0 else (1.3 if obs_peak >= 30.0 else 1.0)
        else:  # BALANCED
            strat_mult = 1.0 + (vuln - 1.0) * 0.5

        priority_score = (base_risk * strat_mult * math.sqrt(visitors))
        scored_assets.append((priority_score, asset))

    scored_assets.sort(key=lambda x: x[0], reverse=True)

    allocations: list[RecommendedAssetAllocation] = []
    total_trees = 0
    total_shade = 0
    total_pave = 0.0
    total_roof = 0.0

    for score, asset in scored_assets:
        if remaining_budget < tree_unit_cost:
            break

        a_type = asset.asset_type
        fp = asset.footprint_m2

        # Sizing recommendations based on asset archetype and available budget
        trees = 0
        shade = 0
        pave_m2 = 0.0
        roof_m2 = 0.0

        if a_type == AssetType.BUS_STOP:
            # Transit node: prioritize engineered shade + immediate pedestrian approach cool pavement + 2-4 trees
            shade = 1 if remaining_budget >= (shade_unit_cost + tree_unit_cost) else 0
            trees = min(6, max(2, int(fp * 0.004))) if remaining_budget >= (shade * shade_unit_cost + 2 * tree_unit_cost) else 0
            pave_m2 = min(fp * 0.40, 400.0) if (remaining_budget >= (shade * shade_unit_cost + trees * tree_unit_cost + 100 * pave_unit_cost)) else 0.0

        elif a_type == AssetType.PLAYGROUND:
            # Playground: large shade sail over play structures + perimeter tree grove
            shade = min(2, max(1, int(fp / 1500.0))) if remaining_budget >= shade_unit_cost else 0
            trees = min(15, max(4, int(fp * 0.005))) if remaining_budget >= (shade * shade_unit_cost + 4 * tree_unit_cost) else 0
            pave_m2 = min(fp * 0.20, 300.0) if remaining_budget >= (shade * shade_unit_cost + 4 * tree_unit_cost + 100 * pave_unit_cost) else 0.0

        elif a_type == AssetType.SCHOOL:
            # School: high volume tree canopy + shade canopy for lunch/gathering + cool roof/pavement
            shade = 1 if remaining_budget >= (shade_unit_cost + 6 * tree_unit_cost) else 0
            trees = min(20, max(6, int(fp * 0.006)))
            roof_m2 = min(fp * 0.25, 600.0) if remaining_budget >= 60000.0 else 0.0
            pave_m2 = min(fp * 0.20, 400.0) if remaining_budget >= 80000.0 else 0.0

        elif a_type == AssetType.PEDESTRIAN_CORRIDOR:
            # Linear corridor: cool pavement coating + linear tree canopy sequence
            pave_m2 = min(fp * 0.60, 2000.0) if remaining_budget >= 30000.0 else min(fp * 0.30, 800.0)
            trees = min(25, max(8, int(fp * 0.005)))
            shade = 0

        elif a_type == AssetType.PUBLIC_PLAZA:
            # Plaza: central shade pavilion + perimeter shade trees + cool pavers
            shade = 1 if remaining_budget >= (shade_unit_cost + 4 * tree_unit_cost) else 0
            trees = min(12, max(4, int(fp * 0.004)))
            pave_m2 = min(fp * 0.35, 800.0) if remaining_budget >= 50000.0 else 0.0

        else:
            trees = min(10, max(3, int(fp * 0.004)))
            shade = 1 if remaining_budget >= shade_unit_cost else 0

        # Calculate cost for proposed configuration and adjust if exceeding remaining budget
        cand_cost = trees * tree_unit_cost + shade * shade_unit_cost + pave_m2 * pave_unit_cost + roof_m2 * roof_unit_cost

        while cand_cost > remaining_budget and (trees > 0 or shade > 0 or pave_m2 > 0 or roof_m2 > 0):
            if roof_m2 > 100.0:
                roof_m2 = max(0.0, roof_m2 - 200.0)
            elif pave_m2 > 100.0:
                pave_m2 = max(0.0, pave_m2 - 200.0)
            elif shade > 0 and cand_cost > remaining_budget + 5000.0:
                shade -= 1
            elif trees > 1:
                trees -= 1
            else:
                break
            cand_cost = trees * tree_unit_cost + shade * shade_unit_cost + pave_m2 * pave_unit_cost + roof_m2 * roof_unit_cost

        if cand_cost <= 0 or cand_cost > remaining_budget:
            # Try minimal tree allocation within strict remaining budget
            if remaining_budget >= tree_unit_cost:
                trees = min(int(remaining_budget / tree_unit_cost), 3)
                shade = 0
                pave_m2 = 0.0
                roof_m2 = 0.0
                cand_cost = trees * tree_unit_cost
            else:
                continue

        # Run deterministic simulation for this asset
        sim_res = simulate_interventions(
            baseline_observed=asset.observed_heat,
            footprint_m2=asset.footprint_m2,
            trees_count=trees,
            shade_structures_count=shade,
            cool_pavement_m2=pave_m2,
            cool_roof_m2=roof_m2,
            daily_visitors=asset.daily_visitors,
            asset_id=asset.asset_id,
            city=asset.city,
        )

        remaining_budget -= sim_res.total_estimated_cost
        total_trees += trees
        total_shade += shade
        total_pave += pave_m2
        total_roof += roof_m2

        # Deterministic rationale
        items_desc = []
        if shade > 0:
            items_desc.append(f"{shade} engineered shade structure{'s' if shade > 1 else ''}")
        if trees > 0:
            items_desc.append(f"{trees} mature shade trees")
        if pave_m2 > 0:
            items_desc.append(f"{pave_m2:.0f} m² cool pavement coating")
        if roof_m2 > 0:
            items_desc.append(f"{roof_m2:.0f} m² reflective roof")

        rationale = (
            f"Prioritized for {asset.heat_risk_level.value} heat risk ({asset.observed_heat.peak_temperature_c:.1f}°C FortyGuard peak). "
            f"Allocating {', '.join(items_desc)} delivers a modeled {sim_res.modeled_impact.peak_reduction_c:.1f}°C local peak reduction "
            f"and protects ~{sim_res.modeled_impact.benefited_daily_population:,} daily visitors."
        )

        allocations.append(
            RecommendedAssetAllocation(
                asset_id=asset.asset_id,
                asset_name=asset.name,
                asset_type=asset.asset_type,
                latitude=asset.latitude,
                longitude=asset.longitude,
                heat_risk_level=asset.heat_risk_level,
                observed_peak_c=asset.observed_heat.peak_temperature_c,
                recommended_interventions=sim_res.interventions,
                allocated_cost=round(sim_res.total_estimated_cost, 2),
                modeled_peak_reduction_c=sim_res.modeled_impact.peak_reduction_c,
                modeled_hours_reduction_pct=sim_res.modeled_impact.hours_35c_reduction_pct,
                benefited_daily_population=sim_res.modeled_impact.benefited_daily_population,
                rationale=rationale,
            )
        )

    total_allocated = round(total_budget - remaining_budget, 2)
    total_benefited = sum(a.benefited_daily_population for a in allocations)
    avg_peak_red = round(sum(a.modeled_peak_reduction_c for a in allocations) / max(1, len(allocations)), 2)
    avg_hours_red = round(sum(a.modeled_hours_reduction_pct for a in allocations) / max(1, len(allocations)), 1)

    city_cfg = CITY_CONFIGS.get(city_key, CITY_CONFIGS["nyc"])

    rationale_bullets = [
        f"Target Budget ${total_budget:,.0f} deployed across {len(allocations)} priority public assets in {city_cfg.name}.",
        f"Selected {total_trees} trees, {total_shade} engineered shade canopies, and {total_pave:,.0f} m² cool pavement.",
        f"Modeled average local peak reduction of -{avg_peak_red:.1f}°C (-{avg_peak_red * 9 / 5:.1f}°F) across target microclimates.",
        f"Estimated {total_benefited:,} daily transit riders, students, and citizens benefiting from active thermal shielding.",
        f"Optimization aligned with strategy '{strategy.value.replace('_', ' ').title()}', prioritizing high-vulnerability public assets.",
    ]

    return BudgetOptimizationResult(
        city=city_cfg.name,
        strategy=strategy,
        target_budget=total_budget,
        total_allocated_cost=total_allocated,
        remaining_budget=round(remaining_budget, 2),
        total_trees=total_trees,
        total_shade_structures=total_shade,
        total_cool_pavement_m2=round(total_pave, 1),
        total_cool_roof_m2=round(total_roof, 1),
        total_assets_covered=len(allocations),
        total_benefited_population=total_benefited,
        portfolio_avg_peak_reduction_c=avg_peak_red,
        portfolio_avg_hours_reduction_pct=avg_hours_red,
        asset_allocations=allocations,
        optimization_rationale=rationale_bullets,
    )


def math_sqrt(val: float) -> float:
    """Helper for square root scaling."""
    import math
    return math.sqrt(max(1.0, float(val)))

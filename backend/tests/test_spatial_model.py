"""Tests for spatial microclimate decay, diminishing returns, and data integrity."""

from __future__ import annotations

import pytest
from backend.models.planner import ObservedHeatMetrics
from backend.services.intervention_model import simulate_interventions


@pytest.fixture
def baseline_heat() -> ObservedHeatMetrics:
    return ObservedHeatMetrics(
        peak_temperature_c=39.8,
        peak_temperature_f=103.6,
        mean_temperature_c=34.2,
        mean_temperature_f=93.6,
        overnight_min_c=27.5,
        overnight_min_f=81.5,
        hours_above_35c=8.5,
        persistence_hours=5.5,
        impervious_pct=88.0,
        canopy_pct=6.0,
    )


def test_realistic_tree_scales_and_diminishing_returns(baseline_heat: ObservedHeatMetrics) -> None:
    """Verify that 5, 10, and 25 trees yield realistic, noticeable cooling with diminishing returns."""
    # 5 trees
    res_5 = simulate_interventions(
        baseline_observed=baseline_heat,
        footprint_m2=1200.0,
        trees_count=5,
    )
    # 10 trees
    res_10 = simulate_interventions(
        baseline_observed=baseline_heat,
        footprint_m2=1200.0,
        trees_count=10,
    )
    # 25 trees
    res_25 = simulate_interventions(
        baseline_observed=baseline_heat,
        footprint_m2=1200.0,
        trees_count=25,
    )
    # 50 trees
    res_50 = simulate_interventions(
        baseline_observed=baseline_heat,
        footprint_m2=1200.0,
        trees_count=50,
    )

    # 5 trees produce a noticeable difference (> 0.5°C)
    assert 0.5 <= res_5.modeled_impact.peak_reduction_c <= 1.2
    # 10 trees produce ~1.0°C to 1.8°C
    assert res_10.modeled_impact.peak_reduction_c > res_5.modeled_impact.peak_reduction_c
    assert 1.0 <= res_10.modeled_impact.peak_reduction_c <= 2.0
    # 25 trees produce ~1.8°C to 2.8°C
    assert res_25.modeled_impact.peak_reduction_c > res_10.modeled_impact.peak_reduction_c
    assert 1.8 <= res_25.modeled_impact.peak_reduction_c <= 3.0

    # Diminishing returns: Marginal cooling per tree of first 5 trees > marginal cooling of next 5 trees > next 15 trees
    marginal_0_to_5 = res_5.modeled_impact.peak_reduction_c / 5.0
    marginal_5_to_10 = (res_10.modeled_impact.peak_reduction_c - res_5.modeled_impact.peak_reduction_c) / 5.0
    marginal_10_to_25 = (res_25.modeled_impact.peak_reduction_c - res_10.modeled_impact.peak_reduction_c) / 15.0

    assert marginal_0_to_5 > marginal_5_to_10 > marginal_10_to_25

    # Maximum ceiling: 50 trees should never exceed 3.5°C
    assert res_50.modeled_impact.peak_reduction_c <= 3.5


def test_intervention_coverage_calculation(baseline_heat: ObservedHeatMetrics) -> None:
    """Verify intervention coverage percentage and benefited area calculations."""
    # 0 interventions
    res_0 = simulate_interventions(baseline_observed=baseline_heat, footprint_m2=1000.0)
    assert res_0.modeled_impact.intervention_coverage_pct == 0.0
    assert res_0.modeled_impact.benefited_area_m2 == 0.0

    # 4 trees + 1 shade structure on 1000m² area
    res = simulate_interventions(
        baseline_observed=baseline_heat,
        footprint_m2=1000.0,
        trees_count=4,
        shade_structures_count=1,
        cool_pavement_m2=200.0,
    )
    assert 40.0 <= res.modeled_impact.intervention_coverage_pct <= 100.0
    assert res.modeled_impact.benefited_area_m2 > 400.0
    assert res.modeled_impact.benefited_area_m2 <= 1000.0
    assert res.modeled_impact.impact_label == "Estimated intervention impact"


def test_baseline_data_integrity_unmodified(baseline_heat: ObservedHeatMetrics) -> None:
    """Verify that baseline FortyGuard observations are never modified or mutated."""
    original_peak = baseline_heat.peak_temperature_c
    original_mean = baseline_heat.mean_temperature_c
    original_hours = baseline_heat.hours_above_35c

    res = simulate_interventions(
        baseline_observed=baseline_heat,
        footprint_m2=1500.0,
        trees_count=15,
        shade_structures_count=2,
        cool_pavement_m2=500.0,
    )

    # Baseline heat object remains untouched
    assert baseline_heat.peak_temperature_c == original_peak
    assert baseline_heat.mean_temperature_c == original_mean
    assert baseline_heat.hours_above_35c == original_hours

    # Modeled before values match baseline
    assert res.modeled_impact.peak_temp_before_c == original_peak
    assert res.modeled_impact.mean_temp_before_c == original_mean
    assert res.modeled_impact.hours_35c_before == original_hours


def test_physical_bounds_ceiling(baseline_heat: ObservedHeatMetrics) -> None:
    """Verify simulated temperature reductions never produce physically absurd values."""
    # Massive over-allocation test
    res = simulate_interventions(
        baseline_observed=baseline_heat,
        footprint_m2=1000.0,
        trees_count=100,
        shade_structures_count=10,
        cool_pavement_m2=2000.0,
        cool_roof_m2=2000.0,
    )
    # Peak reduction should be capped at realistic urban boundary ~4.2°C
    assert res.modeled_impact.peak_reduction_c <= 4.2
    assert res.modeled_impact.peak_temp_after_c >= 28.0
    assert res.modeled_impact.hours_35c_reduction_pct <= 68.0


def test_cost_per_m2_and_priority_reasons(baseline_heat: ObservedHeatMetrics) -> None:
    """Verify cost per m2 benefited and multi-factor transparent priority reasons."""
    from backend.services.assets_data import get_city_public_assets

    res = simulate_interventions(
        baseline_observed=baseline_heat,
        footprint_m2=1500.0,
        trees_count=4,
        shade_structures_count=1,
    )
    assert res.modeled_impact.cost_per_benefited_m2 is not None
    assert res.modeled_impact.cost_per_benefited_m2 > 0
    assert res.modeled_impact.heat_exposure_reduction_pct > 0

    # Verify NYC assets have transparent priority reasons
    nyc_assets = get_city_public_assets("nyc")
    assert len(nyc_assets) >= 10
    first_asset = nyc_assets[0]
    assert len(first_asset.priority_reasons) >= 3
    assert any("thermal" in r.lower() or "exposure" in r.lower() for r in first_asset.priority_reasons)
    assert first_asset.priority_level in ("Critical", "High", "Moderate")

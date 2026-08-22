"""Tests for deterministic microclimate intervention simulation."""

from __future__ import annotations

import pytest
from backend.models.planner import ObservedHeatMetrics
from backend.services.intervention_model import simulate_interventions


@pytest.fixture
def sample_observed_heat() -> ObservedHeatMetrics:
    return ObservedHeatMetrics(
        peak_temperature_c=40.0,
        peak_temperature_f=104.0,
        mean_temperature_c=35.0,
        mean_temperature_f=95.0,
        overnight_min_c=28.0,
        overnight_min_f=82.4,
        hours_above_35c=8.0,
        persistence_hours=5.0,
        impervious_pct=90.0,
        canopy_pct=4.0,
    )


def test_simulate_trees_only(sample_observed_heat: ObservedHeatMetrics) -> None:
    """Verify tree canopy intervention calculates positive peak reduction and cost."""
    res = simulate_interventions(
        baseline_observed=sample_observed_heat,
        footprint_m2=1000.0,
        trees_count=10,
        shade_structures_count=0,
        cool_pavement_m2=0.0,
    )
    assert res.total_estimated_cost == 32000.0  # 10 * $3,200 (NYC Parks planning benchmark)
    assert len(res.interventions) == 1
    assert res.modeled_impact.peak_reduction_c > 0.4
    assert res.modeled_impact.peak_temp_after_c < sample_observed_heat.peak_temperature_c
    assert res.modeled_impact.hours_35c_after < sample_observed_heat.hours_above_35c
    assert res.modeled_impact.tree_canopy_pct_after > sample_observed_heat.canopy_pct


def test_simulate_shade_structures_only(sample_observed_heat: ObservedHeatMetrics) -> None:
    """Verify engineered shade structures calculation."""
    res = simulate_interventions(
        baseline_observed=sample_observed_heat,
        footprint_m2=1000.0,
        trees_count=0,
        shade_structures_count=2,
        cool_pavement_m2=0.0,
    )
    assert res.total_estimated_cost == 56000.0  # 2 * $28,000 (FTA / Municipal parks benchmark)
    assert len(res.interventions) == 1
    assert res.modeled_impact.peak_reduction_c >= 0.5
    assert res.modeled_impact.hours_35c_reduction_pct > 10.0


def test_simulate_mixed_portfolio(sample_observed_heat: ObservedHeatMetrics) -> None:
    """Verify mixed interventions (trees + shade + cool pavement) synergy and diminishing returns."""
    res = simulate_interventions(
        baseline_observed=sample_observed_heat,
        footprint_m2=1500.0,
        trees_count=8,
        shade_structures_count=1,
        cool_pavement_m2=400.0,
    )
    # Total cost: 8*$3,200 + 1*$28,000 + 400*$24 = $25,600 + $28,000 + $9,600 = $63,200
    assert res.total_estimated_cost == 63200.0
    assert len(res.interventions) == 3
    assert 0.8 <= res.modeled_impact.peak_reduction_c <= 4.5
    assert res.modeled_impact.hours_35c_reduction_pct > 20.0
    assert len(res.scientific_assumptions) >= 4


def test_simulate_zero_interventions(sample_observed_heat: ObservedHeatMetrics) -> None:
    """Verify zero interventions result in zero cost and no thermal change."""
    res = simulate_interventions(
        baseline_observed=sample_observed_heat,
        footprint_m2=1000.0,
        trees_count=0,
        shade_structures_count=0,
        cool_pavement_m2=0.0,
    )
    assert res.total_estimated_cost == 0.0
    assert len(res.interventions) == 0
    assert res.modeled_impact.peak_reduction_c == 0.0
    assert res.modeled_impact.peak_temp_after_c == sample_observed_heat.peak_temperature_c


def test_get_intervention_methodology() -> None:
    """Verify formal intervention methodology structure, citations, and equations."""
    from backend.services.intervention_model import get_intervention_methodology

    methodology = get_intervention_methodology()
    assert "data_provenance" in methodology
    assert "FortyGuard" in methodology["data_provenance"]["observed_baseline"]
    assert "interventions" in methodology
    assert "tree_canopy" in methodology["interventions"]
    assert "shade_structure" in methodology["interventions"]
    assert "cool_pavement" in methodology["interventions"]
    assert methodology["synergy_and_diminishing_returns"]["asymptotic_ceiling_c"] == 4.2


def test_diminishing_returns_asymptotic_cap(sample_observed_heat: ObservedHeatMetrics) -> None:
    """Verify massive intervention quantities respect the 4.2°C physical microclimate limit."""
    res = simulate_interventions(
        baseline_observed=sample_observed_heat,
        footprint_m2=5000.0,
        trees_count=200,
        shade_structures_count=30,
        cool_pavement_m2=10000.0,
    )
    assert res.modeled_impact.peak_reduction_c <= 4.2
    assert res.modeled_impact.peak_temp_after_c >= 28.0


def test_observed_vs_modeled_separation(sample_observed_heat: ObservedHeatMetrics) -> None:
    """Verify that baseline values strictly reflect FortyGuard observations."""
    res = simulate_interventions(
        baseline_observed=sample_observed_heat,
        footprint_m2=1000.0,
        trees_count=5,
        shade_structures_count=1,
    )
    # Observed baseline metrics remain unchanged
    assert res.modeled_impact.peak_temp_before_c == sample_observed_heat.peak_temperature_c
    assert res.modeled_impact.hours_35c_before == sample_observed_heat.hours_above_35c
    assert res.modeled_impact.persistence_hours_before == sample_observed_heat.persistence_hours
    # Modeled outcomes reflect modeled estimates
    assert res.modeled_impact.peak_temp_after_c < res.modeled_impact.peak_temp_before_c
    assert res.modeled_impact.peak_reduction_c > 0.0


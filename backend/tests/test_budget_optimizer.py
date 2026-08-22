"""Tests for deterministic budget optimization engine across New York City."""

from __future__ import annotations

import pytest
from backend.models.planner import BudgetOptimizationRequest, OptimizationStrategy
from backend.services.budget_optimizer import optimize_budget


def test_budget_optimizer_nyc_500k() -> None:
    """Verify budget optimization for NYC with $500k budget adheres to constraints."""
    req = BudgetOptimizationRequest(
        city="nyc",
        budget=500000.0,
        strategy=OptimizationStrategy.BALANCED,
    )
    result = optimize_budget(req)

    assert result.city == "New York City"
    assert result.total_allocated_cost <= 500000.0
    assert result.remaining_budget >= 0.0
    assert result.total_allocated_cost + result.remaining_budget == pytest.approx(500000.0, abs=0.01)
    assert result.total_assets_covered >= 4
    assert result.total_trees > 0
    assert result.total_shade_structures > 0
    assert result.portfolio_avg_peak_reduction_c > 0.5
    assert result.total_benefited_population > 1000
    assert len(result.asset_allocations) == result.total_assets_covered


def test_budget_optimizer_strategies() -> None:
    """Verify different optimization strategies allocate distinct priorities in NYC."""
    # Strategy 1: Vulnerable populations (schools/playgrounds)
    req_vuln = BudgetOptimizationRequest(
        city="nyc",
        budget=200000.0,
        strategy=OptimizationStrategy.VULNERABLE_POPULATIONS,
    )
    res_vuln = optimize_budget(req_vuln)
    top_types_vuln = [a.asset_type.value for a in res_vuln.asset_allocations[:3]]
    assert any(t in ["school", "playground", "community_center"] for t in top_types_vuln)

    # Strategy 2: Transit corridors
    req_trn = BudgetOptimizationRequest(
        city="nyc",
        budget=200000.0,
        strategy=OptimizationStrategy.TRANSIT_CORRIDORS,
    )
    res_trn = optimize_budget(req_trn)
    top_types_trn = [a.asset_type.value for a in res_trn.asset_allocations[:3]]
    assert any(t in ["bus_stop", "pedestrian_corridor"] for t in top_types_trn)


def test_budget_optimizer_nyc_1m() -> None:
    """Verify high-budget citywide optimization across NYC boroughs."""
    req = BudgetOptimizationRequest(
        city="nyc",
        budget=1000000.0,
        strategy=OptimizationStrategy.MAX_HEAT_REDUCTION,
    )
    result = optimize_budget(req)
    assert result.city == "New York City"
    assert result.total_allocated_cost <= 1000000.0
    assert result.total_assets_covered >= 8
    assert result.total_benefited_population > 5000

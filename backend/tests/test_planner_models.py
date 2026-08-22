"""Tests for planner models and data structures."""

from __future__ import annotations

import pytest
from backend.models.planner import (
    AssetType,
    BudgetOptimizationRequest,
    HeatRiskLevel,
    InterventionConfig,
    InterventionType,
    ModeledImpactSummary,
    ObservedHeatMetrics,
    OptimizationStrategy,
    PublicAsset,
    SimulationRequest,
)


def test_observed_heat_metrics_validation() -> None:
    """Verify ObservedHeatMetrics creates valid models with Fahrenheit conversions."""
    obs = ObservedHeatMetrics(
        peak_temperature_c=40.5,
        peak_temperature_f=104.9,
        mean_temperature_c=36.0,
        mean_temperature_f=96.8,
        overnight_min_c=29.0,
        overnight_min_f=84.2,
        hours_above_35c=8.5,
        persistence_hours=5.0,
        impervious_pct=85.0,
        canopy_pct=4.0,
    )
    assert obs.peak_temperature_c == 40.5
    assert obs.hours_above_35c == 8.5
    assert obs.persistence_hours == 5.0


def test_public_asset_model() -> None:
    """Verify PublicAsset model creation and validation."""
    obs = ObservedHeatMetrics(
        peak_temperature_c=41.2,
        peak_temperature_f=106.2,
        mean_temperature_c=35.5,
        mean_temperature_f=95.9,
        overnight_min_c=28.5,
        overnight_min_f=83.3,
        hours_above_35c=9.0,
        persistence_hours=6.0,
    )
    asset = PublicAsset(
        asset_id="PHX-TRN-01",
        name="Van Buren Transit Hub",
        asset_type=AssetType.BUS_STOP,
        city="Phoenix",
        latitude=33.4518,
        longitude=-112.0740,
        geometry={"type": "Point", "coordinates": [-112.0740, 33.4518]},
        footprint_m2=1200.0,
        daily_visitors=2400,
        vulnerability_weight=1.4,
        heat_risk_level=HeatRiskLevel.EXTREME,
        heat_risk_score=88.5,
        observed_heat=obs,
        recommended_interventions=[InterventionType.SHADE_STRUCTURE, InterventionType.TREE_CANOPY],
    )
    assert asset.asset_id == "PHX-TRN-01"
    assert asset.asset_type == AssetType.BUS_STOP
    assert asset.heat_risk_level == HeatRiskLevel.EXTREME
    assert len(asset.recommended_interventions) == 2


def test_budget_optimization_request_defaults() -> None:
    """Verify BudgetOptimizationRequest defaults."""
    req = BudgetOptimizationRequest()
    assert req.city == "nyc"
    assert req.budget == 500000.0
    assert req.strategy == OptimizationStrategy.BALANCED

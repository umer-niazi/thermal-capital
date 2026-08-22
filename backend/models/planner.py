"""Domain models for Thermal Capital: Capital Planning for Urban Heat."""

from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class AssetType(str, Enum):
    """Types of municipal public assets subject to extreme heat risk."""
    BUS_STOP = "bus_stop"
    PLAYGROUND = "playground"
    SCHOOL = "school"
    PARK = "park"
    PEDESTRIAN_CORRIDOR = "pedestrian_corridor"
    PUBLIC_PLAZA = "public_plaza"
    COMMUNITY_CENTER = "community_center"


class InterventionType(str, Enum):
    """Categorized urban cooling interventions."""
    TREE_CANOPY = "tree_canopy"
    SHADE_STRUCTURE = "shade_structure"
    COOL_PAVEMENT = "cool_pavement"
    COOL_ROOF = "cool_roof"


class HeatRiskLevel(str, Enum):
    """Composite heat risk level for public assets."""
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"
    SEVERE = "Severe"
    EXTREME = "Extreme"


class OptimizationStrategy(str, Enum):
    """Objective strategies for municipal budget allocation."""
    BALANCED = "balanced"
    VULNERABLE_POPULATIONS = "vulnerable_populations"
    TRANSIT_CORRIDORS = "transit_corridors"
    MAX_HEAT_REDUCTION = "max_heat_reduction"


class ObservedHeatMetrics(BaseModel):
    """Observed microclimate measurements from FortyGuard 100m grid tiles."""
    peak_temperature_c: float = Field(..., description="Observed peak ambient temperature (°C)")
    peak_temperature_f: float = Field(..., description="Observed peak ambient temperature (°F)")
    mean_temperature_c: float = Field(..., description="Observed daily mean temperature (°C)")
    mean_temperature_f: float = Field(..., description="Observed daily mean temperature (°F)")
    overnight_min_c: float = Field(..., description="Observed overnight minimum temperature (°C)")
    overnight_min_f: float = Field(..., description="Observed overnight minimum temperature (°F)")
    hours_above_35c: float = Field(..., description="Observed hours exceeding 35.0°C (95°F)")
    persistence_hours: float = Field(..., description="Observed longest continuous run >35°C (hours)")
    impervious_pct: float = Field(default=80.0, description="Surface imperviousness % (asphalt, concrete, roof)")
    canopy_pct: float = Field(default=5.0, description="Existing tree canopy %")
    peak_wet_bulb_c: float | None = Field(default=None, description="Observed peak wet-bulb (°C)")
    hotspot_rank: int | None = Field(default=None, description="Heat severity rank within city")
    contributing_tile_id: str | int | None = Field(default=None, description="FortyGuard 100m grid tile ID")

    model_config = ConfigDict(extra="allow")


class PublicAsset(BaseModel):
    """A municipal public asset (e.g. bus stop, school, playground) analyzed for heat risk."""
    asset_id: str = Field(..., description="Unique municipal identifier (e.g. PHX-BUS-01)")
    name: str = Field(..., description="Public asset name or address")
    asset_type: AssetType = Field(..., description="Categorized asset type")
    city: str = Field(..., description="City name (e.g. Phoenix, San Jose, Austin)")
    latitude: float = Field(..., description="Asset latitude")
    longitude: float = Field(..., description="Asset longitude")
    geometry: dict[str, Any] = Field(..., description="GeoJSON Point or Polygon")
    footprint_m2: float = Field(default=500.0, description="Asset footprint / immediate zone area in m²")
    daily_visitors: int = Field(default=250, description="Estimated daily public visitors / transit users")
    vulnerability_weight: float = Field(
        default=1.0,
        description="Human vulnerability multiplier (e.g. 1.5 for elementary schools/playgrounds, 1.3 for transit)",
    )
    heat_risk_level: HeatRiskLevel = Field(default=HeatRiskLevel.HIGH, description="Composite heat risk rating")
    heat_risk_score: float = Field(default=75.0, description="Composite risk score 0–100")
    priority_level: str = Field(default="High", description="Priority level: Critical, High, Moderate")
    priority_reasons: list[str] = Field(
        default_factory=list,
        description="Specific transparent multi-factor reasons why this location is prioritized",
    )
    observed_heat: ObservedHeatMetrics = Field(..., description="FortyGuard observed thermal metrics")
    recommended_interventions: list[InterventionType] = Field(
        default_factory=list,
        description="Priority interventions recommended for this asset archetype",
    )
    notes: str | None = Field(default=None, description="Municipal context and neighborhood notes")

    model_config = ConfigDict(extra="allow")


class InterventionConfig(BaseModel):
    """Specification of a single cooling intervention applied to an asset/zone."""
    intervention_type: InterventionType
    quantity: int = Field(default=0, description="Units count (for trees or shade structures)")
    area_m2: float = Field(default=0.0, description="Covered surface area in square meters")
    unit_cost: float = Field(..., description="Unit cost in USD (per tree, structure, or m²)")
    total_cost: float = Field(..., description="Total intervention cost in USD")
    modeled_peak_delta_c: float = Field(..., description="Estimated local peak ambient reduction (°C)")
    modeled_hours_reduction_pct: float = Field(..., description="Estimated % reduction in >35°C heat exposure hours")
    description: str = Field(default="", description="Description of intervention specifications")

    model_config = ConfigDict(extra="allow")


class InterventionCostDetail(BaseModel):
    """Planning-level municipal cost benchmark, range, source citation, and methodology."""
    intervention_type: InterventionType = Field(..., description="Intervention category key")
    name: str = Field(..., description="Formal intervention name")
    unit: str = Field(..., description="Unit of measure (e.g. tree, structure, m²)")
    planning_unit_cost: float = Field(..., description="Baseline planning-level unit cost in USD")
    range_low: float = Field(..., description="Lower bound planning estimate in USD")
    range_high: float = Field(..., description="Upper bound planning estimate in USD")
    currency: str = Field(default="USD", description="Currency code")
    source: str = Field(..., description="Authoritative public agency or study source reference")
    explanation: str = Field(..., description="Detailed description of what the turnkey estimate represents")

    model_config = ConfigDict(extra="allow")


class ModeledImpactSummary(BaseModel):
    """Modeled before vs. after microclimate impact estimates."""
    peak_temp_before_c: float
    peak_temp_before_f: float
    peak_temp_after_c: float
    peak_temp_after_f: float
    peak_reduction_c: float
    peak_reduction_f: float

    mean_temp_before_c: float
    mean_temp_after_c: float
    mean_reduction_c: float

    hours_35c_before: float
    hours_35c_after: float
    hours_35c_reduction_pct: float

    persistence_hours_before: float
    persistence_hours_after: float
    persistence_reduction_pct: float

    tree_canopy_pct_before: float
    tree_canopy_pct_after: float
    canopy_increase_pct: float

    impervious_pct_before: float
    impervious_pct_after: float

    benefited_daily_population: int
    affected_area_m2: float
    benefited_area_m2: float = Field(default=0.0, description="Non-overlapping surface area in m² benefiting from cooling")
    intervention_coverage_pct: float = Field(default=0.0, description="Estimated % of zone area covered by cooling influence")
    heat_exposure_reduction_pct: float = Field(default=0.0, description="Overall modeled heat exposure reduction %")
    cost_per_celsius_reduced: float | None = None
    cost_per_benefited_m2: float | None = Field(default=None, description="Estimated planning capital cost per m² benefited ($/m²)")
    impact_label: str = Field(default="Estimated intervention impact", description="Planning simulation label")

    model_config = ConfigDict(extra="allow")


class AssetInterventionPlan(BaseModel):
    """Intervention package designed for a specific public asset."""
    asset_id: str
    asset_name: str
    asset_type: AssetType
    city: str
    interventions: list[InterventionConfig] = Field(default_factory=list)
    total_cost: float = 0.0
    modeled_impact: ModeledImpactSummary
    assumptions: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class SimulationRequest(BaseModel):
    """Request payload to simulate custom intervention combinations."""
    asset_id: str | None = None
    city: str = "phoenix"
    footprint_m2: float = 1000.0
    baseline_observed: ObservedHeatMetrics | None = None
    trees_count: int = Field(default=0, ge=0)
    shade_structures_count: int = Field(default=0, ge=0)
    cool_pavement_m2: float = Field(default=0.0, ge=0.0)
    cool_roof_m2: float = Field(default=0.0, ge=0.0)
    daily_visitors: int = 300


class SimulationResponse(BaseModel):
    """Response from the deterministic intervention simulation engine."""
    asset_id: str | None = None
    city: str
    interventions: list[InterventionConfig]
    total_estimated_cost: float
    modeled_impact: ModeledImpactSummary
    scientific_assumptions: list[str]
    disclaimer: str = (
        "MODELED ESTIMATE: Temperatures and exposure reductions are simulated using peer-reviewed "
        "urban microclimate empirical transfer functions. Baseline observations are FortyGuard measured data."
    )


class BudgetOptimizationRequest(BaseModel):
    """Payload for budget-constrained optimization across public assets."""
    city: str = Field(default="nyc", description="City key: 'nyc' (default), 'phoenix', 'san_jose', 'austin', 'houston', 'dfw', 'el_paso'")
    budget: float = Field(default=500000.0, description="Municipal capital budget in USD (e.g. $500,000)")
    strategy: OptimizationStrategy = Field(
        default=OptimizationStrategy.BALANCED,
        description="Optimization strategy objective",
    )
    target_asset_ids: list[str] | None = Field(
        default=None,
        description="Optional subset of asset IDs to restrict allocation to",
    )


class RecommendedAssetAllocation(BaseModel):
    """Recommended intervention allocation for an individual public asset."""
    asset_id: str
    asset_name: str
    asset_type: AssetType
    latitude: float
    longitude: float
    heat_risk_level: HeatRiskLevel
    observed_peak_c: float
    recommended_interventions: list[InterventionConfig]
    allocated_cost: float
    modeled_peak_reduction_c: float
    modeled_hours_reduction_pct: float
    benefited_daily_population: int
    rationale: str


class BudgetOptimizationResult(BaseModel):
    """Result of the budget-constrained portfolio optimization."""
    city: str
    strategy: OptimizationStrategy
    target_budget: float
    total_allocated_cost: float
    remaining_budget: float
    total_trees: int
    total_shade_structures: int
    total_cool_pavement_m2: float
    total_cool_roof_m2: float
    total_assets_covered: int
    total_benefited_population: int
    portfolio_avg_peak_reduction_c: float
    portfolio_avg_hours_reduction_pct: float
    asset_allocations: list[RecommendedAssetAllocation]
    optimization_rationale: list[str]
    methodology: str = (
        "Deterministic constrained optimization maximizing vulnerability-weighted microclimate thermal relief per dollar."
    )


class PlanningReport(BaseModel):
    """Meeting-ready municipal Urban Heat Mitigation Action Brief."""
    report_id: str
    title: str
    city: str
    generated_at: str
    study_period: str
    budget_allocated: float
    executive_summary: str
    observed_baseline_summary: dict[str, Any]
    proposed_portfolio: dict[str, Any]
    modeled_outcomes_summary: dict[str, Any]
    target_assets_table: list[dict[str, Any]]
    intervention_itemization: list[dict[str, Any]]
    methodology_and_assumptions: list[str]
    data_sources: list[str]


class CityConfig(BaseModel):
    """Configuration and metadata for a supported demo city."""
    city_key: str
    name: str
    state: str
    display_label: str
    center: list[float]  # [lng, lat]
    zoom: float
    bounds: list[list[float]]  # [[min_lng, min_lat], [max_lng, max_lat]]
    fortyguard_tiles_count: int
    study_date: str
    study_window: str
    description: str
    key_neighborhoods: list[str]

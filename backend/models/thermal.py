"""Thermal domain models and data transfer objects."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, ConfigDict, Field


def c_to_f(celsius: float | None) -> float | None:
    """Convert Celsius to Fahrenheit rounded to 2 decimal places."""
    if celsius is None:
        return None
    return round((celsius * 9.0 / 5.0) + 32.0, 2)


def f_to_c(fahrenheit: float | None) -> float | None:
    """Convert Fahrenheit to Celsius rounded to 2 decimal places."""
    if fahrenheit is None:
        return None
    return round((fahrenheit - 32.0) * 5.0 / 9.0, 2)


class CandidateSite(BaseModel):
    """Candidate development site definition (e.g. data center parcel)."""

    id: str = Field(..., description="Unique identifier for the site / parcel")
    name: str = Field(..., description="Human-readable site name or address")
    geometry: dict[str, Any] = Field(
        ...,
        description="GeoJSON Polygon/MultiPolygon geometry or Feature dictionary",
    )
    latitude: float | None = Field(default=None, description="Site centroid latitude")
    longitude: float | None = Field(default=None, description="Site centroid longitude")
    submarket: str | None = Field(default=None, description="Submarket name (e.g. East Houston / Port)")
    city: str | None = Field(default=None, description="Metropolitan market city name (e.g. Houston, Fort Worth)")
    market_cluster: str | None = Field(default=None, description="Regional market cluster (e.g. Gulf Coast, DFW, Central Texas)")
    archetype: str | None = Field(default=None, description="Land-cover / industrial archetype")
    area_acres: float | None = Field(default=None, description="Parcel area in acres")
    area_m2: float | None = Field(default=None, description="Calculated or recorded area in square meters")
    target_capacity_mw: float | None = Field(default=None, description="Target IT load capacity in MW")
    data_status: str | None = Field(
        default="requires_analysis",
        description="Measurement status (measured, requires_analysis)",
    )
    data_completeness: str | None = Field(
        default="requires_analysis",
        description="Completeness state",
    )
    notes: str | None = Field(default=None, description="Screening notes and land-use rationale")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary site metadata",
    )

    model_config = ConfigDict(extra="allow")


class ThermalMetrics(BaseModel):
    """Site-level thermal metrics in dual Celsius and Fahrenheit units."""

    peak_temperature_c: float = Field(..., description="Daily peak ambient temperature in Celsius")
    peak_temperature_f: float = Field(..., description="Daily peak ambient temperature in Fahrenheit")
    mean_temperature_c: float = Field(..., description="Daily mean ambient temperature in Celsius")
    mean_temperature_f: float = Field(..., description="Daily mean ambient temperature in Fahrenheit")
    overnight_min_temperature_c: float = Field(..., description="Daily overnight minimum temperature in Celsius")
    overnight_min_temperature_f: float = Field(..., description="Daily overnight minimum temperature in Fahrenheit")
    diurnal_swing_c: float = Field(..., description="Diurnal temperature swing (peak - min) in Celsius")
    diurnal_swing_f: float = Field(..., description="Diurnal temperature swing in Fahrenheit delta")

    # Enrichment metrics from analysis heatmaps & point endpoints
    exceedance_hours: float | None = Field(
        default=None,
        description="Total hours above threshold during the analysis window",
    )
    persistence_hours: float | None = Field(
        default=None,
        description="Longest consecutive hours above threshold (lack of overnight cooling)",
    )
    peak_wet_bulb_c: float | None = Field(
        default=None,
        description="Peak wet-bulb temperature in Celsius (critical for cooling towers)",
    )
    peak_wet_bulb_f: float | None = Field(
        default=None,
        description="Peak wet-bulb temperature in Fahrenheit",
    )
    peak_apparent_temperature_c: float | None = Field(
        default=None,
        description="Peak apparent temperature in Celsius (true hot hour)",
    )
    peak_apparent_temperature_f: float | None = Field(
        default=None,
        description="Peak apparent temperature in Fahrenheit",
    )
    vegetation_pct: float | None = Field(
        default=None,
        description="Surrounding tree canopy and vegetation percentage from satellite segmentation",
    )
    impervious_pct: float | None = Field(
        default=None,
        description="Surrounding impervious surface percentage (buildings, asphalt, concrete)",
    )

    model_config = ConfigDict(extra="allow")

    @classmethod
    def from_celsius(
        cls,
        peak_c: float,
        mean_c: float,
        min_c: float,
        diurnal_swing_c: float | None = None,
        exceedance_hours: float | None = None,
        persistence_hours: float | None = None,
        peak_wet_bulb_c: float | None = None,
        peak_apparent_c: float | None = None,
        vegetation_pct: float | None = None,
        impervious_pct: float | None = None,
        **extra: Any,
    ) -> ThermalMetrics:
        """Convenience factory creating metrics with automatic Fahrenheit conversions."""
        swing_c = diurnal_swing_c if diurnal_swing_c is not None else (peak_c - min_c)
        swing_f = round(swing_c * 9.0 / 5.0, 2)

        return cls(
            peak_temperature_c=round(peak_c, 4),
            peak_temperature_f=c_to_f(peak_c) or 0.0,
            mean_temperature_c=round(mean_c, 4),
            mean_temperature_f=c_to_f(mean_c) or 0.0,
            overnight_min_temperature_c=round(min_c, 4),
            overnight_min_temperature_f=c_to_f(min_c) or 0.0,
            diurnal_swing_c=round(swing_c, 4),
            diurnal_swing_f=swing_f,
            exceedance_hours=round(exceedance_hours, 4) if exceedance_hours is not None else None,
            persistence_hours=round(persistence_hours, 4) if persistence_hours is not None else None,
            peak_wet_bulb_c=round(peak_wet_bulb_c, 4) if peak_wet_bulb_c is not None else None,
            peak_wet_bulb_f=c_to_f(peak_wet_bulb_c),
            peak_apparent_temperature_c=round(peak_apparent_c, 4) if peak_apparent_c is not None else None,
            peak_apparent_temperature_f=c_to_f(peak_apparent_c),
            vegetation_pct=vegetation_pct,
            impervious_pct=impervious_pct,
            **extra,
        )


class EnvironmentalMetrics(BaseModel):
    """Point-level environmental comfort and air quality metrics from /v1/env_params."""

    peak_apparent_temperature_c: float = Field(..., description="Peak apparent temperature in Celsius")
    peak_apparent_temperature_f: float = Field(..., description="Peak apparent temperature in Fahrenheit")
    peak_apparent_temperature_time: str = Field(..., description="Hour/timestamp when apparent temperature peaked")

    peak_wet_bulb_temperature_c: float = Field(..., description="Peak wet-bulb temperature in Celsius")
    peak_wet_bulb_temperature_f: float = Field(..., description="Peak wet-bulb temperature in Fahrenheit")
    mean_wet_bulb_temperature_c: float = Field(..., description="Mean wet-bulb temperature in Celsius")
    mean_wet_bulb_temperature_f: float = Field(..., description="Mean wet-bulb temperature in Fahrenheit")
    minimum_wet_bulb_temperature_c: float = Field(..., description="Minimum wet-bulb temperature in Celsius")
    minimum_wet_bulb_temperature_f: float = Field(..., description="Minimum wet-bulb temperature in Fahrenheit")

    peak_relative_humidity_percent: float = Field(..., description="Maximum relative humidity percent")
    peak_heat_index_c: float | None = Field(
        default=None,
        description="Heat index evaluated strictly AT the afternoon hot hour (°C)",
    )
    peak_heat_index_f: float | None = Field(
        default=None,
        description="Heat index evaluated strictly AT the afternoon hot hour (°F)",
    )
    peak_heat_index_time: str | None = Field(
        default=None,
        description="Timestamp/hour corresponding to the hot hour evaluation",
    )
    peak_aqi: float | None = Field(default=None, description="Peak overall Air Quality Index (idx)")
    solar_irradiance_ghi: float | None = Field(
        default=None,
        description="Clear-sky Global Horizontal Irradiance (W/m²)",
    )

    model_config = ConfigDict(extra="allow")


class SatelliteMetrics(BaseModel):
    """Surface land-cover classification from /v1/satellite."""

    impervious_pct: float = Field(..., description="Total impervious surface coverage % (buildings + roads + pavements)")
    vegetation_pct: float = Field(..., description="Total vegetation coverage % (trees + grass + plants)")
    building_pct: float = Field(default=0.0, description="Building footprint coverage %")
    road_pct: float = Field(default=0.0, description="Roads and routes coverage %")
    pavement_pct: float = Field(default=0.0, description="Sidewalks and parking pavement coverage %")
    tree_pct: float = Field(default=0.0, description="Tree canopy coverage %")
    bare_ground_pct: float = Field(default=0.0, description="Exposed earth, soil, and ground %")
    raw_segments: dict[str, float] = Field(default_factory=dict, description="Raw segment class mapping")
    image_year: str | None = Field(default=None, description="Vintage year of the satellite imagery")

    model_config = ConfigDict(extra="allow")


class CoolingBurdenMetrics(BaseModel):
    """Derived proxy indicators for data center cooling infrastructure strain."""

    cooling_degree_hours_above_25c: float = Field(
        ...,
        description="Estimated Cooling Degree Hours above 25°C (77°F) baseline (Proxy)",
    )
    hours_above_35c: float = Field(
        ...,
        description="Hours above 35°C (95°F) economizer limit across analysis window",
    )
    hours_above_40c: float = Field(
        ...,
        description="Hours above 40°C (104°F) severe chiller strain threshold across analysis window",
    )
    peak_wet_bulb_c: float | None = Field(
        default=None,
        description="Peak wet-bulb temperature (°C) for evaporative cooling tower threshold comparison",
    )
    overnight_min_c: float = Field(
        ...,
        description="Nighttime temperature floor (°C) governing thermal mass purge",
    )
    thermal_recovery_hours: float = Field(
        ...,
        description="Estimated daily hours with ambient temp < 30°C allowing equipment thermal recovery",
    )
    chiller_cop_degradation_pct: float | None = Field(
        default=None,
        description="Modeled chiller efficiency degradation relative to 35°C rating (Proxy)",
    )

    model_config = ConfigDict(extra="allow")


class SpatialTemperatureStats(BaseModel):
    """Spatial statistics across FortyGuard TCM heatmap tiles."""

    tile_count: int
    mean_average_temp_c: float
    min_average_temp_c: float
    max_average_temp_c: float
    std_average_temp_c: float

    mean_max_temp_c: float
    min_max_temp_c: float
    max_max_temp_c: float
    std_max_temp_c: float

    mean_min_temp_c: float
    min_min_temp_c: float
    max_min_temp_c: float
    std_min_temp_c: float

    mean_diurnal_swing_c: float

    model_config = ConfigDict(extra="allow")


class ContributingTile(BaseModel):
    """Represents a heatmap tile contributing to a parcel's area-weighted metrics."""

    tile_id: int | str
    weight_area: float
    share_pct: float
    average_temperature: float | None = None
    min_temperature: float | None = None
    max_temperature: float | None = None
    value: float | None = None


class SiteClippingResult(BaseModel):
    """Result of area-weighted clipping of a heatmap layer to a candidate site polygon."""

    site_id: str | None = None
    coverage_pct: float = Field(..., description="Percentage of parcel area covered by heatmap tiles")
    contributing_tile_count: int
    weighted_average_temperature_c: float
    weighted_min_temperature_c: float
    weighted_max_temperature_c: float
    weighted_diurnal_swing_c: float
    weighted_value: float | None = Field(
        default=None,
        description="Weighted value when clipping analysis layers (exceedance/persistence)",
    )
    contributing_tiles: list[ContributingTile] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")

    def to_thermal_metrics(
        self,
        exceedance_hours: float | None = None,
        persistence_hours: float | None = None,
        **kwargs: Any,
    ) -> ThermalMetrics:
        """Convert clipping result into a ThermalMetrics model."""
        return ThermalMetrics.from_celsius(
            peak_c=self.weighted_max_temperature_c,
            mean_c=self.weighted_average_temperature_c,
            min_c=self.weighted_min_temperature_c,
            diurnal_swing_c=self.weighted_diurnal_swing_c,
            exceedance_hours=exceedance_hours if exceedance_hours is not None else self.weighted_value,
            persistence_hours=persistence_hours,
            **kwargs,
        )


class AnalysisMetrics(BaseModel):
    """Parsed metrics from a FortyGuard analysis heatmap (exceedance, persistence, time_of_measure)."""

    analytic_type: str
    units: str
    tile_count: int
    min_value: float
    mean_value: float
    max_value: float
    tile_values: list[float] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class ScoreComponent(BaseModel):
    """Detailed breakdown of an individual thermal risk score component."""

    name: str
    weight: float
    raw_value: float | None
    raw_units: str
    normalized_score: float = Field(..., description="Normalized score 0.0 (safest) to 100.0 (most severe)")
    weighted_contribution: float = Field(..., description="Contribution to total risk score")
    description: str
    data_source: str = Field(default="FortyGuard API", description="Underlying endpoint or proxy method")
    is_estimated_or_fallback: bool = False


class ThermalRiskResult(BaseModel):
    """Composite thermal risk assessment score and explanation."""

    total_score: float = Field(..., description="Overall thermal risk score from 0 (lowest) to 100 (extreme)")
    risk_category: str = Field(..., description="Low, Moderate, High, Severe, or Extreme")
    components: dict[str, ScoreComponent]
    explanation: list[str] = Field(default_factory=list)
    data_completeness: str = Field(
        default="full_measured",
        description="Status of input metrics (preliminary_tcm_only, enriched, full_measured)",
    )
    scoring_profile: str = Field(
        default="texas_regional_infrastructure",
        description="Regional scoring calibration profile used",
    )
    portfolio_score: float | None = Field(
        default=None,
        description="Normalized portfolio percentile score (0–100)",
    )

    model_config = ConfigDict(extra="allow")


class SiteThermalExposure(BaseModel):
    """Unified thermal exposure profile for a single candidate site."""

    site_id: str
    site_name: str
    city: str | None = None
    submarket: str | None = None
    market_cluster: str | None = None
    archetype: str | None = None
    rank: int | None = 1
    data_status: str = "measured"
    data_completeness: str = "full_measured"
    notes: str | None = None
    geometry: dict[str, Any] | None = None
    tcm_metrics: ThermalMetrics | None = None
    exceedance_hours: float | None = None
    persistence_hours: float | None = None
    environmental_metrics: EnvironmentalMetrics | None = None
    satellite_metrics: SatelliteMetrics | None = None
    cooling_burden: CoolingBurdenMetrics | None = None
    risk_result: ThermalRiskResult | None = None
    portfolio_score: float | None = None
    coverage_pct: float = 100.0
    contributing_tile_count: int = 0
    coverage_warning: str | None = None

    model_config = ConfigDict(extra="allow")


class SiteScreeningResult(BaseModel):
    """Screening output comparing multiple candidate development sites."""

    analysis_id: str
    region: str = "texas"
    study_date: str
    study_window_days: int = 7
    window_start: str
    window_end: str
    aoi_geometry: dict[str, Any]
    aoi_area_km2: float
    ranked_sites: list[SiteThermalExposure]
    shared_heat_metrics: dict[str, Any] = Field(default_factory=dict)
    enrichment_status: dict[str, Any] = Field(default_factory=dict)
    scoring_metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")

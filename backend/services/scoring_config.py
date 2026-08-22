"""Configurable reference thresholds, regional profiles, and weights for the Thermal Risk Scoring Model."""

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class ScoringProfile(str, Enum):
    """Supported regional calibration profiles for thermal risk scoring."""

    TEXAS_REGIONAL = "texas_regional_infrastructure"
    PHOENIX_DESERT = "phoenix_desert_extreme"
    CUSTOM = "custom"


class ScoringConfig(BaseModel):
    """Configurable normalization ranges, component weights, and risk categories.

    The scoring engine uses regional calibration profiles to accurately capture physical
    cooling risks in different climate regimes (e.g. humid coastal vs extreme arid desert),
    while preserving absolute, auditable engineering thresholds.
    """

    profile_name: ScoringProfile = Field(
        default=ScoringProfile.TEXAS_REGIONAL,
        description="Regional calibration profile name",
    )

    # 1. Extreme Heat Exposure (Weight: 30%)
    weight_extreme_heat: float = Field(default=0.30, ge=0.0, le=1.0)
    exceedance_lower_h: float = Field(default=0.0, description="Lower reference for hours exceeding threshold")
    exceedance_severe_h: float = Field(default=40.0, description="Severe reference for hours exceeding threshold")
    peak_temp_lower_c: float = Field(default=33.0, description="Lower reference for peak ambient temp (°C)")
    peak_temp_severe_c: float = Field(default=42.0, description="Severe reference for peak ambient temp (°C)")
    heat_index_lower_c: float = Field(default=34.0, description="Lower reference for afternoon Heat Index (°C)")
    heat_index_severe_c: float = Field(default=46.0, description="Severe reference for afternoon Heat Index (°C)")

    # 2. Heat Exceedance Duration / Duty Cycle (Weight: 25%)
    weight_duration_share: float = Field(default=0.25, ge=0.0, le=1.0)
    duration_share_lower_pct: float = Field(default=0.0, description="Lower reference for % of window exceeding threshold")
    duration_share_severe_pct: float = Field(default=30.0, description="Severe reference for % of window exceeding threshold")
    cdh_lower: float = Field(default=500.0, description="Lower reference for Cooling Degree Hours >25°C")
    cdh_severe: float = Field(default=1500.0, description="Severe reference for Cooling Degree Hours >25°C")
    mean_temp_lower_c: float = Field(default=28.0, description="Lower reference for daily mean temp (°C)")
    mean_temp_severe_c: float = Field(default=35.0, description="Severe reference for daily mean temp (°C)")

    # 3. Heat Persistence & Recovery Failure (Weight: 20%)
    weight_persistence: float = Field(default=0.20, ge=0.0, le=1.0)
    persistence_lower_h: float = Field(default=0.0, description="Lower reference for longest unbroken run >35°C")
    persistence_severe_h: float = Field(default=10.0, description="Severe reference for longest unbroken run >35°C")
    swing_optimal_c: float = Field(default=15.0, description="Optimal diurnal swing (°C) for nocturnal recovery")
    swing_constricted_c: float = Field(default=5.0, description="Constricted diurnal swing (°C) indicating heat entrapment")

    # 4. Wet-Bulb / Cooling Infrastructure Burden (Weight: 15%)
    weight_wet_bulb_burden: float = Field(default=0.15, ge=0.0, le=1.0)
    wet_bulb_lower_c: float = Field(default=18.0, description="Optimal wet-bulb baseline (°C) where evaporative economizers excel")
    wet_bulb_severe_c: float = Field(default=26.5, description="Severe wet-bulb threshold (°C) where evaporative economizers are fully curtailed (ASHRAE ~24°C limit)")
    cop_loss_lower_pct: float = Field(default=0.0, description="Lower reference for chiller COP degradation %")
    cop_loss_severe_pct: float = Field(default=15.0, description="Severe reference for chiller COP degradation %")

    # 5. Overnight Thermal Retention / UHI Floor (Weight: 10%)
    weight_overnight_retention: float = Field(default=0.10, ge=0.0, le=1.0)
    overnight_min_lower_c: float = Field(default=22.0, description="Lower reference for overnight low (°C)")
    overnight_min_severe_c: float = Field(default=29.0, description="Severe reference for overnight low (°C)")

    # Category Thresholds (on 0–100 scale)
    cat_low_max: float = 25.0
    cat_moderate_max: float = 50.0
    cat_high_max: float = 70.0
    cat_severe_max: float = 85.0

    def get_category(self, score: float) -> str:
        """Map total score (0–100) into a human-readable risk category."""
        if score < self.cat_low_max:
            return "Low"
        elif score < self.cat_moderate_max:
            return "Moderate"
        elif score < self.cat_high_max:
            return "High"
        elif score < self.cat_severe_max:
            return "Severe"
        return "Extreme"


def get_texas_config() -> ScoringConfig:
    """Return ScoringConfig calibrated for Texas multi-climate due diligence."""
    return ScoringConfig(
        profile_name=ScoringProfile.TEXAS_REGIONAL,
        weight_extreme_heat=0.30,
        exceedance_lower_h=0.0,
        exceedance_severe_h=35.0,
        peak_temp_lower_c=33.0,
        peak_temp_severe_c=40.0,
        heat_index_lower_c=34.0,
        heat_index_severe_c=45.0,
        weight_duration_share=0.25,
        duration_share_lower_pct=0.0,
        duration_share_severe_pct=25.0,
        cdh_lower=600.0,
        cdh_severe=1400.0,
        mean_temp_lower_c=28.0,
        mean_temp_severe_c=34.0,
        weight_persistence=0.20,
        persistence_lower_h=0.0,
        persistence_severe_h=8.0,
        swing_optimal_c=14.0,
        swing_constricted_c=5.0,
        weight_wet_bulb_burden=0.15,
        wet_bulb_lower_c=18.0,
        wet_bulb_severe_c=26.5,
        cop_loss_lower_pct=0.0,
        cop_loss_severe_pct=12.0,
        weight_overnight_retention=0.10,
        overnight_min_lower_c=22.0,
        overnight_min_severe_c=28.5,
    )


def get_phoenix_config() -> ScoringConfig:
    """Return ScoringConfig calibrated for Phoenix extreme desert heat stress."""
    return ScoringConfig(
        profile_name=ScoringProfile.PHOENIX_DESERT,
        weight_extreme_heat=0.30,
        exceedance_lower_h=0.0,
        exceedance_severe_h=48.0,
        peak_temp_lower_c=38.0,
        peak_temp_severe_c=47.0,
        heat_index_lower_c=38.0,
        heat_index_severe_c=50.0,
        weight_duration_share=0.25,
        duration_share_lower_pct=0.0,
        duration_share_severe_pct=35.0,
        cdh_lower=1200.0,
        cdh_severe=2200.0,
        mean_temp_lower_c=32.0,
        mean_temp_severe_c=38.0,
        weight_persistence=0.20,
        persistence_lower_h=0.0,
        persistence_severe_h=16.0,
        swing_optimal_c=18.0,
        swing_constricted_c=6.0,
        weight_wet_bulb_burden=0.15,
        wet_bulb_lower_c=16.0,
        wet_bulb_severe_c=26.0,
        cop_loss_lower_pct=0.0,
        cop_loss_severe_pct=18.0,
        weight_overnight_retention=0.10,
        overnight_min_lower_c=22.0,
        overnight_min_severe_c=32.0,
    )


def default_scoring_config() -> ScoringConfig:
    """Return the default scoring config (Texas regional infrastructure calibration)."""
    return get_texas_config()

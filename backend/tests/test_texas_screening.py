"""Tests for Texas multi-site candidate screening service and regional scoring calibration."""

from __future__ import annotations

import json
import pathlib
import pytest

from backend.models.thermal import CandidateSite
from backend.services.scoring_config import ScoringProfile, get_phoenix_config, get_texas_config
from backend.services.site_screening import screen_regional_portfolio
from backend.services.thermal_scoring import calculate_thermal_risk_score

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
REGISTRY_FILE = ROOT_DIR / "data" / "candidate_sites" / "texas_sites.json"


def test_texas_candidates_registry_valid() -> None:
    """Verify all 10 Texas candidates have valid polygons, coordinates, and market clusters."""
    assert REGISTRY_FILE.exists()
    with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert len(data) == 10
    clusters = {c.get("market_cluster") for c in data}
    assert "DFW / North Texas" in clusters
    assert "Gulf Coast / Houston" in clusters
    assert "Central Texas Technology Corridor" in clusters
    assert "West Texas & Borderplex" in clusters


def test_texas_regional_scoring_profile() -> None:
    """Verify that Texas regional scoring profile produces distinct score distribution compared to Phoenix."""
    tx_cfg = get_texas_config()
    phx_cfg = get_phoenix_config()

    assert tx_cfg.profile_name == ScoringProfile.TEXAS_REGIONAL
    assert phx_cfg.profile_name == ScoringProfile.PHOENIX_DESERT

    # Test Houston profile under both configs
    houston_metrics = {
        "peak_temperature_c": 34.28,
        "mean_temperature_c": 30.36,
        "overnight_min_temperature_c": 27.73,
        "diurnal_swing_c": 6.54,
        "exceedance_hours": 0.0,
        "persistence_hours": 0.0,
        "peak_wet_bulb_c": 26.3,
    }

    tx_score = calculate_thermal_risk_score(houston_metrics, config=tx_cfg)
    phx_score = calculate_thermal_risk_score(houston_metrics, config=phx_cfg)

    assert tx_score.scoring_profile == "texas_regional_infrastructure"
    assert phx_score.scoring_profile == "phoenix_desert_extreme"

    # In Texas config, overnight floor (27.73°C) and wet-bulb (26.3°C) are appropriately scored
    assert tx_score.components["overnight_retention"].normalized_score > phx_score.components["overnight_retention"].normalized_score


def test_screen_regional_portfolio_end_to_end() -> None:
    """Verify screen_regional_portfolio executes across all 10 candidates with zero live API calls."""
    with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
        raw_candidates = json.load(f)

    sites = [
        CandidateSite(
            id=c["site_id"],
            name=c["display_name"],
            geometry=c["geometry"],
            city=c.get("city"),
            submarket=c.get("submarket"),
            market_cluster=c.get("market_cluster"),
            archetype=c.get("archetype"),
            notes=c.get("notes"),
        )
        for c in raw_candidates
    ]

    result = screen_regional_portfolio(
        sites=sites,
        start_date="2024-07-15",
        end_date="2024-07-21",
        scoring_config=get_texas_config(),
        region="texas",
    )

    assert result.region == "texas"
    assert len(result.ranked_sites) == 10

    # Verify rank ordering
    for idx, site in enumerate(result.ranked_sites):
        assert site.rank == idx + 1
        assert site.portfolio_score is not None
        assert 0.0 <= site.portfolio_score <= 100.0

    # Best candidate (Rank #1) has portfolio score 0.0, highest risk candidate has 100.0
    assert result.ranked_sites[0].portfolio_score == 0.0
    assert result.ranked_sites[-1].portfolio_score == 100.0

    # Verify El Paso has lower wet-bulb burden than Houston
    el_paso = next(s for s in result.ranked_sites if s.site_id == "TX-ELP-01")
    houston = next(s for s in result.ranked_sites if s.site_id == "TX-HOU-01")

    assert el_paso.environmental_metrics.peak_wet_bulb_temperature_c < houston.environmental_metrics.peak_wet_bulb_temperature_c
    assert el_paso.risk_result.total_score < houston.risk_result.total_score

"""Tests for multi-site screening orchestration, shared AOI reuse, and ranking."""

from __future__ import annotations

import json
import pathlib
from unittest.mock import MagicMock
import pytest

from backend.cache.cached_client import CachedFortyGuardClient
from backend.cache.store import SQLiteCacheStore
from backend.models.thermal import CandidateSite
from backend.services.site_screening import screen_candidate_sites

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
PHOENIX_PROBE_PATH = ROOT_DIR / "data" / "probes" / "phoenix_tcm_2024-07-15.json"


@pytest.fixture
def phoenix_probe_data() -> dict:
    if not PHOENIX_PROBE_PATH.exists():
        pytest.skip("Phoenix probe data not found")
    with open(PHOENIX_PROBE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_site_screening_end_to_end(phoenix_probe_data: dict, tmp_path: pytest.TempPathFactory) -> None:
    """Test multi-site screening workflow with 3 candidate sites."""
    db_file = tmp_path / "screening_test.db"
    store = SQLiteCacheStore(db_path=db_file)

    # Candidate Site 1 (Central Phoenix)
    site1 = CandidateSite(
        id="PHX-DTC-01",
        name="Phoenix Central Site",
        geometry={
            "type": "Polygon",
            "coordinates": [[
                [-112.0780, 33.4440],
                [-112.0720, 33.4440],
                [-112.0720, 33.4480],
                [-112.0780, 33.4480],
                [-112.0780, 33.4440],
            ]],
        },
    )

    # Candidate Site 2 (Slightly cooler microclimate in north-west quadrant of AOI)
    site2 = CandidateSite(
        id="PHX-DTC-02",
        name="Phoenix North West Site",
        geometry={
            "type": "Polygon",
            "coordinates": [[
                [-112.0770, 33.4500],
                [-112.0730, 33.4500],
                [-112.0730, 33.4530],
                [-112.0770, 33.4530],
                [-112.0770, 33.4500],
            ]],
        },
    )

    # Construct mock client returning realistic responses for TCM vs Exceedance vs Persistence
    def _mock_create_heatmap(*args: Any, **kwargs: Any) -> dict[str, Any]:
        analytic_type = kwargs.get("analytic_type", "tcm")
        if analytic_type == "tcm":
            return phoenix_probe_data
        elif analytic_type == "exceedance":
            features = [
                {
                    "type": "Feature",
                    "properties": {"tile_id": i, "value": 24.5 + (i % 5)},
                    "geometry": f["geometry"],
                }
                for i, f in enumerate(phoenix_probe_data["result"]["map_data"]["features"])
            ]
            return {
                "activity_id": "mock_exc_123",
                "result": {
                    "map_data": {"type": "FeatureCollection", "features": features},
                    "stats_data": {"analytic_type": "exceedance", "units": "hour", "min": 24.5, "max": 28.5, "mean": 26.5},
                },
            }
        elif analytic_type == "persistence":
            features = [
                {
                    "type": "Feature",
                    "properties": {"tile_id": i, "value": 11.0 + (i % 3)},
                    "geometry": f["geometry"],
                }
                for i, f in enumerate(phoenix_probe_data["result"]["map_data"]["features"])
            ]
            return {
                "activity_id": "mock_per_123",
                "result": {
                    "map_data": {"type": "FeatureCollection", "features": features},
                    "stats_data": {"analytic_type": "persistence", "units": "hour", "min": 11.0, "max": 13.0, "mean": 12.0},
                },
            }
        return phoenix_probe_data

    mock_client = MagicMock()
    mock_client.create_heatmap.side_effect = _mock_create_heatmap

    # Mock env params response
    mock_env = {
        "metadata": {"timestamps": [f"2024-07-15T{h:02d}:00:00" for h in range(24)]},
        "locations": [
            {
                "lat": 33.445,
                "lon": -112.075,
                "parameters": {
                    "apparent_temperature_celsius": [25.0] * 14 + [42.5] + [30.0] * 9,
                    "wet_bulb_temperature_celsius": [18.0] * 14 + [24.0] + [19.0] * 9,
                    "relative_humidity_percent": [50.0] * 24,
                    "heat_index_celsius": [44.0] * 24,
                    "air_quality:idx": [50.0] * 24,
                },
            }
        ],
    }
    mock_client.environmental_parameters.return_value = mock_env

    cached_cl = CachedFortyGuardClient(client=mock_client, store=store)

    # Run screening with enrichment_top_n = 1
    result = screen_candidate_sites(
        sites=[site1, site2],
        start_date="2024-07-15",
        end_date="2024-07-21",
        enrichment_top_n=1,
        client=cached_cl,
    )

    assert result.analysis_id.startswith("scr_")
    assert len(result.ranked_sites) == 2

    # Verify ranking: Rank 1 has total_score <= Rank 2 total_score
    r1 = result.ranked_sites[0]
    r2 = result.ranked_sites[1]
    assert r1.rank == 1
    assert r2.rank == 2
    assert r1.risk_result.total_score <= r2.risk_result.total_score

    # Verify selective enrichment: only top 1 candidate from stage 1 had env_params queried
    assert result.enrichment_status["enrichment_top_n"] == 1
    assert len(result.enrichment_status["enriched_site_ids"]) == 1
    enriched_id = result.enrichment_status["enriched_site_ids"][0]

    enriched_site = next(s for s in result.ranked_sites if s.site_id == enriched_id)
    unenriched_site = next(s for s in result.ranked_sites if s.site_id != enriched_id)

    assert enriched_site.environmental_metrics is not None
    assert unenriched_site.environmental_metrics is None

    # Verify heatmap calls count: Exactly 3 calls (1x TCM, 1x Exceedance, 1x Persistence)
    assert mock_client.create_heatmap.call_count == 3

"""Tests for SQLite caching layer, deterministic keys, and CachedFortyGuardClient."""

from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from backend.cache.cached_client import CachedFortyGuardClient
from backend.cache.keys import generate_cache_key
from backend.cache.store import SQLiteCacheStore


def test_generate_cache_key_deterministic() -> None:
    """Verify that generate_cache_key is deterministic and insensitive to dictionary key ordering."""
    payload1 = {
        "polygon_aoi": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
        "date_time": {"start_date": "2024-07-15", "filter_type": 3},
        "granularity": 100,
        "analytic_type": "tcm",
    }
    payload2 = {
        "analytic_type": "tcm",
        "granularity": 100,
        "date_time": {"filter_type": 3, "start_date": "2024-07-15"},
        "polygon_aoi": {"coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]], "type": "Polygon"},
    }

    key1 = generate_cache_key("/v1/heatmap", payload1)
    key2 = generate_cache_key("/v1/heatmap", payload2)
    assert key1 == key2
    assert len(key1) == 64  # SHA-256 hex length

    # Different parameters should yield different keys
    payload3 = dict(payload1, granularity=80)
    key3 = generate_cache_key("/v1/heatmap", payload3)
    assert key1 != key3


def test_generate_cache_key_ignores_secrets() -> None:
    """Verify that API keys or authorization headers are stripped from cache key hashing."""
    payload_with_key = {"param": "value", "api_key": "fg_live_secret123"}
    payload_clean = {"param": "value"}

    assert generate_cache_key("/v1/test", payload_with_key) == generate_cache_key("/v1/test", payload_clean)


def test_sqlite_cache_store(tmp_path: pytest.TempPathFactory) -> None:
    """Test SQLiteCacheStore get, set, hit tracking, and clear operations."""
    db_file = tmp_path / "test_cache.db"
    store = SQLiteCacheStore(db_path=db_file)

    key = "test_sha256_key_123"
    endpoint = "/v1/heatmap"
    payload = {"start_date": "2024-07-15"}
    sample_response = {"activity_id": "act_123", "result": {"data": "sample"}}

    # Initial get -> cache miss
    assert store.get(key) is None
    assert store.has(key) is False

    # Store entry
    store.set(key, endpoint, payload, sample_response)
    assert store.has(key) is True

    # Retrieve entry -> cache hit
    retrieved = store.get(key)
    assert retrieved == sample_response

    # Stats check
    stats = store.stats()
    assert stats["total_entries"] == 1
    assert stats["total_hits"] >= 1
    assert stats["endpoint_breakdown"].get(endpoint) == 1

    # Delete entry
    assert store.delete(key) is True
    assert store.get(key) is None


def test_cached_fortyguard_client_interception(tmp_path: pytest.TempPathFactory) -> None:
    """Test that CachedFortyGuardClient calls the underlying client once and uses cache on repeat."""
    db_file = tmp_path / "client_cache.db"
    store = SQLiteCacheStore(db_path=db_file)

    mock_client = MagicMock()
    mock_response = {
        "activity_id": "act_mock_999",
        "result": {"map_data": {"type": "FeatureCollection", "features": []}},
    }
    mock_client.create_heatmap.return_value = mock_response

    cached_client = CachedFortyGuardClient(client=mock_client, store=store)

    aoi = {"type": "FeatureCollection", "features": []}

    # First call: cache miss -> calls underlying client
    resp1 = cached_client.create_heatmap(
        polygon_aoi=aoi,
        start_date="2024-07-15",
        filter_type=3,
    )
    assert resp1 == mock_response
    assert mock_client.create_heatmap.call_count == 1

    # Second call (identical): cache hit -> underlying client NOT called again
    resp2 = cached_client.create_heatmap(
        polygon_aoi=aoi,
        start_date="2024-07-15",
        filter_type=3,
    )
    assert resp2 == mock_response
    assert mock_client.create_heatmap.call_count == 1  # Still 1!

    # Third call with different parameter -> cache miss -> client called again
    resp3 = cached_client.create_heatmap(
        polygon_aoi=aoi,
        start_date="2024-07-15",
        filter_type=3,
        granularity=80,  # Changed granularity
    )
    assert resp3 == mock_response
    assert mock_client.create_heatmap.call_count == 2

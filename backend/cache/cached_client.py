"""Cached wrapper for FortyGuardClient ensuring transparent caching and zero redundant calls."""

from __future__ import annotations

from typing import Any, Iterable

from fortyguard.client import FortyGuardClient
from backend.cache.keys import generate_cache_key
from backend.cache.store import SQLiteCacheStore, get_cache_store


class CachedFortyGuardClient:
    """Wrapper around FortyGuardClient that intercepts calls to query the persistent cache first."""

    def __init__(
        self,
        client: FortyGuardClient | None = None,
        store: SQLiteCacheStore | None = None,
    ) -> None:
        self._client = client or FortyGuardClient()
        self._store = store or get_cache_store()

    @property
    def client(self) -> FortyGuardClient:
        return self._client

    @property
    def store(self) -> SQLiteCacheStore:
        return self._store

    def create_heatmap(
        self,
        polygon_aoi: dict[str, Any],
        start_date: str,
        filter_type: int,
        granularity: int = 100,
        start_time: str | None = None,
        end_time: str | None = None,
        end_date: str | None = None,
        analytic_type: str = "tcm",
        threshold: float | None = None,
        direction: str | None = None,
        bypass_cache: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Fetch or retrieve cached heatmap response (TCM, exceedance, persistence)."""
        date_time: dict[str, Any] = {"start_date": start_date, "filter_type": filter_type}
        if start_time is not None:
            date_time["start_time"] = start_time
        if end_time is not None:
            date_time["end_time"] = end_time
        if end_date is not None:
            date_time["end_date"] = end_date

        payload: dict[str, Any] = {
            "polygon_aoi": polygon_aoi,
            "date_time": date_time,
            "granularity": granularity,
            "analytic_type": analytic_type,
        }
        if threshold is not None:
            payload["threshold"] = threshold
        if direction is not None:
            payload["direction"] = direction

        cache_key = generate_cache_key("/v1/heatmap", payload)

        if not bypass_cache:
            cached_resp = self._store.get(cache_key)
            if cached_resp is not None:
                return cached_resp

        # Cache miss -> Execute live API request
        response = self._client.create_heatmap(
            polygon_aoi=polygon_aoi,
            start_date=start_date,
            filter_type=filter_type,
            granularity=granularity,
            start_time=start_time,
            end_time=end_time,
            end_date=end_date,
            analytic_type=analytic_type,
            threshold=threshold,
            direction=direction,
            **kwargs,
        )

        if isinstance(response, dict):
            self._store.set(cache_key, "/v1/heatmap", payload, response)

        return response

    def environmental_parameters(
        self,
        latitude: float,
        longitude: float,
        temperature: float,
        start_date: str,
        filter_type: int,
        start_time: str | None = None,
        end_time: str | None = None,
        end_date: str | None = None,
        analysis: Iterable[str] | None = None,
        bypass_cache: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Fetch or retrieve cached environmental parameters time-series."""
        date_time: dict[str, Any] = {"start_date": start_date, "filter_type": filter_type}
        if start_time is not None:
            date_time["start_time"] = start_time
        if end_time is not None:
            date_time["end_time"] = end_time
        if end_date is not None:
            date_time["end_date"] = end_date

        payload: dict[str, Any] = {
            "latitude": round(latitude, 5),
            "longitude": round(longitude, 5),
            "temperature": round(temperature, 2),
            "date_time": date_time,
        }
        if analysis is not None:
            payload["analysis"] = sorted(list(analysis))

        cache_key = generate_cache_key("/v1/env_params", payload)

        if not bypass_cache:
            cached_resp = self._store.get(cache_key)
            if cached_resp is not None:
                return cached_resp

        response = self._client.environmental_parameters(
            latitude=latitude,
            longitude=longitude,
            temperature=temperature,
            start_date=start_date,
            filter_type=filter_type,
            start_time=start_time,
            end_time=end_time,
            end_date=end_date,
            analysis=analysis,
            **kwargs,
        )

        if isinstance(response, dict):
            self._store.set(cache_key, "/v1/env_params", payload, response)

        return response

    def satellite_segmentation(
        self,
        latitude: float,
        longitude: float,
        start_date: str,
        filter_type: int,
        granularity: int = 100,
        start_time: str | None = None,
        end_time: str | None = None,
        end_date: str | None = None,
        bypass_cache: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Fetch or retrieve cached satellite land-cover segmentation."""
        date_time: dict[str, Any] = {"start_date": start_date, "filter_type": filter_type}
        if start_time is not None:
            date_time["start_time"] = start_time
        if end_time is not None:
            date_time["end_time"] = end_time
        if end_date is not None:
            date_time["end_date"] = end_date

        payload = {
            "sat": {"latitude": round(latitude, 5), "longitude": round(longitude, 5)},
            "date_time": date_time,
            "granularity": granularity,
        }

        cache_key = generate_cache_key("/v1/satellite", payload)

        if not bypass_cache:
            cached_resp = self._store.get(cache_key)
            if cached_resp is not None:
                return cached_resp

        response = self._client.satellite_segmentation(
            latitude=latitude,
            longitude=longitude,
            start_date=start_date,
            filter_type=filter_type,
            granularity=granularity,
            start_time=start_time,
            end_time=end_time,
            end_date=end_date,
            **kwargs,
        )

        if isinstance(response, dict):
            self._store.set(cache_key, "/v1/satellite", payload, response)

        return response

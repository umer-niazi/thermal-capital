"""Offline mock engine for the FortyGuard tOS Enterprise API.

Provides local, network-free simulation using authentic captured fixtures from
`fixtures/fortyguard/`. Implements Haversine nearest-neighbor matching so that any
map click, parcel screening, or geographic pan returns realistic, schema-compliant
microclimate observations without schema drift.
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any, Iterable

logger = logging.getLogger("fortyguard.mock")

# Default coordinates for known regions (fallback if manifest is not yet generated)
DEFAULT_REGIONS = {
    "phoenix": {
        "name": "Phoenix, AZ",
        "climate": "Hot Desert (BWh)",
        "coordinates": {"lat": 33.4484, "lon": -112.0740},
        "has_satellite": True,
        "has_streetview": False,
    },
    "nyc": {
        "name": "New York City, NY",
        "climate": "Humid Subtropical / Dense Urban Canyon (Cfa)",
        "coordinates": {"lat": 40.7128, "lon": -74.0060},
        "has_satellite": True,
        "has_streetview": False,
    },
    "dallas": {
        "name": "Dallas-Fort Worth, TX",
        "climate": "Humid Subtropical Sprawl (Cfa)",
        "coordinates": {"lat": 32.7767, "lon": -96.7970},
        "has_satellite": False,
        "has_streetview": False,
    },
    "houston": {
        "name": "Houston, TX",
        "climate": "Humid Subtropical Gulf Coast (Cfa)",
        "coordinates": {"lat": 29.7604, "lon": -95.3698},
        "has_satellite": False,
        "has_streetview": False,
    },
    "austin": {
        "name": "Austin, TX",
        "climate": "Subtropical Hill Country (Cfa)",
        "coordinates": {"lat": 30.2672, "lon": -97.7431},
        "has_satellite": False,
        "has_streetview": False,
    },
    "el_paso": {
        "name": "El Paso, TX",
        "climate": "Cold Semi-Arid / High Desert (BSk)",
        "coordinates": {"lat": 31.7619, "lon": -106.4850},
        "has_satellite": False,
        "has_streetview": False,
    },
    "san_jose": {
        "name": "San Jose, CA",
        "climate": "Warm-Summer Mediterranean / Silicon Valley (Csb)",
        "coordinates": {"lat": 37.3382, "lon": -121.8863},
        "has_satellite": True,
        "has_streetview": True,
    },
    "miami": {
        "name": "Miami, FL",
        "climate": "Tropical Monsoon Coastal (Am)",
        "coordinates": {"lat": 25.7617, "lon": -80.1918},
        "has_satellite": False,
        "has_streetview": False,
    },
}


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in kilometers."""
    radius_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return radius_km * c


def extract_polygon_centroid(polygon_aoi: dict[str, Any]) -> tuple[float, float]:
    """Compute the centroid (lat, lon) of arbitrary GeoJSON geometry / Feature / FeatureCollection."""
    coords: list[tuple[float, float]] = []

    def _collect_coords(obj: Any) -> None:
        if isinstance(obj, (list, tuple)):
            if len(obj) >= 2 and isinstance(obj[0], (int, float)) and isinstance(obj[1], (int, float)):
                # GeoJSON coordinates are [lon, lat]
                coords.append((float(obj[1]), float(obj[0])))
            else:
                for item in obj:
                    _collect_coords(item)
        elif isinstance(obj, dict):
            if "coordinates" in obj:
                _collect_coords(obj["coordinates"])
            elif "geometry" in obj:
                _collect_coords(obj["geometry"])
            elif "features" in obj:
                _collect_coords(obj["features"])

    _collect_coords(polygon_aoi)

    if not coords:
        # Default fallback to Phoenix center
        return (33.4484, -112.0740)

    mean_lat = sum(c[0] for c in coords) / len(coords)
    mean_lon = sum(c[1] for c in coords) / len(coords)
    return (mean_lat, mean_lon)


class MockFortyGuardStore:
    """In-memory cache and dispatcher for offline FortyGuard fixtures."""

    def __init__(self, fixtures_dir: Path | None = None) -> None:
        if fixtures_dir:
            self.fixtures_dir = fixtures_dir
        else:
            # Search common locations
            current_dir = Path(__file__).resolve().parent
            candidates = [
                current_dir.parent / "fixtures" / "fortyguard",
                current_dir / "fixtures" / "fortyguard",
                Path.cwd() / "fixtures" / "fortyguard",
            ]
            self.fixtures_dir = next((c for c in candidates if c.exists()), candidates[0])

        self._cache: dict[str, Any] = {}
        self._manifest: dict[str, Any] = {}
        self._load_manifest()

    def _load_manifest(self) -> None:
        manifest_path = self.fixtures_dir / "manifest.json"
        if manifest_path.exists():
            try:
                with manifest_path.open("r", encoding="utf-8") as f:
                    self._manifest = json.load(f)
            except Exception as exc:
                logger.warning(f"[MOCK FortyGuard API] Could not load manifest.json: {exc}")

    def load_fixture(self, filename: str) -> dict[str, Any] | None:
        """Load and cache a JSON fixture from the fixtures directory."""
        if filename in self._cache:
            return self._cache[filename]

        filepath = self.fixtures_dir / filename
        if not filepath.exists():
            # Fallback check in data/ directories
            data_candidates = [
                self.fixtures_dir.parent.parent / "data" / "probes" / filename,
                self.fixtures_dir.parent.parent / "data" / "heatmaps" / filename,
            ]
            filepath = next((c for c in data_candidates if c.exists()), filepath)

        if not filepath.exists():
            logger.warning(f"[MOCK FortyGuard API] Fixture file not found: {filename}")
            return None

        try:
            with filepath.open("r", encoding="utf-8") as f:
                data = json.load(f)
                self._cache[filename] = data
                return data
        except Exception as exc:
            logger.error(f"[MOCK FortyGuard API] Error reading {filename}: {exc}")
            return None

    def find_nearest_region(
        self,
        lat: float,
        lon: float,
        require_satellite: bool = False,
        require_streetview: bool = False,
        require_heatmap: bool = False,
    ) -> tuple[str, float]:
        """Find the closest matching region to the target coordinates using Haversine distance."""
        best_region = "phoenix"
        min_dist = float("inf")

        for reg_id, reg_info in DEFAULT_REGIONS.items():
            if require_satellite and not reg_info.get("has_satellite", False):
                continue
            if require_streetview and not reg_info.get("has_streetview", False):
                continue

            r_coords = reg_info["coordinates"]
            dist = haversine_distance_km(lat, lon, r_coords["lat"], r_coords["lon"])
            if dist < min_dist:
                min_dist = dist
                best_region = reg_id

        return best_region, min_dist

    def create_heatmap(
        self,
        polygon_aoi: dict[str, Any],
        start_date: str,
        filter_type: int,
        granularity: int = 100,
        analytic_type: str = "tcm",
        threshold: float | None = None,
        direction: str | None = None,
        *,
        wait: bool = True,
        **_kwargs: Any,
    ) -> dict[str, Any] | str:
        """Serve mock heatmap (TCM, exceedance, persistence) based on polygon centroid."""
        lat, lon = extract_polygon_centroid(polygon_aoi)
        region, dist_km = self.find_nearest_region(lat, lon, require_heatmap=True)

        fixture_filename = f"{region}_{analytic_type}.json"
        data = self.load_fixture(fixture_filename)

        # Fallbacks if specific analytic_type fixture is absent
        if not data:
            if analytic_type != "tcm":
                data = self.load_fixture(f"{region}_tcm.json")
            if not data:
                # Default to Phoenix or NYC
                data = self.load_fixture(f"phoenix_{analytic_type}.json") or self.load_fixture("phoenix_tcm.json")

        activity_id = f"mock-heatmap-{region}-{analytic_type}"
        logger.info(
            f"[MOCK FortyGuard API] Serving offline {analytic_type.upper()} heatmap for ({lat:.4f}, {lon:.4f}) -> "
            f"Nearest: {DEFAULT_REGIONS.get(region, {}).get('name', region)} ({dist_km:.1f} km away)"
        )

        result_payload = data.get("result", data) if data else {"map_data": {"type": "FeatureCollection", "features": []}}
        response = {"activity_id": activity_id, "result": result_payload}

        if not wait:
            return activity_id
        return response

    def environmental_parameters(
        self,
        latitude: float,
        longitude: float,
        temperature: float,
        start_date: str,
        filter_type: int,
        analysis: Iterable[str] | None = None,
        *,
        wait: bool = True,
        **_kwargs: Any,
    ) -> dict[str, Any] | str:
        """Serve mock 24-hour environmental parameters time series."""
        region, dist_km = self.find_nearest_region(latitude, longitude)

        # Check for August vs July multi-temporal data
        is_august = "08-" in str(start_date) or "-08" in str(start_date)
        fixture_filename = f"{region}_env_params_august.json" if is_august else f"{region}_env_params.json"
        data = self.load_fixture(fixture_filename)
        if not data:
            data = self.load_fixture(f"{region}_env_params.json") or self.load_fixture("phoenix_env_params.json")

        activity_id = f"mock-env_params-{region}"
        logger.info(
            f"[MOCK FortyGuard API] Serving offline env_params for ({latitude:.4f}, {longitude:.4f}) on {start_date} -> "
            f"Nearest: {DEFAULT_REGIONS.get(region, {}).get('name', region)} ({dist_km:.1f} km away)"
        )

        result_payload = data.get("result", data) if data else {"locations": []}
        if isinstance(result_payload, dict) and "result" in result_payload and isinstance(result_payload["result"], dict):
            if "locations" in result_payload["result"]:
                result_payload = result_payload["result"]

        response = {"activity_id": activity_id, "result": result_payload}

        if not wait:
            return activity_id
        return response

    def satellite_segmentation(
        self,
        latitude: float,
        longitude: float,
        start_date: str,
        filter_type: int,
        granularity: int = 100,
        *,
        wait: bool = True,
        **_kwargs: Any,
    ) -> dict[str, Any] | str:
        """Serve mock satellite land-cover segmentation."""
        region, dist_km = self.find_nearest_region(latitude, longitude, require_satellite=True)
        fixture_filename = f"{region}_satellite.json"
        data = self.load_fixture(fixture_filename) or self.load_fixture("phoenix_satellite.json")

        activity_id = f"mock-satellite-{region}"
        logger.info(
            f"[MOCK FortyGuard API] Serving offline satellite segmentation for ({latitude:.4f}, {longitude:.4f}) -> "
            f"Nearest: {DEFAULT_REGIONS.get(region, {}).get('name', region)} ({dist_km:.1f} km away)"
        )

        result_payload = data.get("result", data) if data else {}
        response = {"activity_id": activity_id, "result": result_payload}

        if not wait:
            return activity_id
        return response

    def street_view_segmentation(
        self,
        latitude: float,
        longitude: float,
        vertical_angle: float = 0.0,
        horizontal_angle: float = 0.0,
        back_view: bool = False,
        *,
        wait: bool = True,
        **_kwargs: Any,
    ) -> dict[str, Any] | str:
        """Serve mock street view segmentation."""
        region, dist_km = self.find_nearest_region(latitude, longitude, require_streetview=True)
        fixture_filename = f"{region}_streetview.json"
        data = self.load_fixture(fixture_filename) or self.load_fixture("san_jose_streetview.json")

        activity_id = f"mock-streetview-{region}"
        logger.info(
            f"[MOCK FortyGuard API] Serving offline streetview segmentation for ({latitude:.4f}, {longitude:.4f}) -> "
            f"Nearest: {DEFAULT_REGIONS.get(region, {}).get('name', region)}"
        )

        result_payload = data.get("result", data) if data else {}
        response = {"activity_id": activity_id, "result": result_payload}

        if not wait:
            return activity_id
        return response

    def get_status(self, activity_id: str) -> dict[str, Any]:
        """Return completed mock status for any mock activity."""
        logger.info(f"[MOCK FortyGuard API] Serving offline status check for {activity_id}")
        # Identify layer and region from activity_id
        parts = activity_id.split("-")
        layer = parts[1] if len(parts) > 1 else "tcm"
        region = parts[2] if len(parts) > 2 else "phoenix"

        fixture = self.load_fixture(f"{region}_{layer}.json") or self.load_fixture("phoenix_tcm.json")
        result = fixture.get("result", fixture) if fixture else {}

        return {
            "activity_id": activity_id,
            "status": "completed",
            "result": result,
        }

    def fetch_api_key_usage(self) -> dict[str, Any]:
        """Return offline API key usage summary."""
        logger.info("[MOCK FortyGuard API] Serving offline API key usage summary")
        data = self.load_fixture("api_usage_summary.json")
        if data:
            return data
        return {
            "api_key_details": {
                "status": "active (offline mock demo)",
                "valid": True,
                "api_access_available": True,
            },
            "credit_summary": {
                "total_credits": 1000000,
                "available_credits": 1000000,
                "credits_used": 0,
            },
        }

    def fetch_api_key_custom_usage(self, start_date: str, end_date: str) -> dict[str, Any]:
        """Return offline API key custom usage breakdown."""
        logger.info(f"[MOCK FortyGuard API] Serving offline custom usage for {start_date} to {end_date}")
        data = self.load_fixture("api_custom_usage.json")
        if data:
            return data
        return {
            "date_range": {"start_date": start_date, "end_date": end_date},
            "activity_breakdown": [],
            "total_credits_used": 0,
        }


# Singleton instance
_MOCK_STORE_INSTANCE: MockFortyGuardStore | None = None


def get_mock_store() -> MockFortyGuardStore:
    """Get or create singleton MockFortyGuardStore."""
    global _MOCK_STORE_INSTANCE
    if _MOCK_STORE_INSTANCE is None:
        _MOCK_STORE_INSTANCE = MockFortyGuardStore()
    return _MOCK_STORE_INSTANCE

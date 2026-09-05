"""Capture fixtures from the FortyGuard API and curate comprehensive offline fixtures.

Hits live endpoints while API key is active for:
- System API key usage and billing stats
- Environmental parameters across varied cities (Phoenix, NYC, Miami, Dallas, etc.)
- Multi-temporal points (July 15 and August 15)

Also curates and verifies authentic responses from existing probe datasets
(Phoenix, NYC citywide & borough tiles, Texas cities: DFW, Houston, Austin, El Paso,
and San Jose Diridon & APN parcels) into `fixtures/fortyguard/`.

Produces:
- Descriptive fixture files (phoenix.json, nyc_summer.json, dallas.json, etc.)
- Granular endpoint files (<city>_<layer>.json)
- manifest.json index with geographic coordinates, layers, and bounding boxes.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("capture_fixtures")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
FIXTURES_DIR = PROJECT_ROOT / "fixtures" / "fortyguard"
DATA_DIR = PROJECT_ROOT / "data"

REGIONS = {
    "phoenix": {
        "name": "Phoenix, AZ",
        "climate": "Hot Desert (BWh)",
        "coordinates": {"lat": 33.4484, "lon": -112.0740},
        "bbox": [-112.110, 33.430, -112.040, 33.470],
    },
    "nyc": {
        "name": "New York City, NY",
        "climate": "Humid Subtropical / Dense Urban Canyon (Cfa)",
        "coordinates": {"lat": 40.7128, "lon": -74.0060},
        "bbox": [-74.259, 40.477, -73.700, 40.917],
    },
    "dallas": {
        "name": "Dallas-Fort Worth, TX",
        "climate": "Humid Subtropical Sprawl (Cfa)",
        "coordinates": {"lat": 32.7767, "lon": -96.7970},
        "bbox": [-96.850, 32.740, -96.750, 32.820],
    },
    "houston": {
        "name": "Houston, TX",
        "climate": "Humid Subtropical Gulf Coast (Cfa)",
        "coordinates": {"lat": 29.7604, "lon": -95.3698},
        "bbox": [-95.420, 29.720, -95.320, 29.800],
    },
    "austin": {
        "name": "Austin, TX",
        "climate": "Subtropical Hill Country (Cfa)",
        "coordinates": {"lat": 30.2672, "lon": -97.7431},
        "bbox": [-97.800, 30.230, -97.700, 30.310],
    },
    "el_paso": {
        "name": "El Paso, TX",
        "climate": "Cold Semi-Arid / High Desert (BSk)",
        "coordinates": {"lat": 31.7619, "lon": -106.4850},
        "bbox": [-106.520, 31.730, -106.440, 31.800],
    },
    "san_jose": {
        "name": "San Jose, CA",
        "climate": "Warm-Summer Mediterranean / Silicon Valley (Csb)",
        "coordinates": {"lat": 37.3382, "lon": -121.8863},
        "bbox": [-121.930, 37.300, -121.850, 37.370],
    },
    "miami": {
        "name": "Miami, FL",
        "climate": "Tropical Monsoon Coastal (Am)",
        "coordinates": {"lat": 25.7617, "lon": -80.1918},
        "bbox": [-80.230, 25.730, -80.160, 25.800],
    },
}


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_json(data: Any, filepath: Path) -> None:
    ensure_dir(filepath.parent)
    with filepath.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    logger.info(f"Saved fixture: {filepath.relative_to(PROJECT_ROOT)} ({filepath.stat().st_size:,} bytes)")


def load_json_safe(filepath: Path) -> dict[str, Any] | None:
    if not filepath.exists():
        return None
    try:
        with filepath.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning(f"Failed loading {filepath}: {exc}")
        return None


def capture_system_usage(client: Any) -> dict[str, Any] | None:
    try:
        logger.info("Fetching API key billing usage...")
        usage = client.fetch_api_key_usage()
        save_json(usage, FIXTURES_DIR / "api_usage_summary.json")

        logger.info("Fetching API key custom usage (2024-07-01 to 2024-08-31)...")
        custom_usage = client.fetch_api_key_custom_usage("2024-07-01", "2024-08-31")
        save_json(custom_usage, FIXTURES_DIR / "api_custom_usage.json")
        return usage
    except Exception as exc:
        logger.error(f"Error capturing system usage: {exc}")
        return None


def capture_live_env_params(
    client: Any,
    lat: float,
    lon: float,
    temp: float,
    start_date: str,
    output_file: Path,
) -> dict[str, Any] | None:
    if output_file.exists():
        logger.info(f"Fixture {output_file.name} already exists, skipping live request.")
        return load_json_safe(output_file)
    try:
        logger.info(f"Querying live env_params for ({lat}, {lon}) on {start_date}...")
        resp = client.environmental_parameters(
            latitude=lat,
            longitude=lon,
            temperature=temp,
            start_date=start_date,
            filter_type=3,
            verbose=False,
        )
        if isinstance(resp, dict):
            save_json(resp, output_file)
            return resp
    except Exception as exc:
        logger.error(f"Failed live env_params query for ({lat}, {lon}): {exc}")
    return None


def build_composite_fixture(
    region_key: str,
    tcm_data: dict[str, Any] | None,
    env_data: dict[str, Any] | None,
    exceedance_data: dict[str, Any] | None = None,
    persistence_data: dict[str, Any] | None = None,
    satellite_data: dict[str, Any] | None = None,
    streetview_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    info = REGIONS.get(region_key, {})
    composite = {
        "region_id": region_key,
        "region_name": info.get("name", region_key),
        "climate_zone": info.get("climate", "Urban"),
        "coordinates": info.get("coordinates", {}),
        "bbox": info.get("bbox", []),
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "endpoints": {
            "heatmap_tcm": tcm_data,
            "heatmap_exceedance": exceedance_data,
            "heatmap_persistence": persistence_data,
            "env_params": env_data,
            "satellite": satellite_data,
            "streetview": streetview_data,
        },
    }
    return composite


def main() -> None:
    load_dotenv()
    api_key = os.getenv("FORTYGUARD_API_KEY")

    client = None
    if api_key:
        try:
            from fortyguard import FortyGuardClient
            client = FortyGuardClient(api_key=api_key)
            logger.info("FortyGuard client initialized with live API key.")
        except Exception as exc:
            logger.warning(f"Could not initialize live FortyGuard client: {exc}")

    ensure_dir(FIXTURES_DIR)

    # 1. Live system stats
    if client:
        capture_system_usage(client)

    # 2. Curate and capture data for each of the 8 regions
    # --- PHOENIX ---
    logger.info("Processing Phoenix fixtures...")
    phx_tcm = load_json_safe(DATA_DIR / "probes" / "phoenix_tcm_2024-07-15.json")
    if phx_tcm:
        save_json(phx_tcm, FIXTURES_DIR / "phoenix_tcm.json")
    phx_exc = load_json_safe(DATA_DIR / "probes" / "phoenix_exceedance_2024-07-15_2024-07-21.json")
    if phx_exc:
        save_json(phx_exc, FIXTURES_DIR / "phoenix_exceedance.json")
    phx_per = load_json_safe(DATA_DIR / "probes" / "phoenix_persistence_2024-07-15_2024-07-21.json")
    if phx_per:
        save_json(phx_per, FIXTURES_DIR / "phoenix_persistence.json")
    phx_sat = load_json_safe(DATA_DIR / "probes" / "phoenix_satellite_2024-07-15.json")
    if phx_sat:
        save_json(phx_sat, FIXTURES_DIR / "phoenix_satellite.json")
    phx_env = load_json_safe(DATA_DIR / "probes" / "phoenix_env_params_2024-07-15.json")
    if phx_env:
        save_json(phx_env, FIXTURES_DIR / "phoenix_env_params.json")

    # Capture August time-point for Phoenix if client is live
    if client:
        capture_live_env_params(
            client, 33.4484, -112.0740, 42.0, "2024-08-15",
            FIXTURES_DIR / "phoenix_env_params_august.json"
        )

    # Save primary descriptive file: phoenix.json
    phoenix_composite = build_composite_fixture(
        "phoenix", phx_tcm, phx_env, phx_exc, phx_per, phx_sat
    )
    save_json(phoenix_composite, FIXTURES_DIR / "phoenix.json")

    # --- NYC ---
    logger.info("Processing NYC fixtures...")
    nyc_tcm = load_json_safe(DATA_DIR / "probes" / "nyc_tcm_2024-07-15.json")
    if nyc_tcm:
        save_json(nyc_tcm, FIXTURES_DIR / "nyc_tcm.json")
    nyc_exc = load_json_safe(DATA_DIR / "probes" / "nyc_exceedance_2024-07-15_2024-07-21.json")
    if nyc_exc:
        save_json(nyc_exc, FIXTURES_DIR / "nyc_exceedance.json")
    nyc_per = load_json_safe(DATA_DIR / "probes" / "nyc_persistence_2024-07-15_2024-07-21.json")
    if nyc_per:
        save_json(nyc_per, FIXTURES_DIR / "nyc_persistence.json")
    nyc_sat = load_json_safe(DATA_DIR / "probes" / "nyc_satellite_2024-07-15.json")
    if nyc_sat:
        save_json(nyc_sat, FIXTURES_DIR / "nyc_satellite.json")
    nyc_env = load_json_safe(DATA_DIR / "probes" / "nyc_env_params_2024-07-15.json")
    if nyc_env:
        save_json(nyc_env, FIXTURES_DIR / "nyc_env_params.json")

    # Full citywide probe data
    nyc_city_tcm = load_json_safe(DATA_DIR / "probes" / "nyc_citywide_tcm.json")
    if nyc_city_tcm:
        save_json(nyc_city_tcm, FIXTURES_DIR / "nyc_citywide_tcm.json")
    nyc_city_exc = load_json_safe(DATA_DIR / "probes" / "nyc_citywide_exceedance.json")
    if nyc_city_exc:
        save_json(nyc_city_exc, FIXTURES_DIR / "nyc_citywide_exceedance.json")
    nyc_city_per = load_json_safe(DATA_DIR / "probes" / "nyc_citywide_persistence.json")
    if nyc_city_per:
        save_json(nyc_city_per, FIXTURES_DIR / "nyc_citywide_persistence.json")

    # Capture August time-point for NYC if client is live
    if client:
        capture_live_env_params(
            client, 40.7128, -74.0060, 31.0, "2024-08-15",
            FIXTURES_DIR / "nyc_env_params_august.json"
        )

    # Save primary descriptive file: nyc_summer.json
    nyc_composite = build_composite_fixture(
        "nyc", nyc_tcm, nyc_env, nyc_exc, nyc_per, nyc_sat
    )
    save_json(nyc_composite, FIXTURES_DIR / "nyc_summer.json")

    # --- DALLAS ---
    logger.info("Processing Dallas-Fort Worth fixtures...")
    dfw_tcm = load_json_safe(DATA_DIR / "probes" / "texas_tcm_TX-DFW-01_2024-07-15.json")
    if dfw_tcm:
        save_json(dfw_tcm, FIXTURES_DIR / "dallas_tcm.json")
    dfw_exc = load_json_safe(DATA_DIR / "probes" / "texas_exceedance_TX-DFW-01_2024-07-15_2024-07-21.json")
    if dfw_exc:
        save_json(dfw_exc, FIXTURES_DIR / "dallas_exceedance.json")
    dfw_per = load_json_safe(DATA_DIR / "probes" / "texas_persistence_TX-DFW-01_2024-07-15_2024-07-21.json")
    if dfw_per:
        save_json(dfw_per, FIXTURES_DIR / "dallas_persistence.json")
    dfw_env = load_json_safe(DATA_DIR / "probes" / "texas_env_params_TX-DFW-01_2024-07-15.json")
    if dfw_env:
        save_json(dfw_env, FIXTURES_DIR / "dallas_env_params.json")

    dfw_composite = build_composite_fixture("dallas", dfw_tcm, dfw_env, dfw_exc, dfw_per)
    save_json(dfw_composite, FIXTURES_DIR / "dallas.json")

    # --- HOUSTON ---
    logger.info("Processing Houston fixtures...")
    hou_tcm = load_json_safe(DATA_DIR / "probes" / "texas_tcm_TX-HOU-01_2024-07-15.json")
    if hou_tcm:
        save_json(hou_tcm, FIXTURES_DIR / "houston_tcm.json")
    hou_exc = load_json_safe(DATA_DIR / "probes" / "texas_exceedance_TX-HOU-01_2024-07-15_2024-07-21.json")
    if hou_exc:
        save_json(hou_exc, FIXTURES_DIR / "houston_exceedance.json")
    hou_per = load_json_safe(DATA_DIR / "probes" / "texas_persistence_TX-HOU-01_2024-07-15_2024-07-21.json")
    if hou_per:
        save_json(hou_per, FIXTURES_DIR / "houston_persistence.json")
    hou_env = load_json_safe(DATA_DIR / "probes" / "texas_env_params_TX-HOU-01_2024-07-15.json")
    if hou_env:
        save_json(hou_env, FIXTURES_DIR / "houston_env_params.json")

    hou_composite = build_composite_fixture("houston", hou_tcm, hou_env, hou_exc, hou_per)
    save_json(hou_composite, FIXTURES_DIR / "houston.json")

    # --- AUSTIN ---
    logger.info("Processing Austin fixtures...")
    aus_tcm = load_json_safe(DATA_DIR / "probes" / "texas_tcm_TX-AUS-01_2024-07-15.json")
    if aus_tcm:
        save_json(aus_tcm, FIXTURES_DIR / "austin_tcm.json")
    aus_exc = load_json_safe(DATA_DIR / "probes" / "texas_exceedance_TX-AUS-01_2024-07-15_2024-07-21.json")
    if aus_exc:
        save_json(aus_exc, FIXTURES_DIR / "austin_exceedance.json")
    aus_per = load_json_safe(DATA_DIR / "probes" / "texas_persistence_TX-AUS-01_2024-07-15_2024-07-21.json")
    if aus_per:
        save_json(aus_per, FIXTURES_DIR / "austin_persistence.json")
    aus_env = load_json_safe(DATA_DIR / "probes" / "texas_env_params_TX-AUS-01_2024-07-15.json")
    if aus_env:
        save_json(aus_env, FIXTURES_DIR / "austin_env_params.json")

    aus_composite = build_composite_fixture("austin", aus_tcm, aus_env, aus_exc, aus_per)
    save_json(aus_composite, FIXTURES_DIR / "austin.json")

    # --- EL PASO ---
    logger.info("Processing El Paso fixtures...")
    elp_tcm = load_json_safe(DATA_DIR / "probes" / "texas_tcm_TX-ELP-01_2024-07-15.json")
    if elp_tcm:
        save_json(elp_tcm, FIXTURES_DIR / "el_paso_tcm.json")
    elp_exc = load_json_safe(DATA_DIR / "probes" / "texas_exceedance_TX-ELP-01_2024-07-15_2024-07-21.json")
    if elp_exc:
        save_json(elp_exc, FIXTURES_DIR / "el_paso_exceedance.json")
    elp_per = load_json_safe(DATA_DIR / "probes" / "texas_persistence_TX-ELP-01_2024-07-15_2024-07-21.json")
    if elp_per:
        save_json(elp_per, FIXTURES_DIR / "el_paso_persistence.json")
    elp_env = load_json_safe(DATA_DIR / "probes" / "texas_env_params_TX-ELP-01_2024-07-15.json")
    if elp_env:
        save_json(elp_env, FIXTURES_DIR / "el_paso_env_params.json")

    elp_composite = build_composite_fixture("el_paso", elp_tcm, elp_env, elp_exc, elp_per)
    save_json(elp_composite, FIXTURES_DIR / "el_paso.json")

    # --- SAN JOSE ---
    logger.info("Processing San Jose fixtures...")
    sj_tcm = load_json_safe(DATA_DIR / "heatmaps" / "heatmap_parcel_diridon_san_jose_2024-07-15_tcm.json")
    if sj_tcm:
        save_json(sj_tcm, FIXTURES_DIR / "san_jose_tcm.json")
    sj_exc = load_json_safe(DATA_DIR / "heatmaps" / "heatmap_parcel_diridon_san_jose_2024-07-12_2024-07-18_exceedance.json")
    if sj_exc:
        save_json(sj_exc, FIXTURES_DIR / "san_jose_exceedance.json")
    sj_per = load_json_safe(DATA_DIR / "heatmaps" / "heatmap_parcel_diridon_san_jose_2024-07-12_2024-07-18_persistence.json")
    if sj_per:
        save_json(sj_per, FIXTURES_DIR / "san_jose_persistence.json")
    sj_env = load_json_safe(DATA_DIR / "env_params" / "env_params_parcel_diridon_san_jose_2024-07-15.json")
    if sj_env:
        save_json(sj_env, FIXTURES_DIR / "san_jose_env_params.json")
    sj_sat = load_json_safe(DATA_DIR / "satellite" / "satellite_parcel_diridon_san_jose_2024-07-15.json")
    if sj_sat:
        save_json(sj_sat, FIXTURES_DIR / "san_jose_satellite.json")
    sj_stv = load_json_safe(DATA_DIR / "street_view" / "streetview_parcel_diridon_san_jose.json")
    if sj_stv:
        save_json(sj_stv, FIXTURES_DIR / "san_jose_streetview.json")

    # Also include San Jose parcel portfolio fixtures
    sj_port_tcm = load_json_safe(DATA_DIR / "heatmaps" / "heatmap_parcel_portfolio_san_jose_2026-08-03_tcm.json")
    if sj_port_tcm:
        save_json(sj_port_tcm, FIXTURES_DIR / "san_jose_portfolio_tcm.json")

    sj_composite = build_composite_fixture(
        "san_jose", sj_tcm, sj_env, sj_exc, sj_per, sj_sat, sj_stv
    )
    save_json(sj_composite, FIXTURES_DIR / "san_jose.json")

    # --- MIAMI ---
    logger.info("Processing Miami fixtures...")
    miami_tcm = None
    if (FIXTURES_DIR / "miami_tcm.json").exists():
        miami_tcm = load_json_safe(FIXTURES_DIR / "miami_tcm.json")
    elif client:
        try:
            logger.info("Fetching completed Miami TCM heatmap...")
            st = client.get_status("e639acbc-4072-46b8-ba38-7f228c008703")
            if st and "result" in st:
                miami_tcm = {"activity_id": "e639acbc-4072-46b8-ba38-7f228c008703", "result": st["result"]}
                save_json(miami_tcm, FIXTURES_DIR / "miami_tcm.json")
        except Exception as exc:
            logger.warning(f"Could not retrieve Miami heatmap activity: {exc}")

    miami_env = None
    if client:
        miami_env = capture_live_env_params(
            client, 25.7617, -80.1918, 32.5, "2024-07-15",
            FIXTURES_DIR / "miami_env_params.json"
        )
        capture_live_env_params(
            client, 25.7617, -80.1918, 33.0, "2024-08-15",
            FIXTURES_DIR / "miami_env_params_august.json"
        )
    else:
        miami_env = load_json_safe(FIXTURES_DIR / "miami_env_params.json")

    miami_composite = build_composite_fixture("miami", miami_tcm, miami_env)
    save_json(miami_composite, FIXTURES_DIR / "miami.json")

    # 3. Create manifest.json
    logger.info("Generating manifest.json...")
    all_fixtures = list(FIXTURES_DIR.glob("*.json"))
    manifest = {
        "generator": "scripts/capture_fixtures.py",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_files": len(all_fixtures) + 1,
        "regions": REGIONS,
        "fixtures": {
            f.name: {
                "size_bytes": f.stat().st_size,
                "path": f"fixtures/fortyguard/{f.name}",
            }
            for f in sorted(all_fixtures, key=lambda p: p.name)
            if f.name != "manifest.json"
        },
    }
    save_json(manifest, FIXTURES_DIR / "manifest.json")
    logger.info(f"Capture complete. Generated {len(manifest['fixtures'])} fixtures in {FIXTURES_DIR.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()

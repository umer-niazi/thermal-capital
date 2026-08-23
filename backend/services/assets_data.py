"""Public assets registry and FortyGuard microclimate spatial enrichment service."""

from __future__ import annotations

import functools
import json
import math
import pathlib
from typing import Any

from backend.models.planner import (
    AssetType,
    CityConfig,
    HeatRiskLevel,
    InterventionType,
    ObservedHeatMetrics,
    PublicAsset,
)

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
PROBES_DIR = ROOT_DIR / "data" / "probes"
HEATMAPS_DIR = ROOT_DIR / "data" / "heatmaps"

CITY_CONFIGS: dict[str, CityConfig] = {
    "nyc": CityConfig(
        city_key="nyc",
        name="New York City",
        state="NY",
        display_label="New York City (All Boroughs)",
        center=[-73.9680, 40.7300],
        zoom=11.0,
        bounds=[[-74.258, 40.495], [-73.700, 40.915]],
        fortyguard_tiles_count=47,
        study_date="2024-07-15",
        study_window="Jul 15–21, 2024",
        description="Citywide FortyGuard 100m ambient microclimate grid across all five New York City boroughs (Manhattan, Brooklyn, Queens, The Bronx, and Staten Island).",
        key_neighborhoods=["Manhattan", "Brooklyn", "Queens", "The Bronx", "Staten Island", "Hunts Point / Longwood", "Lower Manhattan", "Downtown Brooklyn", "Flushing", "Jamaica"],
    ),
    "manhattan": CityConfig(
        city_key="manhattan",
        name="Manhattan",
        state="NY",
        display_label="Manhattan",
        center=[-73.9712, 40.7831],
        zoom=12.5,
        bounds=[[-74.048, 40.683], [-73.906, 40.880]],
        fortyguard_tiles_count=9,
        study_date="2024-07-15",
        study_window="Jul 15–21, 2024",
        description="High-density urban canyons, commercial corridors, and civic transit plazas across Manhattan.",
        key_neighborhoods=["Lower Manhattan", "Midtown", "Harlem", "Washington Heights", "East Village"],
    ),
    "brooklyn": CityConfig(
        city_key="brooklyn",
        name="Brooklyn",
        state="NY",
        display_label="Brooklyn",
        center=[-73.9442, 40.6782],
        zoom=12.0,
        bounds=[[-74.042, 40.570], [-73.833, 40.739]],
        fortyguard_tiles_count=14,
        study_date="2024-07-15",
        study_window="Jul 15–21, 2024",
        description="Major transit interchanges, commercial corridors, residential brownstone districts, and coastal communities in Brooklyn.",
        key_neighborhoods=["Downtown Brooklyn", "Williamsburg", "Bushwick", "Bed-Stuy", "Coney Island"],
    ),
    "queens": CityConfig(
        city_key="queens",
        name="Queens",
        state="NY",
        display_label="Queens",
        center=[-73.8317, 40.7282],
        zoom=12.0,
        bounds=[[-73.963, 40.542], [-73.700, 40.801]],
        fortyguard_tiles_count=23,
        study_date="2024-07-15",
        study_window="Jul 15–21, 2024",
        description="Diverse commercial hubs, elevated transit spines, and residential neighborhoods across Queens.",
        key_neighborhoods=["Flushing", "Jamaica", "Jackson Heights", "Long Island City", "Astoria", "Rockaways"],
    ),
    "bronx": CityConfig(
        city_key="bronx",
        name="The Bronx",
        state="NY",
        display_label="The Bronx",
        center=[-73.8648, 40.8448],
        zoom=12.5,
        bounds=[[-73.934, 40.785], [-73.765, 40.916]],
        fortyguard_tiles_count=11,
        study_date="2024-07-15",
        study_window="Jul 15–21, 2024",
        description="South Bronx industrial-residential interface, freight corridors, and high heat-vulnerability census tracts.",
        key_neighborhoods=["Hunts Point", "Longwood", "Mott Haven", "Grand Concourse", "Riverdale"],
    ),
    "staten_island": CityConfig(
        city_key="staten_island",
        name="Staten Island",
        state="NY",
        display_label="Staten Island",
        center=[-74.1502, 40.5795],
        zoom=12.0,
        bounds=[[-74.256, 40.496], [-74.049, 40.649]],
        fortyguard_tiles_count=11,
        study_date="2024-07-15",
        study_window="Jul 15–21, 2024",
        description="Ferry transit terminals, maritime commercial corridors, and suburban/parkland interfaces across Staten Island.",
        key_neighborhoods=["St. George", "Stapleton", "Tottenville", "Mid-Island", "North Shore"],
    ),
    "hunts_point": CityConfig(
        city_key="hunts_point",
        name="Hunts Point / Longwood",
        state="NY",
        display_label="Hunts Point / Longwood (South Bronx)",
        center=[-73.8860, 40.8145],
        zoom=14.5,
        bounds=[[-73.900, 40.805], [-73.870, 40.825]],
        fortyguard_tiles_count=4,
        study_date="2024-07-15",
        study_window="Jul 15–21, 2024",
        description="Hyperlocal thermal screening across the Hunts Point Food Distribution Center and Longwood urban corridor.",
        key_neighborhoods=["Hunts Point Peninsula", "Southern Boulevard", "Barretto Waterfront"],
    ),
    "lower_manhattan": CityConfig(
        city_key="lower_manhattan",
        name="Lower Manhattan",
        state="NY",
        display_label="Lower Manhattan & Financial District",
        center=[-74.0080, 40.7120],
        zoom=14.5,
        bounds=[[-74.020, 40.700], [-73.970, 40.730]],
        fortyguard_tiles_count=3,
        study_date="2024-07-15",
        study_window="Jul 15–21, 2024",
        description="Dense canyon microclimates and heavy pedestrian transit corridors in Lower Manhattan.",
        key_neighborhoods=["Financial District", "Chinatown", "Fulton Center", "Battery Park"],
    ),
    "downtown_brooklyn": CityConfig(
        city_key="downtown_brooklyn",
        name="Downtown Brooklyn",
        state="NY",
        display_label="Downtown Brooklyn & DUMBO",
        center=[-73.9850, 40.6920],
        zoom=14.5,
        bounds=[[-74.000, 40.680], [-73.970, 40.710]],
        fortyguard_tiles_count=3,
        study_date="2024-07-15",
        study_window="Jul 15–21, 2024",
        description="Fulton Mall pedestrian district, Atlantic Terminal, and DUMBO waterfront microclimates.",
        key_neighborhoods=["Downtown Brooklyn", "Fulton Mall", "Atlantic Terminal", "DUMBO"],
    ),
    "flushing": CityConfig(
        city_key="flushing",
        name="Flushing / Corona",
        state="NY",
        display_label="Flushing & Corona (Queens)",
        center=[-73.8300, 40.7580],
        zoom=14.5,
        bounds=[[-73.855, 40.740], [-73.815, 40.770]],
        fortyguard_tiles_count=3,
        study_date="2024-07-15",
        study_window="Jul 15–21, 2024",
        description="High-density commercial core and multimodal transit hub in Northern Queens.",
        key_neighborhoods=["Flushing Main St", "Corona Plaza", "Flushing Meadows"],
    ),
    "jamaica": CityConfig(
        city_key="jamaica",
        name="Jamaica Hub",
        state="NY",
        display_label="Jamaica Hub & Archer Ave (Queens)",
        center=[-73.7990, 40.7025],
        zoom=14.5,
        bounds=[[-73.815, 40.690], [-73.780, 40.715]],
        fortyguard_tiles_count=3,
        study_date="2024-07-15",
        study_window="Jul 15–21, 2024",
        description="Major regional transit center (AirTrain, LIRR, Subways) with extensive asphalt bus aprons.",
        key_neighborhoods=["Jamaica Center", "Archer Ave Corridor", "Parsons Blvd"],
    ),
    "staten_island_north": CityConfig(
        city_key="staten_island_north",
        name="Staten Island North Shore",
        state="NY",
        display_label="Staten Island North Shore (St. George)",
        center=[-74.0780, 40.6430],
        zoom=14.5,
        bounds=[[-74.110, 40.630], [-74.070, 40.655]],
        fortyguard_tiles_count=3,
        study_date="2024-07-15",
        study_window="Jul 15–21, 2024",
        description="St. George Ferry Terminal transit corridor and Bay Street commercial district.",
        key_neighborhoods=["St. George Terminal", "Bay Street", "Stapleton"],
    ),
}

# Raw representative assets definitions across all 5 NYC boroughs
RAW_ASSETS: dict[str, list[dict[str, Any]]] = {
    "nyc": [
        # --- THE BRONX ---
        {
            "asset_id": "NYC-BX-TRN-01",
            "name": "Hunts Point Ave Station & Plaza (6 Train Transfer)",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.8209,
            "longitude": -73.8906,
            "footprint_m2": 2400.0,
            "daily_visitors": 8500,
            "vulnerability_weight": 1.6,
            "notes": "Major subway and South Bronx bus transfer hub on Southern Blvd with heavy transit rider dwell time and severe asphalt heat island exposure.",
        },
        {
            "asset_id": "NYC-BX-PLG-01",
            "name": "Barretto Point Waterfront Park & Play Area",
            "asset_type": AssetType.PLAYGROUND,
            "latitude": 40.8068,
            "longitude": -73.8824,
            "footprint_m2": 4500.0,
            "daily_visitors": 2100,
            "vulnerability_weight": 1.4,
            "notes": "Popular South Bronx waterfront recreation park on Tiffany St; exposed play equipment and limited canopy shelter during peak summer heat.",
        },
        {
            "asset_id": "NYC-BX-SCH-01",
            "name": "IS 131 Albert Einstein School & Community Yard",
            "asset_type": AssetType.SCHOOL,
            "latitude": 40.8235,
            "longitude": -73.8865,
            "footprint_m2": 3800.0,
            "daily_visitors": 950,
            "vulnerability_weight": 1.7,
            "notes": "Longwood middle school campus with extensive paved courtyard blacktop and high child vulnerability during midday activity.",
        },
        {
            "asset_id": "NYC-BX-COR-01",
            "name": "Southern Boulevard Commercial & Transit Corridor",
            "asset_type": AssetType.PEDESTRIAN_CORRIDOR,
            "latitude": 40.8220,
            "longitude": -73.8920,
            "footprint_m2": 6200.0,
            "daily_visitors": 9200,
            "vulnerability_weight": 1.3,
            "notes": "Dense commercial walking and shopping spine with heavy bus traffic, asphalt pavement, and zero tree cover.",
        },
        {
            "asset_id": "NYC-BX-CTR-01",
            "name": "The Point Community Development Center & Arts Yard",
            "asset_type": AssetType.COMMUNITY_CENTER,
            "latitude": 40.8182,
            "longitude": -73.8888,
            "footprint_m2": 2200.0,
            "daily_visitors": 1400,
            "vulnerability_weight": 1.5,
            "notes": "Vital community resilience and youth arts center on Garrison Ave; key cooling hub and climate justice anchor.",
        },
        {
            "asset_id": "NYC-BX-PLZ-01",
            "name": "Hunts Point Riverside Park Community Green & Pier",
            "asset_type": AssetType.PUBLIC_PLAZA,
            "latitude": 40.8175,
            "longitude": -73.8785,
            "footprint_m2": 3100.0,
            "daily_visitors": 1200,
            "vulnerability_weight": 1.2,
            "notes": "Bronx River community park converted from former illegal dumping site; prime candidate for shade canopy enhancement.",
        },
        {
            "asset_id": "NYC-BX-TRN-02",
            "name": "Southern Blvd & E 163rd St Bus Interchange (Bx6/Bx19)",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.8212,
            "longitude": -73.8932,
            "footprint_m2": 650.0,
            "daily_visitors": 3400,
            "vulnerability_weight": 1.5,
            "notes": "High-volume cross-Bronx bus connection with unshaded sidewalk curbs and elevated surface temperatures.",
        },
        {
            "asset_id": "NYC-BX-SCH-02",
            "name": "PS 48 Joseph R. Drake Elementary Courtyard",
            "asset_type": AssetType.SCHOOL,
            "latitude": 40.8160,
            "longitude": -73.8870,
            "footprint_m2": 3200.0,
            "daily_visitors": 780,
            "vulnerability_weight": 1.6,
            "notes": "Elementary school on Spofford Ave surrounded by food market freight routes; high ground-level particulate and heat retention.",
        },

        # --- MANHATTAN ---
        {
            "asset_id": "NYC-MN-TRN-01",
            "name": "Fulton Center & Broadway Transit Plaza (Lower Manhattan)",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.7110,
            "longitude": -74.0090,
            "footprint_m2": 3200.0,
            "daily_visitors": 18500,
            "vulnerability_weight": 1.4,
            "notes": "Major Downtown subway and bus interchange serving 9 subway lines; dense concrete and glass canyon with severe radiant heat loading.",
        },
        {
            "asset_id": "NYC-MN-COR-01",
            "name": "Canal Street Pedestrian & Retail Corridor (Chinatown)",
            "asset_type": AssetType.PEDESTRIAN_CORRIDOR,
            "latitude": 40.7180,
            "longitude": -73.9980,
            "footprint_m2": 7500.0,
            "daily_visitors": 14000,
            "vulnerability_weight": 1.5,
            "notes": "Heavily congested arterial connecting Manhattan and Brooklyn; high elderly pedestrian density and severe lack of vegetative shade.",
        },
        {
            "asset_id": "NYC-MN-PLZ-01",
            "name": "Herald Square & Broadway Pedestrian Plaza (Midtown)",
            "asset_type": AssetType.PUBLIC_PLAZA,
            "latitude": 40.7495,
            "longitude": -73.9880,
            "footprint_m2": 4800.0,
            "daily_visitors": 22000,
            "vulnerability_weight": 1.3,
            "notes": "High-foot-traffic midtown civic square on Broadway & 34th St with intense solar exposure and zero permanent canopy.",
        },
        {
            "asset_id": "NYC-MN-SCH-01",
            "name": "PS 125 Ralph Bunche School Community Blacktop (Harlem)",
            "asset_type": AssetType.SCHOOL,
            "latitude": 40.8105,
            "longitude": -73.9540,
            "footprint_m2": 3600.0,
            "daily_visitors": 820,
            "vulnerability_weight": 1.7,
            "notes": "Central Harlem elementary school courtyard with 100% asphalt surfacing and high heat vulnerability during summer youth activities.",
        },
        {
            "asset_id": "NYC-MN-PLG-01",
            "name": "Highbridge Park Youth Recreation Zone (Washington Heights)",
            "asset_type": AssetType.PLAYGROUND,
            "latitude": 40.8420,
            "longitude": -73.9310,
            "footprint_m2": 3900.0,
            "daily_visitors": 1900,
            "vulnerability_weight": 1.4,
            "notes": "Upper Manhattan park play area on Amsterdam Ave serving dense residential community; candidate for shade structure deployment.",
        },

        # --- BROOKLYN ---
        {
            "asset_id": "NYC-BK-TRN-01",
            "name": "Atlantic Ave - Barclays Center Transit Hub & Plaza",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.6845,
            "longitude": -73.9780,
            "footprint_m2": 5200.0,
            "daily_visitors": 26000,
            "vulnerability_weight": 1.4,
            "notes": "Brooklyn's largest transit nexus (LIRR and 10 subway lines); expansive concrete apron and heavy pedestrian transfer dwell times.",
        },
        {
            "asset_id": "NYC-BK-COR-01",
            "name": "Fulton Mall Pedestrian & Bus Transit Spine",
            "asset_type": AssetType.PEDESTRIAN_CORRIDOR,
            "latitude": 40.6905,
            "longitude": -73.9850,
            "footprint_m2": 8500.0,
            "daily_visitors": 19500,
            "vulnerability_weight": 1.4,
            "notes": "Busiest shopping and bus transit corridor in Brooklyn; unshaded asphalt and high afternoon thermal retention.",
        },
        {
            "asset_id": "NYC-BK-SCH-01",
            "name": "Boys & Girls High School Athletic Campus (Bed-Stuy)",
            "asset_type": AssetType.SCHOOL,
            "latitude": 40.6800,
            "longitude": -73.9360,
            "footprint_m2": 6200.0,
            "daily_visitors": 1400,
            "vulnerability_weight": 1.6,
            "notes": "Historic Bedford-Stuyvesant high school campus with expansive paved courts; priority for street trees and cool surface coatings.",
        },
        {
            "asset_id": "NYC-BK-PLG-01",
            "name": "Maria Hernandez Park Youth Play Area (Bushwick)",
            "asset_type": AssetType.PLAYGROUND,
            "latitude": 40.7030,
            "longitude": -73.9240,
            "footprint_m2": 4200.0,
            "daily_visitors": 2800,
            "vulnerability_weight": 1.5,
            "notes": "Central community park in Bushwick with high youth and family summer usage; exposed play zone with canopy deficits.",
        },
        {
            "asset_id": "NYC-BK-PLZ-01",
            "name": "Coney Island - Stillwell Ave Terminal Plaza",
            "asset_type": AssetType.PUBLIC_PLAZA,
            "latitude": 40.5770,
            "longitude": -73.9810,
            "footprint_m2": 4600.0,
            "daily_visitors": 16000,
            "vulnerability_weight": 1.3,
            "notes": "Southern Brooklyn transit terminal gateway with vast unshaded concrete sidewalks and heavy beachgoer summer volumes.",
        },

        # --- QUEENS ---
        {
            "asset_id": "NYC-QN-TRN-01",
            "name": "Flushing - Main Street 7 Train & Bus Terminal Hub",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.7595,
            "longitude": -73.8300,
            "footprint_m2": 4900.0,
            "daily_visitors": 24000,
            "vulnerability_weight": 1.5,
            "notes": "One of NYC's busiest transit hubs with 20+ bus lines; heavy pedestrian crowding, diesel exhaust, and intense urban heat island effect.",
        },
        {
            "asset_id": "NYC-QN-COR-01",
            "name": "Roosevelt Avenue Elevated Transit Corridor (Jackson Heights)",
            "asset_type": AssetType.PEDESTRIAN_CORRIDOR,
            "latitude": 40.7490,
            "longitude": -73.8910,
            "footprint_m2": 7800.0,
            "daily_visitors": 16500,
            "vulnerability_weight": 1.4,
            "notes": "Vibrant immigrant commercial corridor beneath the 7 train elevated structure; trapped vehicle heat and high ground surface exposure.",
        },
        {
            "asset_id": "NYC-QN-SCH-01",
            "name": "Queens High School of Teaching Athletic Yard (Glen Oaks)",
            "asset_type": AssetType.SCHOOL,
            "latitude": 40.7420,
            "longitude": -73.7150,
            "footprint_m2": 5800.0,
            "daily_visitors": 1100,
            "vulnerability_weight": 1.5,
            "notes": "Eastern Queens educational campus with wide asphalt walkways and exposed sports fields.",
        },
        {
            "asset_id": "NYC-QN-PLZ-01",
            "name": "Jamaica Center - Parsons/Archer Transit Plaza",
            "asset_type": AssetType.PUBLIC_PLAZA,
            "latitude": 40.7020,
            "longitude": -73.7995,
            "footprint_m2": 5400.0,
            "daily_visitors": 21000,
            "vulnerability_weight": 1.5,
            "notes": "Major Queens civic and commuter hub with extensive asphalt bus aprons; severe afternoon radiant heat load.",
        },
        {
            "asset_id": "NYC-QN-PLG-01",
            "name": "Travers Park Children's Play Space (Jackson Heights)",
            "asset_type": AssetType.PLAYGROUND,
            "latitude": 40.7530,
            "longitude": -73.8860,
            "footprint_m2": 3800.0,
            "daily_visitors": 3200,
            "vulnerability_weight": 1.5,
            "notes": "Densely populated Jackson Heights community park with high child activity and limited mature tree canopy.",
        },

        # --- STATEN ISLAND ---
        {
            "asset_id": "NYC-SI-TRN-01",
            "name": "St. George Ferry Terminal Bus Bays & Esplanade",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.6435,
            "longitude": -74.0740,
            "footprint_m2": 5100.0,
            "daily_visitors": 18000,
            "vulnerability_weight": 1.3,
            "notes": "Primary transit link between Staten Island and Manhattan; extensive unshaded concrete walkways and bus boarding platforms.",
        },
        {
            "asset_id": "NYC-SI-COR-01",
            "name": "Bay Street Maritime & Commercial Corridor",
            "asset_type": AssetType.PEDESTRIAN_CORRIDOR,
            "latitude": 40.6350,
            "longitude": -74.0760,
            "footprint_m2": 6500.0,
            "daily_visitors": 5800,
            "vulnerability_weight": 1.3,
            "notes": "North Shore waterfront connector with asphalt streetscape and high heat retention into late evening.",
        },
        {
            "asset_id": "NYC-SI-SCH-01",
            "name": "Curtis High School Open Courtyard & Quad",
            "asset_type": AssetType.SCHOOL,
            "latitude": 40.6450,
            "longitude": -74.0880,
            "footprint_m2": 4200.0,
            "daily_visitors": 1600,
            "vulnerability_weight": 1.5,
            "notes": "St. George high school campus with concrete steps and unshaded quad area.",
        },
        {
            "asset_id": "NYC-SI-PLG-01",
            "name": "Faber Park Waterfront Playground & Pool Plaza",
            "asset_type": AssetType.PLAYGROUND,
            "latitude": 40.6410,
            "longitude": -74.1380,
            "footprint_m2": 3600.0,
            "daily_visitors": 1500,
            "vulnerability_weight": 1.4,
            "notes": "Kill Van Kull waterfront park on Richmond Terrace; open recreational pool deck and exposed playground equipment.",
        },
    ],
}


@functools.lru_cache(maxsize=16)
def _load_city_heatmap_tiles(city_key: str = "nyc") -> list[dict[str, Any]]:
    """Load FortyGuard 100m grid tiles for New York City."""
    citywide_path = PROBES_DIR / "nyc_citywide_tcm.json"
    fallback_path = PROBES_DIR / "nyc_tcm_2024-07-15.json"

    path = citywide_path if citywide_path.exists() else fallback_path
    if not path.exists():
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return (data.get("result") or data).get("map_data", {}).get("features", [])
    except Exception:
        return []


@functools.lru_cache(maxsize=16)
def _load_city_tile_centroids(city_key: str = "nyc") -> list[tuple[float, float, dict[str, Any], int]]:
    """Pre-computed (avg_lng, avg_lat, tile, tile_idx) list for fast spatial distance lookup."""
    tiles = _load_city_heatmap_tiles(city_key)
    centroids: list[tuple[float, float, dict[str, Any], int]] = []
    for idx, t in enumerate(tiles):
        geom = t.get("geometry", {})
        coords = geom.get("coordinates", [])
        if not coords or not coords[0]:
            continue
        c_list = coords[0]
        n = len(c_list)
        avg_lng = sum(pt[0] for pt in c_list) / n
        avg_lat = sum(pt[1] for pt in c_list) / n
        centroids.append((avg_lng, avg_lat, t, idx))
    return centroids


@functools.lru_cache(maxsize=16)
def _load_city_exceedance_persistence(city_key: str = "nyc") -> tuple[dict[int, float], dict[int, float]]:
    """Load FortyGuard exceedance and persistence tiles mapping tile_idx -> value."""
    exc_map: dict[int, float] = {}
    per_map: dict[int, float] = {}

    exc_citywide = PROBES_DIR / "nyc_citywide_exceedance.json"
    exc_p = exc_citywide if exc_citywide.exists() else (PROBES_DIR / "nyc_exceedance_2024-07-15_2024-07-21.json")

    per_citywide = PROBES_DIR / "nyc_citywide_persistence.json"
    per_p = per_citywide if per_citywide.exists() else (PROBES_DIR / "nyc_persistence_2024-07-15_2024-07-21.json")

    if exc_p.exists():
        try:
            with open(exc_p, "r", encoding="utf-8") as f:
                d = json.load(f)
            feats = (d.get("result") or d).get("map_data", {}).get("features", [])
            for idx, ft in enumerate(feats):
                exc_map[idx] = float(ft.get("properties", {}).get("value", 0.0))
        except Exception:
            pass

    if per_p.exists():
        try:
            with open(per_p, "r", encoding="utf-8") as f:
                d = json.load(f)
            feats = (d.get("result") or d).get("map_data", {}).get("features", [])
            for idx, ft in enumerate(feats):
                per_map[idx] = float(ft.get("properties", {}).get("value", 0.0))
        except Exception:
            pass

    return exc_map, per_map


def _find_nearest_tile(
    lat: float,
    lng: float,
    tiles: list[dict[str, Any]],
) -> tuple[dict[str, Any], int]:
    """Find the closest FortyGuard 100m tile to a given coordinate."""
    if not tiles:
        return {}, -1

    best_dist = float("inf")
    best_tile = tiles[0]
    best_idx = 0

    for idx, t in enumerate(tiles):
        geom = t.get("geometry", {})
        coords = geom.get("coordinates", [])
        if not coords or not coords[0]:
            continue
        c_list = coords[0]
        avg_lng = sum(pt[0] for pt in c_list) / len(c_list)
        avg_lat = sum(pt[1] for pt in c_list) / len(c_list)

        d = math.hypot(avg_lng - lng, avg_lat - lat)
        if d < best_dist:
            best_dist = d
            best_tile = t
            best_idx = idx

    return best_tile, best_idx


def _find_nearest_tile_fast(
    lat: float,
    lng: float,
    centroids: list[tuple[float, float, dict[str, Any], int]],
) -> tuple[dict[str, Any], int]:
    """Find the closest FortyGuard 100m tile using pre-calculated polygon centroids."""
    if not centroids:
        return {}, -1

    best_dist = float("inf")
    best_tile = centroids[0][2]
    best_idx = centroids[0][3]

    for avg_lng, avg_lat, t, idx in centroids:
        dx = avg_lng - lng
        dy = avg_lat - lat
        d_sq = dx * dx + dy * dy
        if d_sq < best_dist:
            best_dist = d_sq
            best_tile = t
            best_idx = idx

    return best_tile, best_idx


@functools.lru_cache(maxsize=32)
def get_city_public_assets(city_key: str = "nyc") -> list[PublicAsset]:
    """Retrieve all public assets for a city enriched with observed FortyGuard microclimate data."""
    city_norm = city_key.lower().strip()
    raw_list = RAW_ASSETS.get(city_norm, RAW_ASSETS["nyc"])
    centroids = _load_city_tile_centroids(city_norm)
    exc_map, per_map = _load_city_exceedance_persistence(city_norm)

    enriched_assets: list[PublicAsset] = []

    for raw in raw_list:
        lat = raw["latitude"]
        lng = raw["longitude"]
        matched_tile, tile_idx = _find_nearest_tile_fast(lat, lng, centroids)
        t_props = matched_tile.get("properties", {}) if matched_tile else {}

        peak_c = float(t_props.get("max_temperature", t_props.get("temperature", 38.5)))
        mean_c = float(t_props.get("average_temperature", t_props.get("temperature", 32.0)))
        min_c = float(t_props.get("min_temperature", 26.5))

        exc_hrs = exc_map.get(tile_idx, 8.5 if peak_c > 38.0 else 4.0)
        per_hrs = per_map.get(tile_idx, 5.0 if peak_c > 38.0 else 2.5)

        # Baseline impervious & canopy based on asset type
        a_type = raw["asset_type"]
        if a_type == AssetType.BUS_STOP:
            imp_pct = 92.0
            can_pct = 3.0
            rec_interventions = [InterventionType.SHADE_STRUCTURE, InterventionType.TREE_CANOPY, InterventionType.COOL_PAVEMENT]
        elif a_type == AssetType.PLAYGROUND:
            imp_pct = 65.0
            can_pct = 8.0
            rec_interventions = [InterventionType.SHADE_STRUCTURE, InterventionType.TREE_CANOPY]
        elif a_type == AssetType.SCHOOL:
            imp_pct = 78.0
            can_pct = 6.0
            rec_interventions = [InterventionType.TREE_CANOPY, InterventionType.SHADE_STRUCTURE, InterventionType.COOL_ROOF]
        elif a_type == AssetType.PEDESTRIAN_CORRIDOR:
            imp_pct = 95.0
            can_pct = 4.0
            rec_interventions = [InterventionType.COOL_PAVEMENT, InterventionType.TREE_CANOPY]
        elif a_type == AssetType.PUBLIC_PLAZA:
            imp_pct = 88.0
            can_pct = 5.0
            rec_interventions = [InterventionType.SHADE_STRUCTURE, InterventionType.TREE_CANOPY, InterventionType.COOL_PAVEMENT]
        else:
            imp_pct = 80.0
            can_pct = 5.0
            rec_interventions = [InterventionType.TREE_CANOPY, InterventionType.SHADE_STRUCTURE]

        # Calculate composite heat risk score (0–100) adapted for NYC climate
        # Peak temp score (25 to 40°C -> 0 to 100)
        t_score = min(100.0, max(0.0, (peak_c - 25.0) / 15.0 * 100.0))
        # Overnight recovery score (22 to 30°C -> 0 to 100)
        m_score = min(100.0, max(0.0, (min_c - 22.0) / 8.0 * 100.0))
        # Exceedance score (0 to 15h -> 0 to 100)
        e_score = min(100.0, max(0.0, (exc_hrs / 15.0) * 100.0))
        # Vulnerability multiplier
        v_mult = raw.get("vulnerability_weight", 1.0)
        composite_score = round(min(100.0, max(5.0, (t_score * 0.45 + m_score * 0.25 + e_score * 0.30) * (0.7 + 0.3 * v_mult))), 1)

        if composite_score >= 80.0:
            risk_level = HeatRiskLevel.EXTREME
            priority_level = "Critical"
        elif composite_score >= 65.0:
            risk_level = HeatRiskLevel.SEVERE
            priority_level = "High"
        elif composite_score >= 50.0:
            risk_level = HeatRiskLevel.HIGH
            priority_level = "High"
        elif composite_score >= 35.0:
            risk_level = HeatRiskLevel.MODERATE
            priority_level = "Moderate"
        else:
            risk_level = HeatRiskLevel.LOW
            priority_level = "Moderate"

        # Transparent multi-factor prioritization reasons
        priority_reasons: list[str] = []
        if peak_c >= 38.5:
            priority_reasons.append(f"Critical afternoon thermal load ({peak_c:.1f}°C peak ambient exposure)")
        elif peak_c >= 34.5:
            priority_reasons.append(f"Elevated daytime heat exposure ({peak_c:.1f}°C peak ambient)")

        if min_c >= 26.5:
            priority_reasons.append(f"Poor overnight cooling recovery ({min_c:.1f}°C overnight minimum)")
        elif min_c >= 24.5:
            priority_reasons.append(f"Limited overnight cooling recovery ({min_c:.1f}°C minimum)")

        if exc_hrs >= 6.0:
            priority_reasons.append(f"Extended extreme heat duration ({exc_hrs:.1f} cumulative hours exceeding 35°C)")
        elif exc_hrs >= 3.0:
            priority_reasons.append(f"Recurrent heatwave exceedance ({exc_hrs:.1f} hours > 35°C)")

        if raw.get("daily_visitors", 0) >= 2000:
            priority_reasons.append(f"High public exposure (~{raw.get('daily_visitors', 0):,} daily transit & pedestrian users)")
        elif raw.get("daily_visitors", 0) >= 500:
            priority_reasons.append(f"Substantial community usage (~{raw.get('daily_visitors', 0):,} daily visitors)")

        if can_pct <= 6.0 and imp_pct >= 75.0:
            priority_reasons.append(f"Severe canopy deficit ({can_pct:.0f}% canopy vs {imp_pct:.0f}% impervious surface)")
        elif can_pct <= 10.0:
            priority_reasons.append(f"Low vegetative canopy coverage ({can_pct:.0f}%)")

        obs = ObservedHeatMetrics(
            peak_temperature_c=round(peak_c, 2),
            peak_temperature_f=round(peak_c * 9.0 / 5.0 + 32.0, 1),
            mean_temperature_c=round(mean_c, 2),
            mean_temperature_f=round(mean_c * 9.0 / 5.0 + 32.0, 1),
            overnight_min_c=round(min_c, 2),
            overnight_min_f=round(min_c * 9.0 / 5.0 + 32.0, 1),
            hours_above_35c=round(exc_hrs, 1),
            persistence_hours=round(per_hrs, 1),
            impervious_pct=imp_pct,
            canopy_pct=can_pct,
            contributing_tile_id=tile_idx,
        )

        geom = {
            "type": "Point",
            "coordinates": [lng, lat],
        }

        enriched_assets.append(
            PublicAsset(
                asset_id=raw["asset_id"],
                name=raw["name"],
                asset_type=raw["asset_type"],
                city=CITY_CONFIGS.get(city_norm, CITY_CONFIGS["nyc"]).name,
                latitude=lat,
                longitude=lng,
                geometry=geom,
                footprint_m2=raw.get("footprint_m2", 1000.0),
                daily_visitors=raw.get("daily_visitors", 500),
                vulnerability_weight=v_mult,
                heat_risk_level=risk_level,
                heat_risk_score=composite_score,
                priority_level=priority_level,
                priority_reasons=priority_reasons,
                observed_heat=obs,
                recommended_interventions=rec_interventions,
                notes=raw.get("notes"),
            )
        )

    # Sort assets by composite heat risk score descending
    enriched_assets.sort(key=lambda a: a.heat_risk_score, reverse=True)
    for idx, asset in enumerate(enriched_assets):
        asset.observed_heat.hotspot_rank = idx + 1

    return enriched_assets


def get_public_asset_by_id(asset_id: str, city_key: str = "nyc") -> PublicAsset | None:
    """Retrieve a single public asset by ID."""
    assets = get_city_public_assets(city_key)
    for a in assets:
        if a.asset_id == asset_id:
            return a
    # Fallback search across other cities
    for c_k in CITY_CONFIGS.keys():
        if c_k == city_key.lower():
            continue
        for a in get_city_public_assets(c_k):
            if a.asset_id == asset_id:
                return a
    return None

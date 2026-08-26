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
            "latitude": 40.822,
            "longitude": -73.892,
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
            "latitude": 40.816,
            "longitude": -73.887,
            "footprint_m2": 3200.0,
            "daily_visitors": 780,
            "vulnerability_weight": 1.6,
            "notes": "Elementary school on Spofford Ave surrounded by food market freight routes; high ground-level particulate and heat retention.",
        },
        {
            "asset_id": "NYC-BX-TRN-03",
            "name": "Fordham Plaza Regional Transit & Metro-North Hub",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.8617,
            "longitude": -73.8908,
            "footprint_m2": 5800.0,
            "daily_visitors": 28000,
            "vulnerability_weight": 1.5,
            "notes": "Major central Bronx multimodal transit interchange connecting 12 bus routes, Metro-North, and Fordham University pedestrian traffic.",
        },
        {
            "asset_id": "NYC-BX-TRN-04",
            "name": "3rd Ave - 149th St Hub Subway & SBS Bus Interchange",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.8162,
            "longitude": -73.9178,
            "footprint_m2": 4200.0,
            "daily_visitors": 22500,
            "vulnerability_weight": 1.5,
            "notes": "Heart of The Hub commercial center in South Bronx; heavy transfer volume between 2/5 trains and Bx41 Select Bus Service.",
        },
        {
            "asset_id": "NYC-BX-TRN-05",
            "name": "Grand Concourse & E 161st St Transit Island (Bx6 SBS)",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.8278,
            "longitude": -73.9255,
            "footprint_m2": 3600.0,
            "daily_visitors": 17000,
            "vulnerability_weight": 1.4,
            "notes": "Civic center transit nexus outside Bronx County Hall and Yankee Stadium with wide unshaded concrete medians.",
        },
        {
            "asset_id": "NYC-BX-TRN-06",
            "name": "Pelham Bay Park 6 Train Terminal & Orchard Beach Bus Apron",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.8526,
            "longitude": -73.8278,
            "footprint_m2": 5100.0,
            "daily_visitors": 14500,
            "vulnerability_weight": 1.3,
            "notes": "Northern 6 train terminal and major transfer point to City Island and Orchard Beach buses with vast asphalt boarding bays.",
        },
        {
            "asset_id": "NYC-BX-TRN-07",
            "name": "Broadway & W 231st St 1 Train Elevated Transit Plaza",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.8788,
            "longitude": -73.9048,
            "footprint_m2": 3100.0,
            "daily_visitors": 12000,
            "vulnerability_weight": 1.3,
            "notes": "Kingsbridge commercial corridor beneath the elevated 1 train with vehicle exhaust heat entrapment and dark pavement.",
        },
        {
            "asset_id": "NYC-BX-SCH-03",
            "name": "Bronx High School of Science Outdoor Academic Quad",
            "asset_type": AssetType.SCHOOL,
            "latitude": 40.8778,
            "longitude": -73.8895,
            "footprint_m2": 6500.0,
            "daily_visitors": 3200,
            "vulnerability_weight": 1.3,
            "notes": "Specialized high school campus on W 205th St with wide paved courtyards and exposed athletic fields.",
        },
        {
            "asset_id": "NYC-BX-SCH-04",
            "name": "PS 30 Wilton Elementary School Courtyard (Mott Haven)",
            "asset_type": AssetType.SCHOOL,
            "latitude": 40.8105,
            "longitude": -73.918,
            "footprint_m2": 3400.0,
            "daily_visitors": 850,
            "vulnerability_weight": 1.7,
            "notes": "South Bronx elementary school adjacent to Major Deegan Expressway; high particulate and heat retention.",
        },
        {
            "asset_id": "NYC-BX-SCH-05",
            "name": "Herbert H. Lehman High School Athletics Blacktop",
            "asset_type": AssetType.SCHOOL,
            "latitude": 40.8415,
            "longitude": -73.842,
            "footprint_m2": 7200.0,
            "daily_visitors": 2400,
            "vulnerability_weight": 1.5,
            "notes": "Large East Bronx high school complex near Westchester Square with extensive unshaded asphalt sports courts.",
        },
        {
            "asset_id": "NYC-BX-SCH-06",
            "name": "PS 69 Journey Prep School Yard (Soundview)",
            "asset_type": AssetType.SCHOOL,
            "latitude": 40.825,
            "longitude": -73.868,
            "footprint_m2": 3900.0,
            "daily_visitors": 920,
            "vulnerability_weight": 1.6,
            "notes": "Soundview elementary school courtyard with 100% asphalt surfacing and high youth heat vulnerability.",
        },
        {
            "asset_id": "NYC-BX-SCH-07",
            "name": "Morris High School Historic Campus Quad (Morrisania)",
            "asset_type": AssetType.SCHOOL,
            "latitude": 40.8285,
            "longitude": -73.904,
            "footprint_m2": 5200.0,
            "daily_visitors": 1800,
            "vulnerability_weight": 1.6,
            "notes": "Historic collegiate gothic high school campus on Boston Rd with wide masonry steps and unshaded brick plazas.",
        },
        {
            "asset_id": "NYC-BX-PLG-02",
            "name": "St. Mary's Park Central Playground & Splash Zone (Mott Haven)",
            "asset_type": AssetType.PLAYGROUND,
            "latitude": 40.8125,
            "longitude": -73.912,
            "footprint_m2": 4800.0,
            "daily_visitors": 3500,
            "vulnerability_weight": 1.5,
            "notes": "Largest public park in the South Bronx; heavily utilized play area with intense afternoon radiant heat on rubber play surfacing.",
        },
        {
            "asset_id": "NYC-BX-PLG-03",
            "name": "Mullaly Park Youth Skate & Adventure Playground",
            "asset_type": AssetType.PLAYGROUND,
            "latitude": 40.832,
            "longitude": -73.924,
            "footprint_m2": 4200.0,
            "daily_visitors": 2400,
            "vulnerability_weight": 1.4,
            "notes": "High Bronx youth activity hub adjacent to Yankee Stadium with exposed concrete skate bowls and play structures.",
        },
        {
            "asset_id": "NYC-BX-PLG-04",
            "name": "Soundview Park Central Play Area & Sports Courts",
            "asset_type": AssetType.PLAYGROUND,
            "latitude": 40.816,
            "longitude": -73.864,
            "footprint_m2": 5600.0,
            "daily_visitors": 2900,
            "vulnerability_weight": 1.4,
            "notes": "Bronx River mouth park serving Soundview and Clason Point; wide exposed synthetic turf and asphalt courts.",
        },
        {
            "asset_id": "NYC-BX-PLG-05",
            "name": "Crotona Park Indian Lake Playground & Youth Pavilion",
            "asset_type": AssetType.PLAYGROUND,
            "latitude": 40.84,
            "longitude": -73.892,
            "footprint_m2": 4900.0,
            "daily_visitors": 3100,
            "vulnerability_weight": 1.5,
            "notes": "Central Bronx community play space with large unshaded play equipment and open paved picnic aprons.",
        },
        {
            "asset_id": "NYC-BX-PLZ-02",
            "name": "Roberto Clemente State Park Waterfront Esplanade",
            "asset_type": AssetType.PUBLIC_PLAZA,
            "latitude": 40.852,
            "longitude": -73.921,
            "footprint_m2": 6200.0,
            "daily_visitors": 4500,
            "vulnerability_weight": 1.3,
            "notes": "Harlem River waterfront park esplanade in Morris Heights with wide concrete plazas and high direct sun exposure.",
        },
        {
            "asset_id": "NYC-BX-PLZ-03",
            "name": "Poe Park Visitor Center & Historic Lawn Plaza",
            "asset_type": AssetType.PUBLIC_PLAZA,
            "latitude": 40.8635,
            "longitude": -73.895,
            "footprint_m2": 3800.0,
            "daily_visitors": 2200,
            "vulnerability_weight": 1.3,
            "notes": "Grand Concourse historic civic plaza and community gallery forecourt with heavy senior citizen dwell time.",
        },
        {
            "asset_id": "NYC-BX-PLZ-04",
            "name": "Concrete Plant Park Bronx River Pier & Public Green",
            "asset_type": AssetType.PUBLIC_PLAZA,
            "latitude": 40.828,
            "longitude": -73.884,
            "footprint_m2": 4100.0,
            "daily_visitors": 1900,
            "vulnerability_weight": 1.3,
            "notes": "Adaptive reuse waterfront park along Westchester Ave; industrial concrete remnants amplify local microclimate heat.",
        },
        {
            "asset_id": "NYC-BX-COR-02",
            "name": "Grand Concourse Civic Boulevard (E 166th to E 170th St)",
            "asset_type": AssetType.PEDESTRIAN_CORRIDOR,
            "latitude": 40.835,
            "longitude": -73.918,
            "footprint_m2": 9500.0,
            "daily_visitors": 16500,
            "vulnerability_weight": 1.4,
            "notes": "Iconic Art Deco residential boulevard with wide multi-lane asphalt roadway and limited street tree shading.",
        },
        {
            "asset_id": "NYC-BX-COR-03",
            "name": "East Tremont Avenue Commercial & Shopping Spine",
            "asset_type": AssetType.PEDESTRIAN_CORRIDOR,
            "latitude": 40.844,
            "longitude": -73.889,
            "footprint_m2": 7800.0,
            "daily_visitors": 13000,
            "vulnerability_weight": 1.4,
            "notes": "Bustling retail strip in West Farms / Tremont with narrow sidewalks, high vehicle density, and zero vegetative canopy.",
        },
        {
            "asset_id": "NYC-BX-CTR-02",
            "name": "Casita Maria Center for Arts & Education (Simpson St)",
            "asset_type": AssetType.COMMUNITY_CENTER,
            "latitude": 40.821,
            "longitude": -73.892,
            "footprint_m2": 2800.0,
            "daily_visitors": 1600,
            "vulnerability_weight": 1.6,
            "notes": "Historic South Bronx community resilience hub providing youth arts and cooling center refuge during heat emergencies.",
        },
        {
            "asset_id": "NYC-MN-TRN-01",
            "name": "Fulton Center & Broadway Transit Plaza (Lower Manhattan)",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.711,
            "longitude": -74.009,
            "footprint_m2": 3200.0,
            "daily_visitors": 18500,
            "vulnerability_weight": 1.4,
            "notes": "Major Downtown subway and bus interchange serving 9 subway lines; dense concrete and glass canyon with severe radiant heat loading.",
        },
        {
            "asset_id": "NYC-MN-COR-01",
            "name": "Canal Street Pedestrian & Retail Corridor (Chinatown)",
            "asset_type": AssetType.PEDESTRIAN_CORRIDOR,
            "latitude": 40.718,
            "longitude": -73.998,
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
            "longitude": -73.988,
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
            "longitude": -73.954,
            "footprint_m2": 3600.0,
            "daily_visitors": 820,
            "vulnerability_weight": 1.7,
            "notes": "Central Harlem elementary school courtyard with 100% asphalt surfacing and high heat vulnerability during summer youth activities.",
        },
        {
            "asset_id": "NYC-MN-PLG-01",
            "name": "Highbridge Park Youth Recreation Zone (Washington Heights)",
            "asset_type": AssetType.PLAYGROUND,
            "latitude": 40.842,
            "longitude": -73.931,
            "footprint_m2": 3900.0,
            "daily_visitors": 1900,
            "vulnerability_weight": 1.4,
            "notes": "Upper Manhattan park play area on Amsterdam Ave serving dense residential community; candidate for shade structure deployment.",
        },
        {
            "asset_id": "NYC-MN-TRN-02",
            "name": "125th St & St. Nicholas Ave Subway & M60 SBS Plaza",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.811,
            "longitude": -73.9525,
            "footprint_m2": 3800.0,
            "daily_visitors": 24000,
            "vulnerability_weight": 1.5,
            "notes": "West Harlem express transit hub connecting A/B/C/D subways with airport SBS buses; wide open concrete intersections.",
        },
        {
            "asset_id": "NYC-MN-TRN-03",
            "name": "Port Authority Bus Terminal 8th Ave Mid-Block Plaza",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.757,
            "longitude": -73.9905,
            "footprint_m2": 4500.0,
            "daily_visitors": 32000,
            "vulnerability_weight": 1.3,
            "notes": "Busiest interstate bus terminal in the world with severe asphalt radiation and constant idling bus heat output.",
        },
        {
            "asset_id": "NYC-MN-TRN-04",
            "name": "14th St - Union Square North Pedestrian Island",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.736,
            "longitude": -73.9905,
            "footprint_m2": 5200.0,
            "daily_visitors": 29000,
            "vulnerability_weight": 1.3,
            "notes": "Multimodal transit hub connecting 8 subway lines and 14th St busway; high pedestrian dwell times with unshaded stone paving.",
        },
        {
            "asset_id": "NYC-MN-TRN-05",
            "name": "96th St & 2nd Ave Q Train Terminal Pedestrian Island",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.7845,
            "longitude": -73.9485,
            "footprint_m2": 3400.0,
            "daily_visitors": 16000,
            "vulnerability_weight": 1.3,
            "notes": "Upper East Side / Yorkville Second Ave Subway terminal with concrete sidewalk bulb-outs and direct solar exposure.",
        },
        {
            "asset_id": "NYC-MN-TRN-06",
            "name": "George Washington Bridge Bus Station 179th St Plaza",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.849,
            "longitude": -73.937,
            "footprint_m2": 4100.0,
            "daily_visitors": 18000,
            "vulnerability_weight": 1.4,
            "notes": "Washington Heights regional transit portal over the I-95 expressway canyon; high radiant surface heat from highway traffic.",
        },
        {
            "asset_id": "NYC-MN-SCH-02",
            "name": "PS 180 Hugo Newman Prep Playground Courtyard",
            "asset_type": AssetType.SCHOOL,
            "latitude": 40.806,
            "longitude": -73.957,
            "footprint_m2": 3200.0,
            "daily_visitors": 780,
            "vulnerability_weight": 1.6,
            "notes": "Morningside / South Harlem elementary school yard with unshaded dark asphalt courts.",
        },
        {
            "asset_id": "NYC-MN-SCH-03",
            "name": "Murry Bergtraum High School Urban Blacktop (FiDi)",
            "asset_type": AssetType.SCHOOL,
            "latitude": 40.7125,
            "longitude": -74.0,
            "footprint_m2": 4600.0,
            "daily_visitors": 1400,
            "vulnerability_weight": 1.5,
            "notes": "Lower Manhattan high school courtyard situated beneath the Brooklyn Bridge ramps with heavy asphalt heat absorption.",
        },
        {
            "asset_id": "NYC-MN-SCH-04",
            "name": "PS 188 The Island School Courtyard (Lower East Side)",
            "asset_type": AssetType.SCHOOL,
            "latitude": 40.7195,
            "longitude": -73.978,
            "footprint_m2": 3700.0,
            "daily_visitors": 890,
            "vulnerability_weight": 1.7,
            "notes": "East Houston St campus in Baruch Houses NYCHA complex; high youth vulnerability and lack of mature canopy.",
        },
        {
            "asset_id": "NYC-MN-SCH-05",
            "name": "Wadleigh Secondary School Courtyard (Central Harlem)",
            "asset_type": AssetType.SCHOOL,
            "latitude": 40.8025,
            "longitude": -73.9535,
            "footprint_m2": 3300.0,
            "daily_visitors": 820,
            "vulnerability_weight": 1.6,
            "notes": "Historic 114th St secondary school with enclosed paved courtyard trapping midday solar radiation.",
        },
        {
            "asset_id": "NYC-MN-PLG-02",
            "name": "Seward Park Central Playground & Sprayground (LES)",
            "asset_type": AssetType.PLAYGROUND,
            "latitude": 40.715,
            "longitude": -73.989,
            "footprint_m2": 4400.0,
            "daily_visitors": 3600,
            "vulnerability_weight": 1.5,
            "notes": "America's first municipal playground on Essex St; high family usage, asphalt game courts, and heat-absorbing rubber tile pads.",
        },
        {
            "asset_id": "NYC-MN-PLG-03",
            "name": "Marcus Garvey Park Amphitheater & Youth Play Yard",
            "asset_type": AssetType.PLAYGROUND,
            "latitude": 40.8055,
            "longitude": -73.943,
            "footprint_m2": 4900.0,
            "daily_visitors": 3800,
            "vulnerability_weight": 1.5,
            "notes": "Historic Mount Morris Park recreation core with intense afternoon sun exposure along 122nd St.",
        },
        {
            "asset_id": "NYC-MN-PLG-04",
            "name": "Thomas Jefferson Park Playground & Outdoor Pool Deck",
            "asset_type": AssetType.PLAYGROUND,
            "latitude": 40.793,
            "longitude": -73.937,
            "footprint_m2": 5800.0,
            "daily_visitors": 4200,
            "vulnerability_weight": 1.6,
            "notes": "East Harlem community recreation center with wide concrete pool promenade and heavily utilized youth play courts.",
        },
        {
            "asset_id": "NYC-MN-PLG-05",
            "name": "Jacob Schiff Playground & Sports Courts (Hamilton Heights)",
            "asset_type": AssetType.PLAYGROUND,
            "latitude": 40.8215,
            "longitude": -73.952,
            "footprint_m2": 4100.0,
            "daily_visitors": 2600,
            "vulnerability_weight": 1.5,
            "notes": "Amsterdam Ave play space serving Hamilton Heights families with high asphalt fraction.",
        },
        {
            "asset_id": "NYC-MN-PLZ-02",
            "name": "Chatham Square & Kimlau War Memorial Plaza (Chinatown)",
            "asset_type": AssetType.PUBLIC_PLAZA,
            "latitude": 40.7135,
            "longitude": -73.9985,
            "footprint_m2": 3900.0,
            "daily_visitors": 16000,
            "vulnerability_weight": 1.5,
            "notes": "Major multi-legged intersection connecting East Broadway, Bowery, and Park Row with high senior citizen pedestrian volumes.",
        },
        {
            "asset_id": "NYC-MN-PLZ-03",
            "name": "La Marqueta Open Public Market Plaza (East Harlem)",
            "asset_type": AssetType.PUBLIC_PLAZA,
            "latitude": 40.7985,
            "longitude": -73.9435,
            "footprint_m2": 4300.0,
            "daily_visitors": 8500,
            "vulnerability_weight": 1.5,
            "notes": "Under-viaduct public market along Park Ave at 115th St; concrete plaza and elevated train structure heat trap.",
        },
        {
            "asset_id": "NYC-MN-PLZ-04",
            "name": "Times Square Pedestrian Plazas & Broadway Islands",
            "asset_type": AssetType.PUBLIC_PLAZA,
            "latitude": 40.758,
            "longitude": -73.9855,
            "footprint_m2": 7200.0,
            "daily_visitors": 45000,
            "vulnerability_weight": 1.2,
            "notes": "World's most visited pedestrian space (Broadway 43rd\u201347th); expansive granite paving and digital screen radiant heat.",
        },
        {
            "asset_id": "NYC-MN-COR-02",
            "name": "125th Street Martin Luther King Jr Blvd Retail Corridor",
            "asset_type": AssetType.PEDESTRIAN_CORRIDOR,
            "latitude": 40.808,
            "longitude": -73.947,
            "footprint_m2": 11000.0,
            "daily_visitors": 28000,
            "vulnerability_weight": 1.4,
            "notes": "Primary commercial, cultural, and transit corridor across Upper Manhattan with high sidewalk pedestrian densities.",
        },
        {
            "asset_id": "NYC-MN-COR-03",
            "name": "St. Nicholas Avenue Commercial Spine (181st St)",
            "asset_type": AssetType.PEDESTRIAN_CORRIDOR,
            "latitude": 40.8505,
            "longitude": -73.934,
            "footprint_m2": 8200.0,
            "daily_visitors": 19000,
            "vulnerability_weight": 1.5,
            "notes": "Washington Heights central shopping district with dense sidewalk fruit stands, transit crowds, and narrow unshaded avenues.",
        },
        {
            "asset_id": "NYC-MN-CTR-01",
            "name": "Educational Alliance Manny Cantor Center Plaza (LES)",
            "asset_type": AssetType.COMMUNITY_CENTER,
            "latitude": 40.7145,
            "longitude": -73.988,
            "footprint_m2": 2600.0,
            "daily_visitors": 1800,
            "vulnerability_weight": 1.6,
            "notes": "Major community anchor on East Broadway serving multi-generational immigrants and acting as primary heat relief hub.",
        },
        {
            "asset_id": "NYC-BK-TRN-01",
            "name": "Atlantic Ave - Barclays Center Transit Hub & Plaza",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.6845,
            "longitude": -73.978,
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
            "longitude": -73.985,
            "footprint_m2": 8500.0,
            "daily_visitors": 19500,
            "vulnerability_weight": 1.4,
            "notes": "Busiest shopping and bus transit corridor in Brooklyn; unshaded asphalt and high afternoon thermal retention.",
        },
        {
            "asset_id": "NYC-BK-SCH-01",
            "name": "Boys & Girls High School Athletic Campus (Bed-Stuy)",
            "asset_type": AssetType.SCHOOL,
            "latitude": 40.68,
            "longitude": -73.936,
            "footprint_m2": 6200.0,
            "daily_visitors": 1400,
            "vulnerability_weight": 1.6,
            "notes": "Historic Bedford-Stuyvesant high school campus with expansive paved courts; priority for street trees and cool surface coatings.",
        },
        {
            "asset_id": "NYC-BK-PLG-01",
            "name": "Maria Hernandez Park Youth Play Area (Bushwick)",
            "asset_type": AssetType.PLAYGROUND,
            "latitude": 40.703,
            "longitude": -73.924,
            "footprint_m2": 4200.0,
            "daily_visitors": 2800,
            "vulnerability_weight": 1.5,
            "notes": "Central community park in Bushwick with high youth and family summer usage; exposed play zone with canopy deficits.",
        },
        {
            "asset_id": "NYC-BK-PLZ-01",
            "name": "Coney Island - Stillwell Ave Terminal Plaza",
            "asset_type": AssetType.PUBLIC_PLAZA,
            "latitude": 40.577,
            "longitude": -73.981,
            "footprint_m2": 4600.0,
            "daily_visitors": 16000,
            "vulnerability_weight": 1.3,
            "notes": "Southern Brooklyn transit terminal gateway with vast unshaded concrete sidewalks and heavy beachgoer summer volumes.",
        },
        {
            "asset_id": "NYC-BK-TRN-02",
            "name": "Broadway Junction Regional Transit Complex (East NY)",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.6785,
            "longitude": -73.9035,
            "footprint_m2": 6400.0,
            "daily_visitors": 28500,
            "vulnerability_weight": 1.6,
            "notes": "Critical multi-level transit nexus (A/C/J/Z/L) with sprawling exposed elevated metal structures and asphalt bus terminals.",
        },
        {
            "asset_id": "NYC-BK-TRN-03",
            "name": "Jay St - MetroTech Subway & Bus Transit Island",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.6925,
            "longitude": -73.987,
            "footprint_m2": 4100.0,
            "daily_visitors": 23000,
            "vulnerability_weight": 1.3,
            "notes": "Downtown Brooklyn university and civic core transit hub with high student and commuter waiting volumes.",
        },
        {
            "asset_id": "NYC-BK-TRN-04",
            "name": "Church Ave & Nostrand Ave B44 SBS Bus Transfer Hub",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.6505,
            "longitude": -73.9495,
            "footprint_m2": 3200.0,
            "daily_visitors": 18000,
            "vulnerability_weight": 1.5,
            "notes": "High-density Caribbean commercial and bus transfer intersection in Flatbush with wide sun-baked asphalt curbs.",
        },
        {
            "asset_id": "NYC-BK-TRN-05",
            "name": "Myrtle - Wyckoff Aves Transit Plaza (Bushwick)",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.6995,
            "longitude": -73.911,
            "footprint_m2": 3700.0,
            "daily_visitors": 21000,
            "vulnerability_weight": 1.5,
            "notes": "Busy L/M train transfer station and pedestrianized plaza with high summer radiant surface heat.",
        },
        {
            "asset_id": "NYC-BK-TRN-06",
            "name": "Utica Ave & Eastern Parkway 3/4 Subway Plaza (Crown Heights)",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.6695,
            "longitude": -73.9305,
            "footprint_m2": 3900.0,
            "daily_visitors": 19500,
            "vulnerability_weight": 1.5,
            "notes": "Major Eastern Parkway subway terminal connecting B46 Select Bus Service with heavy commuter dwell time.",
        },
        {
            "asset_id": "NYC-BK-TRN-07",
            "name": "8th Ave & 60th St N Train Station Plaza (Sunset Park)",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.635,
            "longitude": -74.011,
            "footprint_m2": 3300.0,
            "daily_visitors": 17500,
            "vulnerability_weight": 1.4,
            "notes": "Brooklyn Chinatown open transit cutting and pedestrian portal on 8th Ave with dense street commerce.",
        },
        {
            "asset_id": "NYC-BK-TRN-08",
            "name": "Flatbush Ave - Brooklyn College 2/5 Subway Terminal",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.6325,
            "longitude": -73.9475,
            "footprint_m2": 4500.0,
            "daily_visitors": 22000,
            "vulnerability_weight": 1.4,
            "notes": "The Junction commercial hub with 6 connecting bus routes and heavy college and high school student foot traffic.",
        },
        {
            "asset_id": "NYC-BK-SCH-02",
            "name": "Brooklyn Technical High School Forecourt (Fort Greene)",
            "asset_type": AssetType.SCHOOL,
            "latitude": 40.689,
            "longitude": -73.977,
            "footprint_m2": 5400.0,
            "daily_visitors": 6200,
            "vulnerability_weight": 1.3,
            "notes": "Largest specialized high school building in NYC with wide concrete steps and unshaded brick plazas.",
        },
        {
            "asset_id": "NYC-BK-SCH-03",
            "name": "PS 19 Roberto Clemente School Yard (South Williamsburg)",
            "asset_type": AssetType.SCHOOL,
            "latitude": 40.71,
            "longitude": -73.96,
            "footprint_m2": 3600.0,
            "daily_visitors": 840,
            "vulnerability_weight": 1.6,
            "notes": "South 9th St elementary school with 100% asphalt surfacing adjacent to the Williamsburg Bridge approach.",
        },
        {
            "asset_id": "NYC-BK-SCH-04",
            "name": "Erasmus Hall High School Quad & Blacktop (Flatbush)",
            "asset_type": AssetType.SCHOOL,
            "latitude": 40.65,
            "longitude": -73.958,
            "footprint_m2": 6800.0,
            "daily_visitors": 2100,
            "vulnerability_weight": 1.6,
            "notes": "Historic Flatbush educational campus with large asphalt recreation courts and high heat retention.",
        },
        {
            "asset_id": "NYC-BK-SCH-05",
            "name": "PS 298 Dr. Betty Shabazz School Courtyard (Brownsville)",
            "asset_type": AssetType.SCHOOL,
            "latitude": 40.67,
            "longitude": -73.91,
            "footprint_m2": 3900.0,
            "daily_visitors": 780,
            "vulnerability_weight": 1.8,
            "notes": "Central Brownsville school campus in a high heat vulnerability census tract with zero courtyard tree canopy.",
        },
        {
            "asset_id": "NYC-BK-SCH-06",
            "name": "PS 94 Henry Longfellow School Courtyard (Sunset Park)",
            "asset_type": AssetType.SCHOOL,
            "latitude": 40.642,
            "longitude": -74.012,
            "footprint_m2": 3500.0,
            "daily_visitors": 960,
            "vulnerability_weight": 1.6,
            "notes": "6th Ave elementary school serving Sunset Park youth; unshaded blacktop play yard.",
        },
        {
            "asset_id": "NYC-BK-SCH-07",
            "name": "Thomas Jefferson High School Campus Yard (East New York)",
            "asset_type": AssetType.SCHOOL,
            "latitude": 40.666,
            "longitude": -73.89,
            "footprint_m2": 7400.0,
            "daily_visitors": 1600,
            "vulnerability_weight": 1.7,
            "notes": "Sprawling East New York educational complex with wide unshaded asphalt running track and play areas.",
        },
        {
            "asset_id": "NYC-BK-SCH-08",
            "name": "PS 273 Jerome School Play Yard (Wortman Ave / East NY)",
            "asset_type": AssetType.SCHOOL,
            "latitude": 40.658,
            "longitude": -73.878,
            "footprint_m2": 3300.0,
            "daily_visitors": 690,
            "vulnerability_weight": 1.7,
            "notes": "Lower East New York elementary school yard with direct sun exposure throughout midday.",
        },
        {
            "asset_id": "NYC-BK-PLG-02",
            "name": "Betsy Head Park Youth Play & Pool Complex (Brownsville)",
            "asset_type": AssetType.PLAYGROUND,
            "latitude": 40.664,
            "longitude": -73.912,
            "footprint_m2": 6800.0,
            "daily_visitors": 4100,
            "vulnerability_weight": 1.7,
            "notes": "Major Brownsville regional park with heavily utilized Olympic pool deck, skate park, and exposed turf fields.",
        },
        {
            "asset_id": "NYC-BK-PLG-03",
            "name": "Sunset Park Playground & Olympic Pool Deck (5th Ave)",
            "asset_type": AssetType.PLAYGROUND,
            "latitude": 40.648,
            "longitude": -74.004,
            "footprint_m2": 7200.0,
            "daily_visitors": 5200,
            "vulnerability_weight": 1.5,
            "notes": "Highest point in South Brooklyn with panoramic harbor views; wide concrete pool promenades and packed summer youth playgrounds.",
        },
        {
            "asset_id": "NYC-BK-PLG-04",
            "name": "Herbert Von King Park Children's Play Yard (Bed-Stuy)",
            "asset_type": AssetType.PLAYGROUND,
            "latitude": 40.69,
            "longitude": -73.948,
            "footprint_m2": 4500.0,
            "daily_visitors": 3300,
            "vulnerability_weight": 1.5,
            "notes": "Historic community park on Tompkins Ave with active amphitheater and popular youth play structures.",
        },
        {
            "asset_id": "NYC-BK-PLG-05",
            "name": "Red Hook Recreation Center Pool & Playground (Bay St)",
            "asset_type": AssetType.PLAYGROUND,
            "latitude": 40.673,
            "longitude": -74.007,
            "footprint_m2": 6100.0,
            "daily_visitors": 3900,
            "vulnerability_weight": 1.5,
            "notes": "Premier South Brooklyn public swimming pool and athletic field complex serving maritime Red Hook community.",
        },
        {
            "asset_id": "NYC-BK-PLG-06",
            "name": "Coffey Park Central Youth Playground (Red Hook)",
            "asset_type": AssetType.PLAYGROUND,
            "latitude": 40.678,
            "longitude": -74.01,
            "footprint_m2": 4300.0,
            "daily_visitors": 2200,
            "vulnerability_weight": 1.5,
            "notes": "Verona St neighborhood park with unshaded asphalt basketball courts and play equipment.",
        },
        {
            "asset_id": "NYC-BK-PLG-07",
            "name": "St. John's Recreation Center Play Area (Crown Heights)",
            "asset_type": AssetType.PLAYGROUND,
            "latitude": 40.671,
            "longitude": -73.935,
            "footprint_m2": 4800.0,
            "daily_visitors": 3100,
            "vulnerability_weight": 1.5,
            "notes": "Troy Ave indoor/outdoor recreation facility with exposed blacktop courts and active youth programming.",
        },
        {
            "asset_id": "NYC-BK-PLZ-02",
            "name": "Albee Square Pedestrian Plaza (Downtown Brooklyn)",
            "asset_type": AssetType.PUBLIC_PLAZA,
            "latitude": 40.691,
            "longitude": -73.9835,
            "footprint_m2": 3600.0,
            "daily_visitors": 18000,
            "vulnerability_weight": 1.3,
            "notes": "Pedestrianized civic square on Fulton St surrounded by City Point retail and high pedestrian transfer flow.",
        },
        {
            "asset_id": "NYC-BK-PLZ-03",
            "name": "Marcy Green Public Plaza & Community Space (Williamsburg)",
            "asset_type": AssetType.PUBLIC_PLAZA,
            "latitude": 40.709,
            "longitude": -73.957,
            "footprint_m2": 3900.0,
            "daily_visitors": 8200,
            "vulnerability_weight": 1.4,
            "notes": "Broadway and Marcy Ave open space outside the elevated J/M/Z subway line.",
        },
        {
            "asset_id": "NYC-BK-PLZ-04",
            "name": "Grand Army Plaza Northern Memorial Promenade",
            "asset_type": AssetType.PUBLIC_PLAZA,
            "latitude": 40.674,
            "longitude": -73.97,
            "footprint_m2": 6500.0,
            "daily_visitors": 24000,
            "vulnerability_weight": 1.3,
            "notes": "Monumental gateway to Prospect Park and Central Library with expansive unshaded stone and asphalt surfaces.",
        },
        {
            "asset_id": "NYC-BK-PLZ-05",
            "name": "DUMBO Archway Pedestrian Plaza & Public Market",
            "asset_type": AssetType.PUBLIC_PLAZA,
            "latitude": 40.703,
            "longitude": -73.989,
            "footprint_m2": 4200.0,
            "daily_visitors": 14000,
            "vulnerability_weight": 1.2,
            "notes": "Water St public gathering space beneath the Manhattan Bridge anchorage with heavy tourist and resident foot traffic.",
        },
        {
            "asset_id": "NYC-BK-COR-02",
            "name": "Pitkin Avenue Commercial & Retail Spine (Brownsville)",
            "asset_type": AssetType.PEDESTRIAN_CORRIDOR,
            "latitude": 40.6705,
            "longitude": -73.907,
            "footprint_m2": 8800.0,
            "daily_visitors": 15500,
            "vulnerability_weight": 1.6,
            "notes": "Primary commercial high street of Brownsville with wide roadway, continuous concrete sidewalks, and minimal tree canopy.",
        },
        {
            "asset_id": "NYC-BK-COR-03",
            "name": "5th Avenue Commercial Corridor (Sunset Park 45th\u201355th)",
            "asset_type": AssetType.PEDESTRIAN_CORRIDOR,
            "latitude": 40.645,
            "longitude": -74.008,
            "footprint_m2": 9200.0,
            "daily_visitors": 18500,
            "vulnerability_weight": 1.4,
            "notes": "Dense commercial corridor with intense foot traffic, unshaded streetscape, and high afternoon vehicle emissions.",
        },
        {
            "asset_id": "NYC-BK-COR-04",
            "name": "Nostrand Avenue Commercial & B44 Transit Corridor",
            "asset_type": AssetType.PEDESTRIAN_CORRIDOR,
            "latitude": 40.668,
            "longitude": -73.95,
            "footprint_m2": 9600.0,
            "daily_visitors": 21000,
            "vulnerability_weight": 1.5,
            "notes": "Major north-south transit and commercial spine through Crown Heights with high Select Bus Service ridership.",
        },
        {
            "asset_id": "NYC-BK-CTR-01",
            "name": "Red Hook Community Justice Center & Youth Plaza",
            "asset_type": AssetType.COMMUNITY_CENTER,
            "latitude": 40.6755,
            "longitude": -74.0085,
            "footprint_m2": 2900.0,
            "daily_visitors": 1500,
            "vulnerability_weight": 1.6,
            "notes": "Vital community justice and social resilience hub providing heat emergency services to Red Hook West NYCHA residents.",
        },
        {
            "asset_id": "NYC-BK-CTR-02",
            "name": "Brownsville Multi-Service Family & Youth Center",
            "asset_type": AssetType.COMMUNITY_CENTER,
            "latitude": 40.662,
            "longitude": -73.909,
            "footprint_m2": 3100.0,
            "daily_visitors": 1800,
            "vulnerability_weight": 1.7,
            "notes": "Rockaway Ave public cooling center anchor providing health, childcare, and senior emergency services.",
        },
        {
            "asset_id": "NYC-QN-TRN-01",
            "name": "Flushing - Main Street 7 Train & Bus Terminal Hub",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.7595,
            "longitude": -73.83,
            "footprint_m2": 4900.0,
            "daily_visitors": 24000,
            "vulnerability_weight": 1.5,
            "notes": "One of NYC's busiest transit hubs with 20+ bus lines; heavy pedestrian crowding, diesel exhaust, and intense urban heat island effect.",
        },
        {
            "asset_id": "NYC-QN-COR-01",
            "name": "Roosevelt Avenue Elevated Transit Corridor (Jackson Heights)",
            "asset_type": AssetType.PEDESTRIAN_CORRIDOR,
            "latitude": 40.749,
            "longitude": -73.891,
            "footprint_m2": 7800.0,
            "daily_visitors": 16500,
            "vulnerability_weight": 1.4,
            "notes": "Vibrant immigrant commercial corridor beneath the 7 train elevated structure; trapped vehicle heat and high ground surface exposure.",
        },
        {
            "asset_id": "NYC-QN-SCH-01",
            "name": "Queens High School of Teaching Athletic Yard (Glen Oaks)",
            "asset_type": AssetType.SCHOOL,
            "latitude": 40.742,
            "longitude": -73.715,
            "footprint_m2": 5800.0,
            "daily_visitors": 1100,
            "vulnerability_weight": 1.5,
            "notes": "Eastern Queens educational campus with wide asphalt walkways and exposed sports fields.",
        },
        {
            "asset_id": "NYC-QN-PLZ-01",
            "name": "Jamaica Center - Parsons/Archer Transit Plaza",
            "asset_type": AssetType.PUBLIC_PLAZA,
            "latitude": 40.702,
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
            "latitude": 40.753,
            "longitude": -73.886,
            "footprint_m2": 3800.0,
            "daily_visitors": 3200,
            "vulnerability_weight": 1.5,
            "notes": "Densely populated Jackson Heights community park with high child activity and limited mature tree canopy.",
        },
        {
            "asset_id": "NYC-QN-TRN-02",
            "name": "74th St - Broadway / Jackson Heights Station Complex",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.7465,
            "longitude": -73.8915,
            "footprint_m2": 5600.0,
            "daily_visitors": 31000,
            "vulnerability_weight": 1.5,
            "notes": "Major multi-level transit nexus (7/E/F/M/R subways and LGA Airport Q70 SBS bus) with heavy sidewalk dwell times.",
        },
        {
            "asset_id": "NYC-QN-TRN-03",
            "name": "Queensboro Plaza Elevated Transit Junction (N/W/7)",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.7505,
            "longitude": -73.94,
            "footprint_m2": 4800.0,
            "daily_visitors": 26000,
            "vulnerability_weight": 1.4,
            "notes": "Long Island City regional transit gateway with heavy bridge vehicular traffic, concrete elevated tracks, and high daytime surface temperatures.",
        },
        {
            "asset_id": "NYC-QN-TRN-04",
            "name": "Court Square - 23rd St Transit Island (LIC)",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.747,
            "longitude": -73.945,
            "footprint_m2": 3900.0,
            "daily_visitors": 19500,
            "vulnerability_weight": 1.3,
            "notes": "High-density residential and commercial core in Long Island City around the 7/E/G/M subways with concrete streetscapes.",
        },
        {
            "asset_id": "NYC-QN-TRN-05",
            "name": "Woodside - 61st St LIRR & 7 Train Bus Apron",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.7455,
            "longitude": -73.903,
            "footprint_m2": 4200.0,
            "daily_visitors": 18500,
            "vulnerability_weight": 1.4,
            "notes": "Multi-modal transfer connecting LIRR, 7 train, and local bus routes under heavy elevated concrete structures.",
        },
        {
            "asset_id": "NYC-QN-TRN-06",
            "name": "Jamaica - 179th St F Train Terminal Bus Depot",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.7125,
            "longitude": -73.784,
            "footprint_m2": 4600.0,
            "daily_visitors": 16500,
            "vulnerability_weight": 1.5,
            "notes": "Eastern terminus of the Queens Blvd Line connecting eastern Queens and Nassau County bus lines across extensive asphalt platforms.",
        },
        {
            "asset_id": "NYC-QN-TRN-07",
            "name": "Beach 67th St - Arverne By The Sea A Train Plaza",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.591,
            "longitude": -73.796,
            "footprint_m2": 3400.0,
            "daily_visitors": 7800,
            "vulnerability_weight": 1.4,
            "notes": "Rockaway Peninsula elevated subway station plaza with direct coastal sun exposure and vast asphalt parking surfaces.",
        },
        {
            "asset_id": "NYC-QN-TRN-08",
            "name": "Far Rockaway - Mott Ave A Train Terminal Plaza",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.604,
            "longitude": -73.755,
            "footprint_m2": 3800.0,
            "daily_visitors": 9200,
            "vulnerability_weight": 1.6,
            "notes": "Southernmost subway terminal in Queens serving downtown Far Rockaway; high transit dependence and minimal shade shelter.",
        },
        {
            "asset_id": "NYC-QN-SCH-02",
            "name": "John Bowne High School Agriscience & Athletic Yard",
            "asset_type": AssetType.SCHOOL,
            "latitude": 40.737,
            "longitude": -73.82,
            "footprint_m2": 7200.0,
            "daily_visitors": 3400,
            "vulnerability_weight": 1.4,
            "notes": "Flushing high school campus on Main St with large athletic fields and paved recreation areas.",
        },
        {
            "asset_id": "NYC-QN-SCH-03",
            "name": "Newtown High School Courtyard & Athletic Field (Elmhurst)",
            "asset_type": AssetType.SCHOOL,
            "latitude": 40.738,
            "longitude": -73.878,
            "footprint_m2": 5900.0,
            "daily_visitors": 2800,
            "vulnerability_weight": 1.5,
            "notes": "Elmhurst collegiate high school building with wide paved perimeter yards and unshaded sports grounds.",
        },
        {
            "asset_id": "NYC-QN-SCH-04",
            "name": "Long Island City High School Outdoor Quad (Astoria)",
            "asset_type": AssetType.SCHOOL,
            "latitude": 40.76,
            "longitude": -73.931,
            "footprint_m2": 6100.0,
            "daily_visitors": 2600,
            "vulnerability_weight": 1.4,
            "notes": "Broadway & 21st St educational campus near Queensbridge Houses with extensive unshaded concrete courts.",
        },
        {
            "asset_id": "NYC-QN-SCH-05",
            "name": "Hillcrest High School Campus Courtyard (Jamaica Hills)",
            "asset_type": AssetType.SCHOOL,
            "latitude": 40.716,
            "longitude": -73.799,
            "footprint_m2": 5200.0,
            "daily_visitors": 2200,
            "vulnerability_weight": 1.5,
            "notes": "Highland Ave campus overlooking Jamaica with expansive asphalt sports blacktop.",
        },
        {
            "asset_id": "NYC-QN-SCH-06",
            "name": "Richmond Hill High School Blacktop Courtyard",
            "asset_type": AssetType.SCHOOL,
            "latitude": 40.697,
            "longitude": -73.834,
            "footprint_m2": 4800.0,
            "daily_visitors": 1900,
            "vulnerability_weight": 1.5,
            "notes": "89th Ave secondary school with enclosed paved courtyard trapping radiant heat.",
        },
        {
            "asset_id": "NYC-QN-SCH-07",
            "name": "PS 19 Marino Jeantet School Yard (Corona)",
            "asset_type": AssetType.SCHOOL,
            "latitude": 40.749,
            "longitude": -73.864,
            "footprint_m2": 3900.0,
            "daily_visitors": 1400,
            "vulnerability_weight": 1.7,
            "notes": "One of NYC's largest elementary schools on 41st Ave in a dense, high heat-vulnerability Corona neighborhood.",
        },
        {
            "asset_id": "NYC-QN-PLG-02",
            "name": "Astoria Park South Playground & Great Lawn Forecourt",
            "asset_type": AssetType.PLAYGROUND,
            "latitude": 40.776,
            "longitude": -73.924,
            "footprint_m2": 6500.0,
            "daily_visitors": 4800,
            "vulnerability_weight": 1.3,
            "notes": "East River waterfront park beneath the Triborough Bridge; large concrete pool plaza and exposed children's playground.",
        },
        {
            "asset_id": "NYC-QN-PLG-03",
            "name": "Flushing Meadows Corona Park North Youth Playground",
            "asset_type": AssetType.PLAYGROUND,
            "latitude": 40.744,
            "longitude": -73.85,
            "footprint_m2": 7200.0,
            "daily_visitors": 6500,
            "vulnerability_weight": 1.4,
            "notes": "Queens flagship park recreation space near the NY Hall of Science with massive unshaded asphalt plazas and play decks.",
        },
        {
            "asset_id": "NYC-QN-PLG-04",
            "name": "Rufus King Park Playground & Historic Green (Jamaica)",
            "asset_type": AssetType.PLAYGROUND,
            "latitude": 40.704,
            "longitude": -73.804,
            "footprint_m2": 4400.0,
            "daily_visitors": 3600,
            "vulnerability_weight": 1.6,
            "notes": "Downtown Jamaica historic park surrounded by 89th Ave commercial spine; heavily utilized youth playground with heat-absorbing surfaces.",
        },
        {
            "asset_id": "NYC-QN-PLG-05",
            "name": "Gorman Playground & Sports Deck (East Elmhurst)",
            "asset_type": AssetType.PLAYGROUND,
            "latitude": 40.762,
            "longitude": -73.882,
            "footprint_m2": 4100.0,
            "daily_visitors": 2400,
            "vulnerability_weight": 1.5,
            "notes": "84th St neighborhood park between LGA Airport and Jackson Heights with wide blacktop sports courts.",
        },
        {
            "asset_id": "NYC-QN-PLG-06",
            "name": "Baisley Pond Park Youth Play Area (South Jamaica)",
            "asset_type": AssetType.PLAYGROUND,
            "latitude": 40.679,
            "longitude": -73.788,
            "footprint_m2": 5200.0,
            "daily_visitors": 2900,
            "vulnerability_weight": 1.6,
            "notes": "South Jamaica community park along Baisley Blvd; open sunny recreation zones and high youth foot traffic.",
        },
        {
            "asset_id": "NYC-QN-PLG-07",
            "name": "Bayswater Park Waterfront Play Space (Far Rockaway)",
            "asset_type": AssetType.PLAYGROUND,
            "latitude": 40.601,
            "longitude": -73.771,
            "footprint_m2": 4600.0,
            "daily_visitors": 2100,
            "vulnerability_weight": 1.6,
            "notes": "Jamaica Bay waterfront recreation space on Bay 32nd St with direct unshaded sun exposure and asphalt courts.",
        },
        {
            "asset_id": "NYC-QN-PLZ-02",
            "name": "Corona Plaza Pedestrian Hub (Roosevelt Ave & 103rd St)",
            "asset_type": AssetType.PUBLIC_PLAZA,
            "latitude": 40.7495,
            "longitude": -73.862,
            "footprint_m2": 3900.0,
            "daily_visitors": 19000,
            "vulnerability_weight": 1.6,
            "notes": "Vibrant immigrant public market and civic plaza beneath the 7 train with severe lack of vegetative canopy and intense afternoon heat.",
        },
        {
            "asset_id": "NYC-QN-PLZ-03",
            "name": "Diversity Plaza Community Pedestrian Hub (Jackson Heights)",
            "asset_type": AssetType.PUBLIC_PLAZA,
            "latitude": 40.747,
            "longitude": -73.89,
            "footprint_m2": 3400.0,
            "daily_visitors": 16000,
            "vulnerability_weight": 1.5,
            "notes": "37th Road pedestrian plaza outside the 74th St transit hub; high density community gathering space.",
        },
        {
            "asset_id": "NYC-QN-PLZ-04",
            "name": "Hunters Point South Waterfront Promenade Plaza",
            "asset_type": AssetType.PUBLIC_PLAZA,
            "latitude": 40.741,
            "longitude": -73.959,
            "footprint_m2": 5800.0,
            "daily_visitors": 12000,
            "vulnerability_weight": 1.2,
            "notes": "Long Island City East River waterfront park with wide open concrete piers and direct afternoon solar exposure.",
        },
        {
            "asset_id": "NYC-QN-PLZ-05",
            "name": "Rockaway Beach Boardwalk & 94th St Concession Plaza",
            "asset_type": AssetType.PUBLIC_PLAZA,
            "latitude": 40.585,
            "longitude": -73.818,
            "footprint_m2": 6200.0,
            "daily_visitors": 22000,
            "vulnerability_weight": 1.3,
            "notes": "Major beachside public pavilion with high summer visitor volumes and extreme unshaded solar reflectance.",
        },
        {
            "asset_id": "NYC-QN-COR-02",
            "name": "Steinway Street Commercial Spine (Astoria 28th to 34th)",
            "asset_type": AssetType.PEDESTRIAN_CORRIDOR,
            "latitude": 40.764,
            "longitude": -73.918,
            "footprint_m2": 8900.0,
            "daily_visitors": 17500,
            "vulnerability_weight": 1.4,
            "notes": "Astoria's main shopping corridor with continuous retail frontage, dark asphalt street, and minimal street trees.",
        },
        {
            "asset_id": "NYC-QN-COR-03",
            "name": "Jamaica Avenue Retail & Commercial Spine (160th to 169th)",
            "asset_type": AssetType.PEDESTRIAN_CORRIDOR,
            "latitude": 40.705,
            "longitude": -73.797,
            "footprint_m2": 9400.0,
            "daily_visitors": 23000,
            "vulnerability_weight": 1.5,
            "notes": "Downtown Jamaica's premier retail strip; dense bus traffic, narrow crowded sidewalks, and high surface heat retention.",
        },
        {
            "asset_id": "NYC-QN-COR-04",
            "name": "Junction Boulevard Commercial Spine (Corona)",
            "asset_type": AssetType.PEDESTRIAN_CORRIDOR,
            "latitude": 40.751,
            "longitude": -73.868,
            "footprint_m2": 8200.0,
            "daily_visitors": 16000,
            "vulnerability_weight": 1.5,
            "notes": "Bustling North Queens shopping and walking street connecting Corona and East Elmhurst.",
        },
        {
            "asset_id": "NYC-QN-CTR-01",
            "name": "Queens Central Library Forecourt & Community Plaza",
            "asset_type": AssetType.COMMUNITY_CENTER,
            "latitude": 40.7045,
            "longitude": -73.795,
            "footprint_m2": 3600.0,
            "daily_visitors": 4500,
            "vulnerability_weight": 1.6,
            "notes": "Merrick Blvd flagship public library serving as primary community cooling and educational sanctuary in Southeast Queens.",
        },
        {
            "asset_id": "NYC-SI-TRN-01",
            "name": "St. George Ferry Terminal Bus Bays & Esplanade",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.6435,
            "longitude": -74.074,
            "footprint_m2": 5100.0,
            "daily_visitors": 18000,
            "vulnerability_weight": 1.3,
            "notes": "Primary transit link between Staten Island and Manhattan; extensive unshaded concrete walkways and bus boarding platforms.",
        },
        {
            "asset_id": "NYC-SI-COR-01",
            "name": "Bay Street Maritime & Commercial Corridor",
            "asset_type": AssetType.PEDESTRIAN_CORRIDOR,
            "latitude": 40.635,
            "longitude": -74.076,
            "footprint_m2": 6500.0,
            "daily_visitors": 5800,
            "vulnerability_weight": 1.3,
            "notes": "North Shore waterfront connector with asphalt streetscape and high heat retention into late evening.",
        },
        {
            "asset_id": "NYC-SI-SCH-01",
            "name": "Curtis High School Open Courtyard & Quad",
            "asset_type": AssetType.SCHOOL,
            "latitude": 40.645,
            "longitude": -74.088,
            "footprint_m2": 4200.0,
            "daily_visitors": 1600,
            "vulnerability_weight": 1.5,
            "notes": "St. George high school campus with concrete steps and unshaded quad area.",
        },
        {
            "asset_id": "NYC-SI-PLG-01",
            "name": "Faber Park Waterfront Playground & Pool Plaza",
            "asset_type": AssetType.PLAYGROUND,
            "latitude": 40.641,
            "longitude": -74.138,
            "footprint_m2": 3600.0,
            "daily_visitors": 1500,
            "vulnerability_weight": 1.4,
            "notes": "Kill Van Kull waterfront park on Richmond Terrace; open recreational pool deck and exposed playground equipment.",
        },
        {
            "asset_id": "NYC-SI-TRN-02",
            "name": "Eltingville Transit Center & Commuter Bus Bays",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.542,
            "longitude": -74.167,
            "footprint_m2": 6200.0,
            "daily_visitors": 9500,
            "vulnerability_weight": 1.3,
            "notes": "Major South Shore park-and-ride and express bus terminal (SIM lines) with sprawling unshaded asphalt parking and bus aprons.",
        },
        {
            "asset_id": "NYC-SI-TRN-03",
            "name": "Port Richmond Bus Transfer Island & Richmond Terrace Depot",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.638,
            "longitude": -74.131,
            "footprint_m2": 3700.0,
            "daily_visitors": 8200,
            "vulnerability_weight": 1.5,
            "notes": "Key North Shore bus transfer junction on Port Richmond Ave with heavy transit rider dwell time and dark road surfacing.",
        },
        {
            "asset_id": "NYC-SI-TRN-04",
            "name": "Tottenville SIR Transit Terminal & Main St Bus Loop",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.5125,
            "longitude": -74.251,
            "footprint_m2": 3400.0,
            "daily_visitors": 4500,
            "vulnerability_weight": 1.3,
            "notes": "Southernmost rail terminal in New York State with open paved pedestrian plazas and bus connection loops.",
        },
        {
            "asset_id": "NYC-SI-TRN-05",
            "name": "Arthur Kill SIR Station Plaza & Commuter Bus Apron",
            "asset_type": AssetType.BUS_STOP,
            "latitude": 40.516,
            "longitude": -74.242,
            "footprint_m2": 3900.0,
            "daily_visitors": 5200,
            "vulnerability_weight": 1.3,
            "notes": "Charleston multimodal commuter hub with wide exposed concrete platform walkways and park-and-ride lots.",
        },
        {
            "asset_id": "NYC-SI-SCH-02",
            "name": "Port Richmond High School Athletic Grounds & Quad",
            "asset_type": AssetType.SCHOOL,
            "latitude": 40.628,
            "longitude": -74.144,
            "footprint_m2": 6800.0,
            "daily_visitors": 2200,
            "vulnerability_weight": 1.5,
            "notes": "Innis St secondary school campus with wide paved courtyard blacktop and exposed athletic fields.",
        },
        {
            "asset_id": "NYC-SI-SCH-03",
            "name": "New Dorp High School Campus Blacktop & Sports Court",
            "asset_type": AssetType.SCHOOL,
            "latitude": 40.573,
            "longitude": -74.112,
            "footprint_m2": 6500.0,
            "daily_visitors": 2400,
            "vulnerability_weight": 1.4,
            "notes": "East Shore high school campus on Clawson St with extensive unshaded asphalt recreational courts.",
        },
        {
            "asset_id": "NYC-SI-SCH-04",
            "name": "PS 78 Staten Island Community School Yard (Stapleton)",
            "asset_type": AssetType.SCHOOL,
            "latitude": 40.627,
            "longitude": -74.077,
            "footprint_m2": 3200.0,
            "daily_visitors": 650,
            "vulnerability_weight": 1.7,
            "notes": "Tompkins Ave elementary school in Stapleton NYCHA community with high child heat vulnerability.",
        },
        {
            "asset_id": "NYC-SI-SCH-05",
            "name": "Tottenville High School Outdoor Courtyard (Huguenot)",
            "asset_type": AssetType.SCHOOL,
            "latitude": 40.528,
            "longitude": -74.195,
            "footprint_m2": 7100.0,
            "daily_visitors": 3800,
            "vulnerability_weight": 1.3,
            "notes": "One of NYC's largest high school campuses on Luten Ave with wide concrete concourses and sports fields.",
        },
        {
            "asset_id": "NYC-SI-PLG-02",
            "name": "Lyons Pool Recreation Plaza & Pier Playground",
            "asset_type": AssetType.PLAYGROUND,
            "latitude": 40.636,
            "longitude": -74.073,
            "footprint_m2": 5400.0,
            "daily_visitors": 3400,
            "vulnerability_weight": 1.5,
            "notes": "Historic Tompkinsville public pool complex along the harbor; vast concrete sun deck and active summer youth crowds.",
        },
        {
            "asset_id": "NYC-SI-PLG-03",
            "name": "Midland Beach Playground & FDR Boardwalk Plaza",
            "asset_type": AssetType.PLAYGROUND,
            "latitude": 40.57,
            "longitude": -74.092,
            "footprint_m2": 5800.0,
            "daily_visitors": 4100,
            "vulnerability_weight": 1.4,
            "notes": "East Shore public beach playground with unshaded asphalt sports courts and high summer recreational usage.",
        },
        {
            "asset_id": "NYC-SI-PLG-04",
            "name": "Corporal Thompson Park Field & Play Deck (West New Brighton)",
            "asset_type": AssetType.PLAYGROUND,
            "latitude": 40.638,
            "longitude": -74.116,
            "footprint_m2": 4600.0,
            "daily_visitors": 2100,
            "vulnerability_weight": 1.5,
            "notes": "Broadway & Henderson Ave youth park with synthetic turf field and exposed play structures.",
        },
        {
            "asset_id": "NYC-SI-PLZ-01",
            "name": "Tappen Park & Historic Village Hall Civic Square (Stapleton)",
            "asset_type": AssetType.PUBLIC_PLAZA,
            "latitude": 40.6265,
            "longitude": -74.078,
            "footprint_m2": 3900.0,
            "daily_visitors": 4200,
            "vulnerability_weight": 1.5,
            "notes": "Historic town square on Bay Street serving as the civic and commercial center of Stapleton with wide paved walkways.",
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


BOROUGH_PREFIXES: dict[str, str] = {
    "bronx": "NYC-BX-",
    "the bronx": "NYC-BX-",
    "bx": "NYC-BX-",
    "manhattan": "NYC-MN-",
    "mn": "NYC-MN-",
    "brooklyn": "NYC-BK-",
    "bk": "NYC-BK-",
    "queens": "NYC-QN-",
    "qn": "NYC-QN-",
    "staten_island": "NYC-SI-",
    "staten island": "NYC-SI-",
    "si": "NYC-SI-",
}

@functools.lru_cache(maxsize=32)
def get_city_public_assets(city_key: str = "nyc") -> list[PublicAsset]:
    """Retrieve all public assets for a city or borough enriched with observed FortyGuard microclimate data."""
    city_norm = city_key.lower().strip()
    all_raw = RAW_ASSETS.get("nyc", [])

    if city_norm in ("nyc", "all", "new_york_city", "new york city"):
        raw_list = all_raw
    elif city_norm in BOROUGH_PREFIXES:
        prefix = BOROUGH_PREFIXES[city_norm]
        raw_list = [a for a in all_raw if a.get("asset_id", "").startswith(prefix)]
    elif city_norm in CITY_CONFIGS:
        bounds = CITY_CONFIGS[city_norm].bounds
        min_lng, min_lat = bounds[0]
        max_lng, max_lat = bounds[1]
        raw_list = [
            a for a in all_raw
            if min_lng <= a["longitude"] <= max_lng and min_lat <= a["latitude"] <= max_lat
        ]
        if not raw_list:
            raw_list = all_raw
    else:
        raw_list = RAW_ASSETS.get(city_norm, all_raw)

    centroids = _load_city_tile_centroids("nyc")
    exc_map, per_map = _load_city_exceedance_persistence("nyc")

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

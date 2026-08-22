"""Geographic tiling, merging, and boundary clipping service for New York City."""

from __future__ import annotations

import json
import math
import pathlib
from typing import Any
from shapely.geometry import Point, Polygon, box, mapping, shape
from shapely.ops import unary_union

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
NYC_BOROUGHS_FILE = ROOT_DIR / "data" / "nyc_boroughs.geojson"

# Default tile size in degrees (~5.5 km lon x 6.1 km lat ~= 33.6 km2)
TILE_DLON = 0.065
TILE_DLAT = 0.055


def load_nyc_boroughs() -> dict[str, Any]:
    """Load the official NYC 5-borough GeoJSON FeatureCollection."""
    if not NYC_BOROUGHS_FILE.exists():
        raise FileNotFoundError(f"NYC Boroughs GeoJSON not found at {NYC_BOROUGHS_FILE}")

    with open(NYC_BOROUGHS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_nyc_boundary_shape() -> tuple[Any, dict[str, Any]]:
    """Retrieve the unified Shapely geometry of NYC and mapping of borough name -> Shapely geometry."""
    data = load_nyc_boroughs()
    borough_shapes: dict[str, Any] = {}

    for ft in data.get("features", []):
        b_name = ft.get("properties", {}).get("name", "Unknown")
        geom = shape(ft.get("geometry", {}))
        if not geom.is_valid:
            geom = geom.buffer(0)
        borough_shapes[b_name] = geom

    nyc_union = unary_union(list(borough_shapes.values()))
    if not nyc_union.is_valid:
        nyc_union = nyc_union.buffer(0)

    return nyc_union, borough_shapes


def generate_nyc_tiles(
    dlon: float = TILE_DLON,
    dlat: float = TILE_DLAT,
) -> list[dict[str, Any]]:
    """Partition New York City's bounding box into API-safe geographic tiles intersecting NYC land.

    Returns a list of tile dicts:
    - tile_id: e.g. 'NYC-T01'
    - bounds: [min_lon, min_lat, max_lon, max_lat]
    - polygon_aoi: GeoJSON FeatureCollection formatted for FortyGuard create_heatmap
    - boroughs: list of intersecting borough names
    - area_km2: approximate area in square kilometers
    """
    nyc_boundary, borough_shapes = get_nyc_boundary_shape()
    min_lon, min_lat, max_lon, max_lat = nyc_boundary.bounds

    lon_steps = int(math.ceil((max_lon - min_lon) / dlon))
    lat_steps = int(math.ceil((max_lat - min_lat) / dlat))

    tiles: list[dict[str, Any]] = []
    tile_idx = 0

    for r in range(lat_steps):
        for c in range(lon_steps):
            t_min_lon = round(min_lon + c * dlon, 6)
            t_max_lon = round(min(max_lon, t_min_lon + dlon), 6)
            t_min_lat = round(min_lat + r * dlat, 6)
            t_max_lat = round(min(max_lat, t_min_lat + dlat), 6)

            t_poly = box(t_min_lon, t_min_lat, t_max_lon, t_max_lat)

            # Check if this tile intersects any NYC land
            if t_poly.intersects(nyc_boundary):
                intersecting_boroughs = [
                    b_name for b_name, b_geom in borough_shapes.items() if t_poly.intersects(b_geom)
                ]
                tile_idx += 1
                tile_id = f"NYC-T{tile_idx:02d}"

                # Calculate approximate area in km2
                mid_lat = (t_min_lat + t_max_lat) / 2.0
                dx_km = (t_max_lon - t_min_lon) * 111.32 * math.cos(math.radians(mid_lat))
                dy_km = (t_max_lat - t_min_lat) * 111.0
                area_km2 = round(dx_km * dy_km, 2)

                # Construct polygon_aoi GeoJSON payload expected by FortyGuard
                coords = [
                    [t_min_lon, t_min_lat],
                    [t_max_lon, t_min_lat],
                    [t_max_lon, t_max_lat],
                    [t_min_lon, t_max_lat],
                    [t_min_lon, t_min_lat],
                ]
                poly_aoi = {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "properties": {"tile_id": tile_id, "boroughs": intersecting_boroughs},
                            "geometry": {"type": "Polygon", "coordinates": [coords]},
                        }
                    ],
                }

                tiles.append({
                    "tile_id": tile_id,
                    "tile_index": tile_idx,
                    "bounds": [t_min_lon, t_min_lat, t_max_lon, t_max_lat],
                    "boroughs": intersecting_boroughs,
                    "area_km2": area_km2,
                    "polygon_aoi": poly_aoi,
                })

    return tiles


def merge_and_clip_heatmap_features(
    tile_feature_lists: list[list[dict[str, Any]]],
    clip_to_boundary: bool = True,
) -> list[dict[str, Any]]:
    """Merge multiple tile GeoJSON feature lists, deduplicate overlapping cells, and clip to NYC.

    Parameters
    ----------
    tile_feature_lists:
        List of GeoJSON feature arrays from FortyGuard responses.
    clip_to_boundary:
        If True, only keeps 100m grid cells whose centroids fall within the NYC shoreline boundary.

    Returns
    -------
    list[dict[str, Any]]
        Cleaned, deduplicated, sorted GeoJSON features covering NYC.
    """
    nyc_boundary, borough_shapes = get_nyc_boundary_shape()

    # Use rounded centroid as deduplication key (precision ~1m)
    seen_centroids: set[tuple[float, float]] = set()
    merged_features: list[dict[str, Any]] = []

    for f_list in tile_feature_lists:
        for feat in f_list:
            geom_dict = feat.get("geometry")
            if not geom_dict or geom_dict.get("type") != "Polygon":
                continue

            poly_shape = shape(geom_dict)
            if not poly_shape.is_valid:
                poly_shape = poly_shape.buffer(0)
            if poly_shape.is_empty:
                continue

            centroid = poly_shape.centroid
            c_key = (round(centroid.x, 4), round(centroid.y, 4))

            if c_key in seen_centroids:
                continue
            seen_centroids.add(c_key)

            # Spatial clipping to NYC shoreline boundary
            if clip_to_boundary:
                # If centroid is inside NYC land boundary, keep it
                pt = Point(centroid.x, centroid.y)
                if not nyc_boundary.contains(pt) and not nyc_boundary.intersects(pt):
                    continue

            # Determine borough metadata
            cell_borough = "New York City"
            for b_name, b_geom in borough_shapes.items():
                if b_geom.contains(centroid) or b_geom.intersects(centroid):
                    cell_borough = b_name
                    break

            props = dict(feat.get("properties", {}))
            props["borough"] = cell_borough

            merged_features.append({
                "type": "Feature",
                "properties": props,
                "geometry": geom_dict,
            })

    # Sort deterministically by latitude descending, then longitude ascending
    merged_features.sort(
        key=lambda f: (-f["geometry"]["coordinates"][0][0][1], f["geometry"]["coordinates"][0][0][0])
    )

    # Re-assign sequential tile_ids
    for idx, f in enumerate(merged_features):
        f["id"] = str(idx)
        f["properties"]["tile_id"] = idx

    return merged_features

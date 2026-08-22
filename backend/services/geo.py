"""Geospatial processing service for area-weighted parcel clipping and AOI construction."""

from __future__ import annotations

import math
from typing import Any
from shapely.geometry import mapping, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from backend.models.thermal import ContributingTile, SiteClippingResult


def _parse_geometry(geo_input: Any) -> BaseGeometry:
    """Parse a GeoJSON dictionary, Feature, or Shapely geometry into a valid Shapely shape."""
    if isinstance(geo_input, BaseGeometry):
        geom = geo_input
    elif isinstance(geo_input, dict):
        if geo_input.get("type") == "Feature":
            geom = shape(geo_input.get("geometry", {}))
        elif geo_input.get("type") == "FeatureCollection":
            features = geo_input.get("features", [])
            if not features:
                raise ValueError("GeoJSON FeatureCollection contains no features")
            geom = shape(features[0].get("geometry", {}))
        else:
            geom = shape(geo_input)
    else:
        raise ValueError(f"Unsupported geometry type: {type(geo_input).__name__}")

    if not geom.is_valid:
        geom = geom.buffer(0)
    if geom.is_empty:
        raise ValueError("Geometry is empty")

    return geom


def get_site_centroid(site_geometry: dict[str, Any] | BaseGeometry) -> tuple[float, float]:
    """Calculate the centroid coordinate (latitude, longitude) of a site geometry."""
    geom = _parse_geometry(site_geometry)
    c = geom.centroid
    return round(c.y, 6), round(c.x, 6)


def build_unified_aoi(
    site_geometries: list[dict[str, Any] | BaseGeometry],
    buffer_m: float = 400.0,
) -> tuple[dict[str, Any], float]:
    """Construct a unified convex-hull AOI enclosing all candidate sites with a safety buffer.

    Optimization:
    Rather than making separate FortyGuard heatmap requests for N candidate sites,
    this creates a single enclosing polygon AOI. A single API call covers all sites,
    reducing credit consumption by N-fold and putting all candidate parcels on an
    identical meteorological baseline.

    Parameters
    ----------
    site_geometries:
        List of candidate site polygons.
    buffer_m:
        Buffer distance in meters around the convex hull (default: 400m).

    Returns
    -------
    tuple[dict, float]
        (GeoJSON FeatureCollection AOI payload, Total AOI area in km²)

    Raises
    ------
    ValueError
        If site list is empty or resulting AOI exceeds API limits.
    """
    if not site_geometries:
        raise ValueError("Cannot build AOI from empty site geometries list")

    shapes = [_parse_geometry(g) for g in site_geometries]
    combined = unary_union(shapes)
    hull = combined.convex_hull

    # Approximate degrees per meter at average latitude (1 deg lat ~= 111,000 m)
    lat_center = hull.centroid.y
    deg_lat_per_m = 1.0 / 111000.0
    deg_lon_per_m = 1.0 / (111320.0 * math.cos(math.radians(lat_center)))
    avg_deg_per_m = (deg_lat_per_m + deg_lon_per_m) / 2.0

    buffer_deg = buffer_m * avg_deg_per_m
    aoi_poly = hull.buffer(buffer_deg)

    # Convert area to km²
    area_deg2 = aoi_poly.area
    area_km2 = area_deg2 * (111.0 * (111.32 * math.cos(math.radians(lat_center))))

    # API cap safety check (Premium tier cap is ~50 mi² ~= 130 km²)
    if area_km2 > 130.0:
        raise ValueError(
            f"Unified AOI area ({area_km2:.1f} km²) exceeds FortyGuard Premium area limit (130 km²). "
            "Split candidate sites into distinct regional submarket clusters."
        )

    aoi_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "description": f"Unified Screening AOI enclosing {len(site_geometries)} candidate parcels (+{buffer_m:.0f}m buffer)",
                    "area_km2": round(area_km2, 2),
                },
                "geometry": mapping(aoi_poly),
            }
        ],
    }

    return aoi_geojson, round(area_km2, 2)


def clip_heatmap_to_site(
    features: list[dict[str, Any]],
    site_geometry: dict[str, Any] | BaseGeometry,
    site_id: str | None = None,
) -> SiteClippingResult:
    """Perform area-weighted spatial clipping of FortyGuard TCM heatmap tiles over a site polygon."""
    if not isinstance(features, list) or len(features) == 0:
        raise ValueError("Heatmap features list is empty or invalid")

    site_poly = _parse_geometry(site_geometry)
    site_area = site_poly.area
    if site_area <= 0:
        raise ValueError(f"Site polygon area is non-positive: {site_area}")

    weighted_avg_sum = 0.0
    weighted_min_sum = 0.0
    weighted_max_sum = 0.0
    total_intersection_area = 0.0
    contributing: list[ContributingTile] = []

    for idx, feat in enumerate(features):
        props = feat.get("properties", {})
        tile_geom_raw = feat.get("geometry")
        if not tile_geom_raw:
            continue

        try:
            tile_poly = shape(tile_geom_raw)
        except Exception:
            continue

        if not tile_poly.intersects(site_poly):
            continue

        intersection = tile_poly.intersection(site_poly)
        if intersection.is_empty or intersection.area <= 0:
            continue

        inter_area = intersection.area
        avg_t = props.get("average_temperature", props.get("temperature"))
        min_t = props.get("min_temperature", avg_t)
        max_t = props.get("max_temperature", avg_t)

        if avg_t is None or min_t is None or max_t is None:
            continue

        avg_t = float(avg_t)
        min_t = float(min_t)
        max_t = float(max_t)

        weighted_avg_sum += inter_area * avg_t
        weighted_min_sum += inter_area * min_t
        weighted_max_sum += inter_area * max_t
        total_intersection_area += inter_area

        tile_id = props.get("tile_id", feat.get("id", idx))
        contributing.append(
            ContributingTile(
                tile_id=tile_id,
                weight_area=inter_area,
                share_pct=0.0,
                average_temperature=avg_t,
                min_temperature=min_t,
                max_temperature=max_t,
            )
        )

    if total_intersection_area <= 0 or len(contributing) == 0:
        raise ValueError(
            f"Site polygon does not intersect any heatmap tiles (site_id={site_id}). "
            "Verify site coordinates fall within the heatmap AOI."
        )

    for item in contributing:
        item.share_pct = round((item.weight_area / total_intersection_area) * 100.0, 2)
    contributing.sort(key=lambda t: t.weight_area, reverse=True)

    weighted_avg = weighted_avg_sum / total_intersection_area
    weighted_min = weighted_min_sum / total_intersection_area
    weighted_max = weighted_max_sum / total_intersection_area
    weighted_swing = weighted_max - weighted_min

    coverage_fraction = total_intersection_area / site_area
    coverage_pct = round(min(coverage_fraction * 100.0, 100.0), 2)

    return SiteClippingResult(
        site_id=site_id,
        coverage_pct=coverage_pct,
        contributing_tile_count=len(contributing),
        weighted_average_temperature_c=round(weighted_avg, 4),
        weighted_min_temperature_c=round(weighted_min, 4),
        weighted_max_temperature_c=round(weighted_max, 4),
        weighted_diurnal_swing_c=round(weighted_swing, 4),
        contributing_tiles=contributing,
    )


def clip_analysis_layer_to_site(
    features: list[dict[str, Any]],
    site_geometry: dict[str, Any] | BaseGeometry,
    site_id: str | None = None,
) -> SiteClippingResult:
    """Clip a FortyGuard analysis heatmap layer (exceedance / persistence) to a site polygon."""
    if not isinstance(features, list) or len(features) == 0:
        raise ValueError("Analysis heatmap features list is empty or invalid")

    site_poly = _parse_geometry(site_geometry)
    site_area = site_poly.area
    if site_area <= 0:
        raise ValueError(f"Site polygon area is non-positive: {site_area}")

    weighted_val_sum = 0.0
    total_intersection_area = 0.0
    contributing: list[ContributingTile] = []

    for idx, feat in enumerate(features):
        props = feat.get("properties", {})
        tile_geom_raw = feat.get("geometry")
        if not tile_geom_raw:
            continue

        try:
            tile_poly = shape(tile_geom_raw)
        except Exception:
            continue

        if not tile_poly.intersects(site_poly):
            continue

        intersection = tile_poly.intersection(site_poly)
        if intersection.is_empty or intersection.area <= 0:
            continue

        inter_area = intersection.area
        raw_val = props.get("value")
        if raw_val is None:
            continue

        val = float(raw_val)
        weighted_val_sum += inter_area * val
        total_intersection_area += inter_area

        tile_id = props.get("tile_id", feat.get("id", idx))
        contributing.append(
            ContributingTile(
                tile_id=tile_id,
                weight_area=inter_area,
                share_pct=0.0,
                value=val,
            )
        )

    if total_intersection_area <= 0 or len(contributing) == 0:
        raise ValueError(f"Site polygon does not intersect any analysis tiles (site_id={site_id})")

    for item in contributing:
        item.share_pct = round((item.weight_area / total_intersection_area) * 100.0, 2)
    contributing.sort(key=lambda t: t.weight_area, reverse=True)

    weighted_val = weighted_val_sum / total_intersection_area
    coverage_pct = round(min((total_intersection_area / site_area) * 100.0, 100.0), 2)

    return SiteClippingResult(
        site_id=site_id,
        coverage_pct=coverage_pct,
        contributing_tile_count=len(contributing),
        weighted_average_temperature_c=0.0,
        weighted_min_temperature_c=0.0,
        weighted_max_temperature_c=0.0,
        weighted_diurnal_swing_c=0.0,
        weighted_value=round(weighted_val, 4),
        contributing_tiles=contributing,
    )

"""Service for extracting and validating metrics from raw FortyGuard API responses."""

from __future__ import annotations

import math
import statistics
from typing import Any

from backend.models.thermal import (
    AnalysisMetrics,
    EnvironmentalMetrics,
    SatelliteMetrics,
    SpatialTemperatureStats,
    c_to_f,
)


def extract_tcm_metrics(response_or_result: dict[str, Any]) -> SpatialTemperatureStats:
    """Extract spatial statistics directly from FortyGuard TCM heatmap tile features.

    Note on FortyGuard API behavior:
    The response's `stats_data.temperature_stats` summarizes the `average_temperature`
    distribution across tiles, NOT the peak temperatures (`max_temperature`). Therefore,
    all metrics must be computed directly from `features[].properties` as the authoritative
    source of truth.

    Parameters
    ----------
    response_or_result:
        Raw FortyGuard response dictionary or inner result dictionary containing `map_data`.

    Returns
    -------
    SpatialTemperatureStats
        Comprehensive spatial statistics across the tile layer.

    Raises
    ------
    ValueError
        If the response structure is missing `map_data`, contains empty features,
        or features lack required temperature properties.
    """
    if not isinstance(response_or_result, dict):
        raise ValueError(f"Expected dictionary response, got {type(response_or_result).__name__}")

    # Unpack inner result if full response wrapper is provided
    result = response_or_result.get("result", response_or_result)
    if not isinstance(result, dict):
        raise ValueError("Invalid response: 'result' must be a dictionary")

    # Locate map_data FeatureCollection
    map_data = result.get("map_data")
    if map_data is None:
        if result.get("type") == "FeatureCollection":
            map_data = result
        else:
            raise ValueError("Response is missing required 'map_data' FeatureCollection")

    features = map_data.get("features")
    if not isinstance(features, list) or len(features) == 0:
        raise ValueError("Heatmap contains no tile features ('features' is empty or missing)")

    avg_temps: list[float] = []
    min_temps: list[float] = []
    max_temps: list[float] = []
    diurnal_swings: list[float] = []

    for idx, feature in enumerate(features):
        if not isinstance(feature, dict):
            raise ValueError(f"Tile feature #{idx} is not a valid GeoJSON feature dictionary")

        props = feature.get("properties")
        if not isinstance(props, dict):
            raise ValueError(f"Tile feature #{idx} is missing 'properties' dictionary")

        if "average_temperature" in props and "min_temperature" in props and "max_temperature" in props:
            try:
                avg_t = float(props["average_temperature"])
                min_t = float(props["min_temperature"])
                max_t = float(props["max_temperature"])
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Tile feature #{idx} contains non-numeric temperature values: {props}") from exc

            avg_temps.append(avg_t)
            min_temps.append(min_t)
            max_temps.append(max_t)
            diurnal_swings.append(max_t - min_t)
        elif "temperature" in props:
            try:
                t = float(props["temperature"])
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Tile feature #{idx} contains non-numeric 'temperature': {props}") from exc
            avg_temps.append(t)
            min_temps.append(t)
            max_temps.append(t)
            diurnal_swings.append(0.0)
        else:
            raise ValueError(
                f"Tile feature #{idx} is missing required temperature properties "
                f"('average_temperature', 'min_temperature', 'max_temperature' or 'temperature'). "
                f"Found keys: {list(props.keys())}"
            )

    n_tiles = len(avg_temps)
    if n_tiles == 0:
        raise ValueError("No valid temperature tiles were parsed")

    def _std(vals: list[float]) -> float:
        return statistics.stdev(vals) if len(vals) > 1 else 0.0

    return SpatialTemperatureStats(
        tile_count=n_tiles,
        mean_average_temp_c=round(statistics.mean(avg_temps), 4),
        min_average_temp_c=round(min(avg_temps), 4),
        max_average_temp_c=round(max(avg_temps), 4),
        std_average_temp_c=round(_std(avg_temps), 4),
        mean_max_temp_c=round(statistics.mean(max_temps), 4),
        min_max_temp_c=round(min(max_temps), 4),
        max_max_temp_c=round(max(max_temps), 4),
        std_max_temp_c=round(_std(max_temps), 4),
        mean_min_temp_c=round(statistics.mean(min_temps), 4),
        min_min_temp_c=round(min(min_temps), 4),
        max_min_temp_c=round(max(min_temps), 4),
        std_min_temp_c=round(_std(min_temps), 4),
        mean_diurnal_swing_c=round(statistics.mean(diurnal_swings), 4),
    )


def extract_analysis_metrics(response_or_result: dict[str, Any]) -> AnalysisMetrics:
    """Extract metrics from a FortyGuard analysis heatmap (exceedance, persistence, time_of_measure).

    Parameters
    ----------
    response_or_result:
        Raw FortyGuard response dictionary or inner result dictionary.

    Returns
    -------
    AnalysisMetrics
        Parsed analysis metadata, summary statistics, and tile values.

    Raises
    ------
    ValueError
        If the response is malformed, features are missing, or properties are invalid.
    """
    if not isinstance(response_or_result, dict):
        raise ValueError(f"Expected dictionary response, got {type(response_or_result).__name__}")

    result = response_or_result.get("result", response_or_result)
    if not isinstance(result, dict):
        raise ValueError("Invalid response: 'result' must be a dictionary")

    stats_data = result.get("stats_data", {})
    analytic_type = stats_data.get("analytic_type")

    map_data = result.get("map_data")
    if map_data is None:
        if result.get("type") == "FeatureCollection":
            map_data = result
        else:
            raise ValueError("Response is missing required 'map_data' FeatureCollection")

    features = map_data.get("features", [])
    if not isinstance(features, list) or len(features) == 0:
        raise ValueError("Analysis heatmap contains no tile features")

    values: list[float] = []
    for idx, feature in enumerate(features):
        props = feature.get("properties", {})
        if "value" not in props or props["value"] is None:
            raise ValueError(f"Analysis tile feature #{idx} is missing 'properties.value'")
        try:
            values.append(float(props["value"]))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Analysis tile feature #{idx} contains non-numeric value: {props['value']}") from exc

    if not analytic_type:
        analytic_type = "unknown_analysis"

    units = stats_data.get("units", "hour")

    return AnalysisMetrics(
        analytic_type=analytic_type,
        units=units,
        tile_count=len(values),
        min_value=round(min(values), 4),
        mean_value=round(statistics.mean(values), 4),
        max_value=round(max(values), 4),
        tile_values=values,
    )


def extract_environmental_metrics(response_or_result: dict[str, Any]) -> EnvironmentalMetrics:
    """Extract point-level environmental metrics with strict protection against heat-index artifacts.

    API Quirk Protection:
    The FortyGuard `/v1/env_params` endpoint applies the supplied `temperature` anchor
    across all 24 hours while varying relative humidity. Consequently, `heat_index_celsius`
    falsely peaks overnight (02:00–05:00 AM) when RH is high.

    To remain physically sound:
    1. We find the true afternoon hot-hour where `apparent_temperature_celsius` peaks.
    2. We evaluate `heat_index_celsius` strictly AT that hot hour.
    3. We extract wet-bulb temperature distributions for cooling tower heat rejection.

    Parameters
    ----------
    response_or_result:
        Raw FortyGuard response dictionary or inner result dictionary from `/v1/env_params`.

    Returns
    -------
    EnvironmentalMetrics
        Validated environmental metrics model.

    Raises
    ------
    ValueError
        If the response is missing required locations or time-series arrays.
    """
    if not isinstance(response_or_result, dict):
        raise ValueError(f"Expected dictionary response, got {type(response_or_result).__name__}")

    result = response_or_result.get("result", response_or_result)
    if not isinstance(result, dict):
        raise ValueError("Invalid response: 'result' must be a dictionary")

    metadata = result.get("metadata", {})
    timestamps = metadata.get("timestamps", [])

    locations = result.get("locations")
    if not isinstance(locations, list) or len(locations) == 0:
        raise ValueError("Environmental response is missing 'locations' list")

    location = locations[0]
    params = location.get("parameters", {})

    def _get_series(name: str) -> list[float]:
        val = params.get(name)
        if isinstance(val, list):
            return [float(x) for x in val if x is not None]
        elif isinstance(val, (int, float)):
            return [float(val)]
        return []

    apparent_series = _get_series("apparent_temperature_celsius")
    wet_bulb_series = _get_series("wet_bulb_temperature_celsius")
    rh_series = _get_series("relative_humidity_percent")
    heat_index_series = _get_series("heat_index_celsius")
    aqi_series = _get_series("air_quality:idx")

    if not apparent_series:
        raise ValueError("Environmental parameters missing 'apparent_temperature_celsius' series")
    if not wet_bulb_series:
        raise ValueError("Environmental parameters missing 'wet_bulb_temperature_celsius' series")
    if not rh_series:
        raise ValueError("Environmental parameters missing 'relative_humidity_percent' series")

    # 1. Find true hot-hour where apparent temperature peaks
    peak_apparent_c = max(apparent_series)
    hot_hour_idx = apparent_series.index(peak_apparent_c)

    if hot_hour_idx < len(timestamps):
        hot_hour_time = str(timestamps[hot_hour_idx])
    else:
        hot_hour_time = f"{hot_hour_idx:02d}:00"

    # 2. Evaluate heat index strictly at the true hot hour (avoiding nighttime artifact)
    peak_hi_c: float | None = None
    peak_hi_time: str | None = None
    if heat_index_series and hot_hour_idx < len(heat_index_series):
        peak_hi_c = round(heat_index_series[hot_hour_idx], 2)
        peak_hi_time = hot_hour_time

    # 3. Wet-bulb metrics (critical for data center evaporative cooling)
    peak_wb_c = round(max(wet_bulb_series), 2)
    mean_wb_c = round(statistics.mean(wet_bulb_series), 2)
    min_wb_c = round(min(wet_bulb_series), 2)

    peak_rh = round(max(rh_series), 2)
    peak_aqi = round(max(aqi_series), 2) if aqi_series else None

    # Solar irradiance
    solar_clear_sky = (location.get("solar_irradiance") or {}).get("clear_sky") or {}
    ghi = float(solar_clear_sky["ghi"]) if "ghi" in solar_clear_sky else None

    return EnvironmentalMetrics(
        peak_apparent_temperature_c=round(peak_apparent_c, 2),
        peak_apparent_temperature_f=c_to_f(peak_apparent_c) or 0.0,
        peak_apparent_temperature_time=hot_hour_time,
        peak_wet_bulb_temperature_c=peak_wb_c,
        peak_wet_bulb_temperature_f=c_to_f(peak_wb_c) or 0.0,
        mean_wet_bulb_temperature_c=mean_wb_c,
        mean_wet_bulb_temperature_f=c_to_f(mean_wb_c) or 0.0,
        minimum_wet_bulb_temperature_c=min_wb_c,
        minimum_wet_bulb_temperature_f=c_to_f(min_wb_c) or 0.0,
        peak_relative_humidity_percent=peak_rh,
        peak_heat_index_c=peak_hi_c,
        peak_heat_index_f=c_to_f(peak_hi_c),
        peak_heat_index_time=peak_hi_time,
        peak_aqi=peak_aqi,
        solar_irradiance_ghi=ghi,
    )


def extract_satellite_metrics(response_or_result: dict[str, Any]) -> SatelliteMetrics:
    """Extract and categorize land-cover surface coverage percentages from /v1/satellite.

    Parameters
    ----------
    response_or_result:
        Raw FortyGuard response dictionary or inner result dictionary from `/v1/satellite`.

    Returns
    -------
    SatelliteMetrics
        Categorized surface composition model.

    Raises
    ------
    ValueError
        If the response is missing segmentation data or segments dictionary.
    """
    if not isinstance(response_or_result, dict):
        raise ValueError(f"Expected dictionary response, got {type(response_or_result).__name__}")

    result = response_or_result.get("result", response_or_result)
    if not isinstance(result, dict):
        raise ValueError("Invalid response: 'result' must be a dictionary")

    seg_dict = result.get("segmentation") or {}
    segments_raw = seg_dict.get("segments")
    if not isinstance(segments_raw, dict):
        raise ValueError("Satellite response missing 'segmentation.segments' dictionary")

    segments: dict[str, float] = {k: float(v) for k, v in segments_raw.items()}

    def _share(*names: str) -> float:
        return sum(
            v for k, v in segments.items()
            if any(n in k.lower() for n in names)
        )

    impervious = _share("building", "road", "route", "sidewalk", "pavement", "car", "truck", "fence")
    vegetation = _share("tree", "grass", "plant", "vegetation")
    building = _share("building")
    road = _share("road", "route")
    pavement = _share("sidewalk", "pavement")
    tree = _share("tree")
    bare_ground = _share("earth", "ground", "soil", "sand")

    return SatelliteMetrics(
        impervious_pct=round(impervious, 2),
        vegetation_pct=round(vegetation, 2),
        building_pct=round(building, 2),
        road_pct=round(road, 2),
        pavement_pct=round(pavement, 2),
        tree_pct=round(tree, 2),
        bare_ground_pct=round(bare_ground, 2),
        raw_segments=segments,
        image_year=result.get("image_year"),
    )

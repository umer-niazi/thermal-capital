import React, { useEffect, useMemo, useRef, useState } from "react";
import maplibregl, { Map as MapLibreMap, NavigationControl } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import {
  AppMode,
  CityConfig,
  HeatmapLayerType,
  PlacedIntervention,
  PlacedInterventionType,
  PublicAsset,
  ScenarioViewMode,
  SimulationResponse,
  TemperatureUnit,
} from "../types";
import {
  celsiusToFahrenheit,
  formatCurrency,
  getAssetTypeLabel,
  getRiskColor,
} from "../utils/formatters";
import { useTemperature } from "../context/TemperatureContext";
import { createGeoJSONCircle } from "../utils/geoUtils";
import {
  getDistanceMeters,
  validateInterventionPlacement,
} from "../utils/spatialValidation";
import {
  ChevronUp,
  Crosshair,
  Layers,
  Sun,
  Thermometer,
  Trees,
  Umbrella,
  X,
} from "lucide-react";

interface MapViewerProps {
  cityConfig: CityConfig;
  assets: PublicAsset[];
  selectedAssetId: string | null;
  onSelectAsset: (assetId: string) => void;
  appMode: AppMode;
  onSwitchMode?: (mode: AppMode) => void;
  activeLayer: HeatmapLayerType;
  onChangeLayer: (layer: HeatmapLayerType) => void;
  heatmapGeoJSON: GeoJSON.FeatureCollection | null;
  activeSimulation?: SimulationResponse | null;
  placedInterventions?: PlacedIntervention[];
  onAddIntervention?: (item: Omit<PlacedIntervention, "id" | "created_at">) => void;
  onRemoveIntervention?: (id: string) => void;
  activePlacementTool?: PlacedInterventionType | null;
  onSelectPlacementTool?: (tool: PlacedInterventionType | null) => void;
}

interface LayerConfig {
  label: string;
  shortLabel: string;
  description: string;
  units: string;
  min: number;
  max: number;
  stops: [number, string][];
}

export function getLayerConfigs(unit: TemperatureUnit = "F"): Record<HeatmapLayerType, LayerConfig> {
  return {
    tcm_peak: {
      label: "Peak Heat Exposure",
      shortLabel: "Peak Temp",
      description: "Afternoon peak ambient temperature during study period (100m grid)",
      units: unit === "F" ? "°F" : "°C",
      min: 28.0,
      max: 37.0,
      stops: [
        [28.0, "#fef9c3"],
        [31.5, "#fde047"],
        [33.5, "#fb923c"],
        [35.0, "#ea580c"],
        [36.5, "#dc2626"],
      ],
    },
    tcm_mean: {
      label: "Daily Average Temperature",
      shortLabel: "Daily Mean",
      description: "24-hour mean temperature baseline (100m grid)",
      units: unit === "F" ? "°F" : "°C",
      min: 24.0,
      max: 32.0,
      stops: [
        [24.0, "#fef9c3"],
        [26.5, "#fde047"],
        [28.5, "#fb923c"],
        [30.0, "#ea580c"],
        [31.5, "#dc2626"],
      ],
    },
    exceedance: {
      label: unit === "F" ? "Hours Above 95°F" : "Hours Above 35°C",
      shortLabel: "Exceedance",
      description:
        unit === "F"
          ? "Cumulative hours exceeding 95°F (35°C) threshold"
          : "Cumulative hours exceeding 35°C (95°F) threshold",
      units: "hours",
      min: 0,
      max: 15,
      stops: [
        [0, "#16a34a"],
        [3, "#eab308"],
        [7, "#ea580c"],
        [12, "#dc2626"],
      ],
    },
    persistence: {
      label: "Heat Persistence",
      shortLabel: "Persistence",
      description:
        unit === "F"
          ? "Longest continuous unbroken hours above 95°F without relief"
          : "Longest continuous unbroken hours above 35°C without relief",
      units: "hours",
      min: 0,
      max: 6,
      stops: [
        [0, "#16a34a"],
        [1.5, "#eab308"],
        [3.5, "#ea580c"],
        [5.5, "#dc2626"],
      ],
    },
    cooling: {
      label: "Cooling Degree Hours",
      shortLabel: "Cooling Burden",
      description:
        unit === "F"
          ? "Cumulative cooling demand above 68°F baseline"
          : "Cumulative cooling demand above 20°C baseline",
      units: "CDH",
      min: 400,
      max: 1300,
      stops: [
        [400, "#fef9c3"],
        [700, "#fde047"],
        [950, "#fb923c"],
        [1150, "#ea580c"],
        [1300, "#dc2626"],
      ],
    },
  };
}

export function getBaseMapStyle(apiKey?: string): maplibregl.StyleSpecification {
  const envKey = (import.meta as any).env?.VITE_CARTO_API_KEY as string | undefined;
  const key = apiKey ?? envKey ?? "";
  const query = key.trim() ? `?key=${encodeURIComponent(key.trim())}` : "";
  return {
    version: 8,
    glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
    sources: {
      "carto-positron": {
        type: "raster",
        tiles: [
          `https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png${query}`,
          `https://b.basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png${query}`,
        ],
        tileSize: 256,
        attribution: "&copy; OpenStreetMap contributors &copy; CARTO",
      },
    },
    layers: [
      {
        id: "carto-positron-layer",
        type: "raster",
        source: "carto-positron",
        minzoom: 0,
        maxzoom: 19,
      },
    ],
  };
}

export const BASE_MAP_STYLE: maplibregl.StyleSpecification = getBaseMapStyle();

export const MAP_LAYER_ORDER = [
  "heatmap-tiles-fill",
  "heatmap-tiles-line",
  "interventions-reflective-fill",
  "interventions-reflective-line",
  "interventions-trees-radius-fill",
  "interventions-trees-radius-line",
  "interventions-trees-circle",
  "interventions-shade-circle",
  "assets-clusters-circle",
  "assets-clusters-count",
  "assets-selection-halo",
  "assets-risk-circle",
  "assets-inner-dot",
  "assets-symbol-label",
] as const;

export function addLayerInOrder(
  map: maplibregl.Map,
  layerDef: any
): void {
  if (map.getLayer(layerDef.id)) return;
  const targetIdx = MAP_LAYER_ORDER.indexOf(layerDef.id as any);
  let beforeId: string | undefined = undefined;
  if (targetIdx !== -1) {
    for (let i = targetIdx + 1; i < MAP_LAYER_ORDER.length; i++) {
      const candidateId = MAP_LAYER_ORDER[i];
      if (map.getLayer(candidateId)) {
        beforeId = candidateId;
        break;
      }
    }
  }
  map.addLayer(layerDef, beforeId);
}

export function enforceMapLayerOrder(map: maplibregl.Map): void {
  const activeCustomLayers = MAP_LAYER_ORDER.filter((id) => !!map.getLayer(id));
  for (const layerId of activeCustomLayers) {
    try {
      map.moveLayer(layerId);
    } catch {
      // ignore during style updates
    }
  }
}

export const MapViewer: React.FC<MapViewerProps> = ({
  cityConfig,
  assets,
  selectedAssetId,
  onSelectAsset,
  appMode,
  activeLayer,
  onChangeLayer,
  heatmapGeoJSON,
  activeSimulation,
  placedInterventions = [],
  onAddIntervention,
  onRemoveIntervention,
  activePlacementTool = null,
  onSelectPlacementTool,
}) => {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [assetFilter, setAssetFilter] = useState<string>("all");
  const [scenarioViewMode, setScenarioViewMode] = useState<ScenarioViewMode>("baseline");
  const [isMobileLegendOpen, setIsMobileLegendOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const toastTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const { unit, formatTemp, formatDelta } = useTemperature();

  const layerConfigs = useMemo(() => getLayerConfigs(unit), [unit]);
  const layerCfg = layerConfigs[activeLayer] || layerConfigs.tcm_peak;

  // Automatically switch to scenario view mode if user is testing interventions in plan mode
  useEffect(() => {
    if (appMode === "plan" && placedInterventions.length > 0) {
      setScenarioViewMode("scenario");
    }
  }, [appMode, placedInterventions.length]);

  // Construct Scenario-Adjusted Heatmap GeoJSON (Preserving baseline FortyGuard data)
  const renderedHeatmapGeoJSON = useMemo(() => {
    if (!heatmapGeoJSON) return null;
    if (scenarioViewMode === "baseline" || placedInterventions.length === 0) {
      return heatmapGeoJSON;
    }

    return {
      ...heatmapGeoJSON,
      features: heatmapGeoJSON.features.map((feat) => {
        const props = { ...feat.properties };
        const geom = feat.geometry;
        if (!geom || geom.type !== "Polygon" || !geom.coordinates || !geom.coordinates[0]) {
          return feat;
        }

        // Calculate tile centroid
        const ring = geom.coordinates[0];
        let sumLng = 0;
        let sumLat = 0;
        for (const coord of ring) {
          sumLng += coord[0];
          sumLat += coord[1];
        }
        const centerLng = sumLng / ring.length;
        const centerLat = sumLat / ring.length;

        // Calculate localized cooling influence from nearby placed interventions
        let nearTreeCount = 0;
        let nearShadeCount = 0;
        let nearPaveArea = 0;

        for (const item of placedInterventions) {
          const distM = getDistanceMeters(centerLat, centerLng, item.latitude, item.longitude);
          // Tree cooling influence envelope (~35m radius from 100m cell center)
          if (item.type === "tree" && distM < 45.0) {
            nearTreeCount += 1;
          } else if (item.type === "shade" && distM < 50.0) {
            nearShadeCount += 1;
          } else if (item.type === "reflective" && distM < 60.0) {
            nearPaveArea += item.area_m2 || 200;
          }
        }

        let totalCoolingC = 0.0;
        if (nearTreeCount > 0 || nearShadeCount > 0 || nearPaveArea > 0) {
          const treeDelta = 3.2 * (1.0 - Math.exp(-0.065 * nearTreeCount));
          const shadeDelta = 2.8 * (1.0 - Math.exp(-0.45 * nearShadeCount));
          const paveDelta = 1.8 * (1.0 - Math.exp(-0.0028 * nearPaveArea));
          const rawDelta = treeDelta + shadeDelta + paveDelta;
          totalCoolingC = Math.min(3.8, 3.8 * (1.0 - Math.exp(-rawDelta / 3.4)));
        }

        if (totalCoolingC > 0.05) {
          const origColorMetric = Number(props.color_metric ?? props.value ?? props.peak_c ?? 38.0);
          const origPeakC = Number(props.peak_c ?? origColorMetric);
          const newPeakC = Math.max(24.0, origPeakC - totalCoolingC);

          // Adjust color metric depending on active layer
          if (activeLayer === "tcm_peak" || activeLayer === "tcm_mean") {
            props.color_metric = Math.max(24.0, origColorMetric - totalCoolingC);
            props.display_value = `${formatTemp(origColorMetric - totalCoolingC)} (↓ ${formatDelta(totalCoolingC, 1, "")} modeled)`;
          } else if (activeLayer === "exceedance") {
            const redPct = Math.min(60.0, totalCoolingC * 16.0);
            const origExc = Number(props.color_metric ?? 6.0);
            props.color_metric = Math.max(0.0, origExc * (1.0 - redPct / 100.0));
            props.display_value = `${props.color_metric.toFixed(1)}h (↓ ${redPct.toFixed(0)}% modeled)`;
          } else if (activeLayer === "persistence") {
            const redPct = Math.min(45.0, totalCoolingC * 12.0);
            const origPer = Number(props.color_metric ?? 4.0);
            props.color_metric = Math.max(0.5, origPer * (1.0 - redPct / 100.0));
            props.display_value = `${props.color_metric.toFixed(1)}h (↓ ${redPct.toFixed(0)}% modeled)`;
          }

          props.is_modeled_scenario = true;
          props.modeled_delta_c = totalCoolingC;
          props.scenario_peak_c = newPeakC;
        }

        return {
          ...feat,
          properties: props,
        };
      }),
    };
  }, [heatmapGeoJSON, scenarioViewMode, placedInterventions, activeLayer]);

  // Dynamically compute heatmap range and color ramp from actual data being displayed
  const dynamicLayerStats = useMemo(() => {
    if (!renderedHeatmapGeoJSON || renderedHeatmapGeoJSON.features.length === 0) {
      return {
        min: layerCfg.min,
        max: layerCfg.max,
        stops: layerCfg.stops,
      };
    }

    const values: number[] = [];
    for (const f of renderedHeatmapGeoJSON.features) {
      const v = Number(f.properties?.color_metric ?? f.properties?.value ?? f.properties?.peak_c);
      if (!isNaN(v) && isFinite(v)) {
        values.push(v);
      }
    }

    if (values.length === 0) {
      return {
        min: layerCfg.min,
        max: layerCfg.max,
        stops: layerCfg.stops,
      };
    }

    values.sort((a, b) => a - b);
    const minVal = values[0];
    const maxVal = values[values.length - 1];

    const colors = layerCfg.stops.map((s) => s[1]);
    const numStops = colors.length;

    // Use percentile distribution (5th, 25th, 50th, 75th, 98th percentile) for rich spatial differentiation
    const stops: [number, string][] = colors.map((color, idx) => {
      let pct: number;
      if (idx === 0) pct = 0.05;
      else if (idx === numStops - 1) pct = 0.98;
      else pct = idx / (numStops - 1);

      const valIdx = Math.min(values.length - 1, Math.max(0, Math.floor(values.length * pct)));
      const stopVal = Number(values[valIdx].toFixed(1));
      return [stopVal, color];
    });

    return {
      min: Number(minVal.toFixed(1)),
      max: Number(maxVal.toFixed(1)),
      stops,
    };
  }, [renderedHeatmapGeoJSON, layerCfg]);

  // Initialize MapLibre
  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: BASE_MAP_STYLE,
      center: cityConfig.center,
      zoom: cityConfig.zoom,
      maxZoom: 18,
      minZoom: 4,
      attributionControl: false,
    });

    map.addControl(new NavigationControl({ showCompass: true }), "top-right");

    map.on("load", () => {
      mapRef.current = map;
      setMapLoaded(true);
      map.fitBounds(cityConfig.bounds, { padding: 40, duration: 800 });
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Update map bounds when city changes
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded) return;

    map.fitBounds(cityConfig.bounds, { padding: 40, duration: 1000 });
  }, [cityConfig.city_key, mapLoaded]);

  // Click on map to place intervention when activePlacementTool is active
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded) return;

    const handleMapClick = (e: maplibregl.MapMouseEvent) => {
      if (!activePlacementTool || !onAddIntervention) return;

      const selectedAsset = assets.find((a) => a.asset_id === selectedAssetId);
      const validation = validateInterventionPlacement(
        activePlacementTool,
        e.lngLat,
        e.point,
        map,
        placedInterventions,
        selectedAsset
      );

      if (!validation.valid) {
        setToastMessage(validation.reason || "Cannot place intervention here.");
        if (toastTimeoutRef.current) clearTimeout(toastTimeoutRef.current);
        toastTimeoutRef.current = setTimeout(() => setToastMessage(null), 3500);
        return;
      }

      // Find closest asset within reasonable radius (approx 0.01 deg)
      let closestAssetId: string | null = selectedAssetId;
      if (assets.length > 0) {
        let minDist = Infinity;
        for (const a of assets) {
          const d = Math.hypot(a.latitude - e.lngLat.lat, a.longitude - e.lngLat.lng);
          if (d < minDist) {
            minDist = d;
            if (d < 0.01) {
              closestAssetId = a.asset_id;
            }
          }
        }
      }

      onAddIntervention({
        type: activePlacementTool,
        latitude: e.lngLat.lat,
        longitude: e.lngLat.lng,
        asset_id: closestAssetId,
        area_m2: activePlacementTool === "reflective" ? 200 : undefined,
        label: `Proposed ${activePlacementTool === "tree" ? "Tree" : activePlacementTool === "shade" ? "Shade Structure" : "Reflective Surface"}`,
      });
    };

    map.on("click", handleMapClick);

    if (activePlacementTool) {
      map.getCanvas().style.cursor = "crosshair";
    } else {
      map.getCanvas().style.cursor = "";
    }

    return () => {
      map.off("click", handleMapClick);
    };
  }, [activePlacementTool, onAddIntervention, selectedAssetId, assets, mapLoaded, placedInterventions]);

  // Escape key cancels placement tool
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && activePlacementTool && onSelectPlacementTool) {
        onSelectPlacementTool(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [activePlacementTool, onSelectPlacementTool]);

  // Construct Public Assets GeoJSON FeatureCollection
  const filteredAssets = assetFilter === "all" ? assets : assets.filter((a) => a.asset_type === assetFilter);

  const assetsGeoJSON: GeoJSON.FeatureCollection = {
    type: "FeatureCollection",
    features: filteredAssets.map((a) => {
      const risk = getRiskColor(a.heat_risk_level);
      const isSelected = a.asset_id === selectedAssetId;

      return {
        type: "Feature",
        properties: {
          asset_id: a.asset_id,
          name: a.name,
          asset_type: a.asset_type,
          type_label: getAssetTypeLabel(a.asset_type),
          heat_risk_level: a.heat_risk_level,
          heat_risk_score: a.heat_risk_score,
          priority_level: a.priority_level || a.heat_risk_level,
          peak_c: a.observed_heat.peak_temperature_c,
          peak_f: a.observed_heat.peak_temperature_f,
          hours_35c: a.observed_heat.hours_above_35c,
          daily_visitors: a.daily_visitors,
          is_selected: isSelected,
          risk_color: risk.halo,
        },
        geometry: a.geometry,
      };
    }),
  };

  // Construct Placed Interventions GeoJSON
  const treesRadiusGeoJSON: GeoJSON.FeatureCollection = {
    type: "FeatureCollection",
    features: placedInterventions
      .filter((i) => i.type === "tree")
      .map((i) => ({
        type: "Feature",
        properties: {
          id: i.id,
          type: "tree_radius",
          title: "Tree Microclimate Influence Zone",
        },
        geometry: {
          type: "Polygon",
          coordinates: [createGeoJSONCircle([i.longitude, i.latitude], 12)],
        },
      })),
  };

  const treesGeoJSON: GeoJSON.FeatureCollection = {
    type: "FeatureCollection",
    features: placedInterventions
      .filter((i) => i.type === "tree")
      .map((i) => ({
        type: "Feature",
        properties: {
          id: i.id,
          type: "tree",
          latitude: i.latitude,
          longitude: i.longitude,
          asset_id: i.asset_id,
          title: "Proposed Street Tree",
          scope: "+25 m² direct canopy (~450 m² cooling influence)",
        },
        geometry: {
          type: "Point",
          coordinates: [i.longitude, i.latitude],
        },
      })),
  };

  const shadeGeoJSON: GeoJSON.FeatureCollection = {
    type: "FeatureCollection",
    features: placedInterventions
      .filter((i) => i.type === "shade")
      .map((i) => ({
        type: "Feature",
        properties: {
          id: i.id,
          type: "shade",
          latitude: i.latitude,
          longitude: i.longitude,
          asset_id: i.asset_id,
          title: "Proposed Shade Structure",
          scope: "+100 m² engineered shade canopy",
        },
        geometry: {
          type: "Point",
          coordinates: [i.longitude, i.latitude],
        },
      })),
  };

  const reflectiveGeoJSON: GeoJSON.FeatureCollection = {
    type: "FeatureCollection",
    features: placedInterventions
      .filter((i) => i.type === "reflective")
      .map((i) => ({
        type: "Feature",
        properties: {
          id: i.id,
          type: "reflective",
          latitude: i.latitude,
          longitude: i.longitude,
          asset_id: i.asset_id,
          title: "Proposed Reflective Cool Pavement",
          scope: `${i.area_m2 || 200} m² high-albedo solar-reflective coating`,
        },
        geometry: {
          type: "Polygon",
          coordinates: [createGeoJSONCircle([i.longitude, i.latitude], 14)],
        },
      })),
  };

  // Update Layers on Map
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded) return;

    const buildColorExpression = (cfg: { min: number; stops: [number, string][] }): any => [
      "interpolate",
      ["linear"],
      ["coalesce", ["get", "color_metric"], cfg.min],
      ...cfg.stops.flatMap((s) => [s[0], s[1]]),
    ];

    // 1. Heatmap Grid Tiles Layer
    if (renderedHeatmapGeoJSON) {
      if (map.getSource("heatmap-source")) {
        (map.getSource("heatmap-source") as maplibregl.GeoJSONSource).setData(renderedHeatmapGeoJSON);
      } else {
        map.addSource("heatmap-source", {
          type: "geojson",
          data: renderedHeatmapGeoJSON,
        });

        // Heatmap fill with zoom-interpolated opacity for clarity at city-wide vs parcel zoom
        addLayerInOrder(map, {
          id: "heatmap-tiles-fill",
          type: "fill",
          source: "heatmap-source",
          paint: {
            "fill-color": buildColorExpression(dynamicLayerStats),
            "fill-opacity": [
              "interpolate",
              ["linear"],
              ["zoom"],
              10, 0.65,
              13, 0.55,
              16, 0.45,
            ],
          },
        });

        // Grid lines with zoom-dependent opacity to prevent white haze at low zoom
        addLayerInOrder(map, {
          id: "heatmap-tiles-line",
          type: "line",
          source: "heatmap-source",
          paint: {
            "line-color": "#ffffff",
            "line-width": 0.5,
            "line-opacity": [
              "interpolate",
              ["linear"],
              ["zoom"],
              10, 0.0,
              12, 0.2,
              14, 0.5,
              16, 0.7,
            ],
          },
        });

        // Click contextual popup on heatmap tiles (only when not in placement mode)
        map.on("click", "heatmap-tiles-fill", (e) => {
          if (activePlacementTool) return;
          // If an asset, cluster, or intervention was clicked at this point, do not show tile popup
          const topFeatures = map.queryRenderedFeatures(e.point, {
            layers: [
              "assets-clusters-circle",
              "assets-clusters-count",
              "assets-risk-circle",
              "assets-inner-dot",
              "assets-selection-halo",
              "assets-symbol-label",
              "interventions-trees-circle",
              "interventions-shade-circle",
              "interventions-reflective-fill",
            ],
          });
          if (topFeatures && topFeatures.length > 0) {
            return;
          }

          if (!e.features || !e.features[0]) return;
          const props = e.features[0].properties;
          const tileCode = props.tile_id !== undefined ? `T-${String(props.tile_id).padStart(5, "0")}` : "T-00001";
          const isScenario = props.is_modeled_scenario === true || props.is_modeled_scenario === "true";

          let popupDisplayValue = props.display_value;
          if (!isScenario) {
            if (activeLayer === "exceedance") {
              const hrs = props.color_metric ?? props.exceedance_hours ?? props.value ?? 0;
              popupDisplayValue = `${Number(hrs).toFixed(1)} hrs > ${unit === "F" ? "95°F" : "35°C"}`;
            } else if (activeLayer === "persistence") {
              const hrs = props.color_metric ?? props.persistence_hours ?? props.value ?? 0;
              popupDisplayValue = `${Number(hrs).toFixed(1)} hrs unbroken`;
            } else if (activeLayer === "tcm_peak") {
              popupDisplayValue = formatTemp(props.color_metric ?? props.peak_c);
            } else if (activeLayer === "tcm_mean") {
              popupDisplayValue = formatTemp(props.color_metric ?? props.mean_c);
            }
          }

          new maplibregl.Popup({ className: "light-popup", closeButton: true, maxWidth: "270px" })
            .setLngLat(e.lngLat)
            .setHTML(
              `
              <div class="text-xs text-slate-900 font-sans space-y-1.5 pr-6">
                <div class="border-b border-slate-200 pb-1 flex items-center justify-between">
                  <span class="font-bold text-slate-900 font-mono text-xs">${tileCode}</span>
                  <span class="text-[11px] ${isScenario ? 'text-brand-700 font-semibold bg-brand-50 px-1.5 py-0.5 rounded border border-brand-200' : 'text-slate-500 font-medium'}">
                    ${isScenario ? 'Modeled Scenario' : 'FortyGuard Baseline'}
                  </span>
                </div>
                <div class="text-slate-700 py-0.5">
                  <span class="text-slate-500">${layerCfg.shortLabel}:</span> <strong class="font-mono text-slate-900">${popupDisplayValue}</strong>
                </div>
                <div class="text-[11px] text-slate-600 space-y-0.5 border-t border-slate-100 pt-1">
                  <div>Baseline peak: <strong class="font-mono text-slate-900">${formatTemp(props.peak_c)}</strong> (${unit === "F" ? (props.peak_c ? Number(props.peak_c).toFixed(1) + "°C" : "—") : (props.peak_f ? Number(props.peak_f).toFixed(1) + "°F" : "—")})</div>
                  ${isScenario && props.scenario_peak_c ? `<div>Modeled scenario peak: <strong class="font-mono text-brand-700 font-bold">${formatTemp(props.scenario_peak_c)} (↓ ${formatDelta(props.modeled_delta_c, 1, "")})</strong></div>` : ""}
                  <div>Mean temperature: <strong class="font-mono text-slate-900">${formatTemp(props.mean_c)}</strong></div>
                  ${props.exceedance_hours !== undefined ? `<div>Hours &gt; ${unit === "F" ? "95°F" : "35°C"}: <strong class="font-mono text-slate-900">${Number(props.exceedance_hours).toFixed(1)}h</strong></div>` : ""}
                </div>
              </div>
            `
            )
            .addTo(map);
        });

        map.on("mouseenter", "heatmap-tiles-fill", () => {
          if (!activePlacementTool) map.getCanvas().style.cursor = "pointer";
        });
        map.on("mouseleave", "heatmap-tiles-fill", () => {
          if (!activePlacementTool) map.getCanvas().style.cursor = "";
        });
      }

      // Update color expression dynamically when active layer or data changes
      if (map.getLayer("heatmap-tiles-fill")) {
        map.setPaintProperty("heatmap-tiles-fill", "fill-color", buildColorExpression(dynamicLayerStats));
      }
    }

    // 2. Reflective Pavement Footprint Layer
    if (map.getSource("reflective-interventions-source")) {
      (map.getSource("reflective-interventions-source") as maplibregl.GeoJSONSource).setData(reflectiveGeoJSON);
    } else {
      map.addSource("reflective-interventions-source", {
        type: "geojson",
        data: reflectiveGeoJSON,
      });

      addLayerInOrder(map, {
        id: "interventions-reflective-fill",
        type: "fill",
        source: "reflective-interventions-source",
        paint: {
          "fill-color": "#f59e0b",
          "fill-opacity": 0.35,
        },
      });

      addLayerInOrder(map, {
        id: "interventions-reflective-line",
        type: "line",
        source: "reflective-interventions-source",
        paint: {
          "line-color": "#d97706",
          "line-width": 1.5,
          "line-dasharray": [2, 2],
        },
      });

      // Click on reflective polygon
      map.on("click", "interventions-reflective-fill", (e) => {
        if (activePlacementTool) return;
        if (!e.features || !e.features[0]) return;
        const props = e.features[0].properties;
        const id = props.id;

        const popup = new maplibregl.Popup({ className: "light-popup", closeButton: true, maxWidth: "260px" })
          .setLngLat(e.lngLat)
          .setHTML(
            `
            <div class="text-xs text-slate-900 font-sans space-y-1.5 pr-6">
              <div class="border-b border-slate-200 pb-1 flex items-center justify-between">
                <span class="font-bold text-slate-900">${props.title}</span>
              </div>
              <div class="text-[11px] text-slate-600 space-y-0.5">
                <div>Scope: <strong class="text-slate-900">${props.scope}</strong></div>
                <div>Location: <span class="font-mono text-slate-700">${Number(props.latitude).toFixed(4)}, ${Number(props.longitude).toFixed(4)}</span></div>
              </div>
              <div class="pt-1.5 border-t border-slate-100 flex justify-end">
                <button id="btn-del-intervention-${id}" class="px-2.5 py-1 bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 rounded text-xs font-medium cursor-pointer transition-colors">
                  Remove
                </button>
              </div>
            </div>
          `
          )
          .addTo(map);

        setTimeout(() => {
          const btn = document.getElementById(`btn-del-intervention-${id}`);
          if (btn) {
            btn.onclick = () => {
              if (onRemoveIntervention) onRemoveIntervention(id);
              popup.remove();
            };
          }
        }, 50);
      });
    }

    // 2.5 Tree Planting Influence Radius Layer
    if (map.getSource("trees-radius-source")) {
      (map.getSource("trees-radius-source") as maplibregl.GeoJSONSource).setData(treesRadiusGeoJSON);
    } else {
      map.addSource("trees-radius-source", {
        type: "geojson",
        data: treesRadiusGeoJSON,
      });

      addLayerInOrder(map, {
        id: "interventions-trees-radius-fill",
        type: "fill",
        source: "trees-radius-source",
        paint: {
          "fill-color": "#16a34a",
          "fill-opacity": 0.15,
        },
      });

      addLayerInOrder(map, {
        id: "interventions-trees-radius-line",
        type: "line",
        source: "trees-radius-source",
        paint: {
          "line-color": "#15803d",
          "line-width": 1,
          "line-dasharray": [2, 2],
          "line-opacity": 0.5,
        },
      });
    }

    // 3. Tree Interventions Layer (Pins)
    if (map.getSource("trees-interventions-source")) {
      (map.getSource("trees-interventions-source") as maplibregl.GeoJSONSource).setData(treesGeoJSON);
    } else {
      map.addSource("trees-interventions-source", {
        type: "geojson",
        data: treesGeoJSON,
      });

      addLayerInOrder(map, {
        id: "interventions-trees-circle",
        type: "circle",
        source: "trees-interventions-source",
        paint: {
          "circle-radius": 7,
          "circle-color": "#16a34a",
          "circle-stroke-width": 2,
          "circle-stroke-color": "#ffffff",
          "circle-opacity": 0.95,
        },
      });

      // Click on tree
      map.on("click", "interventions-trees-circle", (e) => {
        if (activePlacementTool) return;
        if (!e.features || !e.features[0]) return;
        const props = e.features[0].properties;
        const id = props.id;

        const popup = new maplibregl.Popup({ className: "light-popup", closeButton: true, maxWidth: "260px" })
          .setLngLat(e.lngLat)
          .setHTML(
            `
            <div class="text-xs text-slate-900 font-sans space-y-1.5 pr-6">
              <div class="border-b border-slate-200 pb-1 flex items-center justify-between">
                <span class="font-bold text-slate-900">${props.title}</span>
              </div>
              <div class="text-[11px] text-slate-600 space-y-0.5">
                <div>Scope: <strong class="text-slate-900">${props.scope}</strong></div>
                <div>Location: <span class="font-mono text-slate-700">${Number(props.latitude).toFixed(4)}, ${Number(props.longitude).toFixed(4)}</span></div>
              </div>
              <div class="pt-1.5 border-t border-slate-100 flex justify-end">
                <button id="btn-del-intervention-${id}" class="px-2.5 py-1 bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 rounded text-xs font-medium cursor-pointer transition-colors">
                  Remove
                </button>
              </div>
            </div>
          `
          )
          .addTo(map);

        setTimeout(() => {
          const btn = document.getElementById(`btn-del-intervention-${id}`);
          if (btn) {
            btn.onclick = () => {
              if (onRemoveIntervention) onRemoveIntervention(id);
              popup.remove();
            };
          }
        }, 50);
      });
    }

    // 4. Shade Interventions Layer
    if (map.getSource("shade-interventions-source")) {
      (map.getSource("shade-interventions-source") as maplibregl.GeoJSONSource).setData(shadeGeoJSON);
    } else {
      map.addSource("shade-interventions-source", {
        type: "geojson",
        data: shadeGeoJSON,
      });

      addLayerInOrder(map, {
        id: "interventions-shade-circle",
        type: "circle",
        source: "shade-interventions-source",
        paint: {
          "circle-radius": 7,
          "circle-color": "#0284c7",
          "circle-stroke-width": 2,
          "circle-stroke-color": "#ffffff",
          "circle-opacity": 0.95,
        },
      });

      // Click on shade
      map.on("click", "interventions-shade-circle", (e) => {
        if (activePlacementTool) return;
        if (!e.features || !e.features[0]) return;
        const props = e.features[0].properties;
        const id = props.id;

        const popup = new maplibregl.Popup({ className: "light-popup", closeButton: true, maxWidth: "260px" })
          .setLngLat(e.lngLat)
          .setHTML(
            `
            <div class="text-xs text-slate-900 font-sans space-y-1.5 pr-6">
              <div class="border-b border-slate-200 pb-1 flex items-center justify-between">
                <span class="font-bold text-slate-900">${props.title}</span>
              </div>
              <div class="text-[11px] text-slate-600 space-y-0.5">
                <div>Scope: <strong class="text-slate-900">${props.scope}</strong></div>
                <div>Location: <span class="font-mono text-slate-700">${Number(props.latitude).toFixed(4)}, ${Number(props.longitude).toFixed(4)}</span></div>
              </div>
              <div class="pt-1.5 border-t border-slate-100 flex justify-end">
                <button id="btn-del-intervention-${id}" class="px-2.5 py-1 bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 rounded text-xs font-medium cursor-pointer transition-colors">
                  Remove
                </button>
              </div>
            </div>
          `
          )
          .addTo(map);

        setTimeout(() => {
          const btn = document.getElementById(`btn-del-intervention-${id}`);
          if (btn) {
            btn.onclick = () => {
              if (onRemoveIntervention) onRemoveIntervention(id);
              popup.remove();
            };
          }
        }, 50);
      });
    }

    // 5. Public Assets Layer with MapLibre Clustering
    if (map.getSource("assets-source")) {
      (map.getSource("assets-source") as maplibregl.GeoJSONSource).setData(assetsGeoJSON);
    } else {
      map.addSource("assets-source", {
        type: "geojson",
        data: assetsGeoJSON,
        cluster: true,
        clusterMaxZoom: 12,
        clusterRadius: 30,
      });

      // Cluster Circle Layer (Softened visual weight to keep FortyGuard heatmap dominant)
      addLayerInOrder(map, {
        id: "assets-clusters-circle",
        type: "circle",
        source: "assets-source",
        filter: ["has", "point_count"],
        paint: {
          "circle-color": "#334155",
          "circle-radius": [
            "step",
            ["get", "point_count"],
            10,
            5,
            12,
            12,
            15,
          ],
          "circle-stroke-width": 1.5,
          "circle-stroke-color": "#ffffff",
          "circle-opacity": 0.85,
        },
      });

      // Cluster Count Symbol Layer (Crisp, centered two-digit counts)
      addLayerInOrder(map, {
        id: "assets-clusters-count",
        type: "symbol",
        source: "assets-source",
        filter: ["has", "point_count"],
        layout: {
          "text-field": ["get", "point_count_abbreviated"],
          "text-font": ["Open Sans Regular", "Arial Unicode MS Regular"],
          "text-size": 10,
          "text-allow-overlap": true,
          "text-ignore-placement": true,
        },
        paint: {
          "text-color": "#ffffff",
        },
      });

      // Expand cluster on click (bound to both circle and count label)
      const handleClusterClick = (e: maplibregl.MapMouseEvent) => {
        if (activePlacementTool) return;
        const features = map.queryRenderedFeatures(e.point, {
          layers: ["assets-clusters-circle", "assets-clusters-count"],
        });
        if (!features || !features[0]) return;

        const clusterId = features[0]?.properties?.cluster_id;
        const source = map.getSource("assets-source") as any;
        if (source && clusterId !== undefined && source.getClusterExpansionZoom) {
          source.getClusterExpansionZoom(clusterId, (err: any, zoom: number) => {
            if (err) return;
            const coords = (features[0].geometry as any).coordinates;
            map.easeTo({
              center: coords,
              zoom: Math.max(zoom, map.getZoom() + 2),
              duration: 500,
            });
          });
        }
      };

      map.on("click", "assets-clusters-circle", handleClusterClick);
      map.on("click", "assets-clusters-count", handleClusterClick);

      const setClusterPointer = () => {
        if (!activePlacementTool) map.getCanvas().style.cursor = "pointer";
      };
      const resetClusterPointer = () => {
        if (!activePlacementTool) map.getCanvas().style.cursor = "";
      };

      map.on("mouseenter", "assets-clusters-circle", setClusterPointer);
      map.on("mouseleave", "assets-clusters-circle", resetClusterPointer);
      map.on("mouseenter", "assets-clusters-count", setClusterPointer);
      map.on("mouseleave", "assets-clusters-count", resetClusterPointer);

      // Unclustered Asset Outer Selection Focus Ring
      addLayerInOrder(map, {
        id: "assets-selection-halo",
        type: "circle",
        source: "assets-source",
        filter: ["!has", "point_count"],
        paint: {
          "circle-radius": 14,
          "circle-color": "transparent",
          "circle-stroke-width": [
            "case",
            ["==", ["get", "asset_id"], selectedAssetId || ""],
            2.5,
            0,
          ],
          "circle-stroke-color": "#0f172a",
        },
      });

      // Unclustered Asset Risk Circle
      addLayerInOrder(map, {
        id: "assets-risk-circle",
        type: "circle",
        source: "assets-source",
        filter: ["!has", "point_count"],
        paint: {
          "circle-radius": [
            "case",
            ["==", ["get", "asset_id"], selectedAssetId || ""],
            8.5,
            7,
          ],
          "circle-color": ["coalesce", ["get", "risk_color"], "#dc2626"],
          "circle-stroke-width": 2,
          "circle-stroke-color": "#ffffff",
          "circle-opacity": 0.95,
        },
      });

      // Unclustered Asset Inner Center Dot
      addLayerInOrder(map, {
        id: "assets-inner-dot",
        type: "circle",
        source: "assets-source",
        filter: ["!has", "point_count"],
        paint: {
          "circle-radius": [
            "case",
            ["==", ["get", "asset_id"], selectedAssetId || ""],
            3,
            2,
          ],
          "circle-color": "#ffffff",
        },
      });

      // Asset text label (with crisp halo for high contrast over red/orange tiles)
      addLayerInOrder(map, {
        id: "assets-symbol-label",
        type: "symbol",
        source: "assets-source",
        filter: ["!has", "point_count"],
        layout: {
          "text-field": ["get", "name"],
          "text-font": ["Open Sans Regular", "Arial Unicode MS Regular"],
          "text-size": 11,
          "text-offset": [0, 1.25],
          "text-anchor": "top",
          "text-max-width": 12,
          "text-allow-overlap": false,
          "text-ignore-placement": false,
        },
        paint: {
          "text-color": "#0f172a",
          "text-halo-color": "#ffffff",
          "text-halo-width": 2.5,
          "text-halo-blur": 0.5,
        },
      });

      // Click on unclustered asset (bound to circles, halo, and label)
      const handleAssetClick = (e: maplibregl.MapMouseEvent) => {
        if (activePlacementTool) return;
        const features = map.queryRenderedFeatures(e.point, {
          layers: ["assets-risk-circle", "assets-inner-dot", "assets-selection-halo", "assets-symbol-label"],
        });
        if (!features || !features[0]) return;
        const aId = features[0].properties?.asset_id;
        if (aId) onSelectAsset(aId);
      };

      map.on("click", "assets-risk-circle", handleAssetClick);
      map.on("click", "assets-inner-dot", handleAssetClick);
      map.on("click", "assets-selection-halo", handleAssetClick);
      map.on("click", "assets-symbol-label", handleAssetClick);

      const setAssetPointer = () => {
        if (!activePlacementTool) map.getCanvas().style.cursor = "pointer";
      };
      const resetAssetPointer = () => {
        if (!activePlacementTool) map.getCanvas().style.cursor = "";
      };

      map.on("mouseenter", "assets-risk-circle", setAssetPointer);
      map.on("mouseleave", "assets-risk-circle", resetAssetPointer);
      map.on("mouseenter", "assets-symbol-label", setAssetPointer);
      map.on("mouseleave", "assets-symbol-label", resetAssetPointer);
    }

    // Dynamic selection styling
    if (map.getLayer("assets-selection-halo")) {
      map.setPaintProperty("assets-selection-halo", "circle-stroke-width", [
        "case",
        ["==", ["get", "asset_id"], selectedAssetId || ""],
        2.5,
        0,
      ]);
    }
    if (map.getLayer("assets-risk-circle")) {
      map.setPaintProperty("assets-risk-circle", "circle-radius", [
        "case",
        ["==", ["get", "asset_id"], selectedAssetId || ""],
        8.5,
        7,
      ]);
    }

    // Enforce deterministic layer order (heatmap below interventions and asset markers)
    enforceMapLayerOrder(map);
  }, [
    renderedHeatmapGeoJSON,
    assetsGeoJSON,
    treesRadiusGeoJSON,
    treesGeoJSON,
    shadeGeoJSON,
    reflectiveGeoJSON,
    activeLayer,
    selectedAssetId,
    mapLoaded,
    layerCfg,
    dynamicLayerStats,
    activePlacementTool,
  ]);

  // Fly to selected asset when explicitly selected by the user
  const prevSelectedAssetIdRef = useRef<string | null>(null);
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !selectedAssetId) {
      prevSelectedAssetIdRef.current = selectedAssetId;
      return;
    }

    if (prevSelectedAssetIdRef.current !== selectedAssetId) {
      const sel = assets.find((a) => a.asset_id === selectedAssetId);
      if (sel) {
        map.flyTo({
          center: [sel.longitude, sel.latitude],
          zoom: 15.5,
          duration: 800,
          essential: true,
        });
      }
    }
    prevSelectedAssetIdRef.current = selectedAssetId;
  }, [selectedAssetId, assets]);

  return (
    <div className="relative w-full h-full bg-slate-100 overflow-hidden flex flex-col" role="region" aria-label="Microclimate Map View">
      {/* Map Container */}
      <div ref={mapContainer} className="w-full h-full" />

      {/* Floating Spatial Placement Toast Alert */}
      {toastMessage && (
        <div
          role="alert"
          aria-live="assertive"
          className="absolute top-3 left-1/2 -translate-x-1/2 z-30 bg-slate-900/95 text-white px-3.5 py-2 rounded shadow-lg border border-slate-700 text-xs flex items-center gap-2 animate-in fade-in slide-in-from-top-2 duration-150 max-w-[92vw] sm:max-w-md"
        >
          <span className="text-amber-400 font-bold flex-shrink-0">Placement blocked:</span>
          <span className="text-slate-100 leading-tight">{toastMessage}</span>
          <button
            onClick={() => setToastMessage(null)}
            className="ml-1 text-slate-400 hover:text-white p-0.5 rounded hover:bg-slate-800 transition-colors flex-shrink-0"
            aria-label="Dismiss warning"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Floating Layer & Filter Toolbar (Top Left on desktop, responsive scrollable bar on mobile) */}
      <div className="absolute top-2 left-2 sm:top-3 sm:left-3 z-10 flex flex-col gap-1.5 sm:gap-2 max-w-[calc(100vw-16px)] sm:max-w-md">
        {/* Scenario Comparison Mode Toggle (Baseline vs Proposed Plan) */}
        <div
          className="bg-white/95 backdrop-blur-xs border border-slate-200 p-1 rounded shadow-xs flex items-center gap-1 overflow-x-auto no-scrollbar w-fit max-w-full"
          role="group"
          aria-label="Scenario comparison toggle"
        >
          <button
            onClick={() => setScenarioViewMode("baseline")}
            aria-pressed={scenarioViewMode === "baseline"}
            aria-label="View FortyGuard baseline heat observations"
            className={`px-2.5 py-1 text-xs rounded font-semibold transition-all focus:outline-none focus:ring-2 focus:ring-slate-400 min-h-[30px] flex-shrink-0 ${
              scenarioViewMode === "baseline"
                ? "bg-slate-900 text-white shadow-xs"
                : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
            }`}
          >
            Baseline Heat
          </button>

          <button
            onClick={() => setScenarioViewMode("scenario")}
            aria-pressed={scenarioViewMode === "scenario"}
            aria-label="View proposed plan modeled cooling scenario"
            className={`flex items-center gap-1.5 px-2.5 py-1 text-xs rounded font-semibold transition-all focus:outline-none focus:ring-2 focus:ring-brand-500 min-h-[30px] flex-shrink-0 ${
              scenarioViewMode === "scenario"
                ? "bg-brand-600 text-white shadow-xs"
                : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
            }`}
          >
            <Layers className="w-3 h-3 text-brand-200" />
            <span>Proposed Plan</span>
            {placedInterventions.length > 0 && (
              <span className="text-[10px] px-1.5 py-0.2 rounded bg-brand-700 text-white font-medium">
                {placedInterventions.length} city-wide
              </span>
            )}
          </button>
        </div>

        {/* Layer Selector */}
        <div
          className="bg-white/95 backdrop-blur-xs border border-slate-200 p-1 sm:p-1.5 rounded shadow-xs flex items-center gap-1 overflow-x-auto no-scrollbar w-fit max-w-full"
          role="group"
          aria-label="Heatmap layer selection"
        >
          <div className="flex items-center gap-1 px-1.5 text-xs font-semibold text-slate-700 mr-0.5 sm:mr-1 border-r border-slate-200 flex-shrink-0">
            <Layers className="w-3.5 h-3.5 text-slate-500" />
            <span className="text-[11px] uppercase tracking-wider text-slate-500">Layer:</span>
          </div>

          {(["tcm_peak", "tcm_mean", "exceedance", "persistence"] as HeatmapLayerType[]).map((layerKey) => {
            const cfg = layerConfigs[layerKey];
            const isActive = activeLayer === layerKey;

            return (
              <button
                key={layerKey}
                onClick={() => onChangeLayer(layerKey)}
                aria-pressed={isActive}
                aria-label={`Show ${cfg.label} layer`}
                className={`px-2 py-0.5 text-xs rounded font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400 min-h-[28px] flex-shrink-0 ${
                  isActive
                    ? "bg-slate-900 text-white shadow-xs"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                }`}
              >
                {cfg.shortLabel}
              </button>
            );
          })}
        </div>

        {/* Public Asset Filters */}
        <div
          className="bg-white/90 backdrop-blur-xs border border-slate-200 px-2 py-1 rounded shadow-xs flex items-center gap-1 text-[11px] overflow-x-auto no-scrollbar w-fit max-w-full"
          role="group"
          aria-label="Area category filter"
        >
          <span className="text-slate-500 font-medium mr-1 flex-shrink-0">Filter:</span>
          {[
            { key: "all", label: "All Areas" },
            { key: "bus_stop", label: "Transit Stops" },
            { key: "school", label: "Schools" },
            { key: "playground", label: "Playgrounds" },
          ].map((item) => (
            <button
              key={item.key}
              onClick={() => setAssetFilter(item.key)}
              aria-pressed={assetFilter === item.key}
              aria-label={`Filter by ${item.label}`}
              className={`px-1.5 py-0.5 rounded font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400 min-h-[26px] flex-shrink-0 ${
                assetFilter === item.key
                  ? "bg-slate-200 text-slate-900 font-semibold"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>

        {/* Interactive Placement Tools Palette (Visible in Test Interventions Mode) */}
        {appMode === "plan" && onSelectPlacementTool && (
          <div
            className="bg-white/95 backdrop-blur-xs border border-brand-300 p-1 sm:p-1.5 rounded shadow-xs flex items-center gap-1 text-xs overflow-x-auto no-scrollbar w-fit max-w-full"
            role="group"
            aria-label="Intervention placement tools"
          >
            <div className="flex items-center gap-1 px-1.5 font-semibold text-brand-800 mr-0.5 border-r border-slate-200 flex-shrink-0">
              <Crosshair className="w-3.5 h-3.5 text-brand-600" />
              <span className="text-[11px]">Place on Map:</span>
            </div>

            <button
              onClick={() => onSelectPlacementTool(activePlacementTool === "tree" ? null : "tree")}
              aria-pressed={activePlacementTool === "tree"}
              className={`flex items-center gap-1 px-2.5 py-1 rounded transition-colors min-h-[30px] flex-shrink-0 ${
                activePlacementTool === "tree"
                  ? "bg-emerald-700 text-white font-semibold"
                  : "bg-emerald-50 text-emerald-800 border border-emerald-200 hover:bg-emerald-100"
              }`}
            >
              <Trees className="w-3 h-3" />
              <span>+ Tree</span>
            </button>

            <button
              onClick={() => onSelectPlacementTool(activePlacementTool === "shade" ? null : "shade")}
              aria-pressed={activePlacementTool === "shade"}
              className={`flex items-center gap-1 px-2.5 py-1 rounded transition-colors min-h-[30px] flex-shrink-0 ${
                activePlacementTool === "shade"
                  ? "bg-sky-700 text-white font-semibold"
                  : "bg-sky-50 text-sky-800 border border-sky-200 hover:bg-sky-100"
              }`}
            >
              <Umbrella className="w-3 h-3" />
              <span>+ Shade</span>
            </button>

            <button
              onClick={() => onSelectPlacementTool(activePlacementTool === "reflective" ? null : "reflective")}
              aria-pressed={activePlacementTool === "reflective"}
              className={`flex items-center gap-1 px-2.5 py-1 rounded transition-colors min-h-[30px] flex-shrink-0 ${
                activePlacementTool === "reflective"
                  ? "bg-amber-700 text-white font-semibold"
                  : "bg-amber-50 text-amber-800 border border-amber-200 hover:bg-amber-100"
              }`}
            >
              <Sun className="w-3 h-3" />
              <span>+ Reflective</span>
            </button>

            {activePlacementTool && (
              <button
                onClick={() => onSelectPlacementTool(null)}
                aria-label="Cancel placement"
                title="Cancel placement mode"
                className="p-1 text-slate-400 hover:text-slate-700 rounded hover:bg-slate-100 transition-colors ml-auto flex-shrink-0"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        )}
      </div>

      {/* Active Placement Banner (Center Top) */}
      {activePlacementTool && (
        <div className="absolute top-2.5 sm:top-3 left-1/2 -translate-x-1/2 z-20 bg-slate-900 text-white px-3 sm:px-3.5 py-1.5 rounded-full shadow-lg text-xs font-medium flex items-center gap-2 animate-in fade-in slide-in-from-top-2 duration-150 max-w-[92vw] truncate">
          <Crosshair className="w-3.5 h-3.5 text-brand-400 animate-pulse flex-shrink-0" />
          <span className="truncate">
            Click map to place {activePlacementTool === "tree" ? "street tree" : activePlacementTool === "shade" ? "shade structure" : "reflective surface"}
          </span>
          <button
            onClick={() => onSelectPlacementTool && onSelectPlacementTool(null)}
            className="text-slate-300 hover:text-white ml-1 font-semibold px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-xs flex-shrink-0 transition-colors"
            aria-label="Cancel placement"
          >
            Cancel
          </button>
        </div>
      )}

      {/* Scenario Mode Floating Badge when active */}
      {appMode === "plan" && activeSimulation && (
        <div className="absolute top-2 sm:top-3 right-12 sm:right-14 z-10 bg-white border border-brand-300 px-2.5 sm:px-3 py-1 sm:py-1.5 rounded shadow-xs flex items-center gap-1.5 sm:gap-2 text-xs text-slate-800 max-w-[200px] sm:max-w-none truncate">
          <Layers className="w-3.5 h-3.5 text-brand-600 flex-shrink-0" />
          <span className="truncate">
            Relief: <strong className="text-brand-700">{formatDelta(activeSimulation.modeled_impact.peak_reduction_c)}</strong> ({formatCurrency(activeSimulation.total_estimated_cost)})
          </span>
        </div>
      )}

      {/* Mobile Heat Legend Toggle Button (visible on small screens when legend is minimized) */}
      {!isMobileLegendOpen && (
        <button
          onClick={() => setIsMobileLegendOpen(true)}
          aria-label="Open heat and risk legend"
          className="lg:hidden absolute bottom-3 left-3 z-10 bg-white/95 backdrop-blur-xs border border-slate-300 text-slate-800 px-2.5 py-1.5 rounded-full shadow-md text-xs font-semibold flex items-center gap-1.5 hover:bg-slate-50 transition-all min-h-[36px]"
        >
          <Thermometer className="w-3.5 h-3.5 text-slate-600" />
          <span>Heat Legend</span>
          <ChevronUp className="w-3.5 h-3.5 text-slate-500" />
        </button>
      )}

      {/* Comprehensive Municipal GIS Legend (Bottom Left - always visible on desktop, collapsible popup on mobile) */}
      <div
        className={`absolute bottom-3 left-3 sm:bottom-4 sm:left-4 z-10 transition-all duration-200 ${
          isMobileLegendOpen ? "block" : "hidden lg:block"
        }`}
      >
        <div className="bg-white/95 backdrop-blur-xs border border-slate-200 p-2.5 sm:p-3 rounded shadow-md sm:shadow-xs w-[270px] sm:w-[280px] text-xs space-y-2.5">
          {/* Mobile Header with Close Button */}
          <div className="flex items-center justify-between lg:hidden border-b border-slate-200 pb-1.5">
            <span className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
              <Thermometer className="w-3.5 h-3.5 text-slate-700" />
              Microclimate Heat Legend
            </span>
            <button
              onClick={() => setIsMobileLegendOpen(false)}
              className="p-1 text-slate-400 hover:text-slate-700 rounded hover:bg-slate-100 transition-colors"
              aria-label="Close legend"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* 1. Heatmap Temperature Scale */}
          <div>
            <div className="flex items-center justify-between gap-2 mb-0.5">
              <span className="font-semibold text-slate-800 text-[11px]">{layerCfg.label}</span>
              <span className="text-[10px] text-slate-500 font-mono">
                ({(activeLayer === "tcm_peak" || activeLayer === "tcm_mean") ? `°${unit}` : layerCfg.units})
              </span>
            </div>
            <div className="text-[10px] text-slate-400 mb-1 leading-tight">
              Peak modeled heat conditions (July 15–21, 2024)
            </div>

            <div className="space-y-1">
              <div
                className="h-2 rounded-xs w-full border border-slate-200"
                style={{
                  background: `linear-gradient(to right, ${dynamicLayerStats.stops.map((s) => s[1]).join(", ")})`,
                }}
              />
              <div className="flex justify-between text-[10px] text-slate-600 font-mono">
                {dynamicLayerStats.stops.map((s, idx) => {
                  const isTempLayer = activeLayer === "tcm_peak" || activeLayer === "tcm_mean";
                  const stopLabel = isTempLayer && unit === "F"
                    ? `${Math.round(celsiusToFahrenheit(s[0]))}°`
                    : isTempLayer
                    ? `${s[0]}°`
                    : `${s[0]}`;
                  return (
                    <span key={idx}>
                      {stopLabel}
                    </span>
                  );
                })}
              </div>
            </div>
          </div>

          {/* 2. Priority Heat Exposure (Composite Score) */}
          <div className="border-t border-slate-200 pt-2 space-y-1">
            <div>
              <span className="font-semibold text-slate-800 block text-[10px] uppercase tracking-wider text-slate-500">
                Priority Heat Exposure
              </span>
              <span className="text-[10px] text-slate-400 block -mt-0.5">
                Composite score: temperature + duration + usage
              </span>
            </div>
            <div className="grid grid-cols-2 gap-x-2 gap-y-1 text-[11px] text-slate-700 pt-0.5">
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-900 border border-white flex-shrink-0" />
                <span>Extreme</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-red-600 border border-white flex-shrink-0" />
                <span>Critical</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-orange-500 border border-white flex-shrink-0" />
                <span>High</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500 border border-white flex-shrink-0" />
                <span>Moderate / Low</span>
              </div>
            </div>
            <div className="flex items-center gap-1.5 text-[10px] text-slate-600 pt-0.5">
              <span className="w-3.5 h-3.5 rounded-full bg-slate-700 text-white font-bold text-[8.5px] flex items-center justify-center border border-white flex-shrink-0">
                #
              </span>
              <span>Cluster · Multiple sites (click to zoom)</span>
            </div>
          </div>

          {/* 3. Proposed Interventions */}
          <div className="border-t border-slate-200 pt-1.5 space-y-1 text-slate-700">
            <span className="font-semibold text-slate-800 block text-[10px] uppercase tracking-wider text-slate-500">
              Proposed Interventions
            </span>
            <div className="flex items-center gap-3 text-[11px]">
              <span className="flex items-center gap-1">
                <span className="inline-block w-2.5 h-2.5 rounded-full bg-emerald-600 border border-white flex-shrink-0" />
                <span>Tree</span>
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block w-2.5 h-2.5 rounded-full bg-sky-600 border border-white flex-shrink-0" />
                <span>Shade</span>
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block w-3 h-2.5 bg-amber-200 border border-dashed border-amber-600 rounded-xs flex-shrink-0" />
                <span>Cool Pavement</span>
              </span>
            </div>
          </div>

          {/* 4. Map & Data Attribution */}
          <div className="border-t border-slate-200 pt-1 text-[9px] text-slate-400 flex items-center justify-between">
            <span>&copy; CARTO &copy; OpenStreetMap</span>
            <span className="font-mono">FortyGuard 100m</span>
          </div>
        </div>
      </div>
    </div>
  );
};

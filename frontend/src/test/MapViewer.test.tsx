import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import {
  MapViewer,
  getLayerConfigs,
  MAP_LAYER_ORDER,
  addLayerInOrder,
  enforceMapLayerOrder,
  getBaseMapStyle,
} from "../components/MapViewer";
import { CityConfig, PlacedIntervention, PublicAsset } from "../types";
import { TemperatureProvider } from "../context/TemperatureContext";

vi.mock("maplibre-gl", () => {
  const MapMock = vi.fn(function () {
    return {
      addControl: vi.fn(),
      on: vi.fn((event: string, handler: Function) => {
        if (event === "load") handler();
      }),
      off: vi.fn(),
      remove: vi.fn(),
      fitBounds: vi.fn(),
      flyTo: vi.fn(),
      getSource: vi.fn(),
      addSource: vi.fn(),
      addLayer: vi.fn(),
      moveLayer: vi.fn(),
      getLayer: vi.fn(),
      setPaintProperty: vi.fn(),
      getCanvas: vi.fn(() => ({ style: {} })),
    };
  });

  const NavigationControlMock = vi.fn();
  const PopupMock = vi.fn(function () {
    return {
      setLngLat: vi.fn().mockReturnThis(),
      setHTML: vi.fn().mockReturnThis(),
      addTo: vi.fn().mockReturnThis(),
      remove: vi.fn(),
    };
  });

  return {
    default: {
      Map: MapMock,
      NavigationControl: NavigationControlMock,
      Popup: PopupMock,
    },
    Map: MapMock,
    NavigationControl: NavigationControlMock,
    Popup: PopupMock,
  };
});

const mockCity: CityConfig = {
  city_key: "phoenix",
  name: "Phoenix",
  state: "AZ",
  display_label: "Phoenix, AZ",
  center: [-112.0720, 33.4485],
  zoom: 14.5,
  bounds: [[-112.078, 33.439], [-112.065, 33.457]],
  fortyguard_tiles_count: 196,
  study_date: "2024-07-15",
  study_window: "Jul 15–21, 2024",
  description: "Downtown Phoenix heatwave",
  key_neighborhoods: ["Downtown Core"],
};

const mockAssets: PublicAsset[] = [
  {
    asset_id: "PHX-TRN-01",
    name: "Van Buren & Central Ave Regional Transit Center",
    asset_type: "bus_stop",
    city: "Phoenix",
    latitude: 33.4518,
    longitude: -112.0740,
    geometry: { type: "Point", coordinates: [-112.0740, 33.4518] },
    footprint_m2: 1200.0,
    daily_visitors: 2400,
    vulnerability_weight: 1.4,
    heat_risk_level: "Extreme",
    heat_risk_score: 88.5,
    observed_heat: {
      peak_temperature_c: 41.2,
      peak_temperature_f: 106.2,
      mean_temperature_c: 35.8,
      mean_temperature_f: 96.4,
      overnight_min_c: 28.5,
      overnight_min_f: 83.3,
      hours_above_35c: 9.0,
      persistence_hours: 6.0,
      impervious_pct: 92.0,
      canopy_pct: 3.0,
      hotspot_rank: 1,
    },
    recommended_interventions: ["shade_structure"],
  },
];

const mockInterventions: PlacedIntervention[] = [
  {
    id: "int-1",
    type: "tree",
    latitude: 33.4518,
    longitude: -112.0740,
    asset_id: "PHX-TRN-01",
    created_at: Date.now(),
  },
];

describe("MapViewer Component", () => {
  it("renders thermal layer buttons and area filter controls", () => {
    const onSelect = vi.fn();
    const onChangeLayer = vi.fn();

    render(
      <MapViewer
        cityConfig={mockCity}
        assets={mockAssets}
        selectedAssetId={null}
        onSelectAsset={onSelect}
        appMode="explore"
        activeLayer="tcm_peak"
        onChangeLayer={onChangeLayer}
        heatmapGeoJSON={null}
      />
    );

    expect(screen.getByText("Peak Temp")).toBeInTheDocument();
    expect(screen.getByText("Daily Mean")).toBeInTheDocument();
    expect(screen.getByText("Exceedance")).toBeInTheDocument();
    expect(screen.getByText("Persistence")).toBeInTheDocument();
    expect(screen.getByText("All Areas")).toBeInTheDocument();
    expect(screen.getByText("Transit Stops")).toBeInTheDocument();
    expect(screen.getByText("Schools")).toBeInTheDocument();
  });

  it("calls onChangeLayer when layer button is clicked", () => {
    const onSelect = vi.fn();
    const onChangeLayer = vi.fn();

    render(
      <MapViewer
        cityConfig={mockCity}
        assets={mockAssets}
        selectedAssetId={null}
        onSelectAsset={onSelect}
        appMode="explore"
        activeLayer="tcm_peak"
        onChangeLayer={onChangeLayer}
        heatmapGeoJSON={null}
      />
    );

    fireEvent.click(screen.getByText("Exceedance"));
    expect(onChangeLayer).toHaveBeenCalledWith("exceedance");
  });

  it("renders visual intervention tools in plan mode", () => {
    const onSelect = vi.fn();
    const onChangeLayer = vi.fn();
    const onSelectTool = vi.fn();

    render(
      <MapViewer
        cityConfig={mockCity}
        assets={mockAssets}
        selectedAssetId="PHX-TRN-01"
        onSelectAsset={onSelect}
        appMode="plan"
        activeLayer="tcm_peak"
        onChangeLayer={onChangeLayer}
        heatmapGeoJSON={null}
        placedInterventions={mockInterventions}
        activePlacementTool={null}
        onSelectPlacementTool={onSelectTool}
      />
    );

    expect(screen.getByText("Place on Map:")).toBeInTheDocument();
    expect(screen.getByText("+ Tree")).toBeInTheDocument();
    expect(screen.getByText("+ Shade")).toBeInTheDocument();
    expect(screen.getByText("+ Reflective")).toBeInTheDocument();

    fireEvent.click(screen.getByText("+ Tree"));
    expect(onSelectTool).toHaveBeenCalledWith("tree");
  });

  it("dynamically configures exceedance and persistence labels based on temperature unit", () => {
    const fConfigs = getLayerConfigs("F");
    expect(fConfigs.exceedance.label).toBe("Hours Above 95°F");
    expect(fConfigs.exceedance.description).toContain("95°F (35°C)");
    expect(fConfigs.persistence.description).toContain("above 95°F");

    const cConfigs = getLayerConfigs("C");
    expect(cConfigs.exceedance.label).toBe("Hours Above 35°C");
    expect(cConfigs.exceedance.description).toContain("35°C (95°F)");
    expect(cConfigs.persistence.description).toContain("above 35°C");
  });

  it("renders Fahrenheit layer label in legend and layer button aria-label when F is active", () => {
    const onSelect = vi.fn();
    const onChangeLayer = vi.fn();

    render(
      <TemperatureProvider initialUnit="F">
        <MapViewer
          cityConfig={mockCity}
          assets={mockAssets}
          selectedAssetId={null}
          onSelectAsset={onSelect}
          appMode="explore"
          activeLayer="exceedance"
          onChangeLayer={onChangeLayer}
          heatmapGeoJSON={null}
        />
      </TemperatureProvider>
    );

    expect(screen.getByRole("button", { name: "Show Hours Above 95°F layer" })).toBeInTheDocument();
    expect(screen.getByText("Hours Above 95°F")).toBeInTheDocument();
  });

  it("renders Celsius layer label in legend and layer button aria-label when C is active", () => {
    const onSelect = vi.fn();
    const onChangeLayer = vi.fn();

    render(
      <TemperatureProvider initialUnit="C">
        <MapViewer
          cityConfig={mockCity}
          assets={mockAssets}
          selectedAssetId={null}
          onSelectAsset={onSelect}
          appMode="explore"
          activeLayer="exceedance"
          onChangeLayer={onChangeLayer}
          heatmapGeoJSON={null}
        />
      </TemperatureProvider>
    );

    expect(screen.getByRole("button", { name: "Show Hours Above 35°C layer" })).toBeInTheDocument();
    expect(screen.getByText("Hours Above 35°C")).toBeInTheDocument();
  });

  describe("Deterministic Layer Ordering", () => {
    it("defines canonical order with heatmap below interventions and asset markers/labels", () => {
      const heatmapFillIdx = MAP_LAYER_ORDER.indexOf("heatmap-tiles-fill");
      const heatmapLineIdx = MAP_LAYER_ORDER.indexOf("heatmap-tiles-line");
      const reflectiveIdx = MAP_LAYER_ORDER.indexOf("interventions-reflective-fill");
      const treeCircleIdx = MAP_LAYER_ORDER.indexOf("interventions-trees-circle");
      const assetClusterIdx = MAP_LAYER_ORDER.indexOf("assets-clusters-circle");
      const assetCircleIdx = MAP_LAYER_ORDER.indexOf("assets-risk-circle");
      const assetLabelIdx = MAP_LAYER_ORDER.indexOf("assets-symbol-label");

      expect(heatmapFillIdx).toBeLessThan(heatmapLineIdx);
      expect(heatmapLineIdx).toBeLessThan(reflectiveIdx);
      expect(reflectiveIdx).toBeLessThan(treeCircleIdx);
      expect(treeCircleIdx).toBeLessThan(assetClusterIdx);
      expect(assetClusterIdx).toBeLessThan(assetCircleIdx);
      expect(assetCircleIdx).toBeLessThan(assetLabelIdx);
    });

    it("inserts heatmap below existing asset layers when added asynchronously", () => {
      const mockMap = {
        getLayer: vi.fn((id: string) => {
          if (id === "assets-clusters-circle" || id === "assets-risk-circle" || id === "assets-symbol-label") {
            return { id };
          }
          return undefined;
        }),
        addLayer: vi.fn(),
      } as any;

      addLayerInOrder(mockMap, { id: "heatmap-tiles-fill", type: "fill" });
      expect(mockMap.addLayer).toHaveBeenCalledWith(
        { id: "heatmap-tiles-fill", type: "fill" },
        "assets-clusters-circle"
      );
    });

    it("enforces order by calling moveLayer sequentially for all active custom layers", () => {
      const mockMap = {
        getLayer: vi.fn((id: string) => {
          if (id === "heatmap-tiles-fill" || id === "assets-risk-circle") {
            return { id };
          }
          return undefined;
        }),
        moveLayer: vi.fn(),
      } as any;

      enforceMapLayerOrder(mockMap);
      expect(mockMap.moveLayer).toHaveBeenCalledWith("heatmap-tiles-fill");
      expect(mockMap.moveLayer).toHaveBeenCalledWith("assets-risk-circle");
    });
  });

  describe("CARTO Basemap Style and API Key Configuration", () => {
    it("returns clean raster tile URLs without query parameter when no API key is set", () => {
      const style = getBaseMapStyle("");
      const source = style.sources["carto-positron"] as any;
      expect(source.type).toBe("raster");
      expect(source.tiles[0]).toBe("https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png");
      expect(source.tiles[1]).toBe("https://b.basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png");
      expect(source.attribution).toContain("CARTO");
      expect(source.attribution).toContain("OpenStreetMap");
    });

    it("appends ?api_key= query parameter when CARTO API key is provided", () => {
      const testKey = "carto_test_key_12345";
      const style = getBaseMapStyle(testKey);
      const source = style.sources["carto-positron"] as any;
      expect(source.tiles[0]).toBe(`https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png?api_key=${testKey}`);
      expect(source.tiles[1]).toBe(`https://b.basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png?api_key=${testKey}`);
    });
  });
});

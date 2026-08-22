import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MapViewer } from "../components/MapViewer";
import { CityConfig, PlacedIntervention, PublicAsset } from "../types";

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
});

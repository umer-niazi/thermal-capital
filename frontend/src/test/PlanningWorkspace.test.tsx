import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { PlanningWorkspace } from "../components/PlanningWorkspace";
import { CityConfig, PlacedIntervention, PublicAsset } from "../types";

vi.mock("../services/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../services/api")>();
  return {
    ...actual,
    simulateInterventions: vi.fn().mockResolvedValue({
      asset_id: "PHX-TRN-01",
      city: "phoenix",
      interventions: [],
      total_estimated_cost: 25000,
      modeled_impact: {
        peak_temp_before_c: 41.2,
        peak_temp_before_f: 106.2,
        peak_temp_after_c: 39.0,
        peak_temp_after_f: 102.2,
        peak_reduction_c: 2.2,
        peak_reduction_f: 4.0,
        mean_temp_before_c: 35.8,
        mean_temp_after_c: 34.5,
        mean_reduction_c: 1.3,
        hours_35c_before: 9.0,
        hours_35c_after: 5.5,
        hours_35c_reduction_pct: 38.9,
        persistence_hours_before: 6.0,
        persistence_hours_after: 4.0,
        persistence_reduction_pct: 33.3,
        tree_canopy_pct_before: 3.0,
        tree_canopy_pct_after: 15.0,
        canopy_increase_pct: 12.0,
        impervious_pct_before: 92.0,
        impervious_pct_after: 80.0,
        benefited_daily_population: 2400,
        affected_area_m2: 1200.0,
      },
      scientific_assumptions: [],
      disclaimer: "Modeled estimate",
    }),
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

const mockAsset: PublicAsset = {
  asset_id: "PHX-TRN-01",
  name: "Van Buren & Central Ave Regional Transit Center",
  asset_type: "bus_stop",
  city: "Phoenix",
  latitude: 33.4515,
  longitude: -112.0740,
  geometry: { type: "Point", coordinates: [-112.0740, 33.4515] },
  footprint_m2: 1200,
  daily_visitors: 2400,
  vulnerability_weight: 1.4,
  heat_risk_level: "Severe",
  heat_risk_score: 84.5,
  observed_heat: {
    peak_temperature_c: 41.2,
    peak_temperature_f: 106.2,
    mean_temperature_c: 35.8,
    mean_temperature_f: 96.4,
    overnight_min_c: 29.5,
    overnight_min_f: 85.1,
    hours_above_35c: 9.0,
    persistence_hours: 6.0,
    impervious_pct: 92.0,
    canopy_pct: 3.0,
  },
  recommended_interventions: ["shade_structure", "tree_canopy", "cool_pavement"],
  notes: "High foot-traffic downtown light-rail transfer hub.",
};

const mockInterventions: PlacedIntervention[] = [
  {
    id: "tree-1",
    type: "tree",
    latitude: 33.4516,
    longitude: -112.0741,
    asset_id: "PHX-TRN-01",
    created_at: Date.now(),
  },
  {
    id: "shade-1",
    type: "shade",
    latitude: 33.4514,
    longitude: -112.0740,
    asset_id: "PHX-TRN-01",
    created_at: Date.now(),
  },
];

describe("PlanningWorkspace Component", () => {
  it("renders target area, intervention controls, and scenario comparison", async () => {
    const onSelect = vi.fn();
    const onOpenOpt = vi.fn();
    const onOpenRep = vi.fn();
    const onSwitch = vi.fn();
    const onAdd = vi.fn();
    const onRemove = vi.fn();
    const onClear = vi.fn();
    const onSelectTool = vi.fn();

    render(
      <PlanningWorkspace
        asset={mockAsset}
        allAssets={[mockAsset]}
        cityConfig={mockCity}
        onSelectAsset={onSelect}
        onOpenOptimizer={onOpenOpt}
        onOpenReport={onOpenRep}
        onSwitchMode={onSwitch}
        placedInterventions={mockInterventions}
        onAddIntervention={onAdd}
        onRemoveIntervention={onRemove}
        onClearAssetInterventions={onClear}
        activePlacementTool={null}
        onSelectPlacementTool={onSelectTool}
      />
    );

    expect(screen.getByText("PLANNING TARGET")).toBeInTheDocument();
    expect(screen.getByText("Add Cooling Interventions")).toBeInTheDocument();
    expect(screen.getByText("Street Tree Planting")).toBeInTheDocument();
    expect(screen.getByText("Engineered Shade Structure")).toBeInTheDocument();
    expect(screen.getByText("Reflective Cool Pavement")).toBeInTheDocument();
    expect(await screen.findByText("Estimated Site Coverage:")).toBeInTheDocument();
    expect(await screen.findByText("Estimated Benefited Area:")).toBeInTheDocument();
    expect(screen.getByText("Optimize Budget")).toBeInTheDocument();
    expect(screen.getByText("Generate Brief")).toBeInTheDocument();
  });
});

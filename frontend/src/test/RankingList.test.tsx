import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { RankingList } from "../components/RankingList";
import { CityConfig, PublicAsset } from "../types";

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
  description: "Peak desert heatwave study: 100m ambient microclimate grid.",
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
    recommended_interventions: ["shade_structure", "tree_canopy"],
  },
  {
    asset_id: "PHX-SCH-01",
    name: "Capitol Elementary School & Youth Playground",
    asset_type: "school",
    city: "Phoenix",
    latitude: 33.4475,
    longitude: -112.0768,
    geometry: { type: "Point", coordinates: [-112.0768, 33.4475] },
    footprint_m2: 3200.0,
    daily_visitors: 650,
    vulnerability_weight: 1.6,
    heat_risk_level: "Severe",
    heat_risk_score: 79.2,
    observed_heat: {
      peak_temperature_c: 40.5,
      peak_temperature_f: 104.9,
      mean_temperature_c: 35.0,
      mean_temperature_f: 95.0,
      overnight_min_c: 28.0,
      overnight_min_f: 82.4,
      hours_above_35c: 8.2,
      persistence_hours: 5.2,
      impervious_pct: 78.0,
      canopy_pct: 6.0,
      hotspot_rank: 2,
    },
    recommended_interventions: ["tree_canopy", "shade_structure"],
  },
];

describe("RankingList Component", () => {
  it("renders priority areas list with risk exposure", () => {
    const onSelect = vi.fn();
    const onPlan = vi.fn();

    render(
      <RankingList
        assets={mockAssets}
        cityConfig={mockCity}
        onSelectAsset={onSelect}
        onPlanAsset={onPlan}
      />
    );

    expect(screen.getByText("Priority Areas — Phoenix")).toBeInTheDocument();
    expect(screen.getByText("Van Buren & Central Ave Regional Transit Center")).toBeInTheDocument();
    expect(screen.getByText("Capitol Elementary School & Youth Playground")).toBeInTheDocument();
    expect(screen.getByText("1.")).toBeInTheDocument();
    expect(screen.getByText("2.")).toBeInTheDocument();
    expect(screen.getByText("Extreme exposure")).toBeInTheDocument();
  });

  it("triggers onPlanAsset when Test button is clicked", () => {
    const onSelect = vi.fn();
    const onPlan = vi.fn();

    render(
      <RankingList
        assets={mockAssets}
        cityConfig={mockCity}
        onSelectAsset={onSelect}
        onPlanAsset={onPlan}
      />
    );

    const testButtons = screen.getAllByText("Test");
    fireEvent.click(testButtons[0]);
    expect(onPlan).toHaveBeenCalledWith("PHX-TRN-01");
  });
});

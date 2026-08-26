import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SiteDetail } from "../components/SiteDetail";
import { PublicAsset } from "../types";
import { TemperatureProvider } from "../context/TemperatureContext";

const mockAsset: PublicAsset = {
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
    contributing_tile_id: 42,
  },
  recommended_interventions: ["shade_structure", "tree_canopy", "cool_pavement"],
  notes: "Major bus and light rail transfer hub with high passenger volume.",
};

describe("SiteDetail Component", () => {
  it("renders area heat exposure, peak temperature in °F by default with °C secondary, and why this area matters", () => {
    const onBack = vi.fn();
    const onPlan = vi.fn();

    render(
      <TemperatureProvider initialUnit="F">
        <SiteDetail
          asset={mockAsset}
          onBack={onBack}
          onPlanIntervention={onPlan}
        />
      </TemperatureProvider>
    );

    expect(screen.getByText("Van Buren & Central Ave Regional Transit Center")).toBeInTheDocument();
    expect(screen.getByText("PHX-TRN-01")).toBeInTheDocument();
    expect(screen.getByText("EXTREME")).toBeInTheDocument();
    expect(screen.getAllByText(/106.2°F/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/41.2°C/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Hours Above 95°F")).toBeInTheDocument();
    expect(screen.getAllByText(/9.0 h/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/\(6.0h run\)/)).toBeInTheDocument();
    expect(screen.getByText(/exceeding 95°F/)).toBeInTheDocument();
    expect(screen.getByText("Why is this area a priority?")).toBeInTheDocument();
  });

  it("renders primary °C and Hours Above 35°C when Celsius preference is active", () => {
    const onBack = vi.fn();
    const onPlan = vi.fn();

    render(
      <TemperatureProvider initialUnit="C">
        <SiteDetail
          asset={mockAsset}
          onBack={onBack}
          onPlanIntervention={onPlan}
        />
      </TemperatureProvider>
    );

    expect(screen.getAllByText(/41.2°C/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/106.2°F/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Hours Above 35°C")).toBeInTheDocument();
    expect(screen.getAllByText(/9.0 h/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/\(6.0h run\)/)).toBeInTheDocument();
    expect(screen.getByText(/exceeding 35°C/)).toBeInTheDocument();
  });

  it("calls onPlanIntervention when test intervention button is clicked", () => {
    const onBack = vi.fn();
    const onPlan = vi.fn();

    render(
      <SiteDetail
        asset={mockAsset}
        onBack={onBack}
        onPlanIntervention={onPlan}
      />
    );

    const testBtn = screen.getByText("Test Cooling Interventions on This Area");
    fireEvent.click(testBtn);
    expect(onPlan).toHaveBeenCalled();
  });

  it("calls onBack when the top-right close button is clicked", () => {
    const onBack = vi.fn();
    const onPlan = vi.fn();

    render(
      <SiteDetail
        asset={mockAsset}
        onBack={onBack}
        onPlanIntervention={onPlan}
      />
    );

    const closeBtn = screen.getByRole("button", { name: "Close" });
    fireEvent.click(closeBtn);
    expect(onBack).toHaveBeenCalled();
  });
});

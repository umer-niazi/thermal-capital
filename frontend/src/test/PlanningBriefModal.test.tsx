import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { PlanningBriefModal } from "../components/PlanningBriefModal";
import { CityConfig } from "../types";

vi.mock("../services/api", () => ({
  generateReport: vi.fn().mockResolvedValue({
    report_id: "REP-PHX-2024-001",
    title: "Phoenix Municipal Heat Intervention & Capital Planning Brief",
    city: "Phoenix",
    generated_at: "2024-07-15 14:00 MST",
    study_period: "Jul 15–21, 2024",
    budget_allocated: 500000,
    executive_summary: "High-resolution microclimate modeling identified key public transit corridors in Phoenix as extreme heat exposure zones.",
    observed_baseline_summary: {},
    proposed_portfolio: {
      total_trees: 80,
      total_shade_structures: 12,
      total_cool_pavement_m2: 6000,
      total_assets_covered: 10,
    },
    modeled_outcomes_summary: {
      portfolio_avg_peak_reduction_c: 2.1,
      portfolio_avg_hours_reduction_pct: 35.0,
      total_benefited_population: 18400,
    },
    target_assets_table: [
      {
        asset_id: "PHX-TRN-01",
        asset_name: "Van Buren & Central Ave Regional Transit Center",
        asset_type: "bus_stop",
        heat_risk_level: "Extreme",
        observed_peak_c: "41.2°C",
        allocated_cost: "$48,000",
        modeled_peak_reduction: "-2.4°C",
        hours_reduction: "-42%",
        benefited_citizens: "2,400",
        interventions_package: "4 Trees, 2 Shade Structures",
        rationale: "Major downtown transfer hub with high transit rider dwell time.",
      },
    ],
    intervention_itemization: [
      {
        category: "Urban Shade Trees",
        units: "80 trees",
        unit_rate: "$600/tree",
        subtotal: "$48,000",
        impact_mechanism: "Direct shading & evaporative cooling",
      },
    ],
    methodology_and_assumptions: [
      "Baseline thermal metrics derived from FortyGuard 100m microclimate sensors.",
      "Tree canopy cooling based on USFS i-Tree microclimate models.",
    ],
    data_sources: [
      "FortyGuard TCM 100m Surface Air Temperature Grid",
      "City of Phoenix Open GIS Public Assets Directory",
    ],
  }),
}));

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

describe("PlanningBriefModal Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders report content and supports print triggering", async () => {
    const onClose = vi.fn();
    const printSpy = vi.spyOn(window, "print").mockImplementation(() => {});

    render(
      <PlanningBriefModal
        cityConfig={mockCity}
        optResult={null}
        onClose={onClose}
      />
    );

    // Wait for report to load
    await waitFor(() => {
      expect(screen.getByText("HEAT ADAPTATION PLANNING BRIEF")).toBeInTheDocument();
    });

    expect(screen.getByText("1. Executive Summary")).toBeInTheDocument();
    expect(screen.getByText(/2\. Proposed Capital Portfolio/i)).toBeInTheDocument();
    expect(screen.getByText(/3\. Itemized Interventions/i)).toBeInTheDocument();
    expect(screen.getByText(/4\. Priority Assets/i)).toBeInTheDocument();
    expect(screen.getByText(/5\. Scientific Methodology/i)).toBeInTheDocument();

    // Verify print button
    const printBtn = screen.getByRole("button", { name: "Print action brief" });
    expect(printBtn).toBeInTheDocument();
    fireEvent.click(printBtn);
    expect(printSpy).toHaveBeenCalledTimes(1);

    // Verify close button
    const closeBtn = screen.getByRole("button", { name: "Close dialog" });
    expect(closeBtn).toBeInTheDocument();
    fireEvent.click(closeBtn);
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});

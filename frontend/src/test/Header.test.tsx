import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Header } from "../components/Header";
import { CityConfig } from "../types";

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

describe("Header Component", () => {
  it("renders brand, subtitle, and mode switcher", () => {
    const onSelectCity = vi.fn();
    const onSwitchMode = vi.fn();
    const onOpenOpt = vi.fn();
    const onOpenRep = vi.fn();

    render(
      <Header
        currentCity={mockCity}
        allCities={[mockCity]}
        onSelectCity={onSelectCity}
        appMode="explore"
        onSwitchMode={onSwitchMode}
        onOpenOptimizer={onOpenOpt}
        onOpenReport={onOpenRep}
      />
    );

    expect(screen.getByText("Thermal Capital")).toBeInTheDocument();
    expect(screen.getByText(/Capital planning for urban heat/i)).toBeInTheDocument();
    expect(screen.getByText(/1\. Identify Risk/i)).toBeInTheDocument();
    expect(screen.getByText(/2\. Intervene & Compare/i)).toBeInTheDocument();
    expect(screen.getByText(/Optimize Budget/i)).toBeInTheDocument();
  });

  it("calls onSwitchMode when Test Interventions is clicked", () => {
    const onSelectCity = vi.fn();
    const onSwitchMode = vi.fn();
    const onOpenOpt = vi.fn();
    const onOpenRep = vi.fn();

    render(
      <Header
        currentCity={mockCity}
        allCities={[mockCity]}
        onSelectCity={onSelectCity}
        appMode="explore"
        onSwitchMode={onSwitchMode}
        onOpenOptimizer={onOpenOpt}
        onOpenReport={onOpenRep}
      />
    );

    fireEvent.click(screen.getByText(/2\. Intervene & Compare/i));
    expect(onSwitchMode).toHaveBeenCalledWith("plan");
  });

  it("calls onOpenOptimizer when optimizer button is clicked", () => {
    const onSelectCity = vi.fn();
    const onSwitchMode = vi.fn();
    const onOpenOpt = vi.fn();
    const onOpenRep = vi.fn();

    render(
      <Header
        currentCity={mockCity}
        allCities={[mockCity]}
        onSelectCity={onSelectCity}
        appMode="explore"
        onSwitchMode={onSwitchMode}
        onOpenOptimizer={onOpenOpt}
        onOpenReport={onOpenRep}
      />
    );

    fireEvent.click(screen.getByText(/Optimize Budget/));
    expect(onOpenOpt).toHaveBeenCalled();
  });
});

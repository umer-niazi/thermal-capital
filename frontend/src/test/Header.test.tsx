import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Header } from "../components/Header";
import { CityConfig } from "../types";
import { TemperatureProvider } from "../context/TemperatureContext";

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
      <TemperatureProvider>
        <Header
          currentCity={mockCity}
          allCities={[mockCity]}
          onSelectCity={onSelectCity}
          appMode="explore"
          onSwitchMode={onSwitchMode}
          onOpenOptimizer={onOpenOpt}
          onOpenReport={onOpenRep}
        />
      </TemperatureProvider>
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
      <TemperatureProvider>
        <Header
          currentCity={mockCity}
          allCities={[mockCity]}
          onSelectCity={onSelectCity}
          appMode="explore"
          onSwitchMode={onSwitchMode}
          onOpenOptimizer={onOpenOpt}
          onOpenReport={onOpenRep}
        />
      </TemperatureProvider>
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
      <TemperatureProvider>
        <Header
          currentCity={mockCity}
          allCities={[mockCity]}
          onSelectCity={onSelectCity}
          appMode="explore"
          onSwitchMode={onSwitchMode}
          onOpenOptimizer={onOpenOpt}
          onOpenReport={onOpenRep}
        />
      </TemperatureProvider>
    );

    fireEvent.click(screen.getByText(/Optimize Budget/));
    expect(onOpenOpt).toHaveBeenCalled();
  });

  it("renders temperature unit toggle with °F selected by default and allows switching", () => {
    const onSelectCity = vi.fn();
    const onSwitchMode = vi.fn();
    const onOpenOpt = vi.fn();
    const onOpenRep = vi.fn();

    render(
      <TemperatureProvider>
        <Header
          currentCity={mockCity}
          allCities={[mockCity]}
          onSelectCity={onSelectCity}
          appMode="explore"
          onSwitchMode={onSwitchMode}
          onOpenOptimizer={onOpenOpt}
          onOpenReport={onOpenRep}
        />
      </TemperatureProvider>
    );

    const fBtn = screen.getByRole("button", { name: "Display temperature in Fahrenheit" });
    const cBtn = screen.getByRole("button", { name: "Display temperature in Celsius" });

    expect(fBtn).toBeInTheDocument();
    expect(cBtn).toBeInTheDocument();
    expect(fBtn).toHaveAttribute("aria-pressed", "true");
    expect(cBtn).toHaveAttribute("aria-pressed", "false");

    fireEvent.click(cBtn);
    expect(cBtn).toHaveAttribute("aria-pressed", "true");
    expect(fBtn).toHaveAttribute("aria-pressed", "false");
  });

  it("maintains fixed layout dimensions on workflow tabs and temperature buttons to prevent layout shift", () => {
    const onSelectCity = vi.fn();
    const onSwitchMode = vi.fn();
    const onOpenOpt = vi.fn();
    const onOpenRep = vi.fn();

    render(
      <TemperatureProvider>
        <Header
          currentCity={mockCity}
          allCities={[mockCity]}
          onSelectCity={onSelectCity}
          appMode="explore"
          onSwitchMode={onSwitchMode}
          onOpenOptimizer={onOpenOpt}
          onOpenReport={onOpenRep}
        />
      </TemperatureProvider>
    );

    const step1Btn = screen.getByRole("button", { name: "1. Identify Risk" });
    const step2Btn = screen.getByRole("button", { name: "2. Intervene & Compare" });
    const fBtn = screen.getByRole("button", { name: "Display temperature in Fahrenheit" });
    const cBtn = screen.getByRole("button", { name: "Display temperature in Celsius" });

    // Step buttons have fixed widths and consistent font weights
    expect(step1Btn.className).toContain("w-[98px]");
    expect(step1Btn.className).toContain("sm:w-[142px]");
    expect(step1Btn.className).toContain("font-semibold");

    expect(step2Btn.className).toContain("w-[106px]");
    expect(step2Btn.className).toContain("sm:w-[174px]");
    expect(step2Btn.className).toContain("font-semibold");

    // Temperature toggle buttons have fixed equal widths and consistent font weights
    expect(fBtn.className).toContain("w-7");
    expect(fBtn.className).toContain("sm:w-8");
    expect(fBtn.className).toContain("font-semibold");

    expect(cBtn.className).toContain("w-7");
    expect(cBtn.className).toContain("sm:w-8");
    expect(cBtn.className).toContain("font-semibold");
  });
});

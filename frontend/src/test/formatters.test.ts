import { describe, expect, it } from "vitest";
import {
  formatCurrency,
  formatDeltaC,
  formatHours,
  formatNumber,
  formatPercent,
  formatTemp,
  formatTempC,
  formatTempF,
  getAssetTypeLabel,
  getRiskColor,
  getScoreProgressColor,
} from "../utils/formatters";

describe("Formatting Utilities", () => {
  it("formats temperature in dual Celsius and Fahrenheit", () => {
    expect(formatTemp(40.5, 104.9)).toBe("40.5°C / 104.9°F");
    expect(formatTempC(40.5)).toBe("40.5°C");
    expect(formatTempF(104.9)).toBe("104.9°F");
    expect(formatDeltaC(2.3)).toBe("-2.3°C");
    expect(formatTemp(null)).toBe("—");
  });

  it("formats hours, percentages, currency, and numbers", () => {
    expect(formatHours(8.5)).toBe("8.5 hrs");
    expect(formatHours(null)).toBe("—");
    expect(formatPercent(77.15)).toBe("77.2%");
    expect(formatPercent(null)).toBe("—");
    expect(formatCurrency(500000)).toBe("$500,000");
    expect(formatNumber(2400)).toBe("2,400");
  });

  it("returns correct risk styling classes", () => {
    const extreme = getRiskColor("extreme");
    expect(extreme.text).toContain("rose");
    const severe = getRiskColor("severe");
    expect(severe.text).toContain("red");
    const high = getRiskColor("high");
    expect(high.text).toContain("orange");
    const moderate = getRiskColor("moderate");
    expect(moderate.text).toContain("amber");
    const low = getRiskColor("low");
    expect(low.text).toContain("emerald");
  });

  it("formats asset type labels and score progress colors", () => {
    expect(getAssetTypeLabel("bus_stop")).toBe("Transit Stop");
    expect(getAssetTypeLabel("playground")).toBe("Playground");
    expect(getScoreProgressColor(85)).toBe("bg-rose-900");
    expect(getScoreProgressColor(15)).toBe("bg-emerald-500");
  });
});

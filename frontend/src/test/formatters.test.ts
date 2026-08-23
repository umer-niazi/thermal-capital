import { describe, expect, it } from "vitest";
import {
  celsiusDeltaToFahrenheit,
  celsiusToFahrenheit,
  fahrenheitToCelsius,
  formatCurrency,
  formatDeltaC,
  formatHours,
  formatNumber,
  formatPercent,
  formatTemp,
  formatTempC,
  formatTempF,
  formatTemperature,
  formatTemperatureDelta,
  formatTemperatureRange,
  formatTemperatureValue,
  getAssetTypeLabel,
  getRiskColor,
  getScoreProgressColor,
} from "../utils/formatters";

describe("Formatting Utilities", () => {
  it("converts absolute temperatures accurately between Celsius and Fahrenheit", () => {
    expect(celsiusToFahrenheit(0)).toBe(32);
    expect(celsiusToFahrenheit(40)).toBe(104);
    expect(celsiusToFahrenheit(41.2)).toBeCloseTo(106.16, 2);
    expect(fahrenheitToCelsius(32)).toBe(0);
    expect(fahrenheitToCelsius(104)).toBe(40);
  });

  it("converts temperature differences (deltas) accurately without absolute 32 offset", () => {
    // 2.2°C difference = 3.96°F difference
    expect(celsiusDeltaToFahrenheit(2.2)).toBeCloseTo(3.96, 2);
    expect(celsiusDeltaToFahrenheit(1.0)).toBe(1.8);
    expect(formatTemperatureDelta(2.2, "F", 1)).toBe("-4.0°F");
    expect(formatTemperatureDelta(2.2, "C", 1)).toBe("-2.2°C");
    expect(formatTemperatureDelta(null, "F")).toBe("—");
  });

  it("formats temperature values and ranges according to unit preference", () => {
    // Fahrenheit default
    expect(formatTemperature(41.2, "F")).toBe("106.2°F");
    expect(formatTemperatureValue(41.2, "F")).toBe("106.2");
    expect(formatTemperatureRange(33.0, 41.0, "F")).toBe("91.4–105.8°F");

    // Celsius option
    expect(formatTemperature(41.2, "C")).toBe("41.2°C");
    expect(formatTemperatureValue(41.2, "C")).toBe("41.2");
    expect(formatTemperatureRange(33.0, 41.0, "C")).toBe("33.0–41.0°C");

    // Null safety
    expect(formatTemperature(null, "F")).toBe("—");
    expect(formatTemperatureRange(null, 41.0, "F")).toBe("—");
  });

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

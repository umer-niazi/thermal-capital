import React, { createContext, useContext, useState } from "react";
import { TemperatureUnit } from "../types";
import {
  formatTemperature,
  formatTemperatureDelta,
  formatTemperatureRange,
  formatTemperatureValue,
} from "../utils/formatters";

export const TEMPERATURE_STORAGE_KEY = "thermal_capital_temp_unit";

export interface TemperatureContextType {
  unit: TemperatureUnit;
  setUnit: (unit: TemperatureUnit) => void;
  toggleUnit: () => void;
  formatTemp: (celsius: number | null | undefined, fractionDigits?: number) => string;
  formatDelta: (deltaCelsius: number | null | undefined, fractionDigits?: number, prefix?: string) => string;
  formatRange: (minCelsius: number | null | undefined, maxCelsius: number | null | undefined, fractionDigits?: number) => string;
  formatValue: (celsius: number | null | undefined, fractionDigits?: number) => string;
}

export const TemperatureContext = createContext<TemperatureContextType>({
  unit: "F",
  setUnit: () => {},
  toggleUnit: () => {},
  formatTemp: (celsius, fractionDigits) => formatTemperature(celsius, "F", fractionDigits),
  formatDelta: (deltaCelsius, fractionDigits, prefix) => formatTemperatureDelta(deltaCelsius, "F", fractionDigits, prefix),
  formatRange: (minC, maxC, fractionDigits) => formatTemperatureRange(minC, maxC, "F", fractionDigits),
  formatValue: (celsius, fractionDigits) => formatTemperatureValue(celsius, "F", fractionDigits),
});

export const TemperatureProvider: React.FC<{
  children: React.ReactNode;
  initialUnit?: TemperatureUnit;
}> = ({ children, initialUnit }) => {
  const [unit, setUnitState] = useState<TemperatureUnit>(() => {
    if (initialUnit) return initialUnit;
    try {
      const saved = localStorage.getItem(TEMPERATURE_STORAGE_KEY);
      if (saved === "C" || saved === "F") {
        return saved;
      }
    } catch {
      // localStorage might not be accessible
    }
    return "F";
  });

  const setUnit = (newUnit: TemperatureUnit) => {
    setUnitState(newUnit);
    try {
      localStorage.setItem(TEMPERATURE_STORAGE_KEY, newUnit);
    } catch {
      // localStorage might not be accessible
    }
  };

  const toggleUnit = () => {
    setUnit(unit === "F" ? "C" : "F");
  };

  const formatTemp = (celsius: number | null | undefined, fractionDigits: number = 1) => {
    return formatTemperature(celsius, unit, fractionDigits);
  };

  const formatDelta = (
    deltaCelsius: number | null | undefined,
    fractionDigits: number = 1,
    prefix: string = "-"
  ) => {
    return formatTemperatureDelta(deltaCelsius, unit, fractionDigits, prefix);
  };

  const formatRange = (
    minC: number | null | undefined,
    maxC: number | null | undefined,
    fractionDigits: number = 1
  ) => {
    return formatTemperatureRange(minC, maxC, unit, fractionDigits);
  };

  const formatValue = (celsius: number | null | undefined, fractionDigits: number = 1) => {
    return formatTemperatureValue(celsius, unit, fractionDigits);
  };

  return (
    <TemperatureContext.Provider
      value={{
        unit,
        setUnit,
        toggleUnit,
        formatTemp,
        formatDelta,
        formatRange,
        formatValue,
      }}
    >
      {children}
    </TemperatureContext.Provider>
  );
};

export function useTemperature(): TemperatureContextType {
  return useContext(TemperatureContext);
}

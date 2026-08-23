import { AssetType, HeatRiskLevel, TemperatureUnit } from "../types";

export function celsiusToFahrenheit(celsius: number): number {
  return (celsius * 9.0) / 5.0 + 32.0;
}

export function fahrenheitToCelsius(fahrenheit: number): number {
  return ((fahrenheit - 32.0) * 5.0) / 9.0;
}

export function celsiusDeltaToFahrenheit(deltaCelsius: number): number {
  return deltaCelsius * 1.8;
}

export function formatTemperature(
  celsius: number | null | undefined,
  unit: TemperatureUnit = "F",
  fractionDigits: number = 1
): string {
  if (celsius === null || celsius === undefined || isNaN(celsius)) return "—";
  const val = unit === "F" ? celsiusToFahrenheit(celsius) : celsius;
  return `${val.toFixed(fractionDigits)}°${unit}`;
}

export function formatTemperatureValue(
  celsius: number | null | undefined,
  unit: TemperatureUnit = "F",
  fractionDigits: number = 1
): string {
  if (celsius === null || celsius === undefined || isNaN(celsius)) return "0";
  const val = unit === "F" ? celsiusToFahrenheit(celsius) : celsius;
  return val.toFixed(fractionDigits);
}

export function formatTemperatureDelta(
  deltaCelsius: number | null | undefined,
  unit: TemperatureUnit = "F",
  fractionDigits: number = 1,
  prefix: string = "-"
): string {
  if (deltaCelsius === null || deltaCelsius === undefined || isNaN(deltaCelsius)) return "—";
  const absVal = Math.abs(deltaCelsius);
  const converted = unit === "F" ? celsiusDeltaToFahrenheit(absVal) : absVal;
  return `${prefix}${converted.toFixed(fractionDigits)}°${unit}`;
}

export function formatTemperatureRange(
  minCelsius: number | null | undefined,
  maxCelsius: number | null | undefined,
  unit: TemperatureUnit = "F",
  fractionDigits: number = 1
): string {
  if (
    minCelsius === null ||
    minCelsius === undefined ||
    isNaN(minCelsius) ||
    maxCelsius === null ||
    maxCelsius === undefined ||
    isNaN(maxCelsius)
  ) {
    return "—";
  }
  const minVal = unit === "F" ? celsiusToFahrenheit(minCelsius) : minCelsius;
  const maxVal = unit === "F" ? celsiusToFahrenheit(maxCelsius) : maxCelsius;
  return `${minVal.toFixed(fractionDigits)}–${maxVal.toFixed(fractionDigits)}°${unit}`;
}

export function formatTemp(celsius: number | null | undefined, fahrenheit?: number | null | undefined): string {
  if (celsius === null || celsius === undefined || isNaN(celsius)) return "—";
  const f = fahrenheit ?? celsiusToFahrenheit(celsius);
  return `${celsius.toFixed(1)}°C / ${f.toFixed(1)}°F`;
}

export function formatTempC(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return "—";
  return `${val.toFixed(1)}°C`;
}

export function formatTempF(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return "—";
  return `${val.toFixed(1)}°F`;
}

export function formatDeltaC(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return "—";
  const sign = val > 0 ? "-" : "+";
  return `${sign}${Math.abs(val).toFixed(1)}°C`;
}

export function formatHours(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return "—";
  return `${val.toFixed(1)} hrs`;
}

export function formatPercent(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return "—";
  return `${val.toFixed(1)}%`;
}

export function formatCurrency(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return "$0";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(val);
}

export function formatNumber(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return "0";
  return new Intl.NumberFormat("en-US").format(val);
}

export function getRiskColor(category: string | HeatRiskLevel): {
  badge: string;
  text: string;
  bg: string;
  border: string;
  halo: string;
} {
  const cat = String(category).toLowerCase();
  if (cat === "extreme") {
    return {
      badge: "bg-rose-100 text-rose-950 border-rose-300",
      text: "text-rose-900",
      bg: "bg-rose-900",
      border: "border-rose-400",
      halo: "#7f1d1d",
    };
  }
  if (cat === "critical" || cat === "severe") {
    return {
      badge: "bg-red-50 text-red-800 border-red-300",
      text: "text-red-700",
      bg: "bg-red-600",
      border: "border-red-300",
      halo: "#dc2626",
    };
  }
  if (cat === "high") {
    return {
      badge: "bg-orange-50 text-orange-900 border-orange-300",
      text: "text-orange-700",
      bg: "bg-orange-600",
      border: "border-orange-300",
      halo: "#ea580c",
    };
  }
  if (cat === "moderate") {
    return {
      badge: "bg-amber-50 text-amber-900 border-amber-300",
      text: "text-amber-800",
      bg: "bg-amber-500",
      border: "border-amber-300",
      halo: "#d97706",
    };
  }
  return {
    badge: "bg-emerald-50 text-emerald-800 border-emerald-300",
    text: "text-emerald-700",
    bg: "bg-emerald-600",
    border: "border-emerald-300",
    halo: "#16a34a",
  };
}

export function getAssetTypeLabel(type: AssetType | string): string {
  switch (type) {
    case "bus_stop":
      return "Transit Stop";
    case "playground":
      return "Playground";
    case "school":
      return "School";
    case "park":
      return "Public Park";
    case "pedestrian_corridor":
      return "Pedestrian Corridor";
    case "public_plaza":
      return "Public Plaza";
    case "community_center":
      return "Community Center";
    default:
      return String(type).replace("_", " ").replace(/\b\w/g, (l) => l.toUpperCase());
  }
}

export function getScoreProgressColor(score: number): string {
  if (score >= 80) return "bg-rose-900";
  if (score >= 65) return "bg-red-600";
  if (score >= 45) return "bg-orange-500";
  if (score >= 25) return "bg-amber-500";
  return "bg-emerald-500";
}

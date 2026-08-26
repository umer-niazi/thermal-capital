import React from "react";
import { AppMode, CityConfig, CoverageSummary } from "../types";
import { useTemperature } from "../context/TemperatureContext";
import {
  ChevronRight,
  Compass,
  FileText,
  Layers,
  SlidersHorizontal,
} from "lucide-react";

interface HeaderProps {
  currentCity: CityConfig;
  allCities: CityConfig[];
  onSelectCity: (cityKey: string) => void;
  appMode: AppMode;
  onSwitchMode: (mode: AppMode) => void;
  onOpenOptimizer: () => void;
  onOpenReport: () => void;
  coverageSummary?: CoverageSummary | null;
}

export const Header: React.FC<HeaderProps> = ({
  currentCity,
  allCities,
  onSelectCity,
  appMode,
  onSwitchMode,
  onOpenOptimizer,
  onOpenReport,
  coverageSummary,
}) => {
  const { unit, setUnit } = useTemperature();
  return (
    <header className="h-14 bg-white border-b border-slate-200 flex items-center justify-between px-2 sm:px-4 lg:px-6 z-20 flex-shrink-0 gap-1.5 sm:gap-2">
      {/* Left: Brand Title, NYC Focus Selector & Coverage Badge */}
      <div className="flex items-center gap-1.5 sm:gap-3 min-w-0">
        <div className="flex items-baseline gap-1.5 sm:gap-2 flex-shrink-0">
          <span className="font-bold text-sm sm:text-base text-slate-900 tracking-tight">
            Thermal Capital
          </span>
          <span className="text-xs text-slate-500 font-normal hidden lg:inline border-l border-slate-200 pl-2">
            Capital planning for urban heat
          </span>
        </div>

        {/* NYC Focus Selector */}
        <div className="flex items-center gap-1 sm:gap-2 pl-1.5 sm:pl-3 border-l border-slate-200 min-w-0">
          <label htmlFor="city-select" className="text-xs font-medium text-slate-600 hidden md:inline">
            NYC Area:
          </label>
          <select
            id="city-select"
            aria-label="Select city location"
            value={currentCity.city_key}
            onChange={(e) => onSelectCity(e.target.value)}
            className="bg-slate-50 hover:bg-slate-100 border border-slate-300 rounded px-1.5 sm:px-2.5 py-1 text-xs text-slate-800 font-medium focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-slate-400 cursor-pointer transition-colors max-w-[125px] xs:max-w-[155px] sm:max-w-[200px] md:max-w-[240px] truncate"
          >
            {allCities.map((c) => (
              <option key={c.city_key} value={c.city_key}>
                {c.display_label || c.name}
              </option>
            ))}
          </select>
        </div>

        {/* FortyGuard Authentic Coverage Indicator (Demoted / Non-competing) */}
        <div
          className="hidden xl:flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-normal text-slate-500 bg-slate-50 border border-slate-200 flex-shrink-0"
          title="Authentic FortyGuard 100m Microclimate Grid across NYC"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 flex-shrink-0" />
          <span>FortyGuard Coverage: NYC • {coverageSummary?.coverage_percentage ?? 100}%</span>
        </div>
      </div>

      {/* Center: Connected 2-Step Workflow Stepper */}
      <nav
        className="flex items-center bg-slate-100/90 p-0.5 rounded-md border border-slate-200 flex-shrink-0"
        aria-label="Planning workflow steps"
      >
        {/* Step 1: Identify Risk */}
        <button
          onClick={() => onSwitchMode("explore")}
          aria-label="1. Identify Risk"
          aria-current={appMode === "explore" ? "step" : undefined}
          className={`w-[98px] sm:w-[142px] h-[30px] whitespace-nowrap flex items-center justify-center gap-1 sm:gap-1.5 px-2 sm:px-3 text-xs rounded transition-colors font-semibold focus:outline-none focus:ring-2 focus:ring-slate-400 flex-shrink-0 ${
            appMode === "explore"
              ? "bg-slate-900 text-white shadow-xs"
              : "text-slate-600 hover:text-slate-900 hover:bg-slate-200/50"
          }`}
        >
          <Compass className="w-3.5 h-3.5 flex-shrink-0" />
          <span className="hidden sm:inline">1. Identify Risk</span>
          <span className="sm:hidden">1. Identify</span>
        </button>

        {/* Connected Stepper Separator */}
        <ChevronRight className="w-3.5 h-3.5 text-slate-400 mx-0.5 flex-shrink-0" aria-hidden="true" />

        {/* Step 2: Intervene & Compare */}
        <button
          onClick={() => onSwitchMode("plan")}
          aria-label="2. Intervene & Compare"
          aria-current={appMode === "plan" ? "step" : undefined}
          className={`w-[106px] sm:w-[188px] h-[30px] whitespace-nowrap flex items-center justify-center gap-1 sm:gap-1.5 px-2 sm:px-3 text-xs rounded transition-colors font-semibold focus:outline-none focus:ring-2 focus:ring-slate-400 flex-shrink-0 ${
            appMode === "plan"
              ? "bg-slate-900 text-white shadow-xs"
              : "text-slate-600 hover:text-slate-900 hover:bg-slate-200/50"
          }`}
        >
          <Layers className="w-3.5 h-3.5 flex-shrink-0" />
          <span className="hidden sm:inline whitespace-nowrap">2. Intervene &amp; Compare</span>
          <span className="sm:hidden">2. Intervene</span>
        </button>
      </nav>

      {/* Right: Secondary Tools & Temperature Unit Preference */}
      <div className="flex items-center gap-1 sm:gap-2 flex-shrink-0">
        {/* Temperature Unit Segmented Toggle */}
        <div
          className="flex items-center bg-slate-100 p-0.5 rounded border border-slate-300 flex-shrink-0"
          role="group"
          aria-label="Temperature unit preference"
        >
          <button
            type="button"
            onClick={() => setUnit("F")}
            aria-pressed={unit === "F"}
            aria-label="Display temperature in Fahrenheit"
            title="Display in Fahrenheit (°F)"
            className={`w-7 sm:w-8 h-[26px] flex items-center justify-center text-xs font-semibold rounded border transition-colors focus:outline-none focus:ring-1 focus:ring-slate-400 flex-shrink-0 ${
              unit === "F"
                ? "bg-white text-slate-900 shadow-xs border-slate-200/80"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            °F
          </button>
          <button
            type="button"
            onClick={() => setUnit("C")}
            aria-pressed={unit === "C"}
            aria-label="Display temperature in Celsius"
            title="Display in Celsius (°C)"
            className={`w-7 sm:w-8 h-[26px] flex items-center justify-center text-xs font-semibold rounded border transition-colors focus:outline-none focus:ring-1 focus:ring-slate-400 flex-shrink-0 ${
              unit === "C"
                ? "bg-white text-slate-900 shadow-xs border-slate-200/80"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            °C
          </button>
        </div>

        <button
          onClick={onOpenOptimizer}
          aria-label="Open budget optimizer"
          className="flex items-center gap-1 sm:gap-1.5 px-2 sm:px-3 py-1.5 text-xs font-medium text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 rounded transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400 min-h-[32px]"
        >
          <SlidersHorizontal className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />
          <span className="hidden md:inline">Optimize Budget</span>
          <span className="md:hidden">Optimize</span>
        </button>

        <button
          onClick={onOpenReport}
          aria-label="Open planning brief"
          className="flex items-center gap-1 sm:gap-1.5 px-2 sm:px-3 py-1.5 text-xs font-medium text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 rounded transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400 min-h-[32px]"
        >
          <FileText className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />
          <span className="hidden sm:inline">Planning Brief</span>
          <span className="sm:hidden">Brief</span>
        </button>
      </div>
    </header>
  );
};

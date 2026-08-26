import React from "react";
import { PublicAsset } from "../types";
import { useTemperature } from "../context/TemperatureContext";
import {
  formatNumber,
  formatTempC,
  formatTempF,
  getAssetTypeLabel,
  getRiskColor,
} from "../utils/formatters";
import {
  ArrowLeft,
  Layers,
  X,
} from "lucide-react";

interface SiteDetailProps {
  asset: PublicAsset;
  onBack: () => void;
  onPlanIntervention: () => void;
}

export const SiteDetail: React.FC<SiteDetailProps> = ({
  asset,
  onBack,
  onPlanIntervention,
}) => {
  const { unit, formatTemp } = useTemperature();
  const obs = asset.observed_heat;
  const risk = getRiskColor(asset.heat_risk_level);

  return (
    <div className="p-4 space-y-4 text-slate-900">
      {/* Back to Priority List & Header Actions */}
      <div className="flex items-center justify-between gap-2">
        <button
          onClick={onBack}
          aria-label="Back to all priority areas"
          className="h-9 px-3 flex items-center gap-1.5 text-xs text-slate-700 hover:text-slate-900 font-medium rounded bg-white hover:bg-slate-100 border border-slate-200 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400 min-h-[36px]"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>All Priority Areas</span>
        </button>

        <div className="flex items-center gap-1.5">
          <button
            onClick={onPlanIntervention}
            className="h-9 flex items-center gap-1.5 px-3.5 bg-brand-600 hover:bg-brand-700 text-white rounded text-xs font-semibold shadow-xs transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 min-h-[36px]"
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Test</span>
          </button>

          <button
            onClick={onBack}
            aria-label="Close"
            title="Close"
            className="w-9 h-9 inline-flex items-center justify-center rounded text-slate-500 hover:text-slate-900 hover:bg-slate-200 focus:outline-none focus:ring-2 focus:ring-slate-400 transition-colors min-h-[36px] min-w-[36px]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Area Title & Type */}
      <div className="border-b border-slate-200 pb-3">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[11px] font-medium text-slate-500 font-mono">
            {asset.asset_id}
          </span>
          <span>•</span>
          <span className="text-[11px] font-medium text-slate-500 font-mono">
            Tile T-{String(obs.contributing_tile_id ?? (obs.hotspot_rank || 1)).padStart(4, "0")}
          </span>
          <span>•</span>
          <span className="text-[11px] font-medium text-slate-600">
            {getAssetTypeLabel(asset.asset_type)}
          </span>
        </div>
        <h2
          className="text-base font-bold text-slate-900 tracking-tight leading-snug"
          title={asset.name}
        >
          {asset.name}
        </h2>
        <p className="text-xs text-slate-500 mt-0.5">
          ~{formatNumber(asset.daily_visitors)} daily users • {asset.footprint_m2.toFixed(0)} m² area
        </p>
      </div>

      {/* Core Heat Metrics Grid */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-[11px] text-slate-500">
          <span className="font-semibold uppercase tracking-wider">Observed Microclimate Baseline</span>
          <span>FortyGuard 100m Grid</span>
        </div>
        <div className="grid grid-cols-2 gap-3 text-xs">
          <div className="bg-white border border-slate-200 p-2.5 rounded">
            <span className="text-[11px] text-slate-600 block mb-0.5">Priority Risk Rating</span>
            <div className={`inline-block px-1.5 py-0.5 rounded text-xs font-bold border ${risk.badge}`}>
              {asset.heat_risk_level.toUpperCase()}
            </div>
          </div>

        <div className="bg-white border border-slate-200 p-2.5 rounded">
          <span className="text-[11px] text-slate-600 block mb-0.5">Peak Temperature</span>
          <div className="font-mono text-sm font-bold text-slate-900">
            {formatTemp(obs.peak_temperature_c)}
            <span className="text-[11px] font-normal text-slate-500 ml-1">
              ({unit === "F" ? formatTempC(obs.peak_temperature_c) : formatTempF(obs.peak_temperature_f)})
            </span>
          </div>
        </div>

        <div className="bg-white border border-slate-200 p-2.5 rounded">
          <span className="text-[11px] text-slate-600 block mb-0.5">{unit === "F" ? "Hours Above 95°F" : "Hours Above 35°C"}</span>
          <div className="font-mono text-sm font-bold text-slate-900">
            {obs.hours_above_35c.toFixed(1)} h
            <span className="text-[11px] font-normal text-slate-500 ml-1">({obs.persistence_hours.toFixed(1)}h run)</span>
          </div>
        </div>

        <div className="bg-white border border-slate-200 p-2.5 rounded">
          <span className="text-[11px] text-slate-600 block mb-0.5">Overnight Minimum</span>
          <div className="font-mono text-sm font-bold text-slate-900">
            {formatTemp(obs.overnight_min_c)}
            <span className="text-[11px] font-normal text-slate-500 ml-1">
              ({unit === "F" ? formatTempC(obs.overnight_min_c) : formatTempF(obs.overnight_min_f)})
            </span>
          </div>
        </div>
      </div>
    </div>

      {/* Surface Composition Table (Baseline) */}
      <div className="bg-white border border-slate-200 rounded p-3 text-xs space-y-1.5">
        <span className="text-xs font-semibold text-slate-800 block">Existing Land Cover (Baseline)</span>
        <div className="flex items-center justify-between text-slate-600 text-xs pt-1">
          <span>Tree canopy: <strong className="text-slate-900 font-mono">{obs.canopy_pct.toFixed(0)}%</strong></span>
          <span>Impervious surface: <strong className="text-slate-900 font-mono">{obs.impervious_pct.toFixed(0)}%</strong></span>
        </div>
      </div>

      {/* Why This Area is a Priority (Quiet Restrained Municipal Rationale) */}
      <div className="bg-slate-50/80 border border-slate-200 border-l-[3px] border-l-amber-500 rounded p-3 space-y-1.5 text-xs">
        <div className="flex items-center justify-between gap-2">
          <span className="font-semibold text-slate-800 text-xs">
            Why is this area a priority?
          </span>
          <span className={`text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded border ${risk.badge}`}>
            Priority: {asset.priority_level || asset.heat_risk_level}
          </span>
        </div>

        <ul className="space-y-1 text-xs text-slate-600 list-disc list-inside leading-snug">
          {(asset.priority_reasons && asset.priority_reasons.length > 0) ? (
            asset.priority_reasons.map((r, i) => <li key={i} className="text-slate-700">{r}</li>)
          ) : (
            <>
              <li>High afternoon peak thermal exposure ({formatTemp(obs.peak_temperature_c)})</li>
              <li>Limited overnight cooling recovery ({formatTemp(obs.overnight_min_c)} minimum)</li>
              <li>Extended heat persistence ({obs.hours_above_35c.toFixed(1)}h exceeding {unit === "F" ? "95°F" : "35°C"})</li>
              <li>High daily pedestrian and transit usage (~{formatNumber(asset.daily_visitors)} citizens)</li>
              <li>Severe vegetative canopy deficit ({obs.canopy_pct.toFixed(0)}% canopy)</li>
            </>
          )}
        </ul>
      </div>

      {/* Test Action Trigger */}
      <button
        onClick={onPlanIntervention}
        className="w-full py-2.5 px-3 bg-brand-600 hover:bg-brand-700 text-white rounded text-xs font-semibold shadow-xs transition-colors flex items-center justify-center gap-1.5 focus:outline-none focus:ring-2 focus:ring-brand-500 min-h-[36px]"
      >
        <Layers className="w-3.5 h-3.5" />
        <span>Test Cooling Interventions on This Area</span>
      </button>
    </div>
  );
};

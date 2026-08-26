import React, { useEffect, useState } from "react";
import {
  BudgetOptimizationResult,
  CityConfig,
  OptimizationStrategy,
} from "../types";
import { optimizeBudget } from "../services/api";
import {
  formatCurrency,
  formatNumber,
  getAssetTypeLabel,
  getRiskColor,
} from "../utils/formatters";
import { useTemperature } from "../context/TemperatureContext";
import { ProgressStageCard } from "./ProgressStageCard";
import {
  CheckCircle2,
  FileText,
  SlidersHorizontal,
  X,
} from "lucide-react";

interface BudgetOptimizerModalProps {
  cityConfig: CityConfig;
  onClose: () => void;
  onApplyPortfolio: (result: BudgetOptimizationResult) => void;
  onOpenReport: (result: BudgetOptimizationResult) => void;
}

export const BudgetOptimizerModal: React.FC<BudgetOptimizerModalProps> = ({
  cityConfig,
  onClose,
  onApplyPortfolio,
  onOpenReport,
}) => {
  const [budget, setBudget] = useState<number>(500000);
  const [strategy, setStrategy] = useState<OptimizationStrategy>("balanced");
  const [result, setResult] = useState<BudgetOptimizationResult | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const { unit, formatDelta } = useTemperature();

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    optimizeBudget({
      city: cityConfig.city_key,
      budget: budget,
      strategy: strategy,
    })
      .then((res) => {
        if (isMounted) {
          setResult(res);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.error("Optimization failed:", err);
          setError(err.message || "Failed to calculate optimization");
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [budget, strategy, cityConfig.city_key]);

  const budgetPresets = [100000, 250000, 500000, 1000000];

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-2 sm:p-4 lg:p-6 animate-in fade-in duration-150"
      role="dialog"
      aria-modal="true"
      aria-labelledby="budget-optimizer-title"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="bg-white border border-slate-300 w-full max-w-4xl max-h-[94vh] sm:max-h-[90vh] rounded-lg shadow-xl flex flex-col overflow-hidden text-slate-900"
      >
        {/* Header */}
        <div className="h-13 sm:h-14 border-b border-slate-200 px-3.5 sm:px-5 flex items-center justify-between flex-shrink-0 bg-slate-50">
          <div className="flex items-center gap-2 sm:gap-2.5 min-w-0">
            <SlidersHorizontal className="w-4 h-4 text-slate-700 flex-shrink-0" />
            <div className="min-w-0">
              <h2 id="budget-optimizer-title" className="text-xs sm:text-sm font-bold text-slate-900 tracking-tight truncate">
                Budget Optimization — {cityConfig.name}, {cityConfig.state}
              </h2>
            </div>
          </div>

          <button
            onClick={onClose}
            aria-label="Close dialog"
            className="w-9 h-9 inline-flex items-center justify-center rounded text-slate-500 hover:text-slate-900 hover:bg-slate-200 focus:outline-none focus:ring-2 focus:ring-slate-400 transition-colors flex-shrink-0 ml-1"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-3 sm:p-5 space-y-4 sm:space-y-5 custom-scrollbar">
          {/* Controls Bar */}
          <div className="bg-slate-50 border border-slate-200 p-3 sm:p-4 rounded space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Budget Slider */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
                  <label htmlFor="budget-slider">Target Capital Budget:</label>
                  <span className="font-mono text-sm font-bold text-slate-900">
                    {formatCurrency(budget)}
                  </span>
                </div>

                <input
                  id="budget-slider"
                  type="range"
                  aria-label="Target capital budget"
                  min={50000}
                  max={2000000}
                  step={25000}
                  value={budget}
                  onChange={(e) => setBudget(Number(e.target.value))}
                  className="w-full h-2 sm:h-1.5 bg-slate-200 rounded appearance-none cursor-pointer accent-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-500"
                />

                <div className="flex flex-wrap items-center gap-1.5 pt-1">
                  {budgetPresets.map((amt) => (
                    <button
                      key={amt}
                      onClick={() => setBudget(amt)}
                      className={`px-2.5 py-1 text-xs rounded transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400 min-h-[30px] ${
                        budget === amt
                          ? "bg-slate-800 text-white font-semibold"
                          : "bg-white text-slate-700 border border-slate-300 hover:bg-slate-100"
                      }`}
                    >
                      {formatCurrency(amt)}
                    </button>
                  ))}
                </div>
              </div>

              {/* Strategy Selector */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-700 block">
                  Optimization Priority:
                </label>
                <div className="grid grid-cols-2 gap-1.5 text-xs">
                  {[
                    { key: "balanced", label: "Balanced", desc: "Equitable distribution" },
                    { key: "vulnerable_populations", label: "Vulnerable Users", desc: "Schools & playgrounds" },
                    { key: "transit_corridors", label: "Transit Corridors", desc: "Bus stops & stations" },
                    { key: "max_heat_reduction", label: "Maximum Relief", desc: "Hottest microclimate tiles" },
                  ].map((s) => (
                    <button
                      key={s.key}
                      onClick={() => setStrategy(s.key as OptimizationStrategy)}
                      className={`p-2 text-left rounded border transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 min-h-[44px] ${
                        strategy === s.key
                          ? "bg-brand-50 border-brand-500 text-brand-900 font-semibold"
                          : "bg-white border-slate-200 text-slate-700 hover:bg-slate-50"
                      }`}
                    >
                      <div>{s.label}</div>
                      <div className="text-[10px] text-slate-500 font-normal">{s.desc}</div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Results Area */}
          {loading ? (
            <div className="py-6">
              <ProgressStageCard
                title="Calculating Optimal Capital Allocation"
                subtitle={`Simulating ${cityConfig.name} microclimate portfolio`}
                stages={[
                  { id: "assets", label: "Loading priority public asset inventory", status: "completed" },
                  { id: "exposure", label: "Evaluating FortyGuard microclimate exposure & vulnerability", status: "completed" },
                  { id: "knapsack", label: "Solving multi-variable capital allocation model", status: "active" },
                  { id: "portfolio", label: "Finalizing optimal municipal intervention portfolio", status: "pending" },
                ]}
              />
            </div>
          ) : error || !result ? (
            <div className="p-3 rounded bg-red-50 border border-red-200 text-red-700 text-xs">
              {error || "Failed to calculate optimization"}
            </div>
          ) : (
            <div className="space-y-4">
              {/* Metric Highlights */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
                <div className="bg-white border border-slate-200 p-2.5 rounded">
                  <span className="text-[11px] text-slate-500 block">Allocated Capital</span>
                  <div className="text-sm font-bold text-slate-900 font-mono">
                    {formatCurrency(result.total_allocated_cost)}
                  </div>
                  <div className="text-[10px] text-slate-500">
                    Remaining: {formatCurrency(result.remaining_budget)}
                  </div>
                </div>

                <div className="bg-white border border-slate-200 p-2.5 rounded">
                  <span className="text-[11px] text-slate-500 block">Planned Interventions</span>
                  <div className="text-sm font-bold text-slate-900">
                    {result.total_trees} Trees • {result.total_shade_structures} Shade
                  </div>
                  <div className="text-[10px] text-slate-500">
                    {formatNumber(result.total_cool_pavement_m2)} m² Cool Pavement
                  </div>
                </div>

                <div className="bg-white border border-slate-200 p-2.5 rounded">
                  <span className="text-[11px] text-slate-500 block">Modeled Average Relief</span>
                  <div className="text-sm font-bold text-brand-700 font-mono">
                    {formatDelta(result.portfolio_avg_peak_reduction_c)}
                  </div>
                  <div className="text-[10px] text-slate-500">
                    -{result.portfolio_avg_hours_reduction_pct.toFixed(0)}% &gt;{unit === "F" ? "95°F" : "35°C"} hours (modeled)
                  </div>
                </div>

                <div className="bg-white border border-slate-200 p-2.5 rounded">
                  <span className="text-[11px] text-slate-500 block">Estimated Protected Users</span>
                  <div className="text-sm font-bold text-slate-900 font-mono">
                    ~{formatNumber(result.total_benefited_population)} / day
                  </div>
                  <div className="text-[10px] text-slate-500">
                    Across {result.total_assets_covered} priority assets
                  </div>
                </div>
              </div>

              {/* Asset Allocation Table */}
              <div className="space-y-1.5">
                <span className="text-xs font-semibold text-slate-800 block">
                  Recommended Site Allocations ({result.asset_allocations.length} Sites)
                </span>

                <div className="border border-slate-200 rounded overflow-x-auto custom-scrollbar">
                  <table className="w-full text-xs text-left border-collapse font-sans min-w-[620px]">
                    <thead className="bg-slate-50 text-slate-700 border-b border-slate-200">
                      <tr>
                        <th className="p-2.5 font-semibold">Asset</th>
                        <th className="p-2.5 font-semibold">Type</th>
                        <th className="p-2.5 font-semibold">Risk Level</th>
                        <th className="p-2.5 font-semibold">Allocated Package</th>
                        <th className="p-2.5 font-semibold text-right">Cost</th>
                        <th className="p-2.5 font-semibold text-right">Modeled ΔT</th>
                        <th className="p-2.5 font-semibold text-right">Protected Users</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 bg-white">
                      {result.asset_allocations.map((alloc) => {
                        const risk = getRiskColor(alloc.heat_risk_level);
                        const pkg = alloc.recommended_interventions
                          .map((i) =>
                            i.quantity > 0
                              ? `${i.quantity} ${i.intervention_type.replace("_", " ")}`
                              : `${i.area_m2.toFixed(0)}m² ${i.intervention_type.replace("_", " ")}`
                          )
                          .join(", ");

                        return (
                          <tr key={alloc.asset_id} className="hover:bg-slate-50">
                            <td className="p-2.5 font-medium text-slate-900">
                              {alloc.asset_name}
                            </td>
                            <td className="p-2.5 text-slate-600">{getAssetTypeLabel(alloc.asset_type)}</td>
                            <td className="p-2.5">
                              <span className={`px-1.5 py-0.2 rounded text-[10px] font-medium border ${risk.badge}`}>
                                {alloc.heat_risk_level}
                              </span>
                            </td>
                            <td className="p-2.5 text-slate-600">{pkg || "Trees & shade"}</td>
                            <td className="p-2.5 text-right font-mono text-slate-900">
                              {formatCurrency(alloc.allocated_cost)}
                            </td>
                            <td className="p-2.5 text-right font-mono font-bold text-brand-700">
                              {formatDelta(alloc.modeled_peak_reduction_c)}
                            </td>
                            <td className="p-2.5 text-right font-mono text-slate-600">
                              {formatNumber(alloc.benefited_daily_population)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="h-auto sm:h-14 py-2.5 sm:py-0 border-t border-slate-200 px-3.5 sm:px-5 flex flex-wrap items-center justify-between gap-2 flex-shrink-0 bg-slate-50">
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-xs font-medium text-slate-700 bg-white hover:bg-slate-100 rounded border border-slate-300 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400 min-h-[34px]"
          >
            Close
          </button>

          {result && (
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={() => onOpenReport(result)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white hover:bg-slate-100 rounded border border-slate-300 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400 min-h-[34px]"
              >
                <FileText className="w-3.5 h-3.5 text-slate-500" />
                <span>Action Brief</span>
              </button>

              <button
                onClick={() => {
                  onApplyPortfolio(result);
                  onClose();
                }}
                className="flex items-center gap-1.5 px-3.5 sm:px-4 py-1.5 text-xs font-semibold text-white bg-brand-600 hover:bg-brand-700 rounded shadow-xs transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 min-h-[34px]"
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Apply Portfolio to Map</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

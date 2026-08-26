import React, { useEffect, useState } from "react";
import { BudgetOptimizationResult, CityConfig, PlanningReport } from "../types";
import { generateReport } from "../services/api";
import { formatCurrency, formatNumber } from "../utils/formatters";
import { useTemperature } from "../context/TemperatureContext";
import { ProgressStageCard } from "./ProgressStageCard";
import {
  Check,
  Copy,
  FileText,
  Printer,
  X,
} from "lucide-react";

interface PlanningBriefModalProps {
  cityConfig: CityConfig;
  optResult?: BudgetOptimizationResult | null;
  onClose: () => void;
}

export const PlanningBriefModal: React.FC<PlanningBriefModalProps> = ({
  cityConfig,
  optResult,
  onClose,
}) => {
  const [report, setReport] = useState<PlanningReport | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);
  const { unit, formatTemp, formatDelta } = useTemperature();

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

    generateReport({
      city: cityConfig.city_key,
      budget: optResult?.target_budget || 500000,
      strategy: optResult?.strategy || "balanced",
    })
      .then((rep) => {
        if (isMounted) {
          setReport(rep);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.error("Failed to generate report:", err);
          setError(err.message || "Failed to generate report");
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [cityConfig.city_key, optResult]);

  const handlePrint = () => {
    window.print();
  };

  const handleCopyMarkdown = () => {
    if (!report) return;

    const peakObservedStr =
      unit === "F"
        ? `${report.observed_baseline_summary.observed_peak_max_f}°F (${report.observed_baseline_summary.observed_peak_max_c}°C)`
        : `${report.observed_baseline_summary.observed_peak_max_c}°C (${report.observed_baseline_summary.observed_peak_max_f}°F)`;

    const peakReliefStr =
      unit === "F"
        ? `-${report.modeled_outcomes_summary.portfolio_avg_peak_reduction_f}°F (-${report.modeled_outcomes_summary.portfolio_avg_peak_reduction_c}°C)`
        : `-${report.modeled_outcomes_summary.portfolio_avg_peak_reduction_c}°C (-${report.modeled_outcomes_summary.portfolio_avg_peak_reduction_f}°F)`;

    const md = `
# ${report.title}
**Report ID:** ${report.report_id}  
**Location:** ${report.city}  
**Assessment Period:** ${report.study_period} (FortyGuard 100m Microclimate Grid)  
**Allocated Budget:** ${formatCurrency(report.budget_allocated)} (Planning-level estimate)  

## 1. Executive Summary
${report.executive_summary}

## 2. Baseline FortyGuard Heat Observations
- **Study Area:** ${report.city} (${report.observed_baseline_summary.fortyguard_tiles_count} FortyGuard 100m ambient grid tiles)
- **Peak Observed Temperature:** ${peakObservedStr}
- **Data Provenance:** ${report.observed_baseline_summary.data_provenance}

## 3. Proposed Capital Portfolio
- **Urban Shade Trees:** ${report.proposed_portfolio.total_trees} units (+${report.proposed_portfolio.total_trees * 25} m² direct canopy)
- **Engineered Shade Structures:** ${report.proposed_portfolio.total_shade_structures} units (+${report.proposed_portfolio.total_shade_structures * 100} m² direct shade)
- **Cool Pavement:** ${formatNumber(report.proposed_portfolio.total_cool_pavement_m2)} m² high-albedo coating
- **Target Assets Covered:** ${report.proposed_portfolio.total_assets_covered} municipal locations

## 4. Modeled Outcomes & Thermal Benefits
- **Average Local Peak Reduction:** ${peakReliefStr}
- **Extreme Heat Hours Reduction:** -${report.modeled_outcomes_summary.portfolio_avg_hours_reduction_pct}%
- **Benefited Daily Citizens:** ${formatNumber(report.modeled_outcomes_summary.total_benefited_population)} / day

## 5. Itemized Planning-Level Cost Breakdown
${report.intervention_itemization.map((i) => `- **${i.category}:** ${i.units} @ ${i.unit_rate} = ${i.subtotal}`).join("\n")}

## 6. Assumptions & Limitations
${report.methodology_and_assumptions.map((m) => `- ${m}`).join("\n")}
    `.trim();

    navigator.clipboard.writeText(md).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-2 sm:p-4 lg:p-6 animate-in fade-in duration-150 printable-document-container"
      role="dialog"
      aria-modal="true"
      aria-labelledby="planning-brief-title"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="bg-white border border-slate-300 w-full max-w-4xl max-h-[94vh] sm:max-h-[90vh] rounded-lg shadow-xl flex flex-col overflow-hidden text-slate-900 printable-document-body"
      >
        {/* Modal Header - Hidden when printing */}
        <div className="h-13 sm:h-14 border-b border-slate-200 px-3.5 sm:px-5 flex items-center justify-between flex-shrink-0 bg-slate-50 print:hidden">
          <div className="flex items-center gap-2 min-w-0">
            <FileText className="w-4 h-4 text-slate-700 flex-shrink-0" />
            <h2 id="planning-brief-title" className="text-xs sm:text-sm font-bold text-slate-900 tracking-tight truncate">
              HEAT ADAPTATION PLANNING BRIEF
            </h2>
          </div>

          <div className="flex items-center gap-1.5 sm:gap-2 flex-shrink-0">
            <button
              onClick={handleCopyMarkdown}
              aria-label="Copy markdown summary"
              className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-slate-700 bg-white hover:bg-slate-100 rounded border border-slate-300 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400 min-h-[32px]"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? "Copied" : "Copy"}</span>
            </button>

            <button
              onClick={handlePrint}
              aria-label="Print action brief"
              className="flex items-center gap-1 px-3 py-1 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded transition-colors shadow-xs focus:outline-none focus:ring-2 focus:ring-slate-600 cursor-pointer min-h-[32px]"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>Print</span>
            </button>

            <button
              onClick={onClose}
              aria-label="Close dialog"
              className="w-9 h-9 inline-flex items-center justify-center rounded text-slate-500 hover:text-slate-900 hover:bg-slate-200 focus:outline-none focus:ring-2 focus:ring-slate-400 transition-colors ml-0.5 sm:ml-1 flex-shrink-0"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Document Content - Expanded naturally across multiple pages when printing */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 space-y-5 sm:space-y-6 custom-scrollbar bg-white text-slate-800 font-sans printable-document-content">
          {loading ? (
            <div className="py-12">
              <ProgressStageCard
                title="Generating Heat Mitigation Planning Brief"
                subtitle={`Compiling municipal brief for ${cityConfig.name}, ${cityConfig.state}`}
                stages={[
                  { id: "baseline", label: "Retrieving FortyGuard microclimate baseline observations", status: "completed" },
                  { id: "costs", label: "Itemizing municipal capital intervention unit costs", status: "completed" },
                  { id: "modeling", label: "Modeling localized thermal cooling & user protection", status: "active" },
                  { id: "doc", label: "Compiling municipal policy document & recommendations", status: "pending" },
                ]}
              />
            </div>
          ) : error || !report ? (
            <div className="p-4 rounded bg-red-50 border border-red-200 text-red-700 text-xs">
              {error || "Failed to generate report"}
            </div>
          ) : (
            <div className="max-w-3xl mx-auto space-y-6 print:space-y-5">
              {/* Document Header */}
              <div className="border-b border-slate-300 pb-3 avoid-break">
                <div className="flex items-center justify-between text-xs text-slate-500 mb-1 flex-wrap gap-1">
                  <span>DOCUMENT ID: {report.report_id}</span>
                  <span>{report.generated_at}</span>
                </div>
                <h1 className="text-lg sm:text-xl font-bold text-slate-900 tracking-tight leading-snug">
                  {report.title}
                </h1>
                <p className="text-xs text-slate-600 mt-0.5">
                  Urban Heat Planning • Study Period: {report.study_period}
                </p>
              </div>

              {/* 1. Executive Summary */}
              <section className="space-y-1.5 avoid-break">
                <h2 className="text-xs font-bold uppercase tracking-wider text-slate-900">
                  1. Executive Summary
                </h2>
                <p className="text-xs text-slate-700 leading-relaxed bg-slate-50 p-3.5 rounded border border-slate-200 print:bg-slate-50/50">
                  {report.executive_summary}
                </p>
              </section>

              {/* 2. Key Proposed Outcomes */}
              <section className="space-y-2 avoid-break">
                <h2 className="text-xs font-bold uppercase tracking-wider text-slate-900">
                  2. Proposed Capital Portfolio &amp; Modeled Estimates
                </h2>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
                  <div className="bg-slate-50 border border-slate-200 p-2.5 rounded print:bg-slate-50/50">
                    <span className="text-[10px] text-slate-500 block">Total Investment</span>
                    <span className="text-sm font-bold text-slate-900 font-mono">{formatCurrency(report.budget_allocated)}</span>
                  </div>
                  <div className="bg-slate-50 border border-slate-200 p-2.5 rounded print:bg-slate-50/50">
                    <span className="text-[10px] text-slate-500 block">Planned Interventions</span>
                    <span className="text-xs font-semibold text-slate-800">
                      {report.proposed_portfolio.total_trees} Trees • {report.proposed_portfolio.total_shade_structures} Shade
                    </span>
                  </div>
                  <div className="bg-slate-50 border border-slate-200 p-2.5 rounded print:bg-slate-50/50">
                    <span className="text-[10px] text-slate-500 block">Modeled Peak Relief</span>
                    <span className="text-sm font-bold text-brand-700 font-mono">
                      {formatDelta(report.modeled_outcomes_summary.portfolio_avg_peak_reduction_c)}
                    </span>
                  </div>
                  <div className="bg-slate-50 border border-slate-200 p-2.5 rounded print:bg-slate-50/50">
                    <span className="text-[10px] text-slate-500 block">Estimated Protected Users</span>
                    <span className="text-sm font-bold text-slate-900 font-mono">
                      ~{formatNumber(report.modeled_outcomes_summary.total_benefited_population)} / day
                    </span>
                  </div>
                </div>
              </section>

              {/* 3. Itemized Cooling Interventions */}
              <section className="space-y-1.5 avoid-break">
                <h2 className="text-xs font-bold uppercase tracking-wider text-slate-900">
                  3. Itemized Interventions &amp; Cost Benchmarks
                </h2>

                <div className="border border-slate-200 rounded overflow-x-auto custom-scrollbar">
                  <table className="w-full text-xs text-left border-collapse font-sans min-w-[540px]">
                    <thead className="bg-slate-50 text-slate-700 border-b border-slate-200">
                      <tr>
                        <th className="p-2.5 font-semibold">Category</th>
                        <th className="p-2.5 font-semibold">Quantity / Scope</th>
                        <th className="p-2.5 font-semibold">Unit Benchmark &amp; Source</th>
                        <th className="p-2.5 font-semibold text-right">Subtotal</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 bg-white">
                      {report.intervention_itemization.map((item, idx) => (
                        <tr key={idx} className="avoid-break">
                          <td className="p-2.5 font-medium text-slate-900">
                            <div>{item.category}</div>
                            <span className="text-[10px] text-slate-500">{item.impact_mechanism}</span>
                          </td>
                          <td className="p-2.5 font-semibold text-slate-800">{item.units}</td>
                          <td className="p-2.5 text-slate-600">{item.unit_rate}</td>
                          <td className="p-2.5 text-right font-mono font-medium text-slate-900">{item.subtotal}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              {/* 4. Target Assets Table */}
              <section className="space-y-1.5 avoid-break">
                <h2 className="text-xs font-bold uppercase tracking-wider text-slate-900">
                  4. Priority Assets &amp; Modeled Allocations
                </h2>

                <div className="border border-slate-200 rounded overflow-x-auto custom-scrollbar">
                  <table className="w-full text-xs text-left border-collapse font-sans min-w-[540px]">
                    <thead className="bg-slate-50 text-slate-700 border-b border-slate-200">
                      <tr>
                        <th className="p-2.5 font-semibold">Asset</th>
                        <th className="p-2.5 font-semibold">Peak Observed (FortyGuard)</th>
                        <th className="p-2.5 font-semibold">Allocated Package</th>
                        <th className="p-2.5 font-semibold text-right">Cost</th>
                        <th className="p-2.5 font-semibold text-right">Modeled ΔT (Estimate)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 bg-white">
                      {report.target_assets_table.map((row, idx) => {
                        const peakNum = parseFloat(row.observed_peak_c.replace(/[^\d.-]/g, ""));
                        const deltaNum = Math.abs(parseFloat(row.modeled_peak_reduction.replace(/[^\d.-]/g, "")));
                        const displayPeak = !isNaN(peakNum) ? formatTemp(peakNum) : row.observed_peak_c;
                        const displayDelta = !isNaN(deltaNum) ? formatDelta(deltaNum) : row.modeled_peak_reduction;

                        return (
                          <tr key={idx} className="avoid-break">
                            <td className="p-2.5 font-medium text-slate-900">
                              <div className="truncate max-w-[220px]" title={row.asset_name}>{row.asset_name}</div>
                              <span className="text-[10px] text-slate-500 font-mono">
                                {row.asset_id} • {row.asset_type}
                              </span>
                            </td>
                            <td className="p-2.5 font-mono text-slate-700">{displayPeak}</td>
                            <td className="p-2.5 text-slate-600">{row.interventions_package}</td>
                            <td className="p-2.5 text-right font-mono text-slate-900">{row.allocated_cost}</td>
                            <td className="p-2.5 text-right font-mono font-bold text-brand-700">{displayDelta}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </section>

              {/* 5. Methodology & Assumptions */}
              <section className="space-y-1 avoid-break">
                <h2 className="text-xs font-bold uppercase tracking-wider text-slate-900">
                  5. Scientific Methodology, Assumptions &amp; Limitations
                </h2>
                <ul className="space-y-1 text-xs text-slate-600 list-disc list-inside bg-slate-50 p-3 rounded border border-slate-200 leading-relaxed print:bg-slate-50/50">
                  {report.methodology_and_assumptions.map((item, idx) => (
                    <li key={idx}>{item}</li>
                  ))}
                </ul>
              </section>

              {/* Footer Note */}
              <div className="pt-3 border-t border-slate-200 text-[10px] text-slate-400 flex items-center justify-between avoid-break">
                <span>FortyGuard 100m Microclimate Grid • City of {report.city}</span>
                <span>Thermal Capital Planning System</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

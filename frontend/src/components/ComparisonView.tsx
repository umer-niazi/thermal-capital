import React, { useEffect, useState } from "react";
import { CandidateSiteSummary, ComparisonResponse, RegionType } from "../types";
import { compareSites } from "../services/api";
import { Columns, Info, Loader2, X } from "lucide-react";
import { getRiskColor } from "../utils/formatters";

interface ComparisonViewProps {
  selectedSiteIds: string[];
  sites: CandidateSiteSummary[];
  onClose: () => void;
  onSelectSite: (siteId: string) => void;
  selectedRegion: RegionType;
}

export const ComparisonView: React.FC<ComparisonViewProps> = ({
  selectedSiteIds,
  sites,
  onClose,
  onSelectSite,
  selectedRegion,
}) => {
  const [data, setData] = useState<ComparisonResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

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
    const ids = selectedSiteIds.length >= 2 ? selectedSiteIds : sites.slice(0, 4).map((s) => s.site_id);

    compareSites(ids, selectedRegion)
      .then((res) => {
        if (isMounted) {
          setData(res);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message || "Failed to load comparison");
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [selectedSiteIds, sites, selectedRegion]);

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-2 sm:p-4 lg:p-8"
      role="dialog"
      aria-modal="true"
      aria-labelledby="comparison-title"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="bg-white border border-slate-300 w-full max-w-5xl max-h-[94vh] sm:max-h-[90vh] rounded-lg shadow-xl flex flex-col overflow-hidden text-slate-900 animate-in fade-in zoom-in-95 duration-150"
      >
        {/* Modal Header */}
        <div className="h-13 sm:h-14 border-b border-slate-200 px-4 sm:px-6 flex items-center justify-between flex-shrink-0 bg-slate-50">
          <div className="flex items-center gap-2 sm:gap-2.5 min-w-0">
            <Columns className="w-4 h-4 text-slate-700 flex-shrink-0" />
            <div className="min-w-0">
              <h2 id="comparison-title" className="text-xs sm:text-sm font-bold text-slate-900 tracking-tight truncate">
                Site Thermal Comparison Matrix ({data?.compared_sites.length || selectedSiteIds.length} Sites)
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

        {/* Modal Content */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 sm:space-y-5 custom-scrollbar">
          {loading ? (
            <div className="h-64 flex flex-col items-center justify-center text-slate-500">
              <Loader2 className="w-6 h-6 animate-spin text-slate-600 mb-2" />
              <p className="text-xs">Computing comparative delta across selected sites...</p>
            </div>
          ) : error || !data ? (
            <div className="p-3 rounded bg-red-50 border border-red-200 text-red-700 text-xs">
              {error || "Failed to load comparison data"}
            </div>
          ) : (
            <>
              {/* Matrix Table */}
              <div className="border border-slate-200 rounded overflow-x-auto custom-scrollbar">
                <table className="w-full text-xs text-left border-collapse font-sans min-w-[650px]">
                  <thead>
                    <tr className="bg-slate-50 text-slate-700 border-b border-slate-200">
                      <th className="p-3 font-semibold text-xs text-slate-600 w-1/4 min-w-[180px]">
                        Evaluated Metric
                      </th>
                      {data.compared_sites.map((s) => {
                        const isMeasured = s.data_status === "measured";
                        const risk = getRiskColor(s.risk_category);
                        return (
                          <th key={s.site_id} className="p-3 border-l border-slate-200 min-w-[200px]">
                            <div className="flex items-center justify-between mb-1">
                              <span className="font-semibold text-slate-900">{s.site_name}</span>
                              {s.rank && <span className="text-[10px] text-slate-500">Rank #{s.rank}</span>}
                            </div>
                            <div className="flex flex-wrap items-center gap-2 mb-1">
                              {isMeasured && s.score ? (
                                <span className={`px-1.5 py-0.2 rounded text-[10px] font-medium border ${risk.badge}`}>
                                  {s.score.toFixed(1)} / 100 [{s.risk_category}]
                                </span>
                              ) : (
                                <span className="px-1.5 py-0.2 rounded bg-slate-100 text-slate-600 border border-slate-300 text-[10px]">
                                  REQUIRES ANALYSIS
                                </span>
                              )}
                              <button
                                onClick={() => {
                                  onClose();
                                  onSelectSite(s.site_id);
                                }}
                                className="text-[10px] text-primary-600 hover:text-primary-700 underline ml-auto"
                              >
                                View
                              </button>
                            </div>
                            <div className="text-[10px] text-slate-500 font-normal">
                              {s.city ? `${s.city} • ` : ""}{s.submarket || s.archetype}
                            </div>
                          </th>
                        );
                      })}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 bg-white">
                    {data.metrics_table.map((row) => (
                      <tr key={row.metric_key} className="hover:bg-slate-50">
                        <td className="p-3 font-medium text-slate-700">
                          <div>{row.label}</div>
                          {row.units && (
                            <span className="text-[10px] text-slate-500 font-mono">({row.units})</span>
                          )}
                        </td>
                        {data.compared_sites.map((s) => {
                          const val = row.values[s.site_id];
                          return (
                            <td key={s.site_id} className="p-3 border-l border-slate-100 font-mono font-semibold text-slate-900">
                              {val !== undefined ? String(val) : "—"}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Explanations & Findings */}
              {data.why_ranking_differs.length > 0 && (
                <div className="bg-slate-50 border border-slate-200 p-4 rounded space-y-1.5 text-xs">
                  <div className="flex items-center gap-1.5 font-semibold text-slate-800 mb-1">
                    <Info className="w-3.5 h-3.5 text-slate-600" />
                    <span>Comparative Drivers</span>
                  </div>
                  <ul className="space-y-1 text-slate-600 leading-relaxed list-disc list-inside">
                    {data.why_ranking_differs.map((exp, idx) => (
                      <li key={idx}>{exp}</li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

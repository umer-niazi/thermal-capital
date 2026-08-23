import React from "react";
import { CityConfig, PublicAsset } from "../types";
import {
  formatTempC,
  getRiskColor,
} from "../utils/formatters";
import {
  ChevronRight,
  Layers,
} from "lucide-react";

interface RankingListProps {
  assets: PublicAsset[];
  cityConfig: CityConfig;
  onSelectAsset: (assetId: string) => void;
  onPlanAsset: (assetId: string) => void;
}

export const RankingList: React.FC<RankingListProps> = ({
  assets,
  cityConfig,
  onSelectAsset,
  onPlanAsset,
}) => {
  return (
    <div className="p-4 space-y-4 text-slate-900">
      {/* City Summary Header */}
      <div className="border-b border-slate-200 pb-3">
        <h2 className="text-sm font-semibold text-slate-900 tracking-tight">
          Priority Areas — {cityConfig.name}
        </h2>
        <p className="text-xs text-slate-500 mt-0.5">
          {assets.length} public assets evaluated using 100m FortyGuard observed heat baseline.
        </p>
      </div>

      {/* Compact Priority Areas List */}
      <div
        className="divide-y divide-slate-100 border border-slate-200 rounded bg-white overflow-hidden shadow-xs"
        role="list"
      >
        {assets.map((asset, index) => {
          const obs = asset.observed_heat;
          const risk = getRiskColor(asset.heat_risk_level);

          return (
            <div
              key={asset.asset_id}
              role="button"
              tabIndex={0}
              aria-label={`Select ${asset.name}, ${asset.heat_risk_level} exposure`}
              onClick={() => onSelectAsset(asset.asset_id)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onSelectAsset(asset.asset_id);
                }
              }}
              className="p-3 hover:bg-slate-50 focus:bg-slate-50 focus:outline-none focus:ring-1 focus:ring-slate-400 transition-colors cursor-pointer flex items-center justify-between gap-3 group"
            >
              <div className="flex items-start gap-2.5 min-w-0">
                <span className="text-xs font-semibold text-slate-500 font-mono w-4 pt-0.5">
                  {index + 1}.
                </span>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="text-xs font-semibold text-slate-900 truncate group-hover:text-primary-600 transition-colors">
                      {asset.name}
                    </h3>
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-slate-600 mt-0.5">
                    <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-medium border ${risk.badge}`}>
                      {asset.heat_risk_level} exposure
                    </span>
                    <span>•</span>
                    <span>{obs.hours_above_35c.toFixed(1)} hrs &gt; 35°C</span>
                    <span>•</span>
                    <span className="font-mono">{formatTempC(obs.peak_temperature_c)} peak</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-1.5 flex-shrink-0">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onPlanAsset(asset.asset_id);
                  }}
                  aria-label={`Test cooling interventions on ${asset.name}`}
                  className="px-3 py-1.5 text-xs font-semibold text-brand-700 hover:text-brand-800 bg-brand-50 hover:bg-brand-100 border border-brand-200 rounded transition-colors flex items-center gap-1 focus:outline-none focus:ring-2 focus:ring-brand-500 min-h-[34px]"
                >
                  <Layers className="w-3 h-3 text-brand-600" />
                  <span>Test</span>
                </button>
                <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-slate-600 transition-colors" />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

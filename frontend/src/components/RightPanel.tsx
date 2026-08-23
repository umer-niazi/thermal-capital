import React, { useEffect, useState } from "react";
import {
  AppMode,
  CityConfig,
  PlacedIntervention,
  PlacedInterventionType,
  PublicAsset,
  SimulationResponse,
} from "../types";
import { RankingList } from "./RankingList";
import { SiteDetail } from "./SiteDetail";
import { PlanningWorkspace } from "./PlanningWorkspace";
import {
  ChevronDown,
  ChevronUp,
  ListFilter,
  Loader2,
  MapPin,
  Maximize2,
  Minimize2,
  SlidersHorizontal,
} from "lucide-react";

interface RightPanelProps {
  appMode: AppMode;
  currentCity: CityConfig;
  assets: PublicAsset[];
  selectedAsset: PublicAsset | null;
  onSelectAsset: (assetId: string) => void;
  onBackToRanking: () => void;
  onPlanAsset: (assetId: string) => void;
  onSwitchMode: (mode: AppMode) => void;
  onOpenOptimizer: () => void;
  onOpenReport: () => void;
  onPlanUpdated: (simulation: SimulationResponse | null) => void;
  placedInterventions: PlacedIntervention[];
  onAddIntervention: (item: Omit<PlacedIntervention, "id" | "created_at">) => void;
  onBatchAddInterventions?: (items: Array<Omit<PlacedIntervention, "id" | "created_at">>) => void;
  onRemoveIntervention: (id: string) => void;
  onClearAssetInterventions: (assetId?: string) => void;
  activePlacementTool: PlacedInterventionType | null;
  onSelectPlacementTool: (tool: PlacedInterventionType | null) => void;
  isLoading: boolean;
}

export type MobileSheetState = "collapsed" | "half" | "full";

export const RightPanel: React.FC<RightPanelProps> = ({
  appMode,
  currentCity,
  assets,
  selectedAsset,
  onSelectAsset,
  onBackToRanking,
  onPlanAsset,
  onSwitchMode,
  onOpenOptimizer,
  onOpenReport,
  onPlanUpdated,
  placedInterventions,
  onAddIntervention,
  onBatchAddInterventions,
  onRemoveIntervention,
  onClearAssetInterventions,
  activePlacementTool,
  onSelectPlacementTool,
  isLoading,
}) => {
  const [sheetState, setSheetState] = useState<MobileSheetState>("half");

  // Auto-expand sheet when an asset is selected or mode changes
  useEffect(() => {
    if (selectedAsset && sheetState === "collapsed") {
      setSheetState("half");
    }
  }, [selectedAsset?.asset_id]);

  useEffect(() => {
    if (appMode === "plan" && sheetState === "collapsed") {
      setSheetState("half");
    }
  }, [appMode]);

  const sheetHeightClass =
    sheetState === "collapsed"
      ? "h-[58px] sm:h-[64px]"
      : sheetState === "half"
      ? "h-[50vh] sm:h-[52vh]"
      : "h-[88vh] sm:h-[85vh]";

  return (
    <aside
      aria-label="Planning and Area Details Panel"
      className={`w-full lg:w-[380px] xl:w-[420px] flex-shrink-0 bg-slate-50 border-slate-200 flex flex-col z-30 lg:z-10 overflow-hidden transition-all duration-300 ease-in-out ${sheetHeightClass} lg:h-full absolute lg:static bottom-0 left-0 right-0 border-t lg:border-t-0 lg:border-l rounded-t-xl lg:rounded-none shadow-2xl lg:shadow-none`}
    >
      {/* Mobile Bottom Sheet Drag Handle & Summary Bar (Visible only on < 1024px) */}
      <div
        onClick={() => {
          if (sheetState === "collapsed") setSheetState("half");
        }}
        className="lg:hidden flex flex-col bg-slate-100/95 border-b border-slate-200 select-none cursor-pointer flex-shrink-0"
      >
        {/* Subtle Pill Handle */}
        <div className="w-10 h-1 bg-slate-300 rounded-full mx-auto mt-2 mb-1" />

        {/* Mobile Header Bar */}
        <div className="h-10 px-3.5 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            {appMode === "plan" ? (
              <div className="flex items-center gap-1.5 text-xs font-bold text-slate-900 truncate">
                <SlidersHorizontal className="w-3.5 h-3.5 text-brand-600 flex-shrink-0" />
                <span className="truncate">
                  {selectedAsset ? selectedAsset.name : "Intervention Planning"}
                </span>
                {placedInterventions.length > 0 && (
                  <span className="text-[10px] px-1.5 py-0.2 rounded bg-brand-100 text-brand-800 font-semibold border border-brand-200 flex-shrink-0">
                    {placedInterventions.length} placed
                  </span>
                )}
              </div>
            ) : selectedAsset ? (
              <div className="flex items-center gap-1.5 text-xs font-bold text-slate-900 truncate">
                <MapPin className="w-3.5 h-3.5 text-brand-600 flex-shrink-0" />
                <span className="truncate">{selectedAsset.name}</span>
                <span className="text-[10px] text-slate-500 font-mono flex-shrink-0">
                  {selectedAsset.asset_id}
                </span>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 text-xs font-bold text-slate-900 truncate">
                <ListFilter className="w-3.5 h-3.5 text-slate-700 flex-shrink-0" />
                <span>Priority Areas — {currentCity.name}</span>
                <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-200 text-slate-700 font-semibold flex-shrink-0">
                  {assets.length}
                </span>
              </div>
            )}
          </div>

          {/* Mobile Sheet State Controls */}
          <div className="flex items-center gap-1 flex-shrink-0">
            {sheetState === "collapsed" ? (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setSheetState("half");
                }}
                aria-label="Expand panel"
                className="p-1.5 text-slate-600 hover:text-slate-900 rounded hover:bg-slate-200 transition-colors flex items-center gap-1 text-xs font-medium"
              >
                <span>Expand</span>
                <ChevronUp className="w-4 h-4" />
              </button>
            ) : (
              <>
                {sheetState === "half" ? (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setSheetState("full");
                    }}
                    aria-label="Maximize panel to full screen"
                    title="Maximize to full screen"
                    className="p-1.5 text-slate-600 hover:text-slate-900 rounded hover:bg-slate-200 transition-colors"
                  >
                    <Maximize2 className="w-3.5 h-3.5" />
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setSheetState("half");
                    }}
                    aria-label="Resize panel to half screen"
                    title="Resize to half screen"
                    className="p-1.5 text-slate-600 hover:text-slate-900 rounded hover:bg-slate-200 transition-colors"
                  >
                    <Minimize2 className="w-3.5 h-3.5" />
                  </button>
                )}

                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setSheetState("collapsed");
                  }}
                  aria-label="Minimize panel to peek bar"
                  title="Minimize panel"
                  className="p-1.5 text-slate-600 hover:text-slate-900 rounded hover:bg-slate-200 transition-colors"
                >
                  <ChevronDown className="w-4 h-4" />
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Main Scrollable Panel Content (Rankings, Detail, Planning Workspace) */}
      <div
        className={`flex-1 overflow-y-auto custom-scrollbar ${
          sheetState === "collapsed" ? "hidden lg:block" : "block"
        }`}
      >
        {isLoading ? (
          <div className="h-full flex flex-col items-center justify-center p-8 text-center text-slate-500">
            <Loader2 className="w-6 h-6 animate-spin text-slate-600 mb-2" />
            <p className="text-xs font-medium text-slate-700">Loading {currentCity.name} heat data...</p>
          </div>
        ) : appMode === "plan" ? (
          <PlanningWorkspace
            asset={selectedAsset || (assets.length > 0 ? assets[0] : null)}
            allAssets={assets}
            cityConfig={currentCity}
            onSelectAsset={onSelectAsset}
            onOpenOptimizer={onOpenOptimizer}
            onOpenReport={onOpenReport}
            onSwitchMode={onSwitchMode}
            onPlanUpdated={onPlanUpdated}
            placedInterventions={placedInterventions}
            onAddIntervention={onAddIntervention}
            onBatchAddInterventions={onBatchAddInterventions}
            onRemoveIntervention={onRemoveIntervention}
            onClearAssetInterventions={onClearAssetInterventions}
            activePlacementTool={activePlacementTool}
            onSelectPlacementTool={onSelectPlacementTool}
          />
        ) : selectedAsset ? (
          <SiteDetail
            asset={selectedAsset}
            onBack={onBackToRanking}
            onPlanIntervention={() => {
              onPlanAsset(selectedAsset.asset_id);
            }}
          />
        ) : (
          <RankingList
            assets={assets}
            cityConfig={currentCity}
            onSelectAsset={onSelectAsset}
            onPlanAsset={onPlanAsset}
          />
        )}
      </div>
    </aside>
  );
};

import React from "react";
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
import { Loader2 } from "lucide-react";

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
  onRemoveIntervention: (id: string) => void;
  onClearAssetInterventions: (assetId?: string) => void;
  activePlacementTool: PlacedInterventionType | null;
  onSelectPlacementTool: (tool: PlacedInterventionType | null) => void;
  isLoading: boolean;
}

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
  onRemoveIntervention,
  onClearAssetInterventions,
  activePlacementTool,
  onSelectPlacementTool,
  isLoading,
}) => {
  return (
    <aside
      aria-label="Planning and Area Details Panel"
      className="w-full lg:w-[380px] xl:w-[420px] flex-shrink-0 h-[45vh] lg:h-full bg-slate-50 border-t lg:border-t-0 lg:border-l border-slate-200 flex flex-col z-10 overflow-hidden"
    >
      <div className="flex-1 overflow-y-auto custom-scrollbar">
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

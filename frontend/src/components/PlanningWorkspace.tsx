import React, { useEffect, useState } from "react";
import {
  AppMode,
  CityConfig,
  PlacedIntervention,
  PlacedInterventionType,
  PublicAsset,
  SimulationResponse,
} from "../types";
import { DEFAULT_INTERVENTION_COSTS, simulateInterventions } from "../services/api";
import {
  formatCurrency,
  formatNumber,
  getAssetTypeLabel,
  getRiskColor,
} from "../utils/formatters";
import { useTemperature } from "../context/TemperatureContext";
import { generateOffsetCoordinate } from "../utils/geoUtils";
import {
  ArrowLeft,
  BookOpen,
  ChevronDown,
  ChevronUp,
  Crosshair,
  FileText,
  HelpCircle,
  Info,
  Minus,
  Plus,
  RotateCcw,
  SlidersHorizontal,
  Sun,
  Trash2,
  Trees,
  Umbrella,
  X,
} from "lucide-react";

interface PlanningWorkspaceProps {
  asset: PublicAsset | null;
  allAssets: PublicAsset[];
  cityConfig: CityConfig;
  onSelectAsset: (assetId: string) => void;
  onOpenOptimizer: () => void;
  onOpenReport: () => void;
  onSwitchMode: (mode: AppMode) => void;
  placedInterventions: PlacedIntervention[];
  onAddIntervention: (item: Omit<PlacedIntervention, "id" | "created_at">) => void;
  onBatchAddInterventions?: (items: Array<Omit<PlacedIntervention, "id" | "created_at">>) => void;
  onRemoveIntervention: (id: string) => void;
  onClearAssetInterventions: (assetId?: string) => void;
  activePlacementTool: PlacedInterventionType | null;
  onSelectPlacementTool: (tool: PlacedInterventionType | null) => void;
  onPlanUpdated?: (simulation: SimulationResponse | null) => void;
}

export const PlanningWorkspace: React.FC<PlanningWorkspaceProps> = ({
  asset,
  allAssets,
  cityConfig,
  onSelectAsset,
  onOpenOptimizer,
  onOpenReport,
  onSwitchMode,
  placedInterventions,
  onAddIntervention,
  onBatchAddInterventions,
  onRemoveIntervention,
  onClearAssetInterventions,
  activePlacementTool,
  onSelectPlacementTool,
  onPlanUpdated,
}) => {
  const [simulation, setSimulation] = useState<SimulationResponse | null>(null);
  const [showAssumptions, setShowAssumptions] = useState<boolean>(false);
  const [showBaselineRationale, setShowBaselineRationale] = useState<boolean>(false);
  const [showMethodologyModal, setShowMethodologyModal] = useState<boolean>(false);
  const { unit, formatTemp, formatDelta } = useTemperature();

  const treeCost = DEFAULT_INTERVENTION_COSTS.tree_canopy.planning_unit_cost;
  const shadeCost = DEFAULT_INTERVENTION_COSTS.shade_structure.planning_unit_cost;
  const paveCost = DEFAULT_INTERVENTION_COSTS.cool_pavement.planning_unit_cost;

  // Filter interventions for the current asset (or all if asset not specific)
  const currentAssetInterventions = asset
    ? placedInterventions.filter((i) => i.asset_id === asset.asset_id || !i.asset_id)
    : placedInterventions;

  const treesCount = currentAssetInterventions.filter((i) => i.type === "tree").length;
  const shadeCount = currentAssetInterventions.filter((i) => i.type === "shade").length;
  const coolPaveM2 = currentAssetInterventions
    .filter((i) => i.type === "reflective")
    .reduce((sum, i) => sum + (i.area_m2 || 200), 0);

  // Initialize with sensible starter visual interventions if none exist for this asset
  useEffect(() => {
    if (!asset) {
      if (allAssets.length > 0) {
        onSelectAsset(allAssets[0].asset_id);
      }
      return;
    }

    const existingForAsset = placedInterventions.filter((i) => i.asset_id === asset.asset_id);
    if (existingForAsset.length === 0) {
      const center: [number, number] = [asset.longitude, asset.latitude];
      const initialTrees = asset.asset_type === "playground" ? 6 : 4;
      const starterItems: Array<Omit<PlacedIntervention, "id" | "created_at">> = [];

      // Add starter trees around asset
      for (let idx = 0; idx < initialTrees; idx++) {
        const [lng, lat] = generateOffsetCoordinate(center, idx, initialTrees, 25);
        starterItems.push({
          type: "tree",
          latitude: lat,
          longitude: lng,
          asset_id: asset.asset_id,
          label: `Tree #${idx + 1}`,
        });
      }

      // Add starter shade structure
      const [shadeLng, shadeLat] = generateOffsetCoordinate(center, 1, 4, 15);
      starterItems.push({
        type: "shade",
        latitude: shadeLat,
        longitude: shadeLng,
        asset_id: asset.asset_id,
        label: "Shade Structure #1",
      });

      // Add starter cool pavement
      const [paveLng, paveLat] = generateOffsetCoordinate(center, 3, 4, 20);
      starterItems.push({
        type: "reflective",
        latitude: paveLat,
        longitude: paveLng,
        asset_id: asset.asset_id,
        area_m2: Math.min(300, Math.round(asset.footprint_m2 * 0.25)),
        label: "Reflective Surface #1",
      });

      if (onBatchAddInterventions) {
        onBatchAddInterventions(starterItems);
      } else {
        starterItems.forEach((item) => onAddIntervention(item));
      }
    }
  }, [asset?.asset_id]);

  // Run simulation whenever quantities or asset change (debounced 50ms to prevent slider thrashing)
  useEffect(() => {
    if (!asset) return;

    let isMounted = true;
    const timerId = setTimeout(() => {
      simulateInterventions({
        asset_id: asset.asset_id,
        city: cityConfig.city_key,
        footprint_m2: asset.footprint_m2,
        baseline_observed: asset.observed_heat,
        trees_count: treesCount,
        shade_structures_count: shadeCount,
        cool_pavement_m2: coolPaveM2,
        cool_roof_m2: 0,
        daily_visitors: asset.daily_visitors,
      })
        .then((res) => {
          if (isMounted) {
            setSimulation(res);
            if (onPlanUpdated) {
              onPlanUpdated(res);
            }
          }
        })
        .catch((err) => {
          console.error("Simulation failed:", err);
        });
    }, 50);

    return () => {
      isMounted = false;
      clearTimeout(timerId);
    };
  }, [asset?.asset_id, treesCount, shadeCount, coolPaveM2, cityConfig.city_key]);

  if (!asset) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-6 text-center text-slate-500 text-xs">
        <SlidersHorizontal className="w-8 h-8 text-slate-400 mb-2" />
        <p className="font-semibold text-slate-700 mb-1">Select an Asset to Plan Interventions</p>
        <p className="text-slate-400 max-w-xs">
          Click any public site on the map or choose from the risk rankings list to model localized cooling.
        </p>
      </div>
    );
  }

  const obs = asset.observed_heat;
  const riskCurrent = getRiskColor(asset.heat_risk_level);
  const imp = simulation?.modeled_impact;

  // Compute post-intervention exposure category based on modeled reduction
  const scenarioPeakC = imp?.peak_temp_after_c ?? obs.peak_temperature_c;
  let scenarioExposure = asset.heat_risk_level;
  if (scenarioPeakC < 33.0) scenarioExposure = "Low" as any;
  else if (scenarioPeakC < 36.0) scenarioExposure = "Moderate" as any;
  else if (scenarioPeakC < 39.0) scenarioExposure = "High" as any;
  else if (scenarioPeakC < 41.5) scenarioExposure = "Critical" as any;
  else scenarioExposure = "Extreme" as any;
  const riskScenario = getRiskColor(scenarioExposure);

  const handleStepTrees = (increment: boolean) => {
    if (increment) {
      const center: [number, number] = [asset.longitude, asset.latitude];
      const [lng, lat] = generateOffsetCoordinate(center, treesCount, treesCount + 1, 20 + treesCount * 3);
      onAddIntervention({
        type: "tree",
        latitude: lat,
        longitude: lng,
        asset_id: asset.asset_id,
        label: `Tree #${treesCount + 1}`,
      });
    } else if (treesCount > 0) {
      const lastTree = [...currentAssetInterventions].reverse().find((i) => i.type === "tree");
      if (lastTree) onRemoveIntervention(lastTree.id);
    }
  };

  const handleStepShade = (increment: boolean) => {
    if (increment) {
      const center: [number, number] = [asset.longitude, asset.latitude];
      const [lng, lat] = generateOffsetCoordinate(center, shadeCount + 1, shadeCount + 2, 12 + shadeCount * 8);
      onAddIntervention({
        type: "shade",
        latitude: lat,
        longitude: lng,
        asset_id: asset.asset_id,
        label: `Shade Structure #${shadeCount + 1}`,
      });
    } else if (shadeCount > 0) {
      const lastShade = [...currentAssetInterventions].reverse().find((i) => i.type === "shade");
      if (lastShade) onRemoveIntervention(lastShade.id);
    }
  };

  const handleStepReflective = (increment: boolean) => {
    const stepSize = 100;
    if (increment) {
      const count = currentAssetInterventions.filter((i) => i.type === "reflective").length;
      const center: [number, number] = [asset.longitude, asset.latitude];
      const [lng, lat] = generateOffsetCoordinate(center, 2 + count, 3 + count, 15 + count * 5);
      onAddIntervention({
        type: "reflective",
        latitude: lat,
        longitude: lng,
        asset_id: asset.asset_id,
        area_m2: stepSize,
        label: `Reflective Surface #${count + 1}`,
      });
    } else if (coolPaveM2 > 0) {
      const lastPave = [...currentAssetInterventions].reverse().find((i) => i.type === "reflective");
      if (lastPave) onRemoveIntervention(lastPave.id);
    }
  };

  // Helper to generate clean readable names for placed items
  let treeSeq = 0;
  let shadeSeq = 0;
  let paveSeq = 0;

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4 text-slate-800 custom-scrollbar">
      {/* Target Asset Banner */}
      <div className="bg-white border border-slate-200 rounded p-3 space-y-2">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 flex-shrink-0">
            <button
              onClick={() => onSwitchMode("explore")}
              title="Return to exploration view"
              aria-label="Return to exploration view"
              className="h-8 px-2.5 text-slate-700 hover:text-slate-900 rounded bg-slate-100 hover:bg-slate-200 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400 flex items-center gap-1 text-xs font-medium flex-shrink-0 min-h-[32px]"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Explore</span>
            </button>
            <span
              className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider flex-shrink-0"
              title="Planning Target"
            >
              PLANNING TARGET
            </span>
          </div>

          <div className="flex items-center gap-1 min-w-0 flex-1 justify-end">
            <select
              aria-label="Select target asset"
              value={asset.asset_id}
              onChange={(e) => onSelectAsset(e.target.value)}
              className="text-xs bg-slate-50 border border-slate-300 rounded px-2 py-1 font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-brand-500 w-full max-w-[130px] sm:max-w-[160px] truncate cursor-pointer"
            >
              {allAssets.map((a) => (
                <option key={a.asset_id} value={a.asset_id}>
                  {a.name} ({a.asset_id})
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <h2
            className="text-sm font-bold text-slate-900 tracking-tight leading-snug truncate"
            title={asset.name}
          >
            {asset.name}
          </h2>
          <div className="flex items-center gap-2 text-[11px] text-slate-500 mt-0.5 flex-wrap">
            <span className="font-mono text-slate-600 font-medium">{asset.asset_id}</span>
            <span>•</span>
            <span>{getAssetTypeLabel(asset.asset_type)}</span>
            <span>•</span>
            <span>{asset.footprint_m2.toFixed(0)} m²</span>
            <span>•</span>
            <span>~{formatNumber(asset.daily_visitors)} users/day</span>
          </div>
        </div>
      </div>

      {/* Intervention Levers / Steppers */}
      <div className="space-y-2.5">
        <div className="flex items-center justify-between text-xs font-semibold text-slate-800">
          <span>Add Cooling Interventions</span>
          {currentAssetInterventions.length > 0 && (
            <button
              onClick={() => onClearAssetInterventions(asset.asset_id)}
              aria-label="Reset interventions for this area"
              className="text-xs font-normal text-slate-500 hover:text-slate-800 flex items-center gap-1 px-2 py-1 rounded hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400 min-h-[28px]"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Reset</span>
            </button>
          )}
        </div>

        {/* 1. Tree Canopy */}
        <div className="bg-white border border-slate-200 p-2.5 rounded flex items-center justify-between gap-2.5 text-xs">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded bg-emerald-50 border border-emerald-200 flex items-center justify-center flex-shrink-0">
              <Trees className="w-4 h-4 text-emerald-600" />
            </div>
            <div className="min-w-0">
              <div className="font-semibold text-slate-900 flex items-center gap-1.5 flex-wrap">
                <span>Street Tree Planting</span>
                <button
                  onClick={() => onSelectPlacementTool(activePlacementTool === "tree" ? null : "tree")}
                  title="Click to place tree directly on map"
                  className={`px-2 py-0.5 rounded text-[10px] font-medium border flex items-center gap-1 transition-colors min-h-[26px] ${
                    activePlacementTool === "tree"
                      ? "bg-slate-900 text-white border-slate-900"
                      : "bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-300"
                  }`}
                >
                  <Crosshair className="w-2.5 h-2.5" />
                  <span>{activePlacementTool === "tree" ? "Placing..." : "Click to Place"}</span>
                </button>
              </div>
              <div className="text-[11px] text-slate-500 mt-0.5">
                ${formatNumber(treeCost)} / tree • +25 m² canopy
              </div>
            </div>
          </div>

          <div className="flex items-center gap-1.5 sm:gap-2 flex-shrink-0">
            <button
              onClick={() => handleStepTrees(false)}
              disabled={treesCount <= 0}
              aria-label="Decrease tree count"
              className="w-9 h-9 sm:w-8 sm:h-8 rounded border border-slate-300 flex items-center justify-center text-slate-700 hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-slate-400 transition-colors"
            >
              <Minus className="w-3.5 h-3.5" />
            </button>
            <span className="font-mono font-bold text-xs w-6 sm:w-7 text-center">{treesCount}</span>
            <button
              onClick={() => handleStepTrees(true)}
              aria-label="Increase tree count"
              className="w-9 h-9 sm:w-8 sm:h-8 rounded border border-slate-300 flex items-center justify-center text-slate-700 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400 transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* 2. Shade Structure */}
        <div className="bg-white border border-slate-200 p-2.5 rounded flex items-center justify-between gap-2.5 text-xs">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded bg-sky-50 border border-sky-200 flex items-center justify-center flex-shrink-0">
              <Umbrella className="w-4 h-4 text-sky-600" />
            </div>
            <div className="min-w-0">
              <div className="font-semibold text-slate-900 flex items-center gap-1.5 flex-wrap">
                <span>Engineered Shade Structure</span>
                <button
                  onClick={() => onSelectPlacementTool(activePlacementTool === "shade" ? null : "shade")}
                  title="Click to place shade structure on map"
                  className={`px-2 py-0.5 rounded text-[10px] font-medium border flex items-center gap-1 transition-colors min-h-[26px] ${
                    activePlacementTool === "shade"
                      ? "bg-slate-900 text-white border-slate-900"
                      : "bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-300"
                  }`}
                >
                  <Crosshair className="w-2.5 h-2.5" />
                  <span>{activePlacementTool === "shade" ? "Placing..." : "Click to Place"}</span>
                </button>
              </div>
              <div className="text-[11px] text-slate-500 mt-0.5">
                ${formatNumber(shadeCost)} / structure • +100 m² shade
              </div>
            </div>
          </div>

          <div className="flex items-center gap-1.5 sm:gap-2 flex-shrink-0">
            <button
              onClick={() => handleStepShade(false)}
              disabled={shadeCount <= 0}
              aria-label="Decrease shade structure count"
              className="w-9 h-9 sm:w-8 sm:h-8 rounded border border-slate-300 flex items-center justify-center text-slate-700 hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-slate-400 transition-colors"
            >
              <Minus className="w-3.5 h-3.5" />
            </button>
            <span className="font-mono font-bold text-xs w-6 sm:w-7 text-center">{shadeCount}</span>
            <button
              onClick={() => handleStepShade(true)}
              aria-label="Increase shade structure count"
              className="w-9 h-9 sm:w-8 sm:h-8 rounded border border-slate-300 flex items-center justify-center text-slate-700 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400 transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* 3. Reflective Pavement */}
        <div className="bg-white border border-slate-200 p-2.5 rounded flex items-center justify-between gap-2.5 text-xs">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded bg-amber-50 border border-amber-200 flex items-center justify-center flex-shrink-0">
              <Sun className="w-4 h-4 text-amber-600" />
            </div>
            <div className="min-w-0">
              <div className="font-semibold text-slate-900 flex items-center gap-1.5 flex-wrap">
                <span>Reflective Cool Pavement</span>
                <button
                  onClick={() => onSelectPlacementTool(activePlacementTool === "reflective" ? null : "reflective")}
                  title="Click to place reflective surface footprint on map"
                  className={`px-2 py-0.5 rounded text-[10px] font-medium border flex items-center gap-1 transition-colors min-h-[26px] ${
                    activePlacementTool === "reflective"
                      ? "bg-slate-900 text-white border-slate-900"
                      : "bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-300"
                  }`}
                >
                  <Crosshair className="w-2.5 h-2.5" />
                  <span>{activePlacementTool === "reflective" ? "Placing..." : "Click to Place"}</span>
                </button>
              </div>
              <div className="text-[11px] text-slate-500 mt-0.5">
                ${paveCost} / m² coating • Albedo ≥ 0.35
              </div>
            </div>
          </div>

          <div className="flex items-center gap-1.5 sm:gap-2 flex-shrink-0">
            <button
              onClick={() => handleStepReflective(false)}
              disabled={coolPaveM2 <= 0}
              aria-label="Decrease reflective surface"
              className="w-9 h-9 sm:w-8 sm:h-8 rounded border border-slate-300 flex items-center justify-center text-slate-700 hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-slate-400 transition-colors"
            >
              <Minus className="w-3.5 h-3.5" />
            </button>
            <span className="font-mono font-bold text-xs w-11 sm:w-12 text-center">{coolPaveM2} m²</span>
            <button
              onClick={() => handleStepReflective(true)}
              aria-label="Increase reflective surface"
              className="w-9 h-9 sm:w-8 sm:h-8 rounded border border-slate-300 flex items-center justify-center text-slate-700 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400 transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Planning Cost Assumptions & Sources Collapsible */}
      <div className="border border-slate-200 rounded bg-white text-xs overflow-hidden">
        <button
          type="button"
          onClick={() => setShowAssumptions(!showAssumptions)}
          className="w-full px-3 py-2 flex items-center justify-between text-slate-700 hover:bg-slate-50 font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400"
          aria-expanded={showAssumptions}
        >
          <div className="flex items-center gap-1.5">
            <Info className="w-3.5 h-3.5 text-slate-500" />
            <span>Planning Cost Assumptions &amp; Sources</span>
          </div>
          {showAssumptions ? <ChevronUp className="w-3.5 h-3.5 text-slate-500" /> : <ChevronDown className="w-3.5 h-3.5 text-slate-500" />}
        </button>

        {showAssumptions && (
          <div className="p-3 border-t border-slate-200 space-y-2.5 bg-slate-50/50 text-[11px] text-slate-600">
            <div className="border-b border-slate-200/80 pb-2">
              <div className="flex items-center justify-between font-semibold text-slate-900">
                <span>Street Tree Planting</span>
                <span className="font-mono text-slate-900 font-bold">$3,200 / tree</span>
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5">
                <strong>Range:</strong> $1,900 – $4,500 / tree • <strong>Source:</strong> NYC Dept. of Parks &amp; Recreation (FY2024 Street Tree Contracts)
              </div>
              <p className="text-[10px] text-slate-600 mt-0.5 leading-snug">
                Includes 2.5–3" caliper urban tree stock, utility clearance, sidewalk concrete cutting, tree pit excavation, structural soil, tree guard, and 2-year establishment warranty.
              </p>
            </div>

            <div className="border-b border-slate-200/80 pb-2">
              <div className="flex items-center justify-between font-semibold text-slate-900">
                <span>Engineered Shade Structure</span>
                <span className="font-mono text-slate-900 font-bold">$28,000 / structure</span>
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5">
                <strong>Range:</strong> $18,000 – $45,000 / unit • <strong>Source:</strong> U.S. Federal Transit Administration (FTA) &amp; Municipal Park Benchmarks
              </div>
              <p className="text-[10px] text-slate-600 mt-0.5 leading-snug">
                Includes commercial ~400–600 sq ft engineered steel cantilever frame, UV-blocking HDPE shade canopy (90%+ UV block), reinforced concrete footings, and ADA compliance.
              </p>
            </div>

            <div>
              <div className="flex items-center justify-between font-semibold text-slate-900">
                <span>Reflective Cool Pavement Coating</span>
                <span className="font-mono text-slate-900 font-bold">$24 / m²</span>
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5">
                <strong>Range:</strong> $14 – $38 / m² • <strong>Source:</strong> U.S. EPA Heat Island Reduction Program &amp; Phoenix Cool Pavement Study
              </div>
              <p className="text-[10px] text-slate-600 mt-0.5 leading-snug">
                Includes surface sweeping, asphalt crack prep, two coats of high-albedo solar-reflective coating (solar reflectance ≥ 0.35), traffic control, and application.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Placed Objects Matrix (Human-Readable Identifiers) */}
      {currentAssetInterventions.length > 0 && (
        <div className="bg-white border border-slate-200 rounded p-2.5 space-y-1.5 text-xs">
          <div className="flex items-center justify-between text-slate-800 font-semibold border-b border-slate-100 pb-1">
            <span>Proposed Interventions · {currentAssetInterventions.length} at this site</span>
            <span className="text-[11px] text-slate-500 font-normal">Click to manage</span>
          </div>

          <div className="max-h-32 overflow-y-auto space-y-1 custom-scrollbar">
            {currentAssetInterventions.map((item) => {
              let displayLabel = item.label;
              if (item.type === "tree") {
                treeSeq += 1;
                displayLabel = `Tree #${treeSeq}`;
              } else if (item.type === "shade") {
                shadeSeq += 1;
                displayLabel = `Shade Structure #${shadeSeq}`;
              } else {
                paveSeq += 1;
                displayLabel = `Reflective Surface #${paveSeq}`;
              }

              return (
                <div
                  key={item.id}
                  className="flex items-center justify-between py-1 px-2 rounded hover:bg-slate-50 text-xs text-slate-700 border border-transparent hover:border-slate-200 transition-colors"
                  title={`Placed at [${item.latitude.toFixed(4)}, ${item.longitude.toFixed(4)}]`}
                >
                  <div className="flex items-center gap-2 truncate">
                    {item.type === "tree" ? (
                      <Trees className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" />
                    ) : item.type === "shade" ? (
                      <Umbrella className="w-3.5 h-3.5 text-sky-600 flex-shrink-0" />
                    ) : (
                      <Sun className="w-3.5 h-3.5 text-amber-600 flex-shrink-0" />
                    )}
                    <span className="font-medium text-slate-900 truncate">
                      {displayLabel}
                    </span>
                    <span className="text-[11px] text-slate-500">
                      {item.type === "tree"
                        ? "+25 m² canopy"
                        : item.type === "shade"
                        ? "+100 m² shade"
                        : `${item.area_m2 || 200} m²`}
                    </span>
                  </div>

                  <button
                    onClick={() => onRemoveIntervention(item.id)}
                    aria-label={`Remove ${displayLabel}`}
                    title="Remove this intervention"
                    className="p-1 text-slate-400 hover:text-red-600 rounded hover:bg-red-50 transition-colors ml-1 flex-shrink-0"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Scenario Comparison & Transparent Cost Breakdown */}
      {imp && simulation && (
        <div className="bg-white border border-slate-200 rounded p-3.5 space-y-3 shadow-xs">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2">
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-semibold text-slate-900">
                Scenario Comparison &amp; Outcomes
              </span>
              <button
                type="button"
                onClick={() => setShowMethodologyModal(true)}
                title="Explain calculation methodology and assumptions"
                aria-label="How is this estimated?"
                className="inline-flex items-center gap-1 text-[11px] text-brand-700 hover:text-brand-900 font-medium hover:underline bg-brand-50 hover:bg-brand-100 px-1.5 py-0.5 rounded transition-colors"
              >
                <HelpCircle className="w-3 h-3 text-brand-600" />
                <span>How is this estimated?</span>
              </button>
            </div>
            <span className="text-[10px] font-medium text-slate-600 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
              Modeled Planning Scenario
            </span>
          </div>

          {/* Side by side BASELINE vs MODELED SCENARIO */}
          <div className="grid grid-cols-2 gap-2.5 text-xs">
            {/* BASELINE */}
            <div className="bg-slate-50 border border-slate-200 p-2.5 rounded space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                  BASELINE (FORTYGUARD)
                </span>
                <span className="text-[9px] font-medium text-slate-600 bg-slate-200/80 px-1 py-0.2 rounded">
                  Observed
                </span>
              </div>
              <div className="font-mono text-sm font-bold text-slate-900">
                {formatTemp(imp.peak_temp_before_c)}
              </div>
              <div className="text-xs text-slate-600">
                Exposure: <strong className={riskCurrent.text}>{asset.heat_risk_level}</strong>
              </div>
              <div className="text-[11px] text-slate-500">
                {imp.hours_35c_before.toFixed(1)} h &gt; {unit === "F" ? "95°F" : "35°C"} observed
              </div>
            </div>

            {/* MODELED SCENARIO */}
            <div className="bg-brand-50/50 border border-brand-200 p-2.5 rounded space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-brand-800 uppercase tracking-wider block">
                  PROPOSED SCENARIO
                </span>
                <span className="text-[9px] font-medium text-brand-800 bg-brand-100 px-1 py-0.2 rounded border border-brand-200">
                  Modeled Estimate
                </span>
              </div>
              <div className="flex items-baseline justify-between gap-1">
                <div className="font-mono text-sm font-bold text-brand-900">
                  {formatTemp(imp.peak_temp_after_c)}
                </div>
                {imp.peak_reduction_c > 0 && (
                  <span className="text-xs font-bold text-brand-800 bg-brand-100 px-1.5 py-0.2 rounded border border-brand-200">
                    ↓ {formatDelta(imp.peak_reduction_c, 1, "")}
                  </span>
                )}
              </div>
              <div className="text-xs text-slate-600">
                Exposure: <strong className={riskScenario.text}>{scenarioExposure}</strong>
              </div>
              <div className="text-[11px] text-slate-500">
                {imp.hours_35c_after.toFixed(1)} h (-{imp.hours_35c_reduction_pct.toFixed(0)}% modeled)
              </div>
            </div>
          </div>

          {/* Land Cover Scenario Comparison */}
          <div className="bg-slate-50 border border-slate-200 rounded p-2.5 space-y-1.5 text-xs">
            <span className="text-xs font-semibold text-slate-800 block">Land Cover Transition (Modeled)</span>
            <div className="grid grid-cols-2 gap-2 text-[11px] pt-0.5">
              <div className="space-y-0.5">
                <span className="text-slate-500 block">Tree Canopy:</span>
                <span className="text-slate-700">
                  <strong className="text-slate-900 font-mono">{obs.canopy_pct.toFixed(0)}%</strong>
                  {" → "}
                  <strong className="text-emerald-700 font-mono">
                    {imp.tree_canopy_pct_after.toFixed(0)}%
                  </strong>
                  {" "}
                  <span className="text-emerald-600 font-medium">(+{imp.canopy_increase_pct.toFixed(0)}%)</span>
                </span>
              </div>
              <div className="space-y-0.5">
                <span className="text-slate-500 block">Impervious Surface:</span>
                <span className="text-slate-700">
                  <strong className="text-slate-900 font-mono">{obs.impervious_pct.toFixed(0)}%</strong>
                  {" → "}
                  <strong className="text-slate-900 font-mono">
                    {imp.impervious_pct_after.toFixed(0)}%
                  </strong>
                </span>
              </div>
            </div>
          </div>

          {/* Transparent Cost Arithmetic Breakdown */}
          <div className="bg-slate-50 border border-slate-200 rounded p-2.5 space-y-1.5 text-xs">
            <div className="flex items-center justify-between text-slate-800 font-semibold border-b border-slate-200 pb-1">
              <span>Planning-Level Cost Itemization</span>
              <span className="font-mono text-slate-900 font-bold">{formatCurrency(simulation.total_estimated_cost)}</span>
            </div>
            <div className="space-y-1 text-[11px] text-slate-600">
              <div className="flex items-center justify-between">
                <span>Street Trees ({treesCount} × ${formatNumber(treeCost)})</span>
                <span className="font-mono text-slate-800 font-medium">{formatCurrency(treesCount * treeCost)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Shade Structures ({shadeCount} × ${formatNumber(shadeCost)})</span>
                <span className="font-mono text-slate-800 font-medium">{formatCurrency(shadeCount * shadeCost)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Cool Pavement ({coolPaveM2} m² × ${paveCost}/m²)</span>
                <span className="font-mono text-slate-800 font-medium">{formatCurrency(coolPaveM2 * paveCost)}</span>
              </div>
            </div>
          </div>

          {/* Spatial Coverage, Cost/m², & Benefited Population Summary */}
          <div className="bg-emerald-50/40 border border-emerald-200/70 rounded p-2.5 space-y-1.5 text-xs text-slate-700">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-slate-900">Estimated Site Coverage:</span>
              <span className="font-mono font-bold text-emerald-800">{imp.intervention_coverage_pct ?? 0}% of site</span>
            </div>
            <div className="flex items-center justify-between text-[11px] text-slate-600">
              <span>Estimated Benefited Area:</span>
              <span className="font-mono font-medium text-slate-900">{formatNumber(imp.benefited_area_m2 ?? 0)} m²</span>
            </div>
            <div className="flex items-center justify-between text-[11px] text-slate-600">
              <span>Estimated Heat Exposure Relief:</span>
              <span className="font-mono font-bold text-emerald-700">↓ {imp.heat_exposure_reduction_pct ?? imp.hours_35c_reduction_pct.toFixed(0)}%</span>
            </div>
            <div className="flex items-center justify-between text-[11px] text-slate-600">
              <span>Planning Cost per m² Benefited:</span>
              <span className="font-mono font-medium text-slate-900">
                {imp.cost_per_benefited_m2 ? `${formatCurrency(imp.cost_per_benefited_m2)} / m²` : "—"}
              </span>
            </div>
            <div className="flex items-center justify-between text-[11px] text-slate-600 pt-1 border-t border-emerald-100">
              <span>Estimated Protected Users:</span>
              <span className="font-mono font-medium text-slate-900">~{formatNumber(imp.benefited_daily_population)} daily citizens</span>
            </div>
          </div>

          {/* Preserved Baseline Priority Rationale (Collapsible / Non-contradicting) */}
          <div className="border border-slate-200 rounded overflow-hidden">
            <button
              type="button"
              onClick={() => setShowBaselineRationale(!showBaselineRationale)}
              className="w-full px-2.5 py-1.5 flex items-center justify-between text-[11px] font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors"
            >
              <span>Baseline Priority Rationale (Historical)</span>
              {showBaselineRationale ? <ChevronUp className="w-3 h-3 text-slate-400" /> : <ChevronDown className="w-3 h-3 text-slate-400" />}
            </button>

            {showBaselineRationale && (
              <div className="p-2.5 border-t border-slate-200 bg-slate-50/60 text-[11px] text-slate-600 space-y-1">
                <p className="text-[10px] text-slate-500 leading-tight">
                  Measured during FortyGuard baseline screening ({cityConfig.study_window}):
                </p>
                <ul className="list-disc list-inside space-y-0.5 text-slate-600 leading-snug">
                  {(asset.priority_reasons && asset.priority_reasons.length > 0) ? (
                    asset.priority_reasons.map((r, i) => <li key={i}>{r}</li>)
                  ) : (
                    <>
                      <li>High afternoon peak thermal exposure ({formatTemp(obs.peak_temperature_c)} baseline)</li>
                      <li>Elevated heat persistence ({obs.hours_above_35c.toFixed(1)}h exceeding {unit === "F" ? "95°F" : "35°C"})</li>
                      <li>High transit/public usage (~{formatNumber(asset.daily_visitors)} citizens/day)</li>
                    </>
                  )}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="grid grid-cols-2 gap-2 pt-1">
        <button
          onClick={onOpenOptimizer}
          className="px-3 py-2.5 bg-white hover:bg-slate-50 text-slate-800 border border-slate-300 rounded text-xs font-semibold transition-colors flex items-center justify-center gap-1.5 focus:outline-none focus:ring-2 focus:ring-slate-400 min-h-[40px]"
        >
          <SlidersHorizontal className="w-3.5 h-3.5 text-slate-500" />
          <span>Optimize Budget</span>
        </button>

        <button
          onClick={onOpenReport}
          className="px-3 py-2.5 bg-brand-600 hover:bg-brand-700 text-white rounded text-xs font-semibold transition-colors flex items-center justify-center gap-1.5 shadow-xs focus:outline-none focus:ring-2 focus:ring-brand-500 min-h-[40px]"
        >
          <FileText className="w-3.5 h-3.5" />
          <span>Generate Brief</span>
        </button>
      </div>

      {/* Methodology & Calculation Explanation Modal */}
      {showMethodologyModal && (
        <div
          onClick={() => setShowMethodologyModal(false)}
          className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-3 sm:p-4 animate-in fade-in duration-150"
          role="dialog"
          aria-modal="true"
          aria-labelledby="methodology-modal-title"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="bg-white border border-slate-300 w-full max-w-2xl max-h-[88vh] rounded-lg shadow-xl flex flex-col overflow-hidden text-slate-900"
          >
            {/* Header */}
            <div className="h-12 border-b border-slate-200 px-4 flex items-center justify-between bg-slate-50 flex-shrink-0">
              <div className="flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-brand-700" />
                <h3 id="methodology-modal-title" className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  Estimation Methodology &amp; Data Provenance
                </h3>
              </div>
              <button
                onClick={() => setShowMethodologyModal(false)}
                aria-label="Close dialog"
                className="w-9 h-9 inline-flex items-center justify-center rounded text-slate-500 hover:text-slate-900 hover:bg-slate-200 transition-colors min-h-[36px] min-w-[36px]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Body */}
            <div className="p-4 overflow-y-auto space-y-4 text-xs text-slate-700 custom-scrollbar leading-relaxed">
              {/* Provenance Box */}
              <div className="bg-slate-50 border border-slate-200 rounded p-3 space-y-2">
                <span className="font-semibold text-slate-900 block text-[11px] uppercase tracking-wider text-slate-500">
                  Data Provenance &amp; Clear Separation
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
                  <div className="bg-white border border-slate-200 p-2 rounded">
                    <span className="font-bold text-slate-900 block mb-0.5">Observed Baseline</span>
                    <p className="text-slate-600 leading-snug">
                      Derived directly from <strong>FortyGuard's 100m ambient temperature grid</strong>, cumulative exceedance hours (&gt;{unit === "F" ? "95°F" : "35°C"}), and persistence runs during the July 15–21, 2024 heatwave.
                    </p>
                  </div>
                  <div className="bg-brand-50/60 border border-brand-200 p-2 rounded">
                    <span className="font-bold text-brand-900 block mb-0.5">Modeled Planning Scenario</span>
                    <p className="text-slate-600 leading-snug">
                      Estimated using <strong>Thermal Capital's planning response functions</strong> calibrated to municipal cost benchmarks and empirical cooling response curves.
                    </p>
                  </div>
                </div>
              </div>

              {/* Physical Response Formulas */}
              <div className="space-y-2">
                <span className="font-semibold text-slate-900 block text-[11px] uppercase tracking-wider text-slate-500">
                  Intervention Response Functions &amp; Benchmarks
                </span>

                <div className="border border-slate-200 rounded divide-y divide-slate-100 text-[11px]">
                  <div className="p-2.5 space-y-0.5 bg-white">
                    <div className="flex items-center justify-between font-semibold text-slate-900">
                      <span>1. Urban Tree Canopy (+25 m² mature crown / tree)</span>
                      <span className="font-mono text-emerald-800 font-bold">$3,200 / tree</span>
                    </div>
                    <p className="text-slate-600 leading-snug">
                      <strong>Cooling mechanism:</strong> Evapotranspirative moisture cooling + solar interception (ΔT = 3.2 · (1 - e^(-0.065 · n)) with sublinear canopy overlap scaling).
                    </p>
                    <span className="text-[10px] text-slate-400 block">Cost source: NYC Parks &amp; Recreation FY2024 Street Tree contracts.</span>
                  </div>

                  <div className="p-2.5 space-y-0.5 bg-white">
                    <div className="flex items-center justify-between font-semibold text-slate-900">
                      <span>2. Engineered Shade Structure (+100 m² usable shade)</span>
                      <span className="font-mono text-sky-800 font-bold">$28,000 / unit</span>
                    </div>
                    <p className="text-slate-600 leading-snug">
                      <strong>Cooling mechanism:</strong> Complete shortwave solar radiation blockage, eliminating ground heat absorption (ΔT = 2.8 · (1 - e^(-0.45 · n))).
                    </p>
                    <span className="text-[10px] text-slate-400 block">Cost source: U.S. Federal Transit Administration (FTA) transit shelter guidelines.</span>
                  </div>

                  <div className="p-2.5 space-y-0.5 bg-white">
                    <div className="flex items-center justify-between font-semibold text-slate-900">
                      <span>3. Reflective Cool Pavement Coating (Albedo ≥ 0.35)</span>
                      <span className="font-mono text-amber-800 font-bold">$24 / m²</span>
                    </div>
                    <p className="text-slate-600 leading-snug">
                      <strong>Cooling mechanism:</strong> High solar reflectance reducing sensible heat flux and overnight heat retention (ΔT = 1.8 · (1 - e^(-0.0028 · A))).
                    </p>
                    <span className="text-[10px] text-slate-400 block">Cost source: U.S. EPA Heat Island Reduction Program &amp; Phoenix Cool Pavement Study.</span>
                  </div>
                </div>
              </div>

              {/* Diminishing Returns & Purpose Statement */}
              <div className="bg-slate-50 border border-slate-200 rounded p-3 space-y-1.5 text-[11px]">
                <span className="font-bold text-slate-900 block">Synergy &amp; Diminishing Returns</span>
                <p className="text-slate-600 leading-relaxed">
                  When combining multiple cooling interventions at a single site, cooling impacts exhibit non-linear diminishing returns because all treatments act upon the same local air volume. The model applies an asymptotic physical ceiling capped at <strong>4.2°C maximum ambient dry-bulb reduction</strong>.
                </p>
                <div className="pt-1.5 border-t border-slate-200 text-slate-500 text-[10px] italic">
                  <strong>Decision-Support Purpose:</strong> These outputs are intended to compare relative intervention scenarios and optimize municipal capital budget allocation. They are not a substitute for site-specific computational fluid dynamics (CFD) engineering or stamped civil construction drawings.
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="p-3 border-t border-slate-200 bg-slate-50 flex justify-end">
              <button
                onClick={() => setShowMethodologyModal(false)}
                className="px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded text-xs font-semibold transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

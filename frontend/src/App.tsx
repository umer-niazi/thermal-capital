import React, { useEffect, useState } from "react";
import {
  AppMode,
  BudgetOptimizationResult,
  CityConfig,
  HeatmapLayerType,
  PlacedIntervention,
  PlacedInterventionType,
  PublicAsset,
  SimulationResponse,
} from "./types";
import {
  fetchAssets,
  fetchCities,
  fetchCoverageSummary,
  fetchHeatmapLayer,
} from "./services/api";
import { Header } from "./components/Header";
import { MapViewer } from "./components/MapViewer";
import { RightPanel } from "./components/RightPanel";
import { BudgetOptimizerModal } from "./components/BudgetOptimizerModal";
import { PlanningBriefModal } from "./components/PlanningBriefModal";
import { generateOffsetCoordinate } from "./utils/geoUtils";
import { AlertCircle, Loader2 } from "lucide-react";
import { CoverageSummary } from "./types";

const FALLBACK_CITIES: CityConfig[] = [
  {
    city_key: "nyc",
    name: "New York City",
    state: "NY",
    display_label: "New York City (All Boroughs)",
    center: [-73.9680, 40.7300],
    zoom: 11.0,
    bounds: [[-74.258, 40.495], [-73.700, 40.915]],
    fortyguard_tiles_count: 47,
    study_date: "2024-07-15",
    study_window: "Jul 15–21, 2024",
    description: "Citywide FortyGuard 100m ambient microclimate grid across all five New York City boroughs (Manhattan, Brooklyn, Queens, The Bronx, and Staten Island).",
    key_neighborhoods: ["Manhattan", "Brooklyn", "Queens", "The Bronx", "Staten Island", "Hunts Point / Longwood", "Lower Manhattan", "Downtown Brooklyn", "Flushing", "Jamaica"],
  },
  {
    city_key: "manhattan",
    name: "Manhattan",
    state: "NY",
    display_label: "Manhattan",
    center: [-73.9712, 40.7831],
    zoom: 12.5,
    bounds: [[-74.048, 40.683], [-73.906, 40.880]],
    fortyguard_tiles_count: 9,
    study_date: "2024-07-15",
    study_window: "Jul 15–21, 2024",
    description: "High-density urban canyons, commercial corridors, and civic transit plazas across Manhattan.",
    key_neighborhoods: ["Lower Manhattan", "Midtown", "Harlem", "Washington Heights", "East Village"],
  },
  {
    city_key: "brooklyn",
    name: "Brooklyn",
    state: "NY",
    display_label: "Brooklyn",
    center: [-73.9442, 40.6782],
    zoom: 12.0,
    bounds: [[-74.042, 40.570], [-73.833, 40.739]],
    fortyguard_tiles_count: 14,
    study_date: "2024-07-15",
    study_window: "Jul 15–21, 2024",
    description: "Major transit interchanges, commercial corridors, residential brownstone districts, and coastal communities in Brooklyn.",
    key_neighborhoods: ["Downtown Brooklyn", "Williamsburg", "Bushwick", "Bed-Stuy", "Coney Island"],
  },
  {
    city_key: "queens",
    name: "Queens",
    state: "NY",
    display_label: "Queens",
    center: [-73.8317, 40.7282],
    zoom: 12.0,
    bounds: [[-73.963, 40.542], [-73.700, 40.801]],
    fortyguard_tiles_count: 23,
    study_date: "2024-07-15",
    study_window: "Jul 15–21, 2024",
    description: "Diverse commercial hubs, elevated transit spines, and residential neighborhoods across Queens.",
    key_neighborhoods: ["Flushing", "Jamaica", "Jackson Heights", "Long Island City", "Astoria", "Rockaways"],
  },
  {
    city_key: "bronx",
    name: "The Bronx",
    state: "NY",
    display_label: "The Bronx",
    center: [-73.8648, 40.8448],
    zoom: 12.5,
    bounds: [[-73.934, 40.785], [-73.765, 40.916]],
    fortyguard_tiles_count: 11,
    study_date: "2024-07-15",
    study_window: "Jul 15–21, 2024",
    description: "South Bronx industrial-residential interface, freight corridors, and high heat-vulnerability census tracts.",
    key_neighborhoods: ["Hunts Point", "Longwood", "Mott Haven", "Grand Concourse", "Riverdale"],
  },
  {
    city_key: "staten_island",
    name: "Staten Island",
    state: "NY",
    display_label: "Staten Island",
    center: [-74.1502, 40.5795],
    zoom: 12.0,
    bounds: [[-74.256, 40.496], [-74.049, 40.649]],
    fortyguard_tiles_count: 11,
    study_date: "2024-07-15",
    study_window: "Jul 15–21, 2024",
    description: "Ferry transit terminals, maritime commercial corridors, and suburban/parkland interfaces across Staten Island.",
    key_neighborhoods: ["St. George", "Stapleton", "Tottenville", "Mid-Island", "North Shore"],
  },
  {
    city_key: "hunts_point",
    name: "Hunts Point / Longwood",
    state: "NY",
    display_label: "Hunts Point / Longwood (South Bronx)",
    center: [-73.8860, 40.8145],
    zoom: 14.5,
    bounds: [[-73.900, 40.805], [-73.870, 40.825]],
    fortyguard_tiles_count: 4,
    study_date: "2024-07-15",
    study_window: "Jul 15–21, 2024",
    description: "Hyperlocal thermal screening across the Hunts Point Food Distribution Center and Longwood urban corridor.",
    key_neighborhoods: ["Hunts Point Peninsula", "Southern Boulevard", "Barretto Waterfront"],
  },
];

export const App: React.FC = () => {
  const [cities, setCities] = useState<CityConfig[]>(FALLBACK_CITIES);
  const [selectedCityKey, setSelectedCityKey] = useState<string>("nyc");
  const [coverageSummary, setCoverageSummary] = useState<CoverageSummary | null>(null);

  const [assets, setAssets] = useState<PublicAsset[]>([]);
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null);

  const [appMode, setAppMode] = useState<AppMode>("explore");
  const [activeLayer, setActiveLayer] = useState<HeatmapLayerType>("tcm_peak");
  const [heatmapGeoJSON, setHeatmapGeoJSON] = useState<GeoJSON.FeatureCollection | null>(null);

  // Scenario state: visual map interventions
  const [placedInterventions, setPlacedInterventions] = useState<PlacedIntervention[]>([]);
  const [activePlacementTool, setActivePlacementTool] = useState<PlacedInterventionType | null>(null);

  const [activeSimulation, setActiveSimulation] = useState<SimulationResponse | null>(null);
  const [isOptimizerOpen, setIsOptimizerOpen] = useState<boolean>(false);
  const [isReportOpen, setIsReportOpen] = useState<boolean>(false);
  const [latestOptResult, setLatestOptResult] = useState<BudgetOptimizationResult | null>(null);

  const [loadingInitial, setLoadingInitial] = useState<boolean>(true);
  const [loadingCityData, setLoadingCityData] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const currentCity = cities.find((c) => c.city_key === selectedCityKey) || cities[0];

  // 1. Initial Load: Cities & Coverage
  useEffect(() => {
    let isMounted = true;
    fetchCities()
      .then((data) => {
        if (isMounted && data.length > 0) {
          setCities(data);
        }
      })
      .catch((err) => {
        console.warn("Could not fetch /api/cities, using fallback:", err);
      });

    fetchCoverageSummary()
      .then((cov) => {
        if (isMounted && cov) {
          setCoverageSummary(cov);
        }
      })
      .catch(() => {});

    return () => {
      isMounted = false;
    };
  }, []);

  // 2. Load Assets and Heatmap when city changes
  useEffect(() => {
    let isMounted = true;
    setLoadingCityData(true);
    setError(null);

    Promise.all([
      fetchAssets(selectedCityKey),
      fetchHeatmapLayer(activeLayer, selectedCityKey),
    ])
      .then(([assetsRes, heatmapRes]) => {
        if (!isMounted) return;
        setAssets(assetsRes);
        setHeatmapGeoJSON(heatmapRes);
        if (assetsRes.length > 0) {
          setSelectedAssetId(assetsRes[0].asset_id);
        } else {
          setSelectedAssetId(null);
        }
        setLoadingInitial(false);
        setLoadingCityData(false);
      })
      .catch((err) => {
        if (!isMounted) return;
        console.error("Failed to load city data:", err);
        setError(err.message || "Failed to load heat data");
        setLoadingInitial(false);
        setLoadingCityData(false);
      });

    return () => {
      isMounted = false;
    };
  }, [selectedCityKey]);

  // 3. Fetch Heatmap Layer when activeLayer changes
  useEffect(() => {
    let isMounted = true;
    fetchHeatmapLayer(activeLayer, selectedCityKey)
      .then((geo) => {
        if (isMounted) setHeatmapGeoJSON(geo);
      })
      .catch((err) => {
        console.error(`Failed to load layer ${activeLayer}:`, err);
      });

    return () => {
      isMounted = false;
    };
  }, [activeLayer, selectedCityKey]);

  const handleSelectAsset = (assetId: string) => {
    setSelectedAssetId(assetId);
  };

  const handleResetSelection = () => {
    setSelectedAssetId(null);
  };

  const handlePlanAsset = (assetId: string) => {
    setSelectedAssetId(assetId);
    setAppMode("plan");
  };

  // Intervention handlers
  const handleAddIntervention = (item: Omit<PlacedIntervention, "id" | "created_at">) => {
    const newIntervention: PlacedIntervention = {
      ...item,
      id: `int-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      created_at: Date.now(),
    };
    setPlacedInterventions((prev) => [...prev, newIntervention]);
  };

  const handleRemoveIntervention = (id: string) => {
    setPlacedInterventions((prev) => prev.filter((i) => i.id !== id));
  };

  const handleClearAssetInterventions = (assetId?: string) => {
    if (assetId) {
      setPlacedInterventions((prev) => prev.filter((i) => i.asset_id !== assetId));
    } else {
      setPlacedInterventions([]);
    }
  };

  const handleApplyPortfolio = (optResult: BudgetOptimizationResult) => {
    setLatestOptResult(optResult);

    // Convert optimized portfolio into placed interventions on the map!
    const newInterventions: PlacedIntervention[] = [];
    optResult.asset_allocations.forEach((alloc) => {
      const center: [number, number] = [alloc.longitude, alloc.latitude];
      let offsetIdx = 0;

      alloc.recommended_interventions.forEach((rec) => {
        if (rec.intervention_type === "tree_canopy") {
          for (let t = 0; t < rec.quantity; t++) {
            const [lng, lat] = generateOffsetCoordinate(center, offsetIdx++, rec.quantity + 2, 25);
            newInterventions.push({
              id: `int-opt-${alloc.asset_id}-tree-${t}-${Date.now()}`,
              type: "tree",
              latitude: lat,
              longitude: lng,
              asset_id: alloc.asset_id,
              label: `Optimized Tree at ${alloc.asset_name}`,
              created_at: Date.now(),
            });
          }
        } else if (rec.intervention_type === "shade_structure") {
          for (let s = 0; s < rec.quantity; s++) {
            const [lng, lat] = generateOffsetCoordinate(center, offsetIdx++, rec.quantity + 2, 18);
            newInterventions.push({
              id: `int-opt-${alloc.asset_id}-shade-${s}-${Date.now()}`,
              type: "shade",
              latitude: lat,
              longitude: lng,
              asset_id: alloc.asset_id,
              label: `Optimized Shade at ${alloc.asset_name}`,
              created_at: Date.now(),
            });
          }
        } else if (rec.intervention_type === "cool_pavement") {
          const [lng, lat] = generateOffsetCoordinate(center, offsetIdx++, 4, 20);
          newInterventions.push({
            id: `int-opt-${alloc.asset_id}-pave-${Date.now()}`,
            type: "reflective",
            latitude: lat,
            longitude: lng,
            asset_id: alloc.asset_id,
            area_m2: rec.area_m2 || 300,
            label: `Optimized Cool Pavement at ${alloc.asset_name}`,
            created_at: Date.now(),
          });
        }
      });
    });

    if (newInterventions.length > 0) {
      setPlacedInterventions(newInterventions);
    }

    if (optResult.asset_allocations.length > 0) {
      setSelectedAssetId(optResult.asset_allocations[0].asset_id);
    }
    setAppMode("plan");
  };

  const handleOpenReportWithResult = (optResult: BudgetOptimizationResult) => {
    setLatestOptResult(optResult);
    setIsOptimizerOpen(false);
    setIsReportOpen(true);
  };

  const selectedAsset = assets.find((a) => a.asset_id === selectedAssetId) || null;

  return (
    <div className="h-screen w-screen flex flex-col bg-slate-50 text-slate-900 overflow-hidden font-sans print:h-auto print:w-full print:overflow-visible print:bg-white app-container">
      {/* Top Header */}
      <div className="print:hidden">
        <Header
          currentCity={currentCity}
          allCities={cities}
          onSelectCity={(cKey) => {
            setSelectedCityKey(cKey);
            setSelectedAssetId(null);
          }}
          appMode={appMode}
          onSwitchMode={setAppMode}
          onOpenOptimizer={() => setIsOptimizerOpen(true)}
          onOpenReport={() => setIsReportOpen(true)}
          coverageSummary={coverageSummary}
        />
      </div>

      {/* Main Map + Side Panel Layout */}
      {loadingInitial ? (
        <div className="flex-1 flex flex-col items-center justify-center text-slate-500 print:hidden">
          <Loader2 className="w-8 h-8 animate-spin text-slate-600 mb-3" />
          <h2 className="text-sm font-semibold text-slate-800">Loading Thermal Capital...</h2>
          <p className="text-xs text-slate-500 mt-1">Retrieving 100m FortyGuard heat data</p>
        </div>
      ) : error ? (
        <div className="flex-1 flex items-center justify-center p-6 print:hidden">
          <div className="max-w-md w-full bg-white border border-red-200 p-6 rounded text-center space-y-3 shadow-sm">
            <AlertCircle className="w-8 h-8 text-red-500 mx-auto" />
            <h2 className="text-sm font-bold text-slate-900">Unable to Load Heat Data</h2>
            <p className="text-xs text-slate-600">{error}</p>
            <button
              onClick={() => window.location.reload()}
              className="px-3 py-1 bg-slate-800 hover:bg-slate-900 text-white rounded text-xs font-semibold"
            >
              Retry
            </button>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex flex-col lg:flex-row overflow-hidden relative print:hidden">
          {/* Primary Map View */}
          <main className="flex-1 h-[55vh] lg:h-full relative">
            <MapViewer
              cityConfig={currentCity}
              assets={assets}
              selectedAssetId={selectedAssetId}
              onSelectAsset={handleSelectAsset}
              appMode={appMode}
              activeLayer={activeLayer}
              onChangeLayer={setActiveLayer}
              heatmapGeoJSON={heatmapGeoJSON}
              activeSimulation={activeSimulation}
              placedInterventions={placedInterventions}
              onAddIntervention={handleAddIntervention}
              onRemoveIntervention={handleRemoveIntervention}
              activePlacementTool={activePlacementTool}
              onSelectPlacementTool={setActivePlacementTool}
            />
          </main>

          {/* Contextual Right Panel */}
          <RightPanel
            appMode={appMode}
            currentCity={currentCity}
            assets={assets}
            selectedAsset={selectedAsset}
            onSelectAsset={handleSelectAsset}
            onBackToRanking={handleResetSelection}
            onPlanAsset={handlePlanAsset}
            onSwitchMode={setAppMode}
            onOpenOptimizer={() => setIsOptimizerOpen(true)}
            onOpenReport={() => setIsReportOpen(true)}
            onPlanUpdated={setActiveSimulation}
            placedInterventions={placedInterventions}
            onAddIntervention={handleAddIntervention}
            onRemoveIntervention={handleRemoveIntervention}
            onClearAssetInterventions={handleClearAssetInterventions}
            activePlacementTool={activePlacementTool}
            onSelectPlacementTool={setActivePlacementTool}
            isLoading={loadingCityData}
          />
        </div>
      )}

      {/* Budget Optimizer Modal */}
      {isOptimizerOpen && (
        <div className="print:hidden">
          <BudgetOptimizerModal
            cityConfig={currentCity}
            onClose={() => setIsOptimizerOpen(false)}
            onApplyPortfolio={handleApplyPortfolio}
            onOpenReport={handleOpenReportWithResult}
          />
        </div>
      )}

      {/* Action Brief Modal */}
      {isReportOpen && (
        <PlanningBriefModal
          cityConfig={currentCity}
          optResult={latestOptResult}
          onClose={() => setIsReportOpen(false)}
        />
      )}
    </div>
  );
};

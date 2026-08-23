import {
  BudgetOptimizationRequest,
  BudgetOptimizationResult,
  CandidateSiteSummary,
  CityConfig,
  ComparisonResponse,
  CoverageSummary,
  HeatmapLayerType,
  InterventionCostDetail,
  PlanningReport,
  PublicAsset,
  RegionType,
  SimulationRequest,
  SimulationResponse,
  SiteScreeningResult,
  SiteThermalExposure,
} from "../types";

const API_BASE = "/api";

export const DEFAULT_INTERVENTION_COSTS: Record<string, InterventionCostDetail> = {
  tree_canopy: {
    intervention_type: "tree_canopy",
    name: "Street Tree Planting",
    unit: "tree",
    planning_unit_cost: 3200,
    range_low: 1900,
    range_high: 4500,
    currency: "USD",
    source: "NYC Dept. of Parks & Recreation Street Tree Contracts (FY2024 Average: ~$3,300; Tree Fund: $1,900) & Forest for All NYC",
    explanation: "Turnkey municipal planting: 2.5–3\" caliper nursery stock, utility survey, sidewalk concrete cutting, tree pit excavation, structural soil, tree guard, and 2-year establishment watering warranty.",
  },
  shade_structure: {
    intervention_type: "shade_structure",
    name: "Engineered Shade Structure",
    unit: "structure",
    planning_unit_cost: 28000,
    range_low: 18000,
    range_high: 45000,
    currency: "USD",
    source: "U.S. Federal Transit Administration (FTA) & Municipal Parks Capital Benchmarks (~$30–$80/sq ft installed)",
    explanation: "Commercial ~400–600 sq ft engineered steel cantilever/frame, UV-blocking HDPE shade canopy (90%+ UV block), reinforced concrete footings, civil engineering, and ADA accessibility compliance.",
  },
  cool_pavement: {
    intervention_type: "cool_pavement",
    name: "Reflective Cool Pavement Coating",
    unit: "m²",
    planning_unit_cost: 24,
    range_low: 14,
    range_high: 38,
    currency: "USD",
    source: "U.S. EPA Heat Island Reduction Program & City of Phoenix Street Transportation Dept. Cool Pavement Program Evaluation",
    explanation: "Surface sweeping, asphalt crack repair/prep, two coats of high-albedo solar-reflective coating (solar reflectance ≥ 0.35), traffic control, and application labor.",
  },
  cool_roof: {
    intervention_type: "cool_roof",
    name: "High-Albedo Cool Roof Coating",
    unit: "m²",
    planning_unit_cost: 32,
    range_low: 20,
    range_high: 55,
    currency: "USD",
    source: "NYC CoolRoofs Initiative & U.S. Department of Energy (DOE) FEMP Benchmark",
    explanation: "Roof deck preparation, primer, elastomeric high-reflectance coating/membrane (initial SRI ≥ 82), and municipal quality control inspection.",
  },
};

// ---------------------------------------------------------------------------
// In-Memory Client Cache Layer
// ---------------------------------------------------------------------------
const memoryCache = new Map<string, any>();

export function clearApiCache(): void {
  memoryCache.clear();
}

export async function fetchInterventionCosts(): Promise<Record<string, InterventionCostDetail>> {
  const cacheKey = "costs:default";
  if (memoryCache.has(cacheKey)) {
    return memoryCache.get(cacheKey);
  }
  try {
    const resp = await fetch(`${API_BASE}/interventions/costs`);
    if (resp.ok) {
      const data = await resp.json();
      memoryCache.set(cacheKey, data);
      return data;
    }
  } catch {
    // Fall back to client default benchmarks
  }
  return DEFAULT_INTERVENTION_COSTS;
}

let citiesPromise: Promise<CityConfig[]> | null = null;
export async function fetchCities(): Promise<CityConfig[]> {
  if (memoryCache.has("cities")) {
    return memoryCache.get("cities");
  }
  if (!citiesPromise) {
    citiesPromise = (async () => {
      const resp = await fetch(`${API_BASE}/cities`);
      if (!resp.ok) {
        throw new Error(`Failed to fetch supported cities: ${resp.statusText}`);
      }
      const data = await resp.json();
      memoryCache.set("cities", data);
      return data;
    })();
  }
  return citiesPromise;
}

let coveragePromise: Promise<CoverageSummary | null> | null = null;
export async function fetchCoverageSummary(): Promise<CoverageSummary | null> {
  if (memoryCache.has("coverage")) {
    return memoryCache.get("coverage");
  }
  if (!coveragePromise) {
    coveragePromise = (async () => {
      try {
        const resp = await fetch(`${API_BASE}/coverage`);
        if (resp.ok) {
          const data = await resp.json();
          memoryCache.set("coverage", data);
          return data;
        }
      } catch {
        // Fallback if not ready
      }
      return null;
    })();
  }
  return coveragePromise;
}

export async function fetchAssets(city: string = "nyc", assetType?: string): Promise<PublicAsset[]> {
  const cacheKey = `assets:${city.toLowerCase()}:${assetType || "all"}`;
  if (memoryCache.has(cacheKey)) {
    return memoryCache.get(cacheKey);
  }

  let url = `${API_BASE}/assets?city=${encodeURIComponent(city)}`;
  if (assetType) {
    url += `&asset_type=${encodeURIComponent(assetType)}`;
  }
  const resp = await fetch(url);
  if (!resp.ok) {
    throw new Error(`Failed to fetch public assets for ${city}: ${resp.statusText}`);
  }
  const data = await resp.json();
  memoryCache.set(cacheKey, data);
  return data;
}

export async function fetchAssetDetail(assetId: string, city: string = "nyc"): Promise<PublicAsset> {
  const cacheKey = `asset:${city.toLowerCase()}:${assetId}`;
  if (memoryCache.has(cacheKey)) {
    return memoryCache.get(cacheKey);
  }

  const resp = await fetch(`${API_BASE}/assets/${assetId}?city=${city}`);
  if (!resp.ok) {
    throw new Error(`Failed to fetch asset detail for ${assetId}: ${resp.statusText}`);
  }
  const data = await resp.json();
  memoryCache.set(cacheKey, data);
  return data;
}

export async function simulateInterventions(req: SimulationRequest): Promise<SimulationResponse> {
  const resp = await fetch(`${API_BASE}/interventions/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!resp.ok) {
    throw new Error(`Failed to simulate interventions: ${resp.statusText}`);
  }
  return resp.json();
}

export async function optimizeBudget(req: BudgetOptimizationRequest): Promise<BudgetOptimizationResult> {
  const targetIdsKey = (req.target_asset_ids || []).slice().sort().join(",");
  const cityKey = (req.city || "nyc").toLowerCase();
  const cacheKey = `optimize:${cityKey}:${req.budget}:${req.strategy}:${targetIdsKey}`;
  if (memoryCache.has(cacheKey)) {
    return memoryCache.get(cacheKey);
  }

  const resp = await fetch(`${API_BASE}/optimize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!resp.ok) {
    throw new Error(`Failed to optimize budget: ${resp.statusText}`);
  }
  const data = await resp.json();
  memoryCache.set(cacheKey, data);
  return data;
}

export async function generateReport(req: BudgetOptimizationRequest): Promise<PlanningReport> {
  const targetIdsKey = (req.target_asset_ids || []).slice().sort().join(",");
  const cityKey = (req.city || "nyc").toLowerCase();
  const cacheKey = `report:${cityKey}:${req.budget}:${req.strategy}:${targetIdsKey}`;
  if (memoryCache.has(cacheKey)) {
    return memoryCache.get(cacheKey);
  }

  const resp = await fetch(`${API_BASE}/report`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!resp.ok) {
    throw new Error(`Failed to generate planning report: ${resp.statusText}`);
  }
  const data = await resp.json();
  memoryCache.set(cacheKey, data);
  return data;
}

export async function fetchHeatmapLayer(
  layer: HeatmapLayerType = "tcm_peak",
  region: string = "nyc",
  borough?: string
): Promise<GeoJSON.FeatureCollection> {
  const bKey = borough && borough !== "all" ? borough.toLowerCase() : "all";
  const cacheKey = `heatmap:${layer}:${region.toLowerCase()}:${bKey}`;
  if (memoryCache.has(cacheKey)) {
    return memoryCache.get(cacheKey);
  }

  let url = `${API_BASE}/heatmap?layer=${layer}&region=${region}`;
  if (borough && borough !== "all") {
    url += `&borough=${encodeURIComponent(borough)}`;
  }
  const resp = await fetch(url);
  if (!resp.ok) {
    throw new Error(`Failed to fetch heatmap layer ${layer} for ${region}: ${resp.statusText}`);
  }
  const data = await resp.json();
  memoryCache.set(cacheKey, data);
  return data;
}

export async function fetchMethodology(): Promise<Record<string, any>> {
  if (memoryCache.has("methodology")) {
    return memoryCache.get("methodology");
  }
  const resp = await fetch(`${API_BASE}/methodology`);
  if (!resp.ok) {
    throw new Error(`Failed to fetch methodology: ${resp.statusText}`);
  }
  const data = await resp.json();
  memoryCache.set("methodology", data);
  return data;
}

// ---------------------------------------------------------------------------
// Backward compatibility functions
// ---------------------------------------------------------------------------

export async function fetchSites(region: RegionType = "texas"): Promise<CandidateSiteSummary[]> {
  const resp = await fetch(`${API_BASE}/sites?region=${region}`);
  if (!resp.ok) {
    throw new Error(`Failed to fetch sites for ${region}: ${resp.statusText}`);
  }
  return resp.json();
}

export async function fetchScreening(region: RegionType = "texas"): Promise<SiteScreeningResult> {
  const resp = await fetch(`${API_BASE}/screening?region=${region}`);
  if (!resp.ok) {
    throw new Error(`Failed to fetch screening for ${region}: ${resp.statusText}`);
  }
  return resp.json();
}

export async function fetchSiteDetail(siteId: string, region: RegionType = "texas"): Promise<SiteThermalExposure> {
  const resp = await fetch(`${API_BASE}/sites/${siteId}?region=${region}`);
  if (!resp.ok) {
    throw new Error(`Failed to fetch site detail for ${siteId}: ${resp.statusText}`);
  }
  return resp.json();
}

export async function compareSites(siteIds: string[], region: RegionType = "texas"): Promise<ComparisonResponse> {
  const resp = await fetch(`${API_BASE}/compare`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ site_ids: siteIds, region }),
  });
  if (!resp.ok) {
    throw new Error(`Failed to compare sites: ${resp.statusText}`);
  }
  return resp.json();
}

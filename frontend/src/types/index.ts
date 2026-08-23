export type AssetType =
  | "bus_stop"
  | "playground"
  | "school"
  | "park"
  | "pedestrian_corridor"
  | "public_plaza"
  | "community_center";

export type InterventionType =
  | "tree_canopy"
  | "shade_structure"
  | "cool_pavement"
  | "cool_roof";

export type HeatRiskLevel = "Low" | "Moderate" | "High" | "Severe" | "Extreme";

export type OptimizationStrategy =
  | "balanced"
  | "vulnerable_populations"
  | "transit_corridors"
  | "max_heat_reduction";

export type AppMode = "explore" | "plan";

export type TemperatureUnit = "F" | "C";

export type PlacedInterventionType = "tree" | "shade" | "reflective";

export interface PlacedIntervention {
  id: string;
  type: PlacedInterventionType;
  latitude: number;
  longitude: number;
  asset_id?: string | null;
  area_m2?: number;
  label?: string;
  created_at: number;
}

export interface ObservedHeatMetrics {
  peak_temperature_c: number;
  peak_temperature_f: number;
  mean_temperature_c: number;
  mean_temperature_f: number;
  overnight_min_c: number;
  overnight_min_f: number;
  hours_above_35c: number;
  persistence_hours: number;
  impervious_pct: number;
  canopy_pct: number;
  peak_wet_bulb_c?: number | null;
  hotspot_rank?: number | null;
  contributing_tile_id?: string | number | null;
}

export type ScenarioViewMode = "baseline" | "scenario";

export interface PublicAsset {
  asset_id: string;
  name: string;
  asset_type: AssetType;
  city: string;
  latitude: number;
  longitude: number;
  geometry: any;
  footprint_m2: number;
  daily_visitors: number;
  vulnerability_weight: number;
  heat_risk_level: HeatRiskLevel;
  heat_risk_score: number;
  priority_level?: string;
  priority_reasons?: string[];
  observed_heat: ObservedHeatMetrics;
  recommended_interventions: InterventionType[];
  notes?: string | null;
}

export interface InterventionConfig {
  intervention_type: InterventionType;
  quantity: number;
  area_m2: number;
  unit_cost: number;
  total_cost: number;
  modeled_peak_delta_c: number;
  modeled_hours_reduction_pct: number;
  description: string;
}

export interface InterventionCostDetail {
  intervention_type: InterventionType;
  name: string;
  unit: string;
  planning_unit_cost: number;
  range_low: number;
  range_high: number;
  currency: string;
  source: string;
  explanation: string;
}

export type InterventionCostRegistry = Record<string, InterventionCostDetail>;

export interface ModeledImpactSummary {
  peak_temp_before_c: number;
  peak_temp_before_f: number;
  peak_temp_after_c: number;
  peak_temp_after_f: number;
  peak_reduction_c: number;
  peak_reduction_f: number;

  mean_temp_before_c: number;
  mean_temp_after_c: number;
  mean_reduction_c: number;

  hours_35c_before: number;
  hours_35c_after: number;
  hours_35c_reduction_pct: number;

  persistence_hours_before: number;
  persistence_hours_after: number;
  persistence_reduction_pct: number;

  tree_canopy_pct_before: number;
  tree_canopy_pct_after: number;
  canopy_increase_pct: number;

  impervious_pct_before: number;
  impervious_pct_after: number;

  benefited_daily_population: number;
  affected_area_m2: number;
  benefited_area_m2?: number;
  intervention_coverage_pct?: number;
  heat_exposure_reduction_pct?: number;
  cost_per_celsius_reduced?: number | null;
  cost_per_benefited_m2?: number | null;
  impact_label?: string;
}

export interface SimulationRequest {
  asset_id?: string | null;
  city?: string;
  footprint_m2?: number;
  baseline_observed?: ObservedHeatMetrics | null;
  trees_count?: number;
  shade_structures_count?: number;
  cool_pavement_m2?: number;
  cool_roof_m2?: number;
  daily_visitors?: number;
}

export interface SimulationResponse {
  asset_id?: string | null;
  city: string;
  interventions: InterventionConfig[];
  total_estimated_cost: number;
  modeled_impact: ModeledImpactSummary;
  scientific_assumptions: string[];
  disclaimer: string;
}

export interface BudgetOptimizationRequest {
  city?: string;
  budget?: number;
  strategy?: OptimizationStrategy;
  target_asset_ids?: string[] | null;
}

export interface RecommendedAssetAllocation {
  asset_id: string;
  asset_name: string;
  asset_type: AssetType;
  latitude: number;
  longitude: number;
  heat_risk_level: HeatRiskLevel;
  observed_peak_c: number;
  recommended_interventions: InterventionConfig[];
  allocated_cost: number;
  modeled_peak_reduction_c: number;
  modeled_hours_reduction_pct: number;
  benefited_daily_population: number;
  rationale: string;
}

export interface BudgetOptimizationResult {
  city: string;
  strategy: OptimizationStrategy;
  target_budget: number;
  total_allocated_cost: number;
  remaining_budget: number;
  total_trees: number;
  total_shade_structures: number;
  total_cool_pavement_m2: number;
  total_cool_roof_m2: number;
  total_assets_covered: number;
  total_benefited_population: number;
  portfolio_avg_peak_reduction_c: number;
  portfolio_avg_hours_reduction_pct: number;
  asset_allocations: RecommendedAssetAllocation[];
  optimization_rationale: string[];
  methodology: string;
}

export interface PlanningReport {
  report_id: string;
  title: string;
  city: string;
  generated_at: string;
  study_period: string;
  budget_allocated: number;
  executive_summary: string;
  observed_baseline_summary: Record<string, any>;
  proposed_portfolio: Record<string, any>;
  modeled_outcomes_summary: Record<string, any>;
  target_assets_table: Array<{
    asset_id: string;
    asset_name: string;
    asset_type: string;
    heat_risk_level: string;
    observed_peak_c: string;
    allocated_cost: string;
    modeled_peak_reduction: string;
    hours_reduction: string;
    benefited_citizens: string;
    interventions_package: string;
    rationale: string;
  }>;
  intervention_itemization: Array<{
    category: string;
    units: string;
    unit_rate: string;
    subtotal: string;
    impact_mechanism: string;
  }>;
  methodology_and_assumptions: string[];
  data_sources: string[];
}

export interface CityConfig {
  city_key: string;
  name: string;
  state: string;
  display_label: string;
  center: [number, number];
  zoom: number;
  bounds: [[number, number], [number, number]];
  fortyguard_tiles_count: number;
  study_date: string;
  study_window: string;
  description: string;
  key_neighborhoods: string[];
}

export interface CoverageSummary {
  city: string;
  study_date: string;
  study_window: string;
  timestamp: string;
  total_tiles_required: number;
  tiles_cached: number;
  tiles_available: number;
  tiles_failed: number;
  coverage_percentage: number;
  is_complete_citywide: boolean;
  layers_available: {
    tcm_peak: number;
    tcm_mean: number;
    exceedance: number;
    persistence: number;
    cooling_burden: number;
  };
  geographic_bounds: {
    min_longitude: number;
    min_latitude: number;
    max_longitude: number;
    max_latitude: number;
  };
  data_provenance: string;
}

// ---------------------------------------------------------------------------
// Existing Screening & Comparison Models for Compatibility
// ---------------------------------------------------------------------------

export interface ThermalMetrics {
  peak_temperature_c: number;
  peak_temperature_f: number;
  mean_temperature_c: number;
  mean_temperature_f: number;
  overnight_min_temperature_c: number;
  overnight_min_temperature_f: number;
  diurnal_swing_c: number;
  diurnal_swing_f: number;
  exceedance_hours?: number | null;
  persistence_hours?: number | null;
  peak_wet_bulb_c?: number | null;
  peak_wet_bulb_f?: number | null;
  peak_apparent_temperature_c?: number | null;
  peak_apparent_temperature_f?: number | null;
  vegetation_pct?: number | null;
  impervious_pct?: number | null;
}

export interface EnvironmentalMetrics {
  peak_apparent_temperature_c: number;
  peak_apparent_temperature_f: number;
  peak_apparent_temperature_time: string;
  peak_wet_bulb_temperature_c: number;
  peak_wet_bulb_temperature_f: number;
  mean_wet_bulb_temperature_c: number;
  mean_wet_bulb_temperature_f: number;
  minimum_wet_bulb_temperature_c: number;
  minimum_wet_bulb_temperature_f: number;
  peak_relative_humidity_percent: number;
  peak_heat_index_c?: number | null;
  peak_heat_index_f?: number | null;
  peak_heat_index_time?: string | null;
  peak_aqi?: number | null;
  solar_irradiance_ghi?: number | null;
}

export interface SatelliteMetrics {
  impervious_pct: number;
  vegetation_pct: number;
  building_pct: number;
  road_pct: number;
  pavement_pct: number;
  tree_pct: number;
  bare_ground_pct: number;
  raw_segments: Record<string, number>;
  image_year?: string | null;
}

export interface CoolingBurdenMetrics {
  cooling_degree_hours_above_25c: number;
  hours_above_35c: number;
  hours_above_40c: number;
  peak_wet_bulb_c?: number | null;
  overnight_min_c: number;
  thermal_recovery_hours: number;
  chiller_cop_degradation_pct?: number | null;
}

export interface ScoreComponent {
  name: string;
  weight: number;
  raw_value: number | null;
  raw_units: string;
  normalized_score: number;
  weighted_contribution: number;
  description: string;
  data_source: string;
  is_estimated_or_fallback: boolean;
}

export interface ThermalRiskResult {
  total_score: number;
  risk_category: string;
  components: Record<string, ScoreComponent>;
  explanation: string[];
  data_completeness: string;
  scoring_profile?: string | null;
  portfolio_score?: number | null;
}

export interface SiteThermalExposure {
  site_id: string;
  site_name: string;
  city?: string | null;
  submarket?: string | null;
  market_cluster?: string | null;
  archetype?: string | null;
  rank?: number | null;
  data_status?: string;
  data_completeness: string;
  notes?: string | null;
  geometry?: any;
  tcm_metrics?: ThermalMetrics | null;
  exceedance_hours?: number | null;
  persistence_hours?: number | null;
  environmental_metrics?: EnvironmentalMetrics | null;
  satellite_metrics?: SatelliteMetrics | null;
  cooling_burden?: CoolingBurdenMetrics | null;
  risk_result?: ThermalRiskResult | null;
  portfolio_score?: number | null;
  coverage_pct: number;
  contributing_tile_count: number;
  coverage_warning?: string | null;
}

export interface SiteScreeningResult {
  analysis_id: string;
  region?: string;
  study_date: string;
  study_window_days: number;
  window_start: string;
  window_end: string;
  aoi_geometry: any;
  aoi_area_km2: number;
  ranked_sites: SiteThermalExposure[];
  shared_heat_metrics: Record<string, any>;
  enrichment_status: Record<string, any>;
  scoring_metadata: Record<string, any>;
}

export interface CandidateSiteSummary {
  site_id: string;
  site_name: string;
  city?: string | null;
  submarket?: string | null;
  market_cluster?: string | null;
  archetype?: string | null;
  rank?: number | null;
  score?: number | null;
  portfolio_score?: number | null;
  risk_category: string;
  data_status?: string;
  data_completeness: string;
  coverage_pct: number;
  contributing_tile_count: number;
  coverage_warning?: string | null;
  geometry?: any;
  notes?: string | null;
  peak_temperature_c?: number | null;
  peak_temperature_f?: number | null;
  mean_temperature_c?: number | null;
  mean_temperature_f?: number | null;
  overnight_min_temperature_c?: number | null;
  overnight_min_temperature_f?: number | null;
  diurnal_swing_c?: number | null;
  diurnal_swing_f?: number | null;
  exceedance_hours?: number | null;
  persistence_hours?: number | null;
  peak_wet_bulb_c?: number | null;
  peak_wet_bulb_f?: number | null;
  hot_hour_apparent_c?: number | null;
  hot_hour_apparent_time?: string | null;
  hot_hour_heat_index_c?: number | null;
  impervious_pct?: number | null;
  vegetation_pct?: number | null;
  cooling_degree_hours?: number | null;
  chiller_cop_loss_pct?: number | null;
  short_interpretation?: string | null;
}

export interface CompareMetricsRow {
  metric_key: string;
  label: string;
  units: string;
  lower_is_better: boolean;
  values: Record<string, string | number>;
}

export interface ComparisonResponse {
  compared_sites: Array<{
    site_id: string;
    site_name: string;
    city?: string | null;
    submarket?: string | null;
    market_cluster?: string | null;
    archetype?: string | null;
    rank?: number | null;
    score: number;
    portfolio_score?: number | null;
    risk_category: string;
    data_status?: string;
    data_completeness: string;
  }>;
  metrics_table: CompareMetricsRow[];
  why_ranking_differs: string[];
}

export type HeatmapLayerType = "tcm_peak" | "tcm_mean" | "exceedance" | "persistence" | "cooling";
export type RegionType = "nyc" | "phoenix" | "san_jose" | "texas" | "austin" | "houston" | "dfw" | "el_paso";

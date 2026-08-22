import { describe, expect, it } from "vitest";
import {
  getDistanceMeters,
  validateInterventionPlacement,
} from "../utils/spatialValidation";
import { PlacedIntervention, PublicAsset } from "../types";

describe("spatialValidation Utility", () => {
  const mockAsset: PublicAsset = {
    asset_id: "NYC-HP-01",
    name: "Hunts Point Community Plaza",
    asset_type: "public_plaza",
    city: "NYC",
    latitude: 40.8165,
    longitude: -73.8860,
    geometry: { type: "Point", coordinates: [-73.8860, 40.8165] },
    footprint_m2: 1500,
    daily_visitors: 1200,
    vulnerability_weight: 1.4,
    heat_risk_level: "Severe",
    heat_risk_score: 86.0,
    observed_heat: {
      peak_temperature_c: 38.5,
      peak_temperature_f: 101.3,
      mean_temperature_c: 32.5,
      mean_temperature_f: 90.5,
      overnight_min_c: 26.0,
      overnight_min_f: 78.8,
      hours_above_35c: 6.0,
      persistence_hours: 4.5,
      impervious_pct: 85.0,
      canopy_pct: 5.0,
    },
    recommended_interventions: ["tree_canopy", "shade_structure"],
  };

  it("calculates accurate distance in meters between coordinates", () => {
    // 0 distance
    expect(getDistanceMeters(40.8165, -73.8860, 40.8165, -73.8860)).toBeCloseTo(0, 1);

    // ~111 meters for 0.001 deg latitude
    const d = getDistanceMeters(40.8165, -73.8860, 40.8175, -73.8860);
    expect(d).toBeGreaterThan(100);
    expect(d).toBeLessThan(120);
  });

  it("accepts valid tree placement on open permeable/plaza area", () => {
    const res = validateInterventionPlacement(
      "tree",
      { lng: -73.8861, lat: 40.8166 },
      { x: 200, y: 200 },
      null,
      [],
      mockAsset
    );
    expect(res.valid).toBe(true);
    expect(res.reason).toBeUndefined();
  });

  it("rejects tree placement too close to an existing tree (< 4m spacing)", () => {
    const existing: PlacedIntervention[] = [
      {
        id: "tree-1",
        type: "tree",
        latitude: 40.81650,
        longitude: -73.88600,
        created_at: Date.now(),
      },
    ];

    // Clicked 1 meter away
    const res = validateInterventionPlacement(
      "tree",
      { lng: -73.88601, lat: 40.81651 },
      { x: 200, y: 200 },
      null,
      existing,
      mockAsset
    );

    expect(res.valid).toBe(false);
    expect(res.reason).toContain("too close to an existing tree");
  });

  it("allows tree placement with adequate spacing (>= 4m spacing)", () => {
    const existing: PlacedIntervention[] = [
      {
        id: "tree-1",
        type: "tree",
        latitude: 40.81650,
        longitude: -73.88600,
        created_at: Date.now(),
      },
    ];

    // Clicked ~12 meters away
    const res = validateInterventionPlacement(
      "tree",
      { lng: -73.88615, lat: 40.81650 },
      { x: 250, y: 200 },
      null,
      existing,
      mockAsset
    );

    expect(res.valid).toBe(true);
  });

  it("rejects tree placement when cursor intersects a building layer", () => {
    const mockMap = {
      queryRenderedFeatures: () => [
        {
          layer: { id: "building-3d" },
          properties: { class: "building", type: "commercial" },
        },
      ],
    };

    const res = validateInterventionPlacement(
      "tree",
      { lng: -73.8861, lat: 40.8166 },
      { x: 200, y: 200 },
      mockMap,
      [],
      mockAsset
    );

    expect(res.valid).toBe(false);
    expect(res.reason).toContain("building");
  });

  it("rejects tree placement when cursor intersects a road/highway layer", () => {
    const mockMap = {
      queryRenderedFeatures: () => [
        {
          layer: { id: "road_primary" },
          properties: { class: "primary", type: "road" },
        },
      ],
    };

    const res = validateInterventionPlacement(
      "tree",
      { lng: -73.8861, lat: 40.8166 },
      { x: 200, y: 200 },
      mockMap,
      [],
      mockAsset
    );

    expect(res.valid).toBe(false);
    expect(res.reason).toContain("road");
  });
});

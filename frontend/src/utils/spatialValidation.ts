import { PlacedIntervention, PublicAsset } from "../types";

export interface PlacementValidationResult {
  valid: boolean;
  reason?: string;
}

/**
 * Calculate distance in meters between two lat/lng coordinates (Haversine formula).
 */
export function getDistanceMeters(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  const R = 6371000; // Earth radius in meters
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

/**
 * Validates whether an intervention can be placed at the clicked coordinate.
 * Rejects placement on buildings, roadways, or within minimum spacing of existing interventions.
 */
export function validateInterventionPlacement(
  toolType: "tree" | "shade" | "reflective",
  lngLat: { lng: number; lat: number },
  point?: { x: number; y: number } | null,
  map?: any,
  existingInterventions: PlacedIntervention[] = [],
  targetAsset?: PublicAsset | null
): PlacementValidationResult {
  // 1. Spacing & Duplicate Stacking Checks
  const MIN_TREE_SPACING_METERS = 4.0; // Minimum 4m spacing between trees for healthy root/canopy space
  const MIN_SHADE_SPACING_METERS = 8.0; // Minimum 8m spacing between shade structures

  for (const item of existingInterventions) {
    const distMeters = getDistanceMeters(
      lngLat.lat,
      lngLat.lng,
      item.latitude,
      item.longitude
    );

    if (toolType === "tree" && item.type === "tree" && distMeters < MIN_TREE_SPACING_METERS) {
      return {
        valid: false,
        reason: "Location is too close to an existing tree (minimum 4m spacing required for root and canopy growth).",
      };
    }

    if (toolType === "shade" && item.type === "shade" && distMeters < MIN_SHADE_SPACING_METERS) {
      return {
        valid: false,
        reason: "Location is too close to an existing shade structure (minimum 8m spacing required).",
      };
    }
  }

  // 2. Query MapLibre Rendered Features Under Cursor if Map instance is available
  if (map && point && typeof map.queryRenderedFeatures === "function") {
    try {
      const bbox: [{ x: number; y: number }, { x: number; y: number }] = [
        { x: point.x - 4, y: point.y - 4 },
        { x: point.x + 4, y: point.y + 4 },
      ];
      const features = map.queryRenderedFeatures(bbox) || [];

      for (const feat of features) {
        const layerId = (feat.layer?.id || "").toLowerCase();
        const sourceLayer = (feat.sourceLayer || "").toLowerCase();
        const props = feat.properties || {};
        const fClass = String(props.class || props.type || props.kind || "").toLowerCase();

        // Building detection
        const isBuilding =
          layerId.includes("building") ||
          sourceLayer.includes("building") ||
          fClass.includes("building") ||
          fClass === "roof" ||
          fClass === "commercial" ||
          fClass === "residential";

        if (isBuilding && toolType === "tree") {
          return {
            valid: false,
            reason: "Trees cannot be planted on building footprints.",
          };
        }

        // Roadway / highway / vehicle lane detection
        const isRoad =
          layerId.includes("road") ||
          layerId.includes("highway") ||
          layerId.includes("street") ||
          layerId.includes("motorway") ||
          layerId.includes("tunnel") ||
          layerId.includes("bridge") ||
          sourceLayer.includes("road") ||
          sourceLayer.includes("transportation") ||
          ["motorway", "trunk", "primary", "secondary", "highway", "road", "street", "motorway_link"].includes(fClass);

        if (isRoad && toolType === "tree") {
          return {
            valid: false,
            reason: "Trees cannot be planted on active roadways or vehicle lanes.",
          };
        }
      }
    } catch {
      // Non-blocking query fallback
    }
  }

  // 3. Asset Boundary Distance Check (ensure not clicked miles away from study target)
  if (targetAsset) {
    const distToAsset = getDistanceMeters(
      lngLat.lat,
      lngLat.lng,
      targetAsset.latitude,
      targetAsset.longitude
    );
    const maxAllowedDistMeters = Math.max(400, Math.sqrt(targetAsset.footprint_m2) * 5);
    if (distToAsset > maxAllowedDistMeters && distToAsset > 600) {
      return {
        valid: false,
        reason: "Location is outside the target municipal planning zone.",
      };
    }
  }

  return { valid: true };
}

import { describe, expect, it, vi, beforeEach } from "vitest";
import { clearApiCache, fetchAssets, fetchHeatmapLayer } from "../services/api";

describe("Frontend In-Memory API Cache", () => {
  beforeEach(() => {
    clearApiCache();
    vi.restoreAllMocks();
  });

  it("caches fetchAssets responses and avoids duplicate network requests", async () => {
    const mockAssets = [{ asset_id: "test-1", name: "Test Park" }];
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => mockAssets,
    } as Response);

    const firstCall = await fetchAssets("nyc");
    expect(firstCall).toEqual(mockAssets);
    expect(fetchSpy).toHaveBeenCalledTimes(1);

    const secondCall = await fetchAssets("nyc");
    expect(secondCall).toEqual(mockAssets);
    expect(fetchSpy).toHaveBeenCalledTimes(1); // Cached!
  });

  it("caches fetchHeatmapLayer responses across layer toggles", async () => {
    const mockGeoJSON = { type: "FeatureCollection", features: [] };
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => mockGeoJSON,
    } as Response);

    const firstCall = await fetchHeatmapLayer("tcm_peak", "nyc");
    expect(firstCall).toEqual(mockGeoJSON);
    expect(fetchSpy).toHaveBeenCalledTimes(1);

    const secondCall = await fetchHeatmapLayer("tcm_peak", "nyc");
    expect(secondCall).toEqual(mockGeoJSON);
    expect(fetchSpy).toHaveBeenCalledTimes(1); // Cached!
  });
});

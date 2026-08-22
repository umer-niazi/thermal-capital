# Data Pipeline & API Integration Architecture

**Project:** Thermal Capital — FortyGuard Hackathon 2026  
**Document:** End-to-End Data Pipeline, API Contracts, Caching & Spatial Orchestration  
**Target Geography:** Phoenix Metropolitan Area, Arizona  
**Date:** 2026-08-18  

---

## 1. Pipeline Overview

Thermal Site Intelligence connects directly to FortyGuard's async API to evaluate and rank candidate infrastructure sites. To optimize performance and API credit consumption, the platform uses a **2-stage tiered pipeline** with a persistent local cache.

```
Candidate Site Polygons (2–10 parcels)
               │
               ▼
   [build_unified_aoi] ──> Single Convex Hull AOI (+400m buffer)
               │
               ├─────────────────────────────────────────────┐
               ▼                                             ▼
 [POST /v1/heatmap (TCM)]                      [SQLite Cache Store]
 [POST /v1/heatmap (Exceedance)]               (Deterministic SHA-256)
 [POST /v1/heatmap (Persistence)]
               │ (Shared AOI fetched once)
               ▼
 [clip_heatmap_to_site] ──> Area-weighted parcel temperatures & durations
               │
               ▼
 [Stage 1: Initial Risk Ranking] ──> Preliminary Ranking
               │
               ▼
 [Stage 2: Top-N Selective Enrichment] (Centroids of Top Candidates)
               ├────────────────────────────┤
               ▼                            ▼
 [POST /v1/env_params]            [POST /v1/satellite]
 (Wet-bulb, hot-hour HI)          (Impervious / Vegetation %)
               │                            │
               └────────────┬───────────────┘
                            ▼
           [Full 5-Component Risk Scoring]
           [Cooling Burden Indicators]
           [Structured JSON / CLI Report]
```

---

## 2. FortyGuard Endpoints & Request Specifications

### 2.1 TCM Heatmap (Daily Aggregate)
- **Endpoint:** `POST /v1/heatmap`
- **Purpose:** Baseline daily peak, mean, overnight min, and diurnal swing.
- **Payload:**
  ```json
  {
    "polygon_aoi": { "type": "FeatureCollection", "features": [...] },
    "date_time": { "start_date": "2024-07-15", "filter_type": 3 },
    "granularity": 100,
    "analytic_type": "tcm"
  }
  ```
- **Authoritative Data Fields:**
  - `result.map_data.features[].properties.max_temperature` (Peak dry-bulb °C)
  - `result.map_data.features[].properties.average_temperature` (Mean dry-bulb °C)
  - `result.map_data.features[].properties.min_temperature` (Overnight low °C)
- **Critical Rule:** `stats_data.temperature_stats.maximum` in `filter_type=3` summarizes `average_temperature` distribution across tiles, NOT peak temperatures. Peak temperatures MUST be extracted directly from `features[].properties.max_temperature`.

### 2.2 Exceedance Heatmap (Multi-Day Duration)
- **Endpoint:** `POST /v1/heatmap`
- **Purpose:** Total cumulative hours above $40.0^\circ\text{C}$ ($104^\circ\text{F}$) severe chiller strain threshold over heatwave window.
- **Payload:**
  ```json
  {
    "polygon_aoi": { "type": "FeatureCollection", "features": [...] },
    "date_time": { "start_date": "2024-07-15", "end_date": "2024-07-21", "filter_type": 4 },
    "granularity": 100,
    "analytic_type": "exceedance",
    "threshold": 40.0,
    "direction": "above"
  }
  ```
- **Authoritative Data Fields:**
  - `result.map_data.features[].properties.value` (Measured hours above threshold)

### 2.3 Persistence Heatmap (Multi-Day Unbroken Run)
- **Endpoint:** `POST /v1/heatmap`
- **Purpose:** Longest continuous unbroken run above $35.0^\circ\text{C}$ ($95^\circ\text{F}$) without overnight temperature relief.
- **Payload:**
  ```json
  {
    "polygon_aoi": { "type": "FeatureCollection", "features": [...] },
    "date_time": { "start_date": "2024-07-15", "end_date": "2024-07-21", "filter_type": 4 },
    "granularity": 100,
    "analytic_type": "persistence",
    "threshold": 35.0,
    "direction": "above"
  }
  ```
- **Authoritative Data Fields:**
  - `result.map_data.features[].properties.value` (Longest unbroken continuous run in hours)

### 2.4 Environmental Parameters (Point Time-Series)
- **Endpoint:** `POST /v1/env_params`
- **Purpose:** Point-level wet-bulb temperature distribution, apparent temperature curve, and air quality at candidate site centroid.
- **Payload:**
  ```json
  {
    "latitude": 33.4460,
    "longitude": -112.0745,
    "temperature": 40.48,
    "date_time": { "start_date": "2024-07-15", "filter_type": 3 },
    "analysis": [
      "apparent_temperature_celsius",
      "wet_bulb_temperature_celsius",
      "relative_humidity_percent",
      "heat_index_celsius",
      "air_quality:idx",
      "solar_irradiance"
    ]
  }
  ```
- **API Quirk & Protection Strategy:**
  - The endpoint applies the supplied `temperature` anchor across all 24 hours while varying relative humidity, causing `heat_index_celsius` to artificially peak at 02:00–05:00 AM (e.g. $56.0^\circ\text{C}$ at 85% RH).
  - **Resolution:**
    1. We find the index of maximum `apparent_temperature_celsius` (afternoon peak, e.g. 15:00).
    2. We evaluate `heat_index_celsius` strictly AT that afternoon hot hour ($40.4^\circ\text{C}$).
    3. We use `wet_bulb_temperature_celsius` for evaporative cooling tower feasibility ($23.8^\circ\text{C}$).

### 2.5 Satellite Land-Cover Segmentation
- **Endpoint:** `POST /v1/satellite`
- **Purpose:** Surface composition analysis (impervious vs. vegetation vs. bare ground).
- **Payload:**
  ```json
  {
    "sat": { "latitude": 33.4460, "longitude": -112.0745 },
    "date_time": { "start_date": "2024-07-15", "filter_type": 3 },
    "granularity": 100
  }
  ```
- **Normalized Aggregation:**
  - `impervious_pct` = `building` + `road, route` + `sidewalk, pavement` + `car` + `truck` + `fence`
  - `vegetation_pct` = `tree` + `grass` + `plant` + `vegetation`
  - `bare_ground_pct` = `earth, ground` + `soil` + `sand`

---

## 3. Spatial Clipping Methodology

Industrial parcels (e.g., 30–50 acres) span multiple 60/80/100m grid tiles. The platform implements rigorous area-weighted spatial clipping (`backend.services.geo`):

1. **Intersection Calculation:** For each tile $i$ in `map_data.features`:
   $$\text{Area}_i = \text{area}(\text{Tile}_i \cap \text{SitePolygon})$$
2. **Area-Weighted Temperature / Duration:**
   $$T_{\text{site}} = \frac{\sum_{i} \text{Area}_i \cdot T_i}{\sum_{i} \text{Area}_i}$$
3. **Boundary Tile Coverage:**
   $$\text{Coverage}_{\%} = \min\left(100.0, \frac{\sum_{i} \text{Area}_i}{\text{area}(\text{SitePolygon})} \times 100.0\right)$$
4. **Coverage Warning:** If $\text{Coverage}_{\%} < 85.0\%$, the result exposes an explicit coverage warning indicating the parcel extends beyond the analyzed heatmap boundary.

---

## 4. Persistent SQLite Cache Architecture

All API requests are intercepted by `CachedFortyGuardClient` (`backend/cache/`):

- **Deterministic SHA-256 Hashing:** Request endpoints and canonicalized JSON parameters are hashed into a 64-character hex key.
- **Zero Redundant Calls:**
  - Cache Hit: Returns parsed JSON in $< 5\text{ms}$ with zero API credit consumption.
  - Cache Miss: Executes live async poll, persists raw response to `data/cache/api_cache.db`, and exports raw audit files to `data/probes/`.
- **Thread & Process Safe:** Configured with SQLite `WAL` mode and `PRAGMA synchronous=NORMAL`.
- **Security:** Strips API keys and secret tokens prior to key hashing.

---

## 5. Multi-Site Shared AOI Optimization

When screening $N$ candidate parcels ($2 \le N \le 10$):
1. The platform calculates the geometric **convex hull** of all candidate polygons and adds a **400m buffer**.
2. **1x TCM + 1x Exceedance + 1x Persistence** heatmap is fetched for the entire cluster once, instead of $3 \times N$ separate API calls.
3. Each candidate parcel is clipped independently against the shared layer.
4. Point endpoints (`/v1/env_params` and `/v1/satellite`) are selectively called only for the top-ranked candidates (`enrichment_top_n=1` or `3`).
5. **Credit Savings:** Reduces API credit usage by up to **80%** compared to naive per-site querying while placing all candidates on an identical meteorological baseline.

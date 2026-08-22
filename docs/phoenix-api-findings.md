# Phoenix Live API Probe Findings

**Date of Execution:** 2026-08-18  
**API Endpoint Tested:** `POST /v1/heatmap` (TCM daily aggregate)  
**Study Date:** `2024-07-15` (Peak Summer)  
**Target Region:** Central Phoenix Industrial Corridor, Arizona (`33.4400°N` to `33.4550°N`, `-112.0850°W` to `-112.0650°W`)  
**Resolution / Granularity:** 100 meters  
**Activity ID:** `15f58cd0-0cac-4c65-99bd-06ad11d78da0`  

---

## 1. Execution Summary

A live API probe was executed via the official `FortyGuardClient` using the configured `FORTYGUARD_API_KEY`. The request completed asynchronously in ~15 seconds across 4 polling cycles (`processing` $\rightarrow$ `completed`) without error.

---

## 2. Actual Response Schema

The endpoint returned a top-level dictionary containing `activity_id` and `result`:

```json
{
  "activity_id": "15f58cd0-0cac-4c65-99bd-06ad11d78da0",
  "result": {
    "map_data": {
      "type": "FeatureCollection",
      "features": [ ... ]
    },
    "stats_data": {
      "temperature_stats": { ... },
      "overall_temperature_distribution": [ ... ],
      "normal_temperature_distribution": { "x_axis": [ ... ], "y_axis": [ ... ] },
      "temperature_frequency": { "x_axis": [ ... ], "y_axis": [ ... ] }
    }
  }
}
```

### 2.1 Feature Tile Schema (`map_data.features[]`)
Total tiles returned: **323 cells** covering a bounding box of `[-112.08552, 33.43982]` to `[-112.06497, 33.45513]`.

Each feature strictly contains:
- `id`: String representation of integer tile index (`"0"`, `"1"`, ...)
- `type`: `"Feature"`
- `geometry`: Polygon with closed 5-coordinate ring (`[[[lon, lat], ...]]`)
- `properties`:
  - `tile_id`: Integer (`0` to `322`)
  - `average_temperature`: Float (°C) — Daily 24-hour mean
  - `min_temperature`: Float (°C) — Daily overnight low
  - `max_temperature`: Float (°C) — Daily afternoon peak

Representative sample tile:
```json
{
  "id": "0",
  "type": "Feature",
  "properties": {
    "tile_id": 0,
    "average_temperature": 35.9187,
    "min_temperature": 29.1065,
    "max_temperature": 40.4933
  },
  "geometry": {
    "type": "Polygon",
    "coordinates": [
      [
        [-112.08533816559384, 33.43982464166299],
        [-112.0842621948719, 33.4398322692225],
        [-112.08426998634125, 33.4407352329388],
        [-112.08534596324317, 33.44072760528436],
        [-112.08533816559384, 33.43982464166299]
      ]
    ]
  }
}
```

---

## 3. Verified Quantitative Results (Phoenix Summer 2024-07-15)

All values are in native **Degrees Celsius** (with Fahrenheit conversions shown in brackets):

| Metric | Minimum | Mean | Maximum | Spread ($\Delta$) |
|---|---|---|---|---|
| **Daily Peak ($T_{\text{max}}$)** | **40.46 °C** (104.83 °F) | **40.49 °C** (104.88 °F) | **40.54 °C** (104.97 °F) | **0.08 °C** (0.14 °F) |
| **Daily Average ($T_{\text{avg}}$)** | **35.73 °C** (96.31 °F) | **36.01 °C** (96.82 °F) | **36.23 °C** (97.21 °F) | **0.50 °C** (0.90 °F) |
| **Daily Overnight Min ($T_{\text{min}}$)** | **29.08 °C** (84.34 °F) | **29.33 °C** (84.79 °F) | **29.78 °C** (85.60 °F) | **0.70 °C** (1.26 °F) |
| **Diurnal Swing ($T_{\text{max}} - T_{\text{min}}$)** | **10.68 °C** (19.22 °F) | **11.16 °C** (20.09 °F) | **11.41 °C** (20.54 °F) | **0.73 °C** (1.31 °F) |

---

## 4. Key Discrepancies & Critical Architectural Takeaways

### 4.1 `stats_data.temperature_stats` Reflects `average_temperature`, NOT `max_temperature`
- **Observed Behavior:**
  ```json
  "temperature_stats": {
    "minimum": 35.7329,
    "maximum": 36.232,
    "mean": 36.00826160990712,
    "standard_deviation": 0.12704650398101358
  }
  ```
  These values match the min, max, and mean of `average_temperature` exactly ($35.73^\circ\text{C} \dots 36.23^\circ\text{C}$). They do **NOT** represent the peak temperature ($40.49^\circ\text{C}$).
- **Architectural Impact:**
  Our backend scoring engine **must aggregate peak temperature directly from `features[].properties.max_temperature`** rather than relying on `stats_data.temperature_stats.maximum`. Reading `stats_data` directly would under-report design peak temperature by $\sim 4.5^\circ\text{C}$ ($\sim 8.1^\circ\text{F}$).

### 4.2 Snapshot Peak Temperature is Nearly Flat at Parcel Scale
- Across the entire $\sim 3\text{ km}^2$ study box, peak temperature varies by only **$0.08^\circ\text{C}$ ($0.14^\circ\text{F}$)**.
- **Architectural Impact:**
  In Phoenix industrial corridors, candidate sites within a submarket cannot be differentiated by snapshot peak temperature alone. The scoring engine **must prioritize exposure duration (`exceedance` hours) and overnight recovery failure (`persistence` hours)** to deliver meaningful, defensible site rankings.

### 4.3 Severe Overnight Baseline in Phoenix
- Overnight low temperatures never dropped below **$29.08^\circ\text{C}$ ($84.34^\circ\text{F}$)**, with some tiles remaining above **$29.78^\circ\text{C}$ ($85.60^\circ\text{F}$)**.
- **Architectural Impact:**
  This directly validates our data center value proposition: continuous high thermal mass saturation prevents nighttime chiller efficiency recovery and electrical transformer cooling, amplifying the value of persistence and cooling-burden analysis.

---

## 5. Artifact Verification

- Raw API JSON response saved: `data/probes/phoenix_tcm_2024-07-15.json`
- Extracted GeoJSON map layer saved: `data/probes/phoenix_tcm_2024-07-15.geojson`
- Verified that `data/` and probe files remain untracked by git via `.gitignore`.

# FortyGuard Texas Feasibility & Data-Quality Coverage Probe

**Document Version:** 1.0.0  
**Study Date Window:** July 15, 2024 – July 21, 2024 (7-Day Summer Window)  
**Resolution:** 100-metre Heatmap Grid  
**API Key Status:** Live Probe Executed with Zero Unapproved Waste (100% Cached in SQLite)  

---

## Executive Summary & Verdict

### Final Recommendation: **GO (or MULTI-REGIONAL HYBRID)**

The FortyGuard Temperature API exhibits **100% data availability, excellent spatial resolution, and strong thermal differentiation** across Texas major metropolitan data center submarkets.

The probe conclusively proves that FortyGuard data can power a multi-market Texas due diligence platform that clearly separates **HOT + HUMID coastal environments (Houston)** from **HOT + CONTINENTAL logistics corridors (DFW)** and **HOT + ARID high-altitude desert plateaus (El Paso)**.

| Climate Dimension | Phoenix (Current Baseline) | Houston (`TX-HOU-01`) | DFW (`TX-DFW-01`) | Austin (`TX-AUS-01`) | El Paso (`TX-ELP-01`) |
|---|---|---|---|---|---|
| **Peak Ambient Dry-Bulb (°C / °F)** | **40.48°C** (104.9°F) | **34.28°C** (93.7°F) | **37.38°C** (99.3°F) | **35.43°C** (95.8°F) | **36.13°C** (97.0°F) |
| **Peak Wet-Bulb (°C / °F)** | **23.80°C** (74.8°F) | **26.30°C** (79.3°F) | **25.40°C** (77.7°F) | **25.30°C** (77.5°F) | **20.20°C** (68.4°F) |
| **Hot-Hour Heat Index (°C / °F)** | **40.40°C** (104.7°F) | **43.50°C** (110.3°F) | **38.80°C** (101.8°F) | **39.40°C** (102.9°F) | **33.90°C** (93.0°F) |
| **Overnight Min Floor (°C / °F)** | **29.32°C** (84.8°F) | **27.73°C** (81.9°F) | **25.89°C** (78.6°F) | **24.92°C** (76.9°F) | **23.92°C** (75.1°F) |
| **Diurnal Swing (Δ °C)** | **11.16°C** | **6.54°C** (Muffled) | **11.50°C** | **10.51°C** | **12.20°C** (Wide) |
| **Hours >35°C Unbroken Persistence** | **8.0h** | **0.0h** | **3.0h** | **3.2h** | **6.0h** |
| **Hours >40°C Exceedance** | **53.0h** | **0.0h** | **0.0h** | **0.0h** | **0.0h** |
| **Cooling Degree Hours (>25°C Base)** | **1,852 CDH** | **899.7 CDH** | **1,070.6 CDH** | **838.2 CDH** | **929.6 CDH** |

---

## 1. Probe Methodology & API Efficiency

### Evaluated Regions & Candidates
1. **Dallas-Fort Worth (`TX-DFW-01`)**: Alliance Texas Logistics & Technology Park ($4.29\text{ km}^2$, 427 tiles)
2. **Houston (`TX-HOU-01`)**: Houston Ship Channel Industrial Logistics Hub ($5.14\text{ km}^2$, 414 tiles)
3. **Austin (`TX-AUS-01`)**: Austin Silicon Hills Semiconductor Campus ($5.13\text{ km}^2$, 488 tiles)
4. **El Paso (`TX-ELP-01`)**: El Paso Desert Borderplex Industrial Gateway ($5.07\text{ km}^2$, 500 tiles)

### API Requests & Credit Audit
- **TCM Heatmaps (`/v1/heatmap`, filter_type=3)**: 4 requests (1 per region)
- **Exceedance Heatmaps (`/v1/heatmap`, filter_type=4, >40°C)**: 4 requests (1 per region)
- **Persistence Heatmaps (`/v1/heatmap`, filter_type=4, >35°C)**: 4 requests (1 per region)
- **Environmental Parameters (`/v1/env_params`, filter_type=3)**: 4 point requests (1 per region centroid)
- **Total API Activities Executed**: 16 activities.
- **All responses saved to SQLite cache and audit artifacts** (`data/probes/texas_*.json`). Repeated runs consume 0 API credits.

---

## 2. Key Scientific Findings & Differentiators

### A. Houston Humidity Test (Phase 6)
- **Evaporative Economizer Failure**: Houston's peak wet-bulb reaches **$26.30^\circ\text{C}$ ($79.3^\circ\text{F}$)**, which is the highest in the dataset and well above the ASHRAE TC 9.9 critical boundary of $\sim 24^\circ\text{C}$.
- **Apparent Temperature Spike**: Despite a moderate dry-bulb temperature ($34.28^\circ\text{C}$), high maritime relative humidity pushes the peak afternoon Heat Index to **$43.50^\circ\text{C}$ ($110.3^\circ\text{F}$)**.
- **Thermal Inertia & Overnight Retention**: Houston retains heat heavily at night with a minimum of **$27.73^\circ\text{C}$** and a muffled diurnal swing of only **$6.54^\circ\text{C}$**, preventing transformer and electrical yard thermal recovery.

### B. El Paso vs. Houston Contrast (Phase 7)
- **Dry Heat vs. Humid Heat**:
  - El Paso daytime dry-bulb reaches **$36.13^\circ\text{C}$** with **$6.0\text{ hours}$ unbroken $>35^\circ\text{C}$** persistence.
  - BUT El Paso's peak wet-bulb is only **$20.20^\circ\text{C}$** — a **$6.10^\circ\text{C}$ advantage** over Houston!
  - In El Paso, evaporative economizers operate with $>3.8^\circ\text{C}$ of safety headroom, significantly lowering electrical cooling consumption.
  - El Paso's overnight minimum falls to **$23.92^\circ\text{C}$** (the lowest in Texas) with a wide **$12.20^\circ\text{C}$ diurnal swing**, allowing nocturnal purging.

### C. DFW vs. Austin Contrast
- **DFW (`TX-DFW-01`)**: Has the highest daytime dry-bulb peak in Texas (**$37.38^\circ\text{C}$**) and highest Cooling Degree Hours (**$1,070.6\text{ CDH}$**), representing substantial annual chiller electrical draw.
- **Austin (`TX-AUS-01`)**: Shows lower dry-bulb peak (**$35.43^\circ\text{C}$**) and lower CDH (**$838.2\text{ CDH}$**), but shares the elevated Central Texas wet-bulb exposure (**$25.30^\circ\text{C}$**).

---

## 3. Data Integrity & Schema Findings
1. **`stats_data` Pitfall Confirmed**: In all Texas TCM responses, `stats_data.temperature_stats.maximum` returns the maximum of the *average* temperatures ($31.53^\circ\text{C}$ for DFW) rather than the true max ambient temperature ($38.01^\circ\text{C}$). Our pipeline's direct extraction from `features[].properties.max_temperature` correctly avoided this trap.
2. **Houston Hot-Hour Protection**: Our implemented afternoon window filter correctly resolved true hot-hour heat index at 13:00 ($43.5^\circ\text{C}$) and eliminated nocturnal 04:00 relative humidity calculation artifacts.
3. **Threshold Calibration Insight**: In Texas, ambient temperatures rarely cross $40.0^\circ\text{C}$ (unlike Phoenix where it occurs daily during summer heatwaves). For Texas markets, exceedance threshold should be calibrated to **$37.0^\circ\text{C}$ or $38.0^\circ\text{C}$**, and wet-bulb / apparent heat index should carry higher weighting in the cooling burden module.

---

## 4. Texas Candidate Portfolio Structure (10 Sites)

The 10 representative candidate sites in `data/probes/texas_candidate_sites.json` provide geographic and archetypal diversity:
- `TX-DFW-01`: DFW North / Alliance Logistics ($65\text{ acres}$, $90\text{ MW}$)
- `TX-DFW-02`: DFW South / Midlothian Hyperscale ($80\text{ acres}$, $120\text{ MW}$)
- `TX-HOU-01`: East Houston / Ship Channel Petrochemical ($70\text{ acres}$, $80\text{ MW}$)
- `TX-HOU-02`: West Houston / Katy I-10 Technology ($55\text{ acres}$, $75\text{ MW}$)
- `TX-AUS-01`: East Austin / Silicon Hills Semiconductor ($60\text{ acres}$, $85\text{ MW}$)
- `TX-SAT-01`: West San Antonio / Westover Hills Enterprise ($50\text{ acres}$, $70\text{ MW}$)
- `TX-ELP-01`: East El Paso / Desert Borderplex ($90\text{ acres}$, $110\text{ MW}$)
- `TX-LUB-01`: Lubbock High Plains Renewable ($110\text{ acres}$, $140\text{ MW}$)
- `TX-WAC-01`: Central Texas / Waco I-35 Logistics ($60\text{ acres}$, $65\text{ MW}$)
- `TX-CRP-01`: Corpus Christi Gulf Marine Terminal ($75\text{ acres}$, $80\text{ MW}$)

# Thermal Risk Scoring Model Specification

**Project:** Thermal Capital — FortyGuard Hackathon 2026  
**Module:** `backend.services.thermal_scoring` / `backend.services.scoring_config`  
**Target Domain:** Critical Infrastructure & Data Center Site Due Diligence  
**Geographic Coverage:** Greater Texas Multi-Market Portfolio & Phoenix Baseline  
**Status:** Regionally Calibrated Multi-Dimensional Analytical Model  

---

## 1. Executive Summary & Problem Statement

In industrial infrastructure site selection—particularly for hyperscale and enterprise data centers—evaluating microclimate thermal risk is essential. Ambient thermal conditions dictate HVAC chiller electrical power consumption (PUE penalty), economizer operating hours, cooling water evaporation rates, and critical electrical equipment stress (transformers and backup generators).

However, traditional site evaluations rely either on regional airport weather station data (which ignores local microclimates and urban heat island effects) or single-moment peak temperature snapshots.

### Why Regional Calibration is Essential
Climate regimes impose fundamentally different failure modes on mission-critical infrastructure:
1. **Desert Arid Regimes (e.g. Phoenix, Arizona; El Paso, Texas):**
   - Daytime dry-bulb temperature is extremely high ($>40^\circ\text{C}$ / $104^\circ\text{F}$), stressing chiller condensing circuits.
   - Wet-bulb temperatures remain low ($<21^\circ\text{C}$ / $70^\circ\text{F}$), providing abundant headroom for evaporative cooling and adiabatic pre-cooling.
   - Large diurnal swings ($11\text{--}18^\circ\text{C}$) enable rapid radiative nocturnal purging.
2. **Humid Maritime & Subtropical Regimes (e.g. Houston, Texas; DFW; Austin):**
   - Ambient dry-bulb peaks between $34^\circ\text{C}$ and $37.5^\circ\text{C}$ (producing zero hours $>40^\circ\text{C}$).
   - **Wet-bulb temperature reaches $26.3^\circ\text{C}$ ($79.3^\circ\text{F}$)**, which **exceeds standard ASHRAE water-side economizer limits ($\sim 24^\circ\text{C}$)** and severely curtails evaporative cooling efficiency.
   - Afternoon Heat Index climbs to **$43.5^\circ\text{C}$ ($110.3^\circ\text{F}$)**.
   - Constricted diurnal swing ($6.5^\circ\text{C}$) and high overnight minimums ($27.7^\circ\text{C}$) prevent nocturnal electrical transformer yard cooldown.

To avoid artificial score compression while preserving physical audibility, Thermal Site Intelligence implements **Regional Scoring Profiles** in `ScoringConfig`.

---

## 2. Regional Scoring Profiles & Normalization Ranges

The model supports two standard regional calibration profiles:
- `texas_regional_infrastructure` (Default for Texas Multi-Market Portfolio)
- `phoenix_desert_extreme` (Baseline for Phoenix)

### Regional Normalization Parameter Comparison

| Scoring Component | Weight ($w_i$) | Texas Profile (`texas_regional_infrastructure`) | Phoenix Profile (`phoenix_desert_extreme`) | Data Source |
|---|---|---|---|---|
| **1. Extreme Heat Exposure** | **30%** | Exceedance ($0\text{--}35\text{h}$) or Heat Index ($34\text{--}45^\circ\text{C}$) or Peak Temp ($33\text{--}40^\circ\text{C}$) | Exceedance ($0\text{--}48\text{h}$) or Peak Temp ($38\text{--}47^\circ\text{C}$) | FortyGuard Exceedance / Env Params (`peak_heat_index_c`) / TCM |
| **2. Heat Exceedance Duration** | **25%** | Exceedance Share ($0\text{--}25\%$) or CDH ($600\text{--}1,400\text{ CDH}$) or Mean Temp ($28\text{--}34^\circ\text{C}$) | Exceedance Share ($0\text{--}35\%$) or CDH ($1,200\text{--}2,200\text{ CDH}$) or Mean Temp ($32\text{--}38^\circ\text{C}$) | FortyGuard Exceedance / Derived Cooling Burden / TCM |
| **3. Heat Persistence & Recovery** | **20%** | Unbroken Run $>35^\circ\text{C}$ ($0\text{--}8\text{h}$) or Swing Deficit ($14^\circ\text{C} \to 5^\circ\text{C}$) | Unbroken Run $>35^\circ\text{C}$ ($0\text{--}16\text{h}$) or Swing Deficit ($18^\circ\text{C} \to 6^\circ\text{C}$) | FortyGuard Persistence / TCM Diurnal Swing |
| **4. Wet-Bulb & Cooling Plant Burden** | **15%** | Peak Wet-Bulb ($18.0\text{--}26.5^\circ\text{C}$) *(ASHRAE economizer limit ~24°C)* | Peak Wet-Bulb ($16.0\text{--}26.0^\circ\text{C}$) | FortyGuard `/v1/env_params` (`peak_wet_bulb_temperature_c`) |
| **5. Overnight Thermal Retention** | **10%** | Overnight Low Floor ($22.0\text{--}28.5^\circ\text{C}$) | Overnight Low Floor ($22.0\text{--}32.0^\circ\text{C}$) | FortyGuard TCM Heatmap (`min_temperature`) |

---

## 3. Dual Score Architecture: Absolute vs Portfolio Rank Score

To serve both engineering facility design and corporate executive decision-making, the platform provides two complementary scores:

1. **Absolute Risk Score ($0 \text{ to } 100$):**
   - Measures raw thermodynamic stress against national ASHRAE engineering benchmarks.
   - Directly auditable: a score of 48.2 in Houston reflects severe wet-bulb load and overnight thermal retention even without $>40^\circ\text{C}$ dry-bulb exceedance.
2. **Portfolio Rank Score ($0 \text{ to } 100$):**
   - Normalizes candidate scores relative to the active candidate portfolio:
     $$\text{Portfolio Score} = \frac{\text{Score} - \text{Score}_{\text{min}}}{\text{Score}_{\text{max}} - \text{Score}_{\text{min}}} \times 100.0$$
   - Rank #1 candidate has Portfolio Score `0.0` (optimal thermal site in the portfolio), while the highest risk site has `100.0`.

---

## 4. Risk Categorization Scale

| Total Score Range | Risk Category | Operational Implication for Critical Infrastructure |
|---|---|---|
| **$0.0 \le \text{Score} < 25.0$** | **Low** | Favorable microclimate; standard cooling design margins are fully adequate; long economizer free-cooling hours. |
| **$25.0 \le \text{Score} < 50.0$** | **Moderate** | Moderate thermal strain; typical summer cooling derating required; partial water-side economizer curtailment. |
| **$50.0 \le \text{Score} < 70.0$** | **High** | Sustained thermal burden; air-cooled chiller derating and elevated water consumption expected. |
| **$70.0 \le \text{Score} < 85.0$** | **Severe** | Severe continuous heat; nighttime cooling recovery is impaired; economizer hours restricted; mitigation recommended. |
| **$85.0 \le \text{Score} \le 100.0$** | **Extreme** | Extreme critical infrastructure risk; near-continuous chiller high-head pressure trip strain; architectural mitigation mandatory. |

# Thermal Capital
**Municipal decision-support and capital planning platform for urban heat mitigation.**

*Built for the **FortyGuard Hackathon 2026**: **Track 1: Resilient Cities & Infrastructure**.*

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.3-61DAFB.svg)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-3178C6.svg)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-5.4-646CFF.svg)](https://vitejs.dev/)
[![Tests](https://img.shields.io/badge/Tests-112%20Passing-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## The Problem & Opportunity

Cities cannot cool every street, transit stop, school, or playground simultaneously. Faced with tight municipal budgets, public-sector leaders must decide:
1. **Where** will cooling capital protect the most vulnerable citizens?
2. **Which** interventions (trees, shade canopies, cool pavement) deliver the most cost-effective thermal relief?
3. **How** can capital allocations be optimized and justified to city councils and grantmakers?

**Thermal Capital** bridges the gap between raw microclimate data and municipal capital allocation:
- **Prioritizes Risk:** Ingests **FortyGuard 100m grid thermal intelligence** across New York City to rank exposed public infrastructure.
- **Simulates Interventions:** Provides an interactive sandbox to model cooling impacts and municipal turnkey costs before spending public funds.
- **Optimizes Budgets:** Runs a deterministic knapsack optimizer to maximize thermal relief and protected citizens within an allocated budget (e.g., \$500,000).
- **Generates Planning Briefs:** Compiles formal, meeting-ready **Heat Adaptation Planning Briefs** for city councils, community boards, and federal grant applications.

---

## 5-Step Planning Workflow

1. **Identify Risk:** Explore city-wide 100m thermal distributions ($T_{\text{peak}}$, $T_{\text{mean}}$, exceedance hours) and review prioritized public assets.
2. **Inspect Asset Footprint:** Drill down into site-level microclimate metrics, land cover (canopy % vs. impervious surface %), and vulnerability drivers.
3. **Intervene & Compare:** Place cooling interventions on the map and immediately compare baseline metrics against modeled outcomes ($\Delta T$ reduction and extreme heat duration cuts).
4. **Optimize Budget:** Set a capital expenditure ceiling to automatically allocate funds across public assets under 4 policy strategies (*Balanced*, *Vulnerable Populations*, *Transit Corridors*, *Maximum Relief*).
5. **Export Planning Brief:** Generate a print-ready briefing document complete with executive narrative, itemized municipal costs, population impact, and methodology citations.

---

## Data & Modeling Methodology

Thermal Capital maintains scientific credibility by strictly separating **observed microclimate baseline data** from **modeled scenario estimates**:

### 1. Observed Microclimate Baseline (FortyGuard API)
Physical measurements and model outputs from FortyGuard's 100m spatial grid during the July 15–21, 2024 heatwave:
- Peak ambient dry-bulb temperature ($T_{\text{peak}}$) and 24-hour mean ($T_{\text{mean}}$).
- Cumulative exceedance hours ($> 35.0^{\circ}\text{C}$ / $95.0^{\circ}\text{F}$) and longest continuous extreme heat runs (thermal persistence).
- High-resolution satellite land-cover classification (canopy % vs. impervious surface %).

### 2. Empirical Intervention Response Models
Cooling outputs are deterministic planning estimates based on published municipal and environmental benchmarks:

- **Urban Street Tree Canopy:** $25\,\text{m}^2$ mature crown per tree. Modeled via evapotranspiration and solar radiation interception:
  $$\Delta T = 3.2 \cdot \left(1 - e^{-0.065 \cdot n}\right) \cdot s$$
  *Planning Cost:* **\$3,200/tree** (NYC Parks FY2024 turnkey planting contracts).

- **Engineered Shade Structures:** $100\,\text{m}^2$ direct shade per structure. Modeled via direct shortwave solar radiation blockage:
  $$\Delta T = 2.8 \cdot \left(1 - e^{-0.45 \cdot n}\right)$$
  *Planning Cost:* **\$28,000/structure** (Federal Transit Administration capital benchmarks).

- **Reflective Cool Pavement Coating:** Solar-reflective high-albedo coating ($\ge 0.35$ albedo). Modeled via reduced surface sensible heat flux:
  $$\Delta T = 1.8 \cdot \left(1 - e^{-0.0028 \cdot A}\right)$$
  *Planning Cost:* **\$24/$\text{m}^2$** (EPA Heat Island Reduction Program benchmarks).

- **Synergy & Diminishing Returns:** Because multi-intervention packages operate on the same local air volume, combined cooling is subject to an empirical asymptotic ceiling:
  $$\Delta T_{\text{net}} = \min\left(4.2, 4.2 \cdot \left(1 - e^{-\Delta T_{\text{raw}} / 3.6}\right)\right)$$

> [!NOTE]
> **Planning-Level Estimates:** Modeled cooling effects and itemized costs are empirical planning benchmarks calibrated for comparative scenario analysis and capital prioritization. They are not a substitute for site-specific CFD engineering or stamped construction drawings.

---

## FortyGuard API Integration

Thermal Capital interfaces with the FortyGuard Enterprise API (`https://api.fortyguard.com`):

| Endpoint | Data Provided | Platform Use Case |
|---|---|---|
| `POST /v1/heatmap` | 100m ambient dry-bulb temperature, exceedance ($> 35^{\circ}\text{C}$), persistence | City-wide baseline risk scoring & heat mapping |
| `POST /v1/satellite` | Surface segmentation (tree canopy %, impervious %, buildings) | Baseline land cover analysis & planting feasibility |
| `POST /v1/env_params` | Diurnal time series (heat index, wet-bulb, relative humidity) | Microclimate thermal comfort profiling |

* **Deterministic Caching:** All API responses are persisted via a SHA-256 local SQLite store (`SQLiteCacheStore`), enabling zero-credit, fully offline demonstrations without duplicate billing.

---

## Architecture & Tech Stack

- **Backend:** Python 3.10+, FastAPI, Pydantic v2, Shapely (geospatial operations), SQLite3 (caching), Uvicorn.
- **Frontend:** React 18, TypeScript, Vite, MapLibre GL JS (vector heatmaps & clustering), Tailwind CSS, Lucide React.
- **Testing:** 63 Pytest tests (backend) + 49 Vitest tests across 10 suites (frontend).

```
thermal-capital/
├── backend/
│   ├── api/router.py             # REST endpoints (/assets, /simulate, /optimize, /report, /heatmap)
│   ├── cache/                    # Deterministic SHA-256 SQLite persistent cache
│   ├── models/                   # Schemas (PublicAsset, InterventionConfig, PlanningReport)
│   ├── services/                 # Intervention physics, knapsack optimizer, spatial tiling
│   └── tests/                    # 63 automated Pytest backend tests
├── frontend/src/
│   ├── components/               # MapViewer, PlanningWorkspace, BudgetOptimizerModal, PlanningBriefModal
│   ├── services/api.ts           # Frontend API client
│   └── test/                     # 49 automated Vitest frontend tests
└── data/                         # Cached FortyGuard 100m NYC heat observations & asset catalogs
```

---

## Quick Start

### 1. Prerequisites & Setup
- **Python 3.10+** and **Node.js 18+**

```bash
# Clone the repository
git clone https://github.com/FortyGuard-Tech/temperature-api-quickstart.git thermal-capital
cd thermal-capital

# Backend setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend setup
cd frontend
npm install
cd ..

# Environment configuration (Optional - bundled offline data enables instant zero-key demoing)
cp .env.example .env
```

### 2. Run the Application

In terminal 1 (FastAPI Backend):
```bash
source .venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

In terminal 2 (React Frontend):
```bash
cd frontend
npm run dev
```

Open **`http://localhost:5173`** in your browser (interactive API documentation is available at `http://localhost:8000/docs`).

---

## Verification & Test Results

The test suite runs 100% offline with zero external API calls:

- **Backend Tests (Pytest):**
  ```bash
  ./.venv/bin/pytest
  ```
  *Result: 63 passed (API routes, knapsack optimizer, spatial tiling, intervention physics).*

- **Frontend Tests (Vitest):**
  ```bash
  cd frontend && npm test -- --run
  ```
  *Result: 49 passed across 10 test suites (map rendering, intervention workspace, budget optimizer, brief export).*

---

## License

This project is licensed under the **MIT License** (see the [LICENSE](LICENSE) file for details).

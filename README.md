# Thermal Capital
**Capital planning for urban heat.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.3-61DAFB.svg)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-3178C6.svg)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-5.4-646CFF.svg)](https://vitejs.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What It Is

**Thermal Capital** is a municipal decision-support and capital-planning platform that uses FortyGuard's hyperlocal microclimate data to help city planners, public works officials, and sustainability directors prioritize urban heat mitigation investments.

### The Problem
Cities cannot cool every street, public plaza, transit stop, school, or playground at once. With constrained municipal budgets, public-sector leaders must decide where limited capital will have the greatest impact on human heat exposure, which cooling interventions will produce the most effective relief, and how to justify capital allocations to city councils and the public.

Thermal Capital bridges the gap between raw microclimate observations and actionable capital planning:
- It transforms **FortyGuard 100m grid thermal intelligence** into prioritized risk rankings across public assets.
- It provides an **interactive planning workspace** to test and compare cooling interventions before spending public funds.
- It runs a **constrained budget optimizer** to maximize thermal relief and protected citizens within a specified budget.
- It compiles a decision-ready **Heat Adaptation Planning Brief** for council reviews, grant applications, and agency coordination.

---

## Key Capabilities

- **Hyperlocal City-Wide Heat Visualization:** Explore 100m spatial resolution ambient dry-bulb temperature ($T_{\text{peak}}$, $T_{\text{mean}}$), cumulative exceedance hours ($>35^\circ\text{C}$), and continuous heat persistence runs across New York City's five boroughs.
- **Priority Heat-Exposure Ranking:** Municipal public assets (bus stops, schools, playgrounds, public plazas, pedestrian corridors) ranked by multi-factor composite risk (afternoon peak, persistence, and demographic vulnerability).
- **Site-Level Heat Inspection:** Inspect individual asset footprints with localized microclimate metrics, existing land cover (canopy % vs. impervious surface %), and transparent ranking rationale.
- **Interactive Intervention Placement:** Test street trees, engineered shade structures, and reflective cool pavement directly on the map around target assets.
- **Before vs. Proposed Scenario Comparison:** Live side-by-side comparison of baseline thermal metrics vs. modeled outcomes (ambient temperature reduction, extreme heat duration reduction, canopy expansion).
- **Itemized Municipal Cost Modeling:** Transparent capital cost accounting based on turnkey municipal procurement benchmarks (NYC Parks street tree contracts, FTA transit shelter guidelines, EPA cool pavement studies).
- **Constrained Budget Optimization:** Deterministic knapsack portfolio optimizer allocating a municipal budget (e.g. \$500,000) across city assets under 4 distinct objective strategies:
  - *Balanced:* Equitable distribution across municipal asset types.
  - *Vulnerable Populations:* Prioritizes elementary schools, daycares, and playgrounds.
  - *Transit Corridors:* Prioritizes high-ridership bus stops and transfer stations.
  - *Maximum Relief:* Prioritizes the hottest, most persistent microclimate zones.
- **Estimated Benefited Citizens:** Quantifies daily protected transit riders, students, and pedestrians based on asset usage and spatial intervention coverage.
- **Decision-Ready Planning Brief:** One-click export of a formal Heat Adaptation Planning Brief with executive summaries, itemized cost tables, and methodology notes.
- **FortyGuard API Integration:** Robust integration with FortyGuard API endpoints, featuring a persistent local SQLite caching layer ensuring zero redundant API calls.

---

## How It Works

The core workflow follows five practical planning steps:

```
  ┌─────────────────┐      ┌─────────────────────────┐      ┌─────────────────────┐
  │ 1. IDENTIFY     │      │ 2. INSPECT A PRIORITY   │      │ 3. INTERVENE &      │
  │    RISK         │ ───> │    LOCATION             │ ───> │    COMPARE          │
  │ City-wide 100m  │      │ Site metrics, land      │      │ Place trees, shade, │
  │ FortyGuard grid │      │ cover, usage & ranking  │      │ & cool pavement     │
  └─────────────────┘      └─────────────────────────┘      └─────────────────────┘
                                                                       │
                                                                       ▼
  ┌─────────────────┐      ┌─────────────────────────┐      ┌─────────────────────┐
  │ 5. GENERATE     │      │ 4. OPTIMIZE THE         │      │ Compare Modeled     │
  │    BRIEF        │ <─── │    AVAILABLE BUDGET     │ <─── │ Scenario vs.        │
  │ Meeting-ready   │      │ Knapsack allocation of  │      │ Observed Baseline   │
  │ municipal plan  │      │ limited funds ($500k)   │      │                     │
  └─────────────────┘      └─────────────────────────┘      └─────────────────────┘
```

1. **Identify Risk:** Planners view city-wide 100m grid heat distributions and explore the prioritized list of exposed public infrastructure.
2. **Inspect a Priority Location:** Selecting an asset zooms to its parcel footprint, displaying measured afternoon peak, exceedance hours, land cover composition, and specific priority reasons.
3. **Intervene & Compare:** Planners place cooling interventions (trees, shade canopies, cool pavement) on the map and immediately see modeled temperature reductions ($\Delta T$) and extreme heat duration reductions.
4. **Optimize the Available Budget:** Planners set an overall capital budget (e.g. \$500,000) and select an objective strategy to automatically allocate funds across dozens of public assets.
5. **Generate a Planning Brief:** Planners export a print-ready briefing document complete with executive narrative, itemized budget breakdowns, and methodology documentation.

---

## Data and Methodology

Thermal Capital maintains strict scientific credibility by separating **observed microclimate baseline data** from **modeled scenario estimates**:

### 1. Observed Baseline Data (FortyGuard Microclimate Intelligence)
- Baseline metrics represent physical measurements and model outputs from FortyGuard's 100m spatial grid during the July 15–21, 2024 heatwave:
  - Peak ambient dry-bulb temperature ($T_{\text{peak}}$).
  - 24-hour mean temperature ($T_{\text{mean}}$).
  - Cumulative hours exceeding $35.0^\circ\text{C}$ ($95.0^\circ\text{F}$).
  - Longest continuous run of hours $>35.0^\circ\text{C}$ (thermal persistence).
  - High-resolution satellite land-cover classification (canopy % and impervious surface %).

### 2. Modeled Intervention Impacts (Planning Estimates)
Post-intervention cooling outputs are empirical planning estimates designed for scenario comparison and budget optimization:
- **Urban Street Tree Canopy:** $25\,\text{m}^2$ mature crown per tree. Modeled via evapotranspiration and solar radiation interception: $\Delta T = 3.2 \cdot (1 - e^{-0.065 \cdot n}) \cdot \text{scale\_factor}$. Planning unit cost: **\$3,200/tree** (NYC Parks FY2024 turnkey contracts).
- **Engineered Shade Structures:** $100\,\text{m}^2$ direct shade per structure. Modeled via direct shortwave solar blockage: $\Delta T = 2.8 \cdot (1 - e^{-0.45 \cdot n})$. Planning unit cost: **\$28,000/structure** (FTA & municipal transit capital guidelines).
- **Reflective Cool Pavement Coating:** Solar-reflective high-albedo coating ($\ge 0.35$ albedo). Modeled via reduced surface sensible heat flux: $\Delta T = 1.8 \cdot (1 - e^{-0.0028 \cdot A_{\text{m2}}})$. Planning unit cost: **\$24/$\text{m}^2$** (EPA Heat Island Reduction Program benchmarks).
- **Synergy & Diminishing Returns:** Multi-intervention packages operate on the same local air volume, subject to an empirical asymptotic ceiling: $\text{Net } \Delta T = \min(4.2, 4.2 \cdot (1 - e^{-\text{raw\_delta}/3.6}))$.

> [!NOTE]
> **Decision-Support Scope:** Modeled cooling effects and itemized costs are planning-level estimates intended to help municipalities compare relative intervention scenarios and prioritize capital spending. They are not a substitute for site-specific computational fluid dynamics (CFD) engineering or stamped civil construction drawings.

---

## FortyGuard API Integration

Thermal Capital connects to the FortyGuard Enterprise REST API (`https://api.fortyguard.com`):

- **Heatmap API (`POST /v1/heatmap`):**
  - `tcm`: 100m ambient dry-bulb temperature grid.
  - `exceedance`: Cumulative hours exceeding thermal threshold ($>35^\circ\text{C}$).
  - `persistence`: Continuous duration of extreme heat runs.
- **Environmental Parameters API (`POST /v1/env_params`):**
  - Point-level diurnal time-series (heat index, apparent temperature, wet-bulb, relative humidity, air quality).
- **Satellite Segmentation API (`POST /v1/satellite`):**
  - Land-cover segmentation (tree canopy %, impervious pavement %, building footprints).
- **Async Polling & Caching:**
  - Robust submit-and-poll lifecycle (`POST` task $\to$ poll `GET /v1/status/{activity_id}`).
  - SHA-256 deterministic caching via `SQLiteCacheStore` to prevent redundant billing and preserve API credits.

---

## Tech Stack

### Backend
- **Python 3.10+** — Core runtime
- **FastAPI** — High-performance asynchronous API framework
- **Pydantic v2** — Type-safe domain models and request/response validation
- **Shapely** — Geospatial polygon operations, buffering, and centroid calculation
- **SQLite3** — Embedded zero-configuration local cache store
- **Uvicorn** — Production-ready ASGI server
- **Pytest** — Automated backend test suite

### Frontend
- **React 18** — Component-driven UI
- **TypeScript** — Static typing and strict interfaces
- **Vite** — High-speed build tool and development server
- **MapLibre GL JS** — Vector map rendering with custom thermal layers and clustering
- **Tailwind CSS** — Utility-first municipal design system
- **Lucide React** — Consistent icon library
- **Vitest & React Testing Library** — Automated frontend test suite

---

## Project Structure

```
thermal-capital/
├── backend/
│   ├── api/
│   │   ├── __init__.py
│   │   └── router.py                 # REST endpoints (/cities, /assets, /simulate, /optimize, /report, /heatmap)
│   ├── cache/
│   │   ├── cached_client.py          # Cached FortyGuard client wrapper
│   │   ├── keys.py                   # Deterministic SHA-256 cache key hashing
│   │   └── store.py                  # SQLite-backed persistent cache
│   ├── models/
│   │   ├── planner.py                # Domain models (PublicAsset, InterventionConfig, PlanningReport)
│   │   └── thermal.py                # Core microclimate metric schemas
│   ├── services/
│   │   ├── assets_data.py            # Public asset registries mapped to FortyGuard 100m grid tiles
│   │   ├── budget_optimizer.py       # Multi-strategy knapsack portfolio optimizer
│   │   ├── geo.py                    # Spatial clipping and GeoJSON utilities
│   │   ├── intervention_model.py     # Microclimate response engine & methodology metadata
│   │   ├── nyc_tiling.py             # NYC 100m grid tiling orchestration
│   │   ├── report_generator.py       # Heat adaptation planning brief compiler
│   │   ├── scoring_config.py         # Multi-factor scoring configuration
│   │   ├── site_analysis.py          # Point & parcel thermal exposure analyzer
│   │   ├── site_screening.py         # Multi-site screening service
│   │   └── thermal_scoring.py        # Composite heat risk calculator
│   ├── tests/                        # 63 Pytest automated unit tests
│   └── main.py                       # FastAPI application entrypoint
├── data/
│   ├── probes/                       # Cached FortyGuard 100m grid observations & coverage
│   ├── candidate_sites/              # Municipal asset catalogs
│   └── nyc_boroughs.geojson          # Borough boundary polygons
├── docs/                             # Architecture specifications & methodology notes
├── fortyguard/                       # Official FortyGuard Python client SDK
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.tsx            # Navigation, city selection, workflow mode switch
│   │   │   ├── MapViewer.tsx         # MapLibre GL map, thermal heatmaps, asset markers
│   │   │   ├── RankingList.tsx       # Priority risk area rankings
│   │   │   ├── SiteDetail.tsx        # Asset inspection & baseline metrics
│   │   │   ├── PlanningWorkspace.tsx # Intervention sliders, live outcomes, methodology popout
│   │   │   ├── BudgetOptimizerModal.tsx # Knapsack portfolio optimization modal
│   │   │   └── PlanningBriefModal.tsx # Exportable & printable planning brief
│   │   ├── services/api.ts           # Frontend API client
│   │   ├── test/                     # 23 Vitest automated unit tests
│   │   ├── types/                    # TypeScript interfaces
│   │   ├── utils/                    # Formatters & spatial helpers
│   │   ├── App.tsx                   # Main layout container & state orchestration
│   │   └── main.tsx                  # React DOM entry point
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.ts
├── .env.example                      # Template environment variables
├── .gitignore                        # Clean Git ignore rules
├── LICENSE                           # MIT License
├── README.md                         # Project documentation
└── requirements.txt                  # Python backend dependencies
```

---

## Setup & Installation

### Prerequisites
- **Python 3.10+**
- **Node.js 18+** & **npm**

### 1. Clone the Repository
```bash
git clone https://github.com/FortyGuard-Tech/temperature-api-quickstart.git thermal-capital
cd thermal-capital
```

### 2. Configure Environment Variables
Create a `.env` file from the provided example:
```bash
cp .env.example .env
```
Edit `.env` and provide your FortyGuard API key (optional for offline demo mode):
```env
FORTYGUARD_API_KEY=your_api_key_here
FORTYGUARD_BASE_URL=https://api.fortyguard.com
```

### 3. Setup the Python Backend
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 4. Setup the React Frontend
```bash
cd frontend
npm install
cd ..
```

---

## Running the Application

### Start the FastAPI Backend
```bash
source .venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
The backend will be live at `http://127.0.0.1:8000` (API documentation available at `http://127.0.0.1:8000/docs`).

### Start the Frontend Development Server
In a separate terminal window:
```bash
cd frontend
npm run dev
```
Open `http://localhost:5173` in your browser. Vite automatically proxies `/api` calls to the FastAPI backend.

---

## Testing & Verification

### Running Backend Tests
The backend test suite verifies API routes, deterministic caching, spatial clipping, intervention physics, budget optimization, and report generation:
```bash
./.venv/bin/pytest
```
*Result: 63 passed.*

### Running Frontend Tests
The frontend test suite verifies component rendering, intervention workflows, budget optimization, report generation, and formatting:
```bash
cd frontend
npm test -- --run
```
*Result: 23 passed across 8 test suites.*

### Building Frontend for Production
```bash
cd frontend
npm run build
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `FORTYGUARD_API_KEY` | Optional | `None` | FortyGuard API authorization key. Bundled offline datasets allow full zero-credit demoing. |
| `FORTYGUARD_BASE_URL` | Optional | `https://api.fortyguard.com` | Base URL for FortyGuard tOS API endpoints. |

---

## Project Status

Thermal Capital was developed for the **FortyGuard Hackathon 2026** under **Track 1: Resilient Cities & Infrastructure**. It represents a functional decision-support prototype demonstrating how high-resolution urban microclimate intelligence can power municipal capital planning and public expenditure prioritization.

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

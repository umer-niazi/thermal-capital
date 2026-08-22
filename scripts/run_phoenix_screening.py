"""Live integration script executing multi-site thermal screening across Phoenix candidate parcels."""

from __future__ import annotations

import json
import os
import pathlib
import sys
from dotenv import load_dotenv

# Ensure repository root is on sys.path
ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Load .env
load_dotenv(ROOT_DIR / ".env")

from backend.cache.cached_client import CachedFortyGuardClient
from backend.models.thermal import CandidateSite
from backend.services.site_screening import screen_candidate_sites

PROBES_DIR = ROOT_DIR / "data" / "probes"
OUTPUTS_DIR = ROOT_DIR / "outputs"


def main() -> None:
    PROBES_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    api_key = os.getenv("FORTYGUARD_API_KEY")
    if not api_key:
        print("Error: FORTYGUARD_API_KEY environment variable is not set in .env")
        sys.exit(1)

    print("=" * 65)
    print("THERMAL CAPITAL — PHOENIX MULTI-SITE SCREENING")
    print("Study Date Range : 2024-07-15 to 2024-07-21 (7-Day Peak Heatwave)")
    print("Target Customer  : Data Center Developers & Infrastructure Planners")
    print("=" * 65)

    # Define 2 candidate industrial data center parcels in Central Phoenix
    site1 = CandidateSite(
        id="PHX-DTC-01",
        name="Phoenix Central Logistics & Power Corridor",
        geometry={
            "type": "Polygon",
            "coordinates": [[
                [-112.0780, 33.4440],
                [-112.0710, 33.4440],
                [-112.0710, 33.4480],
                [-112.0780, 33.4480],
                [-112.0780, 33.4440],
            ]],
        },
        latitude=33.4460,
        longitude=-112.0745,
        area_acres=35.0,
        metadata={"target_capacity_mw": 50, "substation_distance_km": 1.2},
    )

    site2 = CandidateSite(
        id="PHX-DTC-02",
        name="Northwest Airport Industrial Technology Park",
        geometry={
            "type": "Polygon",
            "coordinates": [[
                [-112.0770, 33.4490],
                [-112.0700, 33.4490],
                [-112.0700, 33.4530],
                [-112.0770, 33.4530],
                [-112.0770, 33.4490],
            ]],
        },
        latitude=33.4510,
        longitude=-112.0735,
        area_acres=32.0,
        metadata={"target_capacity_mw": 45, "substation_distance_km": 0.8},
    )

    client = CachedFortyGuardClient()

    print(f"\n[1/4] Running multi-site screening for {len([site1, site2])} candidate parcels...")
    print("      Building unified AOI with 400m safety buffer to minimize API calls...")

    screening_result = screen_candidate_sites(
        sites=[site1, site2],
        start_date="2024-07-15",
        end_date="2024-07-21",
        granularity=100,
        buffer_m=400.0,
        exceedance_threshold=40.0,
        persistence_threshold=35.0,
        enrichment_top_n=1,  # Selectively enrich the top candidate
        run_satellite=True,
        client=client,
        bypass_cache=False,
    )

    # Export cached raw responses to data/probes/ for auditability
    with client.store._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT endpoint, payload_json, response_json FROM api_cache")
        for ep, payload_str, resp_str in cursor.fetchall():
            payload = json.loads(payload_str)
            resp = json.loads(resp_str)
            if ep == "/v1/heatmap":
                analytic = payload.get("analytic_type", "tcm")
                fname = f"phoenix_{analytic}_{payload.get('date_time', {}).get('start_date')}"
                if payload.get("date_time", {}).get("end_date"):
                    fname += f"_{payload['date_time']['end_date']}"
                fname += ".json"
            elif ep == "/v1/env_params":
                fname = "phoenix_env_params_2024-07-15.json"
            elif ep == "/v1/satellite":
                fname = "phoenix_satellite_2024-07-15.json"
            else:
                fname = f"probe_{ep.strip('/').replace('/', '_')}.json"

            with open(PROBES_DIR / fname, "w", encoding="utf-8") as pf:
                json.dump(resp, pf, indent=2)

    # Save output report
    output_report_file = OUTPUTS_DIR / "phoenix_screening.json"
    with open(output_report_file, "w", encoding="utf-8") as f:
        json.dump(screening_result.model_dump(), f, indent=2)

    print(f"\n[2/4] Saved screening JSON report to: {output_report_file}")
    print(f"      Saved raw JSON probe responses to: {PROBES_DIR}/")

    # Cache stats
    stats = client.store.stats()
    print(f"[3/4] Cache Store Status: {stats['total_entries']} cached responses, {stats['total_hits']} hits")

    # -------------------------------------------------------------------------
    # Formatted Human-Readable Summary
    # -------------------------------------------------------------------------
    print("\n" + "=" * 65)
    print("PHOENIX THERMAL SITE SCREENING RESULTS")
    print("=" * 65)
    print(f"Unified AOI Area : {screening_result.aoi_area_km2:.2f} km²")
    print(f"Analysis Window  : {screening_result.window_start} to {screening_result.window_end} ({screening_result.study_window_days} days / {screening_result.scoring_metadata.get('window_hours')}h)")
    print("-" * 65)

    for site_exp in screening_result.ranked_sites:
        tm = site_exp.tcm_metrics
        rr = site_exp.risk_result
        cb = site_exp.cooling_burden
        env = site_exp.environmental_metrics
        sat = site_exp.satellite_metrics

        print(f"\nRANK #{site_exp.rank}: {site_exp.site_name} ({site_exp.site_id})")
        print(f"  • Composite Thermal Score : {rr.total_score:.1f} / 100  [{rr.risk_category.upper()} RISK]")
        print(f"  • Data Completeness       : {rr.data_completeness}")
        print(f"  • Boundary Tile Coverage  : {site_exp.coverage_pct:.1f}% ({site_exp.contributing_tile_count} contributing 100m grid tiles)")
        print(f"  • Daily Peak Ambient Temp : {tm.peak_temperature_c:.2f}°C / {tm.peak_temperature_f:.1f}°F")
        print(f"  • Daily Mean Ambient Temp : {tm.mean_temperature_c:.2f}°C / {tm.mean_temperature_f:.1f}°F")
        print(f"  • Overnight Minimum Temp  : {tm.overnight_min_temperature_c:.2f}°C / {tm.overnight_min_temperature_f:.1f}°F")
        print(f"  • Diurnal Temp Swing      : {tm.diurnal_swing_c:.2f}°C / {tm.diurnal_swing_f:.1f}°F")

        if site_exp.exceedance_hours is not None:
            print(f"  • Hours >40.0°C (104°F)   : {site_exp.exceedance_hours:.1f} hours ({site_exp.exceedance_hours/168*100:.1f}% of 7-day window)")
        if site_exp.persistence_hours is not None:
            print(f"  • Unbroken Run >35.0°C    : {site_exp.persistence_hours:.1f} continuous hours")

        if env:
            print(f"  • Peak Wet-Bulb Temp      : {env.peak_wet_bulb_temperature_c:.2f}°C / {env.peak_wet_bulb_temperature_f:.1f}°F (Economizer threshold ~24°C)")
            print(f"  • Hot-Hour Apparent Temp  : {env.peak_apparent_temperature_c:.2f}°C / {env.peak_apparent_temperature_f:.1f}°F (at {env.peak_apparent_temperature_time})")
            if env.peak_heat_index_c:
                print(f"  • Hot-Hour Heat Index     : {env.peak_heat_index_c:.2f}°C / {env.peak_heat_index_f:.1f}°F")

        if sat:
            print(f"  • Land-Cover Composition  : Impervious: {sat.impervious_pct:.1f}% | Vegetation: {sat.vegetation_pct:.1f}% | Bare Ground: {sat.bare_ground_pct:.1f}%")

        if cb:
            print(f"  • Cooling Degree Hours    : {cb.cooling_degree_hours_above_25c:.1f} CDH (>25°C baseline)")
            if cb.chiller_cop_degradation_pct:
                print(f"  • Chiller COP Loss Proxy  : {cb.chiller_cop_degradation_pct:.1f}% efficiency drop vs 35°C rating")

        print("  • Component Score Breakdown:")
        for comp_name, comp in rr.components.items():
            fallback_label = " [PROXY]" if comp.is_estimated_or_fallback else " [MEASURED]"
            print(f"      - {comp.name:<32} (Wt {int(comp.weight*100):>2}%): {comp.normalized_score:>5.1f}/100 -> {comp.weighted_contribution:>5.2f} pts{fallback_label} ({comp.data_source})")

        print("  • Risk Explanations:")
        for exp in rr.explanation:
            print(f"      * {exp}")

    print("\n" + "=" * 65)
    print("SCREENING COMPLETE")
    print("=" * 65)


if __name__ == "__main__":
    main()

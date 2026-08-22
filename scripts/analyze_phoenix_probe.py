"""Local analysis script for FortyGuard Phoenix TCM probe data.

Loads the verified Phoenix TCM response, extracts spatial metrics, computes
area-weighted site metrics over a sample candidate data center parcel, and
calculates a preliminary thermal risk score.
"""

from __future__ import annotations

import json
import pathlib
import sys

# Ensure repository root is on sys.path
ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.models.thermal import CandidateSite
from backend.services.geo import clip_heatmap_to_site
from backend.services.thermal_metrics import extract_tcm_metrics
from backend.services.thermal_scoring import calculate_thermal_risk_score

PROBE_FILE = ROOT_DIR / "data" / "probes" / "phoenix_tcm_2024-07-15.json"


def main() -> None:
    if not PROBE_FILE.exists():
        print(f"Error: Probe file not found at {PROBE_FILE}")
        sys.exit(1)

    with open(PROBE_FILE, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    stats = extract_tcm_metrics(raw_data)
    features = raw_data["result"]["map_data"]["features"]

    # Define a representative 40-acre candidate data center site in the Central Phoenix AOI
    candidate_parcel = CandidateSite(
        id="PHX-DTC-01",
        name="Phoenix Central Infrastructure Site",
        geometry={
            "type": "Polygon",
            "coordinates": [[
                [-112.0780, 33.4440],
                [-112.0710, 33.4440],
                [-112.0710, 33.4490],
                [-112.0780, 33.4490],
                [-112.0780, 33.4440],
            ]],
        },
        latitude=33.4465,
        longitude=-112.0745,
        metadata={"target_capacity_mw": 60, "zoning": "A-1 Industrial"},
    )

    clip_res = clip_heatmap_to_site(features, candidate_parcel.geometry, site_id=candidate_parcel.id)
    site_metrics = clip_res.to_thermal_metrics()
    risk_result = calculate_thermal_risk_score(site_metrics)

    # -------------------------------------------------------------------------
    # Formatted Output
    # -------------------------------------------------------------------------
    print("=" * 60)
    print("THERMAL CAPITAL — PROBE ANALYSIS")
    print("Phoenix Baseline Probe")
    print("Study Date: 2024-07-15")
    print("=" * 60)
    print(f"\nTiles analyzed: {stats.tile_count}")
    print("\n--- AOI Spatial Aggregate Metrics ---")
    print(f"Peak temperature (spatial mean of tile peaks)")
    print(f"{stats.mean_max_temp_c:.2f}°C / {stats.mean_max_temp_c * 9/5 + 32:.2f}°F")
    print(f"\nDaily mean")
    print(f"{stats.mean_average_temp_c:.2f}°C / {stats.mean_average_temp_c * 9/5 + 32:.2f}°F")
    print(f"\nOvernight minimum")
    print(f"{stats.mean_min_temp_c:.2f}°C / {stats.mean_min_temp_c * 9/5 + 32:.2f}°F")
    print(f"\nMean diurnal swing")
    print(f"{stats.mean_diurnal_swing_c:.2f}°C / {stats.mean_diurnal_swing_c * 9/5:.2f}°F")

    print("\n" + "-" * 60)
    print(f"Candidate Site Evaluation: {candidate_parcel.name} ({candidate_parcel.id})")
    print(f"Contributing Grid Tiles : {clip_res.contributing_tile_count} tiles ({clip_res.coverage_pct:.1f}% boundary coverage)")
    print(f"Site Area-Weighted Peak : {site_metrics.peak_temperature_c:.2f}°C / {site_metrics.peak_temperature_f:.2f}°F")
    print(f"Site Area-Weighted Mean : {site_metrics.mean_temperature_c:.2f}°C / {site_metrics.mean_temperature_f:.2f}°F")
    print(f"Site Area-Weighted Min  : {site_metrics.overnight_min_temperature_c:.2f}°C / {site_metrics.overnight_min_temperature_f:.2f}°F")
    print(f"Site Diurnal Swing      : {site_metrics.diurnal_swing_c:.2f}°C / {site_metrics.diurnal_swing_f:.2f}°F")

    print("\n" + "=" * 60)
    print("PRELIMINARY THERMAL RISK SCORE (TCM Snapshot)")
    print("=" * 60)
    print(f"Composite Score : {risk_result.total_score:.1f} / 100")
    print(f"Risk Category   : {risk_result.risk_category}")
    print(f"Completeness    : {risk_result.data_completeness}")
    print("\nComponent Breakdown:")
    for comp_key, comp in risk_result.components.items():
        fallback_note = " [PRELIMINARY PROXY]" if comp.is_estimated_or_fallback else ""
        print(f"  • {comp.name:<38} (Weight {int(comp.weight*100):>2}%): {comp.normalized_score:>5.1f}/100  -> Contribution: {comp.weighted_contribution:>5.2f} pts{fallback_note}")
        print(f"    Raw: {comp.raw_value} {comp.raw_units} | {comp.description}")

    print("\nAnalytical Explanations:")
    for exp in risk_result.explanation:
        print(f"  - {exp}")

    print("\n" + "=" * 60)
    print("NOTE: This is a PRELIMINARY score because multi-day exceedance,")
    print("persistence, wet-bulb, and satellite surface characteristics")
    print("have not yet been enriched.")
    print("=" * 60)


if __name__ == "__main__":
    main()

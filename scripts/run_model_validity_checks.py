"""Run model reliability, validity, and robustness checks."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.reliability_validity import generate_validity_report, run_model_validity_pipeline


def main() -> int:
    validity_results = run_model_validity_pipeline()
    cronbach = validity_results["cronbach_alpha"]
    ahp = validity_results["ahp_consistency"]
    sensitivity = validity_results["sensitivity_analysis"]
    content_table = validity_results["content_validity_table"]

    print("Cronbach's Alpha result")
    print(f"- status: {cronbach['status']}")
    print(f"- alpha: {cronbach['alpha']}")
    print(f"- explanation: {cronbach['explanation']}")
    print()

    print("AHP consistency result")
    print(f"- status: {ahp['status']}")
    print(f"- explanation: {ahp['explanation']}")
    if "CR" in ahp:
        print(f"- CR: {ahp['CR']}")
    print()

    print("Sensitivity analysis summary")
    print(f"- ranking_stability_ratio: {sensitivity['ranking_stability_ratio']}")
    print(f"- average_spearman_correlation: {sensitivity['average_spearman_correlation']}")
    print(f"- explanation: {sensitivity['explanation']}")
    print()

    print("Content validity")
    print(f"- indicator_count: {len(content_table)}")
    print()

    print("Generated validity report")
    print(generate_validity_report(validity_results))
    return 0


if __name__ == "__main__":
    sys.exit(main())

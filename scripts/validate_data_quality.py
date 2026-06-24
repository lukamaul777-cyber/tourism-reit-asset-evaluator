"""Validate the data quality and data confidence module."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_quality import (  # noqa: E402
    calculate_all_data_confidence_scores,
    generate_data_quality_report,
    get_data_type_distribution,
    get_missingness_summary,
)


REQUIRED_SCORE_COLUMNS = {
    "asset_id",
    "asset_name",
    "completeness_score",
    "source_reliability_score",
    "traceability_score",
    "timeliness_score",
    "coverage_score",
    "data_confidence_score",
    "data_confidence_level",
}
SCORE_COLUMNS = {
    "completeness_score",
    "source_reliability_score",
    "traceability_score",
    "timeliness_score",
    "coverage_score",
    "data_confidence_score",
}
REQUIRED_DISTRIBUTION_COLUMNS = {"table", "data_type", "count", "percentage"}
REQUIRED_MISSINGNESS_COLUMNS = {"table", "column", "missing_count", "missing_percentage", "row_count"}


def _missing_columns(df: pd.DataFrame, required_columns: set[str]) -> set[str]:
    return required_columns - set(df.columns)


def _validate_score_ranges(scores_df: pd.DataFrame) -> list[str]:
    errors: list[str] = []
    for column in SCORE_COLUMNS:
        values = pd.to_numeric(scores_df[column], errors="coerce")
        if values.isna().any():
            errors.append(f"{column} contains non-numeric or missing values.")
        if not values.between(0, 100).all():
            errors.append(f"{column} contains values outside the 0-100 range.")
    return errors


def validate_data_quality() -> list[str]:
    """Run consistency checks for data quality outputs."""
    errors: list[str] = []

    scores_df = calculate_all_data_confidence_scores()
    distribution_df = get_data_type_distribution()
    missingness_df = get_missingness_summary()

    if scores_df.empty:
        errors.append("Data confidence score table is empty.")
    else:
        missing = _missing_columns(scores_df, REQUIRED_SCORE_COLUMNS)
        if missing:
            errors.append("Data confidence score table missing columns: " + ", ".join(sorted(missing)))
        else:
            errors.extend(_validate_score_ranges(scores_df))

            first_asset_id = str(scores_df.iloc[0]["asset_id"])
            report_text = generate_data_quality_report(first_asset_id)
            if not report_text.strip():
                errors.append("Generated data quality report is empty.")
            if "Data Quality Report" not in report_text:
                errors.append("Generated report does not include the expected title.")
            if "Disclaimer" not in report_text:
                errors.append("Generated report does not include a disclaimer.")

    if distribution_df.empty:
        errors.append("Data type distribution table is empty.")
    else:
        missing = _missing_columns(distribution_df, REQUIRED_DISTRIBUTION_COLUMNS)
        if missing:
            errors.append("Data type distribution missing columns: " + ", ".join(sorted(missing)))
        if "overall" not in set(distribution_df.get("table", [])):
            errors.append("Data type distribution does not include an overall summary row.")

    if missingness_df.empty:
        errors.append("Missingness summary table is empty.")
    else:
        missing = _missing_columns(missingness_df, REQUIRED_MISSINGNESS_COLUMNS)
        if missing:
            errors.append("Missingness summary missing columns: " + ", ".join(sorted(missing)))

    return errors


def main() -> int:
    """CLI entry point."""
    try:
        errors = validate_data_quality()
    except Exception as exc:
        print(f"Data quality validation failed: {exc}")
        return 1

    if errors:
        print("Data quality validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    scores_df = calculate_all_data_confidence_scores()
    print("Data quality validation passed.")
    print(f"Assets checked: {len(scores_df)}")
    print(f"Average data confidence score: {scores_df['data_confidence_score'].mean():.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

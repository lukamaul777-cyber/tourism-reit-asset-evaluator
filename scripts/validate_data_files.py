"""Validate CSV data templates for the Tourism REIT Asset Evaluator."""

from __future__ import annotations

import csv
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

REQUIRED_TABLES: dict[str, list[str]] = {
    "assets.csv": [
        "asset_id",
        "asset_name",
        "asset_type",
        "location",
        "description",
        "ownership_status",
        "operation_years",
        "has_major_legal_dispute",
        "cash_flow_source_type",
        "data_type",
        "source_note",
    ],
    "financial_metrics.csv": [
        "asset_id",
        "year",
        "revenue",
        "ebitda",
        "noi",
        "operating_cash_flow",
        "maintenance_capex",
        "estimated_affo",
        "estimated_distribution",
        "total_assets",
        "total_debt",
        "debt_ratio",
        "capex_to_ocf",
        "data_type",
        "source_note",
    ],
    "operation_metrics.csv": [
        "asset_id",
        "year",
        "visitor_volume",
        "occupancy_rate",
        "adr",
        "revpar",
        "average_spending_per_visitor",
        "secondary_spending_ratio",
        "peak_season_revenue_ratio",
        "data_type",
        "source_note",
    ],
    "service_quality_metrics.csv": [
        "asset_id",
        "year",
        "ota_score",
        "review_count",
        "tangibles_score",
        "reliability_score",
        "responsiveness_score",
        "assurance_score",
        "empathy_score",
        "complaint_rate",
        "data_type",
        "source_note",
    ],
    "risk_metrics.csv": [
        "asset_id",
        "year",
        "seasonality_risk",
        "market_competition_risk",
        "policy_risk",
        "climate_physical_risk",
        "financial_pressure_risk",
        "platform_dependency_risk",
        "risk_disclosure_score",
        "data_type",
        "source_note",
    ],
    "digital_maturity_metrics.csv": [
        "asset_id",
        "year",
        "data_availability_score",
        "data_quality_score",
        "smart_operation_score",
        "online_reservation_score",
        "visitor_flow_monitoring_score",
        "public_opinion_monitoring_score",
        "dashboard_monitoring_score",
        "data_type",
        "source_note",
    ],
    "data_dictionary.csv": [
        "table_name",
        "column_name",
        "definition",
        "formula",
        "unit",
        "data_type",
        "source_note",
        "reference_framework",
    ],
}

TEXT_COLUMNS = {
    "asset_id",
    "asset_name",
    "asset_type",
    "location",
    "description",
    "ownership_status",
    "has_major_legal_dispute",
    "cash_flow_source_type",
    "data_type",
    "source_note",
    "table_name",
    "column_name",
    "definition",
    "formula",
    "unit",
    "reference_framework",
}


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Read a CSV file as dictionaries and return fieldnames plus rows."""
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader.fieldnames or []), list(reader)


def validate_required_files_and_columns(errors: list[str]) -> dict[str, list[dict[str, str]]]:
    """Validate required files and columns, returning loaded rows."""
    loaded_rows: dict[str, list[dict[str, str]]] = {}

    for file_name, required_columns in REQUIRED_TABLES.items():
        path = DATA_DIR / file_name
        if not path.exists():
            errors.append(f"Missing required CSV file: {path}")
            continue

        fieldnames, rows = read_csv(path)
        loaded_rows[file_name] = rows
        missing_columns = [column for column in required_columns if column not in fieldnames]

        if missing_columns:
            errors.append(f"{file_name} missing required columns: {', '.join(missing_columns)}.")

        for metadata_column in ("data_type", "source_note"):
            if metadata_column not in fieldnames:
                errors.append(f"{file_name} must include {metadata_column}.")

    return loaded_rows


def validate_asset_ids(
    loaded_rows: dict[str, list[dict[str, str]]],
    errors: list[str],
) -> None:
    """Validate that asset_id values match across all asset-level tables."""
    assets = loaded_rows.get("assets.csv", [])
    canonical_ids = {row.get("asset_id", "").strip() for row in assets if row.get("asset_id")}

    if not canonical_ids:
        errors.append("assets.csv must contain at least one asset_id.")
        return

    for file_name, rows in loaded_rows.items():
        if file_name in {"assets.csv", "data_dictionary.csv"}:
            continue

        table_ids = {row.get("asset_id", "").strip() for row in rows if row.get("asset_id")}
        missing_from_table = canonical_ids - table_ids
        unknown_in_table = table_ids - canonical_ids

        if missing_from_table:
            errors.append(f"{file_name} missing asset_id values: {', '.join(sorted(missing_from_table))}.")
        if unknown_in_table:
            errors.append(f"{file_name} has unknown asset_id values: {', '.join(sorted(unknown_in_table))}.")


def validate_years(
    loaded_rows: dict[str, list[dict[str, str]]],
    errors: list[str],
) -> None:
    """Validate year fields where present."""
    for file_name, rows in loaded_rows.items():
        if "year" not in REQUIRED_TABLES[file_name]:
            continue

        for row_number, row in enumerate(rows, start=2):
            value = row.get("year", "").strip()
            try:
                year = int(value)
            except ValueError:
                errors.append(f"{file_name} row {row_number} has invalid integer year: {value!r}.")
                continue

            if year < 1900 or year > 2100:
                errors.append(f"{file_name} row {row_number} has out-of-range year: {year}.")


def validate_numeric_columns(
    loaded_rows: dict[str, list[dict[str, str]]],
    errors: list[str],
) -> None:
    """Validate numeric parsing for non-text required columns."""
    for file_name, rows in loaded_rows.items():
        numeric_columns = [
            column
            for column in REQUIRED_TABLES[file_name]
            if column not in TEXT_COLUMNS and column != "year"
        ]

        for row_number, row in enumerate(rows, start=2):
            for column in numeric_columns:
                value = row.get(column, "").strip()
                if value == "":
                    errors.append(f"{file_name} row {row_number} column {column} is blank.")
                    continue
                try:
                    float(value)
                except ValueError:
                    errors.append(
                        f"{file_name} row {row_number} column {column} is not numeric: {value!r}."
                    )


def validate_data_files() -> list[str]:
    """Run all data-template validation checks."""
    errors: list[str] = []
    loaded_rows = validate_required_files_and_columns(errors)

    if errors:
        return errors

    validate_asset_ids(loaded_rows, errors)
    validate_years(loaded_rows, errors)
    validate_numeric_columns(loaded_rows, errors)

    return errors


def main() -> int:
    """CLI entry point."""
    errors = validate_data_files()

    if errors:
        print("Data validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Data validation passed.")
    print(f"Checked {len(REQUIRED_TABLES)} CSV files in {DATA_DIR}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

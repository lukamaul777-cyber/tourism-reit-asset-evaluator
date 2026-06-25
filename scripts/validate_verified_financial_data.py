"""Validate optional verified public financial data artifacts."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAPPING_PATH = PROJECT_ROOT / "data_sources" / "company_mapping.csv"
VERIFIED_PATH = PROJECT_ROOT / "data_verified" / "financial_metrics_verified.csv"
PREVIEW_PATH = PROJECT_ROOT / "data_verified" / "replacement_preview.csv"

PROJECT_REQUIRED_COLUMNS = {
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
}
VERIFIED_METADATA_COLUMNS = {"source_name", "source_url", "source_year", "verification_status", "last_verified_date"}
PREVIEW_COLUMNS = {
    "asset_id",
    "asset_name",
    "stock_code",
    "year",
    "field_name",
    "old_value",
    "new_value",
    "source_name",
    "verification_status",
    "notes",
}
VALID_STATUSES = {
    "verified",
    "partially_verified",
    "public_collected",
    "estimated",
    "simulated",
    "pending",
    "fetch_failed",
}
NUMERIC_VERIFIED_COLUMNS = {
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
}


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"stock_code": str})


def _validate_required_columns(df: pd.DataFrame, required: set[str], label: str, errors: list[str]) -> None:
    missing = sorted(required - set(df.columns))
    if missing:
        errors.append(f"{label} missing columns: {', '.join(missing)}")


def _validate_statuses(df: pd.DataFrame, label: str, errors: list[str]) -> None:
    if "verification_status" not in df.columns or df.empty:
        return
    statuses = set(df["verification_status"].dropna().astype(str))
    invalid = sorted(statuses - VALID_STATUSES)
    if invalid:
        errors.append(f"{label} has invalid verification_status values: {', '.join(invalid)}")


def _validate_numeric_values(df: pd.DataFrame, columns: set[str], label: str, errors: list[str]) -> None:
    if df.empty:
        return
    for column in columns:
        if column not in df.columns:
            continue
        values = df[column]
        non_blank = values[values.notna() & (values.astype(str).str.strip() != "")]
        parsed = pd.to_numeric(non_blank, errors="coerce")
        if parsed.isna().any():
            errors.append(f"{label} column {column} contains non-numeric replacement values.")


def validate_verified_financial_data() -> tuple[list[str], dict[str, pd.DataFrame]]:
    """Run validation checks and return errors plus loaded tables."""
    errors: list[str] = []
    tables: dict[str, pd.DataFrame] = {}

    if not MAPPING_PATH.exists():
        errors.append(f"Missing company mapping: {MAPPING_PATH}")
    else:
        mapping_df = _read_csv(MAPPING_PATH)
        tables["mapping"] = mapping_df
        _validate_required_columns(
            mapping_df,
            {"asset_id", "asset_name", "stock_code", "exchange", "company_name_cn", "company_name_en"},
            "company_mapping.csv",
            errors,
        )

    if VERIFIED_PATH.exists():
        verified_df = _read_csv(VERIFIED_PATH)
        tables["verified"] = verified_df
        _validate_required_columns(
            verified_df,
            PROJECT_REQUIRED_COLUMNS | VERIFIED_METADATA_COLUMNS,
            "financial_metrics_verified.csv",
            errors,
        )
        _validate_statuses(verified_df, "financial_metrics_verified.csv", errors)
        _validate_numeric_values(verified_df, NUMERIC_VERIFIED_COLUMNS, "financial_metrics_verified.csv", errors)
    else:
        errors.append(f"Missing verified output file: {VERIFIED_PATH}")

    if PREVIEW_PATH.exists():
        preview_df = _read_csv(PREVIEW_PATH)
        tables["preview"] = preview_df
        _validate_required_columns(preview_df, PREVIEW_COLUMNS, "replacement_preview.csv", errors)
        _validate_statuses(preview_df, "replacement_preview.csv", errors)
        _validate_numeric_values(preview_df, {"year", "old_value", "new_value"}, "replacement_preview.csv", errors)
    else:
        errors.append(f"Missing replacement preview file: {PREVIEW_PATH}")

    return errors, tables


def main() -> int:
    """CLI entry point."""
    try:
        errors, tables = validate_verified_financial_data()
    except Exception as exc:
        print(f"Verified financial data validation failed: {exc}")
        return 1

    if errors:
        print("Verified financial data validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Verified financial data validation passed.")
    verified_df = tables.get("verified", pd.DataFrame())
    preview_df = tables.get("preview", pd.DataFrame())
    if not verified_df.empty and "verification_status" in verified_df.columns:
        print("Verified output status summary:")
        print(verified_df["verification_status"].value_counts(dropna=False).to_string())
    else:
        print("Verified output contains no rows yet.")
    if not preview_df.empty and "field_name" in preview_df.columns:
        print("Replacement preview field summary:")
        print(preview_df["field_name"].value_counts(dropna=False).to_string())
    else:
        print("Replacement preview contains no replacement candidates yet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Transform optional public financial data into reviewable project outputs."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_FINANCIAL_PATH = PROJECT_ROOT / "data" / "financial_metrics.csv"
PUBLIC_RAW_PATH = PROJECT_ROOT / "data_verified" / "financial_metrics_public_raw.csv"
VERIFIED_OUTPUT_PATH = PROJECT_ROOT / "data_verified" / "financial_metrics_verified.csv"
PREVIEW_OUTPUT_PATH = PROJECT_ROOT / "data_verified" / "replacement_preview.csv"

REPLACEABLE_FIELDS = ["revenue", "operating_cash_flow", "total_assets", "total_debt", "debt_ratio"]
ESTIMATED_FIELDS = [
    "ebitda",
    "noi",
    "maintenance_capex",
    "estimated_affo",
    "estimated_distribution",
    "capex_to_ocf",
]
PROJECT_REQUIRED_COLUMNS = [
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
]
METADATA_COLUMNS = ["source_name", "source_url", "source_year", "verification_status", "last_verified_date"]
VERIFIED_COLUMNS = PROJECT_REQUIRED_COLUMNS + METADATA_COLUMNS
PREVIEW_COLUMNS = [
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
]


def _resolve_path(path: str | Path) -> Path:
    resolved = Path(path)
    if not resolved.is_absolute():
        resolved = PROJECT_ROOT / resolved
    return resolved


def load_demo_financial_metrics(path: str | Path = DEMO_FINANCIAL_PATH) -> pd.DataFrame:
    """Load the existing demo financial metrics."""
    resolved = _resolve_path(path)
    return pd.read_csv(resolved)


def load_public_raw(path: str | Path = PUBLIC_RAW_PATH) -> pd.DataFrame:
    """Load raw public financial data if generated."""
    resolved = _resolve_path(path)
    if not resolved.exists():
        return pd.DataFrame()
    return pd.read_csv(resolved, dtype={"stock_code": str})


def _has_value(value: Any) -> bool:
    if value is None or pd.isna(value):
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True


def _normalise_public_df(public_df: pd.DataFrame, mapping_df: pd.DataFrame) -> pd.DataFrame:
    if public_df.empty:
        return public_df.copy()

    output = public_df.copy()
    output["year"] = pd.to_numeric(output["year"], errors="coerce").astype("Int64")
    mapping = mapping_df[["asset_id", "asset_name", "stock_code"]].copy()
    mapping["stock_code"] = mapping["stock_code"].astype(str).str.zfill(6)
    if "asset_id" not in output.columns or output["asset_id"].isna().all():
        output["stock_code"] = output["stock_code"].astype(str).str.zfill(6)
        output = output.merge(mapping, on="stock_code", how="left", suffixes=("", "_mapped"))
        for column in ("asset_id", "asset_name"):
            mapped = f"{column}_mapped"
            if mapped in output.columns:
                output[column] = output[column].fillna(output[mapped])
                output = output.drop(columns=[mapped])
    return output


def _public_lookup(public_df: pd.DataFrame) -> dict[tuple[str, int], pd.Series]:
    lookup: dict[tuple[str, int], pd.Series] = {}
    if public_df.empty or "asset_id" not in public_df.columns or "year" not in public_df.columns:
        return lookup
    for _, row in public_df.iterrows():
        if not _has_value(row.get("asset_id")) or not _has_value(row.get("year")):
            continue
        lookup[(str(row["asset_id"]), int(row["year"]))] = row
    return lookup


def _row_metadata(public_row: pd.Series | None, replaced_fields: list[str]) -> dict[str, Any]:
    if public_row is None or not replaced_fields:
        return {
            "source_name": pd.NA,
            "source_url": pd.NA,
            "source_year": pd.NA,
            "verification_status": "simulated",
            "last_verified_date": pd.NA,
        }

    return {
        "source_name": public_row.get("source_name", pd.NA),
        "source_url": public_row.get("source_url", pd.NA),
        "source_year": public_row.get("source_year", pd.NA),
        "verification_status": public_row.get("verification_status", "public_collected"),
        "last_verified_date": date.today().isoformat(),
    }


def create_verified_financial_metrics(
    demo_df: pd.DataFrame,
    public_df: pd.DataFrame,
    mapping_df: pd.DataFrame,
) -> pd.DataFrame:
    """Create project-compatible financial metrics with reviewed public replacements."""
    public_df = _normalise_public_df(public_df, mapping_df)
    lookup = _public_lookup(public_df)
    rows: list[dict[str, Any]] = []

    for _, demo_row in demo_df.iterrows():
        asset_id = str(demo_row["asset_id"])
        year = int(demo_row["year"])
        public_row = lookup.get((asset_id, year))
        row = demo_row.to_dict()
        replaced_fields: list[str] = []

        if public_row is not None:
            for field in REPLACEABLE_FIELDS:
                new_value = public_row.get(field, pd.NA)
                if _has_value(new_value):
                    row[field] = new_value
                    replaced_fields.append(field)

        if replaced_fields:
            row["data_type"] = "mixed"
            row["source_note"] = (
                "Selected financial fields are from public financial data; NOI, AFFO, "
                "distribution, and maintenance CAPEX may remain estimated for portfolio prototype."
            )

        row.update(_row_metadata(public_row, replaced_fields))
        rows.append(row)

    output = pd.DataFrame(rows)
    for column in VERIFIED_COLUMNS:
        if column not in output.columns:
            output[column] = pd.NA
    return output[VERIFIED_COLUMNS]


def create_replacement_preview(
    demo_df: pd.DataFrame,
    public_df: pd.DataFrame,
    mapping_df: pd.DataFrame,
) -> pd.DataFrame:
    """Create long-format replacement candidates for manual review."""
    public_df = _normalise_public_df(public_df, mapping_df)
    lookup = _public_lookup(public_df)
    mapping_lookup = mapping_df.set_index("asset_id").to_dict(orient="index")
    rows: list[dict[str, Any]] = []

    for _, demo_row in demo_df.iterrows():
        asset_id = str(demo_row["asset_id"])
        year = int(demo_row["year"])
        public_row = lookup.get((asset_id, year))
        if public_row is None:
            continue

        for field in REPLACEABLE_FIELDS:
            new_value = public_row.get(field, pd.NA)
            if not _has_value(new_value):
                continue
            rows.append(
                {
                    "asset_id": asset_id,
                    "asset_name": mapping_lookup.get(asset_id, {}).get("asset_name", asset_id),
                    "stock_code": mapping_lookup.get(asset_id, {}).get("stock_code", public_row.get("stock_code", "")),
                    "year": year,
                    "field_name": field,
                    "old_value": demo_row.get(field, pd.NA),
                    "new_value": new_value,
                    "source_name": public_row.get("source_name", pd.NA),
                    "verification_status": public_row.get("verification_status", "public_collected"),
                    "notes": public_row.get("notes", pd.NA),
                }
            )

    return pd.DataFrame(rows, columns=PREVIEW_COLUMNS)


def save_verified_outputs(
    verified_df: pd.DataFrame,
    preview_df: pd.DataFrame,
    verified_path: str | Path = VERIFIED_OUTPUT_PATH,
    preview_path: str | Path = PREVIEW_OUTPUT_PATH,
) -> tuple[Path, Path]:
    """Write verified metrics and replacement preview outputs."""
    resolved_verified = _resolve_path(verified_path)
    resolved_preview = _resolve_path(preview_path)
    resolved_verified.parent.mkdir(parents=True, exist_ok=True)
    resolved_preview.parent.mkdir(parents=True, exist_ok=True)
    verified_df.to_csv(resolved_verified, index=False, encoding="utf-8-sig")
    preview_df.to_csv(resolved_preview, index=False, encoding="utf-8-sig")
    return resolved_verified, resolved_preview

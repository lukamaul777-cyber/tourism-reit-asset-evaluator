"""Fetch optional public financial data and create reviewable verified outputs."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.public_data_fetcher import (  # noqa: E402
    fetch_all_target_financials,
    load_company_mapping,
    save_public_raw_data,
)
from src.verified_data_pipeline import (  # noqa: E402
    REPLACEABLE_FIELDS,
    create_replacement_preview,
    create_verified_financial_metrics,
    load_demo_financial_metrics,
    save_verified_outputs,
)


def _summarize_raw(raw_df: pd.DataFrame) -> dict[str, int]:
    value_counts = {
        field: int(pd.to_numeric(raw_df.get(field, pd.Series(dtype=float)), errors="coerce").notna().sum())
        for field in REPLACEABLE_FIELDS
    }
    return value_counts


def main() -> int:
    """Run the optional public-financial-data update workflow."""
    try:
        mapping_df = load_company_mapping()
        demo_df = load_demo_financial_metrics()
    except Exception as exc:
        print(f"Public financial data update failed before fetching: {exc}")
        return 1

    print("Fetching public financial data for mapped target companies...")
    raw_df = fetch_all_target_financials(mapping_df, start_year=2021, end_year=2024)
    raw_path = save_public_raw_data(raw_df)

    verified_df = create_verified_financial_metrics(demo_df, raw_df, mapping_df)
    preview_df = create_replacement_preview(demo_df, raw_df, mapping_df)
    verified_path, preview_path = save_verified_outputs(verified_df, preview_df)

    status_counts = raw_df["verification_status"].value_counts(dropna=False).to_dict() if not raw_df.empty else {}
    fetched_counts = _summarize_raw(raw_df)
    missing_counts = {field: int(len(raw_df) - count) for field, count in fetched_counts.items()}

    print("Public financial data update completed.")
    print(f"Companies processed: {mapping_df['asset_id'].nunique()}")
    print(f"Years processed: {raw_df['year'].nunique() if 'year' in raw_df.columns and not raw_df.empty else 0}")
    print(f"Raw rows written: {len(raw_df)}")
    print(f"Replacement candidates generated: {len(preview_df)}")
    print("Verification status counts:")
    for status, count in status_counts.items():
        print(f"- {status}: {count}")
    print("Fields fetched:")
    for field, count in fetched_counts.items():
        print(f"- {field}: {count}")
    print("Fields missing:")
    for field, count in missing_counts.items():
        print(f"- {field}: {count}")
    print("Output files:")
    print(f"- {raw_path}")
    print(f"- {verified_path}")
    print(f"- {preview_path}")
    print("Demo data was not overwritten. Review replacement_preview.csv before using verified outputs.")

    if raw_df["verification_status"].eq("fetch_failed").all() if not raw_df.empty else True:
        print("No public replacement values were fetched. If AKShare is not installed, run: python -m pip install akshare")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Inspect A-module indicator-level scoring details for demo and verified data."""

from __future__ import annotations

import sys
import importlib.util
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.field_source_utils import classify_field_source  # noqa: E402
from src.scoring_model import MODULE_ORDER, run_scoring_pipeline  # noqa: E402


MODULE_A = MODULE_ORDER[0]
REQUIRED_INDICATORS = ["A1", "A2", "A5", "A6", "A7", "A8"]
REQUIRED_FIELD_MAP = {
    "A1": "derived_ocf_positive_ratio_past3",
    "A2": "derived_affo_distribution_coverage",
    "A5": "derived_ocf_margin",
    "A6": "derived_debt_ratio",
    "A7": "derived_revenue_stability",
    "A8": "derived_ocf_stability",
}
PAGE_PATH = PROJECT_ROOT / "pages" / "3_REIT_Fit_Score.py"
DISPLAY_COLUMNS = [
    "asset_id",
    "asset_name",
    "indicator_id",
    "indicator_name_en",
    "indicator_name_zh",
    "raw_value",
    "normalized_score",
    "direction",
    "included_in_score",
    "data_note",
]


def _load_score_page_module():
    spec = importlib.util.spec_from_file_location("reit_fit_score_page", PAGE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to import page module from {PAGE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fmt(value: object) -> str:
    if value is None or pd.isna(value):
        return "Missing"
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def inspect_source(source: str) -> list[str]:
    indicator_scores_df, _module_scores_df, _total_scores_df = run_scoring_pipeline(
        selected_source=source,
    )
    module_a_df = indicator_scores_df[indicator_scores_df["module"] == MODULE_A].copy()
    warnings: list[str] = []

    print("=" * 120)
    print(f"Financial data source: {source}")
    print(
        module_a_df[DISPLAY_COLUMNS].to_string(
            index=False,
            formatters={
                "raw_value": _fmt,
                "normalized_score": _fmt,
            },
        )
    )

    for asset_id, group in module_a_df.groupby("asset_id"):
        present_ids = set(group["indicator_id"].astype(str))
        missing_ids = [indicator_id for indicator_id in REQUIRED_INDICATORS if indicator_id not in present_ids]
        if missing_ids:
            warnings.append(f"{source} {asset_id}: missing indicator records {', '.join(missing_ids)}.")
            continue

        derived_rows = group[group["indicator_id"].isin(["A5", "A6", "A7", "A8"])]
        for row in derived_rows.itertuples(index=False):
            if pd.isna(row.raw_value) or pd.isna(row.normalized_score):
                warnings.append(
                    f"{source} {asset_id} {row.indicator_id}: raw_value or normalized_score is missing."
                )
        for indicator_id, field_name in REQUIRED_FIELD_MAP.items():
            label = classify_field_source(field_name, language="en")["field_source_label"]
            if label != "Model-derived indicator":
                warnings.append(f"{source} {asset_id} {indicator_id}: field source is {label}, expected model-derived.")

    return warnings


def main() -> int:
    warnings: list[str] = []
    page_module = _load_score_page_module()
    for source in ["demo", "verified"]:
        warnings.extend(inspect_source(source))

    indicator_scores_df, _module_scores_df, _total_scores_df = run_scoring_pipeline(selected_source="demo")
    sample_df = indicator_scores_df[indicator_scores_df["asset_id"] == "A_TIANMU"].copy()
    intentionally_missing_columns = sample_df.drop(
        columns=[
            column
            for column in [
                "included_in_score",
                "normalized_score",
                "raw_value",
                "data_note",
                "direction",
                "indicator_name_en",
                "indicator_name_zh",
            ]
            if column in sample_df.columns
        ]
    )
    display_df, missing_ids = page_module.normalize_module_a_indicator_details(intentionally_missing_columns)
    if missing_ids:
        warnings.append("Page helper unexpectedly reported missing Module A records: " + ", ".join(missing_ids))
    if display_df.empty:
        warnings.append("Page helper returned an empty display dataframe for fallback-column test.")
    if "Field Source" not in display_df.columns:
        warnings.append("Page helper display dataframe is missing the Field Source column.")
    elif set(display_df["Field Source"].astype(str)) != {"Model-derived indicator"}:
        warnings.append("Page helper did not label all Module A details as model-derived indicators.")

    if warnings:
        print("\nWARNING")
        for warning in warnings:
            print(f"- {warning}")
        return 1

    print("\nSuccess summary")
    print("A1, A2, and A5-A8 indicator-level details are present for all assets.")
    print("A5-A8 include raw_value and normalized_score for all assets.")
    print("A1, A2, and A5-A8 are classified as model-derived indicators.")
    print("Module A page helper tolerates missing optional display columns.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

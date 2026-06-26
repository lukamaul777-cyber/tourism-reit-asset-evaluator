"""Compare REIT Fit Score outputs between demo and verified financial data."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_loader import (  # noqa: E402
    get_effective_financial_data_source,
    load_financial_metrics,
    resolve_financial_data_path,
)
from src.scoring_model import MODULE_ORDER, load_scoring_data, run_scoring_pipeline  # noqa: E402


CASHFLOW_MODULE = MODULE_ORDER[0]
CORE_FINANCIAL_FIELDS = [
    "revenue",
    "operating_cash_flow",
    "total_assets",
    "total_debt",
    "debt_ratio",
]


def _module_score(module_scores_df: pd.DataFrame, asset_id: str, module_name: str) -> float | None:
    matched = module_scores_df[
        (module_scores_df["asset_id"] == asset_id)
        & (module_scores_df["module"] == module_name)
    ]
    if matched.empty:
        return None
    value = matched.iloc[0]["module_score"]
    return None if pd.isna(value) else float(value)


def _score_table(source: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    scoring_df, _tables = load_scoring_data(selected_source=source)
    _indicator_scores_df, module_scores_df, total_scores_df = run_scoring_pipeline(
        selected_source=source,
    )
    return scoring_df, module_scores_df, total_scores_df


def _scoring_metric(scoring_df: pd.DataFrame, asset_id: str, column: str) -> float | None:
    matched = scoring_df[scoring_df["asset_id"] == asset_id]
    if matched.empty or column not in matched.columns:
        return None
    value = matched.iloc[0][column]
    return None if pd.isna(value) else float(value)


def _core_financial_fields_differ(demo_df: pd.DataFrame, verified_df: pd.DataFrame, asset_id: str) -> bool:
    demo_asset = demo_df[demo_df["asset_id"] == asset_id].copy()
    verified_asset = verified_df[verified_df["asset_id"] == asset_id].copy()
    if demo_asset.empty or verified_asset.empty:
        return False

    merged = demo_asset.merge(
        verified_asset,
        on=["asset_id", "year"],
        suffixes=("_demo", "_verified"),
    )
    for field in CORE_FINANCIAL_FIELDS:
        demo_values = pd.to_numeric(merged[f"{field}_demo"], errors="coerce")
        verified_values = pd.to_numeric(merged[f"{field}_verified"], errors="coerce")
        if not demo_values.equals(verified_values):
            return True
    return False


def _validate_tianmu_revenue_diff(demo_df: pd.DataFrame, verified_df: pd.DataFrame) -> None:
    demo_revenue = demo_df.loc[
        (demo_df["asset_id"] == "A_TIANMU") & (demo_df["year"] == 2024),
        "revenue",
    ]
    verified_revenue = verified_df.loc[
        (verified_df["asset_id"] == "A_TIANMU") & (verified_df["year"] == 2024),
        "revenue",
    ]
    if demo_revenue.empty or verified_revenue.empty:
        raise AssertionError("Tianmu Lake 2024 revenue row is missing in demo or verified data.")

    demo_value = float(demo_revenue.iloc[0])
    verified_value = float(verified_revenue.iloc[0])
    if demo_value == verified_value:
        raise AssertionError(
            "Expected Tianmu Lake 2024 revenue to differ between demo and verified data, "
            f"but both were {demo_value}."
        )

    print(
        "Validation: Tianmu Lake 2024 revenue differs "
        f"(demo={demo_value:.4f}, verified={verified_value:.4f})."
    )


def _validate_scoring_dataframes_differ() -> None:
    _demo_scoring_df, demo_tables = load_scoring_data(selected_source="demo")
    _verified_scoring_df, verified_tables = load_scoring_data(selected_source="verified")
    demo_financial = demo_tables["financial_metrics"]
    verified_financial = verified_tables["financial_metrics"]

    demo_revenue = float(
        demo_financial.loc[
            (demo_financial["asset_id"] == "A_TIANMU") & (demo_financial["year"] == 2024),
            "revenue",
        ].iloc[0]
    )
    verified_revenue = float(
        verified_financial.loc[
            (verified_financial["asset_id"] == "A_TIANMU") & (verified_financial["year"] == 2024),
            "revenue",
        ].iloc[0]
    )
    if demo_revenue == verified_revenue:
        raise AssertionError("Scoring dataframes did not reflect different selected financial sources.")

    print("Validation: scoring pipeline received different financial dataframes.")


def main() -> int:
    verified_path, effective_source, did_fallback, _warning_key = resolve_financial_data_path("verified")
    requested_effective_source, requested_did_fallback, _ = get_effective_financial_data_source("verified")
    verified_exists = verified_path.exists() and effective_source == "verified"

    print(f"Verified financial file: {verified_path}")
    if did_fallback or requested_did_fallback or requested_effective_source != "verified":
        print("WARNING: verified financial file is unavailable; comparison uses demo fallback.")

    demo_financial_df = load_financial_metrics("demo")
    verified_financial_df = load_financial_metrics("verified")

    if verified_exists:
        _validate_tianmu_revenue_diff(demo_financial_df, verified_financial_df)
        _validate_scoring_dataframes_differ()

    demo_scoring_df, demo_modules_df, demo_total_df = _score_table("demo")
    verified_scoring_df, verified_modules_df, verified_total_df = _score_table("verified")

    rows: list[dict[str, object]] = []
    warnings: list[str] = []
    changed_assets: list[str] = []

    for demo_row in demo_total_df.sort_values("asset_id").itertuples(index=False):
        asset_id = str(demo_row.asset_id)
        verified_row = verified_total_df[verified_total_df["asset_id"] == asset_id].iloc[0]

        demo_score = float(demo_row.total_score)
        verified_score = float(verified_row["total_score"])
        demo_cashflow = _module_score(demo_modules_df, asset_id, CASHFLOW_MODULE)
        verified_cashflow = _module_score(verified_modules_df, asset_id, CASHFLOW_MODULE)
        score_diff = verified_score - demo_score
        cashflow_diff = (
            None
            if demo_cashflow is None or verified_cashflow is None
            else verified_cashflow - demo_cashflow
        )

        rows.append(
            {
                "asset_id": asset_id,
                "asset_name": demo_row.asset_name,
                "demo_score": demo_score,
                "verified_score": verified_score,
                "score_diff": score_diff,
                "demo_cashflow_module_score": demo_cashflow,
                "verified_cashflow_module_score": verified_cashflow,
                "cashflow_module_diff": cashflow_diff,
                "demo_ocf_margin": _scoring_metric(demo_scoring_df, asset_id, "derived_ocf_margin"),
                "verified_ocf_margin": _scoring_metric(verified_scoring_df, asset_id, "derived_ocf_margin"),
                "demo_debt_ratio": _scoring_metric(demo_scoring_df, asset_id, "derived_debt_ratio"),
                "verified_debt_ratio": _scoring_metric(verified_scoring_df, asset_id, "derived_debt_ratio"),
                "demo_revenue_stability": _scoring_metric(
                    demo_scoring_df,
                    asset_id,
                    "derived_revenue_stability",
                ),
                "verified_revenue_stability": _scoring_metric(
                    verified_scoring_df,
                    asset_id,
                    "derived_revenue_stability",
                ),
            }
        )

        core_fields_differ = _core_financial_fields_differ(
            demo_financial_df,
            verified_financial_df,
            asset_id,
        )
        score_unchanged = abs(score_diff) < 1e-9
        cashflow_unchanged = cashflow_diff is not None and abs(cashflow_diff) < 1e-9

        if verified_exists and core_fields_differ and score_unchanged and cashflow_unchanged:
            warnings.append(
                f"{asset_id}: core financial fields differ, but total score and cash-flow module score are unchanged."
            )
        if not score_unchanged or not cashflow_unchanged:
            changed_assets.append(asset_id)

    comparison_df = pd.DataFrame(rows)
    print("\nScore comparison")
    print(
        comparison_df.to_string(
            index=False,
            formatters={
                "demo_score": "{:.6f}".format,
                "verified_score": "{:.6f}".format,
                "score_diff": "{:.6f}".format,
                "demo_cashflow_module_score": lambda value: "N/A" if pd.isna(value) else f"{value:.6f}",
                "verified_cashflow_module_score": lambda value: "N/A" if pd.isna(value) else f"{value:.6f}",
                "cashflow_module_diff": lambda value: "N/A" if pd.isna(value) else f"{value:.6f}",
                "demo_ocf_margin": lambda value: "N/A" if pd.isna(value) else f"{value:.6f}",
                "verified_ocf_margin": lambda value: "N/A" if pd.isna(value) else f"{value:.6f}",
                "demo_debt_ratio": lambda value: "N/A" if pd.isna(value) else f"{value:.6f}",
                "verified_debt_ratio": lambda value: "N/A" if pd.isna(value) else f"{value:.6f}",
                "demo_revenue_stability": lambda value: "N/A" if pd.isna(value) else f"{value:.6f}",
                "verified_revenue_stability": lambda value: "N/A" if pd.isna(value) else f"{value:.6f}",
            },
        )
    )

    if warnings:
        print("\nWARNING")
        for warning in warnings:
            print(f"- {warning}")
        print(
            "Reason: the selected financial inputs differ, but the current peer-normalized "
            "indicators may still produce identical ranks or neutral scores when the changed "
            "values do not alter peer ordering, when all peer values are equal, or when changed "
            "fields are not used by available scoring indicators."
        )

    if changed_assets:
        print("\nChanged assets summary")
        print(", ".join(changed_assets))
    else:
        print("\nChanged assets summary")
        print("No asset score changed under the current scoring framework.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

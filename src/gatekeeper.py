"""Regulatory-style gatekeeper checks for tourism REIT asset evaluation.

This module implements a transparent portfolio prototype pre-screen. It is not
an official regulatory review, credit rating, valuation opinion, or investment
recommendation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

try:
    from src.data_loader import load_financial_metrics
except ModuleNotFoundError:  # Allows `python src/gatekeeper.py`.
    from data_loader import load_financial_metrics  # type: ignore


HARD_CONDITIONS = {
    "ownership_clear",
    "no_major_legal_dispute",
    "operating_history",
    "stable_operating_cash_flow",
    "market_based_cash_flow",
    "distribution_capacity",
}

WARNING_CONDITIONS = {
    "capex_pressure_warning",
    "continuous_operation_warning",
}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _resolve_data_dir(data_dir: str | Path) -> Path:
    path = Path(data_dir)
    if not path.is_absolute():
        path = _project_root() / path
    return path


def _clean_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def _to_bool_or_none(value: Any) -> bool | None:
    if pd.isna(value) or str(value).strip() == "":
        return None
    if isinstance(value, bool):
        return value

    normalized = _clean_text(value)
    if normalized in {"true", "yes", "y", "1", "pass", "passed"}:
        return True
    if normalized in {"false", "no", "n", "0", "fail", "failed"}:
        return False
    return None


def _to_number_or_none(value: Any) -> float | None:
    if pd.isna(value) or str(value).strip() == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _result(
    condition: str,
    status: str,
    explanation: str,
    reference_logic: str,
) -> dict[str, str]:
    return {
        "condition": condition,
        "status": status,
        "explanation": explanation,
        "reference_logic": reference_logic,
    }


def _latest_rows_by_asset(df: pd.DataFrame) -> pd.DataFrame:
    """Return the latest available row for each asset_id."""
    if df.empty:
        return df.copy()

    latest_df = df.copy()
    latest_df["year"] = pd.to_numeric(latest_df["year"], errors="coerce")
    latest_df = latest_df.dropna(subset=["asset_id", "year"])
    latest_df = latest_df.sort_values(["asset_id", "year"])
    return latest_df.groupby("asset_id", as_index=False).tail(1)


def load_gatekeeper_data(
    data_dir: str | Path = "data",
    financial_data_source: str = "demo",
) -> pd.DataFrame:
    """Load and merge assets with latest financial and risk metrics.

    Returns an asset-level dataframe using:
    - ``assets.csv``
    - latest available year from ``financial_metrics.csv``
    - latest available year from ``risk_metrics.csv``
    """
    base_dir = _resolve_data_dir(data_dir)
    assets_df = pd.read_csv(base_dir / "assets.csv")
    financial_df = load_financial_metrics(financial_data_source)
    risk_df = pd.read_csv(base_dir / "risk_metrics.csv")

    latest_financial_df = _latest_rows_by_asset(financial_df).add_prefix("financial_")
    latest_risk_df = _latest_rows_by_asset(risk_df).add_prefix("risk_")

    merged_df = assets_df.merge(
        latest_financial_df,
        left_on="asset_id",
        right_on="financial_asset_id",
        how="left",
    )
    merged_df = merged_df.merge(
        latest_risk_df,
        left_on="asset_id",
        right_on="risk_asset_id",
        how="left",
    )

    return merged_df


def check_ownership_clear(row: pd.Series) -> dict[str, str]:
    ownership_status = _clean_text(row.get("ownership_status"))
    reference_logic = "Regulatory-style requirement: ownership or operation rights should be clear."

    if ownership_status in {"clear", "operation_right_clear"}:
        return _result(
            "ownership_clear",
            "Pass",
            f"ownership_status is '{ownership_status}', which indicates clear rights for this prototype.",
            reference_logic,
        )
    if ownership_status in {"", "missing", "unclear", "disputed"}:
        label = "missing" if ownership_status == "" else ownership_status
        return _result(
            "ownership_clear",
            "Fail",
            f"ownership_status is '{label}', so the asset does not pass the clear-rights pre-screen.",
            reference_logic,
        )
    return _result(
        "ownership_clear",
        "Fail",
        f"ownership_status is '{ownership_status}', which is not an accepted pass value.",
        reference_logic,
    )


def check_no_major_legal_dispute(row: pd.Series) -> dict[str, str]:
    has_dispute = _to_bool_or_none(row.get("has_major_legal_dispute"))
    reference_logic = "Regulatory-style requirement: assets should not have major legal disputes."

    if has_dispute is False:
        return _result(
            "no_major_legal_dispute",
            "Pass",
            "has_major_legal_dispute is False.",
            reference_logic,
        )
    if has_dispute is True:
        return _result(
            "no_major_legal_dispute",
            "Fail",
            "has_major_legal_dispute is True.",
            reference_logic,
        )
    return _result(
        "no_major_legal_dispute",
        "Warning",
        "has_major_legal_dispute is missing or not interpretable.",
        reference_logic,
    )


def check_operating_history(row: pd.Series) -> dict[str, str]:
    operation_years = _to_number_or_none(row.get("operation_years"))
    reference_logic = "Regulatory-style requirement: assets should have an operating history of around 3 years or more."

    if operation_years is None:
        return _result(
            "operating_history",
            "Warning",
            "operation_years is missing or not numeric.",
            reference_logic,
        )
    if operation_years >= 3:
        return _result(
            "operating_history",
            "Pass",
            f"operation_years is {operation_years:g}, meeting the prototype 3-year operating-history check.",
            reference_logic,
        )
    return _result(
        "operating_history",
        "Fail",
        f"operation_years is {operation_years:g}, below the prototype 3-year operating-history check.",
        reference_logic,
    )


def check_stable_operating_cash_flow(asset_id: str, financial_df: pd.DataFrame) -> dict[str, str]:
    reference_logic = (
        "Regulatory-style requirement: operating cash flow should be positive in the latest year "
        "and positive in at least 2 of the past 3 available years."
    )
    asset_financials = financial_df[financial_df["asset_id"] == asset_id].copy()

    if asset_financials.empty:
        return _result(
            "stable_operating_cash_flow",
            "Warning",
            "No financial_metrics rows are available for this asset.",
            reference_logic,
        )

    asset_financials["year"] = pd.to_numeric(asset_financials["year"], errors="coerce")
    asset_financials["operating_cash_flow"] = pd.to_numeric(
        asset_financials["operating_cash_flow"],
        errors="coerce",
    )
    asset_financials = asset_financials.dropna(subset=["year"]).sort_values("year")
    recent = asset_financials.tail(3)

    if recent.empty or pd.isna(recent.iloc[-1]["operating_cash_flow"]):
        return _result(
            "stable_operating_cash_flow",
            "Warning",
            "Latest-year operating_cash_flow is missing.",
            reference_logic,
        )

    latest_year = int(recent.iloc[-1]["year"])
    latest_ocf = float(recent.iloc[-1]["operating_cash_flow"])
    positive_count = int((recent["operating_cash_flow"] > 0).sum())

    if latest_ocf <= 0:
        return _result(
            "stable_operating_cash_flow",
            "Fail",
            f"Latest available year {latest_year} operating_cash_flow is {latest_ocf:g}, which is not positive.",
            reference_logic,
        )

    if len(recent) < 3:
        return _result(
            "stable_operating_cash_flow",
            "Warning",
            f"Latest operating_cash_flow is positive, but only {len(recent)} years of data are available.",
            reference_logic,
        )

    if positive_count >= 2:
        return _result(
            "stable_operating_cash_flow",
            "Pass",
            f"Latest operating_cash_flow is positive and {positive_count} of the past {len(recent)} years are positive.",
            reference_logic,
        )

    return _result(
        "stable_operating_cash_flow",
        "Fail",
        f"Only {positive_count} of the past {len(recent)} years have positive operating_cash_flow.",
        reference_logic,
    )


def check_market_based_cash_flow(row: pd.Series) -> dict[str, str]:
    cash_flow_source_type = _clean_text(row.get("cash_flow_source_type"))
    reference_logic = "Regulatory-style requirement: cash flow should mainly come from market-based operating sources."

    if cash_flow_source_type in {"market_based", "mostly_market_based"}:
        return _result(
            "market_based_cash_flow",
            "Pass",
            f"cash_flow_source_type is '{cash_flow_source_type}'.",
            reference_logic,
        )
    if cash_flow_source_type in {"subsidy_dependent", "non_recurring"}:
        return _result(
            "market_based_cash_flow",
            "Fail",
            f"cash_flow_source_type is '{cash_flow_source_type}', which is not market-based recurring cash flow.",
            reference_logic,
        )
    if cash_flow_source_type == "":
        return _result(
            "market_based_cash_flow",
            "Warning",
            "cash_flow_source_type is missing.",
            reference_logic,
        )
    return _result(
        "market_based_cash_flow",
        "Warning",
        f"cash_flow_source_type is '{cash_flow_source_type}', which is not a recognized prototype category.",
        reference_logic,
    )


def check_distribution_capacity(row: pd.Series) -> dict[str, str]:
    estimated_affo = _to_number_or_none(row.get("financial_estimated_affo"))
    estimated_distribution = _to_number_or_none(row.get("financial_estimated_distribution"))
    reference_logic = "Regulatory-style requirement: recurring cash flow should support distributable cash flow."

    if estimated_affo is None or estimated_distribution is None:
        return _result(
            "distribution_capacity",
            "Warning",
            "estimated_affo or estimated_distribution is missing in the latest available year.",
            reference_logic,
        )
    if estimated_affo >= estimated_distribution:
        return _result(
            "distribution_capacity",
            "Pass",
            f"Latest estimated_affo ({estimated_affo:g}) is greater than or equal to estimated_distribution ({estimated_distribution:g}).",
            reference_logic,
        )
    return _result(
        "distribution_capacity",
        "Fail",
        f"Latest estimated_affo ({estimated_affo:g}) is below estimated_distribution ({estimated_distribution:g}).",
        reference_logic,
    )


def check_capex_pressure_warning(row: pd.Series, financial_df: pd.DataFrame) -> dict[str, str]:
    reference_logic = (
        "Prototype warning logic: capex pressure is compared with the sample distribution; "
        "this is not an official threshold."
    )
    capex_to_ocf = _to_number_or_none(row.get("financial_capex_to_ocf"))

    latest_financial_df = _latest_rows_by_asset(financial_df)
    sample_values = pd.to_numeric(latest_financial_df["capex_to_ocf"], errors="coerce").dropna()

    if capex_to_ocf is None or sample_values.empty:
        return _result(
            "capex_pressure_warning",
            "Warning",
            "capex_to_ocf is missing or no comparable sample is available.",
            reference_logic,
        )

    percentile_75 = float(sample_values.quantile(0.75))
    if capex_to_ocf >= percentile_75:
        return _result(
            "capex_pressure_warning",
            "Warning",
            f"Latest capex_to_ocf ({capex_to_ocf:.2f}) is at or above the sample 75th percentile ({percentile_75:.2f}).",
            reference_logic,
        )

    return _result(
        "capex_pressure_warning",
        "Pass",
        f"Latest capex_to_ocf ({capex_to_ocf:.2f}) is below the sample 75th percentile ({percentile_75:.2f}).",
        reference_logic,
    )


def check_continuous_operation_warning(row: pd.Series, risk_df: pd.DataFrame) -> dict[str, str]:
    reference_logic = (
        "Prototype warning logic: operation-risk indicators are compared with the sample distribution; "
        "this is not an official threshold."
    )
    risk_columns = ["policy_risk", "climate_physical_risk", "financial_pressure_risk"]
    latest_risk_df = _latest_rows_by_asset(risk_df)
    warning_details: list[str] = []
    missing_details: list[str] = []

    for column in risk_columns:
        row_value = _to_number_or_none(row.get(f"risk_{column}"))
        sample_values = pd.to_numeric(latest_risk_df[column], errors="coerce").dropna()

        if row_value is None or sample_values.empty:
            missing_details.append(column)
            continue

        percentile_75 = float(sample_values.quantile(0.75))
        if row_value >= percentile_75:
            warning_details.append(f"{column} {row_value:.2f} >= sample 75th percentile {percentile_75:.2f}")

    if missing_details:
        return _result(
            "continuous_operation_warning",
            "Warning",
            "Missing or non-comparable risk fields: " + ", ".join(missing_details) + ".",
            reference_logic,
        )
    if warning_details:
        return _result(
            "continuous_operation_warning",
            "Warning",
            "; ".join(warning_details) + ".",
            reference_logic,
        )

    return _result(
        "continuous_operation_warning",
        "Pass",
        "Policy, climate physical, and financial pressure risks are below the sample 75th percentile.",
        reference_logic,
    )


def run_gatekeeper_checks(
    asset_id: str,
    data_dir: str | Path = "data",
    financial_data_source: str = "demo",
) -> tuple[pd.DataFrame, str, str]:
    """Run all gatekeeper checks for one asset.

    Returns
    -------
    tuple
        ``(gatekeeper_results, overall_status, summary_text)``.
    """
    base_dir = _resolve_data_dir(data_dir)
    assets_merged_df = load_gatekeeper_data(base_dir, financial_data_source)
    financial_df = load_financial_metrics(financial_data_source)
    risk_df = pd.read_csv(base_dir / "risk_metrics.csv")

    matched_rows = assets_merged_df[assets_merged_df["asset_id"] == asset_id]
    if matched_rows.empty:
        raise ValueError(f"Unknown asset_id: {asset_id}")

    row = matched_rows.iloc[0]
    results = [
        check_ownership_clear(row),
        check_no_major_legal_dispute(row),
        check_operating_history(row),
        check_stable_operating_cash_flow(asset_id, financial_df),
        check_market_based_cash_flow(row),
        check_distribution_capacity(row),
        check_capex_pressure_warning(row, financial_df),
        check_continuous_operation_warning(row, risk_df),
    ]
    results_df = pd.DataFrame(results)

    hard_fail_exists = bool(
        (results_df["condition"].isin(HARD_CONDITIONS) & (results_df["status"] == "Fail")).any()
    )
    warning_exists = bool((results_df["status"] == "Warning").any())

    if hard_fail_exists:
        overall_status = "Fail"
    elif warning_exists:
        overall_status = "Pass with Warning"
    else:
        overall_status = "Pass"

    asset_name = row.get("asset_name", asset_id)
    failed_conditions = results_df.loc[results_df["status"] == "Fail", "condition"].tolist()
    warning_conditions = results_df.loc[results_df["status"] == "Warning", "condition"].tolist()

    summary_parts = [
        f"{asset_name} ({asset_id}) gatekeeper status: {overall_status}.",
        "This is a portfolio prototype pre-screen, not an official regulatory conclusion.",
    ]
    if failed_conditions:
        summary_parts.append("Failed hard conditions: " + ", ".join(failed_conditions) + ".")
    if warning_conditions:
        summary_parts.append("Warnings: " + ", ".join(warning_conditions) + ".")

    return results_df, overall_status, " ".join(summary_parts)


def _print_demo_results(data_dir: str | Path = "data") -> None:
    base_dir = _resolve_data_dir(data_dir)
    assets_df = pd.read_csv(base_dir / "assets.csv")

    for asset_id in assets_df["asset_id"].dropna().astype(str):
        results_df, overall_status, summary_text = run_gatekeeper_checks(asset_id, base_dir)
        print("=" * 88)
        print(summary_text)
        print(f"Overall status: {overall_status}")
        print(results_df[["condition", "status", "explanation"]].to_string(index=False))


if __name__ == "__main__":
    _print_demo_results()

"""Scenario simulation backend for the Tourism REIT Asset Evaluator.

Scenario outputs are simulated estimates for portfolio demonstration. They are
not forecasts, investment recommendations, valuation opinions, or regulatory
conclusions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml

try:
    from src.scoring_model import (
        calculate_indicator_scores,
        calculate_module_scores,
        calculate_total_scores,
        load_scoring_data,
    )
except ModuleNotFoundError:  # Allows `python src/scenario_simulator.py`.
    from scoring_model import (  # type: ignore
        calculate_indicator_scores,
        calculate_module_scores,
        calculate_total_scores,
        load_scoring_data,
    )


PARAMETER_RANGES = {
    "revenue_decline_pct": (0.0, 0.50),
    "visitor_volume_decline_pct": (0.0, 0.50),
    "occupancy_decline_pct": (0.0, 0.30),
    "adr_decline_pct": (0.0, 0.30),
    "operating_cost_increase_pct": (0.0, 0.50),
    "maintenance_capex_increase_pct": (0.0, 0.50),
    "ota_score_decline": (0.0, 1.00),
}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _resolve_data_dir(data_dir: str | Path) -> Path:
    path = Path(data_dir)
    if not path.is_absolute():
        path = _project_root() / path
    return path


def _load_indicator_config() -> dict[str, Any]:
    config_path = _project_root() / "config" / "indicator_framework.yml"
    with config_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def _to_float(value: Any) -> float | None:
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_divide(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _validate_parameter(name: str, value: float) -> None:
    lower_bound, upper_bound = PARAMETER_RANGES[name]
    if value < lower_bound or value > upper_bound:
        raise ValueError(
            f"{name} must be between {lower_bound:.2f} and {upper_bound:.2f}; received {value:.4f}."
        )


def load_base_scenario_data(
    data_dir: str | Path = "data",
    financial_data_source: str = "demo",
) -> pd.DataFrame:
    """Return latest-year merged data needed for scenario simulation."""
    scoring_df, _raw_tables = load_scoring_data(_resolve_data_dir(data_dir), financial_data_source)
    return scoring_df


def _recalculate_scores_from_adjusted_dataframe(
    adjusted_scoring_df: pd.DataFrame,
    weight_mode: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    indicator_config = _load_indicator_config()
    indicator_scores_df = calculate_indicator_scores(adjusted_scoring_df, indicator_config)
    module_scores_df = calculate_module_scores(indicator_scores_df)
    total_scores_df = calculate_total_scores(module_scores_df, weight_mode)
    return indicator_scores_df, module_scores_df, total_scores_df


def _set_if_column_exists(df: pd.DataFrame, index: Any, column: str, value: float | None) -> None:
    if column in df.columns:
        df[column] = pd.to_numeric(df[column], errors="coerce").astype("float64")
        df.at[index, column] = pd.NA if value is None else value


def simulate_asset_scenario(
    asset_id: str,
    revenue_decline_pct: float = 0.0,
    visitor_volume_decline_pct: float = 0.0,
    occupancy_decline_pct: float = 0.0,
    adr_decline_pct: float = 0.0,
    operating_cost_increase_pct: float = 0.0,
    maintenance_capex_increase_pct: float = 0.0,
    ota_score_decline: float = 0.0,
    data_dir: str | Path = "data",
    weight_mode: str = "default_expert_weight",
    financial_data_source: str = "demo",
) -> dict[str, Any]:
    """Simulate asset-level downside shocks and recalculate the suitability score."""
    parameters = {
        "revenue_decline_pct": revenue_decline_pct,
        "visitor_volume_decline_pct": visitor_volume_decline_pct,
        "occupancy_decline_pct": occupancy_decline_pct,
        "adr_decline_pct": adr_decline_pct,
        "operating_cost_increase_pct": operating_cost_increase_pct,
        "maintenance_capex_increase_pct": maintenance_capex_increase_pct,
        "ota_score_decline": ota_score_decline,
    }
    for parameter_name, parameter_value in parameters.items():
        _validate_parameter(parameter_name, parameter_value)

    base_scoring_df, _raw_tables = load_scoring_data(_resolve_data_dir(data_dir), financial_data_source)
    base_indicator_scores_df, base_module_scores_df, base_total_scores_df = _recalculate_scores_from_adjusted_dataframe(
        base_scoring_df,
        weight_mode,
    )

    matched_rows = base_scoring_df[base_scoring_df["asset_id"] == asset_id]
    if matched_rows.empty:
        raise ValueError(f"Unknown asset_id: {asset_id}")

    row_index = matched_rows.index[0]
    base_row = base_scoring_df.loc[row_index]
    asset_name = str(base_row["asset_name"])
    warnings: list[str] = [
        "Scenario outputs are simulated estimates for portfolio demonstration; they are not forecasts."
    ]

    revenue = _to_float(base_row.get("financial_metrics_revenue"))
    noi = _to_float(base_row.get("financial_metrics_noi"))
    operating_cash_flow = _to_float(base_row.get("financial_metrics_operating_cash_flow"))
    maintenance_capex = _to_float(base_row.get("financial_metrics_maintenance_capex"))
    estimated_affo = _to_float(base_row.get("financial_metrics_estimated_affo"))
    estimated_distribution = _to_float(base_row.get("financial_metrics_estimated_distribution"))
    visitor_volume = _to_float(base_row.get("operation_metrics_visitor_volume"))
    occupancy_rate = _to_float(base_row.get("operation_metrics_occupancy_rate"))
    adr = _to_float(base_row.get("operation_metrics_adr"))
    ota_score = _to_float(base_row.get("service_quality_metrics_ota_score"))
    base_average_spending = _to_float(base_row.get("operation_metrics_average_spending_per_visitor"))

    revenue_after = None if revenue is None else revenue * (1 - revenue_decline_pct)
    visitor_volume_after = (
        None if visitor_volume is None else visitor_volume * (1 - visitor_volume_decline_pct)
    )
    occupancy_rate_after = None if occupancy_rate is None else occupancy_rate * (1 - occupancy_decline_pct)
    adr_after = None if adr is None else adr * (1 - adr_decline_pct)
    revpar_after = (
        occupancy_rate_after * adr_after
        if occupancy_rate_after is not None and adr_after is not None
        else None
    )
    ota_score_after = None if ota_score is None else max(0.0, ota_score - ota_score_decline)

    if revenue is None or noi is None:
        base_operating_cost = None
        operating_cost_after = None
        noi_after = None
        warnings.append("Revenue or NOI is missing; operating cost and NOI impact are unavailable.")
    else:
        base_operating_cost = revenue - noi
        operating_cost_after = base_operating_cost * (1 + operating_cost_increase_pct)
        noi_after = None if revenue_after is None else revenue_after - operating_cost_after

    if maintenance_capex is None:
        maintenance_capex_after = None
        warnings.append("Maintenance CAPEX is missing; AFFO impact may be unavailable.")
    else:
        maintenance_capex_after = maintenance_capex * (1 + maintenance_capex_increase_pct)

    if operating_cash_flow is None:
        operating_cash_flow_after = None
        warnings.append("Operating cash flow is missing; AFFO proxy is unavailable.")
    elif noi is not None and noi != 0 and noi_after is not None:
        operating_cash_flow_after = operating_cash_flow * (noi_after / noi)
    else:
        operating_cash_flow_after = operating_cash_flow * (1 - revenue_decline_pct)
        warnings.append("NOI is zero or missing; operating cash flow after shock uses revenue-decline proxy.")

    affo_after = (
        operating_cash_flow_after - maintenance_capex_after
        if operating_cash_flow_after is not None and maintenance_capex_after is not None
        else None
    )
    distribution_coverage_before = _safe_divide(estimated_affo, estimated_distribution)
    distribution_coverage_after = _safe_divide(affo_after, estimated_distribution)
    if distribution_coverage_after is None:
        warnings.append("Estimated distribution is missing or zero; distribution coverage is unavailable.")

    if base_average_spending is None:
        average_spending_after = None
    elif visitor_volume_decline_pct >= 1:
        average_spending_after = None
    else:
        average_spending_after = base_average_spending * (1 - revenue_decline_pct) / (
            1 - visitor_volume_decline_pct
        )

    adjusted_scoring_df = base_scoring_df.copy()
    _set_if_column_exists(adjusted_scoring_df, row_index, "financial_metrics_revenue", revenue_after)
    _set_if_column_exists(adjusted_scoring_df, row_index, "financial_metrics_noi", noi_after)
    _set_if_column_exists(
        adjusted_scoring_df,
        row_index,
        "financial_metrics_operating_cash_flow",
        operating_cash_flow_after,
    )
    _set_if_column_exists(
        adjusted_scoring_df,
        row_index,
        "financial_metrics_maintenance_capex",
        maintenance_capex_after,
    )
    _set_if_column_exists(adjusted_scoring_df, row_index, "financial_metrics_estimated_affo", affo_after)
    _set_if_column_exists(
        adjusted_scoring_df,
        row_index,
        "financial_metrics_capex_to_ocf",
        _safe_divide(maintenance_capex_after, operating_cash_flow_after),
    )
    _set_if_column_exists(
        adjusted_scoring_df,
        row_index,
        "operation_metrics_visitor_volume",
        visitor_volume_after,
    )
    _set_if_column_exists(
        adjusted_scoring_df,
        row_index,
        "operation_metrics_occupancy_rate",
        occupancy_rate_after,
    )
    _set_if_column_exists(adjusted_scoring_df, row_index, "operation_metrics_adr", adr_after)
    _set_if_column_exists(adjusted_scoring_df, row_index, "operation_metrics_revpar", revpar_after)
    _set_if_column_exists(
        adjusted_scoring_df,
        row_index,
        "operation_metrics_average_spending_per_visitor",
        average_spending_after,
    )
    _set_if_column_exists(
        adjusted_scoring_df,
        row_index,
        "service_quality_metrics_ota_score",
        ota_score_after,
    )

    base_ocf_positive_ratio = _to_float(base_row.get("derived_ocf_positive_ratio_past3"))
    adjusted_ocf_positive_ratio = base_ocf_positive_ratio
    if operating_cash_flow_after is not None and operating_cash_flow_after <= 0 and base_ocf_positive_ratio is not None:
        adjusted_ocf_positive_ratio = max(0.0, base_ocf_positive_ratio - (1 / 3))
    _set_if_column_exists(
        adjusted_scoring_df,
        row_index,
        "derived_ocf_positive_ratio_past3",
        adjusted_ocf_positive_ratio,
    )

    base_visitor_stability = _to_float(base_row.get("derived_visitor_volume_stability"))
    adjusted_visitor_stability = (
        None if base_visitor_stability is None else base_visitor_stability * (1 - visitor_volume_decline_pct)
    )
    _set_if_column_exists(
        adjusted_scoring_df,
        row_index,
        "derived_visitor_volume_stability",
        adjusted_visitor_stability,
    )
    _set_if_column_exists(
        adjusted_scoring_df,
        row_index,
        "derived_affo_distribution_coverage",
        distribution_coverage_after,
    )
    _set_if_column_exists(
        adjusted_scoring_df,
        row_index,
        "derived_ocf_margin",
        _safe_divide(operating_cash_flow_after, revenue_after),
    )
    previous_revenue = _to_float(base_row.get("derived_previous_revenue"))
    previous_ocf = _to_float(base_row.get("derived_previous_operating_cash_flow"))
    adjusted_revenue_stability = None
    if revenue_after is not None and previous_revenue is not None and previous_revenue > 0:
        adjusted_revenue_stability = max(
            0.0,
            min(1.0, 1 - abs(revenue_after - previous_revenue) / previous_revenue),
        )
    adjusted_ocf_stability = None
    if operating_cash_flow_after is not None and previous_ocf is not None and abs(previous_ocf) > 0:
        adjusted_ocf_stability = max(
            0.0,
            min(1.0, 1 - abs(operating_cash_flow_after - previous_ocf) / abs(previous_ocf)),
        )
    _set_if_column_exists(
        adjusted_scoring_df,
        row_index,
        "derived_revenue_stability",
        adjusted_revenue_stability,
    )
    _set_if_column_exists(
        adjusted_scoring_df,
        row_index,
        "derived_ocf_stability",
        adjusted_ocf_stability,
    )
    scenario_revenue_productivity = revpar_after if revpar_after is not None and revpar_after > 0 else average_spending_after
    _set_if_column_exists(
        adjusted_scoring_df,
        row_index,
        "derived_revenue_productivity",
        scenario_revenue_productivity,
    )

    _indicator_scores_df, _module_scores_df, simulated_total_scores_df = _recalculate_scores_from_adjusted_dataframe(
        adjusted_scoring_df,
        weight_mode,
    )

    base_score_row = base_total_scores_df[base_total_scores_df["asset_id"] == asset_id].iloc[0]
    simulated_score_row = simulated_total_scores_df[simulated_total_scores_df["asset_id"] == asset_id].iloc[0]
    base_score = _to_float(base_score_row.get("total_score"))
    simulated_score = _to_float(simulated_score_row.get("total_score"))
    score_change = (
        None if base_score is None or simulated_score is None else simulated_score - base_score
    )

    base_metrics = {
        "revenue": revenue,
        "noi": noi,
        "operating_cash_flow": operating_cash_flow,
        "maintenance_capex": maintenance_capex,
        "estimated_affo": estimated_affo,
        "estimated_distribution": estimated_distribution,
        "distribution_coverage": distribution_coverage_before,
        "visitor_volume": visitor_volume,
        "occupancy_rate": occupancy_rate,
        "adr": adr,
        "ota_score": ota_score,
    }
    simulated_metrics = {
        "revenue_after": revenue_after,
        "noi_after": noi_after,
        "operating_cash_flow_after": operating_cash_flow_after,
        "maintenance_capex_after": maintenance_capex_after,
        "affo_after": affo_after,
        "distribution_coverage_after": distribution_coverage_after,
        "visitor_volume_after": visitor_volume_after,
        "occupancy_rate_after": occupancy_rate_after,
        "adr_after": adr_after,
        "revpar_after": revpar_after,
        "ota_score_after": ota_score_after,
    }
    impact_metrics = {
        "revenue_change": None if revenue_after is None or revenue is None else revenue_after - revenue,
        "noi_change": None if noi_after is None or noi is None else noi_after - noi,
        "operating_cash_flow_change": (
            None
            if operating_cash_flow_after is None or operating_cash_flow is None
            else operating_cash_flow_after - operating_cash_flow
        ),
        "affo_change": None if affo_after is None or estimated_affo is None else affo_after - estimated_affo,
        "distribution_coverage_change": (
            None
            if distribution_coverage_after is None or distribution_coverage_before is None
            else distribution_coverage_after - distribution_coverage_before
        ),
    }
    severity = classify_scenario_severity(score_change, distribution_coverage_after)

    result = {
        "asset_id": asset_id,
        "asset_name": asset_name,
        "scenario_parameters": parameters,
        "base_metrics": base_metrics,
        "simulated_metrics": simulated_metrics,
        "impact_metrics": impact_metrics,
        "base_score": base_score,
        "simulated_score": simulated_score,
        "score_change": score_change,
        "base_rating": base_score_row.get("rating_level"),
        "simulated_rating": simulated_score_row.get("rating_level"),
        "severity": severity,
        "warnings": warnings,
        "explanation": "",
    }
    result["explanation"] = generate_scenario_explanation(result)
    return result


def classify_scenario_severity(
    score_change: float | None,
    distribution_coverage_after: float | None,
) -> str:
    """Classify internal scenario severity using transparent heuristic labels."""
    score_change_value = 0.0 if score_change is None else score_change
    coverage_value = float("inf") if distribution_coverage_after is None else distribution_coverage_after

    if score_change_value <= -20 or coverage_value < 0.80:
        return "Severe Impact"
    if score_change_value <= -10 or coverage_value < 1.00:
        return "High Impact"
    if score_change_value <= -5 or coverage_value < 1.10:
        return "Moderate Impact"
    return "Low Impact"


def _fmt(value: float | None, digits: int = 2) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:.{digits}f}"


def generate_scenario_explanation(result: dict[str, Any]) -> str:
    """Generate a concise plain-language scenario report."""
    parameters = result["scenario_parameters"]
    impact = result["impact_metrics"]
    base_metrics = result["base_metrics"]
    simulated_metrics = result["simulated_metrics"]

    active_shocks = [
        f"{name}={value:.1%}" if name != "ota_score_decline" else f"{name}={value:.2f}"
        for name, value in parameters.items()
        if value
    ]
    shock_text = ", ".join(active_shocks) if active_shocks else "no shock parameters"
    drivers = []
    if parameters["revenue_decline_pct"]:
        drivers.append("revenue decline")
    if parameters["operating_cost_increase_pct"]:
        drivers.append("operating cost increase")
    if parameters["maintenance_capex_increase_pct"]:
        drivers.append("maintenance CAPEX increase")
    if parameters["visitor_volume_decline_pct"] or parameters["occupancy_decline_pct"] or parameters["adr_decline_pct"]:
        drivers.append("demand and pricing pressure")
    if parameters["ota_score_decline"]:
        drivers.append("online reputation pressure")

    driver_text = ", ".join(drivers) if drivers else "no active downside driver"
    return (
        f"{result['asset_name']} simulated scenario uses {shock_text}. "
        f"Operating cash flow changes by {_fmt(impact['operating_cash_flow_change'])}; "
        f"AFFO proxy changes from {_fmt(base_metrics['estimated_affo'])} to {_fmt(simulated_metrics['affo_after'])}. "
        f"Distribution coverage changes from {_fmt(base_metrics['distribution_coverage'])} to "
        f"{_fmt(simulated_metrics['distribution_coverage_after'])}. "
        f"REITs suitability score changes from {_fmt(result['base_score'], 1)} "
        f"({result['base_rating']}) to {_fmt(result['simulated_score'], 1)} "
        f"({result['simulated_rating']}), a change of {_fmt(result['score_change'], 1)} points. "
        f"Main risk drivers: {driver_text}. Severity label: {result['severity']}. "
        "Severity labels are internal scenario interpretation labels, not official thresholds. "
        "Scenario outputs are simulated estimates for portfolio demonstration and are not forecasts, "
        "investment advice, or regulatory conclusions."
    )


def run_demo_scenarios(
    data_dir: str | Path = "data",
    financial_data_source: str = "demo",
) -> pd.DataFrame:
    """Run three predefined sample scenarios for each asset."""
    base_data = load_base_scenario_data(data_dir, financial_data_source)
    scenarios = {
        "mild downside": {
            "revenue_decline_pct": 0.05,
            "operating_cost_increase_pct": 0.05,
        },
        "demand shock": {
            "revenue_decline_pct": 0.15,
            "visitor_volume_decline_pct": 0.20,
            "occupancy_decline_pct": 0.10,
            "adr_decline_pct": 0.05,
        },
        "stress case": {
            "revenue_decline_pct": 0.25,
            "visitor_volume_decline_pct": 0.30,
            "occupancy_decline_pct": 0.15,
            "adr_decline_pct": 0.10,
            "operating_cost_increase_pct": 0.15,
            "maintenance_capex_increase_pct": 0.20,
            "ota_score_decline": 0.30,
        },
    }
    rows: list[dict[str, Any]] = []

    for asset_id in base_data["asset_id"].dropna().astype(str):
        for scenario_name, kwargs in scenarios.items():
            result = simulate_asset_scenario(
                asset_id,
                data_dir=data_dir,
                financial_data_source=financial_data_source,
                **kwargs,
            )
            rows.append(
                {
                    "asset_id": result["asset_id"],
                    "asset_name": result["asset_name"],
                    "scenario_name": scenario_name,
                    "base_score": result["base_score"],
                    "simulated_score": result["simulated_score"],
                    "score_change": result["score_change"],
                    "base_distribution_coverage": result["base_metrics"]["distribution_coverage"],
                    "simulated_distribution_coverage": result["simulated_metrics"][
                        "distribution_coverage_after"
                    ],
                    "severity": result["severity"],
                }
            )

    return pd.DataFrame(rows)


def _print_cli_output() -> None:
    demo_df = run_demo_scenarios()
    print("=" * 120)
    print("Demo scenario table")
    print(
        demo_df.to_string(
            index=False,
            formatters={
                "base_score": lambda value: _fmt(value, 1),
                "simulated_score": lambda value: _fmt(value, 1),
                "score_change": lambda value: _fmt(value, 1),
                "base_distribution_coverage": lambda value: _fmt(value, 2),
                "simulated_distribution_coverage": lambda value: _fmt(value, 2),
            },
        )
    )
    print("=" * 120)
    print("Detailed stress-case explanations")
    for asset_id in demo_df["asset_id"].drop_duplicates():
        result = simulate_asset_scenario(
            asset_id,
            revenue_decline_pct=0.25,
            visitor_volume_decline_pct=0.30,
            occupancy_decline_pct=0.15,
            adr_decline_pct=0.10,
            operating_cost_increase_pct=0.15,
            maintenance_capex_increase_pct=0.20,
            ota_score_decline=0.30,
        )
        print(f"- {result['explanation']}")


if __name__ == "__main__":
    _print_cli_output()

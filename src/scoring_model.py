"""100-point scoring model for the Tourism REIT Asset Evaluator.

The scoring layer is deliberately separate from the Regulatory Gatekeeper. It
uses sample-relative normalization for portfolio demonstration and asset
management support; it is not an official rating, regulatory conclusion, or
investment recommendation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml

try:
    from src.data_loader import load_financial_metrics
except ModuleNotFoundError:  # Allows `python src/scoring_model.py`.
    from data_loader import load_financial_metrics  # type: ignore


MODULE_ORDER = [
    "A. REITs Cash Flow and Distribution Capacity",
    "B. Tourism Operating Quality",
    "C. Service Quality and Online Reputation",
    "D. Risk Management and Resilience",
    "E. Data Maturity and Smart Operation",
]

ENTROPY_PLACEHOLDER_MESSAGE = (
    "Entropy weighting is reserved for future expansion and requires a larger verified dataset."
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _resolve_data_dir(data_dir: str | Path) -> Path:
    path = Path(data_dir)
    if not path.is_absolute():
        path = _project_root() / path
    return path


def _config_path(file_name: str) -> Path:
    return _project_root() / "config" / file_name


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def _latest_rows_by_asset(df: pd.DataFrame) -> pd.DataFrame:
    latest_df = df.copy()
    latest_df["year"] = pd.to_numeric(latest_df["year"], errors="coerce")
    latest_df = latest_df.dropna(subset=["asset_id", "year"])
    latest_df = latest_df.sort_values(["asset_id", "year"])
    return latest_df.groupby("asset_id", as_index=False).tail(1)


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denominator = denominator.replace({0: pd.NA})
    return numerator / denominator


def _latest_two_year_stability(
    df: pd.DataFrame,
    value_col: str,
    denominator_abs: bool = False,
) -> pd.Series:
    rows: list[dict[str, Any]] = []
    if df.empty or value_col not in df.columns:
        return pd.Series(dtype="Float64", name=f"derived_{value_col}_stability")

    history = df[["asset_id", "year", value_col]].copy()
    history["year"] = pd.to_numeric(history["year"], errors="coerce")
    history[value_col] = pd.to_numeric(history[value_col], errors="coerce")
    history = history.dropna(subset=["asset_id", "year", value_col]).sort_values(["asset_id", "year"])

    for asset_id, group in history.groupby("asset_id"):
        recent = group.tail(2)
        if len(recent) < 2:
            rows.append({"asset_id": asset_id, "stability": pd.NA})
            continue

        previous_value = float(recent.iloc[0][value_col])
        latest_value = float(recent.iloc[1][value_col])
        denominator = abs(previous_value) if denominator_abs else previous_value
        if denominator <= 0:
            rows.append({"asset_id": asset_id, "stability": pd.NA})
            continue

        stability = 1 - abs(latest_value - previous_value) / denominator
        rows.append({"asset_id": asset_id, "stability": max(0.0, min(1.0, stability))})

    if not rows:
        return pd.Series(dtype="Float64", name=f"derived_{value_col}_stability")
    return pd.DataFrame(rows).set_index("asset_id")["stability"].rename(f"derived_{value_col}_stability")


def _previous_year_value(df: pd.DataFrame, value_col: str) -> pd.Series:
    if df.empty or value_col not in df.columns:
        return pd.Series(dtype="Float64", name=f"derived_previous_{value_col}")

    history = df[["asset_id", "year", value_col]].copy()
    history["year"] = pd.to_numeric(history["year"], errors="coerce")
    history[value_col] = pd.to_numeric(history[value_col], errors="coerce")
    history = history.dropna(subset=["asset_id", "year", value_col]).sort_values(["asset_id", "year"])
    rows: list[dict[str, Any]] = []

    for asset_id, group in history.groupby("asset_id"):
        recent = group.tail(2)
        previous_value = pd.NA if len(recent) < 2 else recent.iloc[0][value_col]
        rows.append({"asset_id": asset_id, f"derived_previous_{value_col}": previous_value})

    if not rows:
        return pd.Series(dtype="Float64", name=f"derived_previous_{value_col}")
    return pd.DataFrame(rows).set_index("asset_id")[f"derived_previous_{value_col}"]


def _combine_source_notes(row: pd.Series, prefixes: list[str]) -> tuple[str, str]:
    data_types = []
    source_notes = []

    for prefix in prefixes:
        data_type = row.get(f"{prefix}_data_type")
        source_note = row.get(f"{prefix}_source_note")

        if pd.notna(data_type) and str(data_type).strip():
            data_types.append(str(data_type).strip())
        if pd.notna(source_note) and str(source_note).strip():
            source_notes.append(str(source_note).strip())

    unique_data_types = sorted(set(data_types))
    unique_source_notes = sorted(set(source_notes))

    if not unique_data_types:
        combined_data_type = "unknown"
    elif len(unique_data_types) == 1:
        combined_data_type = unique_data_types[0]
    else:
        combined_data_type = "mixed"

    combined_source_note = " | ".join(unique_source_notes) if unique_source_notes else "Source note unavailable."
    return combined_data_type, combined_source_note


def load_scoring_data(
    data_dir: str | Path = "data",
    financial_data_source: str = "demo",
    selected_source: str | None = None,
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """Load and merge latest-year data for the scoring model.

    Returns
    -------
    tuple
        ``(merged_latest_year_dataframe, raw_table_dictionary)``.
    """
    if selected_source is not None:
        financial_data_source = selected_source

    base_dir = _resolve_data_dir(data_dir)
    tables = {
        "assets": pd.read_csv(base_dir / "assets.csv"),
        "financial_metrics": load_financial_metrics(financial_data_source),
        "operation_metrics": pd.read_csv(base_dir / "operation_metrics.csv"),
        "service_quality_metrics": pd.read_csv(base_dir / "service_quality_metrics.csv"),
        "risk_metrics": pd.read_csv(base_dir / "risk_metrics.csv"),
        "digital_maturity_metrics": pd.read_csv(base_dir / "digital_maturity_metrics.csv"),
    }

    merged_df = tables["assets"].copy()

    for table_name in [
        "financial_metrics",
        "operation_metrics",
        "service_quality_metrics",
        "risk_metrics",
        "digital_maturity_metrics",
    ]:
        latest_df = _latest_rows_by_asset(tables[table_name]).add_prefix(f"{table_name}_")
        merged_df = merged_df.merge(
            latest_df,
            left_on="asset_id",
            right_on=f"{table_name}_asset_id",
            how="left",
        )

    financial_history = tables["financial_metrics"].copy()
    financial_history["operating_cash_flow"] = pd.to_numeric(
        financial_history["operating_cash_flow"],
        errors="coerce",
    )
    ocf_positive_ratio = (
        financial_history.sort_values(["asset_id", "year"])
        .groupby("asset_id")
        .tail(3)
        .assign(ocf_is_positive=lambda df: df["operating_cash_flow"] > 0)
        .groupby("asset_id")["ocf_is_positive"]
        .mean()
        .rename("derived_ocf_positive_ratio_past3")
    )
    merged_df = merged_df.merge(ocf_positive_ratio, on="asset_id", how="left")

    revenue_stability = _latest_two_year_stability(financial_history, "revenue").rename(
        "derived_revenue_stability"
    )
    ocf_stability = _latest_two_year_stability(
        financial_history,
        "operating_cash_flow",
        denominator_abs=True,
    ).rename("derived_ocf_stability")
    previous_revenue = _previous_year_value(financial_history, "revenue")
    previous_ocf = _previous_year_value(financial_history, "operating_cash_flow")
    for derived_series in [revenue_stability, ocf_stability, previous_revenue, previous_ocf]:
        merged_df = merged_df.merge(derived_series, on="asset_id", how="left")

    operation_history = tables["operation_metrics"].copy()
    operation_history["visitor_volume"] = pd.to_numeric(operation_history["visitor_volume"], errors="coerce")
    visitor_stability = (
        operation_history.sort_values(["asset_id", "year"])
        .groupby("asset_id")
        .tail(3)
        .groupby("asset_id")["visitor_volume"]
        .agg(lambda values: 50.0 if values.mean() == 0 else 1 - (values.std(ddof=0) / values.mean()))
        .rename("derived_visitor_volume_stability")
    )
    merged_df = merged_df.merge(visitor_stability, on="asset_id", how="left")

    merged_df["derived_affo_distribution_coverage"] = _safe_divide(
        pd.to_numeric(merged_df["financial_metrics_estimated_affo"], errors="coerce"),
        pd.to_numeric(merged_df["financial_metrics_estimated_distribution"], errors="coerce"),
    )
    merged_df["derived_ocf_margin"] = _safe_divide(
        pd.to_numeric(merged_df["financial_metrics_operating_cash_flow"], errors="coerce"),
        pd.to_numeric(merged_df["financial_metrics_revenue"], errors="coerce"),
    )
    reported_debt_ratio = pd.to_numeric(merged_df.get("financial_metrics_debt_ratio"), errors="coerce")
    calculated_debt_ratio = _safe_divide(
        pd.to_numeric(merged_df["financial_metrics_total_debt"], errors="coerce"),
        pd.to_numeric(merged_df["financial_metrics_total_assets"], errors="coerce"),
    )
    merged_df["derived_debt_ratio"] = reported_debt_ratio.where(
        reported_debt_ratio.notna(),
        calculated_debt_ratio,
    )
    merged_df["derived_revenue_productivity"] = pd.to_numeric(
        merged_df["operation_metrics_revpar"],
        errors="coerce",
    ).where(
        pd.to_numeric(merged_df["operation_metrics_revpar"], errors="coerce") > 0,
        pd.to_numeric(merged_df["operation_metrics_average_spending_per_visitor"], errors="coerce"),
    )
    service_columns = [
        "service_quality_metrics_tangibles_score",
        "service_quality_metrics_reliability_score",
        "service_quality_metrics_responsiveness_score",
        "service_quality_metrics_assurance_score",
        "service_quality_metrics_empathy_score",
    ]
    merged_df["derived_service_quality_survey_score"] = merged_df[service_columns].apply(
        pd.to_numeric,
        errors="coerce",
    ).mean(axis=1)
    risk_columns = [
        "risk_metrics_policy_risk",
        "risk_metrics_climate_physical_risk",
        "risk_metrics_financial_pressure_risk",
        "risk_metrics_market_competition_risk",
        "risk_metrics_platform_dependency_risk",
    ]
    merged_df["derived_operational_risk_index"] = merged_df[risk_columns].apply(
        pd.to_numeric,
        errors="coerce",
    ).mean(axis=1)

    return merged_df, tables


def normalize_positive_indicator(series: pd.Series) -> pd.Series:
    """Return peer-normalized 0-100 scores where higher values are better."""
    numeric = pd.to_numeric(series, errors="coerce")
    valid = numeric.dropna()
    if valid.empty:
        return pd.Series(pd.NA, index=series.index, dtype="Float64")
    minimum = valid.min()
    maximum = valid.max()
    if minimum == maximum:
        return pd.Series(50.0, index=series.index, dtype="Float64").where(numeric.notna(), pd.NA)
    return ((numeric - minimum) / (maximum - minimum) * 100).clip(0, 100)


def normalize_negative_indicator(series: pd.Series) -> pd.Series:
    """Return reverse peer-normalized 0-100 scores where lower values are better."""
    numeric = pd.to_numeric(series, errors="coerce")
    valid = numeric.dropna()
    if valid.empty:
        return pd.Series(pd.NA, index=series.index, dtype="Float64")
    minimum = valid.min()
    maximum = valid.max()
    if minimum == maximum:
        return pd.Series(50.0, index=series.index, dtype="Float64").where(numeric.notna(), pd.NA)
    return ((maximum - numeric) / (maximum - minimum) * 100).clip(0, 100)


def get_indicator_direction(
    indicator_name_or_id: str,
    indicator_config: dict[str, Any] | None,
) -> str:
    """Return indicator direction from config when available."""
    if not indicator_config:
        return "positive"

    lookup_value = str(indicator_name_or_id).strip().lower()
    for indicator in indicator_config.get("indicators", []):
        indicator_id = str(indicator.get("indicator_id", "")).strip().lower()
        indicator_name = str(indicator.get("indicator_name", "")).strip().lower()
        if lookup_value in {indicator_id, indicator_name}:
            direction = str(indicator.get("direction", "positive")).strip().lower()
            return direction if direction in {"positive", "negative"} else "positive"

    return "positive"


def _indicator_metadata(indicator_config: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    metadata: dict[str, dict[str, Any]] = {}
    if not indicator_config:
        return metadata
    for indicator in indicator_config.get("indicators", []):
        metadata[str(indicator.get("indicator_id"))] = indicator
    return metadata


def _scoring_indicator_map() -> list[dict[str, Any]]:
    return [
        {
            "indicator_id": "A1",
            "value_column": "derived_ocf_positive_ratio_past3",
            "source_prefixes": ["financial_metrics"],
        },
        {
            "indicator_id": "A2",
            "value_column": "derived_affo_distribution_coverage",
            "source_prefixes": ["financial_metrics"],
        },
        {
            "indicator_id": "A3",
            "value_column": None,
            "source_prefixes": ["financial_metrics"],
            "missing_reason": "Market-based revenue ratio is not available in the MVP data template.",
        },
        {
            "indicator_id": "A4",
            "value_column": None,
            "source_prefixes": ["financial_metrics"],
            "missing_reason": "DCF valuation support score is not available in the MVP data template.",
        },
        {
            "indicator_id": "A5",
            "value_column": "derived_ocf_margin",
            "source_prefixes": ["financial_metrics"],
        },
        {
            "indicator_id": "A6",
            "value_column": "derived_debt_ratio",
            "source_prefixes": ["financial_metrics"],
            "direction_override": "negative",
        },
        {
            "indicator_id": "A7",
            "value_column": "derived_revenue_stability",
            "source_prefixes": ["financial_metrics"],
        },
        {
            "indicator_id": "A8",
            "value_column": "derived_ocf_stability",
            "source_prefixes": ["financial_metrics"],
        },
        {
            "indicator_id": "B1",
            "value_column": "derived_visitor_volume_stability",
            "source_prefixes": ["operation_metrics"],
        },
        {
            "indicator_id": "B2",
            "value_column": "operation_metrics_occupancy_rate",
            "source_prefixes": ["operation_metrics"],
        },
        {
            "indicator_id": "B3",
            "value_column": "derived_revenue_productivity",
            "source_prefixes": ["operation_metrics"],
        },
        {
            "indicator_id": "B4",
            "value_column": "operation_metrics_peak_season_revenue_ratio",
            "source_prefixes": ["operation_metrics"],
        },
        {
            "indicator_id": "C1",
            "value_column": "service_quality_metrics_ota_score",
            "source_prefixes": ["service_quality_metrics"],
        },
        {
            "indicator_id": "C2",
            "value_column": "service_quality_metrics_complaint_rate",
            "source_prefixes": ["service_quality_metrics"],
        },
        {
            "indicator_id": "C3",
            "value_column": "derived_service_quality_survey_score",
            "source_prefixes": ["service_quality_metrics"],
        },
        {
            "indicator_id": "D1",
            "value_column": "risk_metrics_risk_disclosure_score",
            "source_prefixes": ["risk_metrics"],
        },
        {
            "indicator_id": "D2",
            "value_column": "derived_operational_risk_index",
            "source_prefixes": ["risk_metrics"],
            "direction_override": "negative",
        },
        {
            "indicator_id": "D3",
            "value_column": "risk_metrics_platform_dependency_risk",
            "source_prefixes": ["risk_metrics"],
            "direction_override": "negative",
        },
        {
            "indicator_id": "E1",
            "value_column": "digital_maturity_metrics_data_quality_score",
            "source_prefixes": ["digital_maturity_metrics"],
        },
        {
            "indicator_id": "E2",
            "value_column": "digital_maturity_metrics_smart_operation_score",
            "source_prefixes": ["digital_maturity_metrics"],
        },
        {
            "indicator_id": "E3",
            "value_column": "digital_maturity_metrics_data_availability_score",
            "source_prefixes": ["digital_maturity_metrics"],
        },
    ]


def calculate_indicator_scores(
    scoring_df: pd.DataFrame,
    indicator_config: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Calculate normalized indicator scores for available scoring indicators."""
    if indicator_config is None:
        indicator_config = _load_yaml(_config_path("indicator_framework.yml"))

    metadata = _indicator_metadata(indicator_config)
    rows: list[dict[str, Any]] = []

    for mapping in _scoring_indicator_map():
        indicator_id = mapping["indicator_id"]
        indicator_meta = metadata.get(indicator_id, {})
        indicator_name = indicator_meta.get("indicator_name", indicator_id)
        module = indicator_meta.get("module", "Unmapped")
        value_column = mapping.get("value_column")
        direction = mapping.get("direction_override") or get_indicator_direction(indicator_id, indicator_config)

        if value_column and value_column in scoring_df.columns:
            raw_values = pd.to_numeric(scoring_df[value_column], errors="coerce")
            normalized_scores = (
                normalize_negative_indicator(raw_values)
                if direction == "negative"
                else normalize_positive_indicator(raw_values)
            )
        else:
            raw_values = pd.Series(pd.NA, index=scoring_df.index, dtype="Float64")
            normalized_scores = pd.Series(pd.NA, index=scoring_df.index, dtype="Float64")

        for idx, source_row in scoring_df.iterrows():
            raw_value = raw_values.loc[idx]
            indicator_score = normalized_scores.loc[idx]
            data_type, source_note = _combine_source_notes(source_row, mapping.get("source_prefixes", []))

            if pd.isna(indicator_score):
                explanation = mapping.get(
                    "missing_reason",
                    "Data unavailable; excluded from module average.",
                )
                if "Data unavailable" not in explanation:
                    explanation = explanation + " Data unavailable; excluded from module average."
            else:
                explanation = f"Peer {direction} min-max normalized score from latest available year data."

            rows.append(
                {
                    "asset_id": source_row["asset_id"],
                    "asset_name": source_row["asset_name"],
                    "module": module,
                    "indicator_id": indicator_id,
                    "indicator_name": indicator_name,
                    "raw_value": raw_value,
                    "indicator_score": indicator_score,
                    "direction": direction,
                    "data_type": data_type,
                    "source_note": source_note,
                    "explanation": explanation,
                }
            )

    return pd.DataFrame(rows)


def calculate_module_scores(indicator_scores_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate module-level average scores by asset, excluding missing indicators."""
    rows: list[dict[str, Any]] = []

    grouped = indicator_scores_df.groupby(["asset_id", "asset_name", "module"], sort=False)
    for (asset_id, asset_name, module), group in grouped:
        valid_scores = pd.to_numeric(group["indicator_score"], errors="coerce").dropna()
        module_score = valid_scores.mean() if not valid_scores.empty else pd.NA
        missing_count = int(group["indicator_score"].isna().sum())
        valid_count = int(valid_scores.count())

        if missing_count:
            explanation = (
                f"{valid_count} valid indicators scored; {missing_count} missing indicators excluded from module average."
            )
        else:
            explanation = f"All {valid_count} available indicators included in module average."

        rows.append(
            {
                "asset_id": asset_id,
                "asset_name": asset_name,
                "module": module,
                "module_score": module_score,
                "valid_indicator_count": valid_count,
                "missing_indicator_count": missing_count,
                "explanation": explanation,
            }
        )

    return pd.DataFrame(rows)


def _module_weights(weight_mode: str) -> dict[str, float]:
    weights_config = _load_yaml(_config_path("scoring_weights.yml"))
    mode_config = weights_config.get("weighting_modes", {}).get(weight_mode)
    if not mode_config:
        raise ValueError(f"Unknown weight_mode: {weight_mode}")

    modules = mode_config.get("modules", {})
    if not modules:
        raise ValueError(ENTROPY_PLACEHOLDER_MESSAGE)

    return {module_name: float(config["weight"]) for module_name, config in modules.items()}


def calculate_total_scores(
    module_scores_df: pd.DataFrame,
    weight_mode: str = "default_expert_weight",
) -> pd.DataFrame:
    """Calculate total 100-point scores using configured module weights."""
    if weight_mode == "entropy_weight_placeholder":
        return pd.DataFrame(
            [
                {
                    "asset_id": pd.NA,
                    "asset_name": pd.NA,
                    "total_score": pd.NA,
                    "rating_level": "Not rated",
                    "weight_mode": weight_mode,
                    "explanation": ENTROPY_PLACEHOLDER_MESSAGE,
                }
            ]
        )

    weights = _module_weights(weight_mode)
    rows: list[dict[str, Any]] = []

    for (asset_id, asset_name), group in module_scores_df.groupby(["asset_id", "asset_name"], sort=False):
        module_lookup = {
            row["module"]: row
            for row in group.to_dict(orient="records")
        }
        weighted_sum = 0.0
        available_weight = 0.0
        output_row: dict[str, Any] = {
            "asset_id": asset_id,
            "asset_name": asset_name,
            "weight_mode": weight_mode,
        }
        missing_modules = []

        for module_name in MODULE_ORDER:
            column_name = _module_score_column(module_name)
            module_row = module_lookup.get(module_name)
            module_score = pd.NA if not module_row else module_row["module_score"]
            output_row[column_name] = module_score

            if pd.isna(module_score):
                missing_modules.append(module_name)
                continue

            weighted_sum += float(module_score) * weights[module_name]
            available_weight += weights[module_name]

        total_score = weighted_sum / available_weight if available_weight else pd.NA
        rating_level = assign_rating_level(total_score)
        output_row["total_score"] = total_score
        output_row["rating_level"] = rating_level
        output_row["explanation"] = generate_score_explanation(
            asset_name,
            group,
            total_score,
            rating_level,
        )
        if missing_modules:
            output_row["explanation"] += " Missing modules excluded from total score: " + ", ".join(missing_modules) + "."

        rows.append(output_row)

    return pd.DataFrame(rows)


def _module_score_column(module_name: str) -> str:
    return module_name.split(". ", 1)[0].lower() + "_module_score"


def assign_rating_level(total_score: float | None) -> str:
    """Assign rating level for a 0-100 total score."""
    if total_score is None or pd.isna(total_score):
        return "Not rated"
    score = float(total_score)
    if score >= 85:
        return "Highly Suitable"
    if score >= 70:
        return "Suitable with Monitoring"
    if score >= 55:
        return "Conditional Suitability"
    if score >= 40:
        return "Weak Suitability"
    return "Not Suitable"


def generate_score_explanation(
    asset_name: str,
    module_scores: pd.DataFrame,
    total_score: float | None,
    rating_level: str,
) -> str:
    """Generate concise natural-language score explanation."""
    valid_modules = module_scores.dropna(subset=["module_score"]).copy()

    if valid_modules.empty or total_score is None or pd.isna(total_score):
        return (
            f"{asset_name} is not rated because no module scores are available. "
            "This portfolio prototype is not investment advice."
        )

    strongest = valid_modules.loc[valid_modules["module_score"].idxmax()]
    weakest = valid_modules.loc[valid_modules["module_score"].idxmin()]
    missing_count = int(module_scores["missing_indicator_count"].sum())

    missing_note = (
        f" {missing_count} missing indicator(s) were excluded from module averages."
        if missing_count
        else " No indicator-level missing-data exclusions were required."
    )

    return (
        f"{asset_name} scores {float(total_score):.1f} and is classified as {rating_level}. "
        f"Strongest module: {strongest['module']} ({float(strongest['module_score']):.1f}). "
        f"Weakest module: {weakest['module']} ({float(weakest['module_score']):.1f})."
        f"{missing_note} This scoring output is for portfolio demonstration and asset management support only, "
        "not investment advice, an official rating, or a regulatory conclusion."
    )


def run_scoring_pipeline(
    data_dir: str | Path = "data",
    weight_mode: str = "default_expert_weight",
    financial_data_source: str = "demo",
    selected_source: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run the full scoring pipeline."""
    if selected_source is not None:
        financial_data_source = selected_source

    scoring_df, _tables = load_scoring_data(data_dir, financial_data_source)
    indicator_config = _load_yaml(_config_path("indicator_framework.yml"))
    indicator_scores_df = calculate_indicator_scores(scoring_df, indicator_config)
    module_scores_df = calculate_module_scores(indicator_scores_df)
    total_scores_df = calculate_total_scores(module_scores_df, weight_mode)
    return indicator_scores_df, module_scores_df, total_scores_df


def _print_cli_results() -> None:
    indicator_scores_df, module_scores_df, total_scores_df = run_scoring_pipeline()

    print("=" * 100)
    print("Total score table")
    score_columns = [
        "asset_id",
        "asset_name",
        "a_module_score",
        "b_module_score",
        "c_module_score",
        "d_module_score",
        "e_module_score",
        "total_score",
        "rating_level",
        "weight_mode",
    ]
    print(total_scores_df[score_columns].to_string(index=False))

    print("=" * 100)
    print("Module score table")
    print(
        module_scores_df[
            [
                "asset_id",
                "asset_name",
                "module",
                "module_score",
                "valid_indicator_count",
                "missing_indicator_count",
            ]
        ].to_string(index=False)
    )

    print("=" * 100)
    print("Asset explanations")
    for explanation in total_scores_df["explanation"]:
        print(f"- {explanation}")


if __name__ == "__main__":
    _print_cli_results()

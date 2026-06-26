"""REIT fit score page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.chart_utils import make_indicator_bar_chart, make_module_score_radar
from src.data_loader import get_asset_options, get_financial_data_source_label
from src.data_source_ui import render_financial_data_source_selector
from src.i18n import (
    current_language,
    language_selector,
    localize_dataframe,
    t,
    translate_column_name,
    translate_module_name,
    translate_rating,
)
from src.scoring_model import ENTROPY_PLACEHOLDER_MESSAGE, run_scoring_pipeline


st.set_page_config(page_title="REIT Fit Score", layout="wide")

MODULE_A_NAME = "A. REITs Cash Flow and Distribution Capacity"


def indicator_display_name(row: pd.Series) -> str:
    """Return localized indicator name while preserving scoring output fallback."""
    language = current_language()
    indicator_id = str(row.get("indicator_id", ""))
    translated = t(f"indicator_names.{indicator_id}", "")
    if translated:
        return translated
    if language == "zh" and "indicator_name_zh" in row and pd.notna(row["indicator_name_zh"]):
        return str(row["indicator_name_zh"])
    if language == "en" and "indicator_name_en" in row and pd.notna(row["indicator_name_en"]):
        return str(row["indicator_name_en"])
    return str(row.get("indicator_name", row.get("indicator_id", "")))


def localize_direction(value: object) -> str:
    if value is None or pd.isna(value) or str(value).strip() == "":
        return t("score.unknown")
    return t(f"directions.{value}", str(value))


def localize_included(value: object) -> str:
    return t("score.included_yes") if bool(value) else t("score.included_no")


def normalize_module_a_indicator_details(
    selected_indicators: pd.DataFrame,
) -> tuple[pd.DataFrame, list[str]]:
    """Build a display dataframe for Module A details without assuming optional columns exist."""
    expected_ids = ["A1", "A2", "A5", "A6", "A7", "A8"]
    if selected_indicators.empty or "indicator_id" not in selected_indicators.columns:
        return pd.DataFrame(), expected_ids

    source_df = selected_indicators.copy()
    if "module" in source_df.columns:
        source_df = source_df[source_df["module"] == MODULE_A_NAME].copy()

    module_a_indicators = source_df[source_df["indicator_id"].isin(expected_ids)].copy()
    if module_a_indicators.empty:
        return pd.DataFrame(), expected_ids

    missing_ids = [
        indicator_id
        for indicator_id in expected_ids
        if indicator_id not in set(module_a_indicators["indicator_id"].astype(str))
    ]

    if "normalized_score" not in module_a_indicators.columns:
        if "score" in module_a_indicators.columns:
            module_a_indicators["normalized_score"] = module_a_indicators["score"]
        elif "indicator_score" in module_a_indicators.columns:
            module_a_indicators["normalized_score"] = module_a_indicators["indicator_score"]
        else:
            module_a_indicators["normalized_score"] = pd.NA

    if "raw_value" not in module_a_indicators.columns:
        module_a_indicators["raw_value"] = pd.NA

    if "included_in_score" not in module_a_indicators.columns:
        normalized_values = pd.to_numeric(module_a_indicators["normalized_score"], errors="coerce")
        module_a_indicators["included_in_score"] = normalized_values.notna()
    else:
        module_a_indicators["included_in_score"] = module_a_indicators["included_in_score"].fillna(False).astype(bool)

    if "direction" not in module_a_indicators.columns:
        module_a_indicators["direction"] = t("score.unknown")

    if "data_note" not in module_a_indicators.columns:
        if "source_note" in module_a_indicators.columns:
            module_a_indicators["data_note"] = module_a_indicators["source_note"]
        else:
            module_a_indicators["data_note"] = (
                "模型运行时计算或读取的指标。"
                if current_language() == "zh"
                else "Indicator calculated or loaded at scoring time."
            )

    for column in ["indicator_name", "indicator_name_en", "indicator_name_zh"]:
        if column not in module_a_indicators.columns:
            module_a_indicators[column] = pd.NA

    module_a_indicators["sort_order"] = module_a_indicators["indicator_id"].map(
        {indicator_id: index for index, indicator_id in enumerate(expected_ids)}
    )
    module_a_indicators = module_a_indicators.sort_values("sort_order")
    module_a_indicators["indicator_display_name"] = module_a_indicators.apply(indicator_display_name, axis=1)
    module_a_indicators["included_display"] = module_a_indicators["included_in_score"].map(localize_included)
    module_a_indicators["direction_display"] = module_a_indicators["direction"].map(localize_direction)
    module_a_indicators["data_note_display"] = module_a_indicators["data_note"].fillna(
        "模型运行时计算或读取的指标。"
        if current_language() == "zh"
        else "Indicator calculated or loaded at scoring time."
    )

    display_df = module_a_indicators[
        [
            "indicator_id",
            "indicator_display_name",
            "raw_value",
            "normalized_score",
            "direction_display",
            "included_display",
            "data_note_display",
        ]
    ].rename(
        columns={
            "indicator_id": t("score.indicator_id"),
            "indicator_display_name": t("score.indicator_name"),
            "raw_value": t("score.raw_value"),
            "normalized_score": t("score.normalized_score"),
            "direction_display": t("score.direction"),
            "included_display": t("score.included_in_score"),
            "data_note_display": t("score.data_note"),
        }
    )
    return display_df, missing_ids


def render_module_a_indicator_details(selected_indicators: pd.DataFrame) -> None:
    display_df, missing_ids = normalize_module_a_indicator_details(selected_indicators)
    if missing_ids:
        st.warning(t("score.module_a_missing_indicator_warning", ids=", ".join(missing_ids)))
    if display_df.empty:
        st.info(t("score.module_a_indicator_details_unavailable"))
        return

    st.dataframe(
        display_df.style.format(
            {
                t("score.raw_value"): "{:.3f}",
                t("score.normalized_score"): "{:.1f}",
            },
            na_rep=t("score.missing"),
        ),
        use_container_width=True,
        hide_index=True,
    )


def main() -> None:
    language_selector()
    _selected_financial_source, effective_financial_source, _did_fallback = render_financial_data_source_selector()
    st.title(t("score.title"))
    st.caption(t("score.subtitle"))
    st.caption(
        f"{t('data_source.current_financial_data_source')}: "
        f"{get_financial_data_source_label(effective_financial_source, current_language())}"
    )
    st.info(t("score.notice"))

    try:
        asset_options = get_asset_options()
        selected_label = st.selectbox(t("common.select_asset"), list(asset_options.keys()))
        asset_id = asset_options[selected_label]
    except Exception as exc:
        st.error(t("common.unable_to_load_asset_options", error=exc))
        if st.checkbox(t("common.debug_mode")):
            st.exception(exc)
        return

    weight_mode = st.selectbox(
        t("common.weighting_mode"),
        ["default_expert_weight", "equal_weight", "entropy_weight_placeholder"],
        index=0,
        format_func=lambda value: t(f"weight_modes.{value}", value),
    )
    effective_weight_mode = weight_mode
    if weight_mode == "entropy_weight_placeholder":
        st.warning(ENTROPY_PLACEHOLDER_MESSAGE)
        effective_weight_mode = "default_expert_weight"

    try:
        indicator_scores_df, module_scores_df, total_scores_df = run_scoring_pipeline(
            weight_mode=effective_weight_mode,
            financial_data_source=effective_financial_source,
        )
    except Exception as exc:
        st.error(t("score.pipeline_failed", error=exc))
        if st.checkbox(t("common.debug_scoring")):
            st.exception(exc)
        return

    selected_total = total_scores_df[total_scores_df["asset_id"] == asset_id].iloc[0]
    selected_modules = module_scores_df[module_scores_df["asset_id"] == asset_id].copy()
    selected_indicators = indicator_scores_df[indicator_scores_df["asset_id"] == asset_id].copy()
    valid_modules = selected_modules.dropna(subset=["module_score"])

    if valid_modules.empty:
        strongest_module = "N/A"
        weakest_module = "N/A"
    else:
        strongest = valid_modules.loc[valid_modules["module_score"].idxmax()]
        weakest = valid_modules.loc[valid_modules["module_score"].idxmin()]
        strongest_module = f"{translate_module_name(strongest['module'])} ({strongest['module_score']:.1f})"
        weakest_module = f"{translate_module_name(weakest['module'])} ({weakest['module_score']:.1f})"

    missing_indicator_count = int(selected_modules["missing_indicator_count"].sum())

    kpi_cols = st.columns(4)
    kpi_cols[0].metric(t("labels.total_score"), f"{selected_total['total_score']:.1f}")
    kpi_cols[1].metric(t("labels.rating_level"), translate_rating(selected_total["rating_level"]))
    kpi_cols[2].metric(t("labels.strongest_module"), strongest_module)
    kpi_cols[3].metric(t("labels.weakest_module"), weakest_module)

    st.metric(t("score.missing_indicators"), missing_indicator_count)
    st.write(selected_total["explanation"])

    chart_cols = st.columns([1, 1])
    with chart_cols[0]:
        st.subheader(t("score.module_radar"))
        if selected_modules.dropna(subset=["module_score"]).empty:
            st.info(t("score.module_radar_unavailable"))
        else:
            st.plotly_chart(make_module_score_radar(module_scores_df, asset_id), use_container_width=True)

    with chart_cols[1]:
        st.subheader(t("score.indicator_bar"))
        if selected_indicators.dropna(subset=["indicator_score"]).empty:
            st.info(t("score.indicator_chart_unavailable"))
        else:
            st.plotly_chart(make_indicator_bar_chart(indicator_scores_df, asset_id), use_container_width=True)

    st.subheader(t("score.module_a_indicator_details_title"))
    st.caption(t("score.module_a_indicator_details_note"))
    render_module_a_indicator_details(selected_indicators)

    st.subheader(t("score.module_table"))
    display_modules = localize_dataframe(selected_modules)
    st.dataframe(
        display_modules.style.format(
            {translate_column_name("module_score"): "{:.1f}"},
            na_rep=t("common.data_unavailable"),
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader(t("score.indicator_table"))
    display_indicators = selected_indicators[
        [
            "indicator_id",
            "indicator_name",
            "module",
            "raw_value",
            "indicator_score",
            "direction",
            "data_type",
            "source_note",
            "explanation",
        ]
    ]
    display_indicators = localize_dataframe(display_indicators)
    st.dataframe(
        display_indicators.style.format(
            {
                translate_column_name("raw_value"): "{:.3f}",
                translate_column_name("indicator_score"): "{:.1f}",
            },
            na_rep=t("common.data_unavailable"),
        ),
        use_container_width=True,
        hide_index=True,
    )


if __name__ == "__main__":
    main()

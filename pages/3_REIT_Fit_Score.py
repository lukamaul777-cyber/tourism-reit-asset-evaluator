"""REIT fit score page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.chart_utils import make_indicator_bar_chart, make_module_score_radar
from src.data_loader import get_asset_options
from src.i18n import language_selector, t, translate_rating
from src.scoring_model import ENTROPY_PLACEHOLDER_MESSAGE, run_scoring_pipeline


st.set_page_config(page_title="REIT Fit Score", layout="wide")


def main() -> None:
    language_selector()
    st.title(t("score.title"))
    st.caption(t("score.subtitle"))
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
            weight_mode=effective_weight_mode
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
        strongest_module = f"{strongest['module']} ({strongest['module_score']:.1f})"
        weakest_module = f"{weakest['module']} ({weakest['module_score']:.1f})"

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

    st.subheader(t("score.module_table"))
    st.dataframe(
        selected_modules.style.format({"module_score": "{:.1f}"}, na_rep="N/A"),
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
    st.dataframe(
        display_indicators.style.format({"raw_value": "{:.3f}", "indicator_score": "{:.1f}"}, na_rep="N/A"),
        use_container_width=True,
        hide_index=True,
    )


main()

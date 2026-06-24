"""REIT fit score page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.chart_utils import make_indicator_bar_chart, make_module_score_radar
from src.data_loader import get_asset_options
from src.scoring_model import ENTROPY_PLACEHOLDER_MESSAGE, run_scoring_pipeline


st.set_page_config(page_title="REIT Fit Score", layout="wide")


def main() -> None:
    st.title("REITs Suitability Score")
    st.caption(
        "Review the 100-point reference-based score after the Regulatory Gatekeeper. "
        "The score is sample-relative and is not an official rating."
    )
    st.info(
        "Demo / Simulated Data Notice: scoring outputs are for portfolio demonstration and asset management support only, "
        "not investment advice, an official rating, or a regulatory conclusion."
    )

    try:
        asset_options = get_asset_options()
        selected_label = st.selectbox("Asset", list(asset_options.keys()))
        asset_id = asset_options[selected_label]
    except Exception as exc:
        st.error(f"Unable to load asset options: {exc}")
        if st.checkbox("Debug mode"):
            st.exception(exc)
        return

    weight_mode = st.selectbox(
        "Weighting mode",
        ["default_expert_weight", "equal_weight", "entropy_weight_placeholder"],
        index=0,
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
        st.error(f"Scoring pipeline failed: {exc}")
        if st.checkbox("Debug scoring"):
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
    kpi_cols[0].metric("Total score", f"{selected_total['total_score']:.1f}")
    kpi_cols[1].metric("Rating level", selected_total["rating_level"])
    kpi_cols[2].metric("Strongest module", strongest_module)
    kpi_cols[3].metric("Weakest module", weakest_module)

    st.metric("Missing indicators excluded from module averages", missing_indicator_count)
    st.write(selected_total["explanation"])

    chart_cols = st.columns([1, 1])
    with chart_cols[0]:
        st.subheader("Module Score Radar")
        if selected_modules.dropna(subset=["module_score"]).empty:
            st.info("Module radar chart is unavailable because module scores are missing.")
        else:
            st.plotly_chart(make_module_score_radar(module_scores_df, asset_id), use_container_width=True)

    with chart_cols[1]:
        st.subheader("Indicator Score Bar Chart")
        if selected_indicators.dropna(subset=["indicator_score"]).empty:
            st.info("Indicator chart is unavailable because indicator scores are missing.")
        else:
            st.plotly_chart(make_indicator_bar_chart(indicator_scores_df, asset_id), use_container_width=True)

    st.subheader("Module Score Table")
    st.dataframe(
        selected_modules.style.format({"module_score": "{:.1f}"}, na_rep="N/A"),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Indicator Score Table")
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

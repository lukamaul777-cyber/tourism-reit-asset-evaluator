"""Streamlit entry point for the Tourism REIT Asset Evaluator."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.chart_utils import make_score_bar_chart
from src.data_loader import get_asset_options, load_all_data
from src.gatekeeper import run_gatekeeper_checks
from src.scoring_model import ENTROPY_PLACEHOLDER_MESSAGE, run_scoring_pipeline


st.set_page_config(
    page_title="Tourism REIT Asset Evaluator",
    layout="wide",
)


def render_page_header(title: str, subtitle: str) -> None:
    st.title(title)
    st.caption(subtitle)


def render_notice() -> None:
    st.info(
        "**Demo / Simulated Data Notice:** Demo data may include simulated or mixed values. "
        "Scores are not official ratings, investment recommendations, or regulatory conclusions."
    )


def selected_weight_mode() -> str:
    return st.sidebar.selectbox(
        "Weighting mode",
        ["default_expert_weight", "equal_weight", "entropy_weight_placeholder"],
        index=0,
        help="Entropy weighting is reserved for a larger verified dataset.",
    )


def count_gatekeeper_warnings(asset_ids: list[str]) -> int:
    warning_count = 0
    for asset_id in asset_ids:
        results_df, overall_status, _summary = run_gatekeeper_checks(asset_id)
        has_warning = overall_status == "Pass with Warning" or (results_df["status"] == "Warning").any()
        warning_count += int(has_warning)
    return warning_count


def render_methodology_flow() -> None:
    st.subheader("Methodology Flow")
    columns = st.columns(4)
    steps = [
        ("1", "Regulatory Gatekeeper", "Pre-screen hard suitability conditions."),
        ("2", "Reference-Based Scoring", "Peer-normalized 100-point REITs suitability score."),
        ("3", "Risk Warning", "Sample-relative risk signals and warning flags."),
        ("4", "Model Validity", "Content validity, reliability, and robustness checks."),
    ]
    for column, (number, title, text) in zip(columns, steps):
        with column:
            st.markdown(f"**{number}. {title}**")
            st.write(text)


def main() -> None:
    render_page_header(
        "Tourism REIT Asset Evaluator",
        "文旅消费基础设施 REITs 底层资产评估与风险预警平台",
    )

    st.sidebar.header("Controls")
    weight_mode = selected_weight_mode()

    try:
        asset_options = get_asset_options()
        selected_asset_label = st.sidebar.selectbox("Selected asset", list(asset_options.keys()))
        selected_asset_id = asset_options[selected_asset_label]
        all_data = load_all_data()
    except Exception as exc:
        st.error(f"Unable to load app data: {exc}")
        if st.sidebar.checkbox("Debug mode"):
            st.exception(exc)
        return

    st.sidebar.markdown("### Demo / Simulated Data Notice")
    st.sidebar.caption(
        "Prototype data may be simulated or mixed. Use the source notes before interpreting any result."
    )

    render_notice()

    effective_weight_mode = weight_mode
    if weight_mode == "entropy_weight_placeholder":
        st.warning(ENTROPY_PLACEHOLDER_MESSAGE)
        effective_weight_mode = "default_expert_weight"

    try:
        _indicator_scores_df, _module_scores_df, total_scores_df = run_scoring_pipeline(
            weight_mode=effective_weight_mode
        )
    except Exception as exc:
        st.error(f"Scoring pipeline failed: {exc}")
        if st.sidebar.checkbox("Debug mode"):
            st.exception(exc)
        return

    asset_ids = all_data["assets"]["asset_id"].dropna().astype(str).tolist()
    average_score = pd.to_numeric(total_scores_df["total_score"], errors="coerce").mean()
    highest_row = total_scores_df.sort_values("total_score", ascending=False).iloc[0]
    warning_count = count_gatekeeper_warnings(asset_ids)

    kpi_cols = st.columns(4)
    kpi_cols[0].metric("Asset count", len(asset_ids))
    kpi_cols[1].metric("Average REITs Suitability Score", f"{average_score:.1f}")
    kpi_cols[2].metric("Highest scoring asset", highest_row["asset_name"])
    kpi_cols[3].metric("Assets with Gatekeeper warning", warning_count)

    render_methodology_flow()

    st.subheader("REITs Suitability Score Ranking")
    display_columns = [
        "asset_id",
        "asset_name",
        "a_module_score",
        "b_module_score",
        "c_module_score",
        "d_module_score",
        "e_module_score",
        "total_score",
        "rating_level",
    ]
    score_table = total_scores_df[display_columns].copy()
    st.dataframe(
        score_table.style.format(
            {
                "a_module_score": "{:.1f}",
                "b_module_score": "{:.1f}",
                "c_module_score": "{:.1f}",
                "d_module_score": "{:.1f}",
                "e_module_score": "{:.1f}",
                "total_score": "{:.1f}",
            }
        ),
        use_container_width=True,
    )

    if total_scores_df.dropna(subset=["total_score"]).empty:
        st.info("Score chart is unavailable because no total scores are available.")
    else:
        st.plotly_chart(make_score_bar_chart(total_scores_df), use_container_width=True)

    with st.expander("How to read this dashboard", expanded=True):
        st.markdown(
            """
            - **Regulatory Gatekeeper** checks hard pre-screening conditions before interpreting scores.
            - **REITs Suitability Score** compares assets using latest-year sample-relative indicators.
            - **Risk Warning** highlights higher relative risk categories without using official thresholds.
            - **Model Validity** explains reference coverage, reliability checks, and robustness diagnostics.
            - Always read `data_type` and `source_note`; simulated values are for portfolio demonstration only.
            """
        )

    st.caption(f"Current sidebar asset selection: {selected_asset_id}. Page-level views use their own selectors.")


if __name__ == "__main__":
    main()

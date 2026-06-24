"""Streamlit entry point for the Tourism REIT Asset Evaluator."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.chart_utils import make_score_bar_chart
from src.data_loader import get_asset_options, load_all_data
from src.gatekeeper import run_gatekeeper_checks
from src.i18n import language_selector, localize_dataframe, t, translate_column_name
from src.scoring_model import ENTROPY_PLACEHOLDER_MESSAGE, run_scoring_pipeline


st.set_page_config(
    page_title="Tourism REIT Asset Evaluator",
    layout="wide",
)

# Streamlit's default multipage navigation is filename-driven in this app.
# Page content headings and controls are localized; custom navigation can be added later if needed.


def render_page_header(title: str, subtitle: str) -> None:
    st.title(title)
    st.caption(subtitle)


def render_notice() -> None:
    st.info(f"**{t('common.generated_notice_title')}:** {t('common.disclaimer')}")


def selected_weight_mode() -> str:
    return st.sidebar.selectbox(
        t("common.weighting_mode"),
        ["default_expert_weight", "equal_weight", "entropy_weight_placeholder"],
        index=0,
        format_func=lambda value: t(f"weight_modes.{value}", value),
        help=ENTROPY_PLACEHOLDER_MESSAGE,
    )


def count_gatekeeper_warnings(asset_ids: list[str]) -> int:
    warning_count = 0
    for asset_id in asset_ids:
        results_df, overall_status, _summary = run_gatekeeper_checks(asset_id)
        has_warning = overall_status == "Pass with Warning" or (results_df["status"] == "Warning").any()
        warning_count += int(has_warning)
    return warning_count


def render_methodology_flow() -> None:
    st.subheader(t("home.methodology_flow"))
    columns = st.columns(4)
    steps = [
        ("1", t("methodology.gatekeeper"), t("home.flow_gatekeeper_text")),
        ("2", t("methodology.scoring"), t("home.flow_scoring_text")),
        ("3", t("methodology.risk_warning"), t("home.flow_risk_text")),
        ("4", t("methodology.model_validity"), t("home.flow_validity_text")),
    ]
    for column, (number, title, text) in zip(columns, steps):
        with column:
            st.markdown(f"**{number}. {title}**")
            st.write(text)


def main() -> None:
    language_selector()
    render_page_header(
        t("app.title"),
        t("app.subtitle"),
    )

    st.sidebar.header(t("common.controls"))
    weight_mode = selected_weight_mode()

    try:
        asset_options = get_asset_options()
        selected_asset_label = st.sidebar.selectbox(t("common.selected_asset"), list(asset_options.keys()))
        selected_asset_id = asset_options[selected_asset_label]
        all_data = load_all_data()
    except Exception as exc:
        st.error(t("common.unable_to_load_data", error=exc))
        if st.sidebar.checkbox(t("common.debug_mode")):
            st.exception(exc)
        return

    st.sidebar.markdown(f"### {t('common.generated_notice_title')}")
    st.sidebar.caption(t("common.sidebar_notice"))

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
        st.error(t("score.pipeline_failed", error=exc))
        if st.sidebar.checkbox(t("common.debug_mode")):
            st.exception(exc)
        return

    asset_ids = all_data["assets"]["asset_id"].dropna().astype(str).tolist()
    average_score = pd.to_numeric(total_scores_df["total_score"], errors="coerce").mean()
    highest_row = total_scores_df.sort_values("total_score", ascending=False).iloc[0]
    warning_count = count_gatekeeper_warnings(asset_ids)

    kpi_cols = st.columns(4)
    kpi_cols[0].metric(t("labels.asset_count"), len(asset_ids))
    kpi_cols[1].metric(t("labels.average_score"), f"{average_score:.1f}")
    kpi_cols[2].metric(t("labels.highest_scoring_asset"), highest_row["asset_name"])
    kpi_cols[3].metric(t("labels.assets_with_gatekeeper_warning"), warning_count)

    render_methodology_flow()

    st.subheader(t("home.score_ranking"))
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
    display_score_table = localize_dataframe(score_table)
    st.dataframe(
        display_score_table.style.format(
            {
                translate_column_name("a_module_score"): "{:.1f}",
                translate_column_name("b_module_score"): "{:.1f}",
                translate_column_name("c_module_score"): "{:.1f}",
                translate_column_name("d_module_score"): "{:.1f}",
                translate_column_name("e_module_score"): "{:.1f}",
                translate_column_name("total_score"): "{:.1f}",
            }
        ),
        use_container_width=True,
    )

    if total_scores_df.dropna(subset=["total_score"]).empty:
        st.info(t("home.score_chart_unavailable"))
    else:
        st.plotly_chart(make_score_bar_chart(total_scores_df), use_container_width=True)

    with st.expander(t("home.how_to_read"), expanded=True):
        st.markdown(t("home.how_to_read_text"))

    st.caption(t("home.current_sidebar_asset", asset_id=selected_asset_id))


if __name__ == "__main__":
    main()

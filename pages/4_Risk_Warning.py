"""Risk warning page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.chart_utils import RISK_COLUMNS, make_heatmap_from_risk_scores, make_risk_radar
from src.data_loader import get_asset_options, get_latest_year_data, load_all_data
from src.gatekeeper import run_gatekeeper_checks
from src.i18n import language_selector, localize_dataframe, t, translate_column_name, translate_risk_label


st.set_page_config(page_title="Risk Warning", layout="wide")


def relative_risk_status(value: float, sample: pd.Series) -> tuple[str, str]:
    numeric_sample = pd.to_numeric(sample, errors="coerce").dropna()
    if pd.isna(value) or numeric_sample.empty:
        return t("statuses.unavailable"), "#667085"
    percentile_75 = numeric_sample.quantile(0.75)
    if value >= percentile_75:
        return t("statuses.high_relative_risk"), "#B42318"
    return t("statuses.within_sample_range"), "#1B7F4B"


def main() -> None:
    language_selector()
    st.title(t("risk.title"))
    st.caption(t("risk.subtitle"))

    try:
        asset_options = get_asset_options()
        selected_label = st.selectbox(t("common.select_asset"), list(asset_options.keys()))
        asset_id = asset_options[selected_label]
        data = load_all_data()
    except Exception as exc:
        st.error(t("common.unable_to_load_risk_data", error=exc))
        if st.checkbox(t("common.debug_mode")):
            st.exception(exc)
        return

    latest_risk = get_latest_year_data(data["risk_metrics"])
    selected_risk = latest_risk[latest_risk["asset_id"] == asset_id]

    st.info(t("risk.notice"))

    if selected_risk.empty:
        st.warning(t("risk.latest_unavailable"))
        return

    row = selected_risk.iloc[0]
    st.subheader(t("risk.category_cards"))
    available_risks = [column for column in RISK_COLUMNS if column in latest_risk.columns]
    card_columns = st.columns(3)
    high_risk_categories: list[str] = []
    for index, column in enumerate(available_risks):
        value = pd.to_numeric(pd.Series([row[column]]), errors="coerce").iloc[0]
        status, _color = relative_risk_status(value, latest_risk[column])
        if status == t("statuses.high_relative_risk"):
            high_risk_categories.append(translate_risk_label(column))
        with card_columns[index % 3]:
            st.metric(translate_risk_label(column), f"{value:.2f}" if pd.notna(value) else t("common.data_unavailable"))
            st.caption(status)

    if high_risk_categories:
        st.warning(t("risk.high_categories", categories=", ".join(high_risk_categories)))
    else:
        st.success(t("risk.no_high_categories"))

    chart_cols = st.columns([1, 1])
    with chart_cols[0]:
        st.subheader(t("risk.radar"))
        if selected_risk[available_risks].dropna(how="all").empty:
            st.info(t("risk.radar_unavailable"))
        else:
            st.plotly_chart(make_risk_radar(data["risk_metrics"], asset_id), use_container_width=True)

    with chart_cols[1]:
        st.subheader(t("risk.heatmap"))
        if latest_risk[available_risks].dropna(how="all").empty:
            st.info(t("risk.heatmap_unavailable"))
        else:
            st.plotly_chart(make_heatmap_from_risk_scores(data["risk_metrics"]), use_container_width=True)

    st.subheader(t("risk.latest_metrics"))
    display_risk = localize_dataframe(selected_risk)
    st.dataframe(
        display_risk.style.format(
            {translate_column_name(column): "{:.2f}" for column in available_risks},
            na_rep=t("common.data_unavailable"),
        ),
        use_container_width=True,
    )
    st.caption(f"data_type: {row['data_type']} | source_note: {row['source_note']}")

    try:
        gatekeeper_results, _overall_status, _summary_text = run_gatekeeper_checks(asset_id)
        warning_rows = gatekeeper_results[gatekeeper_results["status"] == "Warning"]
        st.subheader(t("risk.gatekeeper_warning_explanation"))
        if warning_rows.empty:
            st.success(t("risk.no_gatekeeper_warnings"))
        else:
            st.dataframe(localize_dataframe(warning_rows), use_container_width=True, hide_index=True)
    except Exception as exc:
        st.error(t("risk.warning_error", error=exc))
        if st.checkbox(t("risk.debug_warnings")):
            st.exception(exc)


main()

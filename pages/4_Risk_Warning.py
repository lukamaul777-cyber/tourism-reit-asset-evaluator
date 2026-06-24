"""Risk warning page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.chart_utils import RISK_COLUMNS, RISK_LABELS, make_heatmap_from_risk_scores, make_risk_radar
from src.data_loader import get_asset_options, get_latest_year_data, load_all_data
from src.gatekeeper import run_gatekeeper_checks


st.set_page_config(page_title="Risk Warning", layout="wide")


def relative_risk_status(value: float, sample: pd.Series) -> tuple[str, str]:
    numeric_sample = pd.to_numeric(sample, errors="coerce").dropna()
    if pd.isna(value) or numeric_sample.empty:
        return "Unavailable", "#667085"
    percentile_75 = numeric_sample.quantile(0.75)
    if value >= percentile_75:
        return "High relative risk", "#B42318"
    return "Within sample range", "#1B7F4B"


def main() -> None:
    st.title("Risk Warning")
    st.caption(
        "Review latest risk signals and Regulatory Gatekeeper warnings. High-risk labels are sample-relative, "
        "not official thresholds."
    )

    try:
        asset_options = get_asset_options()
        selected_label = st.selectbox("Asset", list(asset_options.keys()))
        asset_id = asset_options[selected_label]
        data = load_all_data()
    except Exception as exc:
        st.error(f"Unable to load risk data: {exc}")
        if st.checkbox("Debug mode"):
            st.exception(exc)
        return

    latest_risk = get_latest_year_data(data["risk_metrics"])
    selected_risk = latest_risk[latest_risk["asset_id"] == asset_id]

    st.info(
        "Demo / Simulated Data Notice: risk values marked simulated or mixed are MVP demo values. "
        "They are sample-relative warning signals, not official risk disclosures or investment advice."
    )

    if selected_risk.empty:
        st.warning("Latest risk metrics are unavailable for this asset.")
        return

    row = selected_risk.iloc[0]
    st.subheader("Risk Category Cards")
    available_risks = [column for column in RISK_COLUMNS if column in latest_risk.columns]
    card_columns = st.columns(3)
    high_risk_categories: list[str] = []
    for index, column in enumerate(available_risks):
        value = pd.to_numeric(pd.Series([row[column]]), errors="coerce").iloc[0]
        status, _color = relative_risk_status(value, latest_risk[column])
        if status == "High relative risk":
            high_risk_categories.append(RISK_LABELS.get(column, column))
        with card_columns[index % 3]:
            st.metric(RISK_LABELS.get(column, column), f"{value:.2f}" if pd.notna(value) else "N/A")
            st.caption(status)

    if high_risk_categories:
        st.warning("High relative risk categories: " + ", ".join(high_risk_categories) + ".")
    else:
        st.success("No selected risk category is above the sample 75th percentile.")

    chart_cols = st.columns([1, 1])
    with chart_cols[0]:
        st.subheader("Risk Radar Chart")
        if selected_risk[available_risks].dropna(how="all").empty:
            st.info("Risk radar chart is unavailable because risk values are missing.")
        else:
            st.plotly_chart(make_risk_radar(data["risk_metrics"], asset_id), use_container_width=True)

    with chart_cols[1]:
        st.subheader("Risk Heatmap")
        if latest_risk[available_risks].dropna(how="all").empty:
            st.info("Risk heatmap is unavailable because risk values are missing.")
        else:
            st.plotly_chart(make_heatmap_from_risk_scores(data["risk_metrics"]), use_container_width=True)

    st.subheader("Latest Risk Metrics")
    st.dataframe(selected_risk.style.format({column: "{:.2f}" for column in available_risks}), use_container_width=True)
    st.caption(f"data_type: {row['data_type']} | source_note: {row['source_note']}")

    try:
        gatekeeper_results, _overall_status, _summary_text = run_gatekeeper_checks(asset_id)
        warning_rows = gatekeeper_results[gatekeeper_results["status"] == "Warning"]
        st.subheader("Regulatory Gatekeeper Warning Explanation")
        if warning_rows.empty:
            st.success("No Gatekeeper warnings for this asset.")
        else:
            st.dataframe(warning_rows, use_container_width=True, hide_index=True)
    except Exception as exc:
        st.error(f"Unable to generate warning explanation: {exc}")
        if st.checkbox("Debug warnings"):
            st.exception(exc)


main()

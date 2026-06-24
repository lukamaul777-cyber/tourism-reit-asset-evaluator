"""Asset profile page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.data_loader import get_asset_options, get_latest_year_data, load_all_data
from src.gatekeeper import run_gatekeeper_checks


st.set_page_config(page_title="Asset Profile", layout="wide")


def status_badge(status: str) -> str:
    colors = {
        "Pass": "#1B7F4B",
        "Pass with Warning": "#A96D00",
        "Warning": "#A96D00",
        "Fail": "#B42318",
    }
    color = colors.get(status, "#475467")
    return (
        f"<span style='display:inline-block;padding:0.25rem 0.55rem;border-radius:999px;"
        f"background:{color};color:white;font-weight:600;font-size:0.85rem'>{status}</span>"
    )


def render_page_header() -> None:
    st.title("Asset Profile")
    st.caption("Review asset identity, source notes, Regulatory Gatekeeper results, and latest operating metrics.")


def format_metric_table(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    return df.style.format(
        {
            "revenue": "{:,.0f}",
            "ebitda": "{:,.0f}",
            "noi": "{:,.0f}",
            "operating_cash_flow": "{:,.0f}",
            "maintenance_capex": "{:,.0f}",
            "estimated_affo": "{:,.0f}",
            "estimated_distribution": "{:,.0f}",
            "total_assets": "{:,.0f}",
            "total_debt": "{:,.0f}",
            "debt_ratio": "{:.1%}",
            "capex_to_ocf": "{:.1%}",
            "visitor_volume": "{:,.0f}",
            "occupancy_rate": "{:.1%}",
            "adr": "{:,.0f}",
            "revpar": "{:,.0f}",
            "average_spending_per_visitor": "{:,.0f}",
            "secondary_spending_ratio": "{:.1%}",
            "peak_season_revenue_ratio": "{:.1%}",
        },
        na_rep="N/A",
    )


def main() -> None:
    render_page_header()

    try:
        asset_options = get_asset_options()
        selected_label = st.selectbox("Asset", list(asset_options.keys()))
        asset_id = asset_options[selected_label]
        data = load_all_data()
    except Exception as exc:
        st.error(f"Unable to load asset data: {exc}")
        if st.checkbox("Debug mode"):
            st.exception(exc)
        return

    asset_row = data["assets"][data["assets"]["asset_id"] == asset_id].iloc[0]
    latest_financial = get_latest_year_data(data["financial_metrics"])
    latest_operation = get_latest_year_data(data["operation_metrics"])
    selected_financial = latest_financial[latest_financial["asset_id"] == asset_id]
    selected_operation = latest_operation[latest_operation["asset_id"] == asset_id]

    try:
        gatekeeper_results, overall_status, summary_text = run_gatekeeper_checks(asset_id)
    except Exception as exc:
        gatekeeper_results = pd.DataFrame()
        overall_status = "Unavailable"
        summary_text = f"Gatekeeper checks failed: {exc}"

    st.markdown(status_badge(overall_status), unsafe_allow_html=True)
    st.subheader(asset_row["asset_name"])

    profile_tab, gatekeeper_tab, financial_tab, operation_tab, notes_tab = st.tabs(
        [
            "Basic Profile",
            "Gatekeeper Results",
            "Latest Financial Metrics",
            "Latest Operation Metrics",
            "Data Source Notes",
        ]
    )

    with profile_tab:
        col1, col2, col3 = st.columns(3)
        col1.metric("Asset type", asset_row["asset_type"])
        col2.metric("Location", asset_row["location"])
        col3.metric("Operation years", f"{float(asset_row['operation_years']):.0f}")
        st.write(asset_row["description"])
        st.info(f"Demo / Simulated Data Notice: {asset_row['source_note']}")

    with gatekeeper_tab:
        st.markdown(f"**Regulatory Gatekeeper status:** {status_badge(overall_status)}", unsafe_allow_html=True)
        st.write(summary_text)
        if gatekeeper_results.empty:
            st.info("Gatekeeper results are unavailable for this asset.")
        else:
            display_results = gatekeeper_results.copy()
            display_results["status_badge"] = display_results["status"].map(status_badge)
            st.dataframe(
                display_results[["condition", "status", "explanation", "reference_logic"]],
                use_container_width=True,
                hide_index=True,
            )

    with financial_tab:
        if selected_financial.empty:
            st.info("Latest financial metrics are unavailable for this asset.")
        else:
            st.dataframe(format_metric_table(selected_financial), use_container_width=True, hide_index=True)

    with operation_tab:
        if selected_operation.empty:
            st.info("Latest operation metrics are unavailable for this asset.")
        else:
            st.dataframe(format_metric_table(selected_operation), use_container_width=True, hide_index=True)

    with notes_tab:
        st.subheader("Data Source Notes")
        note_rows = []
        for table_name, table_df in {
            "assets": data["assets"],
            "financial_metrics": selected_financial,
            "operation_metrics": selected_operation,
        }.items():
            if table_df.empty:
                continue
            row = table_df.iloc[0]
            note_rows.append(
                {
                    "table": table_name,
                    "data_type": row.get("data_type", "N/A"),
                    "source_note": row.get("source_note", "N/A"),
                }
            )
        st.dataframe(pd.DataFrame(note_rows), use_container_width=True, hide_index=True)


main()

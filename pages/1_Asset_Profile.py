"""Asset profile page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.data_loader import get_asset_options, get_latest_year_data, load_all_data
from src.gatekeeper import run_gatekeeper_checks
from src.i18n import language_selector, localize_dataframe, t, translate_column_name, translate_status


st.set_page_config(page_title="Asset Profile", layout="wide")


def status_badge(status: str, label: str | None = None) -> str:
    colors = {
        "Pass": "#1B7F4B",
        "Pass with Warning": "#A96D00",
        "Warning": "#A96D00",
        "Fail": "#B42318",
    }
    color = colors.get(status, "#475467")
    badge_label = label or status
    return (
        f"<span style='display:inline-block;padding:0.25rem 0.55rem;border-radius:999px;"
        f"background:{color};color:white;font-weight:600;font-size:0.85rem'>{badge_label}</span>"
    )


def render_page_header() -> None:
    st.title(t("asset_profile.title"))
    st.caption(t("asset_profile.subtitle"))


def format_metric_table(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    format_map = {
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
    }
    display_df = localize_dataframe(df)
    display_format_map = {translate_column_name(column): fmt for column, fmt in format_map.items()}
    return display_df.style.format(display_format_map, na_rep=t("common.data_unavailable"))


def main() -> None:
    language_selector()
    render_page_header()

    try:
        asset_options = get_asset_options()
        selected_label = st.selectbox(t("common.select_asset"), list(asset_options.keys()))
        asset_id = asset_options[selected_label]
        data = load_all_data()
    except Exception as exc:
        st.error(t("common.unable_to_load_asset_data", error=exc))
        if st.checkbox(t("common.debug_mode")):
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
        summary_text = t("asset_profile.gatekeeper_failed", error=exc)

    st.markdown(status_badge(overall_status, translate_status(overall_status)), unsafe_allow_html=True)
    st.subheader(asset_row["asset_name"])

    profile_tab, gatekeeper_tab, financial_tab, operation_tab, notes_tab = st.tabs(
        [
            t("asset_profile.basic_profile"),
            t("asset_profile.gatekeeper_results"),
            t("asset_profile.latest_financial_metrics"),
            t("asset_profile.latest_operation_metrics"),
            t("asset_profile.data_source_notes"),
        ]
    )

    with profile_tab:
        col1, col2, col3 = st.columns(3)
        col1.metric(t("labels.asset_type"), asset_row["asset_type"])
        col2.metric(t("labels.location"), asset_row["location"])
        col3.metric(t("labels.operation_years"), f"{float(asset_row['operation_years']):.0f}")
        st.write(asset_row["description"])
        st.info(t("common.source_note_notice", source_note=asset_row["source_note"]))

    with gatekeeper_tab:
        st.markdown(
            f"**{t('asset_profile.regulatory_gatekeeper_status')}** "
            f"{status_badge(overall_status, translate_status(overall_status))}",
            unsafe_allow_html=True,
        )
        st.write(summary_text)
        if gatekeeper_results.empty:
            st.info(t("asset_profile.gatekeeper_unavailable"))
        else:
            display_results = gatekeeper_results.copy()
            display_results["status_badge"] = display_results["status"].map(status_badge)
            st.dataframe(
                localize_dataframe(display_results[["condition", "status", "explanation", "reference_logic"]]),
                use_container_width=True,
                hide_index=True,
            )

    with financial_tab:
        if selected_financial.empty:
            st.info(t("asset_profile.financial_unavailable"))
        else:
            st.dataframe(format_metric_table(selected_financial), use_container_width=True, hide_index=True)

    with operation_tab:
        if selected_operation.empty:
            st.info(t("asset_profile.operation_unavailable"))
        else:
            st.dataframe(format_metric_table(selected_operation), use_container_width=True, hide_index=True)

    with notes_tab:
        st.subheader(t("asset_profile.data_source_notes"))
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
        st.dataframe(localize_dataframe(pd.DataFrame(note_rows)), use_container_width=True, hide_index=True)


main()

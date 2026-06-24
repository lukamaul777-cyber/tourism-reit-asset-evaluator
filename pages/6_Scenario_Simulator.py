"""Scenario Simulator page."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.chart_utils import (
    make_base_vs_simulated_bar,
    make_cash_flow_impact_chart,
    make_score_change_chart,
)
from src.data_loader import get_asset_options
from src.scenario_simulator import run_demo_scenarios, simulate_asset_scenario


st.set_page_config(page_title="Scenario Simulator", layout="wide")


PRESETS = {
    "Custom Scenario": {
        "revenue_decline_pct": 0.0,
        "visitor_volume_decline_pct": 0.0,
        "occupancy_decline_pct": 0.0,
        "adr_decline_pct": 0.0,
        "operating_cost_increase_pct": 0.0,
        "maintenance_capex_increase_pct": 0.0,
        "ota_score_decline": 0.0,
    },
    "Mild Downside": {
        "revenue_decline_pct": 0.05,
        "visitor_volume_decline_pct": 0.0,
        "occupancy_decline_pct": 0.0,
        "adr_decline_pct": 0.0,
        "operating_cost_increase_pct": 0.05,
        "maintenance_capex_increase_pct": 0.0,
        "ota_score_decline": 0.0,
    },
    "Demand Shock": {
        "revenue_decline_pct": 0.15,
        "visitor_volume_decline_pct": 0.20,
        "occupancy_decline_pct": 0.10,
        "adr_decline_pct": 0.05,
        "operating_cost_increase_pct": 0.0,
        "maintenance_capex_increase_pct": 0.0,
        "ota_score_decline": 0.0,
    },
    "Stress Case": {
        "revenue_decline_pct": 0.25,
        "visitor_volume_decline_pct": 0.30,
        "occupancy_decline_pct": 0.15,
        "adr_decline_pct": 0.10,
        "operating_cost_increase_pct": 0.15,
        "maintenance_capex_increase_pct": 0.20,
        "ota_score_decline": 0.30,
    },
}


def fmt_number(value: float | None, digits: int = 2) -> str:
    if value is None or pd.isna(value):
        return "Data unavailable"
    return f"{value:,.{digits}f}"


def fmt_score(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "Data unavailable"
    return f"{value:.1f}"


def apply_preset(preset_name: str) -> None:
    for key, value in PRESETS[preset_name].items():
        st.session_state[key] = value
        st.session_state[f"{key}_ui"] = int(round(value * 100)) if key != "ota_score_decline" else value


def percent_slider(label: str, key: str, max_percent: int) -> float:
    value = st.slider(
        label,
        min_value=0,
        max_value=max_percent,
        value=int(st.session_state.get(f"{key}_ui", round(float(st.session_state.get(key, 0.0)) * 100))),
        step=1,
        format="%d%%",
        key=f"{key}_ui",
    )
    st.session_state[key] = value / 100
    return value / 100


def score_decline_slider(label: str, key: str) -> float:
    value = st.slider(
        label,
        min_value=0.0,
        max_value=1.0,
        value=float(st.session_state.get(f"{key}_ui", st.session_state.get(key, 0.0))),
        step=0.1,
        format="%.1f",
        key=f"{key}_ui",
    )
    st.session_state[key] = value
    return value


def result_to_table(metrics: dict[str, float | None]) -> pd.DataFrame:
    return pd.DataFrame(
        [{"metric": key, "value": value if value is not None else pd.NA} for key, value in metrics.items()]
    )


def make_demo_scenario_chart(demo_df: pd.DataFrame):
    if demo_df.empty or "simulated_score" not in demo_df.columns:
        return None
    plot_df = demo_df.copy()
    plot_df["simulated_score"] = pd.to_numeric(plot_df["simulated_score"], errors="coerce")
    if plot_df["simulated_score"].dropna().empty:
        return None
    fig = px.bar(
        plot_df,
        x="asset_name",
        y="simulated_score",
        color="scenario_name",
        barmode="group",
        text="simulated_score",
        title="Demo Scenario Simulated Scores",
        range_y=[0, 100],
        color_discrete_sequence=px.colors.qualitative.Safe,
    )
    fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    fig.update_layout(
        xaxis_title="",
        yaxis_title="Simulated REITs Suitability Score",
        template="plotly_white",
        height=430,
        legend_title_text="Scenario",
    )
    return fig


def main() -> None:
    st.title("Scenario Simulator")
    st.caption("文旅资产情景模拟与压力测试")
    st.info(
        "This page estimates how selected operational and financial shocks may affect cash flow, "
        "AFFO proxy, distribution coverage, and REITs suitability score. It is a simplified "
        "stress-test module, not a forecast, valuation opinion, investment recommendation, or regulatory conclusion."
    )

    try:
        asset_options = get_asset_options()
    except Exception as exc:
        st.error(f"Unable to load asset options: {exc}")
        if st.checkbox("Debug mode"):
            st.exception(exc)
        return

    control_col, output_col = st.columns([0.36, 0.64])

    with control_col:
        st.subheader("Scenario Controls")
        selected_label = st.selectbox("Asset", list(asset_options.keys()))
        asset_id = asset_options[selected_label]
        preset = st.selectbox("Scenario preset", list(PRESETS.keys()))
        if st.button("Apply preset", use_container_width=True):
            apply_preset(preset)

        if preset != "Custom Scenario":
            st.caption("Use Apply preset to populate the sliders with the selected stress-test case.")

        revenue_decline_pct = percent_slider("Revenue decline", "revenue_decline_pct", 50)
        visitor_volume_decline_pct = percent_slider("Visitor volume decline", "visitor_volume_decline_pct", 50)
        occupancy_decline_pct = percent_slider("Occupancy decline", "occupancy_decline_pct", 30)
        adr_decline_pct = percent_slider("ADR decline", "adr_decline_pct", 30)
        operating_cost_increase_pct = percent_slider(
            "Operating cost increase",
            "operating_cost_increase_pct",
            50,
        )
        maintenance_capex_increase_pct = percent_slider(
            "Maintenance CAPEX increase",
            "maintenance_capex_increase_pct",
            50,
        )
        ota_score_decline = score_decline_slider("OTA score decline", "ota_score_decline")

    try:
        result = simulate_asset_scenario(
            asset_id=asset_id,
            revenue_decline_pct=revenue_decline_pct,
            visitor_volume_decline_pct=visitor_volume_decline_pct,
            occupancy_decline_pct=occupancy_decline_pct,
            adr_decline_pct=adr_decline_pct,
            operating_cost_increase_pct=operating_cost_increase_pct,
            maintenance_capex_increase_pct=maintenance_capex_increase_pct,
            ota_score_decline=ota_score_decline,
        )
    except Exception as exc:
        st.error(f"Scenario simulation failed: {exc}")
        if st.checkbox("Debug simulation"):
            st.exception(exc)
        return

    with output_col:
        st.subheader("Simulation Output")
        kpi_cols = st.columns(4)
        kpi_cols[0].metric("Base REITs Suitability Score", fmt_score(result["base_score"]))
        kpi_cols[1].metric("Simulated REITs Suitability Score", fmt_score(result["simulated_score"]))
        kpi_cols[2].metric("Score Change", fmt_score(result["score_change"]))
        kpi_cols[3].metric("Scenario Severity", result["severity"])

        kpi_cols_2 = st.columns(4)
        kpi_cols_2[0].metric(
            "Base Distribution Coverage",
            fmt_number(result["base_metrics"]["distribution_coverage"]),
        )
        kpi_cols_2[1].metric(
            "Simulated Distribution Coverage",
            fmt_number(result["simulated_metrics"]["distribution_coverage_after"]),
        )
        kpi_cols_2[2].metric("AFFO Change", fmt_number(result["impact_metrics"]["affo_change"]))
        kpi_cols_2[3].metric("NOI Change", fmt_number(result["impact_metrics"]["noi_change"]))

        if result["warnings"]:
            st.warning(" ".join(result["warnings"]))

    chart_col_1, chart_col_2 = st.columns(2)
    with chart_col_1:
        st.subheader("Score Impact")
        if result["base_score"] is None or result["simulated_score"] is None:
            st.info("Score comparison is unavailable because score data is missing.")
        else:
            st.plotly_chart(
                make_base_vs_simulated_bar(
                    result["base_score"],
                    result["simulated_score"],
                    "Base vs Simulated REITs Suitability Score",
                    "Score",
                ),
                use_container_width=True,
            )

    with chart_col_2:
        st.subheader("Distribution Coverage Impact")
        if (
            result["base_metrics"]["distribution_coverage"] is None
            or result["simulated_metrics"]["distribution_coverage_after"] is None
        ):
            st.info("Distribution coverage cannot be calculated because estimated distribution is unavailable or zero.")
        else:
            st.plotly_chart(
                make_base_vs_simulated_bar(
                    result["base_metrics"]["distribution_coverage"],
                    result["simulated_metrics"]["distribution_coverage_after"],
                    "Base vs Simulated Distribution Coverage",
                    "Coverage Ratio",
                ),
                use_container_width=True,
            )

    cash_col, waterfall_col = st.columns(2)
    with cash_col:
        st.subheader("Cash Flow Impact")
        cash_values = [
            result["base_metrics"].get("noi"),
            result["simulated_metrics"].get("noi_after"),
            result["base_metrics"].get("operating_cash_flow"),
            result["simulated_metrics"].get("operating_cash_flow_after"),
            result["base_metrics"].get("estimated_affo"),
            result["simulated_metrics"].get("affo_after"),
        ]
        if pd.Series(cash_values).dropna().empty:
            st.info("Cash flow impact chart is unavailable because cash flow metrics are missing.")
        else:
            st.plotly_chart(
                make_cash_flow_impact_chart(result["base_metrics"], result["simulated_metrics"]),
                use_container_width=True,
            )

    with waterfall_col:
        st.subheader("Score Change Waterfall")
        if result["score_change"] is None:
            st.info("Score change waterfall is unavailable because score impact is missing.")
        else:
            st.plotly_chart(
                make_score_change_chart(result["base_score"], result["score_change"], result["simulated_score"]),
                use_container_width=True,
            )

    st.subheader("Automatic Scenario Explanation")
    st.info(result["explanation"])

    table_tab_1, table_tab_2, table_tab_3 = st.tabs(["Base Metrics", "Simulated Metrics", "Impact Metrics"])
    with table_tab_1:
        st.dataframe(result_to_table(result["base_metrics"]).style.format({"value": "{:,.3f}"}, na_rep="Data unavailable"), use_container_width=True)
    with table_tab_2:
        st.dataframe(result_to_table(result["simulated_metrics"]).style.format({"value": "{:,.3f}"}, na_rep="Data unavailable"), use_container_width=True)
    with table_tab_3:
        st.dataframe(result_to_table(result["impact_metrics"]).style.format({"value": "{:,.3f}"}, na_rep="Data unavailable"), use_container_width=True)

    st.divider()
    st.subheader("Demo Scenario Comparison")
    st.caption("Demo scenarios are predefined stress-test cases for comparison and are not forecasts.")
    try:
        demo_df = run_demo_scenarios()
        st.dataframe(
            demo_df.style.format(
                {
                    "base_score": "{:.1f}",
                    "simulated_score": "{:.1f}",
                    "score_change": "{:.1f}",
                    "base_distribution_coverage": "{:.2f}",
                    "simulated_distribution_coverage": "{:.2f}",
                },
                na_rep="Data unavailable",
            ),
            use_container_width=True,
            hide_index=True,
        )
        demo_chart = make_demo_scenario_chart(demo_df)
        if demo_chart is None:
            st.info("Demo scenario score chart is unavailable.")
        else:
            st.plotly_chart(demo_chart, use_container_width=True)
    except Exception as exc:
        st.error(f"Unable to run demo scenario comparison: {exc}")
        if st.checkbox("Debug demo scenarios"):
            st.exception(exc)


main()

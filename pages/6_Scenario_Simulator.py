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
from src.i18n import language_selector, t
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


PRESET_LABEL_KEYS = {
    "Custom Scenario": "scenario.custom",
    "Mild Downside": "scenario.mild_downside",
    "Demand Shock": "scenario.demand_shock",
    "Stress Case": "scenario.stress_case",
}


def fmt_number(value: float | None, digits: int = 2) -> str:
    if value is None or pd.isna(value):
        return t("common.data_unavailable")
    return f"{value:,.{digits}f}"


def fmt_score(value: float | None) -> str:
    if value is None or pd.isna(value):
        return t("common.data_unavailable")
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
        title=t("scenario.demo_chart_title"),
        range_y=[0, 100],
        color_discrete_sequence=px.colors.qualitative.Safe,
    )
    fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    fig.update_layout(
        xaxis_title="",
        yaxis_title=t("scenario.simulated_score_axis"),
        template="plotly_white",
        height=430,
        legend_title_text=t("scenario.scenario_legend"),
    )
    return fig


def main() -> None:
    language_selector()
    st.title(t("scenario.title"))
    st.caption(t("scenario.subtitle"))
    st.info(t("scenario.notice"))

    try:
        asset_options = get_asset_options()
    except Exception as exc:
        st.error(t("common.unable_to_load_asset_options", error=exc))
        if st.checkbox(t("common.debug_mode")):
            st.exception(exc)
        return

    control_col, output_col = st.columns([0.36, 0.64])

    with control_col:
        st.subheader(t("scenario.controls"))
        selected_label = st.selectbox(t("common.select_asset"), list(asset_options.keys()))
        asset_id = asset_options[selected_label]
        preset = st.selectbox(
            t("scenario.preset"),
            list(PRESETS.keys()),
            format_func=lambda value: t(PRESET_LABEL_KEYS.get(value, value), value),
        )
        if st.button(t("common.apply_preset"), use_container_width=True):
            apply_preset(preset)

        if preset != "Custom Scenario":
            st.caption(t("scenario.preset_caption"))

        revenue_decline_pct = percent_slider(t("scenario.revenue_decline"), "revenue_decline_pct", 50)
        visitor_volume_decline_pct = percent_slider(
            t("scenario.visitor_volume_decline"),
            "visitor_volume_decline_pct",
            50,
        )
        occupancy_decline_pct = percent_slider(t("scenario.occupancy_decline"), "occupancy_decline_pct", 30)
        adr_decline_pct = percent_slider(t("scenario.adr_decline"), "adr_decline_pct", 30)
        operating_cost_increase_pct = percent_slider(
            t("scenario.operating_cost_increase"),
            "operating_cost_increase_pct",
            50,
        )
        maintenance_capex_increase_pct = percent_slider(
            t("scenario.maintenance_capex_increase"),
            "maintenance_capex_increase_pct",
            50,
        )
        ota_score_decline = score_decline_slider(t("scenario.ota_score_decline"), "ota_score_decline")

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
        st.error(t("scenario.failed", error=exc))
        if st.checkbox(t("common.debug_simulation")):
            st.exception(exc)
        return

    with output_col:
        st.subheader(t("scenario.output"))
        kpi_cols = st.columns(4)
        kpi_cols[0].metric(t("scenario.base_score"), fmt_score(result["base_score"]))
        kpi_cols[1].metric(t("scenario.simulated_score"), fmt_score(result["simulated_score"]))
        kpi_cols[2].metric(t("scenario.score_change"), fmt_score(result["score_change"]))
        kpi_cols[3].metric(t("scenario.severity"), result["severity"])

        kpi_cols_2 = st.columns(4)
        kpi_cols_2[0].metric(
            t("scenario.base_distribution_coverage"),
            fmt_number(result["base_metrics"]["distribution_coverage"]),
        )
        kpi_cols_2[1].metric(
            t("scenario.simulated_distribution_coverage"),
            fmt_number(result["simulated_metrics"]["distribution_coverage_after"]),
        )
        kpi_cols_2[2].metric(t("scenario.affo_change"), fmt_number(result["impact_metrics"]["affo_change"]))
        kpi_cols_2[3].metric(t("scenario.noi_change"), fmt_number(result["impact_metrics"]["noi_change"]))

        if result["warnings"]:
            st.warning(" ".join(result["warnings"]))

    chart_col_1, chart_col_2 = st.columns(2)
    with chart_col_1:
        st.subheader(t("scenario.score_impact"))
        if result["base_score"] is None or result["simulated_score"] is None:
            st.info(t("scenario.score_comparison_unavailable"))
        else:
            st.plotly_chart(
                make_base_vs_simulated_bar(
                    result["base_score"],
                    result["simulated_score"],
                    t("scenario.score_impact"),
                    t("labels.total_score"),
                ),
                use_container_width=True,
            )

    with chart_col_2:
        st.subheader(t("scenario.distribution_impact"))
        if (
            result["base_metrics"]["distribution_coverage"] is None
            or result["simulated_metrics"]["distribution_coverage_after"] is None
        ):
            st.info(t("scenario.distribution_unavailable"))
        else:
            st.plotly_chart(
                make_base_vs_simulated_bar(
                    result["base_metrics"]["distribution_coverage"],
                    result["simulated_metrics"]["distribution_coverage_after"],
                    t("scenario.distribution_impact"),
                    t("scenario.simulated_distribution_coverage"),
                ),
                use_container_width=True,
            )

    cash_col, waterfall_col = st.columns(2)
    with cash_col:
        st.subheader(t("scenario.cash_flow_impact"))
        cash_values = [
            result["base_metrics"].get("noi"),
            result["simulated_metrics"].get("noi_after"),
            result["base_metrics"].get("operating_cash_flow"),
            result["simulated_metrics"].get("operating_cash_flow_after"),
            result["base_metrics"].get("estimated_affo"),
            result["simulated_metrics"].get("affo_after"),
        ]
        if pd.Series(cash_values).dropna().empty:
            st.info(t("scenario.cash_flow_unavailable"))
        else:
            st.plotly_chart(
                make_cash_flow_impact_chart(result["base_metrics"], result["simulated_metrics"]),
                use_container_width=True,
            )

    with waterfall_col:
        st.subheader(t("scenario.waterfall"))
        if result["score_change"] is None:
            st.info(t("scenario.waterfall_unavailable"))
        else:
            st.plotly_chart(
                make_score_change_chart(result["base_score"], result["score_change"], result["simulated_score"]),
                use_container_width=True,
            )

    st.subheader(t("scenario.explanation"))
    st.info(result["explanation"])

    table_tab_1, table_tab_2, table_tab_3 = st.tabs(
        [t("scenario.base_metrics"), t("scenario.simulated_metrics"), t("scenario.impact_metrics")]
    )
    with table_tab_1:
        st.dataframe(
            result_to_table(result["base_metrics"]).style.format(
                {"value": "{:,.3f}"},
                na_rep=t("common.data_unavailable"),
            ),
            use_container_width=True,
        )
    with table_tab_2:
        st.dataframe(
            result_to_table(result["simulated_metrics"]).style.format(
                {"value": "{:,.3f}"},
                na_rep=t("common.data_unavailable"),
            ),
            use_container_width=True,
        )
    with table_tab_3:
        st.dataframe(
            result_to_table(result["impact_metrics"]).style.format(
                {"value": "{:,.3f}"},
                na_rep=t("common.data_unavailable"),
            ),
            use_container_width=True,
        )

    st.divider()
    st.subheader(t("scenario.demo_comparison"))
    st.caption(t("scenario.demo_caption"))
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
                na_rep=t("common.data_unavailable"),
            ),
            use_container_width=True,
            hide_index=True,
        )
        demo_chart = make_demo_scenario_chart(demo_df)
        if demo_chart is None:
            st.info(t("scenario.demo_chart_unavailable"))
        else:
            st.plotly_chart(demo_chart, use_container_width=True)
    except Exception as exc:
        st.error(t("scenario.demo_error", error=exc))
        if st.checkbox(t("scenario.debug_demo")):
            st.exception(exc)


main()

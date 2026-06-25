"""Interactive report generation page."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import streamlit as st

from src.data_loader import get_asset_options, get_project_root
from src.data_source_ui import render_financial_data_source_selector
from src.i18n import language_selector, t, translate_rating, translate_status
from src.report_generator import (
    generate_asset_report,
    save_report,
    summarize_gatekeeper,
    summarize_score,
)
from src.scenario_simulator import simulate_asset_scenario


st.set_page_config(page_title="Report Generator", layout="wide")


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


def apply_preset(preset_name: str, prefix: str = "report") -> None:
    for key, value in PRESETS[preset_name].items():
        state_key = f"{prefix}_{key}"
        st.session_state[state_key] = value
        st.session_state[f"{state_key}_ui"] = int(round(value * 100)) if key != "ota_score_decline" else value


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


def scenario_controls() -> dict[str, float]:
    preset = st.selectbox(
        t("scenario.preset"),
        list(PRESETS.keys()),
        format_func=lambda value: t(PRESET_LABEL_KEYS.get(value, value), value),
    )
    if st.button(t("common.apply_preset"), use_container_width=True):
        apply_preset(preset)
    if preset != "Custom Scenario":
        st.caption(t("report.preset_caption"))

    prefix = "report"
    return {
        "revenue_decline_pct": percent_slider(t("scenario.revenue_decline"), f"{prefix}_revenue_decline_pct", 50),
        "visitor_volume_decline_pct": percent_slider(
            t("scenario.visitor_volume_decline"),
            f"{prefix}_visitor_volume_decline_pct",
            50,
        ),
        "occupancy_decline_pct": percent_slider(t("scenario.occupancy_decline"), f"{prefix}_occupancy_decline_pct", 30),
        "adr_decline_pct": percent_slider(t("scenario.adr_decline"), f"{prefix}_adr_decline_pct", 30),
        "operating_cost_increase_pct": percent_slider(
            t("scenario.operating_cost_increase"),
            f"{prefix}_operating_cost_increase_pct",
            50,
        ),
        "maintenance_capex_increase_pct": percent_slider(
            t("scenario.maintenance_capex_increase"),
            f"{prefix}_maintenance_capex_increase_pct",
            50,
        ),
        "ota_score_decline": score_decline_slider(t("scenario.ota_score_decline"), f"{prefix}_ota_score_decline"),
    }


def make_report_filename(asset_id: str, scenario_included: bool, suffix: str) -> str:
    scenario_part = "_scenario" if scenario_included else ""
    return f"tourism_reit_report_{asset_id}{scenario_part}.{suffix}"


def render_status_cards(
    asset_id: str,
    weight_mode: str,
    scenario_included: bool,
    financial_data_source: str = "demo",
) -> None:
    try:
        gatekeeper = summarize_gatekeeper(asset_id, financial_data_source=financial_data_source)
        score = summarize_score(asset_id, weight_mode=weight_mode, financial_data_source=financial_data_source)
    except Exception as exc:
        st.warning(t("report.quality_unavailable", error=exc))
        return

    cols = st.columns(5)
    cols[0].metric(t("labels.gatekeeper_status"), translate_status(gatekeeper["overall_status"]))
    cols[1].metric(
        t("labels.total_score"),
        t("common.data_unavailable") if score["total_score"] is None else f"{score['total_score']:.1f}",
    )
    cols[2].metric(t("labels.rating_level"), translate_rating(score["rating_level"]))
    cols[3].metric(t("labels.scenario_included"), t("common.yes") if scenario_included else t("common.no"))
    cols[4].metric(t("labels.data_notice"), t("report.demo_values_may_be_included"))


def save_timestamped_report(report_text: str, asset_id: str, scenario_included: bool) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    scenario_part = "_scenario" if scenario_included else ""
    output_path = get_project_root() / "reports" / f"tourism_reit_report_{asset_id}{scenario_part}_{timestamp}.md"
    return save_report(report_text, output_path)


def main() -> None:
    language_selector()
    _selected_financial_source, effective_financial_source, _did_fallback = render_financial_data_source_selector()
    st.title(t("report.title"))
    st.caption(t("report.subtitle"))
    st.info(t("report.intro"))
    st.warning(t("report.disclaimer"))
    st.caption(t("report.language_note"))

    try:
        asset_options = get_asset_options()
    except Exception as exc:
        st.error(t("common.unable_to_load_asset_options", error=exc))
        if st.checkbox(t("common.debug_mode")):
            st.exception(exc)
        return

    control_col, preview_col = st.columns([0.34, 0.66])

    with control_col:
        st.subheader(t("report.controls"))
        selected_label = st.selectbox(t("common.select_asset"), list(asset_options.keys()))
        asset_id = asset_options[selected_label]
        weight_mode = st.selectbox(
            t("common.weighting_mode"),
            ["default_expert_weight", "equal_weight"],
            index=0,
            format_func=lambda value: t(f"weight_modes.{value}", value),
        )
        include_scenario = st.checkbox(t("report.include_scenario"))

        scenario_kwargs: dict[str, float] = {}
        if include_scenario:
            st.markdown(f"#### {t('report.scenario_controls')}")
            scenario_kwargs = scenario_controls()

        generate_clicked = st.button(t("report.generate"), type="primary", use_container_width=True)

    if not generate_clicked and "generated_report_text" not in st.session_state:
        with preview_col:
            st.subheader(t("report.preview"))
            st.info(t("report.preview_empty"))
        return

    if generate_clicked:
        scenario_result = None
        try:
            if include_scenario:
                scenario_result = simulate_asset_scenario(
                    asset_id=asset_id,
                    weight_mode=weight_mode,
                    financial_data_source=effective_financial_source,
                    **scenario_kwargs,
                )
            report_text = generate_asset_report(
                asset_id=asset_id,
                weight_mode=weight_mode,
                scenario_result=scenario_result,
                financial_data_source=effective_financial_source,
            )
        except Exception as exc:
            st.error(t("report.generation_failed", error=exc))
            if st.checkbox(t("common.debug_report_generation")):
                st.exception(exc)
            return

        st.session_state["generated_report_text"] = report_text
        st.session_state["generated_report_asset_id"] = asset_id
        st.session_state["generated_report_weight_mode"] = weight_mode
        st.session_state["generated_report_scenario_included"] = include_scenario
        st.session_state["generated_report_financial_data_source"] = effective_financial_source

    report_text = st.session_state["generated_report_text"]
    report_asset_id = st.session_state["generated_report_asset_id"]
    scenario_included = bool(st.session_state["generated_report_scenario_included"])

    with preview_col:
        st.subheader(t("report.quality_checks"))
        render_status_cards(
            report_asset_id,
            st.session_state["generated_report_weight_mode"],
            scenario_included,
            st.session_state.get("generated_report_financial_data_source", "demo"),
        )

        st.subheader(t("report.preview"))
        st.markdown(report_text)

        with st.expander(t("report.view_raw"), expanded=False):
            st.code(report_text, language="markdown")

        download_cols = st.columns(3)
        download_cols[0].download_button(
            t("report.download_markdown"),
            data=report_text,
            file_name=make_report_filename(report_asset_id, scenario_included, "md"),
            mime="text/markdown",
            use_container_width=True,
        )
        download_cols[1].download_button(
            t("report.download_txt"),
            data=report_text,
            file_name=make_report_filename(report_asset_id, scenario_included, "txt"),
            mime="text/plain",
            use_container_width=True,
        )
        if download_cols[2].button(t("report.save_local"), use_container_width=True):
            try:
                saved_path = save_timestamped_report(report_text, report_asset_id, scenario_included)
                st.success(t("report.saved_to", path=saved_path))
            except Exception as exc:
                st.error(t("report.save_failed", error=exc))
                if st.checkbox(t("common.debug_report_generation")):
                    st.exception(exc)


main()

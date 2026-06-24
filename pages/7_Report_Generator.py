"""Interactive report generation page."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import streamlit as st

from src.data_loader import get_asset_options, get_project_root
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
    preset = st.selectbox("Scenario preset", list(PRESETS.keys()))
    if st.button("Apply preset", use_container_width=True):
        apply_preset(preset)
    if preset != "Custom Scenario":
        st.caption("Use Apply preset to populate the sliders with this predefined stress-test case.")

    prefix = "report"
    return {
        "revenue_decline_pct": percent_slider("Revenue decline", f"{prefix}_revenue_decline_pct", 50),
        "visitor_volume_decline_pct": percent_slider(
            "Visitor volume decline",
            f"{prefix}_visitor_volume_decline_pct",
            50,
        ),
        "occupancy_decline_pct": percent_slider("Occupancy decline", f"{prefix}_occupancy_decline_pct", 30),
        "adr_decline_pct": percent_slider("ADR decline", f"{prefix}_adr_decline_pct", 30),
        "operating_cost_increase_pct": percent_slider(
            "Operating cost increase",
            f"{prefix}_operating_cost_increase_pct",
            50,
        ),
        "maintenance_capex_increase_pct": percent_slider(
            "Maintenance CAPEX increase",
            f"{prefix}_maintenance_capex_increase_pct",
            50,
        ),
        "ota_score_decline": score_decline_slider("OTA score decline", f"{prefix}_ota_score_decline"),
    }


def make_report_filename(asset_id: str, scenario_included: bool, suffix: str) -> str:
    scenario_part = "_scenario" if scenario_included else ""
    return f"tourism_reit_report_{asset_id}{scenario_part}.{suffix}"


def render_status_cards(asset_id: str, weight_mode: str, scenario_included: bool) -> None:
    try:
        gatekeeper = summarize_gatekeeper(asset_id)
        score = summarize_score(asset_id, weight_mode=weight_mode)
    except Exception as exc:
        st.warning(f"Report quality status unavailable: {exc}")
        return

    cols = st.columns(5)
    cols[0].metric("Gatekeeper status", gatekeeper["overall_status"])
    cols[1].metric("Total score", "Data unavailable" if score["total_score"] is None else f"{score['total_score']:.1f}")
    cols[2].metric("Rating level", score["rating_level"])
    cols[3].metric("Scenario included", "Yes" if scenario_included else "No")
    cols[4].metric("Data notice", "Demo / simulated values may be included")


def save_timestamped_report(report_text: str, asset_id: str, scenario_included: bool) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    scenario_part = "_scenario" if scenario_included else ""
    output_path = get_project_root() / "reports" / f"tourism_reit_report_{asset_id}{scenario_part}_{timestamp}.md"
    return save_report(report_text, output_path)


def main() -> None:
    st.title("Report Generator")
    st.caption("资产分析报告生成器")
    st.info(
        "This page generates a structured asset analysis report based on the Regulatory Gatekeeper, "
        "REITs suitability scoring model, risk warning module, model validity notes, and optional scenario simulation results. "
        "The report is rule-based, deterministic, and does not use external LLM APIs."
    )
    st.warning(
        "Generated reports are for portfolio demonstration and asset management communication only. "
        "They are not investment advice, credit ratings, valuation opinions, or official regulatory conclusions."
    )

    try:
        asset_options = get_asset_options()
    except Exception as exc:
        st.error(f"Unable to load asset options: {exc}")
        if st.checkbox("Debug mode"):
            st.exception(exc)
        return

    control_col, preview_col = st.columns([0.34, 0.66])

    with control_col:
        st.subheader("Report Controls")
        selected_label = st.selectbox("Asset", list(asset_options.keys()))
        asset_id = asset_options[selected_label]
        weight_mode = st.selectbox("Weighting mode", ["default_expert_weight", "equal_weight"], index=0)
        include_scenario = st.checkbox("Include scenario simulation result in report")

        scenario_kwargs: dict[str, float] = {}
        if include_scenario:
            st.markdown("#### Scenario Controls")
            scenario_kwargs = scenario_controls()

        generate_clicked = st.button("Generate Report", type="primary", use_container_width=True)

    if not generate_clicked and "generated_report_text" not in st.session_state:
        with preview_col:
            st.subheader("Report Preview")
            st.info("Choose report controls and click Generate Report.")
        return

    if generate_clicked:
        scenario_result = None
        try:
            if include_scenario:
                scenario_result = simulate_asset_scenario(asset_id=asset_id, weight_mode=weight_mode, **scenario_kwargs)
            report_text = generate_asset_report(
                asset_id=asset_id,
                weight_mode=weight_mode,
                scenario_result=scenario_result,
            )
        except Exception as exc:
            st.error(f"Report generation failed: {exc}")
            if st.checkbox("Debug report generation"):
                st.exception(exc)
            return

        st.session_state["generated_report_text"] = report_text
        st.session_state["generated_report_asset_id"] = asset_id
        st.session_state["generated_report_weight_mode"] = weight_mode
        st.session_state["generated_report_scenario_included"] = include_scenario

    report_text = st.session_state["generated_report_text"]
    report_asset_id = st.session_state["generated_report_asset_id"]
    scenario_included = bool(st.session_state["generated_report_scenario_included"])

    with preview_col:
        st.subheader("Report Quality Checks")
        render_status_cards(report_asset_id, st.session_state["generated_report_weight_mode"], scenario_included)

        st.subheader("Report Preview")
        st.markdown(report_text)

        with st.expander("View raw Markdown", expanded=False):
            st.code(report_text, language="markdown")

        download_cols = st.columns(3)
        download_cols[0].download_button(
            "Download Markdown",
            data=report_text,
            file_name=make_report_filename(report_asset_id, scenario_included, "md"),
            mime="text/markdown",
            use_container_width=True,
        )
        download_cols[1].download_button(
            "Download TXT",
            data=report_text,
            file_name=make_report_filename(report_asset_id, scenario_included, "txt"),
            mime="text/plain",
            use_container_width=True,
        )
        if download_cols[2].button("Save report to local reports folder", use_container_width=True):
            try:
                saved_path = save_timestamped_report(report_text, report_asset_id, scenario_included)
                st.success(f"Saved report to: {saved_path}")
            except Exception as exc:
                st.error(f"Unable to save report: {exc}")
                if st.checkbox("Debug save report"):
                    st.exception(exc)


main()

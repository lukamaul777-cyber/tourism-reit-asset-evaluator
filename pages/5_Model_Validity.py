"""Model validity page."""

from __future__ import annotations

import streamlit as st

from src.i18n import language_selector, t
from src.reliability_validity import generate_validity_report, run_model_validity_pipeline


st.set_page_config(page_title="Model Validity", layout="wide")


def format_optional_float(value: float | None, digits: int = 3) -> str:
    if value is None:
        return "N/A"
    return f"{value:.{digits}f}"


def main() -> None:
    language_selector()
    st.title(t("validity.title"))
    st.caption(t("validity.subtitle"))

    try:
        validity_results = run_model_validity_pipeline()
    except Exception as exc:
        st.error(t("validity.pipeline_failed", error=exc))
        if st.checkbox(t("common.debug_mode")):
            st.exception(exc)
        return

    cronbach = validity_results["cronbach_alpha"]
    ahp = validity_results["ahp_consistency"]
    sensitivity = validity_results["sensitivity_analysis"]
    content_table = validity_results["content_validity_table"]

    st.info(t("validity.notice"))

    content_tab, reliability_tab, ahp_tab, sensitivity_tab, limitations_tab = st.tabs(
        [
            t("validity.content_validity"),
            t("validity.reliability"),
            t("validity.ahp_consistency"),
            t("validity.sensitivity_analysis"),
            t("validity.limitations"),
        ]
    )

    with content_tab:
        st.subheader(t("validity.content_validity"))
        col1, col2, col3 = st.columns(3)
        col1.metric(t("labels.indicator_count"), len(content_table))
        col2.metric(t("labels.module_count"), content_table["module"].nunique())
        col3.metric(t("labels.required_indicators"), int(content_table["whether_it_is_required"].sum()))
        st.write(t("validity.content_validity_text"))
        st.dataframe(content_table, use_container_width=True, hide_index=True)

    with reliability_tab:
        st.subheader(t("validity.reliability"))
        col1, col2, col3 = st.columns(3)
        col1.metric(t("validity.cronbach_alpha"), format_optional_float(cronbach["alpha"]))
        col2.metric(t("validity.status"), cronbach["status"])
        col3.metric(t("validity.valid_item_count"), cronbach.get("valid_item_count", "N/A"))
        st.write(cronbach["explanation"])
        st.warning(t("validity.cronbach_warning"))

    with ahp_tab:
        st.subheader(t("validity.ahp_consistency"))
        st.metric(t("validity.ahp_status"), ahp["status"])
        st.write(ahp["explanation"])
        if ahp["status"] == "not_run":
            st.info(t("validity.ahp_not_run"))
        else:
            st.json(ahp)

    with sensitivity_tab:
        st.subheader(t("validity.sensitivity_analysis"))
        col1, col2 = st.columns(2)
        ranking_stability = sensitivity.get("ranking_stability_ratio")
        average_spearman = sensitivity.get("average_spearman_correlation")
        col1.metric(
            t("validity.ranking_stability_ratio"),
            "N/A" if ranking_stability is None else f"{ranking_stability:.1%}",
        )
        col2.metric(
            t("validity.average_spearman"),
            "N/A" if average_spearman is None else f"{average_spearman:.3f}",
        )
        st.write(sensitivity["explanation"])

    with limitations_tab:
        st.subheader(t("validity.limitations"))
        st.markdown(t("validity.limitations_text"))

    with st.expander(t("validity.generated_report"), expanded=False):
        st.text(generate_validity_report(validity_results))


main()

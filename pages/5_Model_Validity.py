"""Model validity page."""

from __future__ import annotations

import streamlit as st

from src.reliability_validity import generate_validity_report, run_model_validity_pipeline


st.set_page_config(page_title="Model Validity", layout="wide")


def format_optional_float(value: float | None, digits: int = 3) -> str:
    if value is None:
        return "N/A"
    return f"{value:.{digits}f}"


def main() -> None:
    st.title("Model Validity")
    st.caption(
        "Review content validity, reliability, AHP consistency status, and weight-sensitivity robustness diagnostics."
    )

    try:
        validity_results = run_model_validity_pipeline()
    except Exception as exc:
        st.error(f"Model validity pipeline failed: {exc}")
        if st.checkbox("Debug mode"):
            st.exception(exc)
        return

    cronbach = validity_results["cronbach_alpha"]
    ahp = validity_results["ahp_consistency"]
    sensitivity = validity_results["sensitivity_analysis"]
    content_table = validity_results["content_validity_table"]

    st.info(
        "Demo / Simulated Data Notice: validity checks are model-governance diagnostics for a small portfolio prototype. "
        "They are not proof of official rating validity or investment suitability."
    )

    content_tab, reliability_tab, ahp_tab, sensitivity_tab, limitations_tab = st.tabs(
        ["Content Validity", "Reliability", "AHP Consistency", "Sensitivity Analysis", "Limitations"]
    )

    with content_tab:
        st.subheader("Content Validity")
        col1, col2, col3 = st.columns(3)
        col1.metric("Indicator count", len(content_table))
        col2.metric("Module count", content_table["module"].nunique())
        col3.metric("Required indicators", int(content_table["whether_it_is_required"].sum()))
        st.write(
            "Each indicator is mapped to a reference framework, reference note, validation method, "
            "and reliability method."
        )
        st.dataframe(content_table, use_container_width=True, hide_index=True)

    with reliability_tab:
        st.subheader("Reliability")
        col1, col2, col3 = st.columns(3)
        col1.metric("Cronbach's Alpha", format_optional_float(cronbach["alpha"]))
        col2.metric("Status", cronbach["status"])
        col3.metric("Valid item count", cronbach.get("valid_item_count", "N/A"))
        st.write(cronbach["explanation"])
        st.warning(
            "Cronbach's Alpha is applied only to service-quality multi-item fields: tangibles, reliability, "
            "responsiveness, assurance, and empathy. It is not applied to financial ratios."
        )

    with ahp_tab:
        st.subheader("AHP Consistency")
        st.metric("AHP status", ahp["status"])
        st.write(ahp["explanation"])
        if ahp["status"] == "not_run":
            st.info("No AHP pass/fail conclusion is shown because no pairwise matrix exists.")
        else:
            st.json(ahp)

    with sensitivity_tab:
        st.subheader("Sensitivity Analysis")
        col1, col2 = st.columns(2)
        ranking_stability = sensitivity.get("ranking_stability_ratio")
        average_spearman = sensitivity.get("average_spearman_correlation")
        col1.metric(
            "Ranking stability ratio",
            "N/A" if ranking_stability is None else f"{ranking_stability:.1%}",
        )
        col2.metric(
            "Average Spearman correlation",
            "N/A" if average_spearman is None else f"{average_spearman:.3f}",
        )
        st.write(sensitivity["explanation"])

    with limitations_tab:
        st.subheader("Limitations")
        st.markdown(
            """
            - Demo data includes simulated or mixed values.
            - The sample size is small, so statistical inference is limited.
            - AHP consistency is only available if an expert pairwise matrix is provided.
            - Sensitivity analysis perturbs weights; it is not scenario simulation.
            - Outputs are not official ratings, regulatory conclusions, valuation opinions, or investment recommendations.
            """
        )

    with st.expander("Generated validity report", expanded=False):
        st.text(generate_validity_report(validity_results))


main()

"""Data Quality page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.chart_utils import (
    make_data_confidence_bar_chart,
    make_data_quality_dimension_chart,
    make_data_type_distribution_chart,
    make_missingness_chart,
)
from src.data_loader import get_asset_options
from src.data_quality import (
    calculate_all_data_confidence_scores,
    calculate_data_confidence_score,
    generate_data_quality_report,
    get_data_type_distribution,
    get_missingness_summary,
    load_quality_data,
)
from src.i18n import language_selector, localize_dataframe, t, translate_column_name


st.set_page_config(page_title="Data Quality", layout="wide")


CONFIDENCE_LEVEL_KEYS = {
    "High Data Confidence": "data_quality.levels.high_data_confidence",
    "Moderate-High Data Confidence": "data_quality.levels.moderate_high_data_confidence",
    "Moderate Data Confidence": "data_quality.levels.moderate_data_confidence",
    "Low Data Confidence": "data_quality.levels.low_data_confidence",
    "Very Low Data Confidence": "data_quality.levels.very_low_data_confidence",
}
WARNING_KEYS = {
    "Source reliability is limited by mixed or simulated data_type values.": "data_quality.warning_source_reliability",
    "Source notes should be strengthened with more specific source references.": "data_quality.warning_traceability",
    "Completeness can be improved by filling missing analytical fields.": "data_quality.warning_completeness",
}
TABLE_NAME_KEYS = {
    "assets": "data_quality.tables.assets",
    "financial_metrics": "data_quality.tables.financial_metrics",
    "operation_metrics": "data_quality.tables.operation_metrics",
    "service_quality_metrics": "data_quality.tables.service_quality_metrics",
    "risk_metrics": "data_quality.tables.risk_metrics",
    "digital_maturity_metrics": "data_quality.tables.digital_maturity_metrics",
    "data_dictionary": "data_quality.tables.data_dictionary",
    "overall": "data_quality.tables.overall",
}
DATA_TYPE_KEYS = {
    "actual": "data_quality.data_types.actual",
    "public_disclosure": "data_quality.data_types.public_disclosure",
    "public_collected": "data_quality.data_types.public_collected",
    "survey": "data_quality.data_types.survey",
    "manual_assessment": "data_quality.data_types.manual_assessment",
    "mixed": "data_quality.data_types.mixed",
    "simulated": "data_quality.data_types.simulated",
    "unknown": "data_quality.data_types.unknown",
}


def translate_confidence_level(level: str) -> str:
    return t(CONFIDENCE_LEVEL_KEYS.get(str(level), ""), str(level))


def translate_table_name(table_name: str) -> str:
    return t(TABLE_NAME_KEYS.get(str(table_name), ""), str(table_name))


def translate_data_type(data_type: str) -> str:
    return t(DATA_TYPE_KEYS.get(str(data_type), ""), str(data_type))


def translate_warning(warning: str) -> str:
    return t(WARNING_KEYS.get(str(warning), ""), str(warning))


def localized_dimension_explanations() -> list[str]:
    return [
        t("data_quality.explanations.completeness"),
        t("data_quality.explanations.source_reliability"),
        t("data_quality.explanations.traceability"),
        t("data_quality.explanations.timeliness"),
        t("data_quality.explanations.coverage"),
    ]


def localize_quality_table(df: pd.DataFrame) -> pd.DataFrame:
    display_df = localize_dataframe(df)
    level_column = translate_column_name("data_confidence_level")
    if level_column in display_df.columns:
        display_df[level_column] = display_df[level_column].map(translate_confidence_level)
    return display_df


def localize_data_quality_values(df: pd.DataFrame) -> pd.DataFrame:
    display_df = localize_dataframe(df)
    table_column = translate_column_name("table")
    data_type_column = translate_column_name("data_type")

    if table_column in display_df.columns:
        display_df[table_column] = display_df[table_column].map(translate_table_name)
    if data_type_column in display_df.columns:
        display_df[data_type_column] = display_df[data_type_column].map(translate_data_type)
    return display_df


def report_file_name(asset_id: str) -> str:
    return f"tourism_reit_data_quality_{asset_id}.md"


def main() -> None:
    language = language_selector()
    st.title(t("data_quality.title"))
    st.caption(t("data_quality.subtitle"))
    st.info(t("data_quality.intro"))
    st.warning(t("data_quality.disclaimer"))

    try:
        asset_options = get_asset_options()
        dataframes = load_quality_data()
        all_scores_df = calculate_all_data_confidence_scores()
        data_type_df = get_data_type_distribution()
        missingness_df = get_missingness_summary()
    except Exception as exc:
        st.error(t("data_quality.load_error", error=exc))
        if st.checkbox(t("common.debug_mode")):
            st.exception(exc)
        return

    st.sidebar.header(t("common.controls"))
    selected_label = st.sidebar.selectbox(t("common.select_asset"), list(asset_options.keys()))
    asset_id = asset_options[selected_label]
    table_options = ["__all__"] + sorted(missingness_df["table"].dropna().unique().tolist())
    selected_table = st.sidebar.selectbox(
        t("data_quality.table_filter"),
        table_options,
        format_func=lambda value: t("common.all") if value == "__all__" else translate_table_name(value),
    )

    try:
        selected_quality = calculate_data_confidence_score(asset_id, dataframes)
    except Exception as exc:
        st.error(t("data_quality.calculation_error", error=exc))
        if st.checkbox(t("common.debug_mode")):
            st.exception(exc)
        return

    st.subheader(t("data_quality.overview"))
    kpi_cols = st.columns(6)
    kpi_cols[0].metric(t("data_quality.data_confidence_score"), f"{selected_quality['data_confidence_score']:.1f}")
    kpi_cols[1].metric(
        t("data_quality.data_confidence_level"),
        translate_confidence_level(selected_quality["data_confidence_level"]),
    )
    kpi_cols[2].metric(t("data_quality.completeness"), f"{selected_quality['completeness_score']:.1f}")
    kpi_cols[3].metric(t("data_quality.source_reliability"), f"{selected_quality['source_reliability_score']:.1f}")
    kpi_cols[4].metric(t("data_quality.traceability"), f"{selected_quality['traceability_score']:.1f}")
    kpi_cols[5].metric(t("data_quality.coverage"), f"{selected_quality['coverage_score']:.1f}")
    st.metric(t("data_quality.timeliness"), f"{selected_quality['timeliness_score']:.1f}")

    st.subheader(t("data_quality.breakdown"))
    chart_col, explanation_col = st.columns([0.58, 0.42])
    with chart_col:
        st.plotly_chart(make_data_quality_dimension_chart(selected_quality), use_container_width=True)
    with explanation_col:
        st.markdown(f"**{t('data_quality.dimension_explanations')}**")
        for explanation in localized_dimension_explanations():
            st.write(f"- {explanation}")
        if selected_quality["warnings"]:
            st.warning(" ".join(translate_warning(warning) for warning in selected_quality["warnings"]))

    st.subheader(t("data_quality.confidence_ranking"))
    ranking_table = localize_quality_table(all_scores_df)
    st.dataframe(
        ranking_table.style.format(
            {
                translate_column_name("completeness_score"): "{:.1f}",
                translate_column_name("source_reliability_score"): "{:.1f}",
                translate_column_name("traceability_score"): "{:.1f}",
                translate_column_name("timeliness_score"): "{:.1f}",
                translate_column_name("coverage_score"): "{:.1f}",
                translate_column_name("data_confidence_score"): "{:.1f}",
            },
            na_rep=t("common.data_unavailable"),
        ),
        use_container_width=True,
        hide_index=True,
    )
    st.plotly_chart(make_data_confidence_bar_chart(all_scores_df), use_container_width=True)

    st.subheader(t("data_quality.data_type_distribution"))
    dist_col, dist_table_col = st.columns([0.48, 0.52])
    with dist_col:
        st.plotly_chart(make_data_type_distribution_chart(data_type_df), use_container_width=True)
    with dist_table_col:
        st.dataframe(localize_data_quality_values(data_type_df), use_container_width=True, hide_index=True)

    st.subheader(t("data_quality.missingness_summary"))
    if selected_table != "__all__":
        visible_missingness = missingness_df[missingness_df["table"] == selected_table].copy()
    else:
        visible_missingness = missingness_df.copy()
    miss_col, miss_table_col = st.columns([0.42, 0.58])
    with miss_col:
        st.plotly_chart(make_missingness_chart(visible_missingness), use_container_width=True)
    with miss_table_col:
        display_missingness = localize_data_quality_values(visible_missingness)
        st.dataframe(
            display_missingness.style.format(
                {translate_column_name("missing_percentage"): "{:.1f}%"},
                na_rep=t("common.data_unavailable"),
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.subheader(t("data_quality.report"))
    report_text = generate_data_quality_report(asset_id, language=language)
    st.markdown(report_text)
    st.download_button(
        t("data_quality.download_report"),
        data=report_text,
        file_name=report_file_name(asset_id),
        mime="text/markdown",
        use_container_width=True,
    )

    with st.expander(t("data_quality.improvement_suggestions"), expanded=True):
        st.markdown(t("data_quality.improvement_suggestions_text"))


main()

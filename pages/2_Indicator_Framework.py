"""Indicator framework page."""

from __future__ import annotations

import pandas as pd
import streamlit as st
import yaml

from src.data_loader import get_project_root
from src.i18n import language_selector, localize_dataframe, t


st.set_page_config(page_title="Indicator Framework", layout="wide")


def main() -> None:
    language_selector()
    st.title(t("indicator.title"))
    st.caption(t("indicator.subtitle"))

    config_path = get_project_root() / "config" / "indicator_framework.yml"
    try:
        with config_path.open("r", encoding="utf-8") as file:
            indicator_config = yaml.safe_load(file)
    except Exception as exc:
        st.error(t("indicator.load_error", error=exc))
        if st.checkbox(t("common.debug_mode")):
            st.exception(exc)
        return

    indicators_df = pd.DataFrame(indicator_config.get("indicators", []))
    if indicators_df.empty:
        st.info(t("indicator.empty"))
        return

    st.info(t("indicator.content_validity_notice"))

    count_by_module = (
        indicators_df.groupby("module", as_index=False)["indicator_id"]
        .count()
        .rename(columns={"indicator_id": "indicator_count"})
    )
    kpi_cols = st.columns(3)
    kpi_cols[0].metric(t("labels.indicator_count"), len(indicators_df))
    kpi_cols[1].metric(t("labels.module_count"), indicators_df["module"].nunique())
    kpi_cols[2].metric(t("labels.required_indicators"), int(indicators_df["whether_it_is_required"].sum()))

    st.subheader(t("indicator.count_by_module"))
    st.bar_chart(count_by_module.set_index("module"))

    filter_cols = st.columns(3)
    all_label = t("common.all")
    modules = [all_label] + sorted(indicators_df["module"].dropna().unique().tolist())
    data_source_types = [all_label] + sorted(indicators_df["data_source_type"].dropna().unique().tolist())
    reference_options = [all_label] + sorted(
        {
            reference.strip()
            for value in indicators_df["reference_framework"].dropna()
            for reference in str(value).split(";")
            if reference.strip()
        }
    )

    selected_module = filter_cols[0].selectbox(t("indicator.module"), modules)
    selected_source_type = filter_cols[1].selectbox(t("indicator.data_source_type"), data_source_types)
    selected_reference = filter_cols[2].selectbox(t("indicator.reference_framework"), reference_options)

    filtered_df = indicators_df.copy()
    if selected_module != all_label:
        filtered_df = filtered_df[filtered_df["module"] == selected_module]
    if selected_source_type != all_label:
        filtered_df = filtered_df[filtered_df["data_source_type"] == selected_source_type]
    if selected_reference != all_label:
        filtered_df = filtered_df[
            filtered_df["reference_framework"].astype(str).str.contains(selected_reference, regex=False)
        ]

    display_columns = [
        "indicator_id",
        "indicator_name",
        "module",
        "direction",
        "data_source_type",
        "reference_framework",
        "reference_note",
        "validation_method",
        "reliability_method",
        "whether_it_is_required",
    ]
    st.subheader(t("indicator.framework_table"))
    st.dataframe(
        localize_dataframe(filtered_df[display_columns]),
        use_container_width=True,
        hide_index=True,
    )

    with st.expander(t("indicator.reference_details"), expanded=False):
        st.dataframe(
            localize_dataframe(filtered_df[["indicator_id", "indicator_name", "reference_framework", "reference_note"]]),
            use_container_width=True,
            hide_index=True,
        )


main()

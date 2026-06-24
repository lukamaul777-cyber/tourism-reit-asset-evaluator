"""Indicator framework page."""

from __future__ import annotations

import pandas as pd
import streamlit as st
import yaml

from src.data_loader import get_project_root


st.set_page_config(page_title="Indicator Framework", layout="wide")


def main() -> None:
    st.title("Indicator Framework")
    st.caption(
        "Explore the reference-based indicator system. This page supports content validity by showing "
        "how each indicator maps to sources, validation methods, and reliability methods."
    )

    config_path = get_project_root() / "config" / "indicator_framework.yml"
    try:
        with config_path.open("r", encoding="utf-8") as file:
            indicator_config = yaml.safe_load(file)
    except Exception as exc:
        st.error(f"Unable to load indicator framework: {exc}")
        if st.checkbox("Debug mode"):
            st.exception(exc)
        return

    indicators_df = pd.DataFrame(indicator_config.get("indicators", []))
    if indicators_df.empty:
        st.info("Indicator framework is empty.")
        return

    st.info(
        "Content validity check: each indicator should have a clear module, data source type, "
        "reference framework, reference note, validation method, and reliability method."
    )

    count_by_module = (
        indicators_df.groupby("module", as_index=False)["indicator_id"]
        .count()
        .rename(columns={"indicator_id": "indicator_count"})
    )
    kpi_cols = st.columns(3)
    kpi_cols[0].metric("Indicator count", len(indicators_df))
    kpi_cols[1].metric("Module count", indicators_df["module"].nunique())
    kpi_cols[2].metric("Required indicators", int(indicators_df["whether_it_is_required"].sum()))

    st.subheader("Indicator Count by Module")
    st.bar_chart(count_by_module.set_index("module"))

    filter_cols = st.columns(3)
    modules = ["All"] + sorted(indicators_df["module"].dropna().unique().tolist())
    data_source_types = ["All"] + sorted(indicators_df["data_source_type"].dropna().unique().tolist())
    reference_options = ["All"] + sorted(
        {
            reference.strip()
            for value in indicators_df["reference_framework"].dropna()
            for reference in str(value).split(";")
            if reference.strip()
        }
    )

    selected_module = filter_cols[0].selectbox("Module", modules)
    selected_source_type = filter_cols[1].selectbox("Data source type", data_source_types)
    selected_reference = filter_cols[2].selectbox("Reference framework", reference_options)

    filtered_df = indicators_df.copy()
    if selected_module != "All":
        filtered_df = filtered_df[filtered_df["module"] == selected_module]
    if selected_source_type != "All":
        filtered_df = filtered_df[filtered_df["data_source_type"] == selected_source_type]
    if selected_reference != "All":
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
    st.subheader("Framework Table")
    st.dataframe(
        filtered_df[display_columns],
        use_container_width=True,
        hide_index=True,
        column_config={
            "indicator_id": st.column_config.TextColumn("ID", width="small"),
            "indicator_name": st.column_config.TextColumn("Indicator", width="medium"),
            "module": st.column_config.TextColumn("Module", width="medium"),
            "reference_note": st.column_config.TextColumn("Reference note", width="large"),
            "validation_method": st.column_config.TextColumn("Validation method", width="large"),
            "reliability_method": st.column_config.TextColumn("Reliability method", width="large"),
        },
    )

    with st.expander("Reference framework and note details", expanded=False):
        st.dataframe(
            filtered_df[["indicator_id", "indicator_name", "reference_framework", "reference_note"]],
            use_container_width=True,
            hide_index=True,
        )


main()

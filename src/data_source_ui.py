"""Streamlit UI helpers for selecting financial data source."""

from __future__ import annotations

import streamlit as st

from src.data_loader import (
    get_effective_financial_data_source,
    get_financial_data_source_label,
    get_financial_data_source_options,
)
from src.i18n import current_language, t


def render_financial_data_source_selector() -> tuple[str, str, bool]:
    """Render sidebar financial data-source selector and return selected/effective source metadata."""
    language = current_language()
    options = get_financial_data_source_options()
    current = st.session_state.get("financial_data_source", "demo")
    index = options.index(current) if current in options else 0
    selected = st.sidebar.selectbox(
        t("data_source.financial_data_source"),
        options,
        index=index,
        format_func=lambda value: get_financial_data_source_label(value, language),
        key="financial_data_source",
    )
    effective_source, did_fallback, warning_key = get_effective_financial_data_source(selected)
    if did_fallback and warning_key:
        st.sidebar.warning(t(warning_key))
        st.warning(t(warning_key))
    st.sidebar.caption(
        f"{t('data_source.current_financial_data_source')}: "
        f"{get_financial_data_source_label(effective_source, language)}"
    )
    return selected, effective_source, did_fallback

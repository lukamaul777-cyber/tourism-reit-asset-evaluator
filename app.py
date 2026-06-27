"""Streamlit entry point for the Tourism REIT Asset Evaluator landing page."""

from __future__ import annotations

import streamlit as st

from src.data_loader import get_asset_options, get_financial_data_source_options
from src.data_source_ui import render_financial_data_source_selector
from src.i18n import language_selector
from src.landing_page import render_landing_page


st.set_page_config(
    page_title="Tourism REIT Asset Evaluator",
    layout="wide",
)


def _safe_asset_count() -> int:
    try:
        return len(get_asset_options())
    except Exception:
        return 3


def _safe_source_count() -> int:
    try:
        return len(get_financial_data_source_options())
    except Exception:
        return 2


def main() -> None:
    language = language_selector()
    st.sidebar.header("Controls" if language == "en" else "控制")
    render_financial_data_source_selector()
    st.sidebar.caption(
        "Use the multipage navigation to open scoring, risk, scenario, report, and data-quality modules."
        if language == "en"
        else "可通过多页面导航进入评分、风险、情景、报告和数据质量模块。"
    )

    render_landing_page(
        language=language,
        asset_count=_safe_asset_count(),
        source_count=_safe_source_count(),
    )


if __name__ == "__main__":
    main()

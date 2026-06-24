"""Small Streamlit i18n helper for English/Simplified Chinese UI text."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRANSLATION_PATH = PROJECT_ROOT / "config" / "translations.yml"
DEFAULT_LANGUAGE = "en"
LANGUAGE_LABELS = {
    "en": "English",
    "zh": "\u4e2d\u6587",
}

STATUS_KEYS = {
    "Pass": "statuses.pass",
    "Pass with Warning": "statuses.pass_with_warning",
    "Warning": "statuses.warning",
    "Fail": "statuses.fail",
    "Unavailable": "statuses.unavailable",
}
RATING_KEYS = {
    "Highly Suitable": "ratings.highly_suitable",
    "Suitable with Monitoring": "ratings.suitable_with_monitoring",
    "Conditional Suitability": "ratings.conditional_suitability",
    "Weak Suitability": "ratings.weak_suitability",
    "Not Suitable": "ratings.not_suitable",
}
MODULE_KEYS = {
    "A. REITs Cash Flow and Distribution Capacity": "modules.module_a",
    "B. Tourism Operating Quality": "modules.module_b",
    "C. Service Quality and Online Reputation": "modules.module_c",
    "D. Risk Management and Resilience": "modules.module_d",
    "E. Data Maturity and Smart Operation": "modules.module_e",
}
SHORT_MODULE_KEYS = {
    "A. REITs Cash Flow and Distribution Capacity": "modules.short_cash_flow",
    "B. Tourism Operating Quality": "modules.short_tourism_ops",
    "C. Service Quality and Online Reputation": "modules.short_service_quality",
    "D. Risk Management and Resilience": "modules.short_risk_resilience",
    "E. Data Maturity and Smart Operation": "modules.short_data_maturity",
}
PAGE_KEYS = {
    "Home": "page_names.home",
    "Asset Profile": "page_names.asset_profile",
    "Indicator Framework": "page_names.indicator_framework",
    "REIT Fit Score": "page_names.reit_fit_score",
    "Risk Warning": "page_names.risk_warning",
    "Model Validity": "page_names.model_validity",
    "Scenario Simulator": "page_names.scenario_simulator",
    "Report Generator": "page_names.report_generator",
}


@st.cache_data(show_spinner=False)
def load_translations() -> dict[str, Any]:
    """Load translation strings from YAML."""
    with TRANSLATION_PATH.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def current_language() -> str:
    """Return the active language code."""
    init_language_state()
    return str(st.session_state.get("language", DEFAULT_LANGUAGE))


def get_language_label(language_code: str | None = None) -> str:
    """Return the display label for a language code."""
    code = language_code or st.session_state.get("language", DEFAULT_LANGUAGE)
    return LANGUAGE_LABELS.get(code, LANGUAGE_LABELS[DEFAULT_LANGUAGE])


def init_language_state() -> None:
    """Initialize Streamlit session language state."""
    if "language" not in st.session_state:
        st.session_state["language"] = DEFAULT_LANGUAGE


def _lookup(translations: dict[str, Any], language: str, key: str) -> Any:
    """Look up a dotted translation key."""
    current: Any = translations.get(language, {})
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def t(key: str, default: str | None = None, **kwargs: Any) -> str:
    """Translate a dotted key with selected-language, English, default, and key fallback."""
    init_language_state()
    translations = load_translations()
    language = st.session_state.get("language", DEFAULT_LANGUAGE)

    value = _lookup(translations, language, key)
    if value is None:
        value = _lookup(translations, DEFAULT_LANGUAGE, key)
    if value is None:
        value = default if default is not None else key

    text = str(value)
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text


def language_selector() -> str:
    """Render the sidebar language selector and return the selected code."""
    init_language_state()
    translations = load_translations()
    label = _lookup(translations, st.session_state["language"], "common.language")
    label = str(label or "Language / \u8bed\u8a00")
    codes = list(LANGUAGE_LABELS)
    current_code = st.session_state.get("language", DEFAULT_LANGUAGE)
    current_index = codes.index(current_code) if current_code in codes else 0
    selected_label = st.sidebar.selectbox(
        label,
        [LANGUAGE_LABELS[code] for code in codes],
        index=current_index,
        key="language_selector",
    )
    selected_code = next(code for code, option_label in LANGUAGE_LABELS.items() if option_label == selected_label)
    st.session_state["language"] = selected_code
    return selected_code


def translate_status(status: str | None) -> str:
    """Translate a display status while leaving unknown values unchanged."""
    if status is None:
        return t("common.unavailable")
    return t(STATUS_KEYS.get(str(status), ""), str(status))


def translate_rating(rating: str | None) -> str:
    """Translate a display rating while leaving unknown values unchanged."""
    if rating is None:
        return t("common.unavailable")
    return t(RATING_KEYS.get(str(rating), ""), str(rating))


def translate_module_name(module_name: str | None, short: bool = False) -> str:
    """Translate a module name for display only."""
    if module_name is None:
        return t("common.unavailable")
    key_map = SHORT_MODULE_KEYS if short else MODULE_KEYS
    return t(key_map.get(str(module_name), ""), str(module_name))


def translate_page_name(page_name: str | None) -> str:
    """Translate a page name for display only."""
    if page_name is None:
        return t("common.unavailable")
    return t(PAGE_KEYS.get(str(page_name), ""), str(page_name))


def translate_column_name(column_name: str | None) -> str:
    """Translate a dataframe column name for display only."""
    if column_name is None:
        return t("common.unavailable")
    return t(f"columns.{column_name}", str(column_name))


def translate_risk_label(column_name: str | None) -> str:
    """Translate risk metric labels for display only."""
    if column_name is None:
        return t("common.unavailable")
    return t(f"risk_labels.{column_name}", str(column_name))


def localize_dataframe(df: Any) -> Any:
    """Return a display-only dataframe with translated common values and columns."""
    try:
        display_df = df.copy()
    except Exception:
        return df

    if "status" in display_df.columns:
        display_df["status"] = display_df["status"].map(translate_status)
    if "rating_level" in display_df.columns:
        display_df["rating_level"] = display_df["rating_level"].map(translate_rating)
    if "module" in display_df.columns:
        display_df["module"] = display_df["module"].map(translate_module_name)

    return display_df.rename(columns={column: translate_column_name(column) for column in display_df.columns})

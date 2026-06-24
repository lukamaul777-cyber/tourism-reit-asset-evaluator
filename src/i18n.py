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
    "zh": "中文",
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


@st.cache_data(show_spinner=False)
def load_translations() -> dict[str, Any]:
    """Load translation strings from YAML."""
    with TRANSLATION_PATH.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


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
    """Translate a dotted key with English/default/key fallback."""
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
    label = str(label or "Language / 语言")
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

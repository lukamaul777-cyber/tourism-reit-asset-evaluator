"""Validate English/Simplified Chinese translation coverage."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRANSLATION_PATH = PROJECT_ROOT / "config" / "translations.yml"
REQUIRED_LANGUAGES = ("en", "zh")
CRITICAL_KEYS = {
    "app.title",
    "app.subtitle",
    "common.language",
    "common.select_asset",
    "common.weighting_mode",
    "common.disclaimer",
    "home.methodology_flow",
    "asset_profile.title",
    "indicator.title",
    "score.title",
    "risk.title",
    "validity.title",
    "scenario.title",
    "report.title",
}


def load_translation_config() -> dict[str, Any]:
    """Load translations.yml."""
    if not TRANSLATION_PATH.exists():
        raise FileNotFoundError(f"Missing translation file: {TRANSLATION_PATH}")
    with TRANSLATION_PATH.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def flatten_keys(value: Any, prefix: str = "") -> set[str]:
    """Return dotted leaf keys for nested dictionaries."""
    if not isinstance(value, dict):
        return {prefix.rstrip(".")}

    keys: set[str] = set()
    for child_key, child_value in value.items():
        child_prefix = f"{prefix}{child_key}."
        keys.update(flatten_keys(child_value, child_prefix))
    return keys


def validate_translations() -> list[str]:
    """Validate language existence, key coverage, and critical keys."""
    errors: list[str] = []
    config = load_translation_config()

    for language in REQUIRED_LANGUAGES:
        if language not in config:
            errors.append(f"Missing language section: {language}")

    if errors:
        return errors

    flattened = {language: flatten_keys(config[language]) for language in REQUIRED_LANGUAGES}
    en_keys = flattened["en"]
    zh_keys = flattened["zh"]

    missing_in_zh = sorted(en_keys - zh_keys)
    missing_in_en = sorted(zh_keys - en_keys)

    if missing_in_zh:
        errors.append("Keys missing in zh: " + ", ".join(missing_in_zh))
    if missing_in_en:
        errors.append("Keys missing in en: " + ", ".join(missing_in_en))

    for language in REQUIRED_LANGUAGES:
        missing_critical = sorted(CRITICAL_KEYS - flattened[language])
        if missing_critical:
            errors.append(f"Critical keys missing in {language}: " + ", ".join(missing_critical))

    return errors


def main() -> int:
    """CLI entry point."""
    try:
        errors = validate_translations()
    except Exception as exc:
        print(f"Translation validation failed: {exc}")
        return 1

    if errors:
        print("Translation validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    config = load_translation_config()
    print("Translation validation passed.")
    print(f"Checked languages: {', '.join(REQUIRED_LANGUAGES)}")
    print(f"English keys: {len(flatten_keys(config['en']))}")
    print(f"Chinese keys: {len(flatten_keys(config['zh']))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

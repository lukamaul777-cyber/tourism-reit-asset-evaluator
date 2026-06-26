"""Validate field source classification configuration."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIELD_SOURCE_MAP_PATH = PROJECT_ROOT / "config" / "field_source_map.yml"
DATASET_NAME = "financial_metrics"
REQUIRED_CATEGORIES = {"verified_public", "model_derived", "estimated_demo_proxy"}
REQUIRED_VERIFIED_FIELDS = {
    "revenue",
    "operating_cash_flow",
    "total_assets",
    "total_debt",
    "debt_ratio",
}
REQUIRED_DERIVED_FIELDS = {
    "derived_ocf_margin",
    "derived_debt_ratio",
    "derived_revenue_stability",
    "derived_ocf_stability",
}
REQUIRED_ESTIMATED_FIELDS = {
    "estimated_affo",
    "estimated_distribution",
    "maintenance_capex",
}


def load_config() -> dict[str, Any]:
    if not FIELD_SOURCE_MAP_PATH.exists():
        raise FileNotFoundError(f"Missing field source map: {FIELD_SOURCE_MAP_PATH}")
    with FIELD_SOURCE_MAP_PATH.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def _fields_for(config: dict[str, Any], category: str) -> set[str]:
    return {str(field) for field in config[DATASET_NAME][category].get("fields", [])}


def validate_field_source_map() -> list[str]:
    errors: list[str] = []
    config = load_config()

    if DATASET_NAME not in config:
        return [f"Missing dataset section: {DATASET_NAME}"]

    dataset_config = config[DATASET_NAME] or {}
    missing_categories = REQUIRED_CATEGORIES - set(dataset_config)
    if missing_categories:
        errors.append("Missing categories: " + ", ".join(sorted(missing_categories)))
        return errors

    all_fields: list[str] = []
    for category in sorted(REQUIRED_CATEGORIES):
        category_config = dataset_config.get(category, {}) or {}
        fields = category_config.get("fields", [])
        if not fields:
            errors.append(f"{category} has no fields.")
        all_fields.extend(str(field) for field in fields)
        for key in ("label_en", "label_zh", "note_en", "note_zh"):
            if not category_config.get(key):
                errors.append(f"{category} missing {key}.")

    duplicates = sorted(field for field, count in Counter(all_fields).items() if count > 1)
    if duplicates:
        errors.append("Duplicate field classifications: " + ", ".join(duplicates))

    verified_fields = _fields_for(config, "verified_public")
    derived_fields = _fields_for(config, "model_derived")
    estimated_fields = _fields_for(config, "estimated_demo_proxy")

    missing_verified = REQUIRED_VERIFIED_FIELDS - verified_fields
    if missing_verified:
        errors.append("Verified public fields missing: " + ", ".join(sorted(missing_verified)))

    missing_derived = REQUIRED_DERIVED_FIELDS - derived_fields
    if missing_derived:
        errors.append("Model-derived fields missing: " + ", ".join(sorted(missing_derived)))

    missing_estimated = REQUIRED_ESTIMATED_FIELDS - estimated_fields
    if missing_estimated:
        errors.append("Estimated/demo/proxy fields missing: " + ", ".join(sorted(missing_estimated)))

    return errors


def main() -> int:
    try:
        errors = validate_field_source_map()
    except Exception as exc:
        print(f"Field source map validation failed: {exc}")
        return 1

    if errors:
        print("Field source map validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    config = load_config()
    print("Field source map validation passed.")
    for category in sorted(REQUIRED_CATEGORIES):
        fields = _fields_for(config, category)
        print(f"{category}: {len(fields)} fields")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Validate the Tourism REIT Asset Evaluator model configuration files."""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "config"

CONFIG_FILES = {
    "indicator_framework": CONFIG_DIR / "indicator_framework.yml",
    "scoring_weights": CONFIG_DIR / "scoring_weights.yml",
    "model_references": CONFIG_DIR / "model_references.yml",
}

REQUIRED_INDICATOR_FIELDS = {
    "indicator_id",
    "indicator_name",
    "module",
    "definition",
    "formula",
    "direction",
    "data_source_type",
    "reference_framework",
    "reference_note",
    "validation_method",
    "reliability_method",
    "whether_it_is_required",
}

WEIGHTING_MODES_TO_CHECK = ("default_expert_weight", "equal_weight")


def load_yaml_file(path: Path) -> Any:
    """Load a YAML file and raise a useful error if it is missing or invalid."""
    if not path.exists():
        raise FileNotFoundError(f"Missing config file: {path}")

    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def split_reference_frameworks(reference_framework: Any) -> list[str]:
    """Split semicolon-delimited reference framework names from indicators."""
    if isinstance(reference_framework, list):
        values = reference_framework
    else:
        values = str(reference_framework).split(";")

    return [str(value).strip() for value in values if str(value).strip()]


def assert_close_to_100(value: float, label: str, errors: list[str]) -> None:
    """Append an error unless a weight total is effectively 100."""
    if not math.isclose(value, 100.0, rel_tol=0.0, abs_tol=0.001):
        errors.append(f"{label} must sum to 100, found {value:.4f}.")


def validate_indicator_required_fields(
    indicators: list[dict[str, Any]],
    errors: list[str],
) -> None:
    """Validate that each indicator includes every required metadata field."""
    for index, indicator in enumerate(indicators, start=1):
        indicator_id = indicator.get("indicator_id", f"indicator_at_index_{index}")
        missing_fields = REQUIRED_INDICATOR_FIELDS - set(indicator)

        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            errors.append(f"{indicator_id} is missing required fields: {missing}.")


def validate_unique_indicator_ids(
    indicators: list[dict[str, Any]],
    errors: list[str],
) -> None:
    """Validate uniqueness of indicator_id values."""
    seen: set[str] = set()
    duplicates: set[str] = set()

    for indicator in indicators:
        indicator_id = str(indicator.get("indicator_id", "")).strip()
        if indicator_id in seen:
            duplicates.add(indicator_id)
        seen.add(indicator_id)

    if duplicates:
        errors.append("Duplicate indicator_id values: " + ", ".join(sorted(duplicates)) + ".")


def validate_modules_exist_in_weights(
    indicators: list[dict[str, Any]],
    scoring_weights: dict[str, Any],
    errors: list[str],
) -> None:
    """Validate that every indicator module exists in the weighting config."""
    weighting_modes = scoring_weights.get("weighting_modes", {})
    default_mode = weighting_modes.get("default_expert_weight", {})
    configured_modules = set(default_mode.get("modules", {}))
    indicator_modules = {str(indicator.get("module", "")).strip() for indicator in indicators}
    missing_modules = indicator_modules - configured_modules

    if missing_modules:
        errors.append(
            "Modules used by indicators but missing from scoring_weights.yml: "
            + ", ".join(sorted(missing_modules))
            + "."
        )


def validate_references_exist(
    indicators: list[dict[str, Any]],
    model_references: dict[str, Any],
    errors: list[str],
) -> None:
    """Validate indicator reference frameworks against the reference library."""
    reference_names = {
        str(reference.get("name", "")).strip()
        for reference in model_references.get("references", [])
        if reference.get("name")
    }
    used_references: set[str] = set()

    for indicator in indicators:
        used_references.update(split_reference_frameworks(indicator.get("reference_framework")))

    missing_references = used_references - reference_names
    if missing_references:
        errors.append(
            "Reference frameworks used by indicators but missing from model_references.yml: "
            + ", ".join(sorted(missing_references))
            + "."
        )


def validate_weight_sums(scoring_weights: dict[str, Any], errors: list[str]) -> None:
    """Validate selected weighting modes sum to 100 at module and indicator level."""
    weighting_modes = scoring_weights.get("weighting_modes", {})

    for mode_name in WEIGHTING_MODES_TO_CHECK:
        mode = weighting_modes.get(mode_name)
        if not mode:
            errors.append(f"Missing weighting mode: {mode_name}.")
            continue

        modules = mode.get("modules", {})
        module_total = sum(float(module.get("weight", 0.0)) for module in modules.values())
        assert_close_to_100(module_total, f"{mode_name} module weights", errors)

        indicator_total = 0.0
        for module_name, module in modules.items():
            indicator_weights = module.get("indicators", {})
            module_indicator_total = sum(float(weight) for weight in indicator_weights.values())
            module_weight = float(module.get("weight", 0.0))
            indicator_total += module_indicator_total

            if not math.isclose(module_indicator_total, module_weight, rel_tol=0.0, abs_tol=0.001):
                errors.append(
                    f"{mode_name} indicator weights for module '{module_name}' must sum "
                    f"to module weight {module_weight:.4f}, found {module_indicator_total:.4f}."
                )

        assert_close_to_100(indicator_total, f"{mode_name} total indicator weights", errors)


def validate_project_config() -> list[str]:
    """Run all project configuration validation checks."""
    errors: list[str] = []

    try:
        indicator_framework = load_yaml_file(CONFIG_FILES["indicator_framework"])
        scoring_weights = load_yaml_file(CONFIG_FILES["scoring_weights"])
        model_references = load_yaml_file(CONFIG_FILES["model_references"])
    except Exception as exc:
        return [f"YAML load failed: {exc}"]

    indicators = indicator_framework.get("indicators", [])
    if not isinstance(indicators, list) or not indicators:
        errors.append("indicator_framework.yml must contain a non-empty indicators list.")
        return errors

    validate_indicator_required_fields(indicators, errors)
    validate_unique_indicator_ids(indicators, errors)
    validate_modules_exist_in_weights(indicators, scoring_weights, errors)
    validate_references_exist(indicators, model_references, errors)
    validate_weight_sums(scoring_weights, errors)

    return errors


def main() -> int:
    """CLI entry point."""
    errors = validate_project_config()

    if errors:
        print("Configuration validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Configuration validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

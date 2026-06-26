"""Helpers for classifying field source labels used in UI and reports."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIELD_SOURCE_MAP_PATH = PROJECT_ROOT / "config" / "field_source_map.yml"


UNKNOWN_SOURCE = {
    "en": {
        "field_source_category": "unknown",
        "field_source_label": "Unknown source",
        "field_source_note": "No field source classification is available.",
    },
    "zh": {
        "field_source_category": "unknown",
        "field_source_label": "未知来源",
        "field_source_note": "暂无字段来源分类。",
    },
}


def _resolve_path(path: str | Path) -> Path:
    resolved = Path(path)
    if not resolved.is_absolute():
        resolved = PROJECT_ROOT / resolved
    return resolved


def load_field_source_map(path: str | Path = DEFAULT_FIELD_SOURCE_MAP_PATH) -> dict[str, Any]:
    """Load the field source classification map."""
    resolved = _resolve_path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"Missing field source map: {resolved}")
    with resolved.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def classify_field_source(
    field_name: str,
    dataset_name: str = "financial_metrics",
    language: str = "en",
    path: str | Path = DEFAULT_FIELD_SOURCE_MAP_PATH,
) -> dict[str, str]:
    """Return source classification metadata for one field name."""
    language_key = "zh" if language == "zh" else "en"
    config = load_field_source_map(path)
    dataset_config = config.get(dataset_name, {}) or {}
    normalized_field = str(field_name)

    for category, category_config in dataset_config.items():
        fields = {str(field) for field in category_config.get("fields", [])}
        if normalized_field in fields:
            return {
                "field_source_category": str(category),
                "field_source_label": str(
                    category_config.get(f"label_{language_key}")
                    or category_config.get("label_en")
                    or category
                ),
                "field_source_note": str(
                    category_config.get(f"note_{language_key}")
                    or category_config.get("note_en")
                    or ""
                ),
            }

    return UNKNOWN_SOURCE[language_key].copy()


def add_field_source_labels(
    df: pd.DataFrame,
    field_column: str = "field_name",
    dataset_name: str = "financial_metrics",
    language: str = "en",
    path: str | Path = DEFAULT_FIELD_SOURCE_MAP_PATH,
) -> pd.DataFrame:
    """Append field source category, label, and note columns to a dataframe."""
    labeled_df = df.copy()
    if field_column not in labeled_df.columns:
        raise ValueError(f"Field column not found: {field_column}")

    labels = labeled_df[field_column].map(
        lambda field_name: classify_field_source(
            field_name,
            dataset_name=dataset_name,
            language=language,
            path=path,
        )
    )
    label_df = pd.DataFrame(labels.tolist(), index=labeled_df.index)
    return pd.concat([labeled_df, label_df], axis=1)


def get_field_source_legend(
    dataset_name: str = "financial_metrics",
    language: str = "en",
    path: str | Path = DEFAULT_FIELD_SOURCE_MAP_PATH,
) -> pd.DataFrame:
    """Return one display row per configured field source category."""
    language_key = "zh" if language == "zh" else "en"
    config = load_field_source_map(path)
    dataset_config = config.get(dataset_name, {}) or {}
    rows: list[dict[str, Any]] = []

    for category, category_config in dataset_config.items():
        rows.append(
            {
                "field_source_category": category,
                "field_source_label": category_config.get(f"label_{language_key}")
                or category_config.get("label_en")
                or category,
                "field_source_note": category_config.get(f"note_{language_key}")
                or category_config.get("note_en")
                or "",
                "fields": ", ".join(str(field) for field in category_config.get("fields", [])),
            }
        )

    return pd.DataFrame(rows)

"""Reusable data-loading helpers for the Streamlit app layer."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, TypeVar

import pandas as pd
import yaml


F = TypeVar("F", bound=Callable)


def _cache_data(func: F) -> F:
    # The project data files are small. Avoid Streamlit runtime warnings when
    # these helpers are imported by backend CLI scripts.
    return func


def get_project_root() -> Path:
    """Return the project root using Windows-compatible pathlib paths."""
    return Path(__file__).resolve().parents[1]


def _resolve_data_dir(data_dir: str | Path = "data") -> Path:
    path = Path(data_dir)
    if not path.is_absolute():
        path = get_project_root() / path
    return path


def _resolve_project_path(path: str | Path) -> Path:
    resolved = Path(path)
    if not resolved.is_absolute():
        resolved = get_project_root() / resolved
    return resolved


@_cache_data
def load_csv(filename: str, data_dir: str | Path = "data") -> pd.DataFrame:
    """Load a CSV file from the data directory."""
    path = _resolve_data_dir(data_dir) / filename
    if not path.exists():
        raise FileNotFoundError(f"Required data file not found: {path}")
    return pd.read_csv(path)


@_cache_data
def load_data_source_config(config_path: str | Path = "config/data_source.yml") -> dict:
    """Load financial data-source configuration."""
    path = _resolve_project_path(config_path)
    if not path.exists():
        return {
            "default_financial_data": "demo",
            "financial_data_sources": {
                "demo": {
                    "label_en": "Demo Dataset",
                    "label_zh": "示例数据集",
                    "path": "data/financial_metrics.csv",
                }
            },
        }
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def _financial_sources(config_path: str | Path = "config/data_source.yml") -> dict:
    config = load_data_source_config(config_path)
    return config.get("financial_data_sources", {}) or {}


def get_financial_data_source_options(config_path: str | Path = "config/data_source.yml") -> list[str]:
    """Return configured financial data-source keys."""
    sources = _financial_sources(config_path)
    if not sources:
        return ["demo"]
    default_source = load_data_source_config(config_path).get("default_financial_data", "demo")
    ordered = [default_source] if default_source in sources else []
    ordered.extend(source for source in sources if source not in ordered)
    return ordered


def get_financial_data_source_label(
    source: str,
    language: str = "en",
    config_path: str | Path = "config/data_source.yml",
) -> str:
    """Return display label for a configured financial source."""
    source_config = _financial_sources(config_path).get(source, {})
    label_key = "label_zh" if language == "zh" else "label_en"
    return str(source_config.get(label_key) or source_config.get("label_en") or source)


def resolve_financial_data_path(
    selected_source: str = "demo",
    config_path: str | Path = "config/data_source.yml",
) -> tuple[Path, str, bool, str | None]:
    """Resolve financial metrics CSV path with verified-to-demo fallback.

    Returns
    -------
    tuple
        ``(path, effective_source, did_fallback, warning_key)``.
    """
    config = load_data_source_config(config_path)
    sources = config.get("financial_data_sources", {}) or {}
    default_source = config.get("default_financial_data", "demo")
    requested_source = selected_source if selected_source in sources else default_source
    requested_path = _resolve_project_path(sources.get(requested_source, {}).get("path", "data/financial_metrics.csv"))

    if requested_source != "demo" and not requested_path.exists():
        demo_path = _resolve_project_path(sources.get("demo", {}).get("path", "data/financial_metrics.csv"))
        return demo_path, "demo", True, "data_source.verified_missing_fallback"

    if not requested_path.exists():
        demo_path = _resolve_project_path("data/financial_metrics.csv")
        return demo_path, "demo", requested_source != "demo", "data_source.verified_missing_fallback"

    return requested_path, requested_source, False, None


@_cache_data
def load_financial_metrics(selected_source: str = "demo") -> pd.DataFrame:
    """Load financial metrics from demo or verified source, falling back to demo if needed."""
    path, _effective_source, _did_fallback, _warning_key = resolve_financial_data_path(selected_source)
    return pd.read_csv(path)


def get_effective_financial_data_source(selected_source: str = "demo") -> tuple[str, bool, str | None]:
    """Return effective source key plus fallback metadata."""
    _path, effective_source, did_fallback, warning_key = resolve_financial_data_path(selected_source)
    return effective_source, did_fallback, warning_key


@_cache_data
def load_all_data(
    data_dir: str | Path = "data",
    financial_data_source: str = "demo",
) -> dict[str, pd.DataFrame]:
    """Load all app-facing CSV data tables."""
    return {
        "assets": load_csv("assets.csv", data_dir),
        "financial_metrics": load_financial_metrics(financial_data_source),
        "operation_metrics": load_csv("operation_metrics.csv", data_dir),
        "service_quality_metrics": load_csv("service_quality_metrics.csv", data_dir),
        "risk_metrics": load_csv("risk_metrics.csv", data_dir),
        "digital_maturity_metrics": load_csv("digital_maturity_metrics.csv", data_dir),
        "data_dictionary": load_csv("data_dictionary.csv", data_dir),
    }


@_cache_data
def get_asset_options(data_dir: str | Path = "data") -> dict[str, str]:
    """Return display labels mapped to asset_id values."""
    assets_df = load_csv("assets.csv", data_dir)
    return {
        f"{row.asset_name} ({row.asset_id})": row.asset_id
        for row in assets_df.itertuples(index=False)
    }


def get_latest_year_data(
    df: pd.DataFrame,
    group_col: str = "asset_id",
    year_col: str = "year",
) -> pd.DataFrame:
    """Return latest available year rows for each group."""
    if df.empty or group_col not in df.columns or year_col not in df.columns:
        return df.copy()

    latest_df = df.copy()
    latest_df[year_col] = pd.to_numeric(latest_df[year_col], errors="coerce")
    latest_df = latest_df.dropna(subset=[group_col, year_col])
    latest_df = latest_df.sort_values([group_col, year_col])
    return latest_df.groupby(group_col, as_index=False).tail(1)


@_cache_data
def safe_read_markdown(path: str | Path) -> str:
    """Read a Markdown file and return a readable fallback if unavailable."""
    resolved = Path(path)
    if not resolved.is_absolute():
        resolved = get_project_root() / resolved
    try:
        return resolved.read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"Markdown file not found: {resolved}"

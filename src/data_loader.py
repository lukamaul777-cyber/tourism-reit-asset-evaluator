"""Reusable data-loading helpers for the Streamlit app layer."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, TypeVar

import pandas as pd

try:
    import streamlit as st
except ImportError:  # Keep non-UI scripts independent from Streamlit.
    st = None


F = TypeVar("F", bound=Callable)


def _cache_data(func: F) -> F:
    if st is None:
        return func
    return st.cache_data(show_spinner=False)(func)  # type: ignore[return-value]


def get_project_root() -> Path:
    """Return the project root using Windows-compatible pathlib paths."""
    return Path(__file__).resolve().parents[1]


def _resolve_data_dir(data_dir: str | Path = "data") -> Path:
    path = Path(data_dir)
    if not path.is_absolute():
        path = get_project_root() / path
    return path


@_cache_data
def load_csv(filename: str, data_dir: str | Path = "data") -> pd.DataFrame:
    """Load a CSV file from the data directory."""
    path = _resolve_data_dir(data_dir) / filename
    if not path.exists():
        raise FileNotFoundError(f"Required data file not found: {path}")
    return pd.read_csv(path)


@_cache_data
def load_all_data(data_dir: str | Path = "data") -> dict[str, pd.DataFrame]:
    """Load all app-facing CSV data tables."""
    return {
        "assets": load_csv("assets.csv", data_dir),
        "financial_metrics": load_csv("financial_metrics.csv", data_dir),
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

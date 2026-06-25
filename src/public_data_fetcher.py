"""Optional public financial data fetcher for listed-company source data.

The normal Streamlit app does not depend on AKShare. This module is used only by
the public-data update script and fails gracefully when AKShare is unavailable or
remote public endpoints change.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAPPING_PATH = PROJECT_ROOT / "data_sources" / "company_mapping.csv"
PUBLIC_RAW_COLUMNS = [
    "asset_id",
    "asset_name",
    "stock_code",
    "year",
    "revenue",
    "operating_cash_flow",
    "total_assets",
    "total_liabilities",
    "total_debt",
    "debt_ratio",
    "source_name",
    "source_url",
    "source_year",
    "verification_status",
    "notes",
]

FIELD_ALIASES = {
    "revenue": ["营业总收入", "营业收入", "total_operating_revenue", "operating_revenue", "revenue"],
    "operating_cash_flow": ["经营活动产生的现金流量净额", "经营现金流量净额", "net_operate_cash_flow", "operating_cash_flow"],
    "total_assets": ["资产总计", "总资产", "total_assets"],
    "total_liabilities": ["负债合计", "负债总计", "total_liabilities"],
}


def _resolve_path(path: str | Path) -> Path:
    resolved = Path(path)
    if not resolved.is_absolute():
        resolved = PROJECT_ROOT / resolved
    return resolved


def load_company_mapping(path: str | Path = MAPPING_PATH) -> pd.DataFrame:
    """Load target listed-company mapping."""
    resolved = _resolve_path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"Missing company mapping file: {resolved}")
    return pd.read_csv(resolved, dtype={"stock_code": str})


def _blank_row(
    stock_code: str,
    year: int,
    status: str,
    notes: str,
    source_name: str = "AKShare public interface",
) -> dict[str, Any]:
    return {
        "stock_code": str(stock_code),
        "year": year,
        "revenue": pd.NA,
        "operating_cash_flow": pd.NA,
        "total_assets": pd.NA,
        "total_liabilities": pd.NA,
        "total_debt": pd.NA,
        "debt_ratio": pd.NA,
        "source_name": source_name,
        "source_url": "https://akshare.akfamily.xyz/",
        "source_year": year,
        "verification_status": status,
        "notes": notes,
    }


def _safe_import_akshare() -> tuple[Any | None, str | None]:
    try:
        import akshare as ak  # type: ignore
    except ImportError:
        return None, "AKShare is not installed. Run: python -m pip install akshare"
    except Exception as exc:
        return None, f"AKShare import failed: {exc}"
    return ak, None


def _call_akshare_statement(ak: Any, stock_code: str, symbol: str) -> tuple[pd.DataFrame, str | None]:
    """Call a commonly used AKShare Sina financial-statement endpoint."""
    try:
        df = ak.stock_financial_report_sina(stock=str(stock_code), symbol=symbol)
    except Exception as exc:
        return pd.DataFrame(), f"{symbol} fetch failed: {exc}"
    if not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame(), f"{symbol} fetch returned no rows."
    return df, None


def _extract_year(value: Any) -> int | None:
    if pd.isna(value):
        return None
    text = str(value)
    for token in text.replace("/", "-").split("-"):
        if len(token) == 4 and token.isdigit():
            return int(token)
    if len(text) >= 4 and text[:4].isdigit():
        return int(text[:4])
    return None


def _normalise_statement(df: pd.DataFrame) -> pd.DataFrame:
    """Return a year-indexed dataframe from AKShare output when possible."""
    if df.empty:
        return pd.DataFrame()
    normalised = df.copy()
    date_column = None
    for candidate in ("报告日", "报表日期", "截止日期", "日期", "REPORT_DATE"):
        if candidate in normalised.columns:
            date_column = candidate
            break
    if date_column is None:
        date_column = normalised.columns[0]
    normalised["year"] = normalised[date_column].map(_extract_year)
    return normalised.dropna(subset=["year"]).copy()


def _find_field_value(df: pd.DataFrame, year: int, aliases: list[str]) -> float | None:
    if df.empty or "year" not in df.columns:
        return None
    year_rows = df[pd.to_numeric(df["year"], errors="coerce") == int(year)]
    if year_rows.empty:
        return None

    for alias in aliases:
        if alias in year_rows.columns:
            value = pd.to_numeric(year_rows.iloc[0][alias], errors="coerce")
            if pd.notna(value):
                return float(value)
    return None


def fetch_financial_indicators_with_akshare(
    stock_code: str,
    start_year: int = 2021,
    end_year: int = 2024,
) -> pd.DataFrame:
    """Fetch selected public financial fields through AKShare when available.

    Values are not guessed. Missing fields stay blank with notes describing the
    fetch or parsing issue.
    """
    years = list(range(int(start_year), int(end_year) + 1))
    ak, import_error = _safe_import_akshare()
    if ak is None:
        rows = [_blank_row(stock_code, year, "fetch_failed", import_error or "AKShare unavailable.") for year in years]
        return pd.DataFrame(rows, columns=[column for column in PUBLIC_RAW_COLUMNS if column not in {"asset_id", "asset_name"}])

    income_df, income_error = _call_akshare_statement(ak, stock_code, "利润表")
    cash_df, cash_error = _call_akshare_statement(ak, stock_code, "现金流量表")
    balance_df, balance_error = _call_akshare_statement(ak, stock_code, "资产负债表")

    income_df = _normalise_statement(income_df)
    cash_df = _normalise_statement(cash_df)
    balance_df = _normalise_statement(balance_df)
    fetch_notes = [note for note in [income_error, cash_error, balance_error] if note]

    rows: list[dict[str, Any]] = []
    for year in years:
        revenue = _find_field_value(income_df, year, FIELD_ALIASES["revenue"])
        operating_cash_flow = _find_field_value(cash_df, year, FIELD_ALIASES["operating_cash_flow"])
        total_assets = _find_field_value(balance_df, year, FIELD_ALIASES["total_assets"])
        total_liabilities = _find_field_value(balance_df, year, FIELD_ALIASES["total_liabilities"])

        total_debt = total_liabilities
        debt_ratio = None
        if total_assets not in (None, 0) and total_liabilities is not None:
            debt_ratio = total_liabilities / total_assets

        values = [revenue, operating_cash_flow, total_assets, total_liabilities, total_debt, debt_ratio]
        found_count = sum(value is not None and pd.notna(value) for value in values)
        if found_count == 0:
            status = "fetch_failed" if fetch_notes else "pending"
        elif found_count < len(values):
            status = "partially_verified"
        else:
            status = "verified"

        missing_fields = [
            field
            for field, value in [
                ("revenue", revenue),
                ("operating_cash_flow", operating_cash_flow),
                ("total_assets", total_assets),
                ("total_liabilities", total_liabilities),
                ("total_debt", total_debt),
                ("debt_ratio", debt_ratio),
            ]
            if value is None or pd.isna(value)
        ]
        notes = "; ".join(fetch_notes)
        if missing_fields:
            notes = (notes + "; " if notes else "") + "Missing fields: " + ", ".join(missing_fields)
        if not notes:
            notes = "Public financial statement fields parsed from AKShare."

        rows.append(
            {
                "stock_code": str(stock_code),
                "year": year,
                "revenue": revenue,
                "operating_cash_flow": operating_cash_flow,
                "total_assets": total_assets,
                "total_liabilities": total_liabilities,
                "total_debt": total_debt,
                "debt_ratio": debt_ratio,
                "source_name": "AKShare Sina financial statement interface",
                "source_url": "https://akshare.akfamily.xyz/",
                "source_year": year,
                "verification_status": status,
                "notes": notes,
            }
        )

    return pd.DataFrame(rows)


def fetch_all_target_financials(
    mapping_df: pd.DataFrame,
    start_year: int = 2021,
    end_year: int = 2024,
) -> pd.DataFrame:
    """Fetch public financial data for every mapped company."""
    rows: list[pd.DataFrame] = []
    for _, company in mapping_df.iterrows():
        stock_code = str(company["stock_code"]).zfill(6)
        fetched = fetch_financial_indicators_with_akshare(stock_code, start_year, end_year)
        fetched.insert(0, "asset_name", company.get("asset_name", ""))
        fetched.insert(0, "asset_id", company.get("asset_id", ""))
        rows.append(fetched)

    if not rows:
        return pd.DataFrame(columns=PUBLIC_RAW_COLUMNS)
    combined = pd.concat(rows, ignore_index=True)
    for column in PUBLIC_RAW_COLUMNS:
        if column not in combined.columns:
            combined[column] = pd.NA
    return combined[PUBLIC_RAW_COLUMNS]


def save_public_raw_data(
    df: pd.DataFrame,
    output_path: str | Path = "data_verified/financial_metrics_public_raw.csv",
) -> Path:
    """Save raw public financial data output."""
    resolved = _resolve_path(output_path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    output_df = df.copy()
    for column in PUBLIC_RAW_COLUMNS:
        if column not in output_df.columns:
            output_df[column] = pd.NA
    output_df[PUBLIC_RAW_COLUMNS].to_csv(resolved, index=False, encoding="utf-8-sig")
    return resolved

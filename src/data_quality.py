"""Data quality and data confidence assessment for the demo dataset."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

TARGET_FILES = {
    "assets": "assets.csv",
    "financial_metrics": "financial_metrics.csv",
    "operation_metrics": "operation_metrics.csv",
    "service_quality_metrics": "service_quality_metrics.csv",
    "risk_metrics": "risk_metrics.csv",
    "digital_maturity_metrics": "digital_maturity_metrics.csv",
    "data_dictionary": "data_dictionary.csv",
}

ASSET_MODULE_TABLES = {
    "asset profile": "assets",
    "financial metrics": "financial_metrics",
    "operation metrics": "operation_metrics",
    "service quality metrics": "service_quality_metrics",
    "risk metrics": "risk_metrics",
    "digital maturity metrics": "digital_maturity_metrics",
}

METADATA_COLUMNS = {
    "asset_id",
    "asset_name",
    "year",
    "data_type",
    "source_note",
    "description",
}

SOURCE_TYPE_SCORE_MAP = {
    "actual": 100,
    "public_disclosure": 95,
    "public_collected": 80,
    "survey": 75,
    "manual_assessment": 65,
    "mixed": 55,
    "simulated": 35,
    "unknown": 20,
}

DIMENSION_WEIGHTS = {
    "completeness_score": 0.30,
    "source_reliability_score": 0.25,
    "traceability_score": 0.20,
    "timeliness_score": 0.10,
    "coverage_score": 0.15,
}

DATA_CONFIDENCE_LEVEL_ZH = {
    "High Data Confidence": "高数据可信度",
    "Moderate-High Data Confidence": "较高数据可信度",
    "Moderate Data Confidence": "中等数据可信度",
    "Low Data Confidence": "较低数据可信度",
    "Very Low Data Confidence": "很低数据可信度",
}


def resolve_data_dir(data_dir: str | Path = "data") -> Path:
    """Resolve a data directory relative to project root."""
    path = Path(data_dir)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def load_quality_data(data_dir: str | Path = "data") -> dict[str, pd.DataFrame]:
    """Load all data files used by the data quality module."""
    resolved_dir = resolve_data_dir(data_dir)
    dataframes: dict[str, pd.DataFrame] = {}

    for table_name, file_name in TARGET_FILES.items():
        path = resolved_dir / file_name
        if not path.exists():
            dataframes[table_name] = pd.DataFrame()
            continue
        dataframes[table_name] = pd.read_csv(path)

    return dataframes


def get_asset_ids(dataframes: dict[str, pd.DataFrame]) -> list[str]:
    """Return unique asset IDs across asset-level files."""
    asset_ids: set[str] = set()

    for table_name in ASSET_MODULE_TABLES.values():
        df = dataframes.get(table_name, pd.DataFrame())
        if not df.empty and "asset_id" in df.columns:
            asset_ids.update(df["asset_id"].dropna().astype(str).str.strip())

    return sorted(asset_id for asset_id in asset_ids if asset_id)


def _asset_rows(df: pd.DataFrame, asset_id: str) -> pd.DataFrame:
    if df.empty or "asset_id" not in df.columns:
        return pd.DataFrame()
    return df[df["asset_id"].astype(str) == str(asset_id)].copy()


def _usable_value_count(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    usable_columns = [column for column in df.columns if column not in METADATA_COLUMNS]
    if not usable_columns:
        return 0
    return int(df[usable_columns].replace("", pd.NA).notna().sum().sum())


def _get_asset_name(asset_id: str, dataframes: dict[str, pd.DataFrame]) -> str:
    assets_df = dataframes.get("assets", pd.DataFrame())
    asset_rows = _asset_rows(assets_df, asset_id)
    if not asset_rows.empty and "asset_name" in asset_rows.columns:
        return str(asset_rows.iloc[0]["asset_name"])
    return str(asset_id)


def calculate_completeness_score(asset_id: str, dataframes: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """Calculate non-missing value completeness across asset-level tables."""
    non_missing_count = 0
    total_count = 0
    missing_fields: dict[str, list[str]] = {}

    for table_name in ASSET_MODULE_TABLES.values():
        df = dataframes.get(table_name, pd.DataFrame())
        asset_df = _asset_rows(df, asset_id)
        if asset_df.empty:
            usable_columns = [column for column in df.columns if column not in METADATA_COLUMNS]
            missing_fields[table_name] = usable_columns
            total_count += len(usable_columns)
            continue

        usable_columns = [column for column in asset_df.columns if column not in METADATA_COLUMNS]
        total_count += len(usable_columns) * len(asset_df)
        for column in usable_columns:
            missing_count = int(asset_df[column].replace("", pd.NA).isna().sum())
            if missing_count:
                missing_fields.setdefault(table_name, []).append(column)
        non_missing_count += int(asset_df[usable_columns].replace("", pd.NA).notna().sum().sum())

    score = (non_missing_count / total_count * 100) if total_count else 0.0
    explanation = (
        f"{non_missing_count} of {total_count} assessed non-metadata values are present."
        if total_count
        else "No assessable non-metadata fields were found for this asset."
    )

    return {
        "score": round(score, 2),
        "non_missing_count": non_missing_count,
        "total_count": total_count,
        "missing_fields": missing_fields,
        "explanation": explanation,
    }


def calculate_source_reliability_score(asset_id: str, dataframes: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """Calculate data-source reliability using an internal heuristic map."""
    data_type_values: list[str] = []

    for table_name in ASSET_MODULE_TABLES.values():
        asset_df = _asset_rows(dataframes.get(table_name, pd.DataFrame()), asset_id)
        if not asset_df.empty and "data_type" in asset_df.columns:
            data_type_values.extend(asset_df["data_type"].fillna("unknown").astype(str).str.strip().str.lower())

    if not data_type_values:
        data_type_values = ["unknown"]

    scores = [SOURCE_TYPE_SCORE_MAP.get(value, SOURCE_TYPE_SCORE_MAP["unknown"]) for value in data_type_values]
    score = sum(scores) / len(scores)
    distribution = pd.Series(data_type_values).value_counts().to_dict()
    explanation = (
        "Source reliability is an internal portfolio heuristic based on data_type values, "
        "not an official data-quality standard."
    )

    return {
        "score": round(score, 2),
        "data_type_distribution": distribution,
        "explanation": explanation,
    }


def _score_source_note(note: str) -> int:
    cleaned = str(note).strip()
    if not cleaned:
        return 0

    lowered = cleaned.lower()
    detailed_markers = ["http", "www.", "annual report", "page", "prospectus", "disclosure", "source:"]
    if any(marker in lowered for marker in detailed_markers):
        return 100
    if "demo value for portfolio prototype" in lowered or "not official disclosed data" in lowered:
        return 60
    return 75


def calculate_traceability_score(asset_id: str, dataframes: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """Calculate source-note traceability and transparency score."""
    source_notes: list[str] = []

    for table_name in ASSET_MODULE_TABLES.values():
        asset_df = _asset_rows(dataframes.get(table_name, pd.DataFrame()), asset_id)
        if not asset_df.empty and "source_note" in asset_df.columns:
            source_notes.extend(asset_df["source_note"].fillna("").astype(str).tolist())

    if not source_notes:
        return {
            "score": 0.0,
            "source_note_completeness": 0.0,
            "source_note_quality_summary": {"missing": 1},
            "explanation": "No source notes are available for this asset.",
        }

    scored_notes = [_score_source_note(note) for note in source_notes]
    non_empty_count = sum(1 for note in source_notes if str(note).strip())
    completeness = non_empty_count / len(source_notes) * 100
    score = sum(scored_notes) / len(scored_notes)

    summary = {
        "detailed": sum(1 for value in scored_notes if value == 100),
        "explanatory": sum(1 for value in scored_notes if value == 75),
        "generic_demo_transparent": sum(1 for value in scored_notes if value == 60),
        "missing": sum(1 for value in scored_notes if value == 0),
    }
    explanation = (
        f"{non_empty_count} of {len(source_notes)} source notes are non-empty. "
        "Generic demo notes receive partial credit because they are transparent about simulation boundaries."
    )

    return {
        "score": round(score, 2),
        "source_note_completeness": round(completeness, 2),
        "source_note_quality_summary": summary,
        "explanation": explanation,
    }


def calculate_timeliness_score(asset_id: str, dataframes: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """Calculate relative recency within the demo dataset."""
    asset_years: list[int] = []
    dataset_years: list[int] = []

    for table_name in ASSET_MODULE_TABLES.values():
        df = dataframes.get(table_name, pd.DataFrame())
        if df.empty or "year" not in df.columns:
            continue
        years = pd.to_numeric(df["year"], errors="coerce").dropna().astype(int).tolist()
        dataset_years.extend(years)

        asset_df = _asset_rows(df, asset_id)
        if not asset_df.empty:
            asset_years.extend(pd.to_numeric(asset_df["year"], errors="coerce").dropna().astype(int).tolist())

    if not asset_years or not dataset_years:
        return {
            "score": 20.0,
            "latest_year_for_asset": None,
            "latest_year_in_dataset": max(dataset_years) if dataset_years else None,
            "explanation": "No valid year data is available for this asset.",
        }

    latest_asset_year = max(asset_years)
    latest_dataset_year = max(dataset_years)
    year_gap = latest_dataset_year - latest_asset_year
    if year_gap <= 0:
        score = 100
    elif year_gap == 1:
        score = 80
    elif year_gap == 2:
        score = 60
    else:
        score = 40

    return {
        "score": float(score),
        "latest_year_for_asset": latest_asset_year,
        "latest_year_in_dataset": latest_dataset_year,
        "explanation": (
            f"Latest asset year is {latest_asset_year}; latest year in the dataset is {latest_dataset_year}. "
            "Timeliness is assessed relative to the dataset, not the current calendar year."
        ),
    }


def calculate_coverage_score(asset_id: str, dataframes: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """Calculate analytical module coverage for an asset."""
    covered_modules: list[str] = []
    missing_modules: list[str] = []

    for module_name, table_name in ASSET_MODULE_TABLES.items():
        asset_df = _asset_rows(dataframes.get(table_name, pd.DataFrame()), asset_id)
        if not asset_df.empty and _usable_value_count(asset_df) > 0:
            covered_modules.append(module_name)
        else:
            missing_modules.append(module_name)

    score = len(covered_modules) / len(ASSET_MODULE_TABLES) * 100
    explanation = f"{len(covered_modules)} of {len(ASSET_MODULE_TABLES)} analytical modules have usable values."

    return {
        "score": round(score, 2),
        "covered_modules": covered_modules,
        "missing_modules": missing_modules,
        "explanation": explanation,
    }


def assign_data_confidence_level(score: float) -> str:
    """Assign a data confidence level from a 0-100 score."""
    if score >= 85:
        return "High Data Confidence"
    if score >= 70:
        return "Moderate-High Data Confidence"
    if score >= 55:
        return "Moderate Data Confidence"
    if score >= 40:
        return "Low Data Confidence"
    return "Very Low Data Confidence"


def calculate_data_confidence_score(
    asset_id: str,
    dataframes: dict[str, pd.DataFrame] | None = None,
    data_dir: str | Path = "data",
) -> dict[str, Any]:
    """Calculate the weighted data confidence score for one asset."""
    if dataframes is None:
        dataframes = load_quality_data(data_dir)

    completeness = calculate_completeness_score(asset_id, dataframes)
    source_reliability = calculate_source_reliability_score(asset_id, dataframes)
    traceability = calculate_traceability_score(asset_id, dataframes)
    timeliness = calculate_timeliness_score(asset_id, dataframes)
    coverage = calculate_coverage_score(asset_id, dataframes)

    dimension_scores = {
        "completeness_score": completeness["score"],
        "source_reliability_score": source_reliability["score"],
        "traceability_score": traceability["score"],
        "timeliness_score": timeliness["score"],
        "coverage_score": coverage["score"],
    }
    total_score = sum(dimension_scores[key] * weight for key, weight in DIMENSION_WEIGHTS.items())
    warnings: list[str] = []
    if source_reliability["score"] < 60:
        warnings.append("Source reliability is limited by mixed or simulated data_type values.")
    if traceability["score"] < 70:
        warnings.append("Source notes should be strengthened with more specific source references.")
    if completeness["score"] < 80:
        warnings.append("Completeness can be improved by filling missing analytical fields.")

    return {
        "asset_id": asset_id,
        "asset_name": _get_asset_name(asset_id, dataframes),
        **dimension_scores,
        "data_confidence_score": round(total_score, 2),
        "data_confidence_level": assign_data_confidence_level(total_score),
        "explanations": {
            "completeness": completeness["explanation"],
            "source_reliability": source_reliability["explanation"],
            "traceability": traceability["explanation"],
            "timeliness": timeliness["explanation"],
            "coverage": coverage["explanation"],
        },
        "details": {
            "completeness": completeness,
            "source_reliability": source_reliability,
            "traceability": traceability,
            "timeliness": timeliness,
            "coverage": coverage,
        },
        "warnings": warnings,
    }


def calculate_all_data_confidence_scores(data_dir: str | Path = "data") -> pd.DataFrame:
    """Calculate data confidence scores for all assets."""
    dataframes = load_quality_data(data_dir)
    rows = [calculate_data_confidence_score(asset_id, dataframes) for asset_id in get_asset_ids(dataframes)]
    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(
        [
            {
                "asset_id": row["asset_id"],
                "asset_name": row["asset_name"],
                "completeness_score": row["completeness_score"],
                "source_reliability_score": row["source_reliability_score"],
                "traceability_score": row["traceability_score"],
                "timeliness_score": row["timeliness_score"],
                "coverage_score": row["coverage_score"],
                "data_confidence_score": row["data_confidence_score"],
                "data_confidence_level": row["data_confidence_level"],
            }
            for row in rows
        ]
    ).sort_values("data_confidence_score", ascending=False)


def get_data_type_distribution(data_dir: str | Path = "data") -> pd.DataFrame:
    """Summarize data_type counts and percentages by table and overall."""
    dataframes = load_quality_data(data_dir)
    rows: list[dict[str, Any]] = []

    for table_name, df in dataframes.items():
        if df.empty or "data_type" not in df.columns:
            continue
        counts = df["data_type"].fillna("unknown").astype(str).str.strip().str.lower().replace("", "unknown")
        total = len(counts)
        for data_type, count in counts.value_counts().items():
            rows.append(
                {
                    "table": table_name,
                    "data_type": data_type,
                    "count": int(count),
                    "percentage": round(count / total * 100, 2) if total else 0.0,
                }
            )

    if rows:
        all_values = []
        for df in dataframes.values():
            if not df.empty and "data_type" in df.columns:
                all_values.extend(df["data_type"].fillna("unknown").astype(str).str.strip().str.lower().tolist())
        total = len(all_values)
        for data_type, count in pd.Series(all_values).replace("", "unknown").value_counts().items():
            rows.append(
                {
                    "table": "overall",
                    "data_type": data_type,
                    "count": int(count),
                    "percentage": round(count / total * 100, 2) if total else 0.0,
                }
            )

    return pd.DataFrame(rows)


def get_missingness_summary(data_dir: str | Path = "data") -> pd.DataFrame:
    """Summarize missing values by table and column."""
    dataframes = load_quality_data(data_dir)
    rows: list[dict[str, Any]] = []

    for table_name, df in dataframes.items():
        if df.empty:
            continue
        row_count = len(df)
        for column in df.columns:
            missing_count = int(df[column].replace("", pd.NA).isna().sum())
            rows.append(
                {
                    "table": table_name,
                    "column": column,
                    "missing_count": missing_count,
                    "missing_percentage": round(missing_count / row_count * 100, 2) if row_count else 0.0,
                    "row_count": row_count,
                }
            )

    return pd.DataFrame(rows)


def _localized_confidence_level(level: str, language: str) -> str:
    if language == "zh":
        return DATA_CONFIDENCE_LEVEL_ZH.get(level, level)
    return level


def _english_report_sections(result: dict[str, Any]) -> dict[str, list[str]]:
    warnings = result["warnings"] or ["No major data quality warnings generated by this prototype rule set."]

    strengths = []
    if result["completeness_score"] >= 80:
        strengths.append("Most non-metadata fields are populated.")
    if result["coverage_score"] >= 90:
        strengths.append("The asset is covered across nearly all key analytical modules.")
    if result["traceability_score"] >= 60:
        strengths.append("Source notes are present and support transparency about data origin.")
    if not strengths:
        strengths.append("The dataset provides a structured starting point for transparent review.")

    suggestions = [
        "Replace simulated financial data with verified annual report values where available.",
        "Add official source URLs, report names, or page notes to strengthen traceability.",
        "Collect OTA score and review count from documented public platforms.",
        "Expand the peer sample size to support stronger relative comparisons.",
        "Consider adding a future verification_status field to distinguish verified, collected, assessed, mixed, and simulated values.",
    ]

    return {"strengths": strengths, "limitations": warnings, "suggestions": suggestions}


def _chinese_report_sections(result: dict[str, Any]) -> dict[str, list[str]]:
    strengths = []
    if result["completeness_score"] >= 80:
        strengths.append("大多数非元数据字段已经填充。")
    if result["coverage_score"] >= 90:
        strengths.append("该资产在主要分析模块中均有可用数据。")
    if result["traceability_score"] >= 60:
        strengths.append("数据来源说明字段存在，有助于区分模拟、混合或公开采集数据。")
    if not strengths:
        strengths.append("该数据集为透明评估提供了结构化起点。")

    limitations = []
    if result["source_reliability_score"] < 60:
        limitations.append("当前数据中仍包含模拟或混合来源字段，不能视为官方披露数据。")
    if result["traceability_score"] < 70:
        limitations.append("部分 source_note 仍较为概括，后续应补充年报页码、公告链接或采集来源。")
    if result["completeness_score"] < 80:
        limitations.append("部分分析字段存在缺失，可能限制结果解释。")
    limitations.append("样本资产数量较小，数据质量评分主要用于作品集原型展示。")

    suggestions = [
        "用上市公司年报或公告中的真实披露值替换模拟财务字段。",
        "为关键字段补充 official_source_url、报告年份和页码说明。",
        "从公开 OTA 平台补充评分、评论量和服务质量相关数据。",
        "扩大同类资产样本规模，提高评分模型的比较基础。",
        "增加 verification_status 字段，区分已核验、待核验和模拟数据。",
    ]

    return {"strengths": strengths, "limitations": limitations, "suggestions": suggestions}


def generate_data_quality_report(
    asset_id: str,
    data_dir: str | Path = "data",
    language: str = "en",
) -> str:
    """Generate a deterministic Markdown data quality report for one asset."""
    dataframes = load_quality_data(data_dir)
    result = calculate_data_confidence_score(asset_id, dataframes)

    if language == "zh":
        sections = _chinese_report_sections(result)
        lines = [
            f"# 数据质量报告：{result['asset_name']}",
            "",
            "## 总体数据可信度",
            f"- 数据可信度评分：{result['data_confidence_score']:.1f}",
            f"- 数据可信度等级：{_localized_confidence_level(result['data_confidence_level'], language)}",
            "",
            "## 维度得分",
            f"- 完整性：{result['completeness_score']:.1f}",
            f"- 来源可靠性：{result['source_reliability_score']:.1f}",
            f"- 可追溯性：{result['traceability_score']:.1f}",
            f"- 时效性：{result['timeliness_score']:.1f}",
            f"- 覆盖度：{result['coverage_score']:.1f}",
            "",
            "## 主要数据优势",
            *[f"- {item}" for item in sections["strengths"]],
            "",
            "## 主要数据局限",
            *[f"- {item}" for item in sections["limitations"]],
            "",
            "## 改进建议",
            *[f"- {item}" for item in sections["suggestions"]],
            "",
            "## 免责声明",
            "本模块仅评估数据完整性、来源可靠性、可追溯性、时效性与覆盖度，不认证数据真实性，也不会将模拟数据转化为官方披露数据。本结果不构成投资建议、信用评级、估值意见或监管结论。",
        ]
        return "\n".join(lines)

    sections = _english_report_sections(result)

    lines = [
        f"# Data Quality Report: {result['asset_name']}",
        "",
        "## Overall Data Confidence",
        f"- Data confidence score: {result['data_confidence_score']:.1f}",
        f"- Data confidence level: {result['data_confidence_level']}",
        "",
        "## Dimension Scores",
        f"- Completeness: {result['completeness_score']:.1f}",
        f"- Source reliability: {result['source_reliability_score']:.1f}",
        f"- Traceability: {result['traceability_score']:.1f}",
        f"- Timeliness: {result['timeliness_score']:.1f}",
        f"- Coverage: {result['coverage_score']:.1f}",
        "",
        "## Main Data Strengths",
        *[f"- {item}" for item in sections["strengths"]],
        "",
        "## Main Data Limitations",
        *[f"- {item}" for item in sections["limitations"]],
        "",
        "## Improvement Suggestions",
        *[f"- {item}" for item in sections["suggestions"]],
        "",
        "## Disclaimer",
        "This module evaluates data quality and transparency, not asset quality. It does not certify data accuracy and does not convert simulated data into official disclosed data.",
    ]

    return "\n".join(lines)


def main() -> int:
    """CLI smoke test for the data quality module."""
    scores_df = calculate_all_data_confidence_scores()
    distribution_df = get_data_type_distribution()
    missingness_df = get_missingness_summary()

    print("=" * 100)
    print("Data confidence table")
    print(scores_df.to_string(index=False) if not scores_df.empty else "No scores available.")
    print("=" * 100)
    print("Data type distribution")
    print(distribution_df.to_string(index=False) if not distribution_df.empty else "No data_type values available.")
    print("=" * 100)
    print("Missingness summary")
    print(missingness_df.head(40).to_string(index=False) if not missingness_df.empty else "No missingness summary available.")
    print("=" * 100)
    if not scores_df.empty:
        print("Sample data quality report")
        print(generate_data_quality_report(str(scores_df.iloc[0]["asset_id"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

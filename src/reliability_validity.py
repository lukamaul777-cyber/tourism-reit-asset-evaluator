"""Reliability, validity, and robustness checks for the scoring framework.

These checks support model governance for the Tourism REIT Asset Evaluator
portfolio prototype. They do not turn the demo model into an official rating,
regulatory conclusion, or investment recommendation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from src.scoring_model import MODULE_ORDER, run_scoring_pipeline


RI_VALUES = {
    1: 0.00,
    2: 0.00,
    3: 0.58,
    4: 0.90,
    5: 1.12,
    6: 1.24,
    7: 1.32,
    8: 1.41,
    9: 1.45,
    10: 1.49,
}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _resolve_path(path: str | Path) -> Path:
    resolved = Path(path)
    if not resolved.is_absolute():
        resolved = _project_root() / resolved
    return resolved


def _load_yaml(path: str | Path) -> dict[str, Any]:
    with _resolve_path(path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def calculate_cronbach_alpha(df_items: pd.DataFrame) -> dict[str, Any]:
    """Calculate Cronbach's Alpha for survey-scale or multi-item data."""
    numeric_items = df_items.apply(pd.to_numeric, errors="coerce")
    numeric_items = numeric_items.dropna(axis=0, how="all")
    numeric_items = numeric_items.dropna(axis=1, how="all")

    valid_columns = list(numeric_items.columns)
    if len(valid_columns) < 2:
        return {
            "alpha": None,
            "status": "not_applicable",
            "valid_item_count": len(valid_columns),
            "valid_response_count": len(numeric_items),
            "explanation": (
                "Cronbach's Alpha requires at least two valid survey-scale or multi-item variables."
            ),
        }

    complete_items = numeric_items.dropna(axis=0, how="any")
    if len(complete_items) < 2:
        return {
            "alpha": None,
            "status": "not_applicable",
            "valid_item_count": len(valid_columns),
            "valid_response_count": len(complete_items),
            "explanation": "Cronbach's Alpha requires at least two complete observations after missing-value handling.",
        }

    item_variances = complete_items.var(axis=0, ddof=1)
    total_score = complete_items.sum(axis=1)
    total_variance = total_score.var(ddof=1)

    if pd.isna(total_variance) or total_variance == 0:
        return {
            "alpha": None,
            "status": "not_applicable",
            "valid_item_count": len(valid_columns),
            "valid_response_count": len(complete_items),
            "explanation": "Cronbach's Alpha is not applicable because total survey-score variance is zero.",
        }

    item_count = len(valid_columns)
    alpha = (item_count / (item_count - 1)) * (1 - item_variances.sum() / total_variance)
    status = "acceptable" if alpha >= 0.70 else "needs_review"

    return {
        "alpha": float(alpha),
        "status": status,
        "valid_item_count": item_count,
        "valid_response_count": int(len(complete_items)),
        "explanation": (
            f"Cronbach's Alpha is {alpha:.3f}. A value of 0.70 is a common rule-of-thumb "
            "for internal consistency, not an absolute law. Apply this only to survey-scale "
            "or multi-item service-quality dimensions, not ordinary financial ratios."
        ),
    }


def _matrix_to_array(pairwise_matrix: Any) -> tuple[np.ndarray, list[str]]:
    if isinstance(pairwise_matrix, pd.DataFrame):
        labels = [str(label) for label in pairwise_matrix.index]
        matrix = pairwise_matrix.to_numpy(dtype=float)
    else:
        matrix = np.asarray(pairwise_matrix, dtype=float)
        labels = [f"item_{index + 1}" for index in range(matrix.shape[0])]

    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("AHP pairwise_matrix must be square.")
    if matrix.shape[0] > 10:
        raise ValueError("AHP RI lookup is configured only for n = 1 to 10.")
    if np.any(matrix <= 0):
        raise ValueError("AHP pairwise_matrix values must be positive.")

    return matrix, labels


def calculate_ahp_consistency_ratio(pairwise_matrix: Any) -> dict[str, Any]:
    """Calculate AHP consistency ratio for an expert pairwise matrix."""
    matrix, labels = _matrix_to_array(pairwise_matrix)
    n = matrix.shape[0]
    eigenvalues, eigenvectors = np.linalg.eig(matrix)
    principal_index = int(np.argmax(eigenvalues.real))
    lambda_max = float(eigenvalues[principal_index].real)

    if n <= 2:
        return {
            "lambda_max": lambda_max,
            "CI": 0.0,
            "RI": RI_VALUES[n],
            "CR": None,
            "status": "acceptable",
            "labels": labels,
            "explanation": "AHP consistency ratio is not applicable for n <= 2, but consistency can be treated as acceptable.",
        }

    ci = (lambda_max - n) / (n - 1)
    ri = RI_VALUES[n]
    cr = ci / ri if ri else None
    status = "acceptable" if cr is not None and cr <= 0.10 else "needs_revision"

    return {
        "lambda_max": lambda_max,
        "CI": float(ci),
        "RI": float(ri),
        "CR": float(cr) if cr is not None else None,
        "status": status,
        "labels": labels,
        "explanation": (
            f"AHP consistency ratio is {cr:.3f}. A CR <= 0.10 is a common rule-of-thumb "
            "for acceptable expert pairwise consistency, not an official approval test."
        ),
    }


def derive_ahp_weights(pairwise_matrix: Any, labels: list[str] | None = None) -> dict[str, Any]:
    """Derive normalized AHP weights from the principal eigenvector."""
    matrix, inferred_labels = _matrix_to_array(pairwise_matrix)
    output_labels = labels or inferred_labels
    if len(output_labels) != matrix.shape[0]:
        raise ValueError("labels length must match pairwise_matrix size.")

    eigenvalues, eigenvectors = np.linalg.eig(matrix)
    principal_index = int(np.argmax(eigenvalues.real))
    principal_vector = np.abs(eigenvectors[:, principal_index].real)
    weights = principal_vector / principal_vector.sum()

    return {
        "labels": output_labels,
        "weights": {label: float(weight) for label, weight in zip(output_labels, weights)},
        "sum_check": float(weights.sum()),
        "explanation": "AHP weights are derived from the normalized principal eigenvector of the pairwise matrix.",
    }


def calculate_spearman_rank_stability(original_ranking: Any, simulated_ranking: Any) -> float | None:
    """Calculate Spearman rank correlation with a SciPy fallback path."""
    original = pd.Series(original_ranking, dtype="float64")
    simulated = pd.Series(simulated_ranking, dtype="float64")
    aligned = pd.concat([original, simulated], axis=1).dropna()

    if len(aligned) < 2:
        return None

    try:
        from scipy.stats import spearmanr  # type: ignore

        correlation = spearmanr(aligned.iloc[:, 0], aligned.iloc[:, 1], nan_policy="omit").correlation
        return None if pd.isna(correlation) else float(correlation)
    except Exception:
        correlation = aligned.iloc[:, 0].rank(method="average").corr(
            aligned.iloc[:, 1].rank(method="average"),
            method="pearson",
        )
        return None if pd.isna(correlation) else float(correlation)


def run_weight_sensitivity_analysis(
    total_scores_df: pd.DataFrame,
    module_scores_df: pd.DataFrame,
    base_weights: dict[str, float],
    perturbation: float = 0.10,
    n_simulations: int = 500,
    random_state: int = 42,
) -> dict[str, Any]:
    """Test ranking stability when module weights are randomly perturbed."""
    rng = np.random.default_rng(random_state)
    base_weight_series = pd.Series(base_weights, dtype="float64")
    base_weight_series = base_weight_series / base_weight_series.sum() * 100

    score_pivot = module_scores_df.pivot(index="asset_id", columns="module", values="module_score")
    score_pivot = score_pivot.reindex(columns=list(base_weight_series.index))
    asset_names = module_scores_df.drop_duplicates("asset_id").set_index("asset_id")["asset_name"]
    original_scores = total_scores_df.set_index("asset_id")["total_score"]
    original_ranks = original_scores.rank(ascending=False, method="min")
    original_order = tuple(original_scores.sort_values(ascending=False).index)

    simulated_rows: list[dict[str, Any]] = []
    spearman_values: list[float] = []
    identical_rank_count = 0

    for simulation_id in range(1, n_simulations + 1):
        perturbation_factors = rng.uniform(1 - perturbation, 1 + perturbation, len(base_weight_series))
        simulated_weights = base_weight_series * perturbation_factors
        simulated_weights = simulated_weights / simulated_weights.sum() * 100

        weighted_scores = score_pivot.mul(simulated_weights, axis=1)
        available_weights = score_pivot.notna().mul(simulated_weights, axis=1).sum(axis=1)
        simulated_scores = weighted_scores.sum(axis=1) / available_weights.replace({0: np.nan})
        simulated_ranks = simulated_scores.rank(ascending=False, method="min")
        simulated_order = tuple(simulated_scores.sort_values(ascending=False).index)

        if simulated_order == original_order:
            identical_rank_count += 1

        spearman = calculate_spearman_rank_stability(original_ranks, simulated_ranks)
        if spearman is not None:
            spearman_values.append(spearman)

        for asset_id, simulated_score in simulated_scores.items():
            simulated_rows.append(
                {
                    "simulation_id": simulation_id,
                    "asset_id": asset_id,
                    "asset_name": asset_names.get(asset_id, asset_id),
                    "simulated_total_score": simulated_score,
                    "simulated_rank": simulated_ranks.get(asset_id),
                }
            )

    ranking_stability_ratio = identical_rank_count / n_simulations if n_simulations else None
    average_spearman = float(np.mean(spearman_values)) if spearman_values else None

    return {
        "ranking_stability_ratio": ranking_stability_ratio,
        "average_spearman_correlation": average_spearman,
        "simulated_rankings": pd.DataFrame(simulated_rows),
        "explanation": (
            f"Ran {n_simulations} module-weight perturbation simulations at +/- {perturbation:.0%}. "
            "Weights were re-normalized to sum to 100 in each simulation. This tests ranking robustness, "
            "not future operating scenarios."
        ),
    }


def generate_content_validity_table(
    indicator_framework_path: str | Path = "config/indicator_framework.yml",
) -> pd.DataFrame:
    """Generate a reference-mapping table for content validity review."""
    indicator_config = _load_yaml(indicator_framework_path)
    columns = [
        "indicator_id",
        "indicator_name",
        "module",
        "reference_framework",
        "reference_note",
        "validation_method",
        "reliability_method",
        "whether_it_is_required",
    ]
    return pd.DataFrame(indicator_config.get("indicators", []))[columns]


def _load_default_module_weights(weight_mode: str) -> dict[str, float]:
    weights_config = _load_yaml("config/scoring_weights.yml")
    mode_config = weights_config.get("weighting_modes", {}).get(weight_mode, {})
    modules = mode_config.get("modules", {})
    return {module_name: float(module_config["weight"]) for module_name, module_config in modules.items()}


def _load_ahp_pairwise_matrix_if_available() -> tuple[Any | None, list[str] | None, str]:
    matrix_path = _resolve_path("config/ahp_pairwise_matrix.yml")
    if not matrix_path.exists():
        return None, None, "AHP consistency check not run because no pairwise matrix was provided."

    matrix_config = _load_yaml(matrix_path)
    labels = matrix_config.get("labels")
    matrix = matrix_config.get("matrix", matrix_config)
    if labels:
        return pd.DataFrame(matrix, index=labels, columns=labels), labels, "AHP pairwise matrix loaded."
    return np.asarray(matrix, dtype=float), None, "AHP pairwise matrix loaded."


def run_model_validity_pipeline(
    data_dir: str | Path = "data",
    weight_mode: str = "default_expert_weight",
) -> dict[str, Any]:
    """Run available model validity checks."""
    content_validity_table = generate_content_validity_table()
    indicator_scores_df, module_scores_df, total_scores_df = run_scoring_pipeline(data_dir, weight_mode)

    service_quality_path = _resolve_path(data_dir) / "service_quality_metrics.csv"
    service_quality_df = pd.read_csv(service_quality_path)
    service_item_columns = [
        "tangibles_score",
        "reliability_score",
        "responsiveness_score",
        "assurance_score",
        "empathy_score",
    ]
    cronbach_result = calculate_cronbach_alpha(service_quality_df[service_item_columns])

    base_weights = _load_default_module_weights(weight_mode)
    sensitivity_result = run_weight_sensitivity_analysis(
        total_scores_df=total_scores_df,
        module_scores_df=module_scores_df,
        base_weights=base_weights,
    )

    pairwise_matrix, labels, ahp_message = _load_ahp_pairwise_matrix_if_available()
    if pairwise_matrix is None:
        ahp_result = {
            "status": "not_run",
            "explanation": ahp_message,
        }
        ahp_weights = None
    else:
        ahp_result = calculate_ahp_consistency_ratio(pairwise_matrix)
        ahp_weights = derive_ahp_weights(pairwise_matrix, labels)

    return {
        "content_validity_table": content_validity_table,
        "cronbach_alpha": cronbach_result,
        "ahp_consistency": ahp_result,
        "ahp_weights": ahp_weights,
        "sensitivity_analysis": sensitivity_result,
        "indicator_scores_df": indicator_scores_df,
        "module_scores_df": module_scores_df,
        "total_scores_df": total_scores_df,
    }


def generate_validity_report(validity_results: dict[str, Any]) -> str:
    """Generate a plain-language model validity report."""
    content_table = validity_results["content_validity_table"]
    cronbach = validity_results["cronbach_alpha"]
    ahp = validity_results["ahp_consistency"]
    sensitivity = validity_results["sensitivity_analysis"]

    avg_spearman = sensitivity.get("average_spearman_correlation")
    rank_stability = sensitivity.get("ranking_stability_ratio")
    avg_spearman_text = "not available" if avg_spearman is None else f"{avg_spearman:.3f}"
    rank_stability_text = "not available" if rank_stability is None else f"{rank_stability:.1%}"

    sections = [
        "Content validity",
        (
            f"The indicator framework contains {len(content_table)} indicators mapped to reference frameworks, "
            "reference notes, validation methods, and reliability methods."
        ),
        "",
        "Construct validity",
        (
            "The model structure reflects five intended constructs: REIT cash flow and distribution capacity, "
            "tourism operating quality, service quality and online reputation, risk management and resilience, "
            "and data maturity and smart operation."
        ),
        "",
        "Reliability",
        cronbach["explanation"],
        "",
        "Weight consistency",
        ahp["explanation"],
        "",
        "Robustness / sensitivity analysis",
        (
            f"{sensitivity['explanation']} Average Spearman rank correlation: {avg_spearman_text}. "
            f"Identical ranking stability ratio: {rank_stability_text}."
        ),
        "",
        "Limitations",
        (
            "The demo dataset is small and includes simulated or mixed values, which limits statistical inference. "
            "Robustness results should be interpreted as a model-behavior check rather than proof of investment validity."
        ),
        "",
        "Disclaimer",
        (
            "This project is a portfolio prototype, not an official rating system, regulatory conclusion, "
            "valuation opinion, or investment recommendation."
        ),
    ]

    return "\n".join(sections)

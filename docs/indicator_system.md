# Indicator System

## Overview

The indicator system uses a two-layer structure:

1. Regulatory Gatekeeper: binary checks for eligibility and red flags.
2. 100-point Scoring Model: relative assessment across five modules.

Each indicator in `config/indicator_framework.yml` includes an ID, name, module, definition, formula, scoring direction, source type, reference framework, validation method, reliability method, and required-status flag.

The Data Quality / Data Confidence module is a supporting transparency layer around the data inputs. It evaluates completeness, source reliability, traceability, timeliness, and coverage, but it does not add new REITs suitability indicators or change the 100-point scoring formulas.

## Layer 1: Regulatory Gatekeeper

The gatekeeper checks whether the asset has:

- Clear ownership or operation rights.
- No major legal disputes.
- Operating history of around 3 years or more.
- Stable operating cash flow.
- Market-based cash-flow source.
- Ability to support distributable cash flow.
- Capex pressure that is not unusually high relative to the demo sample.
- Continuous-operation risk indicators that are not unusually high relative to the demo sample.

Hard conditions are `ownership_clear`, `no_major_legal_dispute`, `operating_history`, `stable_operating_cash_flow`, `market_based_cash_flow`, and `distribution_capacity`.

Warning-only conditions are `capex_pressure_warning` and `continuous_operation_warning`. These warning checks use sample percentile comparisons in the MVP and do not represent official regulatory thresholds.

Gatekeeper output includes condition-level status, explanation text, reference logic, an overall status, and a summary. Overall status is `Fail` if any hard condition fails, `Pass with Warning` if no hard condition fails but at least one warning exists, and `Pass` if all checks pass without warnings.

## Layer 2: 100-Point Model

The 100-point model uses peer min-max normalization on latest available year data by default. Positive indicators reward higher values relative to the peer sample, while negative indicators reward lower values relative to the peer sample. Missing indicator scores are excluded from module averages and disclosed in explanations.

### A. REITs Cash Flow and Distribution Capacity

This module evaluates whether the asset can generate stable, recurring, market-based operating cash flow that can support distributable cash flow.

### B. Tourism Operating Quality

This module evaluates demand stability, utilization, revenue productivity, and seasonality.

### C. Service Quality and Online Reputation

This module evaluates online reputation, complaint incidence, and survey-based service quality using service-quality frameworks such as SERVQUAL, HOLSERV, and DINESERV.

### D. Risk Management and Resilience

This module evaluates legal and compliance risk, business continuity, operational resilience, subsidy dependence, and climate or physical-risk exposure.

### E. Data Maturity and Smart Operation

This module evaluates data governance maturity, smart operation coverage, and automated data availability.

## Normalization

Positive indicators are normalized so higher raw values produce higher scores. Negative indicators are normalized so lower raw values produce higher scores.

The scoring utilities in `src/scoring_model.py` use peer minimum and maximum values from the current sample. If all peer values are the same for an indicator, the model returns a neutral score of 50. This keeps the scoring layer sample-relative and avoids unsupported official-threshold claims.

## Validity and Reliability Checks

The model validity layer supports content, construct, reliability, weight-consistency, and robustness review.

Content validity is reviewed by checking whether each indicator is mapped to a reference framework and documented validation logic.

Construct validity is reviewed by checking whether indicators align with the five model modules: cash flow, tourism operation, service quality, risk management, and data maturity.

Cronbach's Alpha is reserved for survey-scale or multi-item service-quality fields. It should not be applied to ordinary financial ratios.

AHP consistency ratio is used only when an expert pairwise comparison matrix is provided.

Weight sensitivity analysis tests whether rankings are stable under small randomized module-weight perturbations. This is a robustness check, not a scenario simulation.

## Scenario Simulation

The scenario simulator is a backend stress-test layer. It does not add indicators, change scoring formulas, or change Regulatory Gatekeeper logic.

Scenario inputs adjust selected latest-year operating and financial values such as revenue, visitor volume, occupancy, ADR, operating cost, maintenance CAPEX, and OTA score. The simulator then recalculates selected derived fields and runs the existing 100-point scoring model on an in-memory scenario-adjusted dataframe.

Scenario outputs are simulated estimates for portfolio demonstration. Severity labels such as `Low Impact`, `Moderate Impact`, `High Impact`, and `Severe Impact` are internal interpretation labels and are not official regulatory thresholds.

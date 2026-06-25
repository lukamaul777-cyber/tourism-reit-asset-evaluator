# Verified Public Financial Data Workflow

## Purpose

This workflow is designed to replace selected demo financial values with public financial data when those values can be obtained and reviewed. It supports a more evidence-based portfolio prototype while preserving transparent source tracking.

The workflow does not overwrite `data/financial_metrics.csv`. It writes reviewable outputs to `data_verified/`:

- `financial_metrics_public_raw.csv`
- `financial_metrics_verified.csv`
- `replacement_preview.csv`

## Target Fields

First-stage public replacements are limited to fields that are commonly available from public listed-company statements:

- `revenue`
- `operating_cash_flow`
- `total_assets`
- `total_debt` or total-liabilities proxy
- `debt_ratio`

Fields such as `ebitda`, `noi`, `maintenance_capex`, `estimated_affo`, `estimated_distribution`, and `capex_to_ocf` may remain estimated because listed companies do not always disclose them directly in a project-compatible way.

## Source Policy

Public data fetching may depend on third-party open-source interfaces such as AKShare. AKShare is optional and is not required for normal app operation.

Official annual reports, exchange announcements, prospectuses, and other issuer or exchange disclosures remain the preferred source for final verification. AKShare output should be treated as a convenient public collection layer, not as a substitute for source-document due diligence.

## Unit Standardization

AKShare public financial statement fields may be returned in RMB yuan. The project financial metrics use RMB million internally, matching the demo dataset in `data/financial_metrics.csv`.

Before replacement candidates are written, monetary fields are standardized to RMB million:

- `revenue`
- `operating_cash_flow`
- `total_assets`
- `total_debt`
- `total_liabilities`

If a monetary value is clearly in yuan scale, for example with an absolute value above `1,000,000`, the pipeline divides it by `1,000,000` and records unit metadata in `source_unit`, `standardized_unit`, and `unit_note`.

Ratio fields such as `debt_ratio` are not converted as monetary values. They remain decimal ratios, for example `0.17` means 17%.

## Review Process

1. Install AKShare only if you want to try live public fetching:

   ```powershell
   python -m pip install akshare
   ```

2. Run the public-data update script:

   ```powershell
   python scripts/update_public_financial_data.py
   ```

3. Validate generated outputs:

   ```powershell
   python scripts/validate_verified_financial_data.py
   ```

4. Review `data_verified/replacement_preview.csv` manually before using `financial_metrics_verified.csv`.

5. Confirm source names, years, values, units, and verification status against official disclosures before treating values as verified.

## Important Limitations

This workflow does not convert estimated fields into official data. It does not create official financial disclosures, investment advice, credit ratings, valuation opinions, or regulatory conclusions.

If live fetching fails because AKShare is not installed, a remote endpoint changes, or network access is unavailable, the project still runs with the existing demo dataset.

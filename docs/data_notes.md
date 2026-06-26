# Data Notes

## Source Types

The framework uses five source types:

- `public_disclosure`: prospectuses, annual reports, operating reports, valuation reports, audited statements, and official disclosures.
- `public_collected`: public websites, online travel agencies, review platforms, map platforms, public complaint channels, and tourism information portals.
- `survey`: structured questionnaires for visitors, guests, tenants, operators, or experts.
- `simulated`: generated demo values used for product testing or examples.
- `manual_assessment`: analyst-reviewed scores based on documents, interviews, due diligence, or expert judgment.

## Fields That May Come From Annual Reports or Public Disclosures

The following fields may be sourced from annual reports, prospectuses, audited financial statements, valuation reports, operating reports, or other public disclosures when those sources are directly verified:

- Asset identity and business description fields such as `asset_name`, `asset_type`, `location`, `description`, `ownership_status`, and `cash_flow_source_type`.
- Financial fields such as `revenue`, `ebitda`, `noi`, `operating_cash_flow`, `maintenance_capex`, `estimated_affo`, `estimated_distribution`, `total_assets`, `total_debt`, `debt_ratio`, and `capex_to_ocf`.
- Operating fields such as `visitor_volume`, `occupancy_rate`, `adr`, `revpar`, `average_spending_per_visitor`, `secondary_spending_ratio`, and `peak_season_revenue_ratio`, where the reporting entity discloses comparable operating metrics.
- Risk and disclosure fields such as legal-dispute flags, risk disclosure quality, debt pressure, and climate or operational risk information, where source documents provide enough evidence.

Do not label a value as annual report data unless it has been checked against the actual annual report or official disclosure.

## Fields That May Come From OTA or Public Web Sources

The following fields may be collected from online travel agencies, review platforms, map platforms, hotel booking platforms, tourism portals, public complaint channels, or other public web sources:

- `ota_score`
- `review_count`
- `complaint_rate`
- Public review text or derived sentiment fields if added later.
- Public-opinion monitoring inputs if collected through a documented method.
- Online reservation capability indicators where observable from public channels.

Public web collection should record the platform, collection date, query method, deduplication method, and any scale normalization.

## Fields Simulated in the MVP

The initial CSV files in `data/` are portfolio-ready demo templates, not official datasets. Most numeric fields in the MVP are marked `simulated` because they are included to test model wiring, validation, scoring, and future dashboard workflows.

Some asset identity rows are marked `mixed` because the displayed asset names are recognizable examples, while the template descriptions, operating assumptions, ownership status, and model fields are not verified official disclosure values.

Every data table includes:

- `data_type`
- `source_note`

The MVP source note is:

`Demo value for portfolio prototype; not official disclosed data.`

## Simulated Data

Demo data may include simulated values. Simulated values must be clearly labeled before use. Recommended labels include:

- `is_simulated`
- `simulation_method`
- `simulation_date`
- `simulated_by`
- `source_note`

Simulated values should not be presented as actual asset performance.

Simulated values are used in the MVP so the project can demonstrate schema design, validation checks, model traceability, and portfolio presentation without fabricating official disclosures. They must not be interpreted as official data, audited results, regulatory conclusions, valuation advice, investment advice, or a recommendation to buy, sell, hold, sponsor, or list any asset.

## Data Quality Checks

Recommended checks include:

- Completeness by required indicator.
- Consistency of reporting period and asset boundary.
- Reconciliation between public disclosures and operating data.
- Outlier review for holidays, closures, weather events, policy changes, and one-off subsidies.
- Documentation of manual assumptions and reviewer identity.

## Verified Public Financial Data Upgrade

The optional verified-data workflow in `src/public_data_fetcher.py` and `src/verified_data_pipeline.py` can collect selected public listed-company financial fields where available. The first-stage fields are `revenue`, `operating_cash_flow`, `total_assets`, `total_debt` or total-liabilities proxy, and `debt_ratio`.

The workflow writes review outputs to `data_verified/` and does not overwrite the demo dataset in `data/`. Users must review `data_verified/replacement_preview.csv` before using `data_verified/financial_metrics_verified.csv`.

AKShare public financial data may be returned in RMB yuan. The project internally stores monetary financial metrics in RMB million. Before replacement candidates are written, monetary fields are standardized to RMB million and unit metadata is recorded in `source_unit`, `standardized_unit`, and `unit_note`. Ratio fields such as `debt_ratio` are not converted as monetary values and remain decimal ratios.

NOI, AFFO, estimated distribution, maintenance CAPEX, and related derived fields may remain estimated for the MVP unless they are directly verified from source documents.

The REIT Fit Score A module uses the selected financial dataset to calculate public-financial-data-driven indicators where possible:

- `derived_ocf_margin = operating_cash_flow / revenue`, positive direction.
- `derived_debt_ratio = debt_ratio`, or `total_debt / total_assets` when `debt_ratio` is missing, negative direction.
- `derived_revenue_stability = clip(1 - abs(revenue_t - revenue_t_minus_1) / revenue_t_minus_1, 0, 1)`, positive direction.
- `derived_ocf_stability = clip(1 - abs(operating_cash_flow_t - operating_cash_flow_t_minus_1) / abs(operating_cash_flow_t_minus_1), 0, 1)`, positive direction.

These derived indicators are recalculated from whichever financial source is selected in the app. The demo file in `data/financial_metrics.csv` is not overwritten by the verified workflow or by scoring.

The Streamlit app defaults to the demo financial dataset for deployment stability. After running `python scripts/update_public_financial_data.py`, users can switch the sidebar financial data source to the verified public financial dataset. If the verified file is missing, the app automatically falls back to the demo dataset and displays a warning.

## Field Source Labels

The verified public financial dataset is not a full official-data replacement for every analytical field. The project separates field sources into three transparent categories in `config/field_source_map.yml`:

- `verified_public`: selected public financial fields such as `revenue`, `operating_cash_flow`, `total_assets`, `total_debt`, and `debt_ratio`.
- `model_derived`: indicators calculated at scoring time, including `derived_ocf_margin`, `derived_debt_ratio`, `derived_revenue_stability`, `derived_ocf_stability`, `derived_ocf_positive_ratio_past3`, and `derived_affo_distribution_coverage`.
- `estimated_demo_proxy`: fields that may remain estimated, demo-derived, or proxy-based, such as `noi`, `maintenance_capex`, `estimated_affo`, `estimated_distribution`, operation fields, service-quality fields, risk fields, and digital-maturity fields.

Field source labels do not change scoring formulas, weights, or peer-normalization logic. They only improve transparency and explainability. Derived indicators such as A5-A8 are calculated during scoring and are not written back to the raw financial CSV files.

## Windows Path Notes

Use `pathlib.Path` in Python code where possible. Configuration paths should avoid hard-coded path separators so the project remains compatible with Windows development environments.

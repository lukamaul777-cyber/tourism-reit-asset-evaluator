# Tourism REIT Asset Evaluator Model Methodology

## Purpose

The Tourism REIT Asset Evaluator is a transparent, reference-based evaluation framework for tourism-related consumption infrastructure assets, including scenic areas, resort complexes, and hotel assets.

The framework is designed to assess REITs suitability, cash-flow quality, operating strength, service quality, risk resilience, and data maturity. It is not an official credit rating, public REITs approval opinion, legal opinion, valuation opinion, or investment recommendation.

## Two-Layer Structure

The model separates hard regulatory and eligibility conditions from relative scoring.

Layer 1 is the Regulatory Gatekeeper. It applies binary pass/fail checks for issues such as ownership or operation rights, major legal disputes, operating history, cash-flow stability, market-based cash-flow sources, subsidy dependence, distributable cash-flow support, and continuous-operation risk.

Layer 2 is the 100-point scoring model. It should be applied only after the gatekeeper review is completed. A high scoring-model result does not override a failed gatekeeper condition.

## Regulatory Gatekeeper Layer

The Regulatory Gatekeeper is a transparent pre-screening layer for the portfolio prototype. It separates hard REITs suitability conditions from the 100-point scoring model so that basic eligibility issues are not offset by strong operating or service-quality scores.

Hard gatekeeper checks include clear ownership or operation rights, no major legal dispute, operating history of around 3 years or more, stable operating cash flow, market-based cash-flow source, and distribution capacity. If any hard condition fails, the asset should not be treated as REITs-ready in the prototype, even if it later receives a high operating score.

Capex pressure and continuous-operation risks are treated as warning indicators in the MVP. They are important risk signals, but the current prototype compares them against the sample distribution rather than applying an official regulatory threshold. This avoids inventing a hard official cutoff where the project has not verified one.

The gatekeeper is not an official regulatory conclusion, approval opinion, legal opinion, credit rating, valuation opinion, or investment recommendation. It is a regulatory-style logic layer for portfolio demonstration and analytical screening.

## 100-Point Scoring Layer

The 100-point scoring layer evaluates assets after the Regulatory Gatekeeper layer. It measures relative portfolio strength across cash-flow capacity, tourism operating quality, service quality, risk management and resilience, and data maturity.

The scoring model uses peer min-max normalization for continuous indicators. Positive indicators score higher when the raw value is higher within the peer sample. Negative indicators, such as risk indicators and complaint rates, score higher when the raw value is lower within the peer sample. If all peer values are the same, the model assigns a neutral score of 50 for that indicator.

This peer-normalized approach avoids inventing arbitrary hard thresholds for the scoring layer. Hard pass/fail logic belongs in the Regulatory Gatekeeper. The 100-point score is a relative analytical score, not an eligibility override.

Missing indicators are excluded from the module average rather than forcing a zero score or fabricated value. This keeps the model transparent: unavailable data lowers confidence and is disclosed in explanations, but it does not silently distort the average with made-up inputs.

The scoring layer differs from the Regulatory Gatekeeper in purpose. The gatekeeper asks whether key suitability conditions appear to be met in a prototype pre-screen. The scoring model asks how assets compare against each other on available operating, financial, risk, service, and data-maturity metrics. A failed gatekeeper result should not be treated as REITs-ready merely because the 100-point score is high.

The score is not an official credit rating, investment recommendation, valuation opinion, or regulatory conclusion. It is for portfolio demonstration and asset management support only.

## Scoring Modules

The default expert-weighted model uses five modules:

| Module | Weight |
| --- | ---: |
| A. REITs Cash Flow and Distribution Capacity | 30 |
| B. Tourism Operating Quality | 25 |
| C. Service Quality and Online Reputation | 15 |
| D. Risk Management and Resilience | 15 |
| E. Data Maturity and Smart Operation | 15 |

## Reference Basis

The scoring framework is based on established regulatory, industry, and academic frameworks, including China public infrastructure REITs requirements, REITs cash-flow concepts such as FFO/AFFO, real estate performance measurement guidance, DCF valuation guidance, tourism statistics, service-quality frameworks, enterprise risk management frameworks, climate disclosure frameworks, and data maturity standards.

The project reference library is maintained in `config/model_references.yml`.

## Data and Simulation Policy

Demo data may include simulated values. Simulated values must be clearly labeled at field level, row level, or dataset level before they are used in a dashboard, report, or model output.

The model should distinguish among public disclosure data, publicly collected data, survey data, simulated data, and manual assessment data. Indicator-level source requirements are maintained in `config/indicator_framework.yml`.

## Reliability and Validity

Model reliability and validity should be tested through:

- AHP consistency ratio for expert weighting exercises.
- Cronbach's alpha where survey-scale data is used.
- Sensitivity analysis for score and rating robustness under weight or assumption changes.
- Spearman rank stability analysis for ranking robustness across weighting modes, data samples, or update periods.

The Python implementation in `src/reliability_validity.py` provides these checks where the required data is available and returns clear not-applicable messages where inputs, such as an AHP pairwise matrix, have not been provided.

## Model Reliability, Validity, and Robustness

The model validity layer explains and tests the credibility of the scoring framework without claiming official approval or investment validity.

Content validity is supported by mapping each indicator to reference frameworks, reference notes, validation methods, and reliability methods in `config/indicator_framework.yml`. This makes the framework auditable and helps show why each indicator belongs in the model.

Construct validity is addressed through the five-module structure. The modules correspond to the intended constructs of REIT cash flow and distribution capacity, tourism operation, service quality and online reputation, risk management and resilience, and data maturity and smart operation.

Reliability testing uses Cronbach's Alpha only for survey-scale or multi-item service-quality dimensions, such as tangibles, reliability, responsiveness, assurance, and empathy. Cronbach's Alpha should not be applied to ordinary financial ratios or unrelated operating metrics.

AHP consistency applies only when expert pairwise comparison matrices are used to derive weights. If no pairwise matrix is provided, the AHP consistency check is not run.

Robustness is tested through module-weight sensitivity analysis. The analysis randomly perturbs module weights, re-normalizes them to sum to 100, recalculates total scores, and checks whether asset rankings remain stable using Spearman rank correlation and identical-ranking frequency.

The demo data and small sample size limit statistical inference. Validity outputs should be interpreted as model-governance diagnostics for a portfolio prototype, not as proof that the model is an official rating system, regulatory conclusion, valuation opinion, or investment recommendation.

## Scenario Simulation Layer

The Scenario Simulation layer estimates how selected operational and financial shocks could affect tourism asset cash flow, AFFO proxy, distribution coverage, and the REITs suitability score. It is a stress-test style analytical tool for portfolio demonstration, not a forecast.

Scenario outputs are simulated estimates. They should not be interpreted as official asset forecasts, valuation conclusions, investment recommendations, or regulatory conclusions.

The simulator applies shocks that are relevant for tourism-related consumption infrastructure assets:

- Revenue decline can reflect demand weakness, temporary closures, pricing pressure, or lower visitor spending.
- Visitor volume decline can affect scenic areas, resort complexes, and other volume-driven assets.
- Occupancy and ADR declines are relevant for hotel and accommodation assets.
- Operating cost increases can pressure NOI and operating cash flow.
- Maintenance CAPEX increases can reduce AFFO proxy and distribution capacity.
- OTA score decline can represent online reputation pressure and weaker service perception.

The simulator uses latest-year demo data for the selected asset. It calculates revenue after shock, visitor volume after shock, occupancy and ADR after shock, RevPAR after shock, operating cost after shock, NOI after shock, operating cash flow after shock, maintenance CAPEX after shock, AFFO proxy after shock, and distribution coverage after shock.

To estimate score impact, the simulator creates a scenario-adjusted copy of the latest-year merged scoring dataframe in memory, replaces the selected asset values with simulated values, and recalculates the score through the existing scoring model. This preserves the scoring methodology and avoids creating a separate scenario scoring formula.

Limitations are important. The MVP uses demo data that may be simulated or mixed, simplified financial relationships, and peer-relative score recalculation. The simulator does not model taxes, financing structures, lease terms, seasonality calendars, insurance recoveries, management actions, regulatory approvals, or investor pricing.

## Automatic Report Generation Layer

The automatic report generation layer creates deterministic Markdown asset reports from the existing backend outputs. It integrates Regulatory Gatekeeper results, REITs suitability scoring, model validity notes, risk metrics, and optional scenario simulation results.

The report generator is rule-based and does not use external LLM APIs. Text sections, suggestions, and conclusions are generated from transparent conditions such as gatekeeper warnings, weakest scoring module, sample-relative risk categories, distribution coverage, and scenario severity.

Generated reports are for portfolio demonstration and decision-support communication only. They are not investment advice, credit ratings, valuation opinions, or official regulatory conclusions. Demo reports may include simulated or mixed values and should be read together with data source notes.

## Limitations

The framework is an analytical aid. It depends on the quality, comparability, and timeliness of input data. Legal, tax, regulatory, valuation, and investment conclusions require specialist review and source-document due diligence.

# Data dictionary

Generated from the reviewed exact source mappings and explicit formulas. The machine-readable CSV contains source labels, dates, types and missing-value policy.

| column | unit | description_or_formula |
| --- | --- | --- |
| lsoa_code | identifier / official label | Source value |
| lsoa_name | identifier / official label | Source value |
| district_code | identifier / official label | Source value |
| district_name | identifier / official label | Source value |
| study_role | category | main for Leeds/Bradford; comparison for Wakefield; configured in study.yml |
| access_pt | DfT score 0–100 | Primary modelled public-transport connectivity across purposes; higher is better; not employment-only accessibility |
| access_sustainable | DfT score 0–100 | DfT Overall score: sustainable modes, excludes driving; approximately 52% PT, 40% walking, 8% cycling |
| access_walking | DfT score 0–100 | Source value |
| access_cycling | DfT score 0–100 | Source value |
| access_driving | DfT score 0–100 | Source value |
| employment_overall | DfT score 0–100 | Source value |
| business_pt_unresolved | DfT score 0–100 | Ambiguous original Business (public transport) label; retained for audit only and excluded from analysis/interpretation |
| households_total | households | Source value |
| households_no_car | households | Source value |
| adults_16plus | count of people | Source value |
| active_16plus | count of people | Sum of the listed non-overlapping source categories; missing if any category is missing |
| employed_16plus | count of people | Sum of the listed non-overlapping source categories; missing if any category is missing |
| unemployed_16plus | count of people | Sum of the listed non-overlapping source categories; missing if any category is missing |
| inactive_16plus | count of people | Source value |
| qualifications_16plus | count of people | Source value |
| no_qualifications | count of people | Source value |
| level4plus | count of people | Source value |
| population_total | count of people | Source value |
| residents_per_km2 | usual residents / square kilometre | Source value |
| age_total | count of people | Source value |
| age_0_14 | count of people | Sum of the listed non-overlapping source categories; missing if any category is missing |
| age_65plus | count of people | Sum of the listed non-overlapping source categories; missing if any category is missing |
| income_rate | published rate (0–1) | Source value |
| income_population | count of people | Publisher's mid-2022 resident population denominator; weighting published shrunken scores does not reconstruct an exact numerator |
| imd_district_code | identifier / official label | Source value |
| imd_district_name | identifier / official label | Source value |
| no_car_pct | percent | 100 × households_no_car / households_total; missing if denominator is zero/missing or numerator missing |
| economic_activity_pct | percent | 100 × active_16plus / adults_16plus; missing if denominator is zero/missing or numerator missing |
| employment_16plus_pct | percent | 100 × employed_16plus / adults_16plus; missing if denominator is zero/missing or numerator missing |
| unemployment_pct | percent | 100 × unemployed_16plus / active_16plus; missing if denominator is zero/missing or numerator missing |
| inactivity_pct | percent | 100 × inactive_16plus / adults_16plus; missing if denominator is zero/missing or numerator missing |
| no_qualifications_pct | percent | 100 × no_qualifications / qualifications_16plus; missing if denominator is zero/missing or numerator missing |
| level4plus_pct | percent | 100 × level4plus / qualifications_16plus; missing if denominator is zero/missing or numerator missing |
| age_0_14_pct | percent | 100 × age_0_14 / age_total; missing if denominator is zero/missing or numerator missing |
| age_65plus_pct | percent | 100 × age_65plus / age_total; missing if denominator is zero/missing or numerator missing |
| income_pct | percent | 100 × income_rate; published modelled/shrunken rate, not household income |
| priority_eligible | boolean | All three core indicators are observed; no missing-value imputation |
| poor_access_percentile | fraction 0–1 | 1 − empirical mid-percentile(access_pt) in the selected reference |
| no_car_percentile | fraction 0–1 | Empirical mid-percentile(no_car_pct) in the selected reference |
| income_need_percentile | fraction 0–1 | Empirical mid-percentile(income_rate) in the selected reference |
| priority_score | review score 0–100 | 100 × weighted mean of the three adverse percentile standings; baseline equal weights |
| triple_priority | nullable boolean | All three adverse percentiles ≥ 1 − tail_fraction; baseline pooled quartiles; NA if ineligible |
| score_rank | rank | Descending priority_score rank, minimum rank for ties; 1 is highest review score |
| top_score_band | nullable boolean | Score ≥ (1 − tail_fraction) quantile of eligible scores; includes all threshold ties |
| triple_frequency | fraction 0–1 | Share of 27 documented sensitivity scenarios meeting all-three-tail rule; weight repeats leave this rule unchanged |
| top_score_frequency | fraction 0–1 | Share of 27 scenarios in their highest score band; not a confidence probability |
| best_score_rank | rank | Minimum descending score rank across documented scenarios |
| worst_score_rank | rank | Maximum descending score rank across documented scenarios |
| assessed_scenarios | count | Number of sensitivity scenarios with a non-missing score |
| income_rate_peer_bin | zero-based bin | Pooled empirical tercile bin of income_rate; duplicate cut edges collapse; actual edges in data_quality.json |
| residents_per_km2_peer_bin | zero-based bin | Pooled empirical tercile bin of residents_per_km2; duplicate cut edges collapse; actual edges in data_quality.json |
| age_0_14_pct_peer_bin | zero-based bin | Pooled empirical tercile bin of age_0_14_pct; duplicate cut edges collapse; actual edges in data_quality.json |
| age_65plus_pct_peer_bin | zero-based bin | Pooled empirical tercile bin of age_65plus_pct; duplicate cut edges collapse; actual edges in data_quality.json |
| peer_group | group identifier | Joint pooled tercile bins of income, density, age 0–14 share and age 65+ share |
| peer_count | LSOAs | Number of eligible areas in the peer group, including this area |
| peer_districts | districts | Distinct districts represented in the peer group |
| peer_supported | boolean | Peer group has ≥5 areas and ≥2 districts; configurable minimum |
| peer_median_access | DfT score | Unweighted median access_pt for the peer group, including this area |
| peer_access_gap | DfT score points | access_pt − peer_median_access; missing for unsupported groups; descriptive, not causal |
| sustainable_triple_priority | nullable boolean | Baseline all-three-tail rule with access_sustainable replacing access_pt |
| sustainable_priority_score | review score 0–100 | Baseline score with access_sustainable replacing access_pt |

# Findings: Access to Opportunity

Built from the verified official inputs at 2026-10-11T16:58:45.600259+00:00. All 1,015 eligible geographic areas remain in the dataset; 1,015 have the three core indicators.

## 1. Compare the whole distribution, not a city-centre example

| district_name | neighbourhoods | p10_access | median_access | p90_access | unweighted_mean_access | population_weighted_mean_access |
| --- | --- | --- | --- | --- | --- | --- |
| Bradford | 312 | 59.53 | 71.60 | 80.14 | 70.53 | 70.89 |
| Leeds | 488 | 61.17 | 73.59 | 81.97 | 72.28 | 72.63 |
| Wakefield | 215 | 51.64 | 64.18 | 73.99 | 63.41 | 63.53 |

Evidence: [district_summary.csv](../data/processed/district_summary.csv), calculated by [district_summary.sql](../sql/district_summary.sql). The 10th–90th percentile interval describes neighbourhood variation, not a confidence interval. Population-weighted connectivity uses Census 2021 usual residents; the unweighted mean treats each neighbourhood equally.

Leeds has the highest median public-transport connectivity score (73.59); Wakefield has the lowest (64.18). These are model scores from the 2025 release, not journey times.

## 2. Car non-availability and income need are distinct indicators

| district_name | household_no_car_pct | mean_neighbourhood_no_car_pct | mean_neighbourhood_income_pct | income_denominator_weighted_pct | unemployment_pct |
| --- | --- | --- | --- | --- | --- |
| Bradford | 27.59 | 27.61 | 34.68 | 35.73 | 7.59 |
| Leeds | 28.72 | 28.13 | 24.26 | 24.57 | 6.75 |
| Wakefield | 22.82 | 22.67 | 25.49 | 25.57 | 4.92 |

Household no-car percentage is the ratio of summed TS045 counts, using households as denominator. The neighbourhood mean is a different summary. Income percentages derive from the published income score; the denominator-weighted mean uses the publisher's mid-2022 population, is approximate after shrinkage, and is not an exact deprived-person count. Unemployment uses economically active people aged 16+, including active students. Evidence: [district_summary.csv](../data/processed/district_summary.csv).

## 3. Overlapping disadvantage depends on the definition

With the configured pooled comparison and adverse tails of 25.00%, **3 neighbourhoods** combine low public-transport connectivity, high no-car household share and high income need. The baseline is specified in `config/study.yml`; its weights are `{'poor_access': 1, 'no_car': 1, 'income_need': 1}`.

| district_name | priority_eligible | triple_priority_count |
| --- | --- | --- |
| Bradford | 312.00 | 1.00 |
| Leeds | 488.00 | 0.00 |
| Wakefield | 215.00 | 2.00 |

All baseline intersection members (official LSOA names):

| lsoa_code | lsoa_name | district_name | access_pt | no_car_pct | income_pct | triple_frequency |
| --- | --- | --- | --- | --- | --- | --- |
| E01010718 | Bradford 012C | Bradford | 60.21 | 44.17 | 50.20 | 0.78 |
| E01011792 | Wakefield 039D | Wakefield | 59.71 | 39.74 | 66.30 | 0.56 |
| E01011811 | Wakefield 011E | Wakefield | 56.27 | 39.82 | 58.80 | 0.78 |

The composite is a separate, compensatory review score: 100 × the weighted mean of adverse percentile standings for connectivity, no-car share and income need. A high score can occur without all three indicators being in their adverse tails. It is not an official index, a probability, or an estimate of individual hardship.

Ten highest baseline composite scores, with every constituent visible (the complete ranking is exported):

| lsoa_code | lsoa_name | district_name | access_pt | no_car_pct | income_pct | priority_score | triple_priority | top_score_frequency |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| E01011811 | Wakefield 011E | Wakefield | 56.27 | 39.82 | 58.80 | 88.01 | True | 1.00 |
| E01011792 | Wakefield 039D | Wakefield | 59.71 | 39.74 | 66.30 | 87.47 | True | 1.00 |
| E01010718 | Bradford 012C | Bradford | 60.21 | 44.17 | 50.20 | 85.07 | True | 1.00 |
| E01011780 | Wakefield 027B | Wakefield | 66.05 | 44.96 | 61.60 | 84.20 | False | 1.00 |
| E01010635 | Bradford 047C | Bradford | 67.80 | 49.24 | 61.20 | 83.50 | False | 1.00 |
| E01010612 | Bradford 052A | Bradford | 70.34 | 54.64 | 77.10 | 83.17 | False | 1.00 |
| E01011745 | Wakefield 001D | Wakefield | 57.76 | 35.51 | 52.70 | 82.94 | False | 1.00 |
| E01011747 | Wakefield 003C | Wakefield | 63.04 | 36.02 | 61.70 | 82.76 | False | 1.00 |
| E01010821 | Bradford 052D | Bradford | 68.12 | 45.42 | 66.90 | 82.46 | False | 1.00 |
| E01011624 | Leeds 072D | Leeds | 69.57 | 46.56 | 59.60 | 80.33 | False | 1.00 |

Evidence: [neighbourhoods.csv](../data/processed/neighbourhoods.csv); fields `triple_priority`, `priority_score`, `triple_frequency` and `top_score_frequency`. Frequency means the fraction of documented scenarios selecting the area, not confidence that it needs intervention.

## 4. Sensitivity is part of the result

Across 27 threshold/reference/weight scenarios, all-three-tail membership ranges from 1 to 24 neighbourhoods. Membership in the highest composite-score band has Jaccard overlap with baseline ranging from 0.44 to 1.00 (1 means identical sets).

| comparison_group | tail_fraction | triple_count | top_score_count | triple_jaccard_vs_baseline | score_band_jaccard_vs_baseline |
| --- | --- | --- | --- | --- | --- |
| pooled | 0.20 | 1 | 203 | 0.33 | 0.80 |
| pooled | 0.25 | 3 | 254 | 1.00 | 1.00 |
| pooled | 0.33 | 19 | 339 | 0.16 | 0.75 |
| district | 0.20 | 1 | 203 | 0.33 | 0.69 |
| district | 0.25 | 3 | 254 | 0.20 | 0.73 |
| district | 0.33 | 16 | 339 | 0.19 | 0.72 |
| main_reference | 0.20 | 1 | 203 | 0.33 | 0.80 |
| main_reference | 0.25 | 4 | 255 | 0.75 | 0.92 |
| main_reference | 0.33 | 24 | 338 | 0.12 | 0.75 |

Weights affect the composite, not the independent all-three-tail rule. Ties receive the same percentile; selected counts need not be exact percentages. Main-reference scenarios use Leeds and Bradford to define relative standing while scoring Wakefield against that reference. District scenarios measure relative disadvantage within each district. Empty-set Jaccard is missing, not a perfect match.

Replacing the primary public-transport measure with DfT's sustainable-mode `Overall` score gives 3 all-three-tail areas under the same baseline definition; overlap with baseline is 1.00. No driving-versus-public-transport score difference is calculated.

Evidence: [sensitivity.csv](../data/processed/sensitivity.csv) and `sustainable_triple_priority` in [neighbourhoods.csv](../data/processed/neighbourhoods.csv).

## 5. Associations and comparable-neighbourhood context

| district | variable | complete_pairs | spearman_rho |
| --- | --- | --- | --- |
| All study districts | no_car_pct | 1015 | 0.70 |
| All study districts | income_pct | 1015 | 0.42 |
| All study districts | unemployment_pct | 1015 | 0.60 |
| Bradford | no_car_pct | 312 | 0.70 |
| Bradford | income_pct | 312 | 0.64 |
| Bradford | unemployment_pct | 312 | 0.73 |
| Leeds | no_car_pct | 488 | 0.77 |
| Leeds | income_pct | 488 | 0.43 |
| Leeds | unemployment_pct | 488 | 0.61 |
| Wakefield | no_car_pct | 215 | 0.53 |
| Wakefield | income_pct | 215 | 0.29 |
| Wakefield | unemployment_pct | 215 | 0.36 |

Spearman correlations describe monotonic area-level associations; they are not individual-level relationships or transport effects. Pooled associations can differ from within-district patterns. Evidence: [associations.csv](../data/processed/associations.csv).

908 of 1015 areas have supported peer comparisons: joint quantile bins (3 requested per variable) of income need, density, age 0–14 share and age 65+ share, at least 5 areas and two districts per group. The difference from a peer-group median includes the area itself; coarse bins leave residual differences and do not create matched causal controls.

Largest negative connectivity differences within supported peer groups:

| lsoa_name | district_name | access_pt | peer_count | peer_districts | peer_median_access | peer_access_gap |
| --- | --- | --- | --- | --- | --- | --- |
| Wakefield 034E | Wakefield | 31.86 | 86 | 3 | 61.16 | -29.30 |
| Bradford 023E | Bradford | 37.23 | 9 | 3 | 66.40 | -29.17 |
| Wakefield 034F | Wakefield | 33.21 | 86 | 3 | 61.16 | -27.95 |
| Wakefield 041A | Wakefield | 44.37 | 11 | 3 | 70.65 | -26.28 |
| Wakefield 041B | Wakefield | 48.68 | 7 | 3 | 72.89 | -24.21 |
| Wakefield 035D | Wakefield | 43.60 | 9 | 3 | 66.40 | -22.80 |
| Wakefield 038A | Wakefield | 39.99 | 25 | 3 | 62.63 | -22.64 |
| Wakefield 035A | Wakefield | 48.38 | 30 | 3 | 69.87 | -21.49 |

Evidence: [peer_groups.csv](../data/processed/peer_groups.csv), including each group's actual covariate ranges, and `peer_*` fields in [neighbourhoods.csv](../data/processed/neighbourhoods.csv).

## Interpretation and next step

These results identify areas to investigate with residents and transport evidence, not a validated funding allocation. LSOAs conceal variation; household car availability is not personal access to a car. Census 2021 is pandemic-era; income inputs are mainly March 2024/mid-2022; connectivity is labelled Q4 2024 with mixed input dates. DfT assumes timetabled services and does not measure reliability, affordability or all accessibility needs. Existing jobs are not vacancies. No causal transport–unemployment claim or new 30/45/60-minute job estimate is made.

Read [feasibility.md](feasibility.md), [data_quality.md](data_quality.md), [methodology.md](../docs/methodology.md) and [source_register.csv](../metadata/source_register.csv) alongside the results. The DfT workbook licence cell remains TBA despite OGL terms on the GOV.UK guidance; originals are not bundled in Git.

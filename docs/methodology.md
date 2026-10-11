# Methodology

## Question and study universe

The question is where relatively weak modelled public-transport connectivity coexists with high household car non-availability and high income deprivation. Leeds and Bradford are the main study; Wakefield is a descriptive comparison. No district is a causal control group.

The authoritative ONS LSOA21–ward24–LAD24 best-fit lookup defines all eligible neighbourhoods. Verified codes are Leeds E08000035 (488), Bradford E08000032 (312) and Wakefield E08000036 (215). Names come from ONS; numerical LSOA names should not be presented as named communities without further evidence. The core uses LSOA 2021 throughout and no 2011 correspondence. Boundaries are December 2021 BGC V5, generalised to 20 metres and clipped to the coastline, requested in EPSG:4326. They support neighbourhood maps, not precise street boundaries.

## What accessibility means here

The inspected DfT workbook has Metadata, OA, LSOA, LAD and RGN sheets, with 35 measures at LSOA level. The primary field is exactly `Overall (public transport)`: connectivity across multiple destination purposes. DfT aggregates OA scores to LSOAs using population weights. The 2025 publication labels its reference Q4 2024; destination inputs also include Q1 2025, jobs use provisional BRES 2023 and travel preferences use NTS 2011–2020.

A score of 70 is not a 70th percentile, 70 minutes, or 70% of jobs. DfT scales scores relative to the best origin. Mode scores are independently scaled. We compare neighbourhoods within each measure, without subtracting PT and driving scores to imply a travel-time gap.

Employment-specific fields genuinely exist for walking, cycling, driving and published overall. The PT field is instead `Business (public transport)`. Its interpretation is unresolved, so the pipeline retains that exact evidence and excludes it from employment claims. We do not rename the primary overall-PT measure employment accessibility. The final `Overall` field explicitly combines sustainable modes, excluding driving (approximately 52% PT, 40% walking, 8% cycling); it provides a separate sensitivity check.

The methodology assumes scheduled services run on time, samples departure times and combines destinations/preferences into a score. It does not measure reliability, affordability, wheelchair accessibility or individual job suitability. Its internal 60-minute model cutoff does not turn our score into a count of jobs reachable within 60 minutes.

## Numerators, denominators and units

| Indicator | Numerator | Denominator | Interpretation |
|---|---|---|---|
| No-car households (%) | TS045 no cars or vans in household | TS045 all households | Household availability, not personal car access |
| Economic activity (%) | TS066 active nonstudents + active full-time students | TS066 all usual residents aged 16+ | No upper age restriction |
| Employment, age 16+ (%) | Employed components of both active groups | TS066 all aged 16+ | Not the usual 16–64 headline employment rate |
| Unemployment (%) | Unemployed components of both active groups | All economically active aged 16+ | Includes active students |
| Inactivity (%) | TS066 economically inactive | TS066 all aged 16+ | Includes retirement and other categories |
| No qualifications / level 4+ (%) | TS067 corresponding category | TS067 own all-aged-16+ total | Do not borrow TS066's denominator |
| Children / older residents (%) | TS007a ages 0–14 / ages 65+ | TS007a own all-age total | Grouped-age table supports LSOAs; TS007 single-year bulk does not |
| Income deprivation (%) | Published `Income Score (rate)` × 100 | Already a published rate | Benefit-based low-income measure, not median income |
| Density | TS006 published population density | Residents per square kilometre | Do not recompute using generalised map polygon area |

Each percentage is `100 × numerator / denominator`. Missing components propagate to the sum; a zero or missing denominator gives missing, never zero. Negative counts, infinite values and numerators above their own denominator fail. Nested TS066 categories are not summed twice. Partition audits allow a documented five-person difference for disclosure control; observed activity partitions in this build differ by zero. Cross-table population totals can differ under Census disclosure control, so each rate uses its own table universe.

The 2025 income domain uses mainly March 2024 administrative benefit data and a bespoke mid-2022 denominator. It includes adjustments and shrinkage. It is not a 2025 census of exact deprived-person counts. Overall IMD includes related concepts such as geographical barriers; using the income domain avoids introducing a transport component into the need score. Employment and qualifications remain descriptive context, not extra weights on economic need.

## Geography and missingness checks

A left join from the full official lookup retains every eligible LSOA. Each source is checked for unique, nonmissing codes, expected code format, exact source labels and one-to-one cardinality. The audit records matched areas, unmatched codes and national rows outside the study. Outside-study rows are expected, not failed joins. ONS district assignments must agree with deprivation metadata where observed. Polygon coverage must equal the exact study code set; empty, invalid or duplicate geometries fail the build.

This release has all three core indicators for all 1,015 areas. If a future release lacks one, the area remains visible but receives no core score or false negative flag; eligibility and missingness are reported. The dashboard's grey map layer distinguishes missing values and unsupported peer comparisons from low scores. It currently has 107 unsupported peer differences, which are not imputed.

## Summaries: two questions, two weightings

An unweighted mean or median describes a typical **neighbourhood**. A Census-population-weighted mean of the LSOA connectivity score describes the score attached to a typical **resident's neighbourhood**; it is not an individual's measured journey. It uses Census 2021 population consistently, even though DfT's own underlying aggregation uses its methodology's populations.

The district no-car percentage is `100 × sum(no-car households) / sum(households)`, not a population-weighted average. The neighbourhood mean of no-car percentages is reported separately. All weighted calculations use only pairs where both the value and its positive weight are observed. SQL expresses these denominator filters explicitly and tests compare the actual outputs against independent calculations.

Income population-weighting uses the published deprivation denominator. Because of the publisher's adjustments and shrinkage, this is labelled a weighted mean of published scores, not an exact deprived-person estimate. Distribution plots and 10th–90th percentiles show within-district variation; they are not confidence intervals.

## Two transparent priority definitions

The baseline, specified in `config/study.yml`, uses equal weights, all eligible study areas as reference, and adverse quartiles. No threshold was chosen to force a particular neighbourhood into the result.

For a value x in a reference group of n nonmissing values, define its mid-percentile as:

`p(x) = (number below x + 0.5 × number equal to x) / n`

Ties therefore receive identical treatment. Adverse standing is `1 − p(connectivity)`, `p(no-car percentage)` and `p(income rate)`. Percentiles are based on complete core cases, not separate changing universes.

1. **All-three-tail flag:** all three adverse standings must be at least `1 − tail_fraction` (0.75 at baseline). It is an intersection; one extreme indicator cannot compensate for a favourable one.
2. **Review score:** `100 × (w_access × adverse_access + w_car × adverse_car + w_income × adverse_income) / sum(weights)`. This is compensatory: a strong value on one indicator can offset another. We retain the constituents alongside it and describe it as a review score, not an official deprivation index.

Score ranks give tied scores the same minimum rank. The highest-score band includes values at or above the empirical `(1 − tail)` quantile of scores across the full study, including in district-reference scenarios. Equal values can make selected counts differ from an exact percentage. Nonnegative weights must sum to a positive number; even a zero-weight indicator must be observed for eligibility, keeping the comparison universe fixed.

## Sensitivity and reference groups

The grid crosses three tails (20%, 25%, one-third), three references and three weight sets (1:1:1, 2:1:1, 1:1:2): 27 scenarios.

- **Pooled:** all study areas establish percentile standings.
- **Within district:** each district establishes its own standings. This answers relative local disadvantage, not absolute equivalence between districts.
- **Main-study reference:** Leeds and Bradford establish standings; Wakefield is evaluated against the same reference. Values outside its observed range can have standings of zero or one.

Weights change the composite but cannot change the all-three-tail rule. Its 27-scenario frequency repeats each threshold/reference result across the three weight settings; this does not provide extra independent evidence. The scenario frequency is a descriptive fraction of choices, not a confidence probability. Jaccard overlap is intersection size divided by union size; two empty sets produce missing rather than a perfect score. DfT sustainable-mode `Overall` is examined separately using the same baseline rule.

The district sidebar changes the display, not the chosen percentile reference. The dashboard labels the fixed full-study sensitivity grid separately from its live custom-weight calculations.

## Comparable areas and associations

We form pooled terciles independently for income rate, population density, age 0–14 percentage and age 65+ percentage, then intersect the four bins. Duplicate quantile edges are dropped rather than arbitrarily splitting tied values. Groups require at least five neighbourhoods and representation from two districts. The output preserves bin edges, group sizes, district coverage and actual covariate ranges so readers can inspect remaining heterogeneity.

The reported gap is the area's connectivity minus its supported group median; the median includes the area itself. It is a simple, understandable comparison, not a regression residual, exact matching or a causal estimate. Sparse groups are suppressed; broad bins can conceal important differences. This build supports 908 areas. Narrower bins or exact similarity matching would change overlap and require another documented sensitivity analysis.

Spearman correlations describe monotonic associations across complete pairs, pooled and separately within districts. No p-values imply independent random sampling: this is the full selected geography, with spatial dependence and model uncertainty. Positive area-level correlations do not establish individual behaviour or causal direction. Transport supply, housing, urban form, self-selection and economic need may be related in several ways.

## Reproducibility and limits

Original bytes have SHA-256 names and are never overwritten by a refresh. Reviewed mappings pin exact data checksums; a changed upstream file stops locked reproduction for investigation. A build manifest records input and output hashes, configuration digest and build time. ODS extraction checks both its source and cached output hashes. Dynamic landing pages and methodological extracts are retained as provenance, but page-layout changes do not invalidate unchanged numerical inputs.

Different years remain explicitly labelled. Census 2021 was collected during the pandemic; model inputs and deprivation periods differ. LSOAs conceal variation, boundaries and denominators are choices, and scheduled services miss lived reliability and cost. These uncertainties are not quantified by scenario frequencies. There is no claim that transport causes unemployment, that existing jobs are vacancies, or that the score counts jobs within new time thresholds. Historical JTS and detailed bus routing require separate methods and remain deferred.

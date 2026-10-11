# Data-quality report

Current run: 2026-10-11T16:58:45.600259+00:00

**1015 rows; 0 duplicate LSOA codes; 1015 valid polygons.** ONS lookup verifies all three requested district identities. Boundary CRS: EPSG:4326; LSOA 2021 BGC V5; 20 m generalised, coastline clipped.

## Geographic joins

| table | source_rows | matched | unmatched | outside_study_rows | duplicate_codes | cardinality |
| --- | --- | --- | --- | --- | --- | --- |
| access | 35672 | 1015 | 0 | 34657 | 0 | one_to_one |
| cars | 35672 | 1015 | 0 | 34657 | 0 | one_to_one |
| activity | 35672 | 1015 | 0 | 34657 | 0 | one_to_one |
| qualifications | 35672 | 1015 | 0 | 34657 | 0 | one_to_one |
| population | 35672 | 1015 | 0 | 34657 | 0 | one_to_one |
| density | 35672 | 1015 | 0 | 34657 | 0 | one_to_one |
| age | 35672 | 1015 | 0 | 34657 | 0 | one_to_one |
| income | 33755 | 1015 | 0 | 32740 | 0 | one_to_one |

All joins use LSOA 2021 and left-join onto the full official district spine. Outside-study source rows are expected national coverage, not dropped study neighbourhoods. Any missing study codes are listed explicitly in `data_quality.json`. No 2011 codes are silently joined or population weights invented.

## Counts and missingness

Maximum absolute TS066 active+inactive versus total difference: 0 people. Employed+unemployed versus active: 0. The within-table diagnostic tolerance is five people to allow small disclosure-control discrepancies; larger discrepancies stop the build.

Maximum TS066 versus TS067 age-16+ total difference: 10 people. Each rate uses its own table's denominator; cross-table differences are reported, not force-corrected.

Zero denominators: `{"active_16plus": 0, "adults_16plus": 0, "age_total": 0, "households_total": 0, "qualifications_16plus": 0}`.

Missing derived values:

| field | missing |
| --- | --- |
| peer_access_gap | 107 |

A zero or missing denominator gives a missing rate; partial source sums stay missing. Missing core indicators are excluded from scoring, never imputed to zero. Unsupported peer groups retain their raw indicators and receive no peer gap. No sampling confidence intervals are attached to this census/modelled-data description.

## Provenance and uncertainty

Every consumed original is checksum-verified against the reviewed mapping. Source schema changes, duplicate codes, mismatched district identity, invalid geometry, impossible count ratios and incompatible geography stop preparation. See `metadata/source_register.csv` for successful and failed requests, reference periods, licences, retrieval dates and checksums; `metadata/dft_workbook_inspection.json` records the actual workbook sheets.

Source limitations include disclosure control, aggregation, mixed source dates, modelled transport assumptions, uncertainty in future conditions and DfT's unresolved Business/public-transport label and workbook licence metadata. Quantitative model uncertainty is not supplied in the workbook and cannot be fabricated. Sensitivity describes analytical choices, not a confidence interval.

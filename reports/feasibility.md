# Feasibility assessment — inspected official files

Assessment: 10 October 2026. **Proceed with the descriptive core.** This assessment follows acquisition and precedes dashboard development. Originals and SHA-256 checksums are listed in `metadata/source_register.csv`.

| Source | Inspected contents | Decision |
|---|---|---|
| DfT, published September 2025 | 68,164,574-byte ODS; sheets Metadata, OA, LSOA, LAD, RGN. LSOA has 35,672 England/Wales areas and 35 numeric measures. | Use the exact field `Overall (public transport)`, higher meaning better modelled connectivity. |
| Census 2021 Nomis bulk | TS045, TS066, TS067, TS001, TS006 and TS007a ZIPs have explicit LSOA CSV members. TS007 single-year age has no LSOA member. | Use TS007a grouped ages: 0–14 and 65+, without calling the former under-16 counts. |
| English Indices of Deprivation 2025 | Updated File 7 CSV, 33,755 areas; fields `LSOA code (2021)`, `Income Score (rate)`, `Total population: mid 2022`. Technical report §4.3 and Appendix A.2 inspected. | Use income deprivation; exclude overall IMD and geographical barriers from the need score to avoid conceptual overlap. |
| ONS lookup | Authoritative ONS item 686527814d73403e8f0a59c7a28b0c34; LSOA21–ward24–LAD24 best-fit lookup, corrected August 2025. Pagination agrees with the query count. | Verify district identity and full-district membership from actual rows. |
| ONS boundaries | Authoritative ONS item 68515293204e43ca8ab56fa13ae8a547; LSOA December 2021 BGC V5, generalised to 20 m and coastline clipped. | All 1,015 requested polygons acquired. Not suitable for street-level claims. |

Verified codes and complete district coverage: **Leeds E08000035: 488; Bradford E08000032: 312; Wakefield E08000036: 215**. Leeds and Bradford are the main study; Wakefield is a descriptive comparison, not a causal control. No 2011–2021 crosswalk is needed for the core.

## Accessibility decision

Employment-specific fields exist: `Employment (walking)`, `Employment (cycling)`, `Employment (driving)` and `Employment (overall)`. However, the public-transport-purpose field is labelled **`Business (public transport)`**, while the metadata purpose list omits employment. Preserve the source label and exclude this ambiguous field from employment interpretation pending publisher clarification.

`Overall (public transport)` combines purposes. It is **not employment accessibility**, reachable-job counts, travel minutes, reliability or vacancies. It is an appropriate primary indicator for studying household car non-availability. Mode-specific scores may be explored separately; their independently scaled levels must not be subtracted to infer a car/public-transport gap.

DfT's separate `Overall` score excludes driving: the methodology gives approximately 52% public transport, 40% walking and 8% cycling. Use it as a sustainable-mode sensitivity check. Published scores are scaled to the best area, not national percentile ranks. Our subsequent percentile transformation is a separate study-relative ranking.

## Dates, releases and terms

- **DfT:** workbook version 21 August 2025, V1.0.0; release 29 September 2025; stated reference Q4 2024. The methodology additionally describes Q4 2024/Q1 2025 destination inputs, BRES 2023 provisional jobs and NTS 2011–2020 preferences. This is a mixed-input model, not 2026 transport. The supplied publication page links the 2025 workbook and lists no later workbook.
- **Income need:** 2025 publication, File 7 corrected November 2025. Mainly March 2024 benefit data against mid-2022 population denominators, with publisher denominator adjustments and shrinkage. A population-weighted mean of published scores does not reconstruct an exact deprived-person count. The supplied page links updated 2025 files and says they replace 2019.
- **Census:** 21 March 2021, during the pandemic. TS066 covers age 16+, including economically active full-time students. Unemployment uses economically active residents as denominator. Disclosure control can cause small cross-table differences.
- **Geography:** LAD lookup geography May 2024; LSOA 2021 throughout. ONS catalogue search returned BGC V5, BSC V4 and BFC/BFE V10. BGC V5 is the current returned 20 m product; version numbers differ by generalisation product.
- **Licensing:** Nomis reuse terms and GOV.UK guidance state OGL with attribution. DfT's workbook licence cell says **TBA**: retain this discrepancy rather than invent a dataset-specific licence. Raw files are excluded from Git and linked to official downloads. ONS boundaries have ONS/Ordnance Survey rights and linked ONS geography terms.

## Answerable questions

1. How do weak modelled public-transport connectivity, no-car households and income need overlap across all neighbourhoods?
2. How do within-district distributions differ, and how do unweighted and population-weighted district summaries compare?
3. Which areas are in all three adverse tails? Which have high composite scores? These are distinct definitions.
4. How do results change with thresholds, weights, pooled/district/main-study reference groups and sustainable-mode connectivity?
5. Among coarse peer groups with similar income, density and age profiles, where is connectivity relatively low? Report peer sizes, cross-district overlap and remaining heterogeneity.

## Further data required

This design cannot establish transport's causal effect on unemployment, individual circumstances, current vacancies, delays/cancellations, disabled travellers' actual access or jobs reachable in 30/45/60 minutes. Shift-work access needs departure-specific routing. Historical JTS requires a separate reference-year/geography check and is not a comparable trend in the new score. BRES, routing and JTS extensions are deferred until the core is verified.

## Acquisition issues

Initial proxy 403s were resolved after adding official hosts to environment configuration. A GOV.UK CSV-preview link failed while the actual attachment succeeded. Shorter ONS queries resolved a server limit on query length. Failed attempts remain in the register and are never counted as datasets. Exact spatial and tabular join checks are recorded by the subsequent data-quality report.

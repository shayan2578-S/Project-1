"""Generate evidence-linked reports from the current run, not hand-entered claims."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from opportunity.analysis import jaccard


def markdown_table(frame: pd.DataFrame, digits: int = 2) -> str:
    def cell(value):
        if pd.isna(value):
            return "Missing"
        if isinstance(value, (float, np.floating)):
            return f"{value:.{digits}f}"
        return str(value).replace("|", "/").replace("\n", " ")
    rows = ["| " + " | ".join(map(str, frame.columns)) + " |",
            "| " + " | ".join(["---"] * len(frame.columns)) + " |"]
    rows.extend("| " + " | ".join(cell(v) for v in row) + " |" for row in frame.itertuples(index=False, name=None))
    return "\n".join(rows)


def write_reports(root: Path, frame: pd.DataFrame, districts: pd.DataFrame,
                  scenarios: pd.DataFrame, quality: dict) -> None:
    reports = root / "reports"
    output = root / "data/processed"
    study = yaml.safe_load((root / "config/study.yml").read_text())
    definition = study["priority"]
    flags = frame.loc[frame["triple_priority"].fillna(False)]
    sustainable = set(frame.loc[frame["sustainable_triple_priority"].fillna(False), "lsoa_code"])
    baseline = set(flags["lsoa_code"])
    association = pd.read_csv(output / "associations.csv")
    lines = ["# Findings: Access to Opportunity", "",
             f"Built from the verified official inputs at {quality['generated_at']}. All {len(frame):,} eligible geographic areas remain in the dataset; {int(frame['priority_eligible'].sum()):,} have the three core indicators.", "",
             "## 1. Compare the whole distribution, not a city-centre example", "",
             markdown_table(districts[["district_name", "neighbourhoods", "p10_access", "median_access", "p90_access", "unweighted_mean_access", "population_weighted_mean_access"]]), "",
             "Evidence: [district_summary.csv](../data/processed/district_summary.csv), calculated by [district_summary.sql](../sql/district_summary.sql). The 10th–90th percentile interval describes neighbourhood variation, not a confidence interval. Population-weighted connectivity uses Census 2021 usual residents; the unweighted mean treats each neighbourhood equally.", ""]
    ordered = districts.sort_values("median_access", ascending=False)
    lines += [f"{ordered.iloc[0]['district_name']} has the highest median public-transport connectivity score ({ordered.iloc[0]['median_access']:.2f}); {ordered.iloc[-1]['district_name']} has the lowest ({ordered.iloc[-1]['median_access']:.2f}). These are model scores from the 2025 release, not journey times.", "",
              "## 2. Car non-availability and income need are distinct indicators", "",
              markdown_table(districts[["district_name", "household_no_car_pct", "mean_neighbourhood_no_car_pct", "mean_neighbourhood_income_pct", "income_denominator_weighted_pct", "unemployment_pct"]]), "",
              "Household no-car percentage is the ratio of summed TS045 counts, using households as denominator. The neighbourhood mean is a different summary. Income percentages derive from the published income score; the denominator-weighted mean uses the publisher's mid-2022 population, is approximate after shrinkage, and is not an exact deprived-person count. Unemployment uses economically active people aged 16+, including active students. Evidence: [district_summary.csv](../data/processed/district_summary.csv).", "",
              "## 3. Overlapping disadvantage depends on the definition", "",
              f"With the configured {definition['comparison_group']} comparison and adverse tails of {100 * definition['tail_fraction']:.2f}%, **{len(flags)} neighbourhoods** combine low public-transport connectivity, high no-car household share and high income need. The baseline is specified in `config/study.yml`; its weights are `{definition['weights']}`.", "",
              markdown_table(districts[["district_name", "priority_eligible", "triple_priority_count"]]), ""]
    if flags.empty:
        lines += ["The absence of an all-three-tail intersection is a substantive result under this rule, not evidence that nobody faces transport barriers. Wider thresholds and local reference groups are evaluated separately below.", ""]
    else:
        lines += ["All baseline intersection members (official LSOA names):", "",
                  markdown_table(flags[["lsoa_code", "lsoa_name", "district_name", "access_pt", "no_car_pct", "income_pct", "triple_frequency"]].sort_values("lsoa_code")), ""]
    lines += ["The composite is a separate, compensatory review score: 100 × the weighted mean of adverse percentile standings for connectivity, no-car share and income need. A high score can occur without all three indicators being in their adverse tails. It is not an official index, a probability, or an estimate of individual hardship.", "",
              "Ten highest baseline composite scores, with every constituent visible (the complete ranking is exported):", "",
              markdown_table(frame.nlargest(10, "priority_score")[["lsoa_code", "lsoa_name", "district_name", "access_pt", "no_car_pct", "income_pct", "priority_score", "triple_priority", "top_score_frequency"]]), "",
              "Evidence: [neighbourhoods.csv](../data/processed/neighbourhoods.csv); fields `triple_priority`, `priority_score`, `triple_frequency` and `top_score_frequency`. Frequency means the fraction of documented scenarios selecting the area, not confidence that it needs intervention.", "",
              "## 4. Sensitivity is part of the result", "",
              f"Across {len(scenarios)} threshold/reference/weight scenarios, all-three-tail membership ranges from {scenarios['triple_count'].min()} to {scenarios['triple_count'].max()} neighbourhoods. Membership in the highest composite-score band has Jaccard overlap with baseline ranging from {scenarios['score_band_jaccard_vs_baseline'].min():.2f} to {scenarios['score_band_jaccard_vs_baseline'].max():.2f} (1 means identical sets).", "",
              markdown_table(scenarios.loc[scenarios["weights"].eq("equal"), ["comparison_group", "tail_fraction", "triple_count", "top_score_count", "triple_jaccard_vs_baseline", "score_band_jaccard_vs_baseline"]]), "",
              "Weights affect the composite, not the independent all-three-tail rule. Ties receive the same percentile; selected counts need not be exact percentages. Main-reference scenarios use Leeds and Bradford to define relative standing while scoring Wakefield against that reference. District scenarios measure relative disadvantage within each district. Empty-set Jaccard is missing, not a perfect match.", "",
              f"Replacing the primary public-transport measure with DfT's sustainable-mode `Overall` score gives {len(sustainable)} all-three-tail areas under the same baseline definition; overlap with baseline is {jaccard(baseline, sustainable):.2f}. No driving-versus-public-transport score difference is calculated.", "",
              "Evidence: [sensitivity.csv](../data/processed/sensitivity.csv) and `sustainable_triple_priority` in [neighbourhoods.csv](../data/processed/neighbourhoods.csv).", "",
              "## 5. Associations and comparable-neighbourhood context", "",
              markdown_table(association.loc[association["variable"].isin(["no_car_pct", "income_pct", "unemployment_pct"])]), "",
              "Spearman correlations describe monotonic area-level associations; they are not individual-level relationships or transport effects. Pooled associations can differ from within-district patterns. Evidence: [associations.csv](../data/processed/associations.csv).", "",
              f"{quality['peer_supported']} of {len(frame)} areas have supported peer comparisons: joint quantile bins ({study['peers']['quantile_bins']} requested per variable) of income need, density, age 0–14 share and age 65+ share, at least {study['peers']['minimum_group_size']} areas and two districts per group. The difference from a peer-group median includes the area itself; coarse bins leave residual differences and do not create matched causal controls.", ""]
    supported = frame.loc[frame["peer_supported"].fillna(False)]
    if not supported.empty:
        lines += ["Largest negative connectivity differences within supported peer groups:", "",
                  markdown_table(supported.nsmallest(8, "peer_access_gap")[["lsoa_name", "district_name", "access_pt", "peer_count", "peer_districts", "peer_median_access", "peer_access_gap"]]), ""]
    lines += ["Evidence: [peer_groups.csv](../data/processed/peer_groups.csv), including each group's actual covariate ranges, and `peer_*` fields in [neighbourhoods.csv](../data/processed/neighbourhoods.csv).", "",
              "## Interpretation and next step", "",
              "These results identify areas to investigate with residents and transport evidence, not a validated funding allocation. LSOAs conceal variation; household car availability is not personal access to a car. Census 2021 is pandemic-era; income inputs are mainly March 2024/mid-2022; connectivity is labelled Q4 2024 with mixed input dates. DfT assumes timetabled services and does not measure reliability, affordability or all accessibility needs. Existing jobs are not vacancies. No causal transport–unemployment claim or new 30/45/60-minute job estimate is made.", "",
              "Read [feasibility.md](feasibility.md), [data_quality.md](data_quality.md), [methodology.md](../docs/methodology.md) and [source_register.csv](../metadata/source_register.csv) alongside the results. The DfT workbook licence cell remains TBA despite OGL terms on the GOV.UK guidance; originals are not bundled in Git.", ""]
    (reports / "findings.md").write_text("\n".join(lines))
    audits = pd.DataFrame([{**audit, "unmatched": len(audit["unmatched_codes"])} for audit in quality["joins"]])
    missing = pd.DataFrame([{"field": key, "missing": value} for key, value in quality["missing_values"].items() if value])
    qlines = ["# Data-quality report", "", f"Current run: {quality['generated_at']}", "",
              f"**{quality['rows']} rows; {quality['duplicate_codes']} duplicate LSOA codes; {quality['boundary_count']} valid polygons.** ONS lookup verifies all three requested district identities. Boundary CRS: {quality['boundary_crs']}; {quality['boundary_version']}.", "",
              "## Geographic joins", "", markdown_table(audits[["table", "source_rows", "matched", "unmatched", "outside_study_rows", "duplicate_codes", "cardinality"]]), "",
              "All joins use LSOA 2021 and left-join onto the full official district spine. Outside-study source rows are expected national coverage, not dropped study neighbourhoods. Any missing study codes are listed explicitly in `data_quality.json`. No 2011 codes are silently joined or population weights invented.", "",
              "## Counts and missingness", "",
              f"Maximum absolute TS066 active+inactive versus total difference: {quality['active_inactive_partition_max_abs_difference']:g} people. Employed+unemployed versus active: {quality['employment_partition_max_abs_difference']:g}. The within-table diagnostic tolerance is five people to allow small disclosure-control discrepancies; larger discrepancies stop the build.", "",
              f"Maximum TS066 versus TS067 age-16+ total difference: {quality['cross_table_adult_count_max_abs_difference']:g} people. Each rate uses its own table's denominator; cross-table differences are reported, not force-corrected.", "",
              "Zero denominators: `" + json.dumps(quality["zero_denominators"], sort_keys=True) + "`.", "",
              "Missing derived values:", "", markdown_table(missing) if not missing.empty else "None.", "",
              "A zero or missing denominator gives a missing rate; partial source sums stay missing. Missing core indicators are excluded from scoring, never imputed to zero. Unsupported peer groups retain their raw indicators and receive no peer gap. No sampling confidence intervals are attached to this census/modelled-data description.", "",
              "## Provenance and uncertainty", "",
              "Every consumed original is checksum-verified against the reviewed mapping. Source schema changes, duplicate codes, mismatched district identity, invalid geometry, impossible count ratios and incompatible geography stop preparation. See `metadata/source_register.csv` for successful and failed requests, reference periods, licences, retrieval dates and checksums; `metadata/dft_workbook_inspection.json` records the actual workbook sheets.", "",
              "Source limitations include disclosure control, aggregation, mixed source dates, modelled transport assumptions, uncertainty in future conditions and DfT's unresolved Business/public-transport label and workbook licence metadata. Quantitative model uncertainty is not supplied in the workbook and cannot be fabricated. Sensitivity describes analytical choices, not a confidence interval.", ""]
    (reports / "data_quality.md").write_text("\n".join(qlines))

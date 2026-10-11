"""Generate the dictionary from reviewed source mappings and explicit formulas."""
from pathlib import Path
import sys
import json
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from opportunity.reporting import markdown_table

inputs = yaml.safe_load((ROOT / "config/verified_inputs.yml").read_text())
frame = pd.read_parquet(ROOT / "data/processed/neighbourhoods.parquet")
definitions = {}
for table, spec in inputs["tables"].items():
    for column, source_columns in spec["columns"].items():
        if column in definitions:
            continue
        labels = [source_columns] if isinstance(source_columns, str) else source_columns
        definitions[column] = {
            "description_or_formula": "Source value" if len(labels) == 1 else "Sum of the listed non-overlapping source categories; missing if any category is missing",
            "source": table, "source_columns": " + ".join(labels), "reference_period": spec["reference_period"],
            "unit": "count of people",
        }
        if column.endswith("_code") or column.endswith("_name"):
            definitions[column]["unit"] = "identifier / official label"
        elif column.startswith("access_") or column in {"employment_overall", "business_pt_unresolved"}:
            definitions[column]["unit"] = "DfT score 0–100"
        elif column.startswith("households_"):
            definitions[column]["unit"] = "households"
        elif column == "residents_per_km2":
            definitions[column]["unit"] = "usual residents / square kilometre"
        elif column == "income_rate":
            definitions[column]["unit"] = "published rate (0–1)"
definitions["business_pt_unresolved"]["description_or_formula"] = "Ambiguous original Business (public transport) label; retained for audit only and excluded from analysis/interpretation"
definitions["income_population"]["description_or_formula"] = "Publisher's mid-2022 resident population denominator; weighting published shrunken scores does not reconstruct an exact numerator"
definitions["access_sustainable"]["description_or_formula"] = "DfT Overall score: sustainable modes, excludes driving; approximately 52% PT, 40% walking, 8% cycling"
definitions["access_pt"]["description_or_formula"] = "Primary modelled public-transport connectivity across purposes; higher is better; not employment-only accessibility"

rates = {
    "no_car_pct": ("households_no_car", "households_total", "cars"),
    "economic_activity_pct": ("active_16plus", "adults_16plus", "activity"),
    "employment_16plus_pct": ("employed_16plus", "adults_16plus", "activity"),
    "unemployment_pct": ("unemployed_16plus", "active_16plus", "activity"),
    "inactivity_pct": ("inactive_16plus", "adults_16plus", "activity"),
    "no_qualifications_pct": ("no_qualifications", "qualifications_16plus", "qualifications"),
    "level4plus_pct": ("level4plus", "qualifications_16plus", "qualifications"),
    "age_0_14_pct": ("age_0_14", "age_total", "age"),
    "age_65plus_pct": ("age_65plus", "age_total", "age"),
}
for column, (num, den, table) in rates.items():
    definitions[column] = {"description_or_formula": f"100 × {num} / {den}; missing if denominator is zero/missing or numerator missing",
                           "source": table, "source_columns": f"{num}; {den}", "reference_period": inputs["tables"][table]["reference_period"], "unit": "percent"}
derived = {
    "study_role": ("main for Leeds/Bradford; comparison for Wakefield; configured in study.yml", "category"),
    "income_pct": ("100 × income_rate; published modelled/shrunken rate, not household income", "percent"),
    "priority_eligible": ("All three core indicators are observed; no missing-value imputation", "boolean"),
    "poor_access_percentile": ("1 − empirical mid-percentile(access_pt) in the selected reference", "fraction 0–1"),
    "no_car_percentile": ("Empirical mid-percentile(no_car_pct) in the selected reference", "fraction 0–1"),
    "income_need_percentile": ("Empirical mid-percentile(income_rate) in the selected reference", "fraction 0–1"),
    "priority_score": ("100 × weighted mean of the three adverse percentile standings; baseline equal weights", "review score 0–100"),
    "triple_priority": ("All three adverse percentiles ≥ 1 − tail_fraction; baseline pooled quartiles; NA if ineligible", "nullable boolean"),
    "score_rank": ("Descending priority_score rank, minimum rank for ties; 1 is highest review score", "rank"),
    "top_score_band": ("Score ≥ (1 − tail_fraction) quantile of eligible scores; includes all threshold ties", "nullable boolean"),
    "triple_frequency": ("Share of 27 documented sensitivity scenarios meeting all-three-tail rule; weight repeats leave this rule unchanged", "fraction 0–1"),
    "top_score_frequency": ("Share of 27 scenarios in their highest score band; not a confidence probability", "fraction 0–1"),
    "best_score_rank": ("Minimum descending score rank across documented scenarios", "rank"),
    "worst_score_rank": ("Maximum descending score rank across documented scenarios", "rank"),
    "assessed_scenarios": ("Number of sensitivity scenarios with a non-missing score", "count"),
    "peer_group": ("Joint pooled tercile bins of income, density, age 0–14 share and age 65+ share", "group identifier"),
    "peer_count": ("Number of eligible areas in the peer group, including this area", "LSOAs"),
    "peer_districts": ("Distinct districts represented in the peer group", "districts"),
    "peer_supported": ("Peer group has ≥5 areas and ≥2 districts; configurable minimum", "boolean"),
    "peer_median_access": ("Unweighted median access_pt for the peer group, including this area", "DfT score"),
    "peer_access_gap": ("access_pt − peer_median_access; missing for unsupported groups; descriptive, not causal", "DfT score points"),
    "sustainable_triple_priority": ("Baseline all-three-tail rule with access_sustainable replacing access_pt", "nullable boolean"),
    "sustainable_priority_score": ("Baseline score with access_sustainable replacing access_pt", "review score 0–100"),
}
for field in ["income_rate", "residents_per_km2", "age_0_14_pct", "age_65plus_pct"]:
    derived[field + "_peer_bin"] = (f"Pooled empirical tercile bin of {field}; duplicate cut edges collapse; actual edges in data_quality.json", "zero-based bin")
for name, (description, unit) in derived.items():
    definitions[name] = {"description_or_formula": description, "source": "derived; see methodology", "source_columns": "See formula", "reference_period": "Mixed source periods; not a single-year estimate", "unit": unit}
rows = []
for name in frame:
    if name not in definitions:
        raise ValueError(f"Undocumented output column: {name}")
    rows.append({"column": name, "dtype": str(frame[name].dtype), **definitions[name],
                 "geography": "LSOA 2021", "missing_policy": "NA preserved; no zero imputation"})
dictionary = pd.DataFrame(rows)
dictionary.to_csv(ROOT / "metadata/data_dictionary.csv", index=False)
(ROOT / "docs/data_dictionary.md").write_text("# Data dictionary\n\nGenerated from the reviewed exact source mappings and explicit formulas. The machine-readable CSV contains source labels, dates, types and missing-value policy.\n\n" + markdown_table(dictionary[["column", "unit", "description_or_formula"]]) + "\n")
print(f"Documented {len(dictionary)} output fields.")

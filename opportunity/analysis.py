"""Transparent descriptive comparisons. No causal model or machine learning."""
from __future__ import annotations

from itertools import product

import numpy as np
import pandas as pd

CORE = ["access_pt", "no_car_pct", "income_rate"]
WEIGHT_KEYS = ["poor_access", "no_car", "income_need"]


def percentage(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """A missing/zero denominator produces NA; impossible counts fail loudly."""
    numerator, denominator = numerator.astype(float), denominator.astype(float)
    if np.isinf(numerator).any() or np.isinf(denominator).any():
        raise ValueError("Counts must be finite or missing")
    if (numerator.dropna() < 0).any() or (denominator.dropna() < 0).any():
        raise ValueError("Counts cannot be negative")
    if ((numerator > denominator) & numerator.notna() & denominator.notna()).any():
        raise ValueError("Numerator exceeds its own denominator")
    return 100 * numerator.div(denominator.where(denominator > 0))


def derive_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    pairs = {
        "no_car_pct": ("households_no_car", "households_total"),
        "economic_activity_pct": ("active_16plus", "adults_16plus"),
        "employment_16plus_pct": ("employed_16plus", "adults_16plus"),
        "unemployment_pct": ("unemployed_16plus", "active_16plus"),
        "inactivity_pct": ("inactive_16plus", "adults_16plus"),
        "no_qualifications_pct": ("no_qualifications", "qualifications_16plus"),
        "level4plus_pct": ("level4plus", "qualifications_16plus"),
        "age_0_14_pct": ("age_0_14", "age_total"),
        "age_65plus_pct": ("age_65plus", "age_total"),
    }
    for name, (numerator, denominator) in pairs.items():
        result[name] = percentage(result[numerator], result[denominator])
    result["income_pct"] = result["income_rate"] * 100
    result["priority_eligible"] = result[CORE].notna().all(axis=1)
    return result


def mid_percentile(values: pd.Series, reference: pd.Series) -> pd.Series:
    """Empirical mid-distribution: (n less than x + 0.5 n equal to x) / n.

    Ties have equal ranks. This is relative standing, not a probability of need.
    """
    ref = np.sort(reference.dropna().to_numpy(dtype=float))
    if not len(ref):
        return pd.Series(np.nan, index=values.index)
    left = np.searchsorted(ref, values.to_numpy(dtype=float), side="left")
    right = np.searchsorted(ref, values.to_numpy(dtype=float), side="right")
    return pd.Series((left + right) / (2 * len(ref)), index=values.index).where(values.notna())


def prioritise(frame: pd.DataFrame, tail_fraction: float = 0.25,
               comparison_group: str = "pooled", weights: dict | None = None,
               access_column: str = "access_pt") -> pd.DataFrame:
    if not 0 < tail_fraction < 0.5:
        raise ValueError("Tail fraction must be between 0 and 0.5")
    if comparison_group not in {"pooled", "district", "main_reference"}:
        raise ValueError("Unknown comparison group")
    weights = weights or dict.fromkeys(WEIGHT_KEYS, 1.0)
    if set(weights) != set(WEIGHT_KEYS):
        raise ValueError("Supply exactly the three documented indicator weights")
    w = np.array([weights[key] for key in WEIGHT_KEYS], dtype=float)
    if not np.isfinite(w).all() or (w < 0).any() or w.sum() <= 0:
        raise ValueError("Weights must be finite, nonnegative and sum to a positive value")
    result = frame.copy()
    eligible = result[[access_column, "no_car_pct", "income_rate"]].notna().all(axis=1)
    result["priority_eligible"] = eligible
    for key in WEIGHT_KEYS:
        result[key + "_percentile"] = np.nan
    valid = result.loc[eligible]
    groups = valid.groupby("district_code", sort=True) if comparison_group == "district" else [("all", valid)]
    for _, group in groups:
        reference = group.loc[group["study_role"].eq("main")] if comparison_group == "main_reference" else group
        if reference.empty:
            raise ValueError("No eligible reference neighbourhoods")
        result.loc[group.index, "poor_access_percentile"] = 1 - mid_percentile(group[access_column], reference[access_column])
        result.loc[group.index, "no_car_percentile"] = mid_percentile(group["no_car_pct"], reference["no_car_pct"])
        result.loc[group.index, "income_need_percentile"] = mid_percentile(group["income_rate"], reference["income_rate"])
    percentile_columns = [key + "_percentile" for key in WEIGHT_KEYS]
    result["priority_score"] = 100 * result[percentile_columns].mul(w, axis=1).sum(axis=1, min_count=3) / w.sum()
    result["triple_priority"] = pd.Series(pd.NA, index=result.index, dtype="boolean")
    result.loc[eligible, "triple_priority"] = result.loc[eligible, percentile_columns].ge(1 - tail_fraction).all(axis=1)
    # Score ranking and all-three-tail membership are deliberately distinct.
    result["score_rank"] = result["priority_score"].rank(ascending=False, method="min")
    result["top_score_band"] = pd.Series(pd.NA, index=result.index, dtype="boolean")
    result.loc[eligible, "top_score_band"] = result.loc[eligible, "priority_score"].ge(
        result.loc[eligible, "priority_score"].quantile(1 - tail_fraction))
    return result


def jaccard(left: set, right: set) -> float:
    return len(left & right) / len(left | right) if left | right else np.nan


def sensitivity(frame: pd.DataFrame, config: dict, baseline_config: dict | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    baseline = prioritise(frame, **(baseline_config or {}))
    base_set = set(baseline.loc[baseline["triple_priority"].fillna(False), "lsoa_code"])
    base_top = set(baseline.loc[baseline["top_score_band"].fillna(False), "lsoa_code"])
    scenarios, memberships = [], []
    for group, tail, (weight_name, weights) in product(
        config["comparison_groups"], config["tail_fractions"], config["weights"].items()
    ):
        scored = prioritise(frame, tail, group, weights)
        flag = set(scored.loc[scored["triple_priority"].fillna(False), "lsoa_code"])
        top = set(scored.loc[scored["top_score_band"].fillna(False), "lsoa_code"])
        scenario_id = f"{group}|{tail:.6f}|{weight_name}"
        scenarios.append({"scenario": scenario_id, "comparison_group": group, "tail_fraction": tail,
                          "weights": weight_name, "eligible": int(scored["priority_eligible"].sum()),
                          "triple_count": len(flag), "top_score_count": len(top),
                          "triple_jaccard_vs_baseline": jaccard(flag, base_set),
                          "score_band_jaccard_vs_baseline": jaccard(top, base_top)})
        member = scored[["lsoa_code", "triple_priority", "top_score_band", "score_rank"]].copy()
        member["scenario"] = scenario_id
        memberships.append(member)
    long = pd.concat(memberships, ignore_index=True)
    stability = long.groupby("lsoa_code", as_index=False).agg(
        triple_frequency=("triple_priority", "mean"), top_score_frequency=("top_score_band", "mean"),
        best_score_rank=("score_rank", "min"), worst_score_rank=("score_rank", "max"),
        assessed_scenarios=("score_rank", "count"))
    return pd.DataFrame(scenarios), stability


def peer_comparisons(frame: pd.DataFrame, bins: int = 3, minimum: int = 5) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Coarse, pooled peer strata; report coverage and suppress tiny groups.

    Peer differences are descriptive residuals from a group median. They are
    not a controlled causal effect or a claim that peers are identical.
    """
    result = frame.copy()
    fields = ["income_rate", "residents_per_km2", "age_0_14_pct", "age_65plus_pct"]
    eligible = result[fields + ["access_pt"]].notna().all(axis=1)
    bucket_names, edges = [], {}
    for field in fields:
        key = field + "_peer_bin"
        result[key] = pd.Series(pd.NA, index=result.index, dtype="Int64")
        bucket, breaks = pd.qcut(result.loc[eligible, field], q=bins, labels=False, retbins=True, duplicates="drop")
        result.loc[eligible, key] = bucket.astype("Int64")
        bucket_names.append(key)
        edges[field] = breaks.tolist()
    valid = result.loc[eligible].copy()
    valid["peer_group"] = valid[bucket_names].astype(str).agg("/".join, axis=1)
    group = valid.groupby("peer_group", as_index=False).agg(
        peer_count=("lsoa_code", "size"), peer_districts=("district_code", "nunique"),
        peer_median_access=("access_pt", "median"), peer_min_access=("access_pt", "min"),
        peer_max_access=("access_pt", "max"))
    for field in fields:
        spread = valid.groupby("peer_group")[field].agg(["min", "max"]).add_prefix(field + "_")
        group = group.merge(spread, on="peer_group", validate="one_to_one")
    valid = valid.merge(group, on="peer_group", validate="many_to_one")
    valid["peer_supported"] = valid["peer_count"].ge(minimum) & valid["peer_districts"].ge(2)
    valid["peer_access_gap"] = (valid["access_pt"] - valid["peer_median_access"]).where(valid["peer_supported"])
    columns = ["lsoa_code", "peer_group", "peer_count", "peer_districts", "peer_supported", "peer_median_access", "peer_access_gap"]
    result = result.merge(valid[columns], on="lsoa_code", how="left", validate="one_to_one")
    result.attrs["peer_bin_edges"] = edges
    return result, group


def rank_associations(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for district, group in [("All study districts", frame), *list(frame.groupby("district_name"))]:
        for variable in ["no_car_pct", "income_pct", "unemployment_pct", "residents_per_km2"]:
            complete = group[["access_pt", variable]].dropna()
            rho = complete.rank(method="average").corr().iloc[0, 1] if len(complete) >= 3 else np.nan
            rows.append({"district": district, "variable": variable, "complete_pairs": len(complete), "spearman_rho": rho})
    return pd.DataFrame(rows)

"""Small synthetic fixtures test mathematics only; they are never app data."""
import numpy as np
import pandas as pd
import pytest

from opportunity.analysis import jaccard, mid_percentile, percentage, prioritise, peer_comparisons, sensitivity
from opportunity.prepare import checked_join


@pytest.fixture
def areas():
    return pd.DataFrame({
        "lsoa_code": [f"E0100000{i}" for i in range(1, 6)],
        "district_code": ["A", "A", "A", "B", "B"],
        "district_name": ["A", "A", "A", "B", "B"], "study_role": ["main"] * 3 + ["comparison"] * 2,
        "access_pt": [10, 20, 30, 40, 50], "no_car_pct": [50, 40, 30, 20, 10],
        "income_rate": [0.5, 0.4, 0.3, 0.2, 0.1],
    })


def test_percentage_uses_correct_denominator_and_retains_missing():
    actual = percentage(pd.Series([10, 0, 0, np.nan, 2]), pd.Series([40, 10, 0, 10, np.nan]))
    np.testing.assert_allclose(actual.iloc[:2], [25, 0])
    assert actual.iloc[2:].isna().all()


@pytest.mark.parametrize("numerator,denominator", [(11, 10), (-1, 10), (1, -2), (np.inf, 10)])
def test_impossible_counts_fail(numerator, denominator):
    with pytest.raises(ValueError):
        percentage(pd.Series([numerator]), pd.Series([denominator]))


def test_geographic_join_preserves_spine_and_missing():
    spine = pd.DataFrame({"lsoa_code": ["E01000001", "E01000002"]})
    right = pd.DataFrame({"lsoa_code": ["E01000001", "E01099999"], "value": [7, 9]})
    joined, audit = checked_join(spine, right, "fixture", "LSOA 2021")
    assert len(joined) == 2 and pd.isna(joined.iloc[1]["value"])
    assert audit["unmatched_codes"] == ["E01000002"] and audit["outside_study_rows"] == 1


@pytest.mark.parametrize("side", ["left", "right"])
def test_duplicate_keys_cannot_multiply_rows(side):
    frame = pd.DataFrame({"lsoa_code": ["E01000001"]})
    duplicate = pd.concat([frame, frame], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        checked_join(duplicate if side == "left" else frame, duplicate if side == "right" else frame, "fixture", "LSOA 2021")


def test_identical_code_does_not_make_geography_compatible():
    frame = pd.DataFrame({"lsoa_code": ["E01000001"]})
    with pytest.raises(ValueError, match="incompatible geography"):
        checked_join(frame, frame, "old geography", "LSOA 2011")


def test_tied_percentiles_are_equal_and_do_not_use_row_order():
    values = pd.Series([10, 10, 20, 30])
    np.testing.assert_allclose(mid_percentile(values, values), [0.25, 0.25, 0.625, 0.875])


def test_score_direction_and_intersection(areas):
    result = prioritise(areas)
    np.testing.assert_allclose(result["priority_score"], [90, 70, 50, 30, 10])
    assert result["triple_priority"].tolist() == [True, False, False, False, False]


def test_missing_indicator_is_not_zero_or_false(areas):
    areas.loc[0, "income_rate"] = np.nan
    result = prioritise(areas)
    assert pd.isna(result.loc[0, "priority_score"])
    assert pd.isna(result.loc[0, "triple_priority"])
    assert not result.loc[0, "priority_eligible"]


def test_weights_do_not_change_the_independent_tail_rule(areas):
    areas["no_car_pct"] = [10, 50, 20, 40, 30]
    equal = prioritise(areas)
    weighted = prioritise(areas, weights={"poor_access": 3, "no_car": 0, "income_need": 1})
    pd.testing.assert_series_equal(equal["triple_priority"], weighted["triple_priority"])
    assert not equal["priority_score"].equals(weighted["priority_score"])


def test_bad_weights_fail(areas):
    with pytest.raises(ValueError):
        prioritise(areas, weights={"poor_access": 0, "no_car": 0, "income_need": 0})


def test_main_reference_scores_comparison_areas_without_using_them_as_reference(areas):
    main = prioritise(areas, comparison_group="main_reference")
    # Last area has access above all main areas and need below all main areas.
    assert main.loc[4, "priority_score"] == 0
    assert np.isclose(main.loc[0, "priority_score"], 100 * 5 / 6)


def test_empty_overlap_is_undefined():
    assert np.isnan(jaccard(set(), set()))
    assert jaccard({1, 2}, {2, 3}) == 1 / 3


def test_sensitivity_uses_configured_baseline_not_hidden_defaults(areas):
    weights = {"poor_access": 1, "no_car": 1, "income_need": 1}
    config = {"comparison_groups": ["pooled"], "tail_fractions": [1 / 3], "weights": {"equal": weights}}
    baseline = {"tail_fraction": 1 / 3, "comparison_group": "pooled", "weights": weights}
    scenarios, _ = sensitivity(areas, config, baseline)
    assert scenarios.loc[0, "triple_count"] == 2
    assert scenarios.loc[0, "triple_jaccard_vs_baseline"] == 1


def test_peer_support_requires_multiple_districts_and_enough_areas(areas):
    areas["residents_per_km2"] = [100, 200, 300, 400, 500]
    areas["age_0_14_pct"] = [10, 11, 12, 13, 14]
    areas["age_65plus_pct"] = [10, 11, 12, 13, 14]
    result, _ = peer_comparisons(areas, bins=1, minimum=5)
    assert result["peer_supported"].all()
    assert result["peer_access_gap"].tolist() == [-20, -10, 0, 10, 20]
    areas["district_code"] = "A"
    result, _ = peer_comparisons(areas, bins=1, minimum=5)
    assert result["peer_access_gap"].isna().all()

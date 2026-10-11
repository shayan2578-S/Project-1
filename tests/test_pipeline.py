from pathlib import Path
import json
import zipfile

import duckdb
import numpy as np
import pandas as pd
import pytest
import yaml

from opportunity.acquire import discover_links, fetch, sha256
from opportunity.prepare import checked_path, read_table

ROOT = Path(__file__).resolve().parents[1]
BUILT = (ROOT / "data/processed/neighbourhoods.parquet").exists()


def test_download_links_are_followed_not_guessed():
    result = discover_links('<a href="/files/current.ods">2025 workbook</a><a href="/guide">Guide</a>', 'https://www.gov.uk/release')
    assert result["links"][0]["url"] == "https://www.gov.uk/files/current.ods"
    assert result["links"][0]["is_file"]
    assert not result["links"][1]["is_file"]


def test_corrupt_raw_file_is_rejected(tmp_path):
    path = tmp_path / "data/raw/file.csv"
    path.parent.mkdir(parents=True)
    path.write_text("original")
    descriptor = {"path": "data/raw/file.csv", "sha256": sha256(path)}
    path.write_text("changed")
    with pytest.raises(ValueError, match="checksum"):
        checked_path(tmp_path, descriptor)


def test_partial_sum_stays_missing(tmp_path):
    path = tmp_path / "data/raw/counts.csv"
    path.parent.mkdir(parents=True)
    path.write_text("code,part_a,part_b\nE01000001,10,\nE01000002,10,4\n")
    spec = {"files": [{"path": "data/raw/counts.csv", "sha256": sha256(path)}], "format": "csv",
            "geography_version": "LSOA 2021", "reference_period": "synthetic test", "licence": "synthetic test",
            "definition_evidence": "test fixture", "columns": {"lsoa_code": "code", "sum": ["part_a", "part_b"]}}
    result = read_table(tmp_path, spec)
    assert pd.isna(result.loc[0, "sum"]) and result.loc[1, "sum"] == 14


def test_sql_weighted_mean_uses_only_observed_metric_denominators():
    frame = pd.DataFrame({"value": [10.0, 20.0, None], "population": [1, 3, 1000]})
    with duckdb.connect() as con:
        con.register("f", frame)
        actual = con.execute("SELECT SUM(value*population)/SUM(population) FILTER (WHERE value IS NOT NULL AND population>0) FROM f").fetchone()[0]
    assert actual == 17.5


@pytest.mark.skipif(not BUILT, reason="Official inputs must be acquired and pipeline built")
def test_real_data_coverage_and_no_inner_join_loss():
    frame = pd.read_parquet(ROOT / "data/processed/neighbourhoods.parquet")
    geography = json.loads((ROOT / "metadata/geography_manifest.json").read_text())
    expected = {row["LAD24CD"]: row["lsoas"] for row in geography["district_counts"]}
    assert frame.groupby("district_code").size().to_dict() == expected
    assert frame["lsoa_code"].is_unique
    quality = json.loads((ROOT / "reports/data_quality.json").read_text())
    assert all(audit["matched"] == len(frame) and audit["unmatched_codes"] == [] for audit in quality["joins"])
    assert quality["boundary_count"] == len(frame)


@pytest.mark.skipif(not BUILT, reason="Official data not built")
def test_real_rate_uses_households_not_population():
    frame = pd.read_parquet(ROOT / "data/processed/neighbourhoods.parquet")
    np.testing.assert_allclose(frame["no_car_pct"], 100 * frame["households_no_car"] / frame["households_total"])
    wrong = 100 * frame["households_no_car"] / frame["population_total"]
    assert not np.allclose(frame["no_car_pct"], wrong)


@pytest.mark.skipif(not BUILT, reason="Official data not built")
def test_unemployment_includes_active_students_and_uses_active_denominator():
    frame = pd.read_parquet(ROOT / "data/processed/neighbourhoods.parquet").set_index("lsoa_code")
    config = yaml.safe_load((ROOT / "config/verified_inputs.yml").read_text())["tables"]["activity"]
    with zipfile.ZipFile(ROOT / config["files"][0]["path"]) as z, z.open(config["member"]) as member:
        original = pd.read_csv(member).set_index("geography code").loc[frame.index]
    prefix = "Economic activity status: "
    numerator = original[prefix + "Economically active (excluding full-time students): Unemployed"] + original[prefix + "Economically active and a full-time student: Unemployed"]
    denominator = original[prefix + "Economically active (excluding full-time students)"] + original[prefix + "Economically active and a full-time student"]
    np.testing.assert_allclose(frame["unemployment_pct"], 100 * numerator / denominator)
    assert (original[prefix + "Economically active and a full-time student: Unemployed"] > 0).any()


@pytest.mark.skipif(not BUILT, reason="Official data not built")
def test_real_sql_summary_agrees_with_independent_calculation():
    frame = pd.read_parquet(ROOT / "data/processed/neighbourhoods.parquet")
    summary = pd.read_csv(ROOT / "data/processed/district_summary.csv").set_index("district_code")
    for code, group in frame.groupby("district_code"):
        assert np.isclose(summary.loc[code, "population_weighted_mean_access"], np.average(group["access_pt"], weights=group["population_total"]))
        assert np.isclose(summary.loc[code, "household_no_car_pct"], 100 * group["households_no_car"].sum() / group["households_total"].sum())


@pytest.mark.skipif(not BUILT, reason="Official data not built")
def test_every_locked_original_and_output_checksum():
    manifest = json.loads((ROOT / "data/processed/build_manifest.json").read_text())
    for name, expected in manifest["outputs"].items():
        assert sha256(ROOT / "data/processed" / name) == expected
    for entry in json.loads((ROOT / "metadata/source_lock.json").read_text()):
        assert sha256(ROOT / entry["local_path"]) == entry["sha256"]

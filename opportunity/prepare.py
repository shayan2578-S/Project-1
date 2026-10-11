"""Checksum-pinned preparation with a complete official geography spine."""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import duckdb
import geopandas as gpd
import numpy as np
import pandas as pd
import yaml

from opportunity.acquire import sha256, timestamp
from opportunity.analysis import derive_indicators, peer_comparisons, prioritise, rank_associations, sensitivity
from opportunity.ods import extract_lsoa_sheets

IDENTIFIERS = {"lsoa_code", "lsoa_name", "district_code", "district_name", "imd_district_code", "imd_district_name"}


def unique_codes(frame: pd.DataFrame, label: str) -> None:
    if "lsoa_code" not in frame or frame["lsoa_code"].isna().any():
        raise ValueError(f"{label}: missing area code")
    duplicates = frame.loc[frame["lsoa_code"].duplicated(keep=False), "lsoa_code"].tolist()
    if duplicates:
        raise ValueError(f"{label}: duplicate area codes: {duplicates[:10]}")
    if not frame["lsoa_code"].str.fullmatch(r"[EW]01\d{6}").all():
        raise ValueError(f"{label}: unexpected LSOA code format")


def checked_join(spine: pd.DataFrame, right: pd.DataFrame, label: str, geography: str) -> tuple[pd.DataFrame, dict]:
    if geography != "LSOA 2021":
        raise ValueError(f"{label}: incompatible geography {geography}; no implicit crosswalk is permitted")
    unique_codes(spine, "geography spine")
    unique_codes(right, label)
    left_codes, right_codes = set(spine["lsoa_code"]), set(right["lsoa_code"])
    audit = {"table": label, "spine_rows": len(spine), "source_rows": len(right),
             "matched": len(left_codes & right_codes), "unmatched_codes": sorted(left_codes - right_codes),
             "outside_study_rows": len(right_codes - left_codes), "duplicate_codes": 0,
             "geography_version": geography, "cardinality": "one_to_one"}
    if audit["matched"] == 0:
        raise ValueError(f"{label}: no matching study areas")
    merged = spine.merge(right, on="lsoa_code", how="left", validate="one_to_one")
    if len(merged) != len(spine):
        raise ValueError("Join changed the study universe")
    return merged, audit


def checked_path(root: Path, descriptor: dict) -> Path:
    path = (root / descriptor["path"]).resolve()
    if not path.is_relative_to((root / "data/raw").resolve()):
        raise ValueError("Reviewed source must point to a retained original under data/raw")
    if sha256(path) != descriptor["sha256"]:
        raise ValueError(f"Source checksum changed: {descriptor['path']}; inspect the new release before updating mappings")
    return path


def read_table(root: Path, specification: dict) -> pd.DataFrame:
    if specification["geography_version"] != "LSOA 2021":
        raise ValueError("Direct joining of incompatible geography is forbidden")
    for metadata in ["reference_period", "definition_evidence", "licence"]:
        if not specification.get(metadata):
            raise ValueError(f"Missing reviewed metadata: {metadata}")
    frames = []
    for descriptor in specification["files"]:
        path = checked_path(root, descriptor)
        kind = specification["format"]
        if kind == "zip_csv":
            with zipfile.ZipFile(path) as archive, archive.open(specification["member"]) as member:
                raw = pd.read_csv(member, dtype=str)
        elif kind == "csv":
            raw = pd.read_csv(path, dtype=str, skiprows=specification.get("skiprows", 0))
        elif kind == "dft_ods":
            manifest = extract_lsoa_sheets(path, root / "data/interim/dft")
            sheet = next(item for item in manifest["sheets"] if item["name"] == specification["sheet"])
            raw = pd.read_csv(root / "data/interim/dft" / sheet["csv"], dtype=str,
                              skiprows=specification["skiprows"])
        elif kind == "arcgis_json":
            payload = json.loads(path.read_text())
            if "error" in payload:
                raise ValueError("Recorded ArcGIS response is an error")
            raw = pd.DataFrame(feature["attributes"] for feature in payload["features"])
        else:
            raise ValueError(f"Unsupported reviewed format {kind}")
        result = pd.DataFrame(index=raw.index)
        for target, columns in specification["columns"].items():
            columns = [columns] if isinstance(columns, str) else columns
            if len(set(columns)) != len(columns):
                raise ValueError(f"Repeated source column in {target}")
            if not set(columns).issubset(raw.columns):
                raise ValueError(f"Source schema changed; missing {set(columns) - set(raw.columns)}")
            if target in IDENTIFIERS:
                if len(columns) != 1:
                    raise ValueError("Identifier cannot be a sum")
                result[target] = raw[columns[0]].astype("string").str.strip()
            else:
                numeric = raw[columns].replace({"..": np.nan, ":": np.nan, "": np.nan}).apply(pd.to_numeric, errors="raise")
                # A partially missing aggregate must remain missing.
                result[target] = numeric.sum(axis=1, min_count=len(columns))
        frames.append(result)
    combined = pd.concat(frames, ignore_index=True)
    unique_codes(combined, "source table")
    return combined


def load_boundaries(root: Path, specification: dict, codes: set) -> gpd.GeoDataFrame:
    if specification["geography_version"] != "LSOA 2021":
        raise ValueError("Boundary vintage mismatch")
    features = []
    for descriptor in specification["files"]:
        payload = json.loads(checked_path(root, descriptor).read_text())
        if payload.get("type") != "FeatureCollection" or payload.get("exceededTransferLimit"):
            raise ValueError("Invalid or truncated boundary GeoJSON")
        features.extend(payload["features"])
    geodata = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326").rename(
        columns={specification["code_column"]: "lsoa_code"})
    unique_codes(geodata, "boundaries")
    if set(geodata["lsoa_code"]) != codes:
        raise ValueError("Boundary coverage is not exactly the selected full-district geography spine")
    if geodata.geometry.isna().any() or geodata.geometry.is_empty.any() or not geodata.geometry.is_valid.all():
        raise ValueError("Boundary geometries are missing, empty or invalid; investigate before mapping")
    if not geodata.geom_type.isin(["Polygon", "MultiPolygon"]).all():
        raise ValueError("Expected LSOA polygons")
    return geodata[["lsoa_code", "geometry"]].sort_values("lsoa_code").reset_index(drop=True)


def configuration_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for name in ["study.yml", "verified_inputs.yml"]:
        digest.update((root / "config" / name).read_bytes())
    return digest.hexdigest()


def build(root: Path) -> None:
    study = yaml.safe_load((root / "config/study.yml").read_text())
    inputs = yaml.safe_load((root / "config/verified_inputs.yml").read_text())
    if not inputs.get("reviewed"):
        raise ValueError("Official source definitions and mappings have not been reviewed")
    tables = inputs["tables"]
    frame = read_table(root, tables["lookup"])
    frame = frame.loc[frame["district_code"].isin(study["districts"])].copy()
    district_counts = {}
    for code, district in study["districts"].items():
        subset = frame.loc[frame["district_code"].eq(code)]
        if set(subset["district_name"]) != {district["name"]}:
            raise ValueError(f"Official code/name check failed: {code}")
        district_counts[code] = len(subset)
    frame["study_role"] = frame["district_code"].map({code: item["role"] for code, item in study["districts"].items()})
    audits = []
    for name, specification in tables.items():
        if name == "lookup":
            continue
        right = read_table(root, specification)
        frame, audit = checked_join(frame, right, name, specification["geography_version"])
        audits.append(audit)
    observed_imd = frame["imd_district_code"].notna()
    if not frame.loc[observed_imd, "imd_district_code"].eq(frame.loc[observed_imd, "district_code"]).all():
        raise ValueError("ONS and deprivation district assignments disagree")
    for column in ["access_pt", "access_sustainable", "access_walking", "access_cycling", "access_driving", "employment_overall"]:
        if not frame[column].dropna().between(0, 100).all():
            raise ValueError(f"Unexpected DfT range: {column}")
    if not frame["income_rate"].dropna().between(0, 1).all():
        raise ValueError("Income score is not a proportion")
    if (frame["residents_per_km2"].dropna() < 0).any():
        raise ValueError("Negative population density")
    frame = derive_indicators(frame)
    frame = prioritise(frame, **study["priority"])
    scenarios, stability = sensitivity(frame, study["sensitivity"], study["priority"])
    frame = frame.merge(stability, on="lsoa_code", how="left", validate="one_to_one")
    frame, peer_groups = peer_comparisons(frame, study["peers"]["quantile_bins"], study["peers"]["minimum_group_size"])
    peer_edges = frame.attrs.get("peer_bin_edges", {})
    # Re-run priority definition using the documented non-driving overall score.
    alternative = prioritise(frame, access_column="access_sustainable", **study["priority"])
    frame["sustainable_triple_priority"] = alternative["triple_priority"]
    frame["sustainable_priority_score"] = alternative["priority_score"]
    boundaries = load_boundaries(root, inputs["boundaries"], set(frame["lsoa_code"]))
    activity_delta = frame["active_16plus"] + frame["inactive_16plus"] - frame["adults_16plus"]
    employment_delta = frame["employed_16plus"] + frame["unemployed_16plus"] - frame["active_16plus"]
    quality = {
        "generated_at": timestamp(), "status": "passed", "district_counts": district_counts,
        "rows": len(frame), "duplicate_codes": int(frame["lsoa_code"].duplicated().sum()),
        "joins": audits, "boundary_count": len(boundaries), "invalid_geometries": 0,
        "boundary_crs": str(boundaries.crs), "boundary_version": inputs["boundaries"]["version"],
        "missing_values": {column: int(frame[column].isna().sum()) for column in frame},
        "zero_denominators": {column: int(frame[column].eq(0).sum()) for column in ["households_total", "adults_16plus", "active_16plus", "age_total", "qualifications_16plus"]},
        "active_inactive_partition_max_abs_difference": float(activity_delta.abs().max()),
        "employment_partition_max_abs_difference": float(employment_delta.abs().max()),
        "cross_table_adult_count_max_abs_difference": float((frame["adults_16plus"] - frame["qualifications_16plus"]).abs().max()),
        "priority_eligible": int(frame["priority_eligible"].sum()),
        "peer_supported": int(frame["peer_supported"].fillna(False).sum()), "peer_bin_edges": peer_edges,
    }
    if activity_delta.abs().max() > 5 or employment_delta.abs().max() > 5:
        raise ValueError("Activity partitions differ by more than the documented 5-person audit tolerance")
    output = root / "data/processed"
    output.mkdir(parents=True, exist_ok=True)
    frame = frame.sort_values("lsoa_code").reset_index(drop=True)
    with duckdb.connect(str(output / "opportunity.duckdb")) as connection:
        connection.register("prepared_frame", frame)
        connection.execute("CREATE OR REPLACE TABLE neighbourhoods AS SELECT * FROM prepared_frame")
        district_summary = connection.execute((root / "sql/district_summary.sql").read_text()).df()
        connection.register("district_frame", district_summary)
        connection.execute("CREATE OR REPLACE TABLE district_summary AS SELECT * FROM district_frame")
    frame.to_parquet(output / "neighbourhoods.parquet", index=False)
    frame.to_csv(output / "neighbourhoods.csv", index=False)
    boundaries.to_file(output / "boundaries.geojson", driver="GeoJSON")
    boundaries.to_parquet(output / "boundaries.parquet", index=False)
    district_summary.to_csv(output / "district_summary.csv", index=False)
    scenarios.to_csv(output / "sensitivity.csv", index=False)
    peer_groups.to_csv(output / "peer_groups.csv", index=False)
    rank_associations(frame).to_csv(output / "associations.csv", index=False)
    (root / "reports/data_quality.json").write_text(json.dumps(quality, indent=2, default=str) + "\n")
    manifest = {"built_at": timestamp(), "configuration_sha256": configuration_digest(root),
                "rows": len(frame), "status": "passed", "accessibility": inputs["accessibility"],
                "outputs": {p.name: sha256(p) for p in output.iterdir() if p.suffix in {".parquet", ".csv", ".geojson"}},
                "input_sha256": sorted({item["sha256"] for spec in [*tables.values(), inputs["boundaries"]] for item in spec["files"]})}
    (output / "build_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    from opportunity.reporting import write_reports
    write_reports(root, frame, district_summary, scenarios, quality)
    print(f"Built {len(frame)} real neighbourhoods; {quality['priority_eligible']} have all three core indicators.")

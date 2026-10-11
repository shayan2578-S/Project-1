"""Download complete district lookup rows and compatible ONS polygons.

Service URLs come from inspected authoritative ONS Hub item metadata. Queries
are explicit, paginated, and independently checked against service counts.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlencode

import pandas as pd
import yaml

from opportunity.acquire import fetch, load_register


def query_url(layer: str, **parameters) -> str:
    return layer + "/query?" + urlencode(parameters)


def acquire_geography(root: Path) -> dict:
    study = yaml.safe_load((root / "config/study.yml").read_text())
    source = yaml.safe_load((root / "config/sources.yml").read_text())["sources"]["ons"]
    source.update(reference_period="LSOA boundaries 21 March 2021, BGC V5 July 2024; LAD lookup May 2024, corrected August 2025",
                  geography_version="LSOA 2021 / LAD 2024",
                  licence="ONS Open Government Licence v3.0; boundaries contain OS data Crown copyright and database right 2026")
    records = load_register(root)
    lookup_meta = json.loads((root / "metadata/ons_lookup_v3.json").read_text())["data"]["attributes"]
    boundary_meta = json.loads((root / "metadata/ons_boundaries_v3.json").read_text())["data"]["attributes"]
    for meta in [lookup_meta, boundary_meta]:
        if meta["orgId"] != "ESMARspQHYMw9BZ9" or meta["contentStatus"] != "public_authoritative":
            raise ValueError("Expected an authoritative ONS geography service")
    codes = list(study["districts"])
    if not all(re.fullmatch(r"E\d{8}", code) for code in codes):
        raise ValueError("Invalid English district code")
    where = "LAD24CD IN (" + ",".join("'" + code + "'" for code in codes) + ")"

    def get(url: str, title: str) -> tuple[dict, dict]:
        record = fetch(root, "ons", {**source, "title": title}, url, "artifact", records)
        if record["status"] != "downloaded":
            raise ValueError(record["error"])
        payload = json.loads((root / record["local_path"]).read_text())
        if "error" in payload:
            raise ValueError(f"ArcGIS error: {payload['error']}")
        return payload, record

    count, _ = get(query_url(lookup_meta["url"], where=where, returnCountOnly="true", f="json"), "ONS study lookup count")
    lookup_records, attributes = [], []
    for offset in range(0, count["count"], 1000):
        payload, record = get(query_url(lookup_meta["url"], where=where, outFields="*", returnGeometry="false",
                                       resultOffset=offset, resultRecordCount=1000, orderByFields="LSOA21CD", f="json"),
                              "ONS LSOA21 to LAD24 study lookup page")
        lookup_records.append(record)
        attributes.extend(feature["attributes"] for feature in payload["features"])
    lookup = pd.DataFrame(attributes)
    if len(lookup) != count["count"] or lookup["LSOA21CD"].duplicated().any():
        raise ValueError("Incomplete or duplicate paginated lookup")
    for code, district in study["districts"].items():
        names = set(lookup.loc[lookup["LAD24CD"].eq(code), "LAD24NM"])
        if names != {district["name"]}:
            raise ValueError(f"District identity mismatch for {code}: {names}")
    boundary_records, all_codes = [], []
    lsoa_codes = sorted(lookup["LSOA21CD"])
    # Keep encoded GET queries below the server's query-string length limit.
    for start in range(0, len(lsoa_codes), 50):
        batch = lsoa_codes[start:start + 50]
        if not all(re.fullmatch(r"E01\d{6}", code) for code in batch):
            raise ValueError("Unexpected LSOA code in official lookup")
        boundary_where = "LSOA21CD IN (" + ",".join("'" + code + "'" for code in batch) + ")"
        payload, record = get(query_url(boundary_meta["url"], where=boundary_where,
                                       outFields="LSOA21CD,LSOA21NM", outSR=4326, returnGeometry="true", f="geojson"),
                              "ONS LSOA 2021 BGC V5 study boundaries batch")
        if payload.get("exceededTransferLimit") or len(payload["features"]) != len(batch):
            raise ValueError("Boundary request truncated or missing expected features")
        all_codes.extend(feature["properties"]["LSOA21CD"] for feature in payload["features"])
        boundary_records.append(record)
        print(f"Downloaded ONS polygons: {len(all_codes)}/{len(lsoa_codes)}", flush=True)
    if sorted(all_codes) != lsoa_codes:
        raise ValueError("Boundary codes differ from the full-district lookup")
    manifest = {"lookup_records": lookup_records, "boundary_records": boundary_records,
                "district_counts": lookup.groupby(["LAD24CD", "LAD24NM"]).size().reset_index(name="lsoas").to_dict("records"),
                "lsoa_count": len(lookup), "lookup_item": lookup_meta["itemId"], "boundary_item": boundary_meta["itemId"],
                "boundary_version": "LSOA 2021 BGC V5; 20 m generalised, coastline clipped",
                "lookup_version": "LSOA21 to LAD24 via ward best-fit; corrected August 2025"}
    (root / "metadata/geography_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest

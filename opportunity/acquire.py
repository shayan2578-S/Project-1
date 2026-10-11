"""Follow real official links, preserve original bytes, and record failed attempts.

No table schema or reference period is inferred from a filename. Semantic
review is a separate, explicit stage after inspection of the downloaded files.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
import yaml
from bs4 import BeautifulSoup

REGISTER_FIELDS = [
    "source_id", "kind", "publisher", "title", "landing_page", "download_url",
    "resolved_url", "reference_period", "geography_version", "licence",
    "retrieved_at", "sha256", "bytes", "local_path", "status", "error",
]
FILE_PATTERN = re.compile(r"\.(xlsx|xls|ods|csv|zip|geojson|json|gpkg|pdf)(?:[?#]|$)", re.I)


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_register(root: Path) -> list[dict]:
    path = root / "metadata/source_register.json"
    return json.loads(path.read_text()) if path.exists() else []


def write_register(root: Path, records: list[dict]) -> None:
    directory = root / "metadata"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "source_register.json").write_text(json.dumps(records, indent=2) + "\n")
    with (directory / "source_register.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=REGISTER_FIELDS, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def fetch(root: Path, source_id: str, source: dict, url: str, kind: str,
          records: list[dict], *, max_bytes: int = 250_000_000,
          refresh: bool = False) -> dict:
    """Store downloads by content hash; never overwrite an original download.

    TLS verification stays enabled. A blocked or failed response is an attempt,
    not a dataset. Cached files are checksum verified before reuse.
    """
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Use a public HTTPS URL without embedded credentials")
    if not refresh:
        for previous in reversed(records):
            if previous["download_url"] == url and previous["status"] == "downloaded":
                path = root / previous["local_path"]
                if path.exists():
                    if sha256(path) != previous["sha256"]:
                        raise ValueError(f"Checksum mismatch for retained original: {path}")
                    return previous
    record = dict.fromkeys(REGISTER_FIELDS)
    record.update(source_id=source_id, kind=kind, publisher=source["publisher"],
                  title=source["title"], landing_page=source["landing_page"],
                  download_url=url, retrieved_at=timestamp(), status="attempted",
                  reference_period=source.get("reference_period"),
                  geography_version=source.get("geography_version"), licence=source.get("licence"))
    directory = root / "data/raw" / source_id
    directory.mkdir(parents=True, exist_ok=True)
    temporary = directory / "download.partial"
    try:
        with requests.get(url, stream=True, timeout=(15, 60),
                          headers={"User-Agent": "AccessToOpportunity/0.1 (academic portfolio research)"}) as response:
            record["resolved_url"] = response.url
            response.raise_for_status()
            size = 0
            with temporary.open("wb") as output:
                for block in response.iter_content(1024 * 1024):
                    size += len(block)
                    if size > max_bytes:
                        raise ValueError(f"Download exceeds safety limit of {max_bytes} bytes; review before increasing")
                    output.write(block)
            media_type = response.headers.get("Content-Type", "")
            if kind == "artifact" and "text/html" in media_type:
                raise ValueError("A download link returned HTML, not a data file; inspect the source page")
            extension = Path(urlparse(response.url).path).suffix.lower()
            if kind == "landing":
                extension = ".html"
            if not re.fullmatch(r"\.[a-z0-9]{1,8}", extension):
                extension = ".bin"
            digest = sha256(temporary)
            final_path = directory / (digest + extension)
            if final_path.exists():
                if sha256(final_path) != digest:
                    raise ValueError("Content-addressed raw file was modified")
                temporary.unlink()
            else:
                temporary.replace(final_path)
            record.update(sha256=digest, bytes=size, local_path=str(final_path.relative_to(root)),
                          status="downloaded", content_type=media_type)
    except (requests.RequestException, OSError, ValueError) as exc:
        record.update(status="blocked" if "403" in str(exc) else "failed", error=str(exc))
        temporary.unlink(missing_ok=True)
    records.append(record)
    write_register(root, records)
    return record


def discover_links(body: str, base_url: str) -> dict:
    soup = BeautifulSoup(body, "html.parser")
    links = []
    seen = set()
    for anchor in soup.select("a[href]"):
        url = urljoin(base_url, anchor["href"])
        if urlparse(url).scheme != "https" or url in seen:
            continue
        seen.add(url)
        text = anchor.get_text(" ", strip=True)
        context = anchor.parent.get_text(" ", strip=True)[:1600]
        links.append({"url": url, "text": text, "context": context,
                      "is_file": bool(FILE_PATTERN.search(url))})
    dates = [element.get("datetime") for element in soup.select("time[datetime]")]
    return {"title": soup.title.get_text(strip=True) if soup.title else None,
            "page_dates_not_data_reference_periods": dates,
            "links": links,
            "licence_links": [link for link in links if "licen" in (link["text"] + link["url"]).lower()]}


def inspect_file(path: Path) -> dict:
    """Expose actual sheets, cells, archive members and headers for review."""
    result = {"path": str(path), "sha256": sha256(path), "bytes": path.stat().st_size}
    suffix = path.suffix.lower()
    try:
        if suffix == ".xlsx":
            import openpyxl
            workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
            result["sheets"] = []
            for sheet in workbook.worksheets:
                rows = [[str(cell) if cell is not None else None for cell in row]
                        for row in sheet.iter_rows(min_row=1, max_row=35, max_col=24, values_only=True)]
                result["sheets"].append({"name": sheet.title, "rows": sheet.max_row,
                                         "columns": sheet.max_column, "first_35_rows_first_24_columns": rows})
            workbook.close()
        elif suffix == ".zip":
            with zipfile.ZipFile(path) as archive:
                result["members"] = [{"name": info.filename, "bytes": info.file_size}
                                     for info in archive.infolist()]
                result["csv_previews"] = {}
                for info in archive.infolist():
                    if info.filename.lower().endswith(".csv"):
                        with archive.open(info) as member:
                            sample = member.read(128_000).decode("utf-8-sig", errors="replace")
                        result["csv_previews"][info.filename] = list(csv.reader(io.StringIO(sample)))[:4]
        elif suffix == ".csv":
            sample = pd.read_csv(path, nrows=5)
            result.update(columns=sample.columns.tolist(), preview=sample.fillna("").to_dict("records"))
        elif suffix in (".geojson", ".json"):
            payload = json.loads(path.read_text())
            result["top_level_keys"] = list(payload) if isinstance(payload, dict) else None
            if isinstance(payload, dict) and payload.get("features"):
                result["feature_count"] = len(payload["features"])
                result["first_feature_properties"] = payload["features"][0].get("properties")
                result["crs"] = payload.get("crs", "Not declared; inspect format specification")
        else:
            result["inspection_note"] = "Retained original; manual or format-specific inspection still needed."
    except Exception as exc:
        result["inspection_error"] = f"{type(exc).__name__}: {exc}"
    return result


def acquire(root: Path, *, refresh: bool = False) -> dict:
    config = yaml.safe_load((root / "config/sources.yml").read_text())
    records = load_register(root)
    discovery = {}
    for source_id, source in config["sources"].items():
        page = fetch(root, source_id, source, source["landing_page"], "landing", records, refresh=refresh)
        if page["status"] != "downloaded":
            discovery[source_id] = {"status": page["status"], "error": page["error"]}
            print(f'{source_id}: {page["status"]}: {page["error"]}')
            continue
        links = discover_links((root / page["local_path"]).read_text(errors="replace"),
                               page["resolved_url"])
        pattern = re.compile(source["select_pattern"])
        links["candidate_downloads"] = [link for link in links["links"]
                                        if link["is_file"] and "/csv-preview/" not in link["url"] and pattern.search(
                                            link["url"] + " " + link["text"] + " " + link["context"])]
        links["status"] = "page_inspected"
        discovery[source_id] = links
        for link in links["candidate_downloads"]:
            artifact_source = {**source, "title": link["text"] or source["title"]}
            record = fetch(root, source_id, artifact_source, link["url"], "artifact", records, refresh=refresh)
            print(f'{source_id}: {record["status"]}: {link["url"]}')
    # Reviewed explicit URLs can be added only after following real official links.
    for entry in config.get("selected_artifacts", []):
        source = config["sources"][entry["source_id"]]
        if not entry.get("discovered_on"):
            raise ValueError("Explicit artifact entries require a discovered_on evidence URL")
        fetch(root, entry["source_id"], {**source, "title": entry["title"]},
              entry["url"], "artifact", records, refresh=refresh)
    metadata = root / "metadata"
    metadata.mkdir(exist_ok=True)
    (metadata / "discovery.json").write_text(json.dumps(discovery, indent=2) + "\n")
    inspections = [inspect_file(root / record["local_path"]) for record in records
                   if record["kind"] == "artifact" and record["status"] == "downloaded"]
    (metadata / "file_inspection.json").write_text(json.dumps(inspections, indent=2, default=str) + "\n")
    write_feasibility(root, records, discovery)
    return discovery


def write_feasibility(root: Path, records: list[dict], discovery: dict) -> None:
    artifacts = {r["sha256"]: r for r in records if r["kind"] == "artifact" and r["status"] == "downloaded"}
    lines = ["# Data acquisition and feasibility", "", f"Assessment generated: {timestamp()}", "",
             f"Original data artifacts downloaded: **{len(artifacts)}**.", "",
             "## Acquisition evidence", "", "| Source | Latest acquisition state |", "|---|---|"]
    for source, details in discovery.items():
        state = details.get("status", "unknown")
        error = details.get("error", "").replace("|", "/").replace("\n", " ")
        lines.append(f"| {source} | {state}: {error} |")
    lines += ["", "## Decision before analysis or dashboard development", ""]
    if not artifacts:
        lines += [
            "**Feasibility is unresolved: no official dataset has been acquired.** The proxy rejected the landing-page requests, before their contents or download links could be inspected. This is a network-policy blocker, not evidence that the publishers restrict these datasets.",
            "",
            "No workbook sheets, employment/mode measures, source years, licences, district-code mappings, neighbourhood counts or geographic compatibility have been verified. Newer releases could not be checked. Source-register download URLs for these entries are attempted landing pages; no direct data-file URL or checksum has been invented.",
            "",
            "No substantive research question can yet be answered. No real-data priority list, district comparison or findings should be published. Calculation functions and tests may be prepared independently, but that does not validate the data or complete the core analysis.",
        ]
    else:
        lines += ["Files are preserved and inspected in `metadata/file_inspection.json`. File acquisition alone does not establish semantic or geographic compatibility. Complete the reviewed mappings and a source-specific feasibility assessment before building results.", ""]
        lines += [f'- `{r["local_path"]}` — {r["title"]}' for r in artifacts.values()]
    lines += ["", "## Questions and required evidence", "",
              "| Question | Evidence needed before answering |", "|---|---|",
              "| Where do weak access, no-car households and income need overlap? | Verified LSOA 2021 accessibility definition plus TS045 and an income-domain score, joined to a complete official district lookup. |",
              "| How do distributions differ within and between districts? | Full-district coverage, comparable units/dates, missingness audits and population denominators. |",
              "| How do similar neighbourhoods compare? | Compatible population density, age profiles and income deprivation; enough overlap in descriptive peer groups. |",
              "| Is this specifically access to employment? | The DfT workbook and methodology must explicitly identify an employment-specific measure. Otherwise use its actual overall-connectivity label. |",
              "| Are particular modes worse? | Documented mode-specific measures, not an assumption about an overall score. |",
              "| Does transport cause unemployment? | This descriptive design cannot answer causation, even after downloads succeed. |",
              "| How many jobs are reachable in 30/45/60 minutes? | Routing data, departure times, destinations, mode assumptions and a documented model; outside the core. |",
              "", "## Next steps", "",
              "1. Resolve the network policy using `docs/data_access.md`, then rerun `python -m opportunity acquire --refresh`.",
              "2. Inspect actual files, documentation and newer releases. Verify the three district codes, LSOA version, every numerator/denominator, reference period and licence. Update this report with those findings.",
              "3. Complete `config/verified_inputs.yml` using exact observed column labels; record supporting evidence. Build only after the feasibility gate passes.",
              "4. Keep incompatible 2011 data separate unless a documented, appropriate correspondence method is implemented. Detailed bus routing, BRES and JTS are deferred.", ""]
    report_dir = root / "reports"
    report_dir.mkdir(exist_ok=True)
    # Acquisition reruns must not overwrite the reviewed feasibility assessment.
    (report_dir / "acquisition_status.md").write_text("\n".join(lines))


def replay_lock(root: Path) -> None:
    """Download the exact reviewed inputs; stop if an upstream file changes."""
    lock = json.loads((root / "metadata/source_lock.json").read_text())
    records = load_register(root)
    failures = []
    for entry in lock:
        record = fetch(root, entry["source_id"], entry, entry["download_url"], entry["kind"], records)
        if record["status"] != "downloaded":
            failures.append(f'{entry["title"]}: {record["error"]}')
        elif record["sha256"] != entry["sha256"]:
            failures.append(f'Upstream content changed: {entry["download_url"]}; review before changing the pinned checksum')
        else:
            # Keep semantic review metadata when fetching into a fresh checkout.
            for key in ["reference_period", "geography_version", "licence"]:
                record[key] = entry.get(key)
    write_register(root, records)
    if failures:
        raise ValueError("\n".join(failures))
    print(f"Verified {len(lock)} checksum-pinned original files.")


def lock_reviewed_inputs(root: Path) -> None:
    """Update the lock only from explicit, checksum-verified reviewed mappings."""
    from opportunity.prepare import checked_path
    inputs = yaml.safe_load((root / "config/verified_inputs.yml").read_text())
    if not inputs.get("reviewed"):
        raise ValueError("Review the input mapping before updating the source lock")
    needed = set()
    for specification in [*inputs["tables"].values(), inputs["boundaries"]]:
        for descriptor in specification["files"]:
            checked_path(root, descriptor)
            needed.add(descriptor["sha256"])
    records = load_register(root)
    # Pin inputs actually consumed by the build. Release pages can change their
    # banners or dates without a data revision; their provenance and inspected
    # text remain in the register, rather than blocking exact data reproduction.
    selected = {record["sha256"]: record for record in records if record["status"] == "downloaded" and record["sha256"] in needed}
    if set(selected) != needed:
        raise ValueError("Some mapped original files have no source-register record")
    (root / "metadata/source_lock.json").write_text(json.dumps(list(selected.values()), indent=2) + "\n")

"""Stream the 1 GB XML inside DfT's ODS without building a DOM in memory."""
from __future__ import annotations

import csv
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from opportunity.acquire import sha256

TABLE = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"
TEXT = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
OFFICE = "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}"


def extract_lsoa_sheets(path: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "inspection.json"
    digest = sha256(path)
    if manifest_path.exists():
        cached = json.loads(manifest_path.read_text())
        if cached.get("source_sha256") == digest and all(
            (output / item["csv"]).exists() and sha256(output / item["csv"]) == item["csv_sha256"]
            for item in cached["sheets"] if "csv" in item
        ):
            return cached
    manifest = {"source_sha256": digest, "sheets": []}
    sheet, stream, writer = None, None, None
    with zipfile.ZipFile(path) as archive, archive.open("content.xml") as xml:
        for event, element in ET.iterparse(xml, events=("start", "end")):
            if event == "start" and element.tag == TABLE + "table":
                name = element.get(TABLE + "name")
                sheet = {"name": name, "rows": 0, "preview": []}
                manifest["sheets"].append(sheet)
                if "lsoa" in name.lower():
                    filename = re.sub(r"[^a-zA-Z0-9_-]", "_", name) + ".csv"
                    sheet["csv"] = filename
                    stream = (output / filename).open("w", newline="")
                    writer = csv.writer(stream)
            elif event == "end" and element.tag == TABLE + "table-row":
                values = []
                for cell in element:
                    if cell.tag not in (TABLE + "table-cell", TABLE + "covered-table-cell"):
                        continue
                    value = cell.get(OFFICE + "value")
                    if value is None:
                        value = "\n".join("".join(p.itertext()) for p in cell.iter(TEXT + "p"))
                    repeat = int(cell.get(TABLE + "number-columns-repeated", "1"))
                    # LibreOffice stores very large runs of trailing empty cells.
                    if repeat > 1024:
                        if value:
                            raise ValueError("Unexpected nonempty ODS repetition")
                        break
                    values.extend([value] * repeat)
                while values and values[-1] == "":
                    values.pop()
                if sheet is not None and values:
                    repeat = int(element.get(TABLE + "number-rows-repeated", "1"))
                    if repeat > 1000:
                        raise ValueError("Unexpected nonempty repeated rows")
                    for _ in range(repeat):
                        sheet["rows"] += 1
                        limit = 120 if "metadata" in sheet["name"].lower() else 12
                        if len(sheet["preview"]) < limit:
                            sheet["preview"].append(values)
                        if writer:
                            writer.writerow(values)
                element.clear()
            elif event == "end" and element.tag == TABLE + "table":
                if stream:
                    stream.close()
                    sheet["csv_sha256"] = sha256(output / sheet["csv"])
                    stream, writer = None, None
                print(f'Inspected DfT sheet: {sheet["name"]} ({sheet["rows"]} nonempty rows)', flush=True)
                sheet = None
                element.clear()
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest

# Data acquisition and release review

All core sources were downloaded successfully without credentials. Initial cloud-proxy 403 responses were resolved by allowing the official hosts. Those failed attempts remain in the register; they do not mean the publishers restrict the data. No manual file collection is currently required.

## Reproduce the reviewed release

Run `python -m opportunity acquire --locked` from the repository root, with the project environment active. It downloads the exact 31 inputs in `metadata/source_lock.json`, or reuses checksum-verified originals. It retains bytes in `data/raw/<source>/<sha256>.<extension>` and appends provenance to `metadata/source_register.json` and `.csv`. Unchanged cached files retain their original retrieval time.

Run `python -m opportunity build` next. It verifies the reviewed column mappings, extracts the LSOA sheet from the ODS, validates geography, derives indicators and creates the reports and dashboard tables. A modified original or upstream response causes a checksum failure; never change a checksum merely to make that check pass.

## Actual official downloads

These URLs were followed from official release pages or returned by authoritative ONS catalogue metadata. They are not guessed filenames.

| Source | Landing page | Download used |
|---|---|---|
| DfT | [Transport Connectivity Metrics](https://www.gov.uk/government/publications/transport-connectivity-metric) | [2025 ODS workbook](https://assets.publishing.service.gov.uk/media/68c966fc07d9e92bc5517b80/connectivity_metrics_2025.ods) |
| Census TS045 | [Nomis bulk downloads](https://www.nomisweb.co.uk/census/2021/bulk) | [TS045 ZIP](https://www.nomisweb.co.uk/output/census/2021/census2021-ts045.zip) |
| Census TS066 | Same Nomis page | [TS066 ZIP](https://www.nomisweb.co.uk/output/census/2021/census2021-ts066.zip) |
| Census TS067 | Same Nomis page | [TS067 ZIP](https://www.nomisweb.co.uk/output/census/2021/census2021-ts067.zip) |
| Population | Same Nomis page | [TS001 ZIP](https://www.nomisweb.co.uk/output/census/2021/census2021-ts001.zip) |
| Density | Same Nomis page | [TS006 ZIP](https://www.nomisweb.co.uk/output/census/2021/census2021-ts006.zip) |
| Grouped age | Same Nomis page | [TS007a ZIP](https://www.nomisweb.co.uk/output/census/2021/census2021-ts007a.zip) |
| Income deprivation | [English Indices of Deprivation 2025](https://www.gov.uk/government/statistics/english-indices-of-deprivation-2025) | [Corrected File 7 CSV](https://assets.publishing.service.gov.uk/media/691ded56d140bbbaa59a2a7d/File_7_IoD2025_All_Ranks_Scores_Deciles_Population_Denominators.csv) |
| ONS lookup | [Authoritative item metadata](https://geoportal.statistics.gov.uk/api/v3/datasets/686527814d73403e8f0a59c7a28b0c34_0) | [LSOA21–ward24–LAD24 service](https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/LSOA21_WD24_LAD24_EW_LU/FeatureServer/0) |
| ONS boundaries | [Authoritative item metadata](https://geoportal.statistics.gov.uk/api/v3/datasets/68515293204e43ca8ab56fa13ae8a547_0) | [LSOA December 2021 BGC V5 service](https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/Lower_layer_Super_Output_Areas_December_2021_Boundaries_EW_BGC_V5/FeatureServer/0) |

The lock contains **six Census ZIPs, one DfT workbook, one deprivation CSV, two lookup query responses and 21 boundary query responses**. ArcGIS URLs in the register include the exact query parameters. Lookup pages are ordered by LSOA code; a separate count query checks completeness. Boundary queries use 50 codes per request to avoid the service's URL-length limit and request GeoJSON in EPSG:4326. Dataset item organisation and `public_authoritative` metadata are checked before geography acquisition.

Methodological evidence was also downloaded and inspected, including [DfT guidance](https://www.gov.uk/government/publications/transport-connectivity-metric/transport-connectivity-metric), the [deprivation technical report](https://assets.publishing.service.gov.uk/media/68ff59c80f801e57b5bef907/ID_2025_Technical_Report.pdf), [Nomis reuse terms](https://www.nomisweb.co.uk/home/copyright.asp) and [ONS geography licensing](https://www.ons.gov.uk/methodology/geography/licences). Original bytes and checksums are in the register; inspected text/catalogue metadata is retained under `metadata/`. These documents do not enter the numerical build and are not in the consumed-data lock.

## Check for newer releases

The official pages inspected on 10 October 2026 linked the DfT 2025 workbook, the updated 2025 deprivation files and Census 2021 bulk tables. No newer DfT workbook was listed on its supplied publication page. The geography catalogue returned BGC V5, BSC V4 and BFC/BFE V10; these are different generalisation products, not a single interchangeable version sequence.

1. Run `python -m opportunity acquire --refresh`. It follows current page links, saves new originals alongside old ones and writes discovery/inspection evidence. It does not replace the approved numerical mappings or the reviewed feasibility report.
2. Inspect each changed file with `python -m opportunity inspect path/to/file`. For DfT's large ODS, use `extract_lsoa_sheets` from `opportunity.ods`; it streams the internal XML and produces a manifest, metadata and sheet previews. Review source methods and actual geography, not only a filename/date.
3. Update the feasibility report and exact mappings in `config/verified_inputs.yml` only after reviewing the new definitions and compatibility. Fill in source-specific years, licences and definition evidence. Keep old register entries.
4. Regenerate the consumed-input lock with the reviewed mapping:

   ```bash
   python -c 'from pathlib import Path; from opportunity.acquire import lock_reviewed_inputs; lock_reviewed_inputs(Path.cwd())'
   ```

5. Rebuild, regenerate the dictionary, execute the notebook and run the tests. Review changed findings and source labels. Do not describe a new data release as a comparable trend until its methodology and geography support that comparison.

New ArcGIS service versions require inspecting fresh authoritative ONS catalogue metadata before changing `metadata/ons_lookup_v3.json` or `metadata/ons_boundaries_v3.json`; the current geography command deliberately uses the reviewed services.

## Add a district

1. Find and verify the district code/name in official ONS metadata. Add it to `config/study.yml`, including whether its role is `main` or `comparison`.
2. Run `python -m opportunity geography --update-mappings`. This queries all configured districts, checks every identity, obtains complete polygons, updates the reviewed lookup/boundary file descriptors and regenerates the input lock.
3. Run `make build`, `make notebook` and `make test`. Review geographic counts and the changed priority/peer reference universes.
4. Update narrative titles and labels that currently describe Leeds, Bradford and Wakefield. The numerical pipeline reads configuration; the project's narrative still needs editorial review when the research scope changes.

## If a future download is blocked

The current build has no blocked core dependency. A future failed request will record its exact URL, status and exception in the register. A proxy 403, publisher 403, timeout and upstream checksum change are different problems; read the recorded response before diagnosing one.

For a restricted cloud environment, the core locked downloads require `assets.publishing.service.gov.uk`, `www.nomisweb.co.uk` and `services1.arcgis.com`. Discovery/metadata additionally uses `www.gov.uk`, `geoportal.statistics.gov.uk`, `www.ons.gov.uk`, `www.arcgis.com`, `ons.maps.arcgis.com` and `hub.arcgis.com`. Package installation needs the configured Python package hosts. Retain TLS and checksum verification. No API secret is needed for the public core.

If a network restriction cannot be resolved, precise manual recovery is:

1. Open the source's official landing page above on an allowed connection, choose the named download, and keep its original bytes. For ONS, copy the exact failed query URL from `metadata/source_lock.json` into the browser and save the response; a generic boundary export is not byte-identical to that query response.
2. Compute SHA-256 using `sha256sum downloaded_file` on Linux, `shasum -a 256 downloaded_file` on macOS, or `Get-FileHash downloaded_file -Algorithm SHA256` in PowerShell.
3. Compare with the corresponding lock entry. If it differs, stop and inspect the release/schema/format; do not relabel a changed download as the old file.
4. For an identical file, copy it to that entry's exact `local_path` under the repository, preserving the lock and metadata. Rerun `acquire --locked` to verify the retained file, then rebuild.

A genuinely revised or withdrawn upstream artifact can prevent byte-for-byte reconstruction from public servers. The retained raw snapshot remains the evidence for this completed analysis; the repository does not promise permanent upstream availability.

## Deferred sources

[Nomis BRES](https://www.nomisweb.co.uk/datasets/newbres6pub), [Bus Open Data guidance](https://www.gov.uk/guidance/find-and-use-bus-open-data) and [historical Journey Time Statistics](https://www.gov.uk/government/statistical-data-sets/journey-time-statistics-data-tables-jts) were starting points for optional extensions, not used inputs. No optional download, routing capability or historical comparability is claimed. A later JTS0501 study must establish reference year, geography and any defensible correspondence separately; BRES counts existing jobs, not vacancies; scheduled bus data does not establish reliability.

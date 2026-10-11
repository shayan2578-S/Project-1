# Verification evidence

Verified on **11 October 2026**, using Python 3.12.14 on Linux and the pinned project dependencies. This is evidence for the local workspace; it is not a claim of deployment, GitHub publication, or a future cloud task's readiness.

| Check | Actual result |
|---|---|
| Locked acquisition from an empty data directory | All **31** consumed original files freshly downloaded and SHA-256 matched |
| Independent rebuild using those fresh inputs | **1,015** neighbourhoods; all **five analysis tables identical** to the main build |
| Geographic coverage | Leeds 488, Bradford 312, Wakefield 215; zero duplicate codes, zero unmatched study codes across the eight data joins; 1,015 valid polygons |
| `make build` | Completed; dictionary documents all **66** output fields |
| `.venv/bin/python -m pytest -q` | **30 passed, 0 failed, 0 skipped** |
| `.venv/bin/python -m pip check` | No broken requirements |
| Repeated pinned dependency installation | Completed successfully using the saved setup commands |
| `make notebook` | **8 code cells executed**, no error outputs |
| Streamlit internal health endpoint | HTTP success and `ok` |
| Real Chromium browser check | Full 1,015-area map; Wakefield filter shows 215; indicator switches; comparison/priority/source tabs work |
| Browser CSV download | Exactly the two baseline Wakefield intersection members; constituent values and flags retained |
| Browser errors/network | **0 page errors, 0 failed requests**; map uses no external basemap service |

The fresh acquisition/rebuild initially took about 85 seconds in this machine; this is an observation, not a performance guarantee. The resulting neighbourhood table, district summary, sensitivity table, peer groups and associations were compared with `pandas.testing.assert_frame_equal`. The final implementation was rebuilt against the same fresh files and those five comparisons passed again.

The full browser check used Chromium 154.0.8037.57 and Playwright 1.62.0 with software WebGL in the headless environment. It waits for the real map to load, uses the visible controls and downloads the actual CSV. It does not replace data or mock the app. Run it again with a running Streamlit instance:

```bash
python scripts/browser_smoke.py --chromium /usr/bin/chromium
```

Use the optional browser dependency/setup instructions in the README on another machine. `artifacts/browser_smoke.json` and `artifacts/reproduction_check.json` retain local run details and are intentionally ignored by Git. [The dashboard screenshot](../docs/images/dashboard.png) comes from the successful browser run.

The unit suite includes deliberate negative cases for impossible counts, partially missing sums, duplicate join keys, incompatible geography, invalid weights and changed original bytes. Real-data checks independently verify TS066 student inclusion, correct household denominators, SQL weighting, coverage and checksums. A configured-baseline regression test ensures sensitivity overlap is not silently compared against hidden default settings.

The GitHub Actions workflow runs offline calculation checks. It has not been run on GitHub in this task. Official-data integration tests explicitly skip when acquisition/build have not been performed; a checkout-only CI pass must not be described as full application verification. Browser tooling is optional and not part of the runtime dependency set.

Cloud environment **install_script** and **start_skill** instructions were saved as a draft after their relevant commands were tested. Existing official-domain network settings were preserved. Saving that draft does not publish the environment. Detailed routing, reliability analysis, BRES context and historical JTS comparisons were not attempted as part of this verified core.

"""Create the teaching notebook from a short, readable sequence of questions."""
from pathlib import Path
import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
cells = []
md = lambda text: cells.append(nbf.v4.new_markdown_cell(text))
code = lambda text: cells.append(nbf.v4.new_code_cell(text))
md("""# Access to Opportunity
## Neighbourhood transport accessibility in Leeds, Bradford and Wakefield

**Main question:** Which neighbourhoods combine weak modelled public-transport connectivity, many households without a car and high income deprivation?

Leeds and Bradford are the main study; Wakefield is the comparison. We use all eligible LSOA 2021 areas in the full districts. This notebook explores **official observed/modelled data**, not demonstration data. Start with `reports/feasibility.md`; run the acquisition and build commands in the README before executing this notebook.

Dates differ: Census 21 March 2021; DfT Q4 2024 label, 2025 release, mixed model inputs; income mainly March 2024 with mid-2022 denominators, 2025 release. This is descriptive analysis, not causal inference.""")
code("""from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd
import duckdb
import plotly.express as px

ROOT = Path.cwd()
if not (ROOT / 'config/study.yml').exists():
    ROOT = ROOT.parent
assert (ROOT / 'config/study.yml').exists(), 'Run from the project root or notebooks directory'
sys.path.insert(0, str(ROOT))
from opportunity.analysis import prioritise
from opportunity.visuals import distribution, association_plot

data = pd.read_parquet(ROOT / 'data/processed/neighbourhoods.parquet')
quality = json.loads((ROOT / 'reports/data_quality.json').read_text())
print(f'{len(data):,} LSOAs; {data.priority_eligible.sum():,} with complete core indicators')
data.groupby(['district_name', 'study_role']).size().rename('LSOAs').to_frame()""")
md("""### 1. Do the files actually answer our question?

Inspect the actual workbook sheet names and header—not just the publication title. The primary field is `Overall (public transport)`, combining purposes. It must not be called employment accessibility. The workbook's `Business (public transport)` label is retained but not interpreted as employment without clarification. DfT's `Overall` excludes driving. The 0–100 scores are not travel minutes, reachable-job counts or percentile ranks.""")
code("""inspection = json.loads((ROOT / 'metadata/dft_workbook_inspection.json').read_text())
display(pd.DataFrame([{'sheet': s['name'], 'nonempty_rows_including_headers': s['rows']} for s in inspection['sheets']]))
lsoa_sheet = next(s for s in inspection['sheets'] if s['name'] == 'LSOA')
display(pd.Series(lsoa_sheet['preview'][2], name='Actual LSOA header'))""")
md("""### 2. Are geography and denominators valid?

Joins are one-to-one and left-join onto an official lookup spine. A missing record remains missing. We do not directly join 2011 and 2021 codes. The unemployment rate includes active full-time students; it uses economically active age-16+ residents, while the employment and activity percentages use all age-16+ residents. TS045 uses households, not people.""")
code("""display(pd.DataFrame(quality['joins'])[['table', 'source_rows', 'matched', 'unmatched_codes', 'cardinality']])
assert data.lsoa_code.is_unique
assert len(data) == quality['boundary_count']
np.testing.assert_allclose(data.no_car_pct, 100 * data.households_no_car / data.households_total)
np.testing.assert_allclose(data.unemployment_pct, 100 * data.unemployed_16plus / data.active_16plus)
data[['lsoa_name', 'households_no_car', 'households_total', 'no_car_pct', 'adults_16plus', 'active_16plus', 'unemployed_16plus', 'unemployment_pct']].head()""")
md("""### 3. How do distributions differ within and between districts?

The boxplots give each LSOA equal weight. Do not reduce a district to its centre or its average. Then use SQL to distinguish a population-weighted connectivity mean from the unweighted neighbourhood mean, and the household-level no-car rate from an average of neighbourhood percentages.""")
code("""distribution(data, 'access_pt').show()
with duckdb.connect(str(ROOT / 'data/processed/opportunity.duckdb'), read_only=True) as con:
    summary = con.execute('''
        SELECT district_name, neighbourhoods,
               median_access, p10_access, p90_access,
               unweighted_mean_access, population_weighted_mean_access,
               household_no_car_pct, mean_neighbourhood_no_car_pct
        FROM district_summary ORDER BY median_access DESC
    ''').df()
summary.round(2)""")
md("""### 4. Do high need and weak access necessarily coincide?

Every point below is an LSOA; dot size represents income deprivation. Inspect the observed direction instead of expecting poorer areas always to have lower connectivity. Correlations are area-level descriptions; spatial clustering and omitted factors prevent a causal interpretation. Read the within-district results as well as the pooled result.""")
code("""association_plot(data).show()
pd.read_csv(ROOT / 'data/processed/associations.csv').round(3)""")
md("""### 5. Which neighbourhoods meet a transparent priority rule?

Baseline: all three adverse percentile standings must be at least 0.75 in the pooled study. Ties share a mid-percentile. A separate equal-weight composite averages those standings. An area can have a high composite without being in every adverse quartile.

This is a screening definition, not an official deprivation index, funding decision, probability or individual diagnosis.""")
code("""columns = ['lsoa_code', 'lsoa_name', 'district_name', 'access_pt', 'no_car_pct', 'income_pct', 'priority_score', 'triple_priority']
display(data.loc[data.triple_priority.fillna(False), columns].sort_values('priority_score', ascending=False))
display(data.nlargest(10, 'priority_score')[columns])""")
md("""### 6. How much do the priorities depend on our choices?

Compare adverse fifths, quartiles and thirds; equal, access-emphasis and income-emphasis weights; pooled, within-district and Leeds/Bradford reference groups. Weights affect the composite, not the all-three-tail rule. Jaccard is overlap divided by union; undefined when both sets are empty. Frequencies across scenarios describe sensitivity, not statistical confidence.""")
code("""scenarios = pd.read_csv(ROOT / 'data/processed/sensitivity.csv')
display(scenarios.loc[scenarios.weights.eq('equal')].round(3))
display(data.nlargest(10, 'priority_score')[['lsoa_name', 'triple_frequency', 'top_score_frequency', 'best_score_rank', 'worst_score_rank']])
baseline = set(data.loc[data.triple_priority.fillna(False), 'lsoa_code'])
alternative = set(data.loc[data.sustainable_triple_priority.fillna(False), 'lsoa_code'])
print('Primary all-tail areas:', len(baseline), 'Sustainable-mode alternative:', len(alternative))
print('Same membership:', baseline == alternative)""")
md("""### 7. What if we compare similar neighbourhoods?

Form joint tercile groups of income need, population density, age 0–14 share and age 65+ share. A supported group needs at least five areas across two districts. Show covariate ranges: the same bin does not mean identical characteristics. The group median includes the area itself. These are coarse descriptive peers, not matched causal controls.""")
code("""supported = data.loc[data.peer_supported.fillna(False)]
print(f'Peer-supported areas: {len(supported)} / {len(data)}')
display(supported.nsmallest(10, 'peer_access_gap')[['lsoa_name', 'district_name', 'access_pt', 'peer_group', 'peer_count', 'peer_districts', 'peer_median_access', 'peer_access_gap']])
groups = pd.read_csv(ROOT / 'data/processed/peer_groups.csv')
display(groups.head())""")
md("""### 8. What remains uncertain?

- Census 2021 reflects pandemic conditions and disclosure control; source years do not align.
- A neighbourhood average does not describe every resident; household car availability does not guarantee personal access.
- DfT assumes timetabled services. Reliability, fares, disability access and actual opportunities vary.
- Existing jobs are not vacancies; the score is not a count reachable within 30/45/60 minutes.
- Geography affects results; large rural polygons can dominate a map visually.
- Source model uncertainty is not provided, so we do not manufacture confidence intervals. The sensitivity grid measures our analytical choices only.
- DfT's workbook licence says TBA although the guidance states OGL. Preserve the discrepancy and attribution; raw files are not committed.

**Interview reflection:** Explain one decision you changed after inspecting the real files. Explain why the small three-tail intersection is a useful result rather than a reason to change the threshold. Choose an area from the complete export, inspect all its indicators and peer group, and describe what further evidence you would collect.

See `reports/findings.md` for computed conclusions and `docs/interview.md` for practice questions.""")
notebook = nbf.v4.new_notebook(cells=cells)
notebook.metadata['kernelspec'] = {'display_name': 'Access to Opportunity', 'language': 'python', 'name': 'opportunity'}
notebook.metadata['language_info'] = {'name': 'python', 'version': '3.12'}
destination = ROOT / 'notebooks/01_access_to_opportunity.ipynb'
destination.parent.mkdir(exist_ok=True)
nbf.write(notebook, destination)
print(destination)

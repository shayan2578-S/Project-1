"""Run with: streamlit run app.py. Uses only built, verified official data."""
from pathlib import Path
import json

import geopandas as gpd
import pandas as pd
import plotly.express as px
import streamlit as st
import yaml

from opportunity.analysis import prioritise
from opportunity.prepare import configuration_digest
from opportunity.visuals import LABELS, association_plot, distribution, neighbourhood_map, theme

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="Access to Opportunity", page_icon="◈", layout="wide")
st.markdown("""<style>
.block-container{max-width:1480px;padding-top:3.5rem;padding-bottom:3rem}
h1{font-weight:760!important;letter-spacing:-1.7px!important;font-size:3.25rem!important}
h2,h3{letter-spacing:-.5px!important}
.eyebrow{font-size:.78rem;letter-spacing:.15em;font-weight:700;color:#087f8c;text-transform:uppercase;margin-bottom:.3rem}
.intro{font-size:1.08rem;line-height:1.65;max-width:850px;color:#46616b}
.source-strip{border-top:1px solid #ceddd8;border-bottom:1px solid #ceddd8;padding:12px 0;margin:20px 0;color:#50646c;font-size:.85rem}
[data-testid="stMetric"]{background:#edf2ef;border-radius:9px;padding:15px;border-top:3px solid #8bb9ad}
[data-testid="stMetricValue"]{font-size:1.8rem}
.note{background:#fff2d9;padding:14px 18px;border-left:3px solid #d29b48;border-radius:4px;color:#654e2b}
</style>""", unsafe_allow_html=True)
st.markdown('<div class="eyebrow">West Yorkshire · Neighbourhood evidence</div>', unsafe_allow_html=True)
st.title("Access to Opportunity")
st.markdown('<div class="intro">Where do weaker transport connections meet greater economic need? Explore Leeds and Bradford, with Wakefield as a comparison, across the full local-authority districts.</div>', unsafe_allow_html=True)

manifest_path = ROOT / "data/processed/build_manifest.json"
if not manifest_path.exists():
    st.warning("The official-data analysis has not been built. Follow the README acquisition and build steps; this dashboard does not substitute demonstration data.")
    st.stop()
manifest = json.loads(manifest_path.read_text())
if manifest.get("status") != "passed" or manifest.get("configuration_sha256") != configuration_digest(ROOT):
    st.error("The analysis is out of date for the current study configuration. Rebuild it before viewing results.")
    st.stop()


@st.cache_data
def load_data(build_id):
    directory = ROOT / "data/processed"
    return (pd.read_parquet(directory / "neighbourhoods.parquet"),
            gpd.read_parquet(directory / "boundaries.parquet"),
            pd.read_csv(directory / "district_summary.csv"),
            pd.read_csv(directory / "sensitivity.csv"),
            pd.read_csv(directory / "peer_groups.csv"))


data, boundaries, district_summary, scenarios, peer_groups = load_data(manifest["built_at"])
study = yaml.safe_load((ROOT / "config/study.yml").read_text())
district_order = [item["name"] for item in study["districts"].values()]
st.sidebar.markdown("### Study area")
districts = st.sidebar.multiselect("Districts", district_order, default=district_order)
st.sidebar.caption("Leeds + Bradford: main study. Wakefield: comparison. All LSOAs in each selected district are included.")
with st.sidebar.expander("Priority definition", expanded=False):
    comparison = st.selectbox("Reference group", ["pooled", "district", "main_reference"],
                              format_func=lambda key: {"pooled": "All three districts", "district": "Within each district", "main_reference": "Leeds + Bradford reference"}[key])
    tail = st.select_slider("Adverse tail (%)", options=[20, 25, 100 / 3], value=25,
                            format_func=lambda value: f"{value:.1f}%")
    access_weight = st.slider("Poor access weight", 0, 3, 1)
    car_weight = st.slider("No-car weight", 0, 3, 1)
    income_weight = st.slider("Income need weight", 0, 3, 1)
    st.caption("Weights change the composite score. All-three-tail membership is a separate rule and does not use weights.")
if not districts:
    st.info("Select at least one district to explore its neighbourhoods.")
    st.stop()
if access_weight + car_weight + income_weight == 0:
    st.warning("Choose at least one positive weight.")
    st.stop()
scored = prioritise(data, tail / 100, comparison,
                     {"poor_access": access_weight, "no_car": car_weight, "income_need": income_weight})
view = scored.loc[scored["district_name"].isin(districts)].copy()
st.markdown('<div class="source-strip">CONNECTIVITY: Q4 2024 label · 2025 release &nbsp; / &nbsp; CENSUS: March 2021 &nbsp; / &nbsp; INCOME: mainly March 2024, mid-2022 denominator · 2025 release &nbsp; / &nbsp; LSOA 2021</div>', unsafe_allow_html=True)
metrics = st.columns(4)
metrics[0].metric("Neighbourhoods", f"{len(view):,}")
metrics[1].metric("Median PT connectivity", f"{view['access_pt'].median():.2f}", help="Unweighted LSOA median; a model score out of 100, not minutes or jobs.")
metrics[2].metric("In all three adverse tails", str(int(view["triple_priority"].fillna(False).sum())))
metrics[3].metric("Core indicator coverage", f"{view['priority_eligible'].mean():.0%}")
st.caption("Changing the district filter changes what is displayed. It does not silently change the selected reference group or rerank within the visible subset.")

explore, compare, priority, methods = st.tabs(["Explore neighbourhoods", "Compare districts", "Priority & sensitivity", "Methods & sources"])
with explore:
    left, right = st.columns([2.05, 1], gap="large")
    with left:
        metric = st.selectbox("Map indicator", ["access_pt", "no_car_pct", "income_pct", "priority_score", "peer_access_gap"], format_func=LABELS.get)
        if metric == "peer_access_gap":
            extent = scored[metric].abs().max()
            extent = float(extent) if pd.notna(extent) and extent > 0 else 1.0
            limits = (-extent, extent)
        elif metric == "access_pt":
            limits = (float(scored[metric].min()), float(scored[metric].max()))
        else:
            limits = (0, 100)
        st.plotly_chart(neighbourhood_map(view, boundaries, metric, limits), use_container_width=True, theme=None, key="neighbourhood_map")
        st.caption("Hover for all three constituent indicators; drag to pan and scroll to zoom. Grey means missing or an unsupported peer comparison. Large rural polygons occupy more space but do not represent more people. ONS boundaries; contains OS data © Crown copyright and database right 2026.")
    with right:
        st.subheader("A closer look")
        choices = view.sort_values(["district_name", "lsoa_name"])
        name_by_code = choices.set_index("lsoa_code")["lsoa_name"].to_dict()
        area = st.selectbox("Neighbourhood", choices["lsoa_code"].tolist(), format_func=lambda code: f"{name_by_code[code]} · {code}")
        row = view.set_index("lsoa_code").loc[area]
        st.markdown(f"**{row['lsoa_name']}**  \n{row['district_name']} · {row['study_role']} study area")
        st.dataframe(pd.DataFrame({"Indicator": ["PT connectivity / 100", "No-car households (%)", "Income deprivation (%)", "Unemployment, active 16+ (%)", "Review score / 100"],
                                   "Value": [row["access_pt"], row["no_car_pct"], row["income_pct"], row["unemployment_pct"], row["priority_score"]]}), hide_index=True, width="stretch",
                     column_config={"Value": st.column_config.NumberColumn(format="%.2f")})
        flag = row["triple_priority"]
        st.info("Meets all three adverse-tail conditions." if pd.notna(flag) and flag else "Does not meet all three adverse-tail conditions." if pd.notna(flag) else "Insufficient data for priority assessment.")
        count_label = lambda value: f"{int(value):,}" if pd.notna(value) else "Missing"
        st.caption(f"{count_label(row['households_no_car'])} no-car households / {count_label(row['households_total'])} households. No-car availability describes the household, not each resident's personal access.")
        st.markdown("**Compare with similar areas**")
        if pd.notna(row["peer_access_gap"]):
            st.write(f"Connectivity is {row['peer_access_gap']:+.2f} points from the median of {int(row['peer_count'])} areas in its income/density/age peer group, spanning {int(row['peer_districts'])} districts.")
        else:
            st.write("No supported peer comparison: at least five areas and two districts are required.")
        st.caption("Peer groups are coarse descriptive comparisons. This is not an estimated transport effect.")

with compare:
    st.subheader("Look within each district")
    measure = st.selectbox("Distribution indicator", ["access_pt", "no_car_pct", "income_pct", "access_walking", "access_cycling", "access_driving", "access_sustainable", "employment_overall"], format_func=LABELS.get)
    st.plotly_chart(distribution(view, measure), use_container_width=True, key="district_distribution")
    st.caption("Box: middle 50% of neighbourhoods; centre: median; whiskers: points within 1.5 IQR. Modes are independently scaled—compare places within a mode, not numerical differences between modes.")
    st.subheader("Keep weighting visible")
    columns = ["district_name", "neighbourhoods", "unweighted_mean_access", "population_weighted_mean_access", "household_no_car_pct", "mean_neighbourhood_no_car_pct"]
    st.dataframe(district_summary.loc[district_summary["district_name"].isin(districts), columns].rename(columns={
        "district_name": "District", "neighbourhoods": "LSOAs", "unweighted_mean_access": "Access: LSOA mean", "population_weighted_mean_access": "Access: population weighted", "household_no_car_pct": "No car: household weighted %", "mean_neighbourhood_no_car_pct": "No car: LSOA mean %"}), hide_index=True, width="stretch")
    st.caption("Connectivity weights: Census 2021 usual residents. Household percentage: sum of no-car households / sum of all households. These answer different summary questions.")
    st.plotly_chart(association_plot(view), use_container_width=True, key="association_plot")
    st.caption("Each dot is an LSOA. Larger dots indicate a higher income-deprivation percentage. These are area-level associations; transport cannot be claimed to cause unemployment.")

with priority:
    st.subheader("A review list, with the ingredients visible")
    st.markdown("All-three-tail membership requires weak connectivity **and** high no-car share **and** high income need. The separate composite averages their adverse percentile standings using your chosen weights.")
    only_flags = st.checkbox("Show only areas in all three adverse tails")
    priority_view = view.loc[view["triple_priority"].fillna(False)] if only_flags else view
    priority_columns = ["lsoa_code", "lsoa_name", "district_name", "access_pt", "no_car_pct", "income_pct", "priority_score", "triple_priority", "triple_frequency", "top_score_frequency"]
    st.dataframe(priority_view.sort_values(["priority_score", "lsoa_code"], ascending=[False, True])[priority_columns], hide_index=True, width="stretch",
                 column_config={"priority_score": st.column_config.NumberColumn("Review score", format="%.2f"), "triple_frequency": st.column_config.NumberColumn("All-tail scenario frequency", format="%.2f"), "top_score_frequency": st.column_config.NumberColumn("Score-band scenario frequency", format="%.2f")})
    st.download_button("Download displayed review list", priority_view[priority_columns].to_csv(index=False), "opportunity_review_list.csv", "text/csv")
    st.subheader("How sensitive is the answer?")
    st.caption("The fixed sensitivity grid always covers the full study, independently of sidebar choices. Frequencies use 27 scenarios: three tails × three reference groups × three weight sets. They are not confidence probabilities.")
    figure = px.bar(scenarios.loc[scenarios["weights"].eq("equal")], x="tail_fraction", y="triple_count", color="comparison_group", barmode="group",
                     labels={"tail_fraction": "Adverse tail fraction", "triple_count": "All-three-tail areas", "comparison_group": "Reference"})
    st.plotly_chart(theme(figure, 350), use_container_width=True, key="sensitivity_plot")
    st.dataframe(scenarios, hide_index=True, width="stretch")
    st.caption("Weights do not change the three-tail rule. They do change the composite-score band and its overlap with baseline. Switching to DfT's sustainable-mode overall score is recorded separately in the findings report.")

with methods:
    st.subheader("What this study can—and cannot—say")
    st.markdown("""The primary indicator is DfT **Overall (public transport)**. It covers multiple destination purposes and is not employment-only accessibility. The workbook's **Business (public transport)** label is left unresolved; it is not renamed. The overall sustainable-mode score excludes driving.

Income deprivation supplies the need measure; overall IMD and geographical barriers are excluded to avoid reusing accessibility within the need definition. TS045 uses households. TS066 unemployment uses economically active residents aged 16+, including economically active students. TS067 uses its own age-16+ denominator.

The study includes the full districts, preserves missing values, uses checked one-to-one LSOA 2021 joins and reports every source year. No direct 2011–2021 join is made. Census 2021 reflects the pandemic. Neighbourhood averages do not describe every individual; existing jobs are not vacancies. Scheduled services do not measure reliability. No new 30/45/60-minute reachable-job counts or causal unemployment effects are estimated.

The DfT workbook licence cell says **TBA**, although the GOV.UK guidance states OGL. Original files are linked rather than included in Git. ONS/Census/MHCLG attribution and the ONS/OS boundary licence are documented in the source register and README.""")
    quality = json.loads((ROOT / "reports/data_quality.json").read_text())
    st.write(f"Current build: {manifest['built_at'][:10]}. {quality['rows']:,} LSOAs, {quality['duplicate_codes']} duplicate codes, {quality['boundary_count']:,} valid polygons; {quality['peer_supported']} supported peer comparisons.")
    for title, file in [("Feasibility", "feasibility.md"), ("Data quality", "data_quality.md"), ("Findings", "findings.md")]:
        with st.expander(title):
            st.markdown((ROOT / "reports" / file).read_text())
    register = pd.read_csv(ROOT / "metadata/source_register.csv")
    st.download_button("Download source register", register.to_csv(index=False), "source_register.csv", "text/csv")
    st.dataframe(register[["publisher", "title", "reference_period", "geography_version", "status", "download_url"]], hide_index=True, width="stretch")
    st.caption("Sources: Department for Transport; Office for National Statistics via Nomis; Ministry of Housing, Communities and Local Government. ONS geography licensed under OGL v3.0; contains OS data © Crown copyright and database right 2026.")

st.divider()
st.caption("ACCESS TO OPPORTUNITY · Descriptive evidence for better questions. Modelled connectivity is one part of lived transport access.")

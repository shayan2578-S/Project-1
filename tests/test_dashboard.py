from pathlib import Path
import json

import geopandas as gpd
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from opportunity.visuals import neighbourhood_map

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(not (ROOT / "data/processed/build_manifest.json").exists(), reason="Official data must be built before UI tests")


def test_dashboard_renders_and_district_filter_preserves_full_coverage():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    assert not app.exception
    frame = pd.read_parquet(ROOT / "data/processed/neighbourhoods.parquet")
    assert app.metric[0].value == f"{len(frame):,}"
    app.sidebar.multiselect[0].set_value(["Wakefield"]).run()
    assert not app.exception
    assert app.metric[0].value == f"{frame['district_name'].eq('Wakefield').sum():,}"
    app.sidebar.multiselect[0].set_value([]).run()
    assert not app.exception
    assert any("Select at least" in message.value for message in app.info)


def test_priority_controls_and_neighbourhood_profile():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    # These controls change real calculations and must not crash or silently fail.
    app.sidebar.selectbox[0].set_value("district").run()
    assert not app.exception
    app.sidebar.select_slider[0].set_value(20).run()
    assert not app.exception
    app.checkbox[0].check().run()
    assert not app.exception
    app.sidebar.slider[0].set_value(0)
    app.sidebar.slider[1].set_value(0)
    app.sidebar.slider[2].set_value(0).run()
    assert not app.exception
    assert any("positive weight" in item.value for item in app.warning)


def test_map_has_actual_polygons_and_a_local_style():
    frame = pd.read_parquet(ROOT / "data/processed/neighbourhoods.parquet")
    boundaries = gpd.read_parquet(ROOT / "data/processed/boundaries.parquet")
    figure = neighbourhood_map(frame, boundaries, "access_pt", (0, 100)).to_plotly_json()
    assert len(figure["data"][0]["geojson"]["features"]) == len(frame)
    assert set(figure["data"][1]["locations"]) == set(frame["lsoa_code"])
    assert figure["layout"]["map"]["style"] == "white-bg"
    assert len(figure["data"]) == 2 + frame["district_name"].nunique()

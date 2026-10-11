"""Plotly figures shared by the dashboard and the exploratory notebook."""
from __future__ import annotations

import json

import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

DISTRICT_COLOURS = {"Leeds": "#087f8c", "Bradford": "#d76c3c", "Wakefield": "#69629b"}
LABELS = {
    "access_pt": "Public-transport connectivity",
    "access_sustainable": "Sustainable-mode connectivity",
    "access_walking": "Walking connectivity",
    "access_cycling": "Cycling connectivity",
    "access_driving": "Driving connectivity",
    "employment_overall": "Employment connectivity (published overall)",
    "no_car_pct": "Households without a car (%)",
    "income_pct": "Income deprivation (%)",
    "priority_score": "Priority review score",
    "peer_access_gap": "Connectivity minus peer median",
    "unemployment_pct": "Unemployed / economically active 16+ (%)",
}


def theme(figure: go.Figure, height: int = 440) -> go.Figure:
    figure.update_layout(template="plotly_white", height=height,
                         font=dict(family="Arial, sans-serif", color="#193742"),
                         paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         margin=dict(l=15, r=20, t=35, b=30), legend_title_text="",
                         colorway=list(DISTRICT_COLOURS.values()))
    return figure


def neighbourhood_map(frame: pd.DataFrame, boundaries: gpd.GeoDataFrame, metric: str,
                      limits: tuple[float, float]) -> go.Figure:
    selected = boundaries.loc[boundaries["lsoa_code"].isin(frame["lsoa_code"])].copy()
    if selected.empty:
        return theme(go.Figure(), 580)
    geojson = json.loads(selected.to_json(drop_id=True))
    figure = go.Figure()
    # Grey polygons make missing data explicit rather than silently blank or zero.
    figure.add_trace(go.Choroplethmap(
        geojson=geojson, featureidkey="properties.lsoa_code", locations=selected["lsoa_code"],
        z=[0] * len(selected), colorscale=[[0, "#d8dee2"], [1, "#d8dee2"]],
        showscale=False, marker_line_width=0.3, marker_line_color="#ffffff",
        hovertemplate="%{location}<br>No value for selected indicator<extra></extra>"))
    valid = frame.loc[frame[metric].notna()]
    custom = valid[["lsoa_name", "district_name", "access_pt", "no_car_pct", "income_pct"]].to_numpy()
    colours = [[0, "#e7f4ef"], [0.5, "#74bca8"], [1, "#075e68"]] if metric.startswith("access") else [[0, "#fff4dc"], [0.5, "#edb461"], [1, "#a33e37"]]
    if metric == "peer_access_gap":
        colours = [[0, "#bb4b3b"], [0.5, "#f5f4ec"], [1, "#13868a"]]
    figure.add_trace(go.Choroplethmap(
        geojson=geojson, featureidkey="properties.lsoa_code", locations=valid["lsoa_code"],
        z=valid[metric], zmin=limits[0], zmax=limits[1], colorscale=colours,
        marker_line_width=0.35, marker_line_color="#ffffff", customdata=custom,
        colorbar=dict(title=dict(text="Selected<br>indicator"), thickness=14, len=0.7),
        hovertemplate=("<b>%{customdata[0]}</b><br>%{customdata[1]} · %{location}<br>"
                       + LABELS[metric] + ": %{z:.2f}<br>"
                       "PT connectivity: %{customdata[2]:.2f}<br>"
                       "No-car households: %{customdata[3]:.1f}%<br>"
                       "Income deprivation: %{customdata[4]:.1f}%<extra></extra>")))
    outlines = selected.merge(frame[["lsoa_code", "district_name"]], on="lsoa_code", validate="one_to_one").dissolve(by="district_name")
    for name, row in outlines.iterrows():
        polygons = list(row.geometry.geoms) if row.geometry.geom_type == "MultiPolygon" else [row.geometry]
        lon, lat = [], []
        for polygon in polygons:
            x, y = polygon.exterior.xy
            lon.extend([*x, None]); lat.extend([*y, None])
        figure.add_trace(go.Scattermap(lon=lon, lat=lat, mode="lines", line=dict(color="#243d4b", width=1.6),
                                       name=name, hoverinfo="skip", showlegend=False))
    # A self-contained polygon map needs no access token or external base tiles.
    west, south, east, north = selected.total_bounds
    span = max(east - west, (north - south) / np.cos(np.radians((south + north) / 2)))
    zoom = float(np.clip(np.log2(360 / max(span, 0.01)) - 0.2, 5, 12))
    figure.update_layout(map=dict(style="white-bg", center=dict(lon=(west + east) / 2,
                         lat=(south + north) / 2), zoom=zoom),
                         uirevision="|".join(sorted(frame["district_name"].unique())))
    return theme(figure, 590)


def distribution(frame: pd.DataFrame, metric: str = "access_pt") -> go.Figure:
    figure = px.box(frame, x="district_name", y=metric, color="district_name", points=False,
                    color_discrete_map=DISTRICT_COLOURS, labels={"district_name": "District", metric: LABELS[metric]},
                    category_orders={"district_name": ["Leeds", "Bradford", "Wakefield"]})
    figure.update_layout(showlegend=False)
    return theme(figure, 380)


def association_plot(frame: pd.DataFrame) -> go.Figure:
    figure = px.scatter(frame, x="access_pt", y="no_car_pct", color="district_name", size="income_pct",
                        size_max=18, opacity=0.65, color_discrete_map=DISTRICT_COLOURS,
                        hover_name="lsoa_name", hover_data=["lsoa_code", "income_pct"],
                        labels={**LABELS, "district_name": "District"})
    return theme(figure, 460)

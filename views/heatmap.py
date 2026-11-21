"""Season Heatmap: every ward, every week of a year, coloured by risk tier."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dengue.config import TIERS
from ui_common import TIER_COLORS, get_engine, style_fig

engine = get_engine()
c = st.session_state["controls"]
h = c["horizon"]

st.title("Season Heatmap")
st.caption("Each cell is the risk tier the system would have issued for that ward and week "
           f"({h} weeks ahead). Use it to see how an outbreak spreads across wards and plan teams city by city.")

years = sorted({d.year for d in engine.forecast_weeks()})[1:]
a, b = st.columns([1, 2])
year = a.selectbox("Year", years, index=years.index(c["as_of"].year) if c["as_of"].year in years else len(years) - 1)
view = b.radio("Show", ["Forecast tier", "Actual tier", "Forecast error (cases)"], horizontal=True)


@st.cache_data(show_spinner=False)
def grid(year: int, h: int, city):
    return get_engine().season_grid(year, h, city)


g = grid(year, h, c["city"])
if year <= engine.train_end.year:
    st.info(f"{year} is inside the training period. Pick 2024 or 2025 to see forecasts on unseen data.")

g = g[(g["target_week"].dt.month >= 4) & (g["target_week"].dt.month <= 11)]  # dengue season, readable width
order = g.groupby(["city", "ward_id"])["pred"].sum().reset_index().sort_values(["city", "pred"])
wards = order["ward_id"].tolist()

if view == "Forecast error (cases)":
    z = g.pivot(index="ward_id", columns="target_week", values="pred") - g.pivot(index="ward_id", columns="target_week", values="actual")
    z = z.reindex(wards)
    lim = float(np.nanpercentile(np.abs(z.values), 98)) or 1
    fig = go.Figure(go.Heatmap(
        z=z.values, x=z.columns, y=z.index, zmin=-lim, zmax=lim, zmid=0,
        colorscale=[[0, "#2a78d6"], [0.5, "#f0efec"], [1, "#e34948"]],
        colorbar=dict(title="Forecast − actual"), xgap=1, ygap=1,
        hovertemplate="%{y}<br>Week of %{x|%d %b}<br>Error %{z:+.1f} cases<extra></extra>",
    ))
    fig.update_layout(title="Over-forecast (red) vs under-forecast (blue)")
else:
    col = "pred" if view == "Forecast tier" else "actual"
    from dengue.tiers import tier_index
    g = g.assign(level=tier_index(g[col].fillna(0)))
    z = g.pivot(index="ward_id", columns="target_week", values="level").reindex(wards)
    p = g.pivot(index="ward_id", columns="target_week", values="pred").reindex(wards)
    act = g.pivot(index="ward_id", columns="target_week", values="actual").reindex(wards)
    scale = []
    for i, t in enumerate(TIERS):
        scale += [[i / 4, TIER_COLORS[t]], [(i + 1) / 4, TIER_COLORS[t]]]
    fig = go.Figure(go.Heatmap(
        z=z.values, x=z.columns, y=z.index, zmin=-0.5, zmax=3.5, colorscale=scale, xgap=1, ygap=1,
        customdata=np.dstack([p.values, act.values]),
        colorbar=dict(tickvals=[0, 1, 2, 3], ticktext=list(TIERS), title="Tier", len=0.35, y=1, yanchor="top", thickness=14),
        hovertemplate="%{y}<br>Week of %{x|%d %b}<br>Forecast %{customdata[0]:.1f} · actual %{customdata[1]:.0f}<extra></extra>",
    ))
    fig.update_layout(title=f"{view}, {c['city_label']}, {year} (Apr-Nov)")

fig.update_yaxes(tickfont=dict(size=10), autorange="reversed")
st.plotly_chart(style_fig(fig, height=max(420, 16 * len(wards) + 120), legend=False), use_container_width=True)

"""Season calendar: every ward, every week of a season, coloured by risk level."""
import numpy as np
import plotly.graph_objects as go
import streamlit as st

from dengue.config import TIERS
from dengue.tiers import tier_index
from ui_common import (RAIN, TIER_COLORS, UP, get_engine, html, page_header, style_fig, tier_legend,
                       ward_name)

engine = get_engine()
c = st.session_state["controls"]
h = c["horizon"]

years = sorted({d.year for d in engine.forecast_weeks()})[1:]
year_default = c["as_of"].year if c["as_of"].year in years else years[-1]
head = st.container()
a, b = st.columns([1, 3])
year = a.selectbox("Season", years, index=years.index(year_default))
view = b.segmented_control("Show", ["What we forecast", "What really happened", "Where we were off"],
                           default="What we forecast", key="cal_view") or "What we forecast"

with head:
    page_header(
        "Season calendar", f"How the {year} dengue season unfolded, ward by ward",
        f"Each row is a ward and each column is a week from April to November. The colour shows the risk level "
        f"DengueWatch warned about {h} weeks before that week. Read left to right to see an outbreak spread "
        f"and to plan teams city by city.",
    )


@st.cache_data(show_spinner=False)
def grid(year: int, h: int, city):
    return get_engine().season_grid(year, h, city)


g = grid(year, h, c["city"])
if year <= engine.train_end.year:
    st.info(f"{year} is part of the data the model learned from. Pick 2024 or 2025 to see forecasts on years it never saw.")

g = g[(g["target_week"].dt.month >= 4) & (g["target_week"].dt.month <= 11)].assign(name=lambda d: d["ward_id"].map(ward_name))
order = g.groupby(["city", "name"])["pred"].sum().reset_index().sort_values(["city", "pred"], ascending=[True, False])
wards = order["name"].tolist()

if view == "Where we were off":
    z = g.pivot(index="name", columns="target_week", values="pred") - g.pivot(index="name", columns="target_week", values="actual")
    z = z.reindex(wards)
    lim = float(np.nanpercentile(np.abs(z.values), 98)) or 1
    fig = go.Figure(go.Heatmap(
        z=z.values, x=z.columns, y=z.index, zmin=-lim, zmax=lim, zmid=0,
        colorscale=[[0, RAIN], [0.5, "#F3F1EC"], [1, UP]], xgap=2, ygap=2,
        colorbar=dict(title=dict(text="Forecast minus real", side="right"), thickness=12, len=0.5, y=1, yanchor="top",
                      outlinewidth=0),
        hovertemplate="%{y}<br>Week of %{x|%d %b}<br>Off by %{z:+.1f} cases<extra></extra>",
    ))
    note = (f"Warm cells: the forecast was too high. Cool cells: it was too low. Pale cells: close to right. "
            f"Most misses are a few cases in the busiest weeks.")
else:
    col = "pred" if view == "What we forecast" else "actual"
    g = g.assign(level=tier_index(g[col].fillna(0)))
    z = g.pivot(index="name", columns="target_week", values="level").reindex(wards)
    p = g.pivot(index="name", columns="target_week", values="pred").reindex(wards)
    act = g.pivot(index="name", columns="target_week", values="actual").reindex(wards)
    scale = []
    for i, t in enumerate(TIERS):
        scale += [[i / 4, TIER_COLORS[t]], [(i + 1) / 4, TIER_COLORS[t]]]
    fig = go.Figure(go.Heatmap(
        z=z.values, x=z.columns, y=z.index, zmin=-0.5, zmax=3.5, colorscale=scale, xgap=2, ygap=2, showscale=False,
        customdata=np.dstack([p.values, act.values]),
        hovertemplate="%{y}<br>Week of %{x|%d %b}<br>Forecast %{customdata[0]:.1f} cases · real %{customdata[1]:.0f}<extra></extra>",
    ))
    note = ("Compare this with “What really happened” to see how closely the warnings matched reality."
            if view == "What we forecast" else
            "Real case counts, coloured with the same risk levels, so you can compare them with the forecast.")

fig.update_xaxes(dtick="M1", tickformat="%b", showgrid=False)
fig.update_yaxes(tickfont=dict(size=10), autorange="reversed", showgrid=False)
st.plotly_chart(style_fig(fig, height=max(440, 15 * len(wards) + 60), legend=False), width="stretch")
html(tier_legend() if view != "Where we were off" else "")
st.caption(note + " Wards are grouped by city, busiest first.")

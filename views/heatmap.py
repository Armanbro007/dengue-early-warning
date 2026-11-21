"""Season calendar: every ward, every week of a season, coloured by risk level."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ui_text as tx
from dengue.config import TIERS
from dengue.tiers import tier_index
from ui_common import (RAIN, TIER_COLORS, UP, card_head, get_engine, html, keep_choice, page_header, remember,
                       style_fig, tier_legend, ward_name)

engine = get_engine()
c = st.session_state["controls"]
h = c["horizon"]
n = tx.num

years = sorted({d.year for d in engine.forecast_weeks()})[1:]
year_default = c["as_of"].year if c["as_of"].year in years else years[-1]
head = st.container()
a, b = st.columns([1, 3])
labels, back, key = keep_choice("hm_year", years, lambda y: n(y, "{}"), year_default)
year = remember("hm_year", back[a.selectbox(tx.t("hm_season"), labels, key=key)])
labels, back, key = keep_choice("hm_view", ["fc", "real", "off"], lambda v: tx.t(f"hm_v_{v}"), "fc")
view = remember("hm_view", back[b.segmented_control("Show", labels, key=key, required=True, label_visibility="collapsed")])
picked = tx.t(f"hm_v_{view}")

with head:
    page_header(tx.t("hm_eyebrow"), tx.t("hm_title", year=n(year, "{}")), tx.t("hm_lead", h=n(h)))


@st.cache_data(show_spinner=False)
def grid(year: int, h: int, city):
    return get_engine().season_grid(year, h, city)


g = grid(year, h, c["city"])
if year <= engine.train_end.year:
    st.info(tx.t("hm_train", year=n(year, "{}")))

g = g[(g["target_week"].dt.month >= 4) & (g["target_week"].dt.month <= 11)].assign(name=lambda d: d["ward_id"].map(ward_name))
order = g.groupby(["city", "name"])["pred"].sum().reset_index().sort_values(["city", "pred"], ascending=[True, False])
wards = order["name"].tolist()


def pivot(col: str) -> pd.DataFrame:
    return g.pivot(index="name", columns="target_week", values=col).reindex(wards)


p, act = pivot("pred"), pivot("actual")
weeks = [tx.short(w) for w in p.columns]
fmt = lambda v, f="{:.0f}": "–" if pd.isna(v) else n(v, f)  # noqa: E731

if view == "off":
    z = p - act
    lim = float(np.nanpercentile(np.abs(z.values), 98)) or 1
    hover = [[tx.t("hm_hover_off", ward=w, d=d, v=fmt(v, "{:+.1f}")) for d, v in zip(weeks, rowv)]
             for w, rowv in zip(z.index, z.values)]
    fig = go.Figure(go.Heatmap(
        z=z.values, x=z.columns, y=z.index, zmin=-lim, zmax=lim, zmid=0, text=hover,
        colorscale=[[0, RAIN], [0.5, "#F4F5F8"], [1, UP]], xgap=2, ygap=2,
        colorbar=dict(title=dict(text=tx.t("hm_cb"), side="right"), thickness=12, len=0.5, y=1, yanchor="top",
                      outlinewidth=0),
        hovertemplate="%{text}<extra></extra>",
    ))
    note = tx.t("hm_note_off")
else:
    col = "pred" if view == "fc" else "actual"
    g = g.assign(level=tier_index(g[col].fillna(0)))
    z = pivot("level")
    hover = [[tx.t("hm_hover", ward=w, d=d, p=fmt(pv, "{:.1f}"), a=fmt(av)) for d, pv, av in zip(weeks, pr, ar)]
             for w, pr, ar in zip(z.index, p.values, act.values)]
    scale = []
    for i, t in enumerate(TIERS):
        scale += [[i / 4, TIER_COLORS[t]], [(i + 1) / 4, TIER_COLORS[t]]]
    fig = go.Figure(go.Heatmap(
        z=z.values, x=z.columns, y=z.index, zmin=-0.5, zmax=3.5, colorscale=scale, xgap=2, ygap=2, showscale=False,
        text=hover, hovertemplate="%{text}<extra></extra>",
    ))
    note = tx.t("hm_note_fc") if view == "fc" else tx.t("hm_note_real")

with st.container(key="glass_calendar"):
    html(card_head(picked, f"{note} {tx.t('hm_group')}", "grid"))
    cols = pd.Series(z.columns)
    firsts = cols.groupby(cols.dt.to_period("M")).min()  # label each month at its first week
    fig.update_xaxes(tickvals=list(firsts), ticktext=[tx.month_ticks(d, d)[1][0] for d in firsts], showgrid=False, side="top")
    fig.update_yaxes(tickfont=dict(size=10), autorange="reversed", showgrid=False)
    st.plotly_chart(style_fig(fig, height=max(440, 15 * len(wards) + 60), legend=False), width="stretch",
                    config={"displayModeBar": False})
    html(tier_legend() if view != "off" else "")
    st.write("")

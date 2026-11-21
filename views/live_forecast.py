"""Live forecast: this week's real weather from Open-Meteo (one call, cached, with fallbacks)."""
import time

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ui_text as tx
from dengue import config, weather_api
from dengue.config import TIERS
from ui_common import (TIER_COLORS, card_head, driver_name, get_engine, html, icon, page_header, section,
                       style_fig, tier_cell_style, tier_legend, ward_name)

engine = get_engine()
c = st.session_state["controls"]
h = c["horizon"]
n = tx.num
ttl = config.WEATHER_CACHE_TTL_H

page_header(tx.t("lv_eyebrow"), tx.t("lv_title"), tx.t("lv_lead", ttl=n(ttl)))


@st.cache_data(ttl=600, show_spinner=False)
def load_weather(nonce: int):
    return weather_api.get_weekly_weather(get_engine().raw, force_refresh=bool(nonce))


top_row = st.columns([3, 1], vertical_alignment="center")
if top_row[1].button(tx.t("lv_refresh"), icon=":material/refresh:", help=tx.t("lv_refresh_help")):
    st.session_state["wx_nonce"] = st.session_state.get("wx_nonce", 0) + 1
with st.spinner(tx.t("lv_spin")):
    res = load_weather(st.session_state.get("wx_nonce", 0))

ok = res.source in ("live", "cache")
if tx.lang() == "bn":  # the weather module reports in English; say the same thing in Bangla
    age = (time.time() - res.fetched_at) / 3600 if res.fetched_at else 0
    message = tx.t(f"lv_msg_{res.source}", age=n(age, "{:.1f}" if res.source == "cache" else "{:.0f}"), ttl=n(ttl))
else:
    message = res.message
with top_row[0]:
    html(f'<div class="dw-callout"><div class="ib" style="background:{"#111318" if ok else TIER_COLORS["Medium"]};'
         f'color:#fff;border:none">{icon("check" if ok else "clock", 16)}</div><div><b>{tx.t("lv_src_" + res.source)}{"।" if tx.lang() == "bn" else "."}</b>'
         f'<br><span class="dw-meta">{message}</span></div></div>')

fc = engine.forecast_from_city_weather(res.weekly, h)
if c["city"]:
    fc = fc[fc["city"] == c["city"]]
as_of = fc["date"].max()

section(tx.t("lv_section", date=tx.date(as_of + pd.Timedelta(weeks=h))),
        tx.t("lv_section_sub", date=tx.date(as_of), h=n(h)))
with st.container(key="dark_live"):
    k = st.columns(4)
    for i, t in enumerate(TIERS[::-1]):
        k[i].metric(tx.t("lv_m", tier=tx.tier(t)), n(int((fc["tier"] == t).sum())))
st.write("")

a, b = st.columns([3, 2], gap="small")
with a, st.container(key="glass_rain"):
    html(card_head(tx.t("lv_rain"), tx.t("lv_rain_sub"), "rain"))
    wk = res.weekly if not c["city"] else res.weekly[res.weekly["city"] == c["city"]]
    fig = go.Figure()
    for city, color in zip(sorted(wk["city"].unique()), ["#111318", "#E95A2C", "#5B8DEF", "#D9A82E", "#A61E4D"]):
        d = wk[wk["city"] == city]
        fig.add_scatter(x=d["date"], y=d["rainfall_mm"], name=tx.city(city), mode="lines+markers",
                        line=dict(color=color, width=2), marker=dict(size=8, line=dict(color="white", width=2)),
                        customdata=[tx.t("lv_rain_hover", city=tx.city(city), d=tx.short(x), mm=n(v))
                                    for x, v in zip(d["date"], d["rainfall_mm"])],
                        hovertemplate="%{customdata}<extra></extra>")
    tv, tt = tx.week_ticks(wk["date"], every=2)
    fig.update_layout(yaxis_title=tx.t("rain_axis"))
    fig.update_xaxes(tickvals=tv, ticktext=tt)
    st.plotly_chart(style_fig(fig, height=330), width="stretch", config={"displayModeBar": False})

with b, st.container(key="glass_top"):
    html(card_head(tx.t("lv_top"), tx.t("lv_top_sub"), "list"))
    top = fc.head(12).assign(ward=lambda d: d["ward_id"].map(ward_name), reason=lambda d: d["main_driver"].map(driver_name),
                             tier=lambda d: d["tier"].map(tx.tier))
    st.dataframe(
        top[["ward", "tier", "pred", "reason"]].style.map(tier_cell_style, subset=["tier"])
        .format({"pred": lambda v: n(v, "{:.1f}")}),
        hide_index=True, width="stretch", height=330,
        column_config={"ward": st.column_config.Column(tx.t("col_ward"), width=170), "tier": tx.t("col_risk"),
                       "pred": st.column_config.Column(tx.t("col_cases"), help=tx.t("col_cases_help")),
                       "reason": tx.t("col_reason")},
    )
html(tier_legend())
st.caption(tx.t("lv_cap"))

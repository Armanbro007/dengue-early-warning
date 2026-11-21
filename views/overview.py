"""Overview: the answer first (dark card), then trend, reality check, cities and the wards to act on."""
import json
import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ui_text as tx
from dengue import config
from dengue.config import TIERS
from dengue.tiers import tier_of
from ui_common import (INK, MUTED, TIER_COLORS, TIER_SOFT, about, cached_forecast, case_range, get_engine, html,
                       icon, page_header, style_fig, tier_pill)

engine = get_engine()
c = st.session_state["controls"]
as_of, h = c["as_of"], c["horizon"]
target = as_of + pd.Timedelta(weeks=h)
fc = cached_forecast(str(as_of.date()), h, c["city"])
area = tx.t("area_all") if c["city"] is None else tx.city(c["city"])

HIGH = ("High", "Critical")
n = len(fc)
alert = fc["tier"].isin(HIGH)
n_alert = int(alert.sum())
counts = fc["tier"].value_counts()

page_header(tx.t("ov_eyebrow", date=tx.date(as_of), h=tx.num(h)), tx.t("ov_title", day=tx.day(target)))

# ---- Row 1: answer, trend, reality check ------------------------------------------------
a, b, r = st.columns([5, 4.3, 2.7], gap="small")
with a:
    sub = tx.t("ov_big_sub", day=tx.day(target)) if n_alert else tx.t("ov_none_sub", day=tx.day(target))
    tiles = [(tx.num(int(counts.get("Critical", 0))), tx.t("ov_t_critical"), ""),
             (tx.num(int(counts.get("High", 0))), tx.t("ov_t_high"), ""),
             (tx.num(int(fc["escalating"].sum())), tx.t("ov_t_worse"), " hl"),
             (tx.num(fc["pred"].sum()), tx.t("ov_t_cases"), "")]
    html(f'<div class="dk" style="min-height:338px"><div class="ch"><div><div class="mono" style="color:rgba(255,255,255,.55)">'
         f'{tx.t("ov_card_label", h=tx.num(h)).upper() if tx.lang() == "en" else tx.t("ov_card_label", h=tx.num(h))}</div></div>'
         f'<div class="ib">{icon("target", 16)}</div></div>'
         f'<div class="big">{tx.num(n_alert)}<span class="of"> / {tx.num(n)}</span></div><div class="bigsub">{sub}</div>'
         '<div class="tiles">' + "".join(f'<div class="tile{cls}"><div class="v">{v}</div><div class="k">{k}</div></div>'
                                         for v, k, cls in tiles) + "</div></div>")

with b:
    with st.container(key="glass_trend"):
        raw = engine.raw if c["city"] is None else engine.raw[engine.raw["city"] == c["city"]]
        weekly = raw.groupby("date")["dengue_cases"].sum()
        past = weekly[(weekly.index <= as_of) & (weekly.index > as_of - pd.Timedelta(weeks=14))]
        fc_total = float(fc["pred"].sum())
        real_target = weekly.get(target, float("nan"))
        html(f'<div class="ch" style="margin-bottom:0"><div><h3>{tx.t("ov_trend", area=area, area_of=tx.city_of(c["city"]))}</h3>'
             f'<p>{tx.t("ov_trend_sub", day=tx.day(target))}</p></div><div class="ib">{icon("trend", 16)}</div></div>')
        fig = go.Figure()
        fig.add_scatter(x=past.index, y=past.values, mode="lines", line=dict(color=INK, width=2, shape="spline", smoothing=0.6),
                        fill="tozeroy", fillcolor="rgba(17,19,24,0.05)", name=tx.t("ov_trend_real"),
                        hovertemplate="%{x|%d %b}: %{y:.0f}<extra></extra>")
        fig.add_scatter(x=[as_of, target], y=[past.iloc[-1], fc_total], mode="lines+markers",
                        line=dict(color=TIER_COLORS["High"], width=2, dash="dot"),
                        marker=dict(size=[0, 11], color=TIER_COLORS["High"], line=dict(color="white", width=2)),
                        name=tx.t("ov_trend_fc"), hovertemplate="%{x|%d %b}: ~%{y:.0f}<extra></extra>")
        if not math.isnan(real_target):
            fig.add_scatter(x=[target], y=[real_target], mode="markers", name=tx.t("ov_trend_real"), showlegend=False,
                            marker=dict(size=11, color="white", line=dict(color=INK, width=2)),
                            hovertemplate="%{x|%d %b}: %{y:.0f}<extra></extra>")
        fig.add_annotation(x=target, y=fc_total, text=f"~{tx.num(fc_total)}", showarrow=False, yshift=16,
                           font=dict(color=INK, size=12))
        fig.update_layout(hovermode="closest")
        tv, tt = tx.month_ticks(past.index.min(), target)
        fig.update_xaxes(tickvals=tv, ticktext=tt, showgrid=False)
        fig.update_yaxes(nticks=4)
        st.plotly_chart(style_fig(fig, height=236, legend=True), width="stretch", config={"displayModeBar": False})

with r:
    if fc["actual"].notna().all():
        real = pd.Series(tier_of(fc["actual"]), index=fc.index).isin(HIGH)
        n_real, hit = int(real.sum()), int((real & alert).sum())
        pct = hit / n_real if n_real else 1.0
        text = tx.t("ov_check_text", hit=tx.num(hit), real=tx.num(n_real), h=tx.num(h))
    else:
        m = json.loads(config.METRICS_PATH.read_text())
        pct = m["test"][str(h)]["model"]["high_critical_recall"]
        text = tx.t("ov_check_future", pct=tx.num(f"{pct:.0%}"))
    C = 2 * math.pi * 50
    ring = (f'<svg width="128" height="128" viewBox="0 0 128 128" role="img" aria-label="{pct:.0%}">'
            f'<circle cx="64" cy="64" r="50" fill="none" stroke="rgba(17,19,24,.08)" stroke-width="12"/>'
            f'<circle cx="64" cy="64" r="50" fill="none" stroke="{INK}" stroke-width="12" stroke-linecap="round" '
            f'stroke-dasharray="{pct * C:.1f} {C:.1f}" transform="rotate(-90 64 64)"/>'
            f'<text x="64" y="66" text-anchor="middle" font-size="26" font-weight="650" fill="{INK}" '
            f'font-family="Geist, sans-serif">{tx.num(f"{pct:.0%}")}</text>'
            f'<text x="64" y="85" text-anchor="middle" font-size="11" fill="{MUTED}">{tx.t("ov_caught")}</text></svg>')
    html(f'<div class="gc" style="min-height:338px"><div class="ch"><div><h3>{tx.t("ov_check")}</h3></div>'
         f'<div class="ib">{icon("check", 16)}</div></div><div style="display:grid;place-items:center;margin:6px 0 14px">{ring}</div>'
         f'<p style="font-size:.86rem;color:#4B5160;line-height:1.5;margin:0">{text}</p></div>')

st.write("")

# ---- Row 2: cities and the wards to act on ----------------------------------------------
left, right = st.columns([4, 8], gap="small")
with left:
    all_fc = cached_forecast(str(as_of.date()), h, None)
    rows = []
    for city, d in all_fc.groupby("city", sort=True):
        cnt = d["tier"].value_counts()
        k = int(d["tier"].isin(HIGH).sum())
        bar = "".join(f'<span style="width:{cnt.get(t, 0) / len(d) * 100:.2f}%;background:{TIER_COLORS[t]}" '
                      f'title="{tx.tier(t)}: {cnt.get(t, 0)}"></span>' for t in TIERS if cnt.get(t, 0))
        dim = "" if c["city"] in (None, city) else ' style="opacity:.45"'
        rows.append(f'<div class="crow"{dim}><div class="n">{tx.city(city)}</div>'
                    f'<div class="c"><b>{tx.num(k)}</b> / {tx.num(len(d))}</div><div class="dw-stack">{bar}</div></div>')
    legend = "".join(f'<span>{tier_pill(t)}</span>' for t in TIERS)
    html(f'<div class="gc"><div class="ch"><div><h3>{tx.t("ov_cities")}</h3><p>{tx.t("ov_cities_sub", h=tx.num(h))}</p></div>'
         f'<div class="ib">{icon("map", 16)}</div></div>{"".join(rows)}<div class="dw-legend">{legend}</div></div>')

with right:
    with st.container(key="glass_act"):
        esc = fc[fc["escalating"]]
        pick = pd.concat([esc, fc[alert & ~fc["escalating"]]]).head(6) if n_alert else fc.head(6)
        title = tx.t("ov_act") if n_alert else tx.t("ov_watch")
        sub = tx.t("ov_act_sub") if len(esc) else ""
        cards = []
        for w in pick.itertuples():
            bg, _ = TIER_SOFT[w.tier]
            pct = (w.breeding_rain_mm / max(w.breeding_rain_normal_mm, 1) - 1) * 100
            reason = (f'{tx.t("ov_rain").capitalize()} {tx.num(f"{pct:+.0f}%")}' if w.main_driver.startswith("Rainfall")
                      else tx.driver(w.main_driver))
            cards.append(
                f'<div class="wc" style="background:{bg}"><div class="top"><div><div class="nm">{tx.ward(w.ward_id)}</div>'
                f'<div class="ct">{tx.city(w.city)}</div></div><div class="ib" style="width:28px;height:28px">{icon("arrow_ur", 14)}</div></div>'
                f'<div class="chg">{tier_pill(w.tier_now)} {icon("arrow", 12)} {tier_pill(w.tier)}</div>'
                f'<div class="v">{about(w.pred)}<small>{tx.t("ov_cases")}</small></div>'
                f'<div class="bar"><span style="width:{min(w.pred / 15, 1) * 100:.0f}%;background:{TIER_COLORS[w.tier]}"></span></div>'
                f'<div class="ft"><span>{tx.t("ov_likely", lo=case_range(w.lo, w.hi).split("–")[0], hi=case_range(w.lo, w.hi).split("–")[1])}</span>'
                f'<span class="pl">{reason}</span></div></div>')
        html(f'<div class="ch"><div><h3>{title}</h3><p>{sub}</p></div></div><div class="wgrid">{"".join(cards)}</div>')
        st.write("")
        st.page_link("views/risk_board.py", label=tx.t("ov_see_all"), icon=":material/arrow_forward:", icon_position="right")

st.write("")

# ---- Row 3: how it works ----------------------------------------------------------------
steps = [("rain", 1, ""), ("clock", 2, ""), ("pulse", 3, ""), ("bell", 4, " hl")]
html(f'<div class="gc"><div class="ch"><div><h3>{tx.t("ov_how")}</h3><p>{tx.t("ov_how_sub")}</p></div></div><div class="steps">' +
     "".join(f'<div class="st{cls}"><div class="ic">{icon(ic, 20)}</div><div class="w">{tx.t(f"step{i}_when")}</div>'
             f'<div class="t">{tx.t(f"step{i}_what")}</div><p>{tx.t(f"step{i}_text")}</p></div>' for ic, i, cls in steps)
     + "</div></div>")

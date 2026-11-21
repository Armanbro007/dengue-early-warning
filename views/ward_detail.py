"""Why this ward? The reasons behind one ward's forecast, a rain what-if and its track record."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ui_text as tx
from dengue.explain import DRIVER_GROUPS
from dengue.tiers import tier_of
from ui_common import (DOWN, INK, INK2, MUTED, RAIN, TIER_COLORS, UP, about, cached_forecast, card_head, case_range,
                       driver_name, get_engine, html, keep_choice, page_header, remember, section, style_fig, tier_pill,
                       ward_name)

engine = get_engine()
c = st.session_state["controls"]
as_of, h = c["as_of"], c["horizon"]
target = as_of + pd.Timedelta(weeks=h)
fc = cached_forecast(str(as_of.date()), h, c["city"])
by_ward = fc.set_index("ward_id")
n = tx.num

head = st.container()  # filled after the ward is chosen, but shown above the picker
pick, _ = st.columns([1, 2])
labels, back, key = keep_choice("wd_ward", fc["ward_id"].tolist(),
                                lambda w: f"{ward_name(w)} · {tx.tier(by_ward.loc[w, 'tier'])}", fc["ward_id"].iloc[0])
ward = remember("wd_ward", back[pick.selectbox(tx.t("wd_pick"), labels, key=key)])
row = by_ward.loc[ward]
groups = sorted(DRIVER_GROUPS, key=lambda g: row[g], reverse=True)
up = groups[0]
pct = (row["breeding_rain_mm"] / max(row["breeding_rain_normal_mm"], 1) - 1) * 100
top_driver = driver_name(up).lower() if tx.lang() == "en" else driver_name(up)
reason = tx.t("wd_reason", d=top_driver) if row[up] > 0.05 else tx.t("wd_reason_none")

with head:
    page_header(
        tx.t("wd_eyebrow"), f"{ward_name(ward)}, {tx.city(row['city'])}",
        tx.t("wd_lead", n=about(row["pred"]), date=tx.date(target), range=case_range(row["lo"], row["hi"]),
             base=about(row["baseline"]), reason=reason, mm=n(row["breeding_rain_mm"]), pct=n(abs(pct)),
             dir=tx.t("more") if pct >= 0 else tx.t("less")),
    )
actual = "" if pd.isna(row["actual"]) else (
    f'<div><div class="k">{tx.t("wd_real")}</div><span class="dw-meta" style="color:{INK};font-weight:600">'
    f'{tx.t("wd_real_cases", n=n(row["actual"]))} · </span>{tier_pill(str(tier_of([row["actual"]])[0]))}</div>')
html(f'<div class="dw-change" style="gap:18px;margin:-.6rem 0 1rem"><div><div class="k">{tx.t("col_today")}</div>'
     f'{tier_pill(row["tier_now"])}</div><div><div class="k">{tx.t("col_in", h=n(h))}</div>{tier_pill(row["tier"])}</div>'
     f'{actual}</div>', head)

left, right = st.columns(2, gap="small")

# ---- Reasons -----------------------------------------------------------------------
with left:
    vals = {g: float(row[g]) for g in DRIVER_GROUPS}
    span = max(max(abs(v) for v in vals.values()), 0.5)
    rows = [f'<div class="dw-bar"><div class="lbl">{tx.t("wd_norm")}<div class="dw-meta">{tx.t("wd_norm_sub")}</div></div>'
            f'<div></div><div class="val">{n(row["baseline"], "{:.1f}")}</div></div>']
    for g in groups:
        v = vals[g]
        w = abs(v) / span * 50
        pos = f"left:50%;width:{w:.1f}%" if v >= 0 else f"left:{50 - w:.1f}%;width:{w:.1f}%"
        rows.append(f'<div class="dw-bar"><div class="lbl">{driver_name(g)}</div><div class="trk">'
                    f'<div class="fill" style="{pos};background:{UP if v >= 0 else DOWN}"></div></div>'
                    f'<div class="val">{n(v, "{:+.1f}")}</div></div>')
    rows.append(f'<div class="dw-bar total"><div class="lbl">{tx.t("wd_total")}</div><div></div>'
                f'<div class="val">{n(row["pred"], "{:.1f}")}</div></div>')
    r_ = f'<span style="color:{UP};font-weight:600">{tx.t("wd_right")}</span>'
    l_ = f'<span style="color:{DOWN};font-weight:600">{tx.t("wd_left")}</span>'
    html(f'<div class="gc">{card_head(tx.t("wd_push"), tx.t("wd_push_sub", r=r_, l=l_), "sliders")}'
         f'<div class="dw-bars">{"".join(rows)}</div>'
         f'<p class="dw-meta" style="margin:16px 0 0;line-height:1.5">{tx.t("wd_shap")}</p></div>')

# ---- Breeding clock ------------------------------------------------------------------
with right, st.container(key="glass_clock"):
    html(card_head(tx.t("wd_clock"), tx.t("wd_clock_sub"), "rain"))
    wx = engine.ward_weather(ward, as_of, weeks=10)
    fig = go.Figure()
    fig.add_vrect(x0=target - pd.Timedelta(weeks=4, days=3), x1=target - pd.Timedelta(weeks=2, days=-3),
                  fillcolor=INK, opacity=0.06, line_width=0)
    fig.add_bar(x=wx["date"], y=wx["rainfall_mm"], name=tx.t("wd_rain_name"), marker_color=RAIN, marker_line_width=0,
                customdata=[tx.t("wd_rain_hover", d=tx.short(d), mm=n(v)) for d, v in zip(wx["date"], wx["rainfall_mm"])],
                hovertemplate="%{customdata}<extra></extra>")
    fig.add_vline(x=as_of, line_color=MUTED, line_dash="dot", line_width=1)
    fig.add_vline(x=target, line_color=TIER_COLORS[row["tier"]], line_width=2)
    for x, label in ((as_of, tx.t("wd_today")), (target, tx.t("wd_fweek"))):
        fig.add_annotation(x=x, y=1, yref="paper", text=label, showarrow=False, xanchor="right", xshift=-6,
                           yanchor="top", align="right", font=dict(color=INK2, size=11))
    tv, tt = tx.week_ticks(list(wx["date"]) + [target], every=2)
    fig.update_layout(yaxis_title=tx.t("rain_axis"), bargap=0.3, barcornerradius=4,
                      xaxis_range=[wx["date"].min() - pd.Timedelta(days=4), target + pd.Timedelta(days=5)])
    fig.update_xaxes(tickvals=tv, ticktext=tt)
    st.plotly_chart(style_fig(fig, height=330, legend=False), width="stretch", config={"displayModeBar": False})
    st.caption(tx.t("wd_clock_cap"))

# ---- What-if -----------------------------------------------------------------------------
section(tx.t("wd_whatif"), tx.t("wd_whatif_sub"))
a, b = st.columns([2, 3], gap="large")
extra = a.slider(tx.t("wd_slider"), -100, 200, 0, step=10, key=f"whatif_{ward}")
with b:
    if extra:
        new = cached_forecast(str(as_of.date()), h, c["city"], float(extra)).set_index("ward_id").loc[ward]
        diff = new["pred"] - row["pred"]
        new_tier = str(tier_of([new["pred"]])[0])
        html(f'<div class="dk" style="padding:18px 22px"><div class="dw-meta">'
             f'{tx.t("wd_with", mm=n(abs(extra)), dir=tx.t("more") if extra > 0 else tx.t("less"))}</div>'
             f'<div class="dw-row" style="margin-top:6px"><div class="dw-big">{about(new["pred"])} <small style="color:'
             f'rgba(255,255,255,.66)">{tx.t("wd_new", diff=n(diff, "{:+.1f}"))}</small></div></div>'
             f'<div class="dw-change" style="margin-bottom:0"><div><div class="k">{tx.t("wd_now")}</div>{tier_pill(row["tier"])}</div>'
             f'<div><div class="k">{tx.t("wd_with_rain")}</div>{tier_pill(new_tier)}</div></div></div>')
    else:
        html(f'<div class="gc" style="padding:16px 20px"><div class="dw-meta" style="line-height:1.55">{tx.t("wd_try")}</div></div>')

# ---- Track record ------------------------------------------------------------------------
year = target.year
section(tx.t("wd_track", year=n(year, "{}")), tx.t("wd_track_sub", h=n(h), ward=ward_name(ward)))
hist = engine.ward_history(ward, h, f"{year}-01-01", f"{year}-12-31")
with st.container(key="glass_track"):
    fig = go.Figure()
    fig.add_scatter(x=pd.concat([hist["target_week"], hist["target_week"][::-1]]),
                    y=pd.concat([hist["hi"], hist["lo"][::-1]]), fill="toself", fillcolor="rgba(233,90,44,0.10)",
                    line=dict(width=0), name=tx.t("wd_t_range"), hoverinfo="skip")
    fig.add_scatter(x=hist["target_week"], y=hist["pred"], name=tx.t("wd_t_fc", h=n(h)),
                    line=dict(color=TIER_COLORS["High"], width=2), customdata=hist["target_week"].map(tx.short),
                    hovertemplate="%{customdata}: %{y:.1f}<extra></extra>")
    fig.add_scatter(x=hist["target_week"], y=hist["actual"], name=tx.t("wd_t_real"), mode="markers",
                    marker=dict(size=8, color=INK, line=dict(color="white", width=2)),
                    customdata=hist["target_week"].map(tx.short), hovertemplate="%{customdata}: %{y:.0f}<extra></extra>")
    fig.add_vline(x=target, line_color=MUTED, line_dash="dot", line_width=1)
    tv, tt = tx.month_ticks(hist["target_week"].min(), hist["target_week"].max())
    fig.update_layout(yaxis_title=tx.t("wd_t_axis"), hovermode="closest")
    fig.update_xaxes(tickvals=tv, ticktext=tt)
    st.plotly_chart(style_fig(fig, height=340), width="stretch", config={"displayModeBar": False})

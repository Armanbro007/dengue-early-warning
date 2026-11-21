"""Why this ward? The reasons behind one ward's forecast, a rain what-if and its track record."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dengue.explain import DRIVER_GROUPS
from dengue.tiers import tier_of
from ui_common import (ACCENT, DOWN, INK, INK2, MUTED, RAIN, TIER_COLORS, UP, about, cached_forecast, case_range,
                       driver_name, fmt_week, get_engine, html, page_header, section, style_fig, tier_pill, ward_name)

engine = get_engine()
c = st.session_state["controls"]
as_of, h = c["as_of"], c["horizon"]
target = as_of + pd.Timedelta(weeks=h)
fc = cached_forecast(str(as_of.date()), h, c["city"])
by_ward = fc.set_index("ward_id")

head = st.container()  # filled after the ward is chosen, but shown above the picker
pick, _ = st.columns([1, 2])
ward = pick.selectbox("Choose a ward (highest risk first)", fc["ward_id"].tolist(), index=0,
                      format_func=lambda w: f"{ward_name(w)} · {by_ward.loc[w, 'tier']}")
row = by_ward.loc[ward]
groups = sorted(DRIVER_GROUPS, key=lambda g: row[g], reverse=True)
up = groups[0]
pct = (row["breeding_rain_mm"] / max(row["breeding_rain_normal_mm"], 1) - 1) * 100

reason = (f"The biggest reason is <b>{driver_name(up).lower()}</b>." if row[up] > 0.05 else
          "Nothing pushes it much above normal.")
with head:
    page_header(
        "Why this ward?", f"{ward_name(ward)}, {row['city']}",
        f"DengueWatch expects about <b>{about(row['pred'])} dengue cases</b> here in the week of {fmt_week(target)} "
        f"(likely {case_range(row['lo'], row['hi'])}), compared with about {about(row['baseline'])} for a typical ward at "
        f"this time of year. {reason} It had {row['breeding_rain_mm']:.0f} mm of rain in the last 3 weeks, "
        f"{abs(pct):.0f}% {'more' if pct >= 0 else 'less'} than normal.",
    )
actual = "" if pd.isna(row["actual"]) else (
    f'<div><div class="k">What really happened</div><span class="dw-meta" style="color:{INK};font-weight:600">'
    f'{row["actual"]:.0f} cases · </span>{tier_pill(str(tier_of([row["actual"]])[0]))}</div>')
head.markdown(f'<div class="dw-change" style="gap:18px;margin:-.6rem 0 1rem"><div><div class="k">Today</div>{tier_pill(row["tier_now"])}</div>'
     f'<div><div class="k">In {h} weeks</div>{tier_pill(row["tier"])}</div>{actual}</div>', unsafe_allow_html=True)

left, right = st.columns(2, gap="large")

# ---- Reasons -----------------------------------------------------------------------
with left:
    vals = {g: float(row[g]) for g in DRIVER_GROUPS}
    span = max(max(abs(v) for v in vals.values()), 0.5)
    rows = [f'<div class="dw-bar"><div class="lbl">Normal for the season</div><div class="dw-meta">'
            f'a typical ward, typical weather</div><div class="val">{row["baseline"]:.1f}</div></div>']
    for g in groups:
        v = vals[g]
        w = abs(v) / span * 50
        pos = f"left:50%;width:{w:.1f}%" if v >= 0 else f"left:{50 - w:.1f}%;width:{w:.1f}%"
        rows.append(f'<div class="dw-bar"><div class="lbl">{driver_name(g)}</div><div class="trk">'
                    f'<div class="fill" style="{pos};background:{UP if v >= 0 else DOWN}"></div></div>'
                    f'<div class="val">{v:+.1f}</div></div>')
    rows.append(f'<div class="dw-bar total"><div class="lbl">Expected cases</div><div></div>'
                f'<div class="val">{row["pred"]:.1f}</div></div>')
    html(f'<div class="dw-card"><h4>What pushes this forecast up or down</h4><p class="dw-meta" style="margin:2px 0 16px">'
         f'Cases added (<span style="color:{UP};font-weight:600">right</span>) or removed '
         f'(<span style="color:{DOWN};font-weight:600">left</span>) by this ward\'s own conditions.</p>'
         f'<div class="dw-bars">{"".join(rows)}</div></div>')
    st.caption("Each number is an exact share of the forecast (a Shapley value), so they always add up to the total.")

# ---- Breeding clock ------------------------------------------------------------------
with right:
    wx = engine.ward_weather(ward, as_of, weeks=10)
    fig = go.Figure()
    fig.add_vrect(x0=target - pd.Timedelta(weeks=4, days=3), x1=target - pd.Timedelta(weeks=2, days=-3),
                  fillcolor=ACCENT, opacity=0.08, line_width=0)
    fig.add_bar(x=wx["date"], y=wx["rainfall_mm"], name="Weekly rain (mm)", marker_color=RAIN,
                marker_line_width=0, hovertemplate="Week of %{x|%d %b}: %{y:.0f} mm<extra></extra>")
    fig.add_vline(x=as_of, line_color=MUTED, line_dash="dot", line_width=1)
    fig.add_vline(x=target, line_color=TIER_COLORS[row["tier"]], line_width=2)
    for x, label in ((as_of, "today"), (target, "forecast<br>week")):
        fig.add_annotation(x=x, y=1, yref="paper", text=label, showarrow=False, xanchor="right", xshift=-6,
                           yanchor="top", align="right", font=dict(color=INK2, size=11))
    fig.update_layout(title="Rain now, cases later", yaxis_title="Rain (mm per week)", bargap=0.3, barcornerradius=4,
                      xaxis_range=[wx["date"].min() - pd.Timedelta(days=4), target + pd.Timedelta(days=5)])
    st.plotly_chart(style_fig(fig, height=400, legend=False), width="stretch")
    st.caption("Shaded weeks: the rain that matters most for the forecast week. Standing water needs 7 to 14 days "
               "to produce adult mosquitoes, then infection and symptoms take another 1 to 2 weeks.")

# ---- What-if -----------------------------------------------------------------------------
section("What if this week is wetter or drier?",
        "Move the slider to re-run the forecast for this ward with more or less rain this week.")
a, b = st.columns([2, 3], gap="large")
extra = a.slider("Change in this week's rain (mm)", -100, 200, 0, step=10, key=f"whatif_{ward}")
with b:
    if extra:
        new = cached_forecast(str(as_of.date()), h, c["city"], float(extra)).set_index("ward_id").loc[ward]
        diff = new["pred"] - row["pred"]
        new_tier = str(tier_of([new["pred"]])[0])
        html(f'<div class="dw-card"><div class="dw-meta">With {abs(extra)} mm {"more" if extra > 0 else "less"} rain this week</div>'
             f'<div class="dw-row" style="margin-top:6px"><div class="dw-big">{about(new["pred"])} <small>cases expected '
             f'({diff:+.1f} compared with now)</small></div></div>'
             f'<div class="dw-change"><div><div class="k">Now</div>{tier_pill(row["tier"])}</div>'
             f'<div><div class="k">With this rain</div>{tier_pill(new_tier)}</div></div></div>')
    else:
        html('<div class="dw-card"><div class="dw-meta">Try +100 mm to see a very wet week, or −80 mm for a dry one. '
             'More rain can never lower the forecast: the model is built that way on purpose.</div></div>')

# ---- Track record ------------------------------------------------------------------------
year = target.year
section(f"Track record in {year}", f"What DengueWatch forecast {h} weeks ahead for {ward_name(ward)}, "
        "against what really happened.")
hist = engine.ward_history(ward, h, f"{year}-01-01", f"{year}-12-31")
fig = go.Figure()
fig.add_scatter(x=pd.concat([hist["target_week"], hist["target_week"][::-1]]),
                y=pd.concat([hist["hi"], hist["lo"][::-1]]), fill="toself", fillcolor="rgba(31,111,106,0.12)",
                line=dict(width=0), name="Likely range", hoverinfo="skip")
fig.add_scatter(x=hist["target_week"], y=hist["pred"], name=f"Forecast, made {h} weeks earlier",
                line=dict(color=ACCENT, width=2), hovertemplate="%{x|%d %b}: forecast %{y:.1f}<extra></extra>")
fig.add_scatter(x=hist["target_week"], y=hist["actual"], name="Real cases", mode="markers",
                marker=dict(size=8, color=INK, line=dict(color="white", width=2)),
                hovertemplate="%{x|%d %b}: real %{y:.0f}<extra></extra>")
fig.add_vline(x=target, line_color=MUTED, line_dash="dot", line_width=1)
fig.update_layout(yaxis_title="Cases per week", hovermode="x unified")
st.plotly_chart(style_fig(fig, height=360), width="stretch")

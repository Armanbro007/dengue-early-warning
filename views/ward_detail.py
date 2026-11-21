"""Ward Drivers & What-if: why is this ward at risk, and what if it rains more?"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dengue.explain import DRIVER_GROUPS
from dengue.tiers import tier_of
from ui_common import BLUE, MUTED, TIER_COLORS, cached_forecast, fmt_week, get_engine, style_fig, tier_badge

engine = get_engine()
c = st.session_state["controls"]
as_of, h = c["as_of"], c["horizon"]
target = as_of + pd.Timedelta(weeks=h)
fc = cached_forecast(str(as_of.date()), h, c["city"])

st.title("Ward Drivers & What-if")
ward = st.selectbox("Ward", fc["ward_id"].tolist(), index=0,
                    format_func=lambda w: f"{w}  ({fc.set_index('ward_id').loc[w, 'tier']})")
row = fc.set_index("ward_id").loc[ward]

st.markdown(
    f"{row['city']} · issued week of **{fmt_week(as_of)}** · forecast for week of **{fmt_week(target)}** &nbsp; "
    + tier_badge(row["tier"]), unsafe_allow_html=True,
)

k = st.columns(4)
k[0].metric("Forecast cases", f"{row['pred']:.1f}", help="Model's expected weekly dengue cases in the target week")
k[1].metric("80% range", f"{row['lo']:.1f} – {row['hi']:.1f}")
k[2].metric("Seasonal norm", f"{row['baseline']:.1f}", help="Forecast for a typical ward with typical weather for this week of the year")
k[3].metric("Actual (known later)", "–" if pd.isna(row["actual"]) else f"{row['actual']:.0f}")

col1, col2 = st.columns(2, gap="large")

# ---- Driver waterfall ----------------------------------------------------
with col1:
    vals = [row[g] for g in DRIVER_GROUPS]
    fig = go.Figure(go.Waterfall(
        x=["Seasonal norm", "Rainfall", "Humidity", "Temperature", "Ward", "Forecast"],
        measure=["absolute", *["relative"] * len(vals), "total"],
        y=[row["baseline"], *vals, row["pred"]],
        text=[f"{row['baseline']:.1f}", *[f"{v:+.1f}" for v in vals], f"{row['pred']:.1f}"],
        textposition="outside", textfont=dict(color="#0b0b0b"),
        increasing=dict(marker=dict(color="#e34948")), decreasing=dict(marker=dict(color=BLUE)),
        totals=dict(marker=dict(color="#52514e")), connector=dict(line=dict(color="#c3c2b7", width=1)),
        hovertemplate="%{x}: %{text} cases<extra></extra>",
    ))
    fig.update_layout(title="Why this forecast? Driver breakdown (cases)", yaxis_title="Weekly cases")
    st.plotly_chart(style_fig(fig, height=380, legend=False), use_container_width=True)
    up = max(DRIVER_GROUPS, key=lambda g: row[g])
    st.caption(
        f"Red bars push risk up, blue bars pull it down, relative to a typical ward in a typical "
        f"week of this season. Biggest push: **{up.lower()}** ({row[up]:+.1f} cases). "
        f"Rain in the last 3 weeks: **{row['breeding_rain_mm']:.0f} mm** vs normal {row['breeding_rain_normal_mm']:.0f} mm."
    )

# ---- Breeding clock --------------------------------------------------------
with col2:
    wx = engine.ward_weather(ward, as_of, weeks=10)
    fig = go.Figure()
    fig.add_vrect(x0=target - pd.Timedelta(weeks=4, days=3), x1=target - pd.Timedelta(weeks=2, days=-3),
                  fillcolor="#2a78d6", opacity=0.10, line_width=0)
    fig.add_bar(x=wx["date"], y=wx["rainfall_mm"], name="Weekly rainfall (mm)", marker_color=BLUE,
                marker_line_width=0, hovertemplate="Week of %{x|%d %b}: %{y:.0f} mm<extra></extra>")
    fig.add_vline(x=as_of, line_color=MUTED, line_dash="dot", line_width=1)
    fig.add_vline(x=target, line_color=TIER_COLORS[row["tier"]], line_width=2)
    fig.add_annotation(x=target, y=1, yref="paper", text=f"forecast<br>week", showarrow=False,
                       font=dict(color="#0b0b0b"), xanchor="right", xshift=-4, yshift=-14)
    fig.update_layout(title="The breeding clock: rain now, cases later", yaxis_title="Rainfall (mm/week)",
                      xaxis_range=[wx["date"].min() - pd.Timedelta(days=4), target + pd.Timedelta(days=5)])
    st.plotly_chart(style_fig(fig, height=380, legend=False), use_container_width=True)
    st.caption("Dotted line = this week. Shaded band = the weeks whose rain drives the forecast week (2-4 weeks before it). "
               "Stagnant water needs 7-14 days to produce adult mosquitoes, then incubation and symptoms add more. "
               "That is why this week's rain shows up in hospitals 2-4 weeks later.")

# ---- What-if --------------------------------------------------------------
st.subheader("What-if: extra rain this week")
extra = st.slider("Change in this week's rainfall (mm)", -100, 200, 0, step=10,
                  help="Re-runs the model for this ward with more (or less) rain this week.")
if extra:
    new = cached_forecast(str(as_of.date()), h, c["city"], float(extra)).set_index("ward_id").loc[ward]
    w1, w2, w3 = st.columns(3)
    w1.metric(f"Forecast in {h} weeks", f"{new['pred']:.1f} cases", f"{new['pred'] - row['pred']:+.1f}")
    w2.markdown(f"**Tier:** {tier_badge(row['tier'])} → {tier_badge(str(tier_of([new['pred']])[0]))}", unsafe_allow_html=True)
    w3.metric("80% range", f"{new['lo']:.1f} – {new['hi']:.1f}")
else:
    st.caption("Move the slider to simulate a heavy-rain (or dry) week and see how the forecast responds.")

# ---- Track record -----------------------------------------------------------
year = target.year
hist = engine.ward_history(ward, h, f"{year}-01-01", f"{year}-12-31")
fig = go.Figure()
fig.add_scatter(x=pd.concat([hist["target_week"], hist["target_week"][::-1]]),
                y=pd.concat([hist["hi"], hist["lo"][::-1]]), fill="toself", fillcolor="rgba(42,120,214,0.15)",
                line=dict(width=0), name="80% range", hoverinfo="skip")
fig.add_scatter(x=hist["target_week"], y=hist["pred"], name=f"Forecast made {h} wks earlier",
                line=dict(color=BLUE, width=2), hovertemplate="%{x|%d %b}: forecast %{y:.1f}<extra></extra>")
fig.add_scatter(x=hist["target_week"], y=hist["actual"], name="Actual cases", mode="lines+markers",
                line=dict(color="#0b0b0b", width=1.5), marker=dict(size=5),
                hovertemplate="%{x|%d %b}: actual %{y:.0f}<extra></extra>")
fig.add_vline(x=target, line_color=MUTED, line_dash="dot", line_width=1)
fig.update_layout(title=f"{ward}: forecasts vs actual cases, {year}", yaxis_title="Weekly cases", hovermode="x unified")
st.plotly_chart(style_fig(fig, height=360), use_container_width=True)

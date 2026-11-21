"""Ward Risk Board: which wards need action, ranked by forecast cases."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dengue.briefing import build_facts, get_briefing
from dengue.config import TIERS, TIER_MIN_CASES
from ui_common import TIER_COLORS, cached_forecast, fmt_week, style_fig

c = st.session_state["controls"]
as_of, h = c["as_of"], c["horizon"]
target = as_of + pd.Timedelta(weeks=h)
fc = cached_forecast(str(as_of.date()), h, c["city"])

st.title("Ward Risk Board")
st.markdown(
    f"**{c['city_label']}** · forecast issued week of **{fmt_week(as_of)}** for week of "
    f"**{fmt_week(target)}** ({h} weeks ahead) · {len(fc)} wards"
)

# ---- KPI row --------------------------------------------------------------
k = st.columns(4)
counts = fc["tier"].value_counts()
k[0].metric("Critical wards", int(counts.get("Critical", 0)), help=f"Forecast ≥ {TIER_MIN_CASES['Critical']:.0f} cases/week")
k[1].metric("High wards", int(counts.get("High", 0)), help=f"Forecast {TIER_MIN_CASES['High']:.0f}-{TIER_MIN_CASES['Critical']:.0f} cases/week")
k[2].metric("Forecast cases (all wards)", f"{fc['pred'].sum():,.0f}", help="Sum of ward forecasts for the target week")
k[3].metric("Escalating wards", int(fc["escalating"].sum()),
            help="Low or Medium this week (reported cases) but forecast High or Critical: act here first")

# ---- Briefing -------------------------------------------------------------
left, right = st.columns([3, 2], gap="large")
with right:
    st.subheader("Officer briefing")
    facts = build_facts(fc, as_of, h, c["city"])
    use_llm = st.toggle("Use AI wording (optional, needs API key)", value=False,
                        help="Off = instant template. On = one cached LLM call; falls back to template on any error.")
    text, source = get_briefing(facts, use_llm=use_llm)
    st.markdown(text)
    st.caption(f"Source: {source}. Built only from the model's numbers.")

# ---- Ranked chart -----------------------------------------------------------
with left:
    top = fc.head(20).iloc[::-1]
    fig = go.Figure()
    for tier in TIERS:
        d = top[top["tier"] == tier]
        if d.empty:
            continue
        fig.add_bar(
            y=d["ward_id"], x=d["pred"], orientation="h", name=tier, marker_color=TIER_COLORS[tier],
            marker_line_width=0,
            error_x=dict(type="data", symmetric=False, array=d["hi"] - d["pred"], arrayminus=d["pred"] - d["lo"],
                         color="#898781", thickness=1.2, width=3),
            customdata=d[["lo", "hi", "main_driver", "city"]],
            hovertemplate="<b>%{y}</b> (%{customdata[3]})<br>Forecast %{x:.1f} cases"
                          "<br>80% range %{customdata[0]:.1f}-%{customdata[1]:.1f}<br>Main driver: %{customdata[2]}<extra></extra>",
        )
    for tier in ("High", "Critical"):
        fig.add_vline(x=TIER_MIN_CASES[tier], line_dash="dot", line_color=TIER_COLORS[tier], line_width=1,
                      annotation_text=tier, annotation_position="top", annotation_font_color="#52514e")
    fig.update_layout(title="Top 20 wards by forecast cases (bars = 80% range)", bargap=0.25,
                      xaxis_title="Forecast dengue cases in target week")
    st.plotly_chart(style_fig(fig, height=560), use_container_width=True)

# ---- Full table -------------------------------------------------------------
st.subheader("All wards")
table = fc.assign(
    rank=range(1, len(fc) + 1),
    range=fc["lo"].round(1).astype(str) + " – " + fc["hi"].round(1).astype(str),
    rain_vs_normal=((fc["breeding_rain_mm"] / fc["breeding_rain_normal_mm"].clip(lower=1) - 1) * 100).round(0),
    flag=np.select([fc["escalating"], fc["near_critical"]], ["▲ escalating", "near Critical"], ""),
)[["rank", "ward_id", "city", "tier_now", "tier", "flag", "pred", "range", "main_driver", "rain_vs_normal",
   "water_logging_risk_index", "sanitation_score", "actual"]]


def _tier_style(v):
    ink = "#0b0b0b" if v == "Medium" else "#ffffff"
    return f"background-color:{TIER_COLORS.get(v, '')};color:{ink};font-weight:600"


st.dataframe(
    table.style.map(_tier_style, subset=["tier", "tier_now"]).format({"pred": "{:.1f}", "rain_vs_normal": "{:+.0f}%", "actual": "{:.0f}"}, na_rep="–"),
    hide_index=True, use_container_width=True, height=420,
    column_config={
        "rank": st.column_config.NumberColumn("#", width="small"),
        "ward_id": "Ward", "city": "City", "tier_now": "Now", "tier": f"In {h} weeks", "flag": "Flag",
        "pred": st.column_config.NumberColumn("Forecast cases"),
        "range": "80% range",
        "main_driver": "Main driver",
        "rain_vs_normal": st.column_config.TextColumn("Rain last 3 wks vs normal"),
        "water_logging_risk_index": st.column_config.NumberColumn("Water-logging", format="%.2f"),
        "sanitation_score": st.column_config.NumberColumn("Sanitation", format="%.2f"),
        "actual": st.column_config.NumberColumn("Actual (known later)", help="Real cases in the target week, shown for replayed history only"),
    },
)
st.download_button("Download ward priority list (CSV)", fc.drop(columns=["tier_rank"]).to_csv(index=False).encode(),
                   file_name=f"dengue_priority_{as_of.date()}_h{h}.csv", mime="text/csv")

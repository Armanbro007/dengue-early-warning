"""How accurate is it? A fair test on unseen years, in plain words first and full detail after."""
import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dengue import config
from dengue.config import TIERS
from dengue.tiers import tier_index
from ui_common import ACCENT, INK, MUTED, get_engine, html, page_header, section, style_fig

engine = get_engine()
c = st.session_state["controls"]
h = c["horizon"]
m = json.loads(config.METRICS_PATH.read_text())
t = m["test"][str(h)]
bt = pd.DataFrame(m["backtest"])
btd = bt[bt["horizon"] == h] if not bt.empty else bt

page_header(
    "How accurate is it?", "Tested on two years it had never seen",
    f"DengueWatch learned from 2016–2023. It was then scored once on <b>2024 and 2025</b>, using only the data "
    f"that would have been available each week. Nothing was shuffled, so it could never peek at the future. "
    f"Numbers below are for forecasts <b>{h} weeks ahead</b>.",
)

s_m, s_p = t["model_in_season"]["mae"], t["persistence_in_season"]["mae"]
wins = int((btd["mae"] < btd["persistence_mae"]).sum()) if not btd.empty else 0
cards = [
    (f"{s_m:.1f}", "cases per ward per week",
     f"Average miss in the monsoon season (June–October). A simple “same as this week” guess misses by {s_p:.1f}, "
     f"so DengueWatch is {(1 - s_m / s_p) * 100:.0f}% closer."),
    (f"{t['model']['high_critical_recall']:.0%}", "of high-risk weeks caught",
     "Of all the ward-weeks that really turned high or critical, this share was flagged in advance."),
    (f"{t['model']['interval_coverage']:.0%}", "inside the likely range",
     "How often the real count landed inside the range we show. We aim for 80%, so the ranges are honest."),
    (f"{wins} of {len(btd)}", "years beaten",
     f"Re-trained each year from {int(btd['year'].min()) if len(btd) else '–'} to {int(btd['year'].max()) if len(btd) else '–'} "
     "on earlier years only, it beat the simple guess every time." if wins == len(btd) else
     "Years in which it beat the simple guess, re-trained each year on earlier years only."),
]
html('<div class="dw-grid">' + "".join(
    f'<div class="dw-card"><div class="dw-big">{big}</div><div style="font-weight:600;margin:4px 0 8px">{label}</div>'
    f'<div class="dw-meta" style="line-height:1.5">{text}</div></div>' for big, label, text in cards) + "</div>")

a, b = st.columns(2, gap="large")
with a:
    section("Better than a simple guess, every year", "Average miss per ward per week. Lower is better.")
    if not btd.empty:
        fig = go.Figure()
        fig.add_bar(x=btd["year"], y=btd["mae"], name="DengueWatch", marker_color=ACCENT, marker_line_width=0,
                    hovertemplate="%{x}: misses by %{y:.2f} cases<extra>DengueWatch</extra>")
        fig.add_bar(x=btd["year"], y=btd["persistence_mae"], name="Simple guess (same as this week)",
                    marker_color="#CFCAC0", marker_line_width=0,
                    hovertemplate="%{x}: misses by %{y:.2f} cases<extra>Simple guess</extra>")
        fig.update_layout(barmode="group", bargap=0.35, bargroupgap=0.08, barcornerradius=4,
                          yaxis_title="Average miss (cases)", xaxis=dict(dtick=1))
        st.plotly_chart(style_fig(fig, height=340), width="stretch")

with b:
    section("Why three weeks?", "How closely cases follow the weather of earlier weeks.")
    lc = pd.DataFrame(m["lag_correlations"])
    fig = go.Figure()
    for var, color in [("Rainfall", "#2a78d6"), ("Temperature", "#eb6834"), ("Humidity", "#1baf7a")]:
        d = lc[lc["variable"] == var]
        fig.add_scatter(x=d["lag_weeks"], y=d["correlation"], name=var, mode="lines+markers",
                        line=dict(color=color, width=2), marker=dict(size=8, line=dict(color="white", width=2)),
                        hovertemplate=f"{var}, %{{x}} weeks earlier: r = %{{y:.2f}}<extra></extra>")
    best = lc[lc["variable"] == "Rainfall"].sort_values("correlation").iloc[-1]
    fig.add_annotation(x=best["lag_weeks"], y=best["correlation"], text=f"rain peaks at {int(best['lag_weeks'])} weeks",
                       showarrow=True, arrowcolor=MUTED, arrowwidth=1, ay=-34, font=dict(color=INK, size=12))
    fig.update_layout(xaxis_title="Weeks between the weather and the cases", yaxis_title="Correlation")
    st.plotly_chart(style_fig(fig, height=340), width="stretch")

st.caption("Rain lines up with dengue cases best about 3 weeks later: the time for water to breed mosquitoes, "
           "plus infection and symptoms. That is why the default forecast looks 3 weeks ahead.")


# ---- Full detail -----------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def test_preds(h: int) -> pd.DataFrame:
    e = get_engine()
    return pd.concat([e.season_grid(y, h) for y in (2024, 2025)], ignore_index=True).dropna(subset=["actual"])


with st.expander("Technical details: error metrics, baselines and the tier confusion matrix"):
    rows = []
    for hh in config.HORIZONS:
        tt = m["test"][str(hh)]
        for name, key in [("DengueWatch", "model"), ("Naive: same as this week", "persistence"),
                          ("Naive: same week last year", "last_year")]:
            rows.append({"Horizon": f"{hh} weeks", "Method": name, "MAE Jun–Oct": tt[f"{key}_in_season"]["mae"],
                         "MAE all weeks": tt[key]["mae"], "RMSE": tt[key]["rmse"],
                         "Tier accuracy": tt[key]["tier_accuracy"], "High/Critical recall": tt[key]["high_critical_recall"]})
    st.markdown("**Test set 2024–2025 against simple baselines** (MAE and RMSE in cases per ward per week)")
    st.dataframe(pd.DataFrame(rows).style.format(
        {"MAE Jun–Oct": "{:.2f}", "MAE all weeks": "{:.2f}", "RMSE": "{:.2f}", "Tier accuracy": "{:.0%}",
         "High/Critical recall": "{:.0%}"}, na_rep="–"), hide_index=True, width="stretch")

    tp = test_preds(h)
    a, b = st.columns(2, gap="large")
    with a:
        fig = go.Figure()
        fig.add_scatter(x=tp["actual"], y=tp["pred"], mode="markers", marker=dict(size=5, color=ACCENT, opacity=0.3),
                        name="ward-week", hovertemplate="real %{x:.0f} · forecast %{y:.1f}<extra></extra>")
        mx = float(max(tp["actual"].max(), tp["pred"].max()))
        fig.add_scatter(x=[0, mx], y=[0, mx], mode="lines", line=dict(color=MUTED, dash="dot", width=1), name="perfect")
        fig.update_layout(title="Forecast against real cases, 2024–2025", xaxis_title="Real cases", yaxis_title="Forecast cases")
        st.plotly_chart(style_fig(fig, height=380, legend=False), width="stretch")
    with b:
        yt, pt = tier_index(tp["actual"]), tier_index(tp["pred"])
        cm = pd.crosstab(pd.Categorical(yt, categories=range(4)), pd.Categorical(pt, categories=range(4)), dropna=False).values
        share = cm / cm.sum(axis=1, keepdims=True).clip(min=1)
        fig = go.Figure(go.Heatmap(
            z=share, x=list(TIERS), y=list(TIERS), colorscale=[[0, "#FFFFFF"], [1, ACCENT]], zmin=0, zmax=1,
            text=cm, texttemplate="%{text}", xgap=2, ygap=2, showscale=False,
            hovertemplate="Real %{y}, forecast %{x}: %{text} ward-weeks (%{z:.0%} of row)<extra></extra>",
        ))
        fig.update_layout(title="Risk level: real (rows) vs forecast (columns)", xaxis_title="Forecast level",
                          yaxis_title="Real level")
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(style_fig(fig, height=380, legend=False), width="stretch")
    st.caption(f"Speed: shipped models train in {m['timing']['train_shipped_seconds']} s on a laptop CPU; all 60 wards "
               f"are scored in {m['timing']['inference_ms_all_wards']} ms; the model file is "
               f"{m['timing']['model_file_kb']:.0f} KB.")

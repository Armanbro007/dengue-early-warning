"""Model Accuracy: chronological validation, baselines and the lag evidence."""
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dengue import config
from dengue.config import TIERS
from dengue.tiers import tier_index
from ui_common import BLUE, MUTED, get_engine, style_fig

engine = get_engine()
c = st.session_state["controls"]
h = c["horizon"]
m = json.loads(config.METRICS_PATH.read_text())

st.title("Model Accuracy")
st.markdown(
    "Validated **chronologically**, never with a random split: trained on **2016-2022**, tuned on **2023**, "
    "and the shipped model (trained 2016-2023) is tested on **2024-2025**, which it never saw. "
    "Errors are in dengue cases per ward per week."
)

t = m["test"][str(h)]
k = st.columns(4)
s_m, s_p = t["model_in_season"]["mae"], t["persistence_in_season"]["mae"]
k[0].metric(f"MAE, monsoon season (Jun-Oct)", f"{s_m:.2f}",
            f"{(1 - s_m / s_p) * 100:.0f}% lower error than naive", delta_color="normal",
            help="Mean absolute error in cases per ward per week, during the weeks that matter. Naive = 'same as this week'.")
k[1].metric("MAE, all weeks", f"{t['model']['mae']:.2f}", f"naive {t['persistence']['mae']:.2f}", delta_color="off",
            help=f"Including the dry months, when cases are near zero. RMSE {t['model']['rmse']:.2f}.")
k[2].metric("High/Critical weeks caught", f"{t['model']['high_critical_recall']:.0%}",
            help="Recall: of the ward-weeks that really were High or Critical, how many we flagged High or Critical")
k[3].metric("80% range coverage", f"{t['model']['interval_coverage']:.0%}",
            help="Share of weeks where the actual count fell inside the 80% range")

rows = []
for hh in config.HORIZONS:
    tt = m["test"][str(hh)]
    for name, key in [("DengueWatch model", "model"), ("Naive: same as this week", "persistence"), ("Naive: same week last year", "last_year")]:
        rows.append({"Horizon": f"{hh} wks", "Method": name, "MAE Jun-Oct": tt[f"{key}_in_season"]["mae"],
                     "MAE": tt[key]["mae"], "RMSE": tt[key]["rmse"],
                     "Tier accuracy": tt[key]["tier_accuracy"], "High/Critical recall": tt[key]["high_critical_recall"]})
st.subheader("Test set 2024-2025 vs simple baselines")
st.dataframe(pd.DataFrame(rows).style.format({"MAE Jun-Oct": "{:.2f}", "MAE": "{:.2f}", "RMSE": "{:.2f}", "Tier accuracy": "{:.0%}", "High/Critical recall": "{:.0%}"}, na_rep="–"),
             hide_index=True, use_container_width=True)

a, b = st.columns(2, gap="large")
with a:
    bt = pd.DataFrame(m["backtest"])
    if not bt.empty:
        d = bt[bt["horizon"] == h]
        fig = go.Figure()
        fig.add_bar(x=d["year"], y=d["mae"], name="DengueWatch model", marker_color=BLUE, marker_line_width=0,
                    hovertemplate="%{x}: MAE %{y:.2f}<extra></extra>")
        fig.add_bar(x=d["year"], y=d["persistence_mae"], name="Naive (same as this week)", marker_color="#c3c2b7",
                    marker_line_width=0, hovertemplate="%{x}: MAE %{y:.2f}<extra></extra>")
        fig.update_layout(title=f"Year-by-year backtest, {h}-week horizon (train on all earlier years)",
                          yaxis_title="MAE (cases/ward/week)", barmode="group", bargap=0.3)
        st.plotly_chart(style_fig(fig, height=360), use_container_width=True)

with b:
    lc = pd.DataFrame(m["lag_correlations"])
    fig = go.Figure()
    for var, color in [("Rainfall", BLUE), ("Humidity", "#1baf7a"), ("Temperature", "#eb6834")]:
        d = lc[lc["variable"] == var]
        fig.add_scatter(x=d["lag_weeks"], y=d["correlation"], name=var, mode="lines+markers",
                        line=dict(color=color, width=2), marker=dict(size=8),
                        hovertemplate=f"{var}, %{{x}} weeks earlier: r = %{{y:.2f}}<extra></extra>")
    best = lc[lc["variable"] == "Rainfall"].sort_values("correlation").iloc[-1]
    fig.add_annotation(x=best["lag_weeks"], y=best["correlation"], text=f"rain peaks at {int(best['lag_weeks'])} weeks",
                       showarrow=True, arrowcolor=MUTED, ay=-30, font=dict(color="#0b0b0b"))
    fig.update_layout(title="Evidence for the lag: cases vs weather k weeks earlier",
                      xaxis_title="Lag (weeks)", yaxis_title="Correlation with weekly cases")
    st.plotly_chart(style_fig(fig, height=360), use_container_width=True)


@st.cache_data(show_spinner=False)
def test_preds(h: int) -> pd.DataFrame:
    e = get_engine()
    return pd.concat([e.season_grid(y, h) for y in (2024, 2025)], ignore_index=True).dropna(subset=["actual"])


tp = test_preds(h)
a, b = st.columns(2, gap="large")
with a:
    fig = go.Figure()
    fig.add_scatter(x=tp["actual"], y=tp["pred"], mode="markers", marker=dict(size=5, color=BLUE, opacity=0.35),
                    name="ward-week", hovertemplate="actual %{x:.0f} · forecast %{y:.1f}<extra></extra>")
    mx = float(max(tp["actual"].max(), tp["pred"].max()))
    fig.add_scatter(x=[0, mx], y=[0, mx], mode="lines", line=dict(color=MUTED, dash="dot", width=1), name="perfect")
    fig.update_layout(title="Forecast vs actual, 2024-2025 (live inference)", xaxis_title="Actual cases",
                      yaxis_title="Forecast cases")
    st.plotly_chart(style_fig(fig, height=380, legend=False), use_container_width=True)
with b:
    yt, pt = tier_index(tp["actual"]), tier_index(tp["pred"])
    cm = pd.crosstab(pd.Categorical(yt, categories=range(4)), pd.Categorical(pt, categories=range(4)), dropna=False).values
    share = cm / cm.sum(axis=1, keepdims=True).clip(min=1)
    fig = go.Figure(go.Heatmap(
        z=share, x=list(TIERS), y=list(TIERS), colorscale=[[0, "#fcfcfb"], [1, "#184f95"]], zmin=0, zmax=1,
        text=cm, texttemplate="%{text}", xgap=2, ygap=2, showscale=False,
        hovertemplate="Actual %{y}, forecast %{x}: %{text} ward-weeks (%{z:.0%} of row)<extra></extra>",
    ))
    fig.update_layout(title="Tier confusion matrix, 2024-2025", xaxis_title="Forecast tier", yaxis_title="Actual tier")
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(style_fig(fig, height=380, legend=False), use_container_width=True)

st.caption(f"Timing: shipped models trained in {m['timing']['train_shipped_seconds']} s on a laptop CPU; "
           f"all 60 wards scored in {m['timing']['inference_ms_all_wards']} ms; model file {m['timing']['model_file_kb']:.0f} KB.")

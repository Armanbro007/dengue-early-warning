"""How accurate is it? A fair test on unseen years, in plain words first and full detail after."""
import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ui_text as tx
from dengue import config
from dengue.config import TIERS
from dengue.tiers import tier_index
from ui_common import INK, MUTED, TIER_COLORS, card_head, get_engine, html, page_header, style_fig

engine = get_engine()
c = st.session_state["controls"]
h = c["horizon"]
n = tx.num
pc = lambda v: n(f"{v:.0%}")  # noqa: E731
m = json.loads(config.METRICS_PATH.read_text())
t = m["test"][str(h)]
bt = pd.DataFrame(m["backtest"])
btd = bt[bt["horizon"] == h] if not bt.empty else bt

page_header(tx.t("ac_eyebrow"), tx.t("ac_title"), tx.t("ac_lead", h=n(h)))

s_m, s_p = t["model_in_season"]["mae"], t["persistence_in_season"]["mae"]
wins = int((btd["mae"] < btd["persistence_mae"]).sum()) if not btd.empty else 0
yr = lambda v: n(int(v), "{}") if len(btd) else "–"  # noqa: E731
cards = [
    (n(s_m, "{:.1f}"), tx.t("ac_c1_label"),
     tx.t("ac_c1_text", p=n(s_p, "{:.1f}"), pct=n((1 - s_m / s_p) * 100))),
    (pc(t["model"]["high_critical_recall"]), tx.t("ac_c2_label"), tx.t("ac_c2_text")),
    (pc(t["model"]["interval_coverage"]), tx.t("ac_c3_label"), tx.t("ac_c3_text")),
    (tx.t("ac_c4_big", w=n(wins), n=n(len(btd))), tx.t("ac_c4_label"),
     tx.t("ac_c4_all", a=yr(btd["year"].min()), b=yr(btd["year"].max())) if wins == len(btd) else tx.t("ac_c4_some")),
]
html('<div class="dw-grid">' + "".join(
    f'<div class="{"dk" if i == 0 else "gc"}"><div class="dw-big">{big}</div>'
    f'<div style="font-weight:600;margin:4px 0 8px">{label}</div>'
    f'<div class="dw-meta" style="line-height:1.5">{text}</div></div>' for i, (big, label, text) in enumerate(cards))
     + "</div>")
st.write("")

a, b = st.columns(2, gap="small")
with a, st.container(key="glass_bt"):
    html(card_head(tx.t("ac_bt"), tx.t("ac_bt_sub"), "bars"))
    if not btd.empty:
        fig = go.Figure()
        for col, name, color in (("mae", "DengueWatch", INK), ("persistence_mae", tx.t("ac_simple"), "#C9CCD4")):
            fig.add_bar(x=btd["year"], y=btd[col], name=name, marker_color=color, marker_line_width=0,
                        customdata=[tx.t("ac_bt_hover", y=n(y, "{}"), v=n(v, "{:.2f}")) for y, v in zip(btd["year"], btd[col])],
                        hovertemplate="%{customdata}<extra>" + name + "</extra>")
        fig.update_layout(barmode="group", bargap=0.35, bargroupgap=0.08, barcornerradius=4,
                          yaxis_title=tx.t("ac_miss_axis"))
        fig.update_xaxes(tickvals=list(btd["year"]), ticktext=[n(y, "{}") for y in btd["year"]])
        st.plotly_chart(style_fig(fig, height=330), width="stretch", config={"displayModeBar": False})

with b, st.container(key="glass_lag"):
    html(card_head(tx.t("ac_lag"), tx.t("ac_lag_sub"), "clock"))
    lc = pd.DataFrame(m["lag_correlations"])
    fig = go.Figure()
    for var, color in [("Rainfall", INK), ("Temperature", TIER_COLORS["High"]), ("Humidity", TIER_COLORS["Low"])]:
        d = lc[lc["variable"] == var]
        name = tx.t(f"var_{var}")
        fig.add_scatter(x=d["lag_weeks"], y=d["correlation"], name=name, mode="lines+markers",
                        line=dict(color=color, width=2), marker=dict(size=8, line=dict(color="white", width=2)),
                        customdata=[f"{name}, {n(x)}: r = {n(y, '{:.2f}')}" for x, y in zip(d["lag_weeks"], d["correlation"])],
                        hovertemplate="%{customdata}<extra></extra>")
    best = lc[lc["variable"] == "Rainfall"].sort_values("correlation").iloc[-1]
    fig.add_annotation(x=best["lag_weeks"], y=best["correlation"], text=tx.t("ac_peak", n=n(int(best["lag_weeks"]))),
                       showarrow=True, arrowcolor=MUTED, arrowwidth=1, ay=-34, font=dict(color=INK, size=12))
    fig.update_layout(xaxis_title=tx.t("ac_lag_x"), yaxis_title=tx.t("ac_lag_y"))
    st.plotly_chart(style_fig(fig, height=330), width="stretch", config={"displayModeBar": False})

st.caption(tx.t("ac_lag_cap"))


# ---- Full detail -----------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def test_preds(h: int) -> pd.DataFrame:
    e = get_engine()
    return pd.concat([e.season_grid(y, h) for y in (2024, 2025)], ignore_index=True).dropna(subset=["actual"])


with st.expander(tx.t("ac_tech")):
    rows = []
    for hh in config.HORIZONS:
        tt = m["test"][str(hh)]
        for key in ("model", "persistence", "last_year"):
            name = tx.t({"model": "ac_m_model", "persistence": "ac_m_persist", "last_year": "ac_m_last"}[key])
            rows.append({tx.t("ac_col_h"): tx.t("ac_weeks", h=n(hh)), tx.t("ac_col_m"): name,
                         tx.t("ac_col_mae_s"): tt[f"{key}_in_season"]["mae"], tx.t("ac_col_mae"): tt[key]["mae"],
                         tx.t("ac_col_rmse"): tt[key]["rmse"], tx.t("ac_col_tacc"): tt[key]["tier_accuracy"],
                         tx.t("ac_col_rec"): tt[key]["high_critical_recall"]})
    st.markdown(tx.t("ac_table"))
    two = lambda v: n(v, "{:.2f}")  # noqa: E731
    st.dataframe(pd.DataFrame(rows).style.format(
        {tx.t("ac_col_mae_s"): two, tx.t("ac_col_mae"): two, tx.t("ac_col_rmse"): two,
         tx.t("ac_col_tacc"): pc, tx.t("ac_col_rec"): pc}, na_rep="–"), hide_index=True, width="stretch")

    tp = test_preds(h)
    a, b = st.columns(2, gap="large")
    with a:
        fig = go.Figure()
        fig.add_scatter(x=tp["actual"], y=tp["pred"], mode="markers", marker=dict(size=5, color=INK, opacity=0.25),
                        name="ward-week", hovertemplate="%{x:.0f} · %{y:.1f}<extra></extra>")
        mx = float(max(tp["actual"].max(), tp["pred"].max()))
        fig.add_scatter(x=[0, mx], y=[0, mx], mode="lines", line=dict(color=MUTED, dash="dot", width=1), name="perfect")
        fig.update_layout(title=tx.t("ac_scatter"), xaxis_title=tx.t("ac_real"), yaxis_title=tx.t("ac_fc"))
        st.plotly_chart(style_fig(fig, height=380, legend=False), width="stretch")
    with b:
        yt, pt = tier_index(tp["actual"]), tier_index(tp["pred"])
        cm = pd.crosstab(pd.Categorical(yt, categories=range(4)), pd.Categorical(pt, categories=range(4)), dropna=False).values
        share = cm / cm.sum(axis=1, keepdims=True).clip(min=1)
        labels = [tx.tier(x) for x in TIERS]
        fig = go.Figure(go.Heatmap(
            z=share, x=labels, y=labels, colorscale=[[0, "#FFFFFF"], [1, INK]], zmin=0, zmax=1,
            text=[[n(v) for v in r] for r in cm], texttemplate="%{text}", xgap=2, ygap=2, showscale=False,
            hovertemplate="%{y} → %{x}: %{text}<extra></extra>",
        ))
        fig.update_layout(title=tx.t("ac_cm"), xaxis_title=tx.t("ac_cm_x"), yaxis_title=tx.t("ac_cm_y"))
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(style_fig(fig, height=380, legend=False), width="stretch")
    st.caption(tx.t("ac_speed", t=n(f"{m['timing']['train_shipped_seconds']}"),
                    ms=n(f"{m['timing']['inference_ms_all_wards']}"), kb=n(m["timing"]["model_file_kb"])))

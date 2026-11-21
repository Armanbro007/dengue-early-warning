"""Ward priorities: every ward ranked by expected cases, with an action briefing."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ui_text as tx
from dengue import config
from dengue.briefing import build_facts, get_briefing
from dengue.config import TIERS, TIER_MIN_CASES
from ui_common import (INK2, MUTED, TIER_COLORS, cached_forecast, card_head, driver_name, html, keep_choice,
                       page_header, remember, section, style_fig, tier_cell_style, tier_legend, ward_name)

c = st.session_state["controls"]
as_of, h = c["as_of"], c["horizon"]
target = as_of + pd.Timedelta(weeks=h)
fc = cached_forecast(str(as_of.date()), h, c["city"])
week = tx.date(target)
n = tx.num

page_header(
    tx.t("rb_eyebrow", date=week), tx.t("rb_title"),
    tx.t("rb_lead", n=n(len(fc)), date=week, area_of=tx.city_of(c["city"]),
         area=tx.t("area_all_long") if c["city"] is None else c["city"]),
)

# ---- Headline numbers, in a dark strip like the overview card ------------------------
counts = fc["tier"].value_counts()
with st.container(key="dark_kpis"):
    k = st.columns(4)
    k[0].metric(tx.t("rb_m_crit"), n(int(counts.get("Critical", 0))),
                help=tx.t("rb_m_crit_help", n=n(TIER_MIN_CASES["Critical"])))
    k[1].metric(tx.t("rb_m_high"), n(int(counts.get("High", 0))),
                help=tx.t("rb_m_high_help", a=n(TIER_MIN_CASES["High"]), b=n(TIER_MIN_CASES["Critical"])))
    k[2].metric(tx.t("rb_m_worse"), n(int(fc["escalating"].sum())), help=tx.t("rb_m_worse_help"))
    k[3].metric(tx.t("rb_m_cases"), n(fc["pred"].sum()), help=tx.t("rb_m_cases_help", date=week))
st.write("")

# ---- Ranked chart + briefing ------------------------------------------------------
left, right = st.columns([3, 2], gap="small")
with left, st.container(key="glass_rank"):
    html(card_head(tx.t("rb_chart"), tx.t("rb_chart_sub"), "bars"))
    top = fc.head(15).iloc[::-1].assign(name=lambda d: d["ward_id"].map(ward_name))
    fig = go.Figure()
    for tier in TIERS:
        d = top[top["tier"] == tier]
        if d.empty:
            continue
        fig.add_bar(
            y=d["name"], x=d["pred"], orientation="h", name=tx.tier(tier), marker_color=TIER_COLORS[tier],
            marker_line_width=0,
            error_x=dict(type="data", symmetric=False, array=d["hi"] - d["pred"], arrayminus=d["pred"] - d["lo"],
                         color=MUTED, thickness=1.2, width=3),
            customdata=np.c_[d["lo"].clip(lower=0).map(lambda v: n(v, "{:.0f}")), d["hi"].map(lambda v: n(v, "{:.0f}")),
                             d["main_driver"].map(driver_name), d["city"].map(tx.city),
                             d["pred"].map(lambda v: n(v, "{:.0f}"))],
            hovertemplate=tx.t("rb_hover") + "<extra></extra>",
        )
    for tier in ("High", "Critical"):
        fig.add_vline(x=TIER_MIN_CASES[tier], line_dash="dot", line_color=TIER_COLORS[tier], line_width=1,
                      annotation_text=tx.tier(tier), annotation_position="top",
                      annotation_font=dict(color=INK2, size=11))
    fig.update_layout(bargap=0.35, barcornerradius=4, xaxis_title=tx.t("rb_axis", date=week))
    st.plotly_chart(style_fig(fig, height=540, legend=False), width="stretch", config={"displayModeBar": False})
    html(tier_legend())
    st.write("")

with right, st.container(key="glass_brief"):
    html(card_head(tx.t("rb_brief"), tx.t("rb_brief_sub"), "note"))
    facts = build_facts(fc, as_of, h, c["city"])
    ai_ready = bool(config.GEMINI_API_KEY)  # the AI rewording switch only appears when a key is configured
    text, source = get_briefing(facts, use_llm=ai_ready and st.session_state.get("brief_llm", False), lang=tx.lang())
    st.markdown(text)
    if ai_ready:
        st.toggle(tx.t("rb_ai"), value=False, key="brief_llm", help=tx.t("rb_ai_help"))
        kind = source.split(" ")[0]
        label = tx.t(f"src_{kind}") + (source[len(kind):] if tx.lang() == "en" else "")
        st.caption(tx.t("rb_src", src=label))
    else:
        st.caption(tx.t("rb_src_template"))

# ---- Full list -------------------------------------------------------------------
section(tx.t("rb_all"), tx.t("rb_all_sub"))
labels, back, key = keep_choice("rb_filter", ["all", "high", "worse"], lambda v: tx.t(f"rb_f_{v}"), "all")
show = remember("rb_filter", back[st.segmented_control("Show", labels, key=key, required=True,
                                                       label_visibility="collapsed")])
view = fc.assign(rank=range(1, len(fc) + 1))
if show == "high":
    view = view[view["tier"].isin(["High", "Critical"])]
elif show == "worse":
    view = view[view["escalating"]]

table = view.assign(
    ward=view["ward_id"].map(ward_name),
    city=view["city"].map(tx.city),
    tier=view["tier"].map(tx.tier),
    tier_now=view["tier_now"].map(tx.tier),
    range=[tx.num(f"{max(lo, 0):.0f} – {hi:.0f}") for lo, hi in zip(view["lo"], view["hi"])],
    reason=view["main_driver"].map(driver_name),
    rain_vs_normal=((view["breeding_rain_mm"] / view["breeding_rain_normal_mm"].clip(lower=1) - 1) * 100).round(0),
)[["rank", "ward", "city", "tier_now", "tier", "pred", "range", "reason", "rain_vs_normal", "actual"]]

if table.empty:
    st.info(tx.t("rb_none"))
else:
    st.dataframe(
        table.style.map(tier_cell_style, subset=["tier", "tier_now"])
        .format({"rank": lambda v: n(v), "pred": lambda v: n(v, "{:.1f}"),
                 "rain_vs_normal": lambda v: n(v, "{:+.0f}%"), "actual": lambda v: n(v, "{:.0f}")}, na_rep="–"),
        hide_index=True, width="stretch", height=min(38 + 35 * len(table), 460),
        column_config={
            "rank": st.column_config.Column("#", width="small"),
            "ward": st.column_config.Column(tx.t("col_ward"), width=170), "city": tx.t("col_city"), "tier_now": tx.t("col_today"),
            "tier": tx.t("col_in", h=n(h)), "pred": tx.t("col_pred"), "range": tx.t("col_range"),
            "reason": tx.t("col_reason"), "rain_vs_normal": tx.t("col_rain"),
            "actual": st.column_config.Column(tx.t("col_actual"), help=tx.t("col_actual_help")),
        },
    )
st.write("")
st.download_button(tx.t("rb_download"), fc.drop(columns=["tier_rank"]).to_csv(index=False).encode(),
                   file_name=f"dengue_priority_{as_of.date()}_h{h}.csv", mime="text/csv", icon=":material/download:")

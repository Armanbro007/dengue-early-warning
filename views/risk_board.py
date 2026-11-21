"""Ward priorities: every ward ranked by expected cases, with an action briefing."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dengue.briefing import LANGUAGES, build_facts, get_briefing
from dengue.config import TIERS, TIER_MIN_CASES
from ui_common import (INK2, MUTED, TIER_COLORS, cached_forecast, driver_name, fmt_week, page_header, section,
                       style_fig, tier_cell_style, tier_legend, ward_name, html)

c = st.session_state["controls"]
as_of, h = c["as_of"], c["horizon"]
target = as_of + pd.Timedelta(weeks=h)
fc = cached_forecast(str(as_of.date()), h, c["city"])
area = "all five city corporations" if c["city"] is None else c["city"]

page_header(
    "Ward priorities", "Which wards need help first",
    f"All {len(fc)} wards in {area}, ranked by how many dengue cases DengueWatch expects in the week of "
    f"<b>{fmt_week(target)}</b>. Use it to decide where larvicide teams, clean-up drives and hospital "
    f"supplies go first.",
)

# ---- Headline numbers ---------------------------------------------------------
counts = fc["tier"].value_counts()
k = st.columns(4)
k[0].metric("Critical wards", int(counts.get("Critical", 0)),
            help=f"Expected to have {TIER_MIN_CASES['Critical']:.0f} or more cases a week")
k[1].metric("High-risk wards", int(counts.get("High", 0)),
            help=f"Expected to have {TIER_MIN_CASES['High']:.0f} to {TIER_MIN_CASES['Critical']:.0f} cases a week")
k[2].metric("Getting worse", int(fc["escalating"].sum()),
            help="Low or medium risk today, but expected to be high or critical. Acting here early pays off most.")
k[3].metric("Cases expected", f"{fc['pred'].sum():,.0f}", help=f"Total across these wards in the week of {fmt_week(target)}")

# ---- Ranked chart + briefing ------------------------------------------------------
left, right = st.columns([3, 2], gap="large")
with left:
    top = fc.head(15).iloc[::-1].assign(name=lambda d: d["ward_id"].map(ward_name))
    fig = go.Figure()
    for tier in TIERS:
        d = top[top["tier"] == tier]
        if d.empty:
            continue
        fig.add_bar(
            y=d["name"], x=d["pred"], orientation="h", name=tier, marker_color=TIER_COLORS[tier], marker_line_width=0,
            error_x=dict(type="data", symmetric=False, array=d["hi"] - d["pred"], arrayminus=d["pred"] - d["lo"],
                         color=MUTED, thickness=1.2, width=3),
            customdata=np.c_[d["lo"], d["hi"], d["main_driver"].map(driver_name), d["city"]],
            hovertemplate="<b>%{y}</b>, %{customdata[3]}<br>About %{x:.0f} cases expected"
                          "<br>Likely %{customdata[0]:.0f} to %{customdata[1]:.0f}<br>Main reason: %{customdata[2]}<extra></extra>",
        )
    for tier in ("High", "Critical"):
        fig.add_vline(x=TIER_MIN_CASES[tier], line_dash="dot", line_color=TIER_COLORS[tier], line_width=1,
                      annotation_text=tier, annotation_position="top", annotation_font=dict(color=INK2, size=11))
    fig.update_layout(title="Top 15 wards by expected cases", bargap=0.35, barcornerradius=4,
                      xaxis_title=f"Expected dengue cases in the week of {fmt_week(target)} (line = likely range)")
    st.plotly_chart(style_fig(fig, height=560, legend=False), width="stretch")
    html(tier_legend())

with right:
    with st.container(border=True):
        st.subheader("Action briefing", anchor=False)
        st.caption("A short note an officer can forward to field teams.")
        facts = build_facts(fc, as_of, h, c["city"])
        lang = st.radio("Language", list(LANGUAGES), format_func=LANGUAGES.get, horizontal=True, key="brief_lang",
                        label_visibility="collapsed")
        text, source = get_briefing(facts, use_llm=st.session_state.get("brief_llm", False), lang=lang)
        st.markdown(text)
        st.toggle("Reword with AI (optional, needs an API key)", value=False, key="brief_llm",
                  help="Off: instant template. On: one cached AI call that only sees the numbers above. "
                       "Falls back to the template on any error.")
        st.caption(f"Written by: {source}. Built only from the forecast numbers.")

# ---- Full list -------------------------------------------------------------------
section("All wards", "Expected cases, the likely range and the main reason for each ward.")
show = st.segmented_control("Show", ["All wards", "High and critical", "Getting worse"], default="All wards",
                            key="rb_filter", label_visibility="collapsed") or "All wards"
view = fc.assign(rank=range(1, len(fc) + 1))
if show == "High and critical":
    view = view[view["tier"].isin(["High", "Critical"])]
elif show == "Getting worse":
    view = view[view["escalating"]]

table = view.assign(
    ward=view["ward_id"].map(ward_name),
    range=view["lo"].round(0).astype(int).astype(str) + " – " + view["hi"].round(0).astype(int).astype(str),
    reason=view["main_driver"].map(driver_name),
    rain_vs_normal=((view["breeding_rain_mm"] / view["breeding_rain_normal_mm"].clip(lower=1) - 1) * 100).round(0),
)[["rank", "ward", "city", "tier_now", "tier", "pred", "range", "reason", "rain_vs_normal", "actual"]]

if table.empty:
    st.info("No ward matches this filter for the chosen week.")
else:
    st.dataframe(
        table.style.map(tier_cell_style, subset=["tier", "tier_now"])
        .format({"pred": "{:.1f}", "rain_vs_normal": "{:+.0f}%", "actual": "{:.0f}"}, na_rep="–"),
        hide_index=True, width="stretch", height=min(38 + 35 * len(table), 460),
        column_config={
            "rank": st.column_config.NumberColumn("#", width="small"),
            "ward": "Ward", "city": "City", "tier_now": "Today", "tier": f"In {h} weeks",
            "pred": st.column_config.NumberColumn("Expected cases"),
            "range": "Likely range",
            "reason": "Main reason",
            "rain_vs_normal": st.column_config.TextColumn("Rain, last 3 weeks vs normal"),
            "actual": st.column_config.NumberColumn("What really happened",
                                                    help="Real cases that week. Shown when replaying past weeks."),
        },
    )
st.write("")
st.download_button("Download the priority list (CSV)", fc.drop(columns=["tier_rank"]).to_csv(index=False).encode(),
                   file_name=f"dengue_priority_{as_of.date()}_h{h}.csv", mime="text/csv", icon=":material/download:")

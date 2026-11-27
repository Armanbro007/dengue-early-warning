"""Module 3 page: send spraying crews and see what the model expects 2-4 weeks later."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ui_text as tx
from dengue import config, simulator
from ui_common import INK, card_head, get_engine, html, page_header, style_fig
from ui_ops import L, offline_badge, ops_controls, ward

c = st.session_state["controls"]
s = ops_controls()
as_of, n = c["as_of"], tx.num
engine = get_engine()


@st.cache_data(show_spinner=False, max_entries=64)
def effects_for(as_of: str, city: str | None, per_crew: float) -> pd.DataFrame:
    return get_engine().crew_effects(as_of, city, per_crew)


page_header(
    L(f"What-if simulator · crews sent week of {tx.date(as_of)}", f"কী হলে কী হবে · {tx.date(as_of)} সপ্তাহে স্প্রে দল"),
    L("What do spraying crews buy us?", "স্প্রে দলে কতটা লাভ?"),
    L("A crew destroys part of the breeding water left by the last 3 weeks of rain. The same forecast model then re-forecasts "
      "weeks 2, 3 and 4, so the drop in cases, beds and saline comes from the model, ward by ward.",
      "একটি স্প্রে দল গত ৩ সপ্তাহের বৃষ্টিতে জমা পানির একটি অংশ নষ্ট করে। একই পূর্বাভাস মডেল তখন ২, ৩ ও ৪ সপ্তাহ পরের রোগী "
      "আবার হিসাব করে, তাই রোগী, শয্যা ও স্যালাইন কতটা কমবে তা মডেল থেকেই আসে।"),
)
offline_badge()

top = st.columns([2, 2, 3], gap="small")
mode = top[0].segmented_control(L("Choose wards", "ওয়ার্ড বাছাই"), ["auto", "manual"], default="auto", key="sim_mode",
                                format_func=lambda m: L("Best plan (auto)", "সেরা পরিকল্পনা") if m == "auto" else L("I pick wards", "আমি বাছব"))
per_crew = top[1].slider(L("Breeding water one crew clears", "একটি দল কতটা পানি নষ্ট করে"), 10, 30,
                         int(config.CREW_COVERAGE * 100), step=5, format="%d%%", key="sim_cov",
                         help=L("Planning assumption. Lower it to see how sure the ranking is.",
                                "পরিকল্পনার অনুমান। কমিয়ে দেখুন র‍্যাঙ্কিং কতটা স্থির।")) / 100
eff = effects_for(str(as_of.date()), c["city"], per_crew)
ranking = simulator.roi_ranking(eff)

if mode == "manual":
    default = ranking["ward_id"].head(5).tolist()
    picked = top[2].multiselect(L("Wards to treat", "যে ওয়ার্ডে স্প্রে"), ranking["ward_id"].tolist(), default=default,
                                format_func=ward, key="sim_wards")
    per = top[2].slider(L("Crews per ward", "প্রতি ওয়ার্ডে দল"), 1, config.MAX_CREWS_PER_WARD, 1, key="sim_per")
    plan = {w: per for w in picked}
else:
    plan = simulator.best_plan(eff, s.crews)
    top[2].caption(L(f"Sending the **{n(s.crews)} crews** from the sidebar one by one, each to the ward where the next crew prevents the most cases.",
                     f"সাইডবারের **{n(s.crews)}টি দল** একে একে সেই ওয়ার্ডে যায় যেখানে পরের দলটি সবচেয়ে বেশি রোগী কমায়।"))

sim = simulator.simulate(eff, plan, engine.supply_ratios, per_crew) if plan else pd.DataFrame()
crews_used = int(sum(plan.values()))
prevented = float(sim["cases_prevented"].sum()) if len(sim) else 0.0

with st.container(key="dark_sim"):
    k = st.columns(4)
    k[0].metric(L("Cases prevented (wk 2-4)", "রোগী কমবে (২-৪ সপ্তাহ)"), n(prevented, "{:,.1f}"),
                help=L("Model forecast without crews minus with crews, summed over 2, 3 and 4 weeks ahead.",
                       "দল ছাড়া পূর্বাভাস বিয়োগ দলসহ পূর্বাভাস, ২, ৩ ও ৪ সপ্তাহের যোগফল।"))
    k[1].metric(L("Hospital beds saved", "শয্যা বাঁচবে"), n(prevented * engine.supply_ratios["hospital_beds_required"], "{:,.1f}"))
    k[2].metric(L("Saline bags saved", "স্যালাইন বাঁচবে"), n(prevented * engine.supply_ratios["saline_bags_needed"], "{:,.0f}"))
    k[3].metric(L("Cases prevented per crew", "প্রতি দলে রোগী কমে"), n(prevented / crews_used if crews_used else 0, "{:,.2f}"),
                help=L("Return on each crew: the number to compare plans.", "প্রতিটি দলের ফল: পরিকল্পনা তুলনার মাপকাঠি।"))
st.write("")

left, right = st.columns([3, 2], gap="small")
with left, st.container(key="glass_sim_chart"):
    html(card_head(L("Treated wards: forecast with and without crews", "স্প্রে করা ওয়ার্ড: দলসহ ও দল ছাড়া পূর্বাভাস"),
                   L("Total cases expected 2, 3 and 4 weeks after the crews go out", "দল পাঠানোর ২, ৩ ও ৪ সপ্তাহ পর মোট প্রত্যাশিত রোগী"), "trend"))
    if len(sim):
        weeks = [as_of + pd.Timedelta(weeks=h) for h in config.HORIZONS]
        before = [sim[f"before_h{h}"].sum() for h in config.HORIZONS]
        after = [sim[f"after_h{h}"].sum() for h in config.HORIZONS]
        fig = go.Figure()
        fig.add_bar(x=weeks, y=before, name=L("No crews", "দল ছাড়া"), marker_color="rgba(17,19,24,.16)")
        fig.add_bar(x=weeks, y=after, name=L("With crews", "দলসহ"), marker_color="#2E8B57")
        for x, b, a in zip(weeks, before, after):
            fig.add_annotation(x=x, y=b, text=f"-{tx.num(b - a, '{:.0f}')}", showarrow=False, yshift=12, font=dict(color=INK))
        fig.update_xaxes(tickvals=weeks, ticktext=[tx.date(x) for x in weeks])
        st.plotly_chart(style_fig(fig, height=330), width="stretch", config={"displayModeBar": False})
    else:
        st.info(L("Pick at least one ward or add crews in the sidebar.", "অন্তত একটি ওয়ার্ড বাছুন বা সাইডবারে দল যোগ করুন।"))

with right, st.container(key="glass_sim_wards"):
    html(card_head(L("Where the crews go", "দল কোথায় যাবে"), L("Before → after, weeks 2-4 total", "আগে → পরে, ২-৪ সপ্তাহ মোট"), "target"))
    if len(sim):
        t = sim.sort_values("cases_prevented", ascending=False)
        st.dataframe(pd.DataFrame({
            L("Ward", "ওয়ার্ড"): t["ward_id"].map(ward), L("Crews", "দল"): t["crews"],
            L("Water cleared", "পানি নষ্ট"): t["coverage_pct"].map(lambda v: f"{v:.0f}%"),
            L("Before", "আগে"): t["cases_before"].round(1), L("After", "পরে"): t["cases_after"].round(1),
            L("Prevented", "কমবে"): t["cases_prevented"].round(1), L("Per crew", "প্রতি দলে"): t["roi"].round(2)}),
            hide_index=True, width="stretch", height=330)

st.write("")
with st.container(key="glass_sim_roi"):
    html(card_head(L("ROI ranking: cases prevented by one crew", "ফলাফল র‍্যাঙ্কিং: একটি দলে কত রোগী কমে"),
                   L("Every ward, best first. Wet, crowded, poorly drained wards gain most.",
                     "সব ওয়ার্ড, সেরাটি আগে। জলাবদ্ধ, ঘনবসতিপূর্ণ ওয়ার্ডে লাভ বেশি।"), "bars"))
    r = ranking.head(20).iloc[::-1]
    chosen = r["ward_id"].isin(plan)
    fig = go.Figure(go.Bar(y=r["ward_id"].map(ward), x=r["prevented_by_1_crew"], orientation="h",
                           marker_color=["#2E8B57" if x else "rgba(17,19,24,.25)" for x in chosen],
                           hovertemplate="%{y}: %{x:.2f}<extra></extra>"))
    st.plotly_chart(style_fig(fig, height=480, legend=False), width="stretch", config={"displayModeBar": False})
    st.caption(L(f"Green = gets a crew in this plan. Assumption: one crew clears {per_crew:.0%} of the breeding water "
                 "from the last 3 weeks of rain; a second crew clears the same share of what is left.",
                 f"সবুজ = এই পরিকল্পনায় দল পাচ্ছে। অনুমান: একটি দল গত ৩ সপ্তাহের বৃষ্টির জমা পানির {per_crew:.0%} নষ্ট করে; "
                 "দ্বিতীয় দল বাকি পানির একই অংশ নষ্ট করে।"))

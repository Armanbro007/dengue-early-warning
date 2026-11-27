"""Module 1 page: supplies and crews for every ward, under the stock the officer actually has."""
import plotly.graph_objects as go
import streamlit as st

import ui_text as tx
from dengue import config
from ui_common import card_head, get_engine, html, page_header, style_fig, tier_cell_style
from ui_ops import L, current_plan, offline_badge, ward

plan, c, target = current_plan()
w, s, n = plan.wards, plan.supply_summary, tx.num
sal, kit = s["saline_bags_needed"], s["diagnostic_kits_needed"]

page_header(
    L(f"Supply plan · week of {tx.date(target)}", f"সরবরাহ পরিকল্পনা · {tx.date(target)} সপ্তাহ"),
    L("Who gets saline, test kits and crews", "কে পাবে স্যালাইন, কিট ও স্প্রে দল"),
    L(f"Forecast cases are turned into supplies with ratios learned from past data, then the {n(plan.settings.stock_pct)}% stock "
      "you have is shared: riskiest and most crowded wards first, but every ward gets half its need before anyone is topped up.",
      f"পূর্বাভাসের রোগী সংখ্যাকে অতীত তথ্য থেকে শেখা অনুপাতে সরবরাহে রূপান্তর করা হয়, তারপর হাতে থাকা {n(plan.settings.stock_pct)}% মজুত "
      "ভাগ করা হয়: সবচেয়ে ঝুঁকিপূর্ণ ও ঘনবসতিপূর্ণ ওয়ার্ড আগে, তবে কাউকে পুরো দেওয়ার আগে সবাই চাহিদার অর্ধেক পায়।"),
)
offline_badge()

crit = int((w["deficit"] == "CRITICAL").sum())
short = int((w["deficit"] != "Fully supplied").sum())
with st.container(key="dark_supply"):
    k = st.columns(4)
    k[0].metric(L("Saline bags", "স্যালাইন ব্যাগ"), f"{n(sal['allocated'])} / {n(sal['need'])}",
                delta=f"-{n(sal['short'])}" if sal["short"] else L("enough", "যথেষ্ট"), delta_color="normal" if sal["short"] else "off")
    k[1].metric(L("Test kits", "পরীক্ষার কিট"), f"{n(kit['allocated'])} / {n(kit['need'])}",
                delta=f"-{n(kit['short'])}" if kit["short"] else L("enough", "যথেষ্ট"), delta_color="normal" if kit["short"] else "off")
    k[2].metric(L("Critical deficits", "জরুরি ঘাটতি"), n(crit),
                help=L("Wards getting less than half of what they need.", "যে ওয়ার্ড চাহিদার অর্ধেকও পাচ্ছে না।"))
    k[3].metric(L("Crews sent", "পাঠানো স্প্রে দল"), f"{n(sum(plan.crew_plan.values()))} / {n(int(w['crews_needed'].sum()))}",
                help=L("Assigned vs requested by High and Critical wards.", "উচ্চ ও অতি উচ্চ ঝুঁকির ওয়ার্ডের চাওয়ার বিপরীতে দেওয়া।"))
st.write("")

# ---- Live deficit warnings -----------------------------------------------------------
if crit:
    worst = w[w["deficit"] == "CRITICAL"]
    names = ", ".join(ward(x) for x in worst["ward_id"].head(8)) + ("…" if crit > 8 else "")
    st.error(L(f"**Critical supply deficit in {crit} wards** (under 50% of need): {names}. Raise stock or ration saline for severe cases.",
               f"**{n(crit)}টি ওয়ার্ডে জরুরি ঘাটতি** (চাহিদার ৫০%-এর কম): {names}। মজুত বাড়ান বা গুরুতর রোগীর জন্য স্যালাইন সংরক্ষণ করুন।"),
             icon=":material/error:")
if short - crit:
    st.warning(L(f"{short - crit} more wards get at least half but not all of their supplies.",
                 f"আরও {n(short - crit)}টি ওয়ার্ড অর্ধেকের বেশি পাচ্ছে, তবে পুরোটা নয়।"), icon=":material/warning:")
if not short:
    st.success(L("Every ward is fully supplied at this stock level.", "এই মজুতে সব ওয়ার্ড পুরো সরবরাহ পাচ্ছে।"),
               icon=":material/check_circle:")

# ---- Need vs allocated chart -----------------------------------------------------------
left, right = st.columns([3, 2], gap="small")
with left, st.container(key="glass_alloc_chart"):
    html(card_head(L("Saline: needed vs allocated", "স্যালাইন: চাহিদা বনাম বরাদ্দ"),
                   L("Top 20 wards in priority order", "অগ্রাধিকার অনুযায়ী প্রথম ২০ ওয়ার্ড"), "bars"))
    top = w.head(20).iloc[::-1]
    names = top["ward_id"].map(ward)
    fig = go.Figure()
    fig.add_bar(y=names, x=top["need_saline_bags_needed"], orientation="h", name=L("Needed", "চাহিদা"),
                marker_color="rgba(17,19,24,.12)", hovertemplate="%{y}: %{x}<extra></extra>")
    fig.add_bar(y=names, x=top["alloc_saline_bags_needed"], orientation="h", name=L("Allocated", "বরাদ্দ"),
                marker_color=[config.TIER_COLORS[t] for t in top["tier"]], hovertemplate="%{y}: %{x}<extra></extra>")
    fig.update_layout(barmode="overlay", bargap=0.25)
    st.plotly_chart(style_fig(fig, height=520), width="stretch", config={"displayModeBar": False})

with right, st.container(key="glass_alloc_how"):
    r = w.iloc[0]
    ratios = get_engine().supply_ratios
    html(card_head(L("How the numbers are made", "হিসাব কীভাবে হয়"), "", "sliders"))
    st.markdown(L(
        f"""1. **Need** = forecast cases × learned ratio: **{ratios['saline_bags_needed']:.2f}** saline bags,
**{ratios['diagnostic_kits_needed']:.2f}** kits and **{ratios['hospital_beds_required']:.2f}** beds per case
(learned from 2016-2023, off by under 0.03 units on 2024-2025).
2. **Priority** = tier first, then cases × (ward density ÷ median density).
3. **Round 1:** every ward gets 50% of its need, in priority order.
4. **Round 2:** what is left tops wards up to 100%, in priority order.
5. **Crews** go one by one to the ward where the next crew prevents the most cases (see What-if).

Example: **{ward(r['ward_id'])}** expects {r['plan_cases']:.1f} cases → needs {int(r['need_saline_bags_needed'])} bags,
gets {int(r['alloc_saline_bags_needed'])}.""",
        f"""১. **চাহিদা** = পূর্বাভাসের রোগী × শেখা অনুপাত: প্রতি রোগীতে **{ratios['saline_bags_needed']:.2f}** স্যালাইন,
**{ratios['diagnostic_kits_needed']:.2f}** কিট, **{ratios['hospital_beds_required']:.2f}** শয্যা (২০১৬-২০২৩ থেকে শেখা)।

২. **অগ্রাধিকার** = ঝুঁকির স্তর, তারপর রোগী × (ওয়ার্ডের ঘনত্ব ÷ মধ্যমা ঘনত্ব)।

৩. **প্রথম ধাপ:** অগ্রাধিকার অনুযায়ী সব ওয়ার্ড চাহিদার ৫০% পায়।

৪. **দ্বিতীয় ধাপ:** বাকি মজুত দিয়ে অগ্রাধিকার অনুযায়ী ১০০% পূরণ।

৫. **স্প্রে দল** একে একে সেই ওয়ার্ডে যায় যেখানে পরের দলটি সবচেয়ে বেশি রোগী কমায়।"""))

# ---- Full ward table -------------------------------------------------------------------
st.write("")
with st.container(key="glass_alloc_table"):
    html(card_head(L("Every ward, in priority order", "অগ্রাধিকার অনুযায়ী সব ওয়ার্ড"),
                   L("Allocated / needed. Fill = the worst-covered item.", "বরাদ্দ / চাহিদা। পূরণ = সবচেয়ে কম পাওয়া সামগ্রী।"), "list"))
    t = w.assign(
        ward=w["ward_id"].map(ward), city=w["city"].map(tx.city), tier=w["tier"].map(tx.tier),
        saline=w["alloc_saline_bags_needed"].astype(str) + " / " + w["need_saline_bags_needed"].astype(str),
        kits=w["alloc_diagnostic_kits_needed"].astype(str) + " / " + w["need_diagnostic_kits_needed"].astype(str),
        crews=w["crews_assigned"].astype(str) + " / " + w["crews_needed"].astype(str),
        status=w["deficit"].map({"CRITICAL": L("CRITICAL", "জরুরি ঘাটতি"), "Short": L("Short", "ঘাটতি"),
                                 "Fully supplied": L("Full", "পূর্ণ")}),
    )[["priority", "ward", "city", "tier", "plan_cases", "saline", "kits", "need_hospital_beds_required", "crews", "fill_pct", "status"]]
    cols = {"priority": "#", "ward": L("Ward", "ওয়ার্ড"), "city": L("City", "সিটি"), "tier": L("Risk", "ঝুঁকি"),
            "plan_cases": L("Cases", "রোগী"), "saline": L("Saline", "স্যালাইন"), "kits": L("Kits", "কিট"),
            "need_hospital_beds_required": L("Beds", "শয্যা"), "crews": L("Crews", "স্প্রে দল"),
            "fill_pct": L("Fill", "পূরণ"), "status": L("Status", "অবস্থা")}
    styled = t.rename(columns=cols).style.map(tier_cell_style, subset=[cols["tier"]]).map(
        lambda v: "color:#A61E4D;font-weight:700" if v in ("CRITICAL", "জরুরি ঘাটতি") else
        ("color:#8A6510;font-weight:600" if v in ("Short", "ঘাটতি") else ""), subset=[cols["status"]])
    st.dataframe(styled, hide_index=True, width="stretch", height=420, column_config={
        cols["plan_cases"]: st.column_config.NumberColumn(format="%.1f"),
        cols["fill_pct"]: st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d%%")})
    st.download_button(L("Download plan (CSV)", "পরিকল্পনা ডাউনলোড (CSV)"), w.round(2).to_csv(index=False).encode(),
                       f"supply_plan_{target:%Y-%m-%d}.csv", "text/csv", icon=":material/download:")

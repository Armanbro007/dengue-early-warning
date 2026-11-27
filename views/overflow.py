"""Module 2 page: wards over bed capacity, patients routed inside the same city, city headroom."""
import plotly.graph_objects as go
import streamlit as st

import ui_text as tx
from dengue import config
from ui_common import card_head, html, page_header, style_fig
from ui_ops import L, current_plan, offline_badge, ward

plan, c, target = current_plan()
w, cities, moves, n = plan.wards, plan.cities, plan.transfers, tx.num

page_header(
    L(f"Hospital surge · week of {tx.date(target)}", f"হাসপাতালে চাপ · {tx.date(target)} সপ্তাহ"),
    L("Where patients go when a ward is full", "ওয়ার্ড ভর্তি হলে রোগী কোথায় যাবে"),
    L("Beds needed come from the forecast. When a ward needs more beds than it has free, the extra patients are sent to the ward "
      "with the most free beds in the same city. Patients never cross a city boundary.",
      "পূর্বাভাস থেকে শয্যার চাহিদা হিসাব হয়। কোনো ওয়ার্ডে খালি শয্যার চেয়ে বেশি রোগী হলে বাড়তি রোগী একই সিটির "
      "সবচেয়ে বেশি খালি শয্যার ওয়ার্ডে পাঠানো হয়। রোগী কখনো সিটির বাইরে যায় না।"),
)
offline_badge()

with st.container(key="dark_beds"):
    k = st.columns(4)
    k[0].metric(L("Beds needed", "শয্যার চাহিদা"), n(int(cities["beds_needed"].sum())),
                help=L("Forecast cases × learned beds per case.", "পূর্বাভাসের রোগী × প্রতি রোগীতে শয্যা।"))
    k[1].metric(L("Beds free", "খালি শয্যা"), n(int(cities["beds_available"].sum())))
    k[2].metric(L("Patients moved", "স্থানান্তরিত রোগী"), n(int(moves["patients"].sum()) if len(moves) else 0),
                help=L("Overflow sent to a ward with room in the same city.", "একই সিটির খালি ওয়ার্ডে পাঠানো বাড়তি রোগী।"))
    k[3].metric(L("Still without a bed", "শয্যা পাননি"), n(int(cities["net_deficit"].sum())),
                help=L("The whole city is full: open surge beds.", "পুরো সিটি ভর্তি: অতিরিক্ত শয্যা খুলতে হবে।"))
st.write("")

full = cities[cities["net_deficit"] > 0]
for _, r in full.iterrows():
    st.error(L(f"**{r['city']} is full:** {int(r['net_deficit'])} patient(s) have no bed after routing. Open surge beds or ask for help.",
               f"**{tx.city(r['city'])} ভর্তি:** স্থানান্তরের পরও {n(int(r['net_deficit']))} জন রোগী শয্যা পাননি। অতিরিক্ত শয্যা খুলুন।"),
             icon=":material/emergency:")
if full.empty and len(moves):
    st.success(L("Routing solves every shortage: all overflow patients get a bed inside their own city.",
                 "স্থানান্তরের মাধ্যমে সব ঘাটতি মিটেছে: সবাই নিজ সিটিতেই শয্যা পাচ্ছেন।"), icon=":material/check_circle:")

# ---- City pools -------------------------------------------------------------------------
cols = st.columns(len(cities), gap="small")
for col, (_, r) in zip(cols, cities.iterrows()):
    util = r["utilisation_pct"]
    color = config.TIER_COLORS["Critical"] if util > 100 else (config.TIER_COLORS["High"] if util >= 90 else "#2E8B57")
    col.html(
        f'<div class="gc" style="padding:16px"><div style="font-weight:650">{tx.city(r["city"])}</div>'
        f'<div style="font-size:1.7rem;font-weight:650;color:{color}">{n(util)}%</div>'
        f'<div style="font-size:.8rem;color:#4B5160">{L("beds used", "শয্যা ব্যবহৃত")}: {n(int(r["beds_needed"]))} / {n(int(r["beds_available"]))}<br>'
        f'{L("headroom left", "বাকি খালি")}: <b>{n(int(r["headroom_left"]))}</b><br>'
        f'{L("transfers", "স্থানান্তর")}: {n(int(r["transfers"]))} · {L("no bed", "শয্যাহীন")}: <b>{n(int(r["net_deficit"]))}</b></div>'
        f'<div class="dw-stack" style="margin-top:8px"><span style="width:{min(util, 100):.0f}%;background:{color}"></span></div></div>')
st.write("")

# ---- One city in detail ------------------------------------------------------------------
city_list = list(cities["city"])
default = c["city"] if c["city"] in city_list else cities.sort_values("utilisation_pct").iloc[-1]["city"]
pick = st.segmented_control(L("City", "সিটি"), city_list, default=default, format_func=tx.city, key="beds_city") or default
d = w[w["city"] == pick].sort_values("ward_id")

left, right = st.columns([3, 2], gap="small")
with left, st.container(key="glass_beds_chart"):
    html(card_head(L(f"{pick}: beds needed vs free, per ward", f"{tx.city(pick)}: ওয়ার্ডভিত্তিক শয্যা চাহিদা বনাম খালি"),
                   L("Red = overflow, blue = patients received", "লাল = বাড়তি রোগী, নীল = গ্রহণ করা রোগী"), "bars"))
    names = d["ward_id"].map(ward)
    fig = go.Figure()
    fig.add_bar(x=names, y=d["beds_available"], name=L("Beds free", "খালি শয্যা"), marker_color="rgba(17,19,24,.13)")
    fig.add_bar(x=names, y=d["need_hospital_beds_required"] - d["overflow"], name=L("Own patients", "নিজের রোগী"),
                marker_color="#5B8DEF", base=0, width=0.45)
    fig.add_bar(x=names, y=d["received"], name=L("Received", "গ্রহণ"), marker_color="#9DB8F5", width=0.45,
                base=d["need_hospital_beds_required"] - d["overflow"])
    fig.add_bar(x=names, y=d["overflow"], name=L("Overflow", "বাড়তি"), marker_color=config.TIER_COLORS["Critical"], width=0.45,
                base=d["need_hospital_beds_required"] - d["overflow"] + d["received"])
    fig.update_layout(barmode="overlay")
    fig.update_xaxes(tickangle=-45)
    st.plotly_chart(style_fig(fig, height=380), width="stretch", config={"displayModeBar": False})

with right, st.container(key="glass_beds_moves"):
    html(card_head(L("Transfer orders", "স্থানান্তর নির্দেশ"), L("Biggest overflow first, to the ward with most free beds",
                                                              "সবচেয়ে বেশি বাড়তি আগে, সবচেয়ে বেশি খালি ওয়ার্ডে"), "arrow"))
    m = moves[moves["city"] == pick] if len(moves) else moves
    if m.empty:
        st.caption(L("No transfers needed in this city.", "এই সিটিতে স্থানান্তর দরকার নেই।"))
    else:
        st.dataframe(m.assign(from_ward=m["from_ward"].map(ward), to_ward=m["to_ward"].map(ward))[["from_ward", "to_ward", "patients"]]
                     .rename(columns={"from_ward": L("From", "থেকে"), "to_ward": L("To", "যাবে"), "patients": L("Patients", "রোগী")}),
                     hide_index=True, width="stretch", height=300)

st.write("")
with st.container(key="glass_beds_table"):
    html(card_head(L("Net deficit per ward", "ওয়ার্ডভিত্তিক নিট ঘাটতি"),
                   L("Overflow = needed − free. Net deficit = overflow that found no bed.", "বাড়তি = চাহিদা − খালি। নিট ঘাটতি = যে বাড়তি রোগী শয্যা পাননি।"), "list"))
    t = d[["ward_id", "need_hospital_beds_required", "bed_capacity", "beds_available", "overflow", "sent_out", "received",
           "net_bed_deficit", "headroom_left", "utilisation_pct"]].assign(ward_id=d["ward_id"].map(ward))
    t.columns = [L("Ward", "ওয়ার্ড"), L("Needed", "চাহিদা"), L("Usual beds", "স্বাভাবিক শয্যা"), L("Free", "খালি"),
                 L("Overflow", "বাড়তি"), L("Sent out", "পাঠানো"), L("Received", "গ্রহণ"), L("Net deficit", "নিট ঘাটতি"),
                 L("Headroom", "বাকি খালি"), L("Use %", "ব্যবহার %")]
    st.dataframe(t, hide_index=True, width="stretch")
    st.caption(L("Assumption (the dataset has no bed counts): each city's dengue beds = what it needed in 95% of 2016-2023 weeks, "
                 "split between wards by population density. Change 'Dengue beds free' in the sidebar to test a hospital crunch.",
                 "ধরে নেওয়া (ডেটাসেটে শয্যার সংখ্যা নেই): প্রতিটি সিটির ডেঙ্গু শয্যা = ২০১৬-২০২৩-এর ৯৫% সপ্তাহে যত লেগেছে, "
                 "জনঘনত্ব অনুযায়ী ওয়ার্ডে ভাগ করা। সাইডবারের 'খালি ডেঙ্গু শয্যা' কমিয়ে সংকট পরীক্ষা করুন।"))

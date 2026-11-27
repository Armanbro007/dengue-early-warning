"""Actions: turn the report into a plan, one plain question per step.

1 Send crews (what-if simulator, module 3)   2 Share supplies (constrained allocation, module 1)
3 Hospital beds (cross-ward overflow routing, module 2)   4 Send notices (SMS / WhatsApp / printable, module 4)
Everything here runs on this computer (module 5); only the optional "send by email/WhatsApp" links need internet."""
import io
import urllib.parse
import zipfile

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ui_text as tx
from dengue import config, dispatch, simulator
from ui_common import INK, about, card_head, get_engine, html, page_header, style_fig, tier_cell_style, tier_pill
from ui_ops import cached_plan
from ui_shell import L

engine = get_engine()
ss = st.session_state
c = ss["controls"]
as_of, h, n = c["as_of"], c["horizon"], tx.num
target = as_of + pd.Timedelta(weeks=h)
ratios = engine.supply_ratios
ward = tx.ward

# Answers live in plain keys so they survive page and language changes; widgets start from them
for k, v in (("crews", 20), ("stock", 60), ("beds", 80), ("cautious", False)):
    ss.setdefault(f"v_act_{k}", v)


def keep(k: str) -> dict:
    ss[f"act_{k}"] = ss[f"v_act_{k}"]
    return dict(key=f"act_{k}", on_change=lambda: ss.__setitem__(f"v_act_{k}", ss[f"act_{k}"]))


def plan_now():
    return cached_plan(str(as_of.date()), h, c["city"], float(ss["v_act_stock"]), int(ss["v_act_crews"]),
                       float(ss["v_act_beds"]), bool(ss["v_act_cautious"]))


STEPS = {"crews": L("1 · Send crews", "১ · স্প্রে দল"), "supplies": L("2 · Share supplies", "২ · সরবরাহ"),
         "beds": L("3 · Hospital beds", "৩ · হাসপাতাল শয্যা"), "notices": L("4 · Send notices", "৪ · নোটিশ পাঠান")}
ORDER = list(STEPS)
ss.setdefault("step", "crews")

page_header(L(f"Actions · plan for the week of {tx.date(target)}", f"পদক্ষেপ · {tx.date(target)} সপ্তাহের পরিকল্পনা"),
            L("Plan your response in 4 steps", "৪টি ধাপে ব্যবস্থা নিন"),
            L(f"Cases are expected to rise around <b>{tx.day(target)}</b>, so this week is the time to act. Go through the steps in order: "
              "<b>1</b> send spray crews where they cut the most cases, <b>2</b> share saline and test kits (riskiest, most crowded wards "
              "first), <b>3</b> move patients from full wards to wards with free beds in the same city, <b>4</b> send every ward its "
              "orders. Answer one question per step and the plan updates at once.",
              f"<b>{tx.day(target)}</b> নাগাদ রোগী বাড়ার আশঙ্কা, তাই এ সপ্তাহেই ব্যবস্থা নিন। ধাপগুলো ক্রমানুসারে করুন: "
              "<b>১</b> যেখানে সবচেয়ে বেশি রোগী কমে সেখানে স্প্রে দল পাঠান, <b>২</b> স্যালাইন ও কিট ভাগ করুন (বেশি ঝুঁকি ও ঘনবসতির "
              "ওয়ার্ড আগে), <b>৩</b> ভর্তি ওয়ার্ডের রোগী একই সিটির খালি ওয়ার্ডে পাঠান, <b>৪</b> প্রতিটি ওয়ার্ডে নির্দেশনা পাঠান। "
              "প্রতিটি ধাপে একটি প্রশ্নের উত্তর দিন, পরিকল্পনা সঙ্গে সঙ্গে বদলাবে।"))

with st.container(key="stepper"):
    step = st.segmented_control(L("Step", "ধাপ"), ORDER, format_func=STEPS.get, key="step", required=True,
                                label_visibility="collapsed")
st.write("")


def next_button(cur: str) -> None:
    i = ORDER.index(cur)
    if i + 1 < len(ORDER):
        nxt = ORDER[i + 1]
        st.button(L(f"Next: {STEPS[nxt].split('· ')[1]}", f"পরের ধাপ: {STEPS[nxt].split('· ')[1]}"), icon=":material/arrow_forward:",
                  icon_position="right", type="primary", key=f"next_{cur}", on_click=lambda: ss.__setitem__("step", nxt))


def answer(text: str) -> None:
    html(f'<p class="dw-answer">{text}</p>')


# =============================== Step 1: crews (module 3) ===============================
if step == "crews":
    q, a = st.columns([4, 8], gap="small")
    with q, st.container(key="glass_q_crews"):
        html(card_head(L("How many spray crews can you send this week?", "এ সপ্তাহে কয়টি স্প্রে দল পাঠাতে পারবেন?"),
                       L("Larvicide or fogging teams. One crew works in one ward.", "লার্ভিসাইড বা ফগিং দল। একটি দল একটি ওয়ার্ডে কাজ করে।"),
                       "mosquito"))
        crews = int(st.number_input(L("Crews", "দল"), 0, 240, step=1, label_visibility="collapsed", **keep("crews")))
        st.caption(L("Example number: the data does not say how many crews each city has, so 20 is only a starting example. "
                     "Type your real number and the results change at once.",
                     "উদাহরণ: ডেটায় প্রতিটি সিটির দলের সংখ্যা নেই, তাই ২০ শুধু একটি উদাহরণ। আপনার আসল সংখ্যা লিখুন, ফল সঙ্গে সঙ্গে বদলাবে।"))
        mode = st.segmented_control(L("Choose wards", "ওয়ার্ড বাছাই"), ["auto", "manual"], key="crew_mode", default="auto",
                                    format_func=lambda m: L("Best plan for me", "সেরা পরিকল্পনা") if m == "auto" else L("I pick the wards", "আমি বাছব"))
        next_button("crews")
    plan = plan_now()
    eff = plan.effects
    if mode == "manual":
        rank = simulator.roi_ranking(eff)
        with q:
            picked = st.multiselect(L("Wards to spray", "যে ওয়ার্ডে স্প্রে"), rank["ward_id"].tolist(), default=rank["ward_id"].head(5).tolist(),
                                    format_func=ward, key="crew_pick")
            per = st.slider(L("Crews per ward", "প্রতি ওয়ার্ডে দল"), 1, config.MAX_CREWS_PER_WARD, 1, key="crew_per")
        crew_plan = {w: per for w in picked}
    else:
        crew_plan = simulator.best_plan(eff, crews)
    sim = simulator.simulate(eff, crew_plan, ratios) if crew_plan else pd.DataFrame()
    used = int(sum(crew_plan.values()))
    prevented = float(sim["cases_prevented"].sum()) if len(sim) else 0.0
    need = int(plan.wards["crews_needed"].sum())
    with a, st.container(key="glass_a_crews"):
        if used:
            beds_s, sal_s = about(prevented * ratios["hospital_beds_required"]), about(prevented * ratios["saline_bags_needed"])
            answer(L(f"Send <b>{n(used)} crews</b> to these <b>{n(len(sim))} wards</b>. Over the next 2 to 4 weeks they should prevent "
                     f"<b>about {about(prevented)} cases</b>, saving about {beds_s} hospital bed-weeks and {sal_s} saline bags.",
                     f"<b>{n(used)}টি দল</b> এই <b>{n(len(sim))}টি ওয়ার্ডে</b> পাঠান। আগামী ২ থেকে ৪ সপ্তাহে <b>প্রায় {about(prevented)} জন</b> "
                     f"কম অসুস্থ হবেন, প্রায় {beds_s}টি শয্যা-সপ্তাহ ও {sal_s}টি স্যালাইন বাঁচবে।"))
            if mode == "auto" and used < need:
                st.caption(L(f"High-risk wards ask for {n(need)} crews in total ({n(need - used)} more than you have).",
                             f"উচ্চ ঝুঁকির ওয়ার্ডগুলোর মোট চাহিদা {n(need)}টি দল ({n(need - used)}টি বেশি)।"))
            left, right = st.columns([6, 5], gap="medium")
            with left:
                tiers = plan.wards.set_index("ward_id")["tier"]

                def crew_rows(part):
                    out = []
                    for r in part.itertuples():
                        dots = "".join("<i></i>" for _ in range(r.crews)) + "".join(
                            '<i class="e"></i>' for _ in range(config.MAX_CREWS_PER_WARD - r.crews))
                        out.append(f'<div class="dw-crewrow"><div><div class="nm">{ward(r.ward_id)}</div>'
                                   f'<div class="sub">{tier_pill(tiers[r.ward_id])}</div></div>'
                                   f'<div class="dots" title="{r.crews}">{dots}</div>'
                                   f'<div class="gain">−<b>{about(r.cases_prevented)}</b> {L("cases", "রোগী")}</div></div>')
                    return "".join(out)
                ordered = sim.sort_values("cases_prevented", ascending=False)
                html(crew_rows(ordered.head(6)))
                if len(ordered) > 6:
                    with st.expander(L(f"See all {len(ordered)} wards", f"সব {n(len(ordered))}টি ওয়ার্ড দেখুন")):
                        html(crew_rows(ordered.iloc[6:]))
            with right:
                weeks = [as_of + pd.Timedelta(weeks=k) for k in config.HORIZONS]
                before = [sim[f"before_h{k}"].sum() for k in config.HORIZONS]
                after = [sim[f"after_h{k}"].sum() for k in config.HORIZONS]
                fig = go.Figure()
                fig.add_bar(x=weeks, y=before, name=L("Without crews", "দল ছাড়া"), marker_color="rgba(17,19,24,.16)")
                fig.add_bar(x=weeks, y=after, name=L("With crews", "দলসহ"), marker_color="#2E8B57")
                for x, b, af in zip(weeks, before, after):
                    fig.add_annotation(x=x, y=b, text=f"−{n(b - af, '{:.0f}')}", showarrow=False, yshift=12, font=dict(color=INK))
                fig.update_xaxes(tickvals=weeks, ticktext=[tx.short(x) for x in weeks])
                fig.update_layout(title=L("Cases: with vs without crews", "রোগী: দলসহ বনাম দল ছাড়া"))
                st.plotly_chart(style_fig(fig, height=300), width="stretch", config={"displayModeBar": False})
        else:
            st.info(L("Add at least one crew (or pick wards) to see where it should go.", "অন্তত একটি দল যোগ করুন বা ওয়ার্ড বাছুন।"))
    with st.expander(L("Which wards gain most from one crew? (ROI ranking)", "একটি দলে কোন ওয়ার্ডে সবচেয়ে বেশি লাভ?"), icon=":material/leaderboard:"):
        r = simulator.roi_ranking(eff).head(15).iloc[::-1]
        fig = go.Figure(go.Bar(y=r["ward_id"].map(ward), x=r["prevented_by_1_crew"], orientation="h",
                               marker_color=["#2E8B57" if w in crew_plan else "rgba(17,19,24,.25)" for w in r["ward_id"]],
                               hovertemplate="%{y}: %{x:.2f}<extra></extra>"))
        fig.update_layout(title=L("Cases prevented by one crew (weeks 2-4). Green = in your plan.", "একটি দলে কত রোগী কমে। সবুজ = পরিকল্পনায় আছে।"))
        st.plotly_chart(style_fig(fig, height=430, legend=False), width="stretch", config={"displayModeBar": False})
    with st.expander(L("How is this calculated?", "হিসাব কীভাবে হয়?"), icon=":material/calculate:"):
        st.markdown(L(
            f"A crew destroys part of the standing water left by the last 3 weeks of rain (assumed {config.CREW_COVERAGE:.0%} per crew; "
            "a second crew clears the same share of what is left). The **same trained forecast model** then re-forecasts weeks 2, 3 and 4 "
            "with that rain removed. Cases prevented = forecast without crews − forecast with crews. Beds and saline saved = cases prevented "
            "× the per-case ratios learned from the data. Crews are sent one at a time to the ward where the next crew prevents the most cases.",
            "একটি দল গত ৩ সপ্তাহের বৃষ্টির জমা পানির একটি অংশ নষ্ট করে। একই মডেল সেই পানি বাদ দিয়ে ২, ৩ ও ৪ সপ্তাহ পরের রোগী আবার হিসাব করে। "
            "কমা রোগী = দল ছাড়া পূর্বাভাস − দলসহ পূর্বাভাস।"))

# =============================== Step 2: supplies (module 1) ===============================
elif step == "supplies":
    q, a = st.columns([4, 8], gap="small")
    with q, st.container(key="glass_q_supplies"):
        html(card_head(L("How much saline and test kits are in your store?", "আপনার মজুতে কতটা স্যালাইন ও কিট আছে?"),
                       L("As a share of what all wards need for that week.", "সব ওয়ার্ডের সে সপ্তাহের মোট চাহিদার শতাংশ হিসেবে।"), "drop"))
        stock = st.slider(L("Regional stock", "আঞ্চলিক মজুত"), 30, 100, step=5, format="%d%%", **keep("stock"))
        cautious = st.toggle(L("Plan for a bad week", "খারাপ সপ্তাহ ধরে পরিকল্পনা"), **keep("cautious"),
                             help=L("Use the top of the likely range instead of the expected number (safer early in the season).",
                                    "প্রত্যাশিত সংখ্যার বদলে সম্ভাব্য সীমার ঊর্ধ্বসীমা ধরে হিসাব।"))
        st.caption(L("Spray crews come from step 1. Beds are checked in step 3.", "স্প্রে দল ধাপ ১ থেকে। শয্যা ধাপ ৩-এ।"))
        next_button("supplies")
    plan = cached_plan(str(as_of.date()), h, c["city"], float(stock), int(ss["v_act_crews"]), float(ss["v_act_beds"]), bool(cautious))
    w, s = plan.wards, plan.supply_summary
    sal, kit = s["saline_bags_needed"], s["diagnostic_kits_needed"]
    crit = w[w["deficit"] == "CRITICAL"]
    short = int((w["deficit"] != "Fully supplied").sum())
    with a, st.container(key="glass_a_supplies"):
        answer(L(f"You have <b>{n(sal['allocated'])} of {n(sal['need'])}</b> saline bags and <b>{n(kit['allocated'])} of {n(kit['need'])}</b> "
                 "test kits needed. Every ward first gets half of what it needs; what is left goes to the riskiest and most crowded wards.",
                 f"প্রয়োজনের <b>{n(sal['need'])}টির মধ্যে {n(sal['allocated'])}টি</b> স্যালাইন ও <b>{n(kit['need'])}টির মধ্যে {n(kit['allocated'])}টি</b> "
                 "কিট আছে। প্রথমে সবাই চাহিদার অর্ধেক পায়, বাকিটা বেশি ঝুঁকি ও ঘনবসতির ওয়ার্ডে যায়।"))
        if len(crit):
            names = ", ".join(ward(x) for x in crit["ward_id"].head(8)) + ("…" if len(crit) > 8 else "")
            st.error(L(f"**CRITICAL supply deficit in {len(crit)} wards** (under half of need): {names}. Raise stock or ration saline for severe cases.",
                       f"**{n(len(crit))}টি ওয়ার্ডে জরুরি ঘাটতি** (চাহিদার অর্ধেকের কম): {names}।"), icon=":material/error:")
        if short - len(crit):
            st.warning(L(f"**Deficit warning:** {short - len(crit)} wards get at least half but not all of what they need.",
                         f"**ঘাটতি:** আরও {n(short - len(crit))}টি ওয়ার্ড অর্ধেকের বেশি পাচ্ছে, তবে পুরোটা নয়।"), icon=":material/warning:")
        if not short:
            st.success(L("Every ward is fully supplied at this stock level.", "এই মজুতে সব ওয়ার্ড পুরো সরবরাহ পাচ্ছে।"), icon=":material/check_circle:")
        with st.container(key="dark_supply"):
            k = st.columns(4)
            k[0].metric(L("Saline bags", "স্যালাইন"), f"{n(sal['allocated'])} / {n(sal['need'])}")
            k[1].metric(L("Test kits", "কিট"), f"{n(kit['allocated'])} / {n(kit['need'])}")
            k[2].metric(L("Beds needed", "শয্যা চাহিদা"), n(int(w["need_hospital_beds_required"].sum())))
            k[3].metric(L("Crews sent", "স্প্রে দল"), f"{n(sum(plan.crew_plan.values()))} / {n(int(w['crews_needed'].sum()))}")
    st.write("")
    with st.container(key="glass_alloc_table"):
        html(card_head(L("Who gets what, in priority order", "কে কী পাবে, অগ্রাধিকার অনুযায়ী"),
                       L("Priority = risk level first, then expected cases × population density. Shown as allocated / required.",
                         "অগ্রাধিকার = ঝুঁকির স্তর, তারপর রোগী × জনঘনত্ব। বরাদ্দ / চাহিদা।"), "list"))
        t = w.assign(ward=w["ward_id"].map(ward), city=w["city"].map(tx.city), tier=w["tier"].map(tx.tier),
                     saline=w["alloc_saline_bags_needed"].astype(str) + " / " + w["need_saline_bags_needed"].astype(str),
                     kits=w["alloc_diagnostic_kits_needed"].astype(str) + " / " + w["need_diagnostic_kits_needed"].astype(str),
                     crews=w["crews_assigned"].astype(str) + " / " + w["crews_needed"].astype(str),
                     status=w["deficit"].map({"CRITICAL": L("CRITICAL", "জরুরি ঘাটতি"), "Short": L("Short", "ঘাটতি"), "Fully supplied": L("Full", "পূর্ণ")}),
                     )[["priority", "ward", "city", "tier", "population_density_sqkm", "plan_cases", "saline", "kits",
                        "need_hospital_beds_required", "crews", "fill_pct", "status"]]
        cols = {"priority": "#", "ward": L("Ward", "ওয়ার্ড"), "city": L("City", "সিটি"), "tier": L("Risk", "ঝুঁকি"),
                "population_density_sqkm": L("People/km²", "জনঘনত্ব"), "plan_cases": L("Cases", "রোগী"), "saline": L("Saline", "স্যালাইন"),
                "kits": L("Kits", "কিট"), "need_hospital_beds_required": L("Beds", "শয্যা"), "crews": L("Crews", "দল"),
                "fill_pct": L("Covered", "পূরণ"), "status": L("Status", "অবস্থা")}
        styled = t.rename(columns=cols).style.map(tier_cell_style, subset=[cols["tier"]]).map(
            lambda v: "color:#A61E4D;font-weight:700" if v in ("CRITICAL", "জরুরি ঘাটতি") else
            ("color:#8A6510;font-weight:600" if v in ("Short", "ঘাটতি") else ""), subset=[cols["status"]])
        st.dataframe(styled, hide_index=True, width="stretch", height=420, column_config={
            cols["plan_cases"]: st.column_config.NumberColumn(format="%.1f"),
            cols["fill_pct"]: st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d%%")})
        st.download_button(L("Download supply plan (CSV)", "সরবরাহ পরিকল্পনা (CSV)"), w.round(2).to_csv(index=False).encode(),
                           f"supply_plan_{target:%Y-%m-%d}.csv", "text/csv", icon=":material/download:")
    with st.expander(L("How is this calculated?", "হিসাব কীভাবে হয়?"), icon=":material/calculate:"):
        st.markdown(L(
            f"1. **Need** = forecast cases × ratios learned from the data: {ratios['saline_bags_needed']:.2f} saline bags, "
            f"{ratios['diagnostic_kits_needed']:.2f} kits and {ratios['hospital_beds_required']:.2f} beds per case.\n"
            "2. **Priority** = risk level first (Critical, High, Medium, Low), then cases × (ward density ÷ median density).\n"
            "3. **Round 1:** every ward gets 50% of its need, in priority order (no ward is left with nothing).\n"
            "4. **Round 2:** what is left tops wards up to 100%, in priority order.\n"
            "5. **Deficit alert:** CRITICAL below 50% of need, Short below 100%.",
            "১. **চাহিদা** = পূর্বাভাসের রোগী × ডেটা থেকে শেখা অনুপাত।\n২. **অগ্রাধিকার** = ঝুঁকি, তারপর রোগী × জনঘনত্ব।\n"
            "৩. প্রথমে সবাই ৫০% পায়।\n৪. বাকিটা অগ্রাধিকার অনুযায়ী ১০০% পর্যন্ত।\n৫. ৫০%-এর কম হলে জরুরি ঘাটতি।"))

# =============================== Step 3: beds (module 2) ===============================
elif step == "beds":
    q, a = st.columns([4, 8], gap="small")
    with q, st.container(key="glass_q_beds"):
        html(card_head(L("How many dengue beds are free this week?", "এ সপ্তাহে কতটি ডেঙ্গু শয্যা খালি?"),
                       L("As a share of each ward's usual dengue beds.", "প্রতিটি ওয়ার্ডের স্বাভাবিক ডেঙ্গু শয্যার শতাংশ হিসেবে।"), "pulse"))
        beds = st.slider(L("Beds free", "খালি শয্যা"), 30, 100, step=5, format="%d%%", **keep("beds"))
        st.caption(L("The data has no bed counts, so each city's dengue beds = what it needed in 95% of 2016-2023 weeks, split between "
                     "wards by population density. Patients are only moved inside the same city.",
                     "ডেটায় শয্যার সংখ্যা নেই, তাই প্রতিটি সিটির শয্যা = ২০১৬-২০২৩-এর ৯৫% সপ্তাহে যত লেগেছে, জনঘনত্ব অনুযায়ী ভাগ। "
                     "রোগী শুধু একই সিটির ভেতরে সরানো হয়।"))
        next_button("beds")
    plan = cached_plan(str(as_of.date()), h, c["city"], float(ss["v_act_stock"]), int(ss["v_act_crews"]), float(beds), bool(ss["v_act_cautious"]))
    w, cities, moves = plan.wards, plan.cities, plan.transfers
    over = w[w["overflow"] > 0].sort_values("overflow", ascending=False)
    moved = int(moves["patients"].sum()) if len(moves) else 0
    no_bed = int(cities["net_deficit"].sum())
    with a, st.container(key="glass_a_beds"):
        if len(over):
            answer(L(f"<b>{len(over)} wards</b> will need more beds than they have free. Move <b>{n(moved)} patients</b> to wards with free beds "
                     "in the same city" + (f". <b>{n(no_bed)} patients</b> still have no bed." if no_bed else ": every patient gets a bed."),
                     f"<b>{n(len(over))}টি ওয়ার্ডে</b> খালি শয্যার চেয়ে বেশি রোগী হবে। <b>{n(moved)} জন রোগী</b> একই সিটির খালি ওয়ার্ডে পাঠান"
                     + (f"। <b>{n(no_bed)} জন</b> এখনো শয্যা পাননি।" if no_bed else ": সবাই শয্যা পাবেন।")))
        else:
            answer(L("Every ward has enough free beds for its expected patients.", "প্রতিটি ওয়ার্ডে যথেষ্ট খালি শয্যা আছে।"))
        for _, r in cities[cities["net_deficit"] > 0].iterrows():
            st.error(L(f"**{r['city']} is full:** {int(r['net_deficit'])} patient(s) have no bed after routing. Open surge beds or ask for help.",
                       f"**{tx.city(r['city'])} ভর্তি:** স্থানান্তরের পরও {n(int(r['net_deficit']))} জন শয্যা পাননি।"), icon=":material/emergency:")
        if len(moves):
            html(f'<div class="mono" style="margin:10px 0 4px">{L("TRANSFER ORDERS", "স্থানান্তর নির্দেশ")}</div>' + "".join(
                f'<div class="dw-crewrow" style="grid-template-columns:minmax(0,1.3fr) auto minmax(0,1.3fr) auto">'
                f'<div><div class="nm">{ward(m.from_ward)}</div><div class="sub">{L("full", "ভর্তি")}</div></div>'
                f'<div style="color:#8B909C">→</div><div><div class="nm">{ward(m.to_ward)}</div><div class="sub">{tx.city(m.city)}</div></div>'
                f'<div class="gain"><b>{n(int(m.patients))}</b> {L("patient" if int(m.patients) == 1 else "patients", "রোগী")}</div></div>'
                for m in moves.sort_values("patients", ascending=False).itertuples()))
    st.write("")
    cols = st.columns(len(cities), gap="small")
    for col, (_, r) in zip(cols, cities.iterrows()):
        util = r["utilisation_pct"]
        color = config.TIER_COLORS["Critical"] if util > 100 else (config.TIER_COLORS["High"] if util >= 90 else "#2E8B57")
        col.html(f'<div class="gc" style="padding:16px"><div style="font-weight:650">{tx.city(r["city"])}</div>'
                 f'<div style="font-size:1.7rem;font-weight:650;color:{color}">{n(util)}%</div>'
                 f'<div style="font-size:.8rem;color:#4B5160">{L("beds in use", "শয্যা ব্যবহৃত")}: {n(int(r["beds_needed"]))} / {n(int(r["beds_available"]))}<br>'
                 f'{L("beds left", "বাকি খালি")}: <b>{n(int(r["headroom_left"]))}</b><br>'
                 f'{L("moved", "স্থানান্তর")}: {n(int(r["transfers"]))} · {L("no bed", "শয্যাহীন")}: <b>{n(int(r["net_deficit"]))}</b></div>'
                 f'<div class="dw-stack" style="margin-top:8px"><span style="width:{min(util, 100):.0f}%;background:{color}"></span></div></div>')
    st.write("")
    with st.container(key="glass_beds_table"):
        html(card_head(L("Wards over their bed limit", "শয্যার সীমা ছাড়ানো ওয়ার্ড"),
                       L("Overflow = beds needed − beds free. Net deficit = overflow that found no bed in the city.",
                         "বাড়তি = চাহিদা − খালি। নিট ঘাটতি = যে বাড়তি রোগী সিটিতে শয্যা পাননি।"), "list"))
        show_all = st.toggle(L("Show every ward", "সব ওয়ার্ড দেখুন"), key="beds_all")
        d = w if show_all else over
        t = d[["ward_id", "city", "need_hospital_beds_required", "bed_capacity", "beds_available", "overflow", "sent_out", "sent_to",
               "received", "net_bed_deficit", "headroom_left", "utilisation_pct"]].assign(ward_id=d["ward_id"].map(ward), city=d["city"].map(tx.city),
                                                                                          sent_to=d["sent_to"].map(lambda s: ", ".join(ward(x) for x in s.split(", ")) if s else ""))
        t.columns = [L("Ward", "ওয়ার্ড"), L("City", "সিটি"), L("Beds needed", "চাহিদা"), L("Usual beds", "স্বাভাবিক"), L("Free", "খালি"),
                     L("Overflow", "বাড়তি"), L("Sent out", "পাঠানো"), L("Sent to", "যেখানে"), L("Received", "গ্রহণ"),
                     L("Net deficit", "নিট ঘাটতি"), L("Beds left", "বাকি"), L("Use %", "ব্যবহার %")]
        st.dataframe(t, hide_index=True, width="stretch")
        if len(moves):
            st.download_button(L("Download transfer orders (CSV)", "স্থানান্তর নির্দেশ (CSV)"), moves.to_csv(index=False).encode(),
                               f"bed_transfers_{target:%Y-%m-%d}.csv", "text/csv", icon=":material/download:")

# =============================== Step 4: notices (module 4) ===============================
else:
    plan = plan_now()
    w = plan.wards
    notes = dispatch.notices(plan, target).set_index("ward_id")
    q, a = st.columns([4, 8], gap="small")
    with q, st.container(key="glass_q_notices"):
        html(card_head(L("Which ward's notice do you want?", "কোন ওয়ার্ডের নোটিশ চান?"),
                       L("Wards with a problem come first.", "সমস্যাগ্রস্ত ওয়ার্ড আগে।"), "bell"))
        order = pd.concat([notes[notes["status"] != "OK"], notes[notes["status"] == "OK"]])
        labels = [f"#{int(r.priority)} {ward(i)} · {r.status}" for i, r in order.iterrows()]
        back = dict(zip(labels, order.index))
        key = f"notice_pick_{tx.lang()}"
        if ss.get(key) not in back:
            ss.pop(key, None)
        pick = back[st.selectbox(L("Ward", "ওয়ার্ড"), labels, key=key, label_visibility="collapsed")]
        row = notes.loc[pick]
        counts = notes["status"].value_counts()
        st.caption(L(f"{len(notes)} notices ready: {int(counts.get('CRITICAL DEFICIT', 0))} critical, {int(counts.get('SHORTAGE', 0))} shortage, "
                     f"{int(counts.get('OK', 0))} OK.", f"{n(len(notes))}টি নোটিশ প্রস্তুত।"))
        st.divider()
        html(card_head(L("Send it", "পাঠান"), L("Type an email address or a WhatsApp number.", "ইমেইল বা হোয়াটসঅ্যাপ নম্বর লিখুন।"), "arrow"))
        to = st.text_input(L("Email or WhatsApp number", "ইমেইল বা হোয়াটসঅ্যাপ নম্বর"), placeholder="name@example.org  /  +8801XXXXXXXXX",
                           key="notice_to", label_visibility="collapsed").strip()
        body = row["whatsapp"].replace("*", "")
        if not config.ALLOW_NETWORK:
            st.info(L("Offline mode: sending needs internet. Download the notice below and send it later.",
                      "অফলাইন মোড: পাঠাতে ইন্টারনেট লাগে। নোটিশ ডাউনলোড করে পরে পাঠান।"), icon=":material/wifi_off:")
        elif to:
            if "@" in to:
                url = (f"mailto:{urllib.parse.quote(to)}?subject=" + urllib.parse.quote(f"Dengue dispatch notice: {dispatch.ward_label(pick)}, week of {target:%d %b %Y}")
                       + "&body=" + urllib.parse.quote(body))
                st.link_button(L("Open in email", "ইমেইলে খুলুন"), url, icon=":material/mail:", type="primary")
            else:
                digits = "".join(ch for ch in to if ch.isdigit())
                if digits.startswith("01") and len(digits) == 11:
                    digits = "88" + digits  # Bangladesh mobile without country code
                if len(digits) >= 10:
                    st.link_button(L("Open in WhatsApp", "হোয়াটসঅ্যাপে খুলুন"), f"https://wa.me/{digits}?text=" + urllib.parse.quote(row["whatsapp"]),
                                   icon=":material/chat:", type="primary")
                else:
                    st.warning(L("That does not look like an email address or a phone number.", "এটি ইমেইল বা ফোন নম্বর মনে হচ্ছে না।"))
        st.caption(L("Note: sending opens your email app or WhatsApp with the message filled in, so it needs internet. "
                     "Making the notices does not: it works offline.",
                     "লক্ষ্য করুন: পাঠাতে ইন্টারনেট লাগে। নোটিশ তৈরি অফলাইনেও হয়।"))
    with a, st.container(key="glass_a_notices"):
        badge = {"CRITICAL DEFICIT": "error", "SHORTAGE": "warning", "OK": "success"}[row["status"]]
        getattr(st, badge)(f"{ward(pick)} · {L('Status', 'অবস্থা')}: **{row['status']}**")
        one = w[w["ward_id"] == pick]
        page = dispatch.brief_html(one, target, f"Dispatch notice {pick}", cities=plan.cities)
        tabs = st.tabs([L("Printable notice", "প্রিন্টযোগ্য নোটিশ"), "WhatsApp", "SMS", L("City summary", "সিটির সারাংশ")])
        with tabs[0]:
            if hasattr(st, "iframe"):
                st.iframe(page, height=620)
            else:
                import streamlit.components.v1 as components
                components.html(page, height=620, scrolling=True)
            b = st.columns(2)
            b[0].download_button(L("Download notice (HTML)", "নোটিশ (HTML)"), page.encode(), f"notice_{pick}.html", "text/html", icon=":material/download:")
            pdf = dispatch.brief_pdf(one, target)
            if pdf:
                b[1].download_button(L("Download notice (PDF)", "নোটিশ (PDF)"), pdf, f"notice_{pick}.pdf", "application/pdf", icon=":material/picture_as_pdf:")
        with tabs[1]:
            st.code(row["whatsapp"], language=None, wrap_lines=True)
        with tabs[2]:
            st.markdown(f"**SMS** ({len(row['sms'])}/160)")
            st.code(row["sms"], language=None, wrap_lines=True)
            st.markdown(L("**Bangla SMS** (field staff)", "**বাংলা এসএমএস** (মাঠকর্মী)"))
            st.code(row["sms_bangla"], language=None, wrap_lines=True)
        with tabs[3]:
            st.code(dispatch.city_digest(plan, target), language=None, wrap_lines=True)

    def bundle() -> bytes:
        buf = io.BytesIO()
        allnotes = notes.reset_index()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("sms_messages.csv", allnotes[["priority", "ward_id", "city", "status", "sms"]].to_csv(index=False))
            z.writestr("sms_bangla.txt", "\n\n".join(f"[{x}]\n{y}" for x, y in zip(allnotes["ward_id"], allnotes["sms_bangla"])))
            z.writestr("whatsapp_messages.txt", "\n\n-----\n\n".join(allnotes["whatsapp"]))
            z.writestr("city_digest_whatsapp.txt", dispatch.city_digest(plan, target))
            z.writestr("commissioner_briefs.html", dispatch.brief_html(w, target, cities=plan.cities))
            pdf_all = dispatch.brief_pdf(w, target)
            if pdf_all:
                z.writestr("commissioner_briefs.pdf", pdf_all)
            z.writestr("dispatch_plan.csv", w.round(2).to_csv(index=False))
            z.writestr("bed_transfers.csv", plan.transfers.to_csv(index=False))
        return buf.getvalue()

    st.write("")
    st.download_button(L("Download all 60 notices (ZIP: SMS, WhatsApp, printable HTML and PDF)", "সব ৬০টি নোটিশ ডাউনলোড (ZIP)"),
                       bundle(), f"dispatch_{target:%Y-%m-%d}.zip", "application/zip", icon=":material/folder_zip:", type="primary")

"""Report: what is coming in the next weeks, ward by ward, in plain words.

The first thing a new officer sees: one sentence with the answer, the wards to act on first,
and a map of all 60 wards. Tapping a ward explains why it is at risk and what it will need."""
import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ui_text as tx
from dengue import config
from dengue.tiers import tier_of
from ui_common import (INK, TIER_COLORS, about, cached_forecast, card_head, case_range, get_engine, html, icon,
                       page_header, style_fig, tier_pill)
from ui_map import ward_map
from ui_reality import OUT_COLORS, facts, out_labels
from ui_reality import is_on as rc_on
from ui_shell import L, start_here

engine = get_engine()
ss = st.session_state
c = ss["controls"]
as_of, h = c["as_of"], c["horizon"]
target = as_of + pd.Timedelta(weeks=h)
fc = cached_forecast(str(as_of.date()), h, c["city"])
n = tx.num
HIGH = ("High", "Critical")
alert = fc[fc["tier"].isin(HIGH)]
counts = fc["tier"].value_counts()
ratios = engine.supply_ratios

start_here()

# ---- The answer, in one sentence --------------------------------------------------------
if len(alert):
    title = L(f"{len(alert)} of {len(fc)} wards may reach high dengue risk by {tx.day(target)}",
              f"{tx.day(target)} নাগাদ {n(len(fc))}টির মধ্যে {n(len(alert))}টি ওয়ার্ডে ডেঙ্গুর উচ্চ ঝুঁকি দেখা দিতে পারে")
else:
    title = L(f"No ward is expected to reach high dengue risk by {tx.day(target)}",
              f"{tx.day(target)} নাগাদ কোনো ওয়ার্ডে ডেঙ্গুর উচ্চ ঝুঁকির আশঙ্কা নেই")
page_header(L(f"Report · week of {tx.date(as_of)} · looking {h} weeks ahead",
              f"রিপোর্ট · {tx.date(as_of)} সপ্তাহ · {n(h)} সপ্তাহ সামনে"), title,
            L("Dengue follows rain by about 3 weeks. DengueWatch reads each ward's recent rain, humidity and temperature "
              "and warns before the cases arrive. <b>Tap any ward on the map</b> to see why.",
              "বৃষ্টির প্রায় ৩ সপ্তাহ পর ডেঙ্গু বাড়ে। DengueWatch প্রতিটি ওয়ার্ডের সাম্প্রতিক বৃষ্টি, আর্দ্রতা ও তাপমাত্রা দেখে "
              "রোগী বাড়ার আগেই সতর্ক করে। কারণ জানতে <b>মানচিত্রে যেকোনো ওয়ার্ডে চাপ দিন</b>।"))

# ---- Row 1: the big picture and the wards to act on first --------------------------------
left, right = st.columns([5, 7], gap="small")
with left:
    bar = "".join(f'<span style="width:{counts.get(t, 0) / len(fc) * 100:.2f}%;background:{TIER_COLORS[t]}"></span>'
                  for t in config.TIERS if counts.get(t, 0))
    key = "".join(f'<span><i style="background:{TIER_COLORS[t]}"></i><b>{n(int(counts.get(t, 0)))}</b>{tx.tier(t)}</span>'
                  for t in config.TIERS)
    now_high = int(fc["tier_now"].isin(HIGH).sum())
    label = L(f"IN {h} WEEKS · BY {tx.day(target).upper()}", f"{n(h)} সপ্তাহ পর · {tx.day(target)} নাগাদ")
    html(f'<div class="dk" style="min-height:398px"><div class="ch"><div><div class="mono" style="color:rgba(255,255,255,.55)">{label}</div></div>'
         f'<div class="ib">{icon("target", 16)}</div></div>'
         f'<div class="big">{n(len(alert))}<span class="of"> / {n(len(fc))}</span></div>'
         f'<div class="bigsub">{L("wards at high or critical risk", "ওয়ার্ডে উচ্চ বা অতি উচ্চ ঝুঁকি")}</div>'
         f'<div class="dw-tierbar">{bar}</div><div class="dw-tierkey">{key}</div>'
         f'<div class="bigsub" style="margin:22px 0 0;max-width:none">'
         f'{L(f"Today <b style=color:#fff>{n(now_high)}</b> wards are at high risk. About <b style=color:#fff>{n(fc.pred.sum())}</b> people may fall sick in the week of {tx.day(target)}.", f"এখন <b style=color:#fff>{n(now_high)}</b>টি ওয়ার্ড উচ্চ ঝুঁকিতে। {tx.day(target)} সপ্তাহে প্রায় <b style=color:#fff>{n(fc.pred.sum())}</b> জন অসুস্থ হতে পারেন।")}'
         f'</div></div>')

with right, st.container(key="glass_first"):
    esc = alert[alert["escalating"]]
    first = pd.concat([esc, alert[~alert["escalating"]]]).head(5) if len(alert) else fc.head(5)
    html(card_head(L("Act on these wards first", "আগে এই ওয়ার্ডগুলোতে ব্যবস্থা নিন") if len(alert) else L("Wards to watch", "নজরে রাখার ওয়ার্ড"),
                   L("Calm today, expected to get much worse", "এখন শান্ত, তবে দ্রুত খারাপ হওয়ার আশঙ্কা") if len(esc) else "", "bell"))
    rows = []
    for w in first.itertuples():
        pct = (w.breeding_rain_mm / max(w.breeding_rain_normal_mm, 1) - 1) * 100
        why = (L(f"rain {pct:+.0f}% vs normal", f"বৃষ্টি স্বাভাবিকের চেয়ে {n(f'{pct:+.0f}')}%") if w.main_driver.startswith("Rainfall")
               else tx.driver(w.main_driver))
        rows.append(f'<div class="dw-firstrow"><div><div class="nm">{tx.ward(w.ward_id)}</div>'
                    f'<div class="sub">{tx.city(w.city)} · {L("about", "প্রায়")} {about(w.pred)} {L("cases", "রোগী")} · {why}</div></div>'
                    f'<div>{tier_pill(w.tier_now)} <span style="color:#8B909C">→</span> {tier_pill(w.tier)}</div></div>')
    html("".join(rows))
    st.write("")
    st.page_link("views/actions.py", label=L("Plan actions for these wards", "এই ওয়ার্ডগুলোর জন্য পদক্ষেপ নিন"),
                 icon=":material/arrow_forward:", icon_position="right")

st.write("")

# ---- Row 2: map of all wards + the chosen ward explained ---------------------------------
default_ward = (alert if len(alert) else fc).iloc[0]["ward_id"]
if ss.get("pick_ward") not in set(fc["ward_id"]):
    ss["pick_ward"] = default_ward

map_col, detail_col = st.columns([7, 5], gap="small")
with map_col, st.container(key="glass_map"):
    html(card_head(L(f"Every ward in {h} weeks", f"{n(h)} সপ্তাহ পর প্রতিটি ওয়ার্ড"),
                   L("Each square is one ward, coloured by its risk. Tap a square to see why.",
                     "প্রতিটি ঘর একটি ওয়ার্ড, রং দেখায় ঝুঁকি। কারণ দেখতে ঘরে চাপ দিন।"), "grid"))
    byw = fc.set_index("ward_id")
    rc = facts(str(as_of.date()), h, c["city"]) if rc_on() else None
    if rc:  # Reality check on: colour by warning vs what really happened
        color = {w: OUT_COLORS[o][0] for w, o in rc["outcome"].items()}
        text_color = {w: OUT_COLORS[o][1] for w, o in rc["outcome"].items()}
        hover = {w: f"<b>{tx.ward(w)}</b><br>{L('Forecast', 'পূর্বাভাস')}: {tx.tier(r.tier)} (~{about(r.pred)})<br>"
                    f"{L('Really', 'বাস্তবে')}: {tx.tier(rc['real_tier'][w])} ({n(rc['actual'][w])})" for w, r in byw.iterrows()}
    else:
        color = {w: TIER_COLORS[t] for w, t in byw["tier"].items()}
        text_color = {w: INK if t == "Medium" else "white" for w, t in byw["tier"].items()}
        hover = {w: f"<b>{tx.ward(w)}</b> · {tx.city(r.city)}<br>{tx.tier(r.tier)} · {L('about', 'প্রায়')} {about(r.pred)} "
                    f"{L('cases', 'রোগী')}" for w, r in byw.iterrows()}
    tapped = ward_map(fc, color=color, text_color=text_color, hover=hover, key="ward_map", selected=ss["pick_ward"])
    if tapped:
        ss["pick_ward"] = tapped
        st.rerun()
    if rc:
        cnt = pd.Series(rc["outcome"]).value_counts()
        html('<div class="dw-legend" style="margin-bottom:14px">' + "".join(
            f'<span><i style="display:inline-block;width:10px;height:10px;border-radius:3px;background:{OUT_COLORS[k][0]};margin-right:6px"></i>'
            f'{lab} <b>{n(int(cnt.get(k, 0)))}</b></span>' for k, lab in out_labels().items()) + "</div>")
    else:
        html('<div class="dw-legend" style="margin-bottom:14px">' + "".join(f'<span>{tier_pill(t)} {L(m, b)}</span>' for t, m, b in (
            ("Low", "under 2 cases a week", "সপ্তাহে ২ জনের কম"), ("Medium", "2 to 5", "২ থেকে ৫ জন"),
            ("High", "5 to 10", "৫ থেকে ১০ জন"), ("Critical", "10 or more", "১০ জন বা বেশি"))) + "</div>")

with detail_col, st.container(key="glass_detail"):
    ids = fc.sort_values("ward_id")["ward_id"].tolist()
    # Options are the names in the current language, one widget per language, so switching language never trips the list
    wkey, names = f"pick_ward_{tx.lang()}", [tx.ward(w) for w in ids]
    back = dict(zip(names, ids))
    if ss.get(wkey) != tx.ward(ss["pick_ward"]):
        ss[wkey] = tx.ward(ss["pick_ward"])
    st.selectbox(L("Tap a square on the map, or pick a ward here", "মানচিত্রে ঘরে চাপ দিন, বা এখান থেকে ওয়ার্ড বাছুন"), names,
                 key=wkey, on_change=lambda: ss.__setitem__("pick_ward", back[ss[wkey]]))
    r = fc.set_index("ward_id").loc[ss["pick_ward"]]
    html(f'<div class="ch" style="margin:6px 0 4px"><div><h3 style="font-size:1.3rem !important">{tx.ward(ss["pick_ward"])}</h3>'
         f'<p>{tx.city(r.city)}</p></div></div>'
         f'<div class="dw-row" style="margin:4px 0 12px"><span class="dw-meta">{L("Now", "এখন")}</span> {tier_pill(r.tier_now)}'
         f'<span class="dw-sep">→</span><span class="dw-meta">{L(f"in {h} weeks", f"{n(h)} সপ্তাহ পর")}</span> {tier_pill(r.tier)}</div>'
         f'<div class="dw-big">{about(r.pred)}<small>{L("cases expected", "জন রোগীর আশঙ্কা")}</small></div>'
         f'<div class="dw-meta">{L("likely between", "সম্ভাব্য")} {case_range(r.lo, r.hi)} '
         f'{L("in the week of", "জন,")} {tx.date(target)}{"" if tx.lang() == "en" else " সপ্তাহে"}</div>')
    if rc:
        o = rc["outcome"][ss["pick_ward"]]
        html(f'<div class="dw-callout" style="margin-top:10px;padding:10px 14px"><span style="width:10px;height:10px;border-radius:3px;'
             f'background:{OUT_COLORS[o][0]};flex:none;margin-top:6px"></span><span>{L("Really happened", "বাস্তবে")}: '
             f'<b>{n(rc["actual"][ss["pick_ward"]])} {L("cases", "জন রোগী")}</b> ({tx.tier(rc["real_tier"][ss["pick_ward"]])}). {out_labels()[o]}.</span></div>')

    # Why: the biggest pushes up or down, in plain words
    pct = (r.breeding_rain_mm / max(r.breeding_rain_normal_mm, 1) - 1) * 100
    say = {
        "Rainfall (0-6 wks ago)": (
            L(f"<b>Rain was {pct:+.0f}% vs normal</b> over the last 3 weeks, so there is more standing water for mosquitoes to breed.",
              f"গত ৩ সপ্তাহে <b>বৃষ্টি স্বাভাবিকের চেয়ে {n(f'{pct:+.0f}')}%</b>, তাই মশা জন্মানোর মতো জমা পানি বেশি।"),
            L(f"<b>Less rain than usual</b> ({pct:+.0f}%), so less water for mosquitoes to breed in.",
              f"<b>স্বাভাবিকের চেয়ে কম বৃষ্টি</b> ({n(f'{pct:+.0f}')}%), তাই মশার প্রজননের পানি কম।")),
        "Humidity": (L("<b>Humid air</b> helps mosquitoes live longer and bite more.", "<b>আর্দ্র বাতাসে</b> মশা বেশি দিন বাঁচে, বেশি কামড়ায়।"),
                     L("<b>Drier air than usual</b> shortens mosquito life.", "<b>স্বাভাবিকের চেয়ে শুষ্ক বাতাসে</b> মশা কম দিন বাঁচে।")),
        "Temperature": (L("<b>Warm weather</b> speeds up mosquito breeding.", "<b>গরম আবহাওয়ায়</b> মশা দ্রুত জন্মায়।"),
                        L("<b>Cooler weather than usual</b> slows mosquito breeding.", "<b>স্বাভাবিকের চেয়ে ঠান্ডায়</b> মশা ধীরে জন্মায়।")),
        "Ward vulnerability": (L("<b>Water-logging, crowding and poor sanitation</b> make this ward more exposed.",
                                 "<b>জলাবদ্ধতা, ঘনবসতি ও দুর্বল স্যানিটেশনের</b> কারণে এই ওয়ার্ড বেশি ঝুঁকিতে।"),
                               L("<b>Good drainage and sanitation</b> protect this ward.", "<b>ভালো নিষ্কাশন ও স্যানিটেশন</b> এই ওয়ার্ডকে রক্ষা করে।")),
    }
    drivers = sorted(say, key=lambda g: -abs(float(r[g])))[:3]
    html(f'<div style="margin-top:16px"><div class="mono" style="margin-bottom:2px">{L("WHY", "কেন")}</div>' + "".join(
        f'<div class="dw-why"><span class="ar {"up" if r[g] > 0 else "down"}">{"↑" if r[g] > 0 else "↓"}</span>'
        f'<span>{say[g][0] if r[g] > 0 else say[g][1]}</span></div>' for g in drivers if abs(float(r[g])) > 0.05) + "</div>")

    # What it will need
    crews = config.CREWS_NEEDED.get(r.tier, 0)
    todo = [("mosquito", L(f"Send {n(crews)} spray crew{'s' if crews > 1 else ''}", f"{n(crews)}টি স্প্রে দল পাঠান")
             if crews else L("No spray crew needed yet: keep watching", "এখনই স্প্রে দল লাগবে না: নজর রাখুন")),
            ("drop", L(f"Keep {n(math.ceil(r.pred * ratios['saline_bags_needed']))} saline bags and "
                       f"{n(math.ceil(r.pred * ratios['diagnostic_kits_needed']))} test kits ready",
                       f"{n(math.ceil(r.pred * ratios['saline_bags_needed']))}টি স্যালাইন ও "
                       f"{n(math.ceil(r.pred * ratios['diagnostic_kits_needed']))}টি পরীক্ষার কিট প্রস্তুত রাখুন")),
            ("pulse", L(f"Expect about {n(math.ceil(r.pred * ratios['hospital_beds_required']))} hospital bed(s) in use",
                        f"প্রায় {n(math.ceil(r.pred * ratios['hospital_beds_required']))}টি হাসপাতাল শয্যা লাগতে পারে"))]
    html(f'<div style="margin-top:14px"><div class="mono" style="margin-bottom:8px">{L("WHAT IT WILL NEED", "যা লাগবে")}</div>'
         '<div class="dw-todo">' + "".join(f'<div><span class="ic">{icon(i, 16)}</span>{t}</div>' for i, t in todo) + "</div></div>")
    st.write("")

st.write("")

# ---- More detail, folded away -------------------------------------------------------------
with st.expander(L("How did this forecast do? (reality check)", "এই পূর্বাভাস কতটা মিলেছিল?"), icon=":material/verified:"):
    if fc["actual"].notna().all():
        real = pd.Series(tier_of(fc["actual"]), index=fc.index).isin(HIGH)
        hit = int((real & fc["tier"].isin(HIGH)).sum())
        st.markdown(L(f"This week is in the past, so we can check. **{hit} of {int(real.sum())}** wards that really reached high risk "
                      f"were flagged {h} weeks earlier. The model never saw 2024 or 2025 while learning.",
                      f"এই সপ্তাহ অতীতের, তাই মিলিয়ে দেখা যায়। বাস্তবে উচ্চ ঝুঁকিতে পৌঁছানো {n(int(real.sum()))}টি ওয়ার্ডের মধ্যে "
                      f"**{n(hit)}টি** {n(h)} সপ্তাহ আগেই চিহ্নিত হয়েছিল।"))
    else:
        st.markdown(L("This week is beyond the data, so it cannot be checked yet.", "এই সপ্তাহের প্রকৃত তথ্য এখনো নেই।"))
    st.page_link("views/accuracy.py", label=L("See full accuracy report", "পূর্ণ নির্ভুলতা রিপোর্ট"), icon=":material/arrow_forward:",
                 icon_position="right")

with st.expander(L("Cases over the last 3 months", "গত ৩ মাসের রোগী"), icon=":material/show_chart:"):
    raw = engine.raw if c["city"] is None else engine.raw[engine.raw["city"] == c["city"]]
    weekly = raw.groupby("date")["dengue_cases"].sum()
    past = weekly[(weekly.index <= as_of) & (weekly.index > as_of - pd.Timedelta(weeks=14))]
    fig = go.Figure()
    fig.add_scatter(x=past.index, y=past.values, mode="lines", line=dict(color=INK, width=2), name=L("Real cases", "শনাক্ত রোগী"),
                    fill="tozeroy", fillcolor="rgba(17,19,24,0.05)")
    fig.add_scatter(x=[as_of, target], y=[past.iloc[-1], fc["pred"].sum()], mode="lines+markers", name=L("Forecast", "পূর্বাভাস"),
                    line=dict(color=TIER_COLORS["High"], width=2, dash="dot"), marker=dict(size=[0, 10], color=TIER_COLORS["High"]))
    st.plotly_chart(style_fig(fig, height=260), width="stretch", config={"displayModeBar": False})

"""Reality check: replay a past week and compare DengueWatch's warning with what really happened,
then estimate what acting on the warning would have saved. Built so a judge (or a sceptical
officer) can check the system in one screen."""
import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ui_text as tx
from dengue import config, simulator
from dengue.tiers import tier_of
from ui_common import INK, about, cached_forecast, card_head, get_engine, html, icon, page_header, style_fig
from ui_map import ward_map
from ui_ops import cached_plan
from ui_shell import L

engine = get_engine()
ss = st.session_state
c = ss["controls"]
as_of, h, n = c["as_of"], c["horizon"], tx.num
target = as_of + pd.Timedelta(weeks=h)
fc = cached_forecast(str(as_of.date()), h, c["city"])
ratios = engine.supply_ratios
HIGH = ("High", "Critical")

if fc["actual"].isna().any():
    page_header(L("Reality check", "বাস্তবের সঙ্গে মিলিয়ে দেখা"), L("This week cannot be checked yet", "এই সপ্তাহ এখনো মেলানো যাবে না"),
                L(f"The real cases for {tx.date(target)} are not in the data. Pick an earlier report week (top right).",
                  f"{tx.date(target)} সপ্তাহের প্রকৃত তথ্য নেই। ওপরের ডান দিক থেকে আগের কোনো সপ্তাহ বাছুন।"))
    st.stop()

real_tier = pd.Series(tier_of(fc["actual"]), index=fc.index)
rh, fh = real_tier.isin(HIGH), fc["tier"].isin(HIGH)
caught, missed, false_alarm = int((rh & fh).sum()), int((rh & ~fh).sum()), int((fh & ~rh).sum())
inside = int(((fc["actual"] >= fc["lo"].clip(lower=0).apply(math.floor)) & (fc["actual"] <= fc["hi"].apply(math.ceil))).sum())
pred_total, real_total, hi_total = float(fc["pred"].sum()), float(fc["actual"].sum()), float(fc["hi"].sum())
real_rows = engine.raw[(engine.raw["date"] == target) & engine.raw["ward_id"].isin(fc["ward_id"])]
real_need = {k: float(real_rows[k].sum()) for k in ("saline_bags_needed", "diagnostic_kits_needed", "hospital_beds_required")}

page_header(L(f"Reality check · replay of {tx.date(as_of)}", f"বাস্তবের সঙ্গে মিলিয়ে দেখা · {tx.date(as_of)}"),
            L(f"DengueWatch warned about {caught} of the {int(rh.sum())} wards that really reached high risk",
              f"বাস্তবে উচ্চ ঝুঁকিতে পৌঁছানো {n(int(rh.sum()))}টি ওয়ার্ডের {n(caught)}টির আগাম সতর্কতা দিয়েছিল DengueWatch"),
            L(f"This week is in the past, so we can compare the warning made on {tx.date(as_of)} with what really happened "
              f"{h} weeks later. " + ("The model never saw 2024 or 2025 while learning, so this is a fair test."
                                      if c["unseen"] else "<b>Note:</b> this week was part of the training data (2016–2023). "
                                      "Pick a week in 2024 or 2025 for a fair test."),
              f"এই সপ্তাহ অতীতের, তাই {tx.date(as_of)} তারিখের সতর্কতা {n(h)} সপ্তাহ পরের বাস্তবের সঙ্গে মেলানো যায়। "
              + ("মডেল শেখার সময় ২০২৪ বা ২০২৫ দেখেনি, তাই এটি ন্যায্য পরীক্ষা।" if c["unseen"]
                 else "<b>লক্ষ্য করুন:</b> এই সপ্তাহ প্রশিক্ষণ তথ্যের অংশ। ন্যায্য পরীক্ষার জন্য ২০২৪ বা ২০২৫ বাছুন।")))

# ---- Three proofs ---------------------------------------------------------------------------------
a, b, d = st.columns(3, gap="small")
pct = caught / max(int(rh.sum()), 1)
C = 2 * math.pi * 44
ring = (f'<svg width="112" height="112" viewBox="0 0 112 112" role="img" aria-label="{pct:.0%}">'
        f'<circle cx="56" cy="56" r="44" fill="none" stroke="rgba(17,19,24,.08)" stroke-width="11"/>'
        f'<circle cx="56" cy="56" r="44" fill="none" stroke="#2E8B57" stroke-width="11" stroke-linecap="round" '
        f'stroke-dasharray="{pct * C:.1f} {C:.1f}" transform="rotate(-90 56 56)"/>'
        f'<text x="56" y="62" text-anchor="middle" font-size="22" font-weight="650" fill="{INK}" font-family="Geist, sans-serif">'
        f'{n(f"{pct:.0%}")}</text></svg>')
with a:
    html(f'<div class="gc">{card_head(L("Warned in time", "সময়মতো সতর্কতা"), L(f"{h} weeks before the cases", f"রোগী বাড়ার {n(h)} সপ্তাহ আগে"), "bell")}'
         f'<div class="ring">{ring}<p>{L(f"<b>{caught} of {int(rh.sum())}</b> high-risk wards were flagged early. {missed} missed, {false_alarm} false alarm(s).", f"<b>{n(int(rh.sum()))}টির মধ্যে {n(caught)}টি</b> উচ্চ ঝুঁকির ওয়ার্ড আগেই চিহ্নিত। {n(missed)}টি বাদ পড়েছে, {n(false_alarm)}টি ভুল সতর্কতা।")}</p></div></div>')
with b:
    html(f'<div class="gc">{card_head(L("Cases: forecast vs real", "রোগী: পূর্বাভাস বনাম বাস্তব"), L(f"Week of {tx.date(target)}", f"{tx.date(target)} সপ্তাহ"), "pulse")}'
         f'<div class="dw-row" style="gap:22px;margin:4px 0 12px"><div><div class="dw-meta">{L("Expected", "প্রত্যাশিত")}</div><div class="dw-big">{n(pred_total)}</div></div>'
         f'<div><div class="dw-meta">{L("Bad-week plan", "খারাপ সপ্তাহের হিসাব")}</div><div class="dw-big">{n(hi_total)}</div></div>'
         f'<div><div class="dw-meta">{L("Really happened", "বাস্তবে")}</div><div class="dw-big">{n(real_total)}</div></div></div>'
         f'<p style="font-size:.86rem;color:#4B5160;margin:0">{L(f"Real cases fell inside our likely range in <b>{inside} of {len(fc)}</b> wards.", f"<b>{n(len(fc))}টির মধ্যে {n(inside)}টি</b> ওয়ার্ডে প্রকৃত রোগী আমাদের সম্ভাব্য সীমার মধ্যে ছিল।")}</p></div>')
with d:
    plan_sal = pred_total * ratios["saline_bags_needed"]
    bad_sal = hi_total * ratios["saline_bags_needed"]
    html(f'<div class="gc">{card_head(L("Saline: planned vs really needed", "স্যালাইন: পরিকল্পনা বনাম প্রকৃত চাহিদা"), L("Real need comes from the dataset", "প্রকৃত চাহিদা ডেটাসেট থেকে"), "drop")}'
         f'<div class="dw-row" style="gap:22px;margin:4px 0 12px"><div><div class="dw-meta">{L("Expected plan", "প্রত্যাশিত হিসাব")}</div><div class="dw-big">{n(plan_sal)}</div></div>'
         f'<div><div class="dw-meta">{L("Bad-week plan", "খারাপ সপ্তাহের হিসাব")}</div><div class="dw-big">{n(bad_sal)}</div></div>'
         f'<div><div class="dw-meta">{L("Really needed", "প্রকৃত চাহিদা")}</div><div class="dw-big">{n(real_need["saline_bags_needed"])}</div></div></div>'
         f'<p style="font-size:.86rem;color:#4B5160;margin:0">{L("Planning for a bad week (Actions, top of the likely range) " + ("would have covered the real need." if bad_sal >= real_need["saline_bags_needed"] else "would still have fallen short."), "খারাপ সপ্তাহ ধরে পরিকল্পনা করলে " + ("প্রকৃত চাহিদা পূরণ হতো।" if bad_sal >= real_need["saline_bags_needed"] else "তবুও ঘাটতি থাকত।"))}</p></div>')

st.write("")

# ---- Map: right, missed, false alarm ------------------------------------------------------------
OUT = {"caught": ("#2E8B57", "white", L("Warned, and it happened", "সতর্ক করেছিল, ঘটেছেও")),
       "missed": ("#A61E4D", "white", L("Missed", "বাদ পড়েছে")),
       "false": ("#D9A82E", INK, L("False alarm", "ভুল সতর্কতা")),
       "calm": ("rgba(17,19,24,.13)", INK, L("Calm, and stayed calm", "শান্ত ছিল, শান্তই থেকেছে"))}
outcome = pd.Series("calm", index=fc.index)
outcome[rh & fh], outcome[rh & ~fh], outcome[fh & ~rh] = "caught", "missed", "false"
byw = fc.assign(outcome=outcome, real_tier=real_tier).set_index("ward_id")
left, right = st.columns([7, 5], gap="small")
with left, st.container(key="glass_rc_map"):
    html(card_head(L("Every ward: warning vs reality", "প্রতিটি ওয়ার্ড: সতর্কতা বনাম বাস্তব"),
                   L(f"Forecast made {tx.date(as_of)} for the week of {tx.date(target)}", f"{tx.date(as_of)} তারিখের পূর্বাভাস, {tx.date(target)} সপ্তাহের জন্য"), "check"))
    ward_map(fc, color={w: OUT[o][0] for w, o in byw["outcome"].items()},
             text_color={w: OUT[o][1] for w, o in byw["outcome"].items()},
             hover={w: f"<b>{tx.ward(w)}</b><br>{L('Forecast', 'পূর্বাভাস')}: {tx.tier(r.tier)} (~{about(r.pred)})<br>"
                       f"{L('Really', 'বাস্তবে')}: {tx.tier(r.real_tier)} ({n(r.actual)})" for w, r in byw.iterrows()},
             key="rc_map")
    counts = byw["outcome"].value_counts()
    html('<div class="dw-legend" style="margin-bottom:14px">' + "".join(
        f'<span><i style="display:inline-block;width:10px;height:10px;border-radius:3px;background:{col};margin-right:6px"></i>'
        f'{lab} <b>{n(int(counts.get(k, 0)))}</b></span>' for k, (col, _, lab) in OUT.items()) + "</div>")

# ---- What acting on the warning would have saved -------------------------------------------------
with right, st.container(key="glass_rc_saved"):
    crews = int(ss.get("v_act_crews", 20))
    plan = cached_plan(str(as_of.date()), h, c["city"], float(ss.get("v_act_stock", 60)), crews, float(ss.get("v_act_beds", 80)), False)
    need = int(plan.wards["crews_needed"].sum())

    def saved(k: int) -> dict:
        p = simulator.best_plan(plan.effects, k)
        s = simulator.simulate(plan.effects, p, ratios) if p else pd.DataFrame()
        cases = float(s["cases_prevented"].sum()) if len(s) else 0.0
        return {"cases": cases, "beds": cases * ratios["hospital_beds_required"], "saline": cases * ratios["saline_bags_needed"],
                "kits": cases * ratios["diagnostic_kits_needed"]}
    html(card_head(L(f"If crews had gone out on {tx.date(as_of)}", f"{tx.date(as_of)} তারিখে স্প্রে দল পাঠালে"),
                   L("Model estimate of cases prevented over the next 2 to 4 weeks", "আগামী ২-৪ সপ্তাহে কত রোগী কমত (মডেলের হিসাব)"), "mosquito"))
    for k, lab in ((crews, L(f"With your {crews} crews", f"আপনার {n(crews)}টি দলে")),
                   (max(need, crews), L(f"With {max(need, crews)} crews (every high-risk ward covered)",
                                        f"{n(max(need, crews))}টি দলে (সব উচ্চ ঝুঁকির ওয়ার্ড)"))):
        v = saved(k)
        beds, sal, kits = about(v["beds"]), about(v["saline"]), about(v["kits"])
        sub = L(f"about {beds} bed-weeks, {sal} saline bags and {kits} test kits saved",
                f"প্রায় {beds}টি শয্যা-সপ্তাহ, {sal}টি স্যালাইন ও {kits}টি কিট বাঁচত")
        html(f'<div class="dw-firstrow"><div><div class="nm">{lab}</div><div class="sub">{sub}</div></div>'
             f'<div class="dw-big" style="font-size:1.6rem;color:#1F7A4A">−{about(v["cases"])}<small>{L("cases", "রোগী")}</small></div></div>')
    st.caption(L("What did not happen cannot be observed, so this uses the same forecast model with the crews' share of breeding "
                 "water removed (see Actions, step 1). Real cases in the replay are untouched.",
                 "যা ঘটেনি তা দেখা যায় না, তাই একই মডেলে স্প্রে দলের নষ্ট করা পানি বাদ দিয়ে হিসাব করা হয়েছে।"))

st.write("")


# ---- The whole season: forecast vs real --------------------------------------------------------
@st.cache_data(show_spinner=False, max_entries=16)
def season(year: int, h: int, city: str | None) -> pd.DataFrame:
    g = get_engine().season_grid(year, h, city)
    return g.groupby("target_week")[["pred", "actual"]].sum().reset_index()


with st.container(key="glass_rc_season"):
    yr = target.year
    s = season(yr, h, c["city"])
    html(card_head(L(f"The {yr} season: real cases vs the forecast made {h} weeks earlier", f"{n(yr)} মৌসুম: প্রকৃত রোগী বনাম {n(h)} সপ্তাহ আগের পূর্বাভাস"),
                   L("Each point of the forecast line was made with only the weather known at the time.", "পূর্বাভাসের প্রতিটি বিন্দু শুধু তখনকার আবহাওয়া দিয়ে তৈরি।"), "trend"))
    fig = go.Figure()
    fig.add_scatter(x=s["target_week"], y=s["actual"], name=L("Real cases", "প্রকৃত রোগী"), mode="lines", line=dict(color=INK, width=2.2))
    fig.add_scatter(x=s["target_week"], y=s["pred"], name=L(f"Forecast ({h} weeks earlier)", f"পূর্বাভাস ({n(h)} সপ্তাহ আগে)"), mode="lines",
                    line=dict(color=config.TIER_COLORS["High"], width=2.2, dash="dot"))
    fig.add_vline(x=target, line=dict(color="rgba(17,19,24,.35)", width=1, dash="dash"))
    fig.add_annotation(x=target, y=float(s["actual"].max()), text=L("this replay", "এই সপ্তাহ"), showarrow=False, yshift=10,
                       font=dict(size=11, color=INK))
    tv, tt = tx.month_ticks(s["target_week"].min(), s["target_week"].max())
    fig.update_xaxes(tickvals=tv, ticktext=tt)
    st.plotly_chart(style_fig(fig, height=300), width="stretch", config={"displayModeBar": False})

"""Reality check: a small floating switch. When it is on, a compact card compares the forecast with what
really happened in that (past) week, and estimates what acting on the warning would have saved.
When it is off, nothing extra is shown."""
from __future__ import annotations

import math

import pandas as pd
import streamlit as st

import ui_text as tx
from dengue import simulator
from dengue.tiers import tier_of
from ui_common import INK, about, cached_forecast, get_engine, html
from ui_ops import cached_plan
from ui_shell import L

HIGH = ("High", "Critical")

CSS = """
<style>
.st-key-rc_float{position:fixed !important; right:22px; bottom:22px; z-index:999990; width:auto !important;
  background:#111318; border-radius:999px; padding:9px 18px 9px 14px; box-shadow:0 18px 40px -14px rgba(17,19,24,.6);}
.st-key-rc_float p{color:#fff !important; font-weight:600 !important; font-size:.92rem !important;}
.st-key-rc_panel{position:fixed !important; right:22px; bottom:82px; z-index:999989; width:min(390px, calc(100vw - 32px)) !important;
  max-height:72vh; overflow:auto; background:rgba(255,255,255,.95); backdrop-filter:blur(20px); -webkit-backdrop-filter:blur(20px);
  border:1px solid rgba(17,19,24,.08); border-radius:22px; box-shadow:0 30px 60px -24px rgba(17,19,24,.45); padding:16px 18px 10px;}
.rc-h{font-weight:650; font-size:1.02rem; color:#111318; letter-spacing:-0.01em;}
.rc-s{font-size:.78rem; color:#8B909C; margin:1px 0 8px;}
.rc-row{display:grid; grid-template-columns:repeat(3, 1fr); gap:6px; margin:6px 0 2px;}
.rc-row > div{background:rgba(17,19,24,.04); border-radius:12px; padding:7px 9px;}
.rc-row .k{font-size:.7rem; color:#8B909C; line-height:1.2;} .rc-row .v{font-size:1.15rem; font-weight:650; color:#111318; font-variant-numeric:tabular-nums;}
.rc-row > div.real{background:#111318;} .rc-row div.real .k{color:rgba(255,255,255,.6);} .rc-row div.real .v{color:#fff;}
.rc-l{font-size:.8rem; font-weight:600; color:#4B5160; margin-top:10px;}
.rc-n{font-size:.82rem; color:#4B5160; line-height:1.45; margin:6px 0 4px;}
.rc-n b{color:#111318;}
.rc-save{display:flex; align-items:center; justify-content:space-between; gap:10px; background:#E5F4E4; border-radius:14px; padding:9px 12px; margin-top:8px;}
.rc-save .v{font-size:1.35rem; font-weight:700; color:#1F7A4A; white-space:nowrap;} .rc-save .t{font-size:.8rem; color:#24563A; line-height:1.4;}
</style>
"""

OUT_COLORS = {"caught": ("#2E8B57", "white"), "missed": ("#A61E4D", "white"), "false": ("#D9A82E", INK),
              "calm": ("rgba(17,19,24,.13)", INK)}


def out_labels() -> dict:
    return {"caught": L("Warned, and it happened", "সতর্ক করেছিল, ঘটেছেও"), "missed": L("Missed", "বাদ পড়েছে"),
            "false": L("False alarm", "ভুল সতর্কতা"), "calm": L("Calm, and stayed calm", "শান্ত ছিল, শান্তই থেকেছে")}


def is_on() -> bool:
    return bool(st.session_state.get("v_rc_on", False))


def toggle() -> None:
    """The floating switch (bottom right). Drawn on every page by the app shell."""
    ss = st.session_state
    ss.setdefault("v_rc_on", False)
    ss["rc_on"] = ss["v_rc_on"]
    st.html(CSS)
    c = ss.get("controls")
    f = facts(str(c["as_of"].date()), c["horizon"], c["city"]) if c else None
    with st.container(key="rc_float", width="content", horizontal=True, vertical_alignment="center", gap="small"):
        if f:  # the headline accuracy, always visible on the button: share of real high-risk wards warned in time
            pct = f["caught"] / max(f["real_high"], 1)
            C = 2 * math.pi * 13
            html(f'<div title="{L("Warned in time", "সময়মতো সতর্কতা")}" style="display:flex;align-items:center">'
                 f'<svg width="34" height="34" viewBox="0 0 34 34" aria-label="{pct:.0%}"><circle cx="17" cy="17" r="13" fill="none" '
                 f'stroke="rgba(255,255,255,.18)" stroke-width="4"/><circle cx="17" cy="17" r="13" fill="none" stroke="#4ADE80" '
                 f'stroke-width="4" stroke-linecap="round" stroke-dasharray="{pct * C:.1f} {C:.1f}" transform="rotate(-90 17 17)"/>'
                 f'<text x="17" y="21" text-anchor="middle" font-size="9.5" font-weight="700" fill="#fff" font-family="Geist, sans-serif">'
                 f'{tx.num(f"{pct:.0%}")}</text></svg></div>')
        st.toggle(L("Reality check", "বাস্তবের সঙ্গে মেলান"), key="rc_on", on_change=lambda: ss.__setitem__("v_rc_on", ss["rc_on"]),
                  help=L("Compare this week's warning with what really happened (past weeks only).",
                         "এই সপ্তাহের সতর্কতা বাস্তবের সঙ্গে মিলিয়ে দেখুন (শুধু অতীতের সপ্তাহ)।"))


@st.cache_data(show_spinner=False, max_entries=64)
def facts(as_of: str, h: int, city: str | None) -> dict | None:
    """Warning vs reality for one replay week. None if the target week is beyond the data."""
    engine = get_engine()
    fc = cached_forecast(as_of, h, city)
    if fc["actual"].isna().any():
        return None
    real = pd.Series(tier_of(fc["actual"]), index=fc.index)
    rh, fh = real.isin(HIGH), fc["tier"].isin(HIGH)
    outcome = pd.Series("calm", index=fc.index)
    outcome[rh & fh], outcome[rh & ~fh], outcome[fh & ~rh] = "caught", "missed", "false"
    lo = fc["lo"].clip(lower=0).apply(math.floor)
    inside = int(((fc["actual"] >= lo) & (fc["actual"] <= fc["hi"].apply(math.ceil))).sum())
    target = pd.Timestamp(as_of) + pd.Timedelta(weeks=h)
    rows = engine.raw[(engine.raw["date"] == target) & engine.raw["ward_id"].isin(fc["ward_id"])]
    r = engine.supply_ratios
    return {
        "n": len(fc), "real_high": int(rh.sum()), "caught": int((rh & fh).sum()), "missed": int((rh & ~fh).sum()),
        "false": int((fh & ~rh).sum()), "inside": inside,
        "pred": float(fc["pred"].sum()), "hi": float(fc["hi"].sum()), "real": float(fc["actual"].sum()),
        "saline_plan": float(fc["pred"].sum() * r["saline_bags_needed"]), "saline_bad": float(fc["hi"].sum() * r["saline_bags_needed"]),
        "saline_real": float(rows["saline_bags_needed"].sum()),
        "outcome": dict(zip(fc["ward_id"], outcome)), "real_tier": dict(zip(fc["ward_id"], real)),
        "actual": dict(zip(fc["ward_id"], fc["actual"])),
    }


def savings(as_of: str, h: int, city: str | None, crews: int) -> dict:
    """Model estimate of what `crews` sent that week would have prevented over weeks 2-4."""
    ss = st.session_state
    plan = cached_plan(as_of, h, city, float(ss.get("v_act_stock", 60)), int(ss.get("v_act_crews", 20)),
                       float(ss.get("v_act_beds", 80)), False)
    r = get_engine().supply_ratios
    p = simulator.best_plan(plan.effects, crews)
    s = simulator.simulate(plan.effects, p, r) if p else pd.DataFrame()
    cases = float(s["cases_prevented"].sum()) if len(s) else 0.0
    return {"cases": cases, "beds": cases * r["hospital_beds_required"], "saline": cases * r["saline_bags_needed"],
            "kits": cases * r["diagnostic_kits_needed"], "need": int(plan.wards["crews_needed"].sum())}


def panel() -> None:
    """The floating comparison card, shown only while the switch is on."""
    if not is_on():
        return
    c = st.session_state["controls"]
    as_of, h, n = c["as_of"], c["horizon"], tx.num
    target = as_of + pd.Timedelta(weeks=h)
    f = facts(str(as_of.date()), h, c["city"])
    with st.container(key="rc_panel"):
        html(f'<div class="rc-h">{L("Reality check", "বাস্তবের সঙ্গে মিলিয়ে দেখা")}</div>'
             f'<div class="rc-s">{L(f"Warning made {tx.date(as_of)} · real cases {tx.date(target)}", f"{tx.date(as_of)} তারিখের সতর্কতা · {tx.date(target)} সপ্তাহের প্রকৃত রোগী")}</div>')
        if f is None:
            html(f'<p class="rc-n">{L("This week is beyond the data (it ends 29 Dec 2025), so it cannot be checked. Pick an earlier week at the top.", "এই সপ্তাহের প্রকৃত তথ্য নেই। ওপর থেকে আগের কোনো সপ্তাহ বাছুন।")}</p>')
            return
        if not c["unseen"]:
            html(f'<p class="rc-n"><b>{L("Note:", "লক্ষ্য করুন:")}</b> {L("this week was in the training data. Pick 2024 or 2025 for a fair test.", "এই সপ্তাহ প্রশিক্ষণ তথ্যে ছিল। ন্যায্য পরীক্ষার জন্য ২০২৪ বা ২০২৫ বাছুন।")}</p>')
        pct = f["caught"] / max(f["real_high"], 1)
        caught, real_high, missed, false = f["caught"], f["real_high"], f["missed"], f["false"]
        C = 2 * math.pi * 30
        ring = (f'<svg width="76" height="76" viewBox="0 0 76 76" role="img" aria-label="{pct:.0%}">'
                f'<circle cx="38" cy="38" r="30" fill="none" stroke="rgba(17,19,24,.08)" stroke-width="8"/>'
                f'<circle cx="38" cy="38" r="30" fill="none" stroke="#2E8B57" stroke-width="8" stroke-linecap="round" '
                f'stroke-dasharray="{pct * C:.1f} {C:.1f}" transform="rotate(-90 38 38)"/>'
                f'<text x="38" y="43" text-anchor="middle" font-size="16" font-weight="700" fill="#111318" '
                f'font-family="Geist, sans-serif">{n(f"{pct:.0%}")}</text></svg>')
        html(f'<div style="display:flex;gap:12px;align-items:center;margin:2px 0 4px">{ring}<div class="rc-n" style="margin:0">'
             + L(f"<b>Accuracy: {caught} of {real_high}</b> wards that really reached high risk were warned {h} weeks early. "
                 f"{missed} missed, {false} false alarm(s).",
                 f"<b>নির্ভুলতা: {n(real_high)}টির মধ্যে {n(caught)}টি</b> উচ্চ ঝুঁকির ওয়ার্ডে {n(h)} সপ্তাহ আগেই সতর্কতা। "
                 f"{n(missed)}টি বাদ, {n(false)}টি ভুল সতর্কতা।") + '</div></div>')
        html(f'<div class="rc-l">{L("Cases that week", "সে সপ্তাহের রোগী")}</div><div class="rc-row">'
             f'<div><div class="k">{L("Expected", "প্রত্যাশিত")}</div><div class="v">{n(f["pred"])}</div></div>'
             f'<div><div class="k">{L("Bad-week plan", "খারাপ সপ্তাহ")}</div><div class="v">{n(f["hi"])}</div></div>'
             f'<div class="real"><div class="k">{L("Really", "বাস্তবে")}</div><div class="v">{n(f["real"])}</div></div></div>'
             f'<div class="rc-l">{L("Saline bags", "স্যালাইন ব্যাগ")}</div><div class="rc-row">'
             f'<div><div class="k">{L("Expected plan", "প্রত্যাশিত")}</div><div class="v">{n(f["saline_plan"])}</div></div>'
             f'<div><div class="k">{L("Bad-week plan", "খারাপ সপ্তাহ")}</div><div class="v">{n(f["saline_bad"])}</div></div>'
             f'<div class="real"><div class="k">{L("Really needed", "প্রকৃত চাহিদা")}</div><div class="v">{n(f["saline_real"])}</div></div></div>')
        inside, nw = f["inside"], f["n"]
        html(f'<p class="rc-n">{L(f"Real cases fell inside our likely range in <b>{inside} of {nw}</b> wards.", f"<b>{n(nw)}টির মধ্যে {n(inside)}টি</b> ওয়ার্ডে প্রকৃত রোগী সম্ভাব্য সীমার মধ্যে ছিল।")}</p>')
        crews = int(st.session_state.get("v_act_crews", 20))
        s = savings(str(as_of.date()), h, c["city"], crews)
        cases, beds, sal = about(s["cases"]), about(s["beds"]), about(s["saline"])
        html(f'<div class="rc-save"><div class="t">{L(f"If your {crews} crews had gone out on {tx.date(as_of)}: about {beds} bed-weeks and {sal} saline bags saved (model estimate).", f"{tx.date(as_of)} তারিখে আপনার {n(crews)}টি দল পাঠালে: প্রায় {beds}টি শয্যা-সপ্তাহ ও {sal}টি স্যালাইন বাঁচত (মডেলের হিসাব)।")}</div>'
             f'<div class="v">−{cases}</div></div>')
        st.page_link("views/reality.py", label=L("Open the full comparison", "পূর্ণ তুলনা দেখুন"), icon=":material/arrow_forward:",
                     icon_position="right")

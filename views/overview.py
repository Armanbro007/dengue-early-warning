"""Overview: one clear answer for a first-time visitor, then where and why."""
import pandas as pd
import streamlit as st

from dengue.config import TIERS
from dengue.tiers import tier_of
from ui_common import (TIER_COLORS, about, cached_forecast, case_range, driver_name, fmt_day, fmt_week,
                       html, icon, page_header, section, tier_legend, tier_pill, ward_name)

c = st.session_state["controls"]
as_of, h = c["as_of"], c["horizon"]
target = as_of + pd.Timedelta(weeks=h)
fc = cached_forecast(str(as_of.date()), h, c["city"])
area = "the five city corporations" if c["city"] is None else c["city"]

HIGH = ("High", "Critical")
n = len(fc)
alert = fc["tier"].isin(HIGH)
now_alert = fc["tier_now"].isin(HIGH)
n_alert, n_now = int(alert.sum()), int(now_alert.sum())

# ---- The answer ---------------------------------------------------------------
if n_alert:
    title = f"{n_alert} of {n} wards are likely to reach high dengue risk by {fmt_day(target)}"
else:
    title = f"No ward is expected to reach high dengue risk by {fmt_day(target)}"
lead = (f"Rain over the last few weeks shows where mosquitoes are breeding. From it, DengueWatch expects about "
        f"<b>{fc['pred'].sum():,.0f} dengue cases</b> across {area} in the week of {fmt_week(target)}.")
if n_alert > n_now:
    lead += (" Today <b>no ward</b> is at high risk yet" if n_now == 0 else
             f" Today only <b>{n_now} of {n}</b> wards are at high risk")
    lead += ", so there is still time to act before hospitals fill up."
page_header(f"Forecast made on {fmt_week(as_of)} · {h} weeks ahead", title, lead)

if fc["actual"].notna().all():
    real = pd.Series(tier_of(fc["actual"]), index=fc.index).isin(HIGH)
    hit = int((real & alert).sum())
    html(
        f'<div class="dw-callout">{icon("check", 20)}<div><b>What really happened:</b> {int(real.sum())} of {n} wards '
        f"reached high or critical risk that week. DengueWatch had flagged {hit} of them {h} weeks earlier, "
        f"using only the data available on {fmt_week(as_of)}.</div></div>"
    )

# ---- How it works ---------------------------------------------------------------
section("How DengueWatch sees it coming",
        "Dengue follows the rain with a delay of about three weeks. That delay is the warning window.")
steps = [
    ("rain", "Week 0", "It rains", "Water collects in drains, tyres, pots and rooftops.", ""),
    ("clock", "Weeks 1–2", "Mosquitoes breed", "Eggs in that water become biting Aedes mosquitoes in 7 to 14 days.", ""),
    ("pulse", "Weeks 2–4", "People fall sick", "Bites spread the virus. Fever, tests and hospital visits follow.", ""),
    ("bell", "Week 0", "DengueWatch warns", "It reads this week's rain and names the wards at risk, while there is still time.", " hl"),
]
html('<div class="dw-steps">' + "".join(
    f'<div class="dw-step{cls}"><div class="ic">{icon(ic)}</div><div class="when">{when}</div>'
    f'<div class="what">{what}</div><p>{text}</p></div>' for ic, when, what, text, cls in steps) + "</div>")

# ---- Where --------------------------------------------------------------------------
all_fc = cached_forecast(str(as_of.date()), h, None)
section("Where the risk is", f"Expected risk level of each ward in the week of {fmt_week(target)}, by city corporation.")
cards = []
for city, d in all_fc.groupby("city", sort=False):
    counts = d["tier"].value_counts()
    k = int(d["tier"].isin(HIGH).sum())
    bar = "".join(
        f'<span style="width:{counts.get(t, 0) / len(d) * 100:.2f}%;background:{TIER_COLORS[t]}" '
        f'title="{t}: {counts.get(t, 0)} wards"></span>' for t in TIERS if counts.get(t, 0))
    top = d.sort_values("pred", ascending=False).iloc[0]
    dim = "" if c["city"] in (None, city) else ' style="opacity:.55"'
    cards.append(
        f'<div class="dw-card"{dim}><h4>{city}</h4><div class="dw-meta">{len(d)} wards</div>'
        f'<div class="dw-big" style="margin-top:14px">{k}<span class="of"> / {len(d)}</span></div>'
        f'<div class="dw-meta">wards high or critical</div>'
        f'<div class="dw-stack">{bar}</div>'
        f'<div class="dw-reason">Most at risk: <b>{ward_name(top.ward_id)}</b>, about {about(top.pred)} cases</div></div>')
html('<div class="dw-grid five">' + "".join(cards) + "</div>" + tier_legend())

# ---- Which wards first ------------------------------------------------------------
esc = fc[fc["escalating"]]
rest = fc[alert & ~fc["escalating"]]
pick = pd.concat([esc, rest]).head(6) if n_alert else fc.head(6)
if n_alert and len(esc):
    section("Act on these wards first",
            "These wards look calm today but are expected to get much worse. "
            "Acting now, before cases rise, costs the least.")
elif n_alert:
    section("Act on these wards first", "The wards with the highest expected case counts.")
else:
    section("Wards to keep an eye on", "No ward is expected to reach high risk. These have the highest forecasts.")

cards = []
for r in pick.itertuples():
    pct = (r.breeding_rain_mm / max(r.breeding_rain_normal_mm, 1) - 1) * 100
    reason = driver_name(r.main_driver).lower()
    cards.append(
        f'<div class="dw-card"><div class="dw-meta">{r.city}</div><h4>{ward_name(r.ward_id)}</h4>'
        f'<div class="dw-change"><div><div class="k">Today</div>{tier_pill(r.tier_now)}</div>'
        f'<div class="ar">{icon("arrow", 16)}</div><div><div class="k">In {h} weeks</div>{tier_pill(r.tier)}</div></div>'
        f'<div class="dw-big">{about(r.pred)} <small>cases expected</small></div>'
        f'<div class="dw-meta">Likely between {case_range(r.lo, r.hi).replace("–", " and ")}</div>'
        f'<div class="dw-reason">Main reason: <b>{reason}</b>. {r.breeding_rain_mm:.0f} mm of rain in the last '
        f"3 weeks ({pct:+.0f}% compared with normal).</div></div>")
html('<div class="dw-grid wide">' + "".join(cards) + "</div>")

# ---- Next steps --------------------------------------------------------------------
section("Go deeper")
a, b, d = st.columns(3)
a.page_link("views/risk_board.py", label="Every ward, ranked, with an action plan", icon=":material/format_list_numbered:")
b.page_link("views/ward_detail.py", label="Why one ward is at risk", icon=":material/help:")
d.page_link("views/accuracy.py", label="How accurate it has been", icon=":material/verified:")

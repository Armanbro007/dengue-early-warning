"""Module 4: ward dispatch notices from the plan, by plain templates (no AI, no network).

Three formats per ward, all from the same numbers in plan.wards:
  * SMS       one message of at most 160 plain characters (plus a Bangla SMS for field staff)
  * WhatsApp  a short structured message with *bold* labels
  * Brief     a printable HTML page for the ward commissioner (and a PDF of all briefs)

Every notice lists: forecast cases and tier, supplies allocated vs required,
deficit alert, bed overflow transfers, and spraying crews assigned.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

import pandas as pd

from . import config
from .i18n import TIER_BN, bn_date, bn_digits, bn_ward

SMS_LIMIT = 160


def ward_label(ward_id: str) -> str:
    return str(ward_id).replace("_", " ")


def short_ward(ward_id: str) -> str:
    """'DSCC_Ward_04' -> 'DSCC W04' (saves SMS characters)."""
    return str(ward_id).replace("_Ward_", " W")


def _status(r) -> str:
    if r["deficit"] == "CRITICAL" or r["net_bed_deficit"] > 0:
        return "CRITICAL DEFICIT"
    if r["deficit"] == "Short":
        return "SHORTAGE"
    return "OK"


def _beds_line(r, short: bool = False) -> str:
    need, have = int(r["need_hospital_beds_required"]), int(r["beds_available"])
    out = f"Beds {need} need/{have} free"
    if r["sent_out"]:
        out += f", {int(r['sent_out'])} to {short_ward(r['sent_to'].split(', ')[0]) if short else ward_label(r['sent_to'])}"
    if r["net_bed_deficit"]:
        out += f", {int(r['net_bed_deficit'])} NO BED"
    return out


def sms(r, week) -> str:
    """One plain-text SMS (GSM characters only, <= 160)."""
    d = pd.Timestamp(week)
    parts = [
        f"DengueWatch {short_ward(r['ward_id'])} wk {d:%d%b}: ~{r['plan_cases']:.0f} cases ({r['tier']}).",
        f"Saline {int(r['alloc_saline_bags_needed'])}/{int(r['need_saline_bags_needed'])}"
        f" Kits {int(r['alloc_diagnostic_kits_needed'])}/{int(r['need_diagnostic_kits_needed'])}.",
        _beds_line(r, short=True) + ".",
        f"Crews {int(r['crews_assigned'])}/{int(r['crews_needed'])}.",
        _status(r),
    ]
    text = " ".join(parts)
    if len(text) > SMS_LIMIT:  # drop the least important detail first, never the numbers
        text = " ".join(parts[:2] + [parts[3], parts[4]])
    return text[:SMS_LIMIT]


def sms_bangla(r, week) -> str:
    """Bangla SMS for field staff (Unicode SMS, so it may take 2-3 parts)."""
    n = lambda v: bn_digits(int(round(v)))  # noqa: E731
    status = {"CRITICAL DEFICIT": "জরুরি ঘাটতি", "SHORTAGE": "ঘাটতি", "OK": "পর্যাপ্ত"}[_status(r)]
    return (f"ডেঙ্গুওয়াচ: {bn_ward(r['ward_id'])}, {bn_date(week)} সপ্তাহ। সম্ভাব্য রোগী {n(r['plan_cases'])} ({TIER_BN[r['tier']]} ঝুঁকি)। "
            f"স্যালাইন {n(r['alloc_saline_bags_needed'])}/{n(r['need_saline_bags_needed'])}, "
            f"কিট {n(r['alloc_diagnostic_kits_needed'])}/{n(r['need_diagnostic_kits_needed'])}, "
            f"শয্যা দরকার {n(r['need_hospital_beds_required'])}, খালি {n(r['beds_available'])}"
            + (f", {n(r['sent_out'])} জন অন্য ওয়ার্ডে" if r["sent_out"] else "")
            + f"। স্প্রে দল {n(r['crews_assigned'])}/{n(r['crews_needed'])}। অবস্থা: {status}।")


def whatsapp(r, week) -> str:
    d = pd.Timestamp(week)
    lines = [
        f"*DengueWatch dispatch | {ward_label(r['ward_id'])}, {r['city']}*",
        f"Week of {d:%d %b %Y} | Status: *{_status(r)}*",
        "",
        f"*Forecast:* ~{r['plan_cases']:.0f} cases ({r['tier']} risk), range {r['lo']:.0f}-{r['hi']:.0f}",
        f"*Priority:* #{int(r['priority'])} of the region",
        "",
        "*Supplies (allocated / required)*",
        f"- Saline bags: {int(r['alloc_saline_bags_needed'])} / {int(r['need_saline_bags_needed'])}",
        f"- Test kits: {int(r['alloc_diagnostic_kits_needed'])} / {int(r['need_diagnostic_kits_needed'])}",
        f"- Hospital beds: {int(r['need_hospital_beds_required'])} needed / {int(r['beds_available'])} free",
    ]
    if r["sent_out"]:
        lines.append(f"- Overflow: send {int(r['sent_out'])} patient(s) to {ward_label(r['sent_to'])}")
    if r["received"]:
        lines.append(f"- Receive {int(r['received'])} patient(s) from nearby wards")
    if r["net_bed_deficit"]:
        lines.append(f"- *NO BED for {int(r['net_bed_deficit'])} patient(s): city is full, request surge beds*")
    lines += ["", f"*Spraying crews:* {int(r['crews_assigned'])} assigned / {int(r['crews_needed'])} requested"]
    if r["cases_prevented"] > 0:
        lines.append(f"Expected effect: about {r['cases_prevented']:.0f} fewer cases over the next 2-4 weeks")
    if r["deficit"] != "Fully supplied":
        lines.append(f"*Deficit alert:* only {r['fill_pct']:.0f}% of supplies covered")
    return "\n".join(lines)


_CSS = """
body{font-family:Arial,Helvetica,sans-serif;color:#111;margin:24px;max-width:780px}
h1{font-size:20px;margin:0}h2{font-size:15px;margin:18px 0 6px}
.meta{color:#555;font-size:12px;margin:4px 0 12px}
.badge{display:inline-block;padding:3px 10px;border-radius:12px;font-weight:bold;font-size:12px}
.CRITICAL{background:#fde2e4;color:#a61e4d}.SHORTAGE{background:#fff1d6;color:#8a5a00}.OK{background:#e3f4e8;color:#1e6b3a}
table{border-collapse:collapse;width:100%;font-size:13px}td,th{border:1px solid #ccc;padding:6px 8px;text-align:left}
th{background:#f3f4f6}.num{text-align:right}.foot{color:#666;font-size:11px;margin-top:16px}
.page{page-break-after:always}@media print{body{margin:10mm}.page{page-break-after:always}}
"""


def _brief_body(r, week) -> str:
    e = html.escape
    status = _status(r)
    rows = [
        ("Saline bags", r["need_saline_bags_needed"], r["alloc_saline_bags_needed"]),
        ("Diagnostic kits", r["need_diagnostic_kits_needed"], r["alloc_diagnostic_kits_needed"]),
        ("Hospital beds (local, free)", r["need_hospital_beds_required"], min(r["beds_available"], r["need_hospital_beds_required"])),
        ("Spraying crews", r["crews_needed"], r["crews_assigned"]),
    ]
    table = "".join(f"<tr><td>{e(a)}</td><td class=num>{int(b)}</td><td class=num>{int(c)}</td>"
                    f"<td class=num>{int(b) - int(c) if int(b) > int(c) else 0}</td></tr>" for a, b, c in rows)
    actions = []
    if r["sent_out"]:
        actions.append(f"Transfer {int(r['sent_out'])} patient(s) to {e(ward_label(r['sent_to']))} (same city).")
    if r["received"]:
        actions.append(f"Prepare to receive {int(r['received'])} patient(s) from neighbouring wards.")
    if r["net_bed_deficit"]:
        actions.append(f"<b>{int(r['net_bed_deficit'])} patient(s) have no bed in {e(r['city'])}</b>: open surge beds or request help.")
    if r["crews_assigned"]:
        actions.append(f"Deploy {int(r['crews_assigned'])} larvicide/fogging crew(s) this week: about "
                       f"{r['cases_prevented']:.0f} fewer cases expected over weeks 2-4.")
    if r["deficit"] != "Fully supplied":
        actions.append(f"Supplies cover only {r['fill_pct']:.0f}% of need: ration saline for severe cases, request top-up.")
    if not actions:
        actions.append("No shortage. Keep routine surveillance and source reduction.")
    return (f'<h1>Dengue dispatch brief: {e(ward_label(r["ward_id"]))}, {e(r["city"])}</h1>'
            f'<div class=meta>For the week of {pd.Timestamp(week):%d %B %Y} | priority #{int(r["priority"])} | '
            f'<span class="badge {status.split()[0]}">{status}</span></div>'
            f'<h2>Forecast</h2><p>About <b>{r["plan_cases"]:.0f}</b> dengue cases expected ({e(r["tier"])} risk; '
            f'80% range {r["lo"]:.0f} to {r["hi"]:.0f}).</p>'
            f'<h2>Supplies and crews</h2><table><tr><th>Item</th><th class=num>Required</th>'
            f'<th class=num>Allocated</th><th class=num>Deficit</th></tr>{table}</table>'
            f'<h2>Actions</h2><ul>' + "".join(f"<li>{a}</li>" for a in actions) + "</ul>")


def brief_html(wards: pd.DataFrame, week, title: str = "Commissioner dispatch briefs") -> str:
    """One printable HTML file; each ward on its own printed page."""
    pages = "".join(f'<div class=page>{_brief_body(r, week)}</div>' for _, r in wards.iterrows())
    foot = ("<div class=foot>Generated offline by DengueWatch from the local forecast model and templates. "
            "Supply ratios learned from 2016-2023 data; bed capacity and crew effect are stated planning assumptions.</div>")
    return (f"<!doctype html><html><head><meta charset=utf-8><title>{html.escape(title)}</title>"
            f"<style>{_CSS}</style></head><body>{pages}{foot}</body></html>")


def brief_pdf(wards: pd.DataFrame, week) -> bytes | None:
    """PDF of the briefs (English). Returns None if the optional fpdf2 package is missing."""
    try:
        from fpdf import FPDF
    except ImportError:
        return None
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(True, 15)
    for _, r in wards.iterrows():
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 15)
        pdf.cell(0, 9, f"Dengue dispatch brief: {ward_label(r['ward_id'])}, {r['city']}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, f"Week of {pd.Timestamp(week):%d %B %Y} | priority #{int(r['priority'])} | status: {_status(r)}",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6, f"Forecast: about {r['plan_cases']:.0f} cases ({r['tier']} risk), "
                             f"80% range {r['lo']:.0f}-{r['hi']:.0f}.")
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 10)
        for head, wdt in (("Item", 80), ("Required", 35), ("Allocated", 35), ("Deficit", 35)):
            pdf.cell(wdt, 7, head, border=1)
        pdf.ln()
        pdf.set_font("Helvetica", "", 10)
        for name, need, got in (("Saline bags", r["need_saline_bags_needed"], r["alloc_saline_bags_needed"]),
                                ("Diagnostic kits", r["need_diagnostic_kits_needed"], r["alloc_diagnostic_kits_needed"]),
                                ("Hospital beds (local)", r["need_hospital_beds_required"],
                                 min(r["beds_available"], r["need_hospital_beds_required"])),
                                ("Spraying crews", r["crews_needed"], r["crews_assigned"])):
            for val, wdt in ((name, 80), (int(need), 35), (int(got), 35), (max(int(need) - int(got), 0), 35)):
                pdf.cell(wdt, 7, str(val), border=1)
            pdf.ln()
        pdf.ln(3)
        pdf.multi_cell(0, 6, whatsapp(r, week).replace("*", "").split("\n\n", 1)[-1])
    return bytes(pdf.output())


def city_digest(plan, week) -> str:
    """One WhatsApp-style summary for the city health officer group."""
    lines = [f"*DengueWatch city digest, week of {pd.Timestamp(week):%d %b %Y}*"]
    for _, c in plan.cities.iterrows():
        lines.append(f"- {c['city']}: beds {int(c['beds_needed'])}/{int(c['beds_available'])} "
                     f"({c['utilisation_pct']:.0f}%), {int(c['transfers'])} transfers, "
                     f"{int(c['headroom_left'])} beds left" + (f", *{int(c['net_deficit'])} without bed*" if c["net_deficit"] else ""))
    s = plan.supply_summary
    lines.append(f"Saline {s['saline_bags_needed']['allocated']}/{s['saline_bags_needed']['need']}, "
                 f"kits {s['diagnostic_kits_needed']['allocated']}/{s['diagnostic_kits_needed']['need']}, "
                 f"crews {sum(plan.crew_plan.values())} sent. {len(plan.alerts)} wards need attention.")
    return "\n".join(lines)


def notices(plan, week) -> pd.DataFrame:
    """All notices for all wards in one table (what the page shows and the export writes)."""
    w = plan.wards
    return pd.DataFrame({"priority": w["priority"], "ward_id": w["ward_id"], "city": w["city"],
                         "status": w.apply(_status, axis=1),
                         "sms": w.apply(lambda r: sms(r, week), axis=1),
                         "sms_bangla": w.apply(lambda r: sms_bangla(r, week), axis=1),
                         "whatsapp": w.apply(lambda r: whatsapp(r, week), axis=1)})


def write_exports(plan, week, out_dir: Path | None = None, brief_wards: int = 5) -> list[Path]:
    """Write sample notices to /exports. Briefs: the top `brief_wards` priority wards."""
    out = Path(out_dir or config.EXPORTS_DIR)
    out.mkdir(parents=True, exist_ok=True)
    n = notices(plan, week)
    top = plan.wards.head(brief_wards)
    files = {
        "sms_messages.csv": n[["priority", "ward_id", "city", "status", "sms"]].to_csv(index=False),
        "sms_bangla.txt": "\n\n".join(f"[{w}]\n{t}" for w, t in zip(n["ward_id"], n["sms_bangla"])),
        "whatsapp_messages.txt": "\n\n-----\n\n".join(n["whatsapp"]),
        "city_digest_whatsapp.txt": city_digest(plan, week),
        "commissioner_briefs.html": brief_html(top, week),
        "dispatch_plan.csv": plan.wards.drop(columns=["lo", "hi"]).round(2).to_csv(index=False),
        "bed_transfers.csv": plan.transfers.to_csv(index=False),
    }
    paths = []
    for name, text in files.items():
        p = out / name
        p.write_text(text, encoding="utf-8")
        paths.append(p)
    pdf = brief_pdf(top, week)
    if pdf:
        (out / "commissioner_briefs.pdf").write_bytes(pdf)
        paths.append(out / "commissioner_briefs.pdf")
    meta = {"week": str(pd.Timestamp(week).date()), "settings": vars(plan.settings),
            "files": [p.name for p in paths], "network_used": False}
    (out / "manifest.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return paths + [out / "manifest.json"]

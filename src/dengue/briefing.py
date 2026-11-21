"""Officer briefing: a short action plan for the wards that need attention.

Default: a deterministic template (free, instant, works offline).
Optional: if GEMINI_API_KEY is set, an LLM rewrites the same facts as a
plain-language briefing. Token and cost controls:
  * the LLM only sees a compact JSON of at most 5 wards (~250 input tokens),
  * output is capped (LLM_MAX_OUTPUT_TOKENS), temperature is low,
  * responses are cached on disk by a hash of the facts, so the same week is
    never paid for twice,
  * a daily call budget, plus retries/backoff/circuit breaker from http.py,
  * any failure falls back to the template, so the UI never breaks.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date

import pandas as pd

from . import config
from .http import NetworkUnavailable, request_json

CACHE = config.CACHE_DIR / "briefings"
USAGE_FILE = config.CACHE_DIR / "llm_usage.json"
MAX_WARDS = 5

# All fixed wording of the template, in English and Bangla. Numbers and ward
# names come from the model; only these phrases are translated.
TEXT = {
    "en": {
        "header": "**{area}, forecast for week of {week}:** {Critical} Critical, {High} High, {Medium} Medium, {Low} Low wards.",
        "quiet": "No ward is forecast above Medium. Keep routine surveillance and drain clearing.",
        "more": " and {n} more",
        "tier_line": "- **{tier}:** {names}. **Action:** {action}.",
        "tiers": {"Critical": "Critical", "High": "High"},
        "actions": {
            "Critical": "deploy larvicide + fogging teams this week, alert nearby hospitals to stock saline and NS1 kits",
            "High": "schedule source-reduction drives (drains, containers) and community warnings",
        },
        "early": "- **Early warning:** {n} wards are Low/Medium today but forecast High or Critical. "
                 "Acting there now is cheaper than responding after admissions rise.",
        "why": "- **Why:** {ward} had {mm} mm of rain in the last 3 weeks ({pct:+.0f}% vs normal for this "
               "time of year); main driver: {driver}.",
        "drivers": {},
    },
    "bn": {
        "header": "**{area}, {week} সপ্তাহের পূর্বাভাস:** {Critical}টি ওয়ার্ড সংকটজনক, {High}টি উচ্চ, "
                  "{Medium}টি মাঝারি এবং {Low}টি নিম্ন ঝুঁকিতে।",
        "quiet": "কোনো ওয়ার্ডে মাঝারির বেশি ঝুঁকির পূর্বাভাস নেই। নিয়মিত নজরদারি ও ড্রেন পরিষ্কার চালিয়ে যান।",
        "more": " এবং আরও {n}টি",
        "tier_line": "- **{tier}:** {names}। **করণীয়:** {action}।",
        "tiers": {"Critical": "সংকটজনক", "High": "উচ্চ ঝুঁকি"},
        "actions": {
            "Critical": "এই সপ্তাহেই লার্ভিসাইড ও ফগিং টিম পাঠান, কাছের হাসপাতালগুলোকে স্যালাইন ও NS1 কিট মজুত রাখতে বলুন",
            "High": "ড্রেন ও পানি জমে থাকা পাত্র পরিষ্কারের অভিযান চালান এবং এলাকাবাসীকে সতর্ক করুন",
        },
        "early": "- **আগাম সতর্কতা:** {n}টি ওয়ার্ডে এখন ঝুঁকি নিম্ন বা মাঝারি, কিন্তু পূর্বাভাস উচ্চ বা সংকটজনক। "
                 "হাসপাতালে ভর্তি বাড়ার আগেই সেখানে ব্যবস্থা নেওয়া কম খরচের।",
        "why": "- **কারণ:** {ward}-এ গত ৩ সপ্তাহে {mm} মিমি বৃষ্টি হয়েছে (এই সময়ের স্বাভাবিকের তুলনায় "
               "{pct:+.0f}%); প্রধান কারণ: {driver}।",
        "drivers": {
            "Rainfall (0-6 wks ago)": "বৃষ্টিপাত",
            "Humidity": "আর্দ্রতা",
            "Temperature": "তাপমাত্রা",
            "Ward vulnerability": "ওয়ার্ডের জলাবদ্ধতা, ঘনবসতি ও স্যানিটেশন",
            "Seasonal norm": "মৌসুমি স্বাভাবিক মাত্রা",
        },
    },
}
LANGUAGES = {"en": "English", "bn": "বাংলা (Bangla)"}


def build_facts(fc: pd.DataFrame, as_of, h: int, city: str | None) -> dict:
    """Compact, model-derived facts. This is the ONLY thing the LLM ever sees."""
    top = fc[fc["tier"].isin(["Critical", "High"])].head(MAX_WARDS)
    return {
        "area": city or "All cities",
        "issued_week": str(pd.Timestamp(as_of).date()),
        "target_week": str((pd.Timestamp(as_of) + pd.Timedelta(weeks=h)).date()),
        "counts": {t: int((fc["tier"] == t).sum()) for t in config.TIERS},
        "escalating": int(fc["escalating"].sum()),
        "wards": [
            {
                "ward": r.ward_id,
                "tier": r.tier,
                "cases": round(float(r.pred), 1),
                "range": [round(float(r.lo), 1), round(float(r.hi), 1)],
                "driver": r.main_driver,
                "breeding_rain_mm": round(float(r.breeding_rain_mm)),
                "normal_mm": round(float(r.breeding_rain_normal_mm)),
            }
            for r in top.itertuples()
        ],
    }


def template_briefing(facts: dict, lang: str = "en") -> str:
    t = TEXT[lang]
    c = facts["counts"]
    lines = [t["header"].format(area=facts["area"], week=facts["target_week"], **c)]
    if not facts["wards"]:
        lines.append(t["quiet"])
        return "\n\n".join(lines)
    for tier in ("Critical", "High"):
        wards = [w for w in facts["wards"] if w["tier"] == tier]
        if not wards:
            continue
        names = ", ".join(f"{w['ward']} (~{w['cases']:.0f})" for w in wards)
        if c[tier] > len(wards):
            names += t["more"].format(n=c[tier] - len(wards))
        lines.append(t["tier_line"].format(tier=t["tiers"][tier], names=names, action=t["actions"][tier]))
    if facts.get("escalating"):
        lines.append(t["early"].format(n=facts["escalating"]))
    top = facts["wards"][0]
    if top["normal_mm"] > 0:
        pct = (top["breeding_rain_mm"] / top["normal_mm"] - 1) * 100
        driver = t["drivers"].get(top["driver"], top["driver"].lower())
        lines.append(t["why"].format(ward=top["ward"], mm=top["breeding_rain_mm"], pct=pct, driver=driver))
    return "\n".join(lines)


# ---- optional LLM ---------------------------------------------------------
def _usage_today() -> dict:
    try:
        u = json.loads(USAGE_FILE.read_text())
    except (OSError, ValueError):
        u = {}
    if u.get("date") != str(date.today()):
        u = {"date": str(date.today()), "calls": 0, "input_tokens": 0, "output_tokens": 0}
    return u


def _save_usage(u: dict) -> None:
    USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    USAGE_FILE.write_text(json.dumps(u))


def llm_status() -> dict:
    u = _usage_today()
    return {"enabled": bool(config.GEMINI_API_KEY), "model": config.GEMINI_MODEL,
            "budget": config.LLM_DAILY_CALL_BUDGET, **u}


PROMPT = (
    "You are a public-health assistant for a Bangladeshi city corporation. Using ONLY the JSON "
    "facts below (model forecasts of weekly dengue cases per ward), write a briefing for the "
    "health officer: one summary sentence, then one bullet per ward with a concrete action "
    "(larvicide/fogging, drain clearing, hospital stock alerts). Max 120 words. No new numbers.\n\n"
)
BANGLA = "Write the briefing in Bangla (Bengali script); keep ward IDs and numbers as given.\n\n"


def get_briefing(facts: dict, use_llm: bool = True, lang: str = "en") -> tuple[str, str]:
    """Return (markdown, source) where source is 'template', 'cache' or 'llm'."""
    if not (use_llm and config.GEMINI_API_KEY):
        return template_briefing(facts, lang), "template"

    payload = json.dumps(facts, sort_keys=True, separators=(",", ":"))
    key = hashlib.sha256((config.GEMINI_MODEL + lang + payload).encode()).hexdigest()[:16]
    cached = CACHE / f"{key}.md"
    if cached.exists():
        return cached.read_text(encoding="utf-8"), "cache"

    usage = _usage_today()
    if usage["calls"] >= config.LLM_DAILY_CALL_BUDGET:
        return template_briefing(facts, lang), "template (daily LLM budget reached)"

    body = {
        "contents": [{"parts": [{"text": PROMPT + (BANGLA if lang == "bn" else "") + payload}]}],
        "generationConfig": {"maxOutputTokens": config.LLM_MAX_OUTPUT_TOKENS, "temperature": 0.2},
    }
    if config.GEMINI_MODEL.startswith("gemini-2.5"):
        body["generationConfig"]["thinkingConfig"] = {"thinkingBudget": 0}  # no hidden reasoning tokens
    try:
        resp = request_json(
            "gemini", "POST",
            f"https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_MODEL}:generateContent",
            headers={"x-goog-api-key": config.GEMINI_API_KEY, "Content-Type": "application/json"},
            json=body, max_retries=3,
        )
        text = resp["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (NetworkUnavailable, KeyError, IndexError, TypeError) as exc:
        return template_briefing(facts, lang), f"template (LLM unavailable: {str(exc)[:60]})"

    meta = resp.get("usageMetadata", {})
    usage["calls"] += 1
    usage["input_tokens"] += int(meta.get("promptTokenCount", 0))
    usage["output_tokens"] += int(meta.get("candidatesTokenCount", 0))
    _save_usage(usage)
    CACHE.mkdir(parents=True, exist_ok=True)
    cached.write_text(text, encoding="utf-8")
    return text, "llm"

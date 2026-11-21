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

ACTIONS = {
    "Critical": "deploy larvicide + fogging teams this week, alert nearby hospitals to stock saline and NS1 kits",
    "High": "schedule source-reduction drives (drains, containers) and community warnings",
}


def build_facts(fc: pd.DataFrame, as_of, h: int, city: str | None) -> dict:
    """Compact, model-derived facts. This is the ONLY thing the LLM ever sees."""
    top = fc[fc["tier"].isin(["Critical", "High"]) | fc["critical_watch"]].head(MAX_WARDS)
    return {
        "area": city or "All cities",
        "issued_week": str(pd.Timestamp(as_of).date()),
        "target_week": str((pd.Timestamp(as_of) + pd.Timedelta(weeks=h)).date()),
        "counts": {t: int((fc["tier"] == t).sum()) for t in config.TIERS},
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


def template_briefing(facts: dict) -> str:
    c = facts["counts"]
    lines = [
        f"**{facts['area']}, forecast for week of {facts['target_week']}:** "
        f"{c['Critical']} Critical, {c['High']} High, {c['Medium']} Medium, {c['Low']} Low wards."
    ]
    if not facts["wards"]:
        lines.append("No ward is forecast above Medium. Keep routine surveillance and drain clearing.")
        return "\n\n".join(lines)
    for tier in ("Critical", "High"):
        wards = [w for w in facts["wards"] if w["tier"] == tier]
        if not wards:
            continue
        names = ", ".join(f"{w['ward']} (~{w['cases']:.0f})" for w in wards)
        lines.append(f"- **{tier}:** {names}. **Action:** {ACTIONS[tier]}.")
    watch = [w for w in facts["wards"] if w["tier"] not in ("Critical", "High")]
    if watch:
        lines.append("- **Watch:** " + ", ".join(w["ward"] for w in watch) + " (upper forecast range reaches Critical).")
    top = facts["wards"][0]
    if top["normal_mm"] > 0:
        pct = (top["breeding_rain_mm"] / top["normal_mm"] - 1) * 100
        lines.append(
            f"- **Why:** {top['ward']} had {top['breeding_rain_mm']} mm of rain 1-3 weeks ago "
            f"({pct:+.0f}% vs normal for this time of year); main driver: {top['driver'].lower()}."
        )
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


def get_briefing(facts: dict, use_llm: bool = True) -> tuple[str, str]:
    """Return (markdown, source) where source is 'template', 'cache' or 'llm'."""
    if not (use_llm and config.GEMINI_API_KEY):
        return template_briefing(facts), "template"

    payload = json.dumps(facts, sort_keys=True, separators=(",", ":"))
    key = hashlib.sha256((config.GEMINI_MODEL + payload).encode()).hexdigest()[:16]
    cached = CACHE / f"{key}.md"
    if cached.exists():
        return cached.read_text(encoding="utf-8"), "cache"

    usage = _usage_today()
    if usage["calls"] >= config.LLM_DAILY_CALL_BUDGET:
        return template_briefing(facts), "template (daily LLM budget reached)"

    body = {
        "contents": [{"parts": [{"text": PROMPT + payload}]}],
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
        return template_briefing(facts), f"template (LLM unavailable: {str(exc)[:60]})"

    meta = resp.get("usageMetadata", {})
    usage["calls"] += 1
    usage["input_tokens"] += int(meta.get("promptTokenCount", 0))
    usage["output_tokens"] += int(meta.get("candidatesTokenCount", 0))
    _save_usage(usage)
    CACHE.mkdir(parents=True, exist_ok=True)
    cached.write_text(text, encoding="utf-8")
    return text, "llm"

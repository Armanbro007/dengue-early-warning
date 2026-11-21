"""Network failure handling: retries, Retry-After, circuit breaker and fallbacks.

No real network is used: a fake session plays back scripted responses.
"""
import json
import time

import pandas as pd
import pytest
import requests

from dengue import briefing, config, weather_api
from dengue.http import NetworkUnavailable, request_json


class FakeResp:
    def __init__(self, status=200, body=None, headers=None):
        self.status_code = status
        self._body = body if body is not None else {"ok": True}
        self.headers = {"Content-Type": "application/json", **(headers or {})}

    def json(self):
        return self._body


class FakeSession:
    """Returns (or raises) the scripted items in order and counts calls."""

    def __init__(self, script):
        self.script, self.calls = list(script), 0

    def request(self, method, url, **kwargs):
        self.calls += 1
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def test_rate_limit_is_retried_and_retry_after_is_honoured():
    sleeps = []
    s = FakeSession([FakeResp(429, headers={"Retry-After": "2"}), FakeResp(200, {"v": 1})])
    out = request_json("svc-ratelimit", "GET", "http://x", session=s, sleep=sleeps.append)
    assert out == {"v": 1}
    assert s.calls == 2 and sleeps == [2.0]


def test_backoff_grows_exponentially_then_gives_up():
    sleeps = []
    s = FakeSession([requests.ConnectionError()] * 4)
    with pytest.raises(NetworkUnavailable):
        request_json("svc-down", "GET", "http://x", session=s, sleep=sleeps.append, max_retries=4)
    assert s.calls == 4
    assert sleeps[0] < sleeps[1] < sleeps[2]  # 0.5s, 1s, 2s (+ small jitter)


def test_client_errors_are_not_retried():
    s = FakeSession([FakeResp(404)])
    with pytest.raises(NetworkUnavailable):
        request_json("svc-404", "GET", "http://x", session=s, sleep=lambda _: None)
    assert s.calls == 1


def test_circuit_breaker_stops_calling_a_failing_service():
    s = FakeSession([requests.Timeout()] * 10)
    for _ in range(config.CIRCUIT_BREAKER_FAILS):
        with pytest.raises(NetworkUnavailable):
            request_json("svc-flaky", "GET", "http://x", session=s, sleep=lambda _: None, max_retries=1)
    calls_before = s.calls
    with pytest.raises(NetworkUnavailable, match="circuit open"):
        request_json("svc-flaky", "GET", "http://x", session=s, sleep=lambda _: None, max_retries=1)
    assert s.calls == calls_before  # no request was made while the circuit is open


# ---- weather fallbacks ------------------------------------------------------
def _payload(days=63):
    dates = pd.date_range(pd.Timestamp.today().normalize() - pd.Timedelta(days=days - 16), periods=days)
    daily = {"time": [d.strftime("%Y-%m-%d") for d in dates],
             **{k: [10.0] * days for k in weather_api.DAILY_VARS}}
    return [{"daily": daily} for _ in config.CITY_COORDS]


@pytest.fixture
def raw():
    from dengue.data import load_raw
    return load_raw(allow_download=False)


@pytest.fixture
def offline(monkeypatch, tmp_path):
    monkeypatch.setattr(weather_api, "CACHE_FILE", tmp_path / "weather.json")

    def fail():
        raise NetworkUnavailable("simulated outage")
    monkeypatch.setattr(weather_api, "_request", fail)
    return tmp_path / "weather.json"


def test_no_network_and_no_cache_uses_climatology(raw, offline):
    res = weather_api.get_weekly_weather(raw)
    assert res.source == "climatology"
    assert set(res.weekly["city"]) == set(config.CITY_COORDS)


def test_no_network_uses_stale_cache(raw, offline):
    offline.write_text(json.dumps({"fetched_at": time.time() - 48 * 3600, "payload": _payload()}))
    res = weather_api.get_weekly_weather(raw)
    assert res.source == "stale-cache" and len(res.weekly) > 0


def test_fresh_cache_makes_zero_api_calls(raw, offline, monkeypatch):
    offline.write_text(json.dumps({"fetched_at": time.time(), "payload": _payload()}))
    monkeypatch.setattr(weather_api, "_request", lambda: pytest.fail("API must not be called"))
    res = weather_api.get_weekly_weather(raw)
    assert res.source == "cache" and res.api_calls == 0


def test_live_weather_produces_a_forecast_for_every_ward(raw, offline, monkeypatch):
    from dengue.engine import Engine
    monkeypatch.setattr(weather_api, "_request", _payload)
    res = weather_api.get_weekly_weather(raw)
    assert res.source == "live" and res.api_calls == 1
    fc = Engine.load().forecast_from_city_weather(res.weekly, 3)
    assert len(fc) == raw["ward_id"].nunique()


# ---- LLM briefing fallbacks --------------------------------------------------
FACTS = {"area": "Dhaka South", "issued_week": "2025-06-02", "target_week": "2025-06-23",
         "counts": {"Low": 0, "Medium": 1, "High": 1, "Critical": 0}, "escalating": 1,
         "wards": [{"ward": "W1", "tier": "High", "cases": 7.0, "range": [4.0, 11.0],
                    "driver": "Rainfall", "breeding_rain_mm": 200, "normal_mm": 120}]}


@pytest.fixture
def llm_sandbox(monkeypatch, tmp_path):
    monkeypatch.setattr(briefing, "CACHE", tmp_path / "briefings")
    monkeypatch.setattr(briefing, "USAGE_FILE", tmp_path / "usage.json")
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")


def test_briefing_without_key_uses_template(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    text, source = briefing.get_briefing(FACTS)
    assert source == "template" and "W1" in text


def test_bangla_template_keeps_wards_and_numbers(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    text, _ = briefing.get_briefing(FACTS, lang="bn")
    assert "W1" in text and "আগাম সতর্কতা" in text and "200" in text


def test_briefing_falls_back_when_llm_fails(llm_sandbox, monkeypatch):
    def fail(*a, **k):
        raise NetworkUnavailable("simulated 503")
    monkeypatch.setattr(briefing, "request_json", fail)
    text, source = briefing.get_briefing(FACTS)
    assert source.startswith("template") and "W1" in text


def test_briefing_is_cached_so_the_same_week_costs_tokens_once(llm_sandbox, monkeypatch):
    calls = []

    def fake_llm(*a, **k):
        calls.append(1)
        return {"candidates": [{"content": {"parts": [{"text": "Act in W1."}]}}],
                "usageMetadata": {"promptTokenCount": 250, "candidatesTokenCount": 40}}
    monkeypatch.setattr(briefing, "request_json", fake_llm)
    assert briefing.get_briefing(FACTS) == ("Act in W1.", "llm")
    assert briefing.get_briefing(FACTS) == ("Act in W1.", "cache")
    assert len(calls) == 1
    assert briefing.llm_status()["input_tokens"] == 250


def test_daily_llm_budget_is_enforced(llm_sandbox, monkeypatch):
    monkeypatch.setattr(config, "LLM_DAILY_CALL_BUDGET", 0)
    monkeypatch.setattr(briefing, "request_json", lambda *a, **k: pytest.fail("over budget: must not call"))
    _, source = briefing.get_briefing(FACTS)
    assert "budget" in source

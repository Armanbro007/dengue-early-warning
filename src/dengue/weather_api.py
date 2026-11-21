"""Live weather for forecast mode, with aggressive API-call minimisation.

* ONE HTTP request covers all 5 cities (Open-Meteo accepts comma-separated
  coordinates) and returns ~8 weeks of past weather + 16 days of forecast.
  Wards share their city's weather; ward differences come from ward attributes.
* The response is cached on disk for WEATHER_CACHE_TTL_H hours.
* Open-Meteo is free and needs no API key, so there is no secret to leak.

Fallback chain if the network fails: fresh cache -> stale cache -> climatology
(each city's historical median weather for those weeks of the year). The app
always gets usable weather plus a status saying which source was used.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass

import pandas as pd

from . import config
from .http import NetworkUnavailable, request_json

URL = "https://api.open-meteo.com/v1/forecast"
DAILY_VARS = {
    "temperature_2m_mean": "avg_temp_c",
    "temperature_2m_max": "max_temp_c",
    "temperature_2m_min": "min_temp_c",
    "precipitation_sum": "rainfall_mm",
    "relative_humidity_2m_mean": "relative_humidity_pct",
}
CACHE_FILE = config.CACHE_DIR / "weather_openmeteo.json"
PAST_DAYS = 63  # 9 weeks: enough for the 6-week lags plus a partial week


@dataclass
class WeatherResult:
    weekly: pd.DataFrame
    source: str          # live | cache | stale-cache | climatology
    fetched_at: float | None
    message: str
    api_calls: int = 0


def _request() -> list[dict]:
    cities = list(config.CITY_COORDS)
    params = {
        "latitude": ",".join(str(config.CITY_COORDS[c][0]) for c in cities),
        "longitude": ",".join(str(config.CITY_COORDS[c][1]) for c in cities),
        "daily": ",".join(DAILY_VARS),
        "past_days": PAST_DAYS,
        "forecast_days": 16,
        "timezone": "Asia/Dhaka",
    }
    data = request_json("open-meteo", "GET", URL, params=params)
    return data if isinstance(data, list) else [data]


def parse_daily(payload: list[dict]) -> pd.DataFrame:
    frames = []
    for city, loc in zip(config.CITY_COORDS, payload):
        d = pd.DataFrame(loc["daily"]).rename(columns={"time": "day", **DAILY_VARS})
        d["city"] = city
        frames.append(d)
    daily = pd.concat(frames, ignore_index=True)
    daily["day"] = pd.to_datetime(daily["day"])
    return daily


def to_weekly(daily: pd.DataFrame) -> pd.DataFrame:
    """Aggregate to Monday-start weeks, matching the training data."""
    daily = daily.copy()
    daily["date"] = daily["day"] - pd.to_timedelta(daily["day"].dt.weekday, unit="D")
    agg = daily.groupby(["city", "date"]).agg(
        avg_temp_c=("avg_temp_c", "mean"), max_temp_c=("max_temp_c", "mean"),
        min_temp_c=("min_temp_c", "mean"), rainfall_mm=("rainfall_mm", "sum"),
        relative_humidity_pct=("relative_humidity_pct", "mean"), days=("day", "count"),
    ).reset_index()
    return agg[agg["days"] >= 4].drop(columns="days")  # drop tiny partial weeks


def climatology(raw: pd.DataFrame, weeks: int = 9) -> pd.DataFrame:
    """Typical weather for the coming weeks of the year, per city (offline fallback)."""
    today = pd.Timestamp.today().normalize()
    monday = today - pd.Timedelta(days=today.weekday())
    dates = [monday - pd.Timedelta(weeks=k) for k in range(weeks - 1, -1, -1)]
    r = raw.assign(woy=raw["date"].dt.isocalendar().week.astype(int).clip(upper=52))
    med = r.groupby(["city", "woy"])[list(DAILY_VARS.values())].median().reset_index()
    rows = []
    for d in dates:
        woy = min(int(d.isocalendar().week), 52)
        part = med[med["woy"] == woy].drop(columns="woy").assign(date=d)
        rows.append(part)
    return pd.concat(rows, ignore_index=True)


def get_weekly_weather(raw: pd.DataFrame, force_refresh: bool = False) -> WeatherResult:
    cached = None
    if CACHE_FILE.exists():
        try:
            cached = json.loads(CACHE_FILE.read_text())
        except ValueError:
            cached = None

    age_h = (time.time() - cached["fetched_at"]) / 3600 if cached else None
    if cached and not force_refresh and age_h < config.WEATHER_CACHE_TTL_H:
        return WeatherResult(to_weekly(parse_daily(cached["payload"])), "cache", cached["fetched_at"],
                             f"Cached forecast, {age_h:.1f} h old (refreshes every {config.WEATHER_CACHE_TTL_H} h). 0 API calls.")
    try:
        payload = _request()
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        now = time.time()
        CACHE_FILE.write_text(json.dumps({"fetched_at": now, "payload": payload}))
        return WeatherResult(to_weekly(parse_daily(payload)), "live", now,
                             "Live Open-Meteo forecast: 1 API call for all 5 cities.", api_calls=1)
    except (NetworkUnavailable, KeyError, ValueError, TypeError) as exc:
        if cached:
            return WeatherResult(to_weekly(parse_daily(cached["payload"])), "stale-cache", cached["fetched_at"],
                                 f"Weather API unavailable ({exc}). Using last saved forecast from {age_h:.0f} h ago.")
        return WeatherResult(climatology(raw), "climatology", None,
                             f"Weather API unavailable ({exc}) and no saved forecast. Using typical weather for this time of year.")

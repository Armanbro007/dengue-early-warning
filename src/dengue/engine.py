"""Prediction engine: the one object the dashboard (and a future API) talks to.

It owns the data, features and loaded models, and answers questions like
"forecast every ward in Dhaka South 3 weeks after 7 July 2025" in milliseconds.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import config
from .data import STATIC_COLS, TARGET, file_hash, load_raw
from .explain import DRIVER_GROUPS, apply_rain_whatif, explain
from .features import FEATURES, add_targets, build_features
from .model import load_or_train, predict
from .tiers import add_tiers


@dataclass
class Engine:
    raw: pd.DataFrame
    feat: pd.DataFrame
    bundle: dict
    load_seconds: float = 0.0

    @classmethod
    def load(cls) -> "Engine":
        t0 = time.perf_counter()
        raw = load_raw()
        feat = add_targets(build_features(raw))
        bundle = load_or_train(feat, file_hash())
        return cls(raw, feat, bundle, time.perf_counter() - t0)

    # ---- lookups --------------------------------------------------------
    @property
    def wards(self) -> pd.DataFrame:
        return self.raw.drop_duplicates("ward_id")[["ward_id", "city", *STATIC_COLS]].reset_index(drop=True)

    @property
    def cities(self) -> list[str]:
        return sorted(self.raw["city"].unique())

    def forecast_weeks(self) -> list[pd.Timestamp]:
        """As-of weeks that have the full 6-week lag history."""
        ok = self.feat.dropna(subset=FEATURES)
        return sorted(ok["date"].unique())

    @property
    def train_end(self) -> pd.Timestamp:
        return pd.Timestamp(self.bundle["train_end"])

    def _rows(self, as_of, city: str | None = None, ward: str | None = None) -> pd.DataFrame:
        f = self.feat[self.feat["date"] == pd.Timestamp(as_of)]
        if city:
            f = f[f["city"] == city]
        if ward:
            f = f[f["ward_id"] == ward]
        return f.dropna(subset=FEATURES)

    # ---- forecasting ----------------------------------------------------
    def forecast_rows(self, rows: pd.DataFrame, h: int, extra_rain_mm: float = 0.0) -> pd.DataFrame:
        X = apply_rain_whatif(rows, extra_rain_mm) if extra_rain_mm else rows
        p = predict(self.bundle, X, h)
        e = explain(self.bundle, X, h)
        out = rows[["date", "city", "ward_id", *STATIC_COLS]].join(p).join(e.drop(columns="prediction"))
        out["target_week"] = out["date"] + pd.Timedelta(weeks=h)
        tcol = f"target_h{h}"
        out["actual"] = rows[tcol] if tcol in rows else np.nan
        return add_tiers(out).sort_values("pred", ascending=False).reset_index(drop=True)

    def forecast(self, as_of, h: int, city: str | None = None, extra_rain_mm: float = 0.0) -> pd.DataFrame:
        return self.forecast_rows(self._rows(as_of, city), h, extra_rain_mm)

    def ward_history(self, ward: str, h: int, start, end) -> pd.DataFrame:
        """Model forecasts made h weeks earlier vs what actually happened, per target week."""
        f = self.feat[(self.feat["ward_id"] == ward)].dropna(subset=FEATURES)
        f = f[(f["date"] + pd.Timedelta(weeks=h) >= pd.Timestamp(start)) & (f["date"] + pd.Timedelta(weeks=h) <= pd.Timestamp(end))]
        p = predict(self.bundle, f, h)
        out = pd.DataFrame({"target_week": f["date"] + pd.Timedelta(weeks=h), "issued": f["date"]}).join(p)
        actual = self.raw[self.raw["ward_id"] == ward].set_index("date")[TARGET]
        out["actual"] = out["target_week"].map(actual)
        return out.reset_index(drop=True)

    def season_grid(self, year: int, h: int, city: str | None = None) -> pd.DataFrame:
        """Forecast for every ward and every target week of a year (heatmap)."""
        f = self.feat.dropna(subset=FEATURES)
        tw = f["date"] + pd.Timedelta(weeks=h)
        f = f[tw.dt.year == year]
        if city:
            f = f[f["city"] == city]
        p = add_tiers(predict(self.bundle, f, h))
        p["ward_id"], p["city"] = f["ward_id"], f["city"]
        p["target_week"] = f["date"] + pd.Timedelta(weeks=h)
        p["actual"] = f[f"target_h{h}"]
        return p.reset_index(drop=True)

    def ward_weather(self, ward: str, end, weeks: int = 12) -> pd.DataFrame:
        r = self.raw[(self.raw["ward_id"] == ward) & (self.raw["date"] <= pd.Timestamp(end))]
        return r.tail(weeks)

    # ---- live mode ------------------------------------------------------
    def forecast_from_city_weather(self, weekly: pd.DataFrame, h: int) -> pd.DataFrame:
        """Forecast every ward from weekly city-level weather (live API or fallback).

        `weekly` has columns: city, date (week start, Monday), avg_temp_c, max_temp_c,
        min_temp_c, rainfall_mm, relative_humidity_pct; at least 7 weeks per city.
        """
        frame = self.wards.merge(weekly, on="city", how="inner")
        frame[TARGET] = np.nan
        feat = build_features(frame)
        ok = feat.dropna(subset=FEATURES)
        rows = ok[ok["date"] == ok.groupby("ward_id")["date"].transform("max")]
        return self.forecast_rows(rows, h)


def driver_columns() -> list[str]:
    return list(DRIVER_GROUPS)

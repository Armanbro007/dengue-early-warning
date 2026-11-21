"""Feature engineering: multi-week weather lags computed separately per ward.

Why lags: rain fills drains and containers, Aedes eggs need 7-14 days to become
adults, then viral incubation and symptom onset add more time. In this dataset
cases correlate most with rainfall from 3 weeks earlier (r = 0.75).

Every lag uses groupby("ward_id").shift(k), so a ward's lag never reads another
ward's weather. All features use only information available at the "as-of" week.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config
from .data import STATIC_COLS, TARGET

RAIN_LAGS = tuple(range(0, 7))  # 0-6 weeks back
HUM_LAGS = (0, 1, 2, 3, 4)
TEMP_LAGS = (0, 2, 4, 6)

RAIN_LAG_COLS = [f"rain_lag_{k}" for k in RAIN_LAGS]
RAIN_DERIVED = ["rain_sum_2wk", "rain_sum_4wk", "rain_sum_6wk"]
HUM_COLS = [f"humidity_lag_{k}" for k in HUM_LAGS]
TEMP_COLS = [f"temp_lag_{k}" for k in TEMP_LAGS] + ["temp_range_0"]
SEASON_COLS = ["woy_sin", "woy_cos"]

FEATURE_GROUPS: dict[str, list[str]] = {
    "Rainfall (0-6 wks ago)": RAIN_LAG_COLS + RAIN_DERIVED,
    "Humidity": HUM_COLS,
    "Temperature": TEMP_COLS,
    "Ward vulnerability": list(STATIC_COLS),
    "Season": SEASON_COLS,
}
FEATURES: list[str] = [c for cols in FEATURE_GROUPS.values() for c in cols]

# Domain constraints for the model: more rain / worse drainage / denser wards
# never *lower* predicted risk; better sanitation never raises it.
MONOTONIC = {
    **{c: 1 for c in RAIN_LAG_COLS + RAIN_DERIVED},
    "water_logging_risk_index": 1,
    "population_density_sqkm": 1,
    "sanitation_score": -1,
}


def add_rain_derived(df: pd.DataFrame) -> pd.DataFrame:
    """Rolling rain totals built from the lag columns (re-used by the what-if tool)."""
    df["rain_sum_2wk"] = df[["rain_lag_0", "rain_lag_1"]].sum(axis=1, min_count=2)
    df["rain_sum_4wk"] = df[[f"rain_lag_{k}" for k in range(4)]].sum(axis=1, min_count=4)
    df["rain_sum_6wk"] = df[[f"rain_lag_{k}" for k in range(6)]].sum(axis=1, min_count=6)
    return df


def add_season(df: pd.DataFrame) -> pd.DataFrame:
    woy = df["date"].dt.isocalendar().week.astype(int).clip(upper=52)
    df["woy"] = woy
    df["woy_sin"] = np.sin(2 * np.pi * woy / 52)
    df["woy_cos"] = np.cos(2 * np.pi * woy / 52)
    return df


def build_features(raw: pd.DataFrame) -> pd.DataFrame:
    """Return one row per (ward, as-of week) with lag features. Input must be validated."""
    df = raw.sort_values(["ward_id", "date"]).reset_index(drop=True).copy()
    g = df.groupby("ward_id", sort=False)
    new = {}
    for k in RAIN_LAGS:
        new[f"rain_lag_{k}"] = g["rainfall_mm"].shift(k)
    for k in HUM_LAGS:
        new[f"humidity_lag_{k}"] = g["relative_humidity_pct"].shift(k)
    for k in TEMP_LAGS:
        new[f"temp_lag_{k}"] = g["avg_temp_c"].shift(k)
    df = pd.concat([df, pd.DataFrame(new, index=df.index)], axis=1)
    df["temp_range_0"] = df["max_temp_c"] - df["min_temp_c"]
    df = add_rain_derived(df)
    df = add_season(df)
    return df


def add_targets(df: pd.DataFrame, horizons=config.HORIZONS) -> pd.DataFrame:
    """target_h{h} = cases in the same ward h weeks after the as-of week."""
    g = df.groupby("ward_id", sort=False)[TARGET]
    for h in horizons:
        df[f"target_h{h}"] = g.shift(-h)
    return df


def seasonal_reference(feat: pd.DataFrame, end_date: str | None = None) -> pd.DataFrame:
    """Typical conditions per week-of-year (median over all wards and training years).

    Used by the driver breakdown to answer: "compared with a normal week at this
    time of year in a typical ward, what is pushing this ward's risk up?"
    """
    src = feat if end_date is None else feat[feat["date"] <= end_date]
    weather_cols = RAIN_LAG_COLS + HUM_COLS + TEMP_COLS
    ref = src.groupby("woy")[weather_cols].median()
    ref = add_rain_derived(ref)
    for c in STATIC_COLS:
        ref[c] = src.drop_duplicates("ward_id")[c].median()
    return ref


def lag_correlations(raw: pd.DataFrame, max_lag: int = 8) -> pd.DataFrame:
    """Correlation of weekly cases with each weather variable k weeks earlier."""
    df = raw.sort_values(["ward_id", "date"])
    g = df.groupby("ward_id")
    rows = []
    for var, label in [("rainfall_mm", "Rainfall"), ("relative_humidity_pct", "Humidity"), ("avg_temp_c", "Temperature")]:
        for k in range(max_lag + 1):
            rows.append({"variable": label, "lag_weeks": k, "correlation": df[TARGET].corr(g[var].shift(k))})
    return pd.DataFrame(rows)

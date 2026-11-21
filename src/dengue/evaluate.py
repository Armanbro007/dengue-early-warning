"""Chronological evaluation: hold-out validation/test and a year-by-year backtest.

Nothing is ever shuffled. A model is only scored on weeks that come after
every week it was trained on, exactly like real deployment.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config
from .data import TARGET
from .features import FEATURES
from .model import fit_horizon, predict, training_rows
from .tiers import tier_index


def score(y, pred, lo=None, hi=None) -> dict:
    y, pred = np.asarray(y, float), np.asarray(pred, float)
    yt, pt = tier_index(y), tier_index(pred)
    high_true, high_pred = yt >= 2, pt >= 2
    out = {
        "n": int(len(y)),
        "mae": float(np.mean(np.abs(y - pred))),
        "rmse": float(np.sqrt(np.mean((y - pred) ** 2))),
        "tier_accuracy": float(np.mean(yt == pt)),
        "high_critical_recall": float((high_true & high_pred).sum() / max(high_true.sum(), 1)),
        "high_critical_precision": float((high_true & high_pred).sum() / max(high_pred.sum(), 1)),
    }
    if lo is not None and hi is not None:
        inside = (y >= np.asarray(lo)) & (y <= np.asarray(hi))
        out["interval_coverage"] = float(np.mean(inside))
        out["interval_coverage_case_weeks"] = float(np.mean(inside[y > 0])) if (y > 0).any() else None
    return out


def add_baselines(feat: pd.DataFrame, h: int) -> pd.DataFrame:
    """Naive forecasts a health office could use without ML, for comparison."""
    g = feat.groupby("ward_id", sort=False)[TARGET]
    feat = feat.copy()
    feat[f"persistence_h{h}"] = feat[TARGET]              # "same as this week"
    feat[f"last_year_h{h}"] = g.shift(52 - h)              # "same week last year"
    return feat


def period_rows(feat: pd.DataFrame, h: int, start: str, end: str | None = None) -> pd.DataFrame:
    return training_rows(feat, h, start=start, end=end)


def evaluate_split(bundle: dict, feat: pd.DataFrame, start: str, end: str | None = None) -> dict:
    """Score a trained bundle on target weeks in [start, end] for every horizon."""
    res = {}
    for h in bundle["horizons"]:
        rows = add_baselines(feat, h).loc[period_rows(feat, h, start, end).index]
        p = predict(bundle, rows, h)
        y = rows[f"target_h{h}"]
        base_ok = rows[f"last_year_h{h}"].notna()
        season = (rows["date"] + pd.Timedelta(weeks=h)).dt.month.between(6, 10).to_numpy()
        res[h] = {
            "model_in_season": score(y[season], p["pred"][season], p["lo"][season], p["hi"][season]),
            "persistence_in_season": score(y[season], rows.loc[season, f"persistence_h{h}"]),
            "last_year_in_season": score(y[season & base_ok.to_numpy()], rows.loc[season & base_ok.to_numpy(), f"last_year_h{h}"]),
            "model": score(y, p["pred"], p["lo"], p["hi"]),
            "persistence": score(y, rows[f"persistence_h{h}"]),
            "last_year": score(y[base_ok], rows.loc[base_ok, f"last_year_h{h}"]),
        }
    return res


def backtest_by_year(feat: pd.DataFrame, years=config.BACKTEST_YEARS, horizons=config.HORIZONS) -> list[dict]:
    """Expanding window: for each year Y, train on everything before Y, test on Y."""
    out = []
    for year in years:
        for h in horizons:
            train = training_rows(feat, h, end=f"{year - 1}-12-31")
            test = add_baselines(feat, h).loc[training_rows(feat, h, start=f"{year}-01-01", end=f"{year}-12-31").index]
            if test.empty:
                continue
            m = fit_horizon(train, h, intervals=False)
            pred = np.clip(m["mean"].predict(test[FEATURES]), 0, None)
            s = score(test[f"target_h{h}"], pred)
            s.update(year=year, horizon=h, persistence_mae=float(np.mean(np.abs(test[f"target_h{h}"] - test[f"persistence_h{h}"]))))
            out.append(s)
    return out

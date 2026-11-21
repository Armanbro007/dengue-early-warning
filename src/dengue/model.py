"""Train, save, load and run the dengue forecasting models.

One model per horizon (2, 3, 4 weeks ahead), each a HistGradientBoosting
regressor with a Poisson loss (cases are non-negative counts, 58% zeros).

80% intervals use split-conformal calibration: we re-fit the model on earlier
years, forecast the following year it never saw, and record how far off it was.
The 10th/90th percentiles of those out-of-sample errors (per forecast-size bin)
become the interval. Cheap, honest and needs no extra models at inference.
(sklearn's quantile-loss boosting collapsed to 0 on this zero-heavy target,
so we deliberately do not use it.)

Models are serialized with joblib and loaded once, so inference is ~ms.
"""
from __future__ import annotations

import logging
import time
import warnings
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import HistGradientBoostingRegressor

from . import config
from .features import FEATURES, MONOTONIC, seasonal_reference

log = logging.getLogger(__name__)


def make_model(loss: str = "poisson") -> HistGradientBoostingRegressor:
    return HistGradientBoostingRegressor(
        **config.MODEL_PARAMS, loss=loss, monotonic_cst={c: MONOTONIC.get(c, 0) for c in FEATURES}
    )


def training_rows(feat: pd.DataFrame, h: int, start=None, end=None) -> pd.DataFrame:
    """Rows usable for horizon h. The *target* week (as-of + h) must fall inside
    [start, end], so no label from a later period leaks into training."""
    tcol = f"target_h{h}"
    d = feat.dropna(subset=FEATURES + [tcol])
    target_date = d["date"] + pd.Timedelta(weeks=h)
    mask = pd.Series(True, index=d.index)
    if start is not None:
        mask &= target_date >= pd.Timestamp(start)
    if end is not None:
        mask &= target_date <= pd.Timestamp(end)
    return d[mask]


INTERVAL_BIN_EDGES = (0.0, 0.5, 2.0, 5.0, 10.0, np.inf)
CALIBRATION_YEARS = 3


def _calibrate(train: pd.DataFrame, h: int) -> dict:
    """Out-of-sample residual quantiles from the last few training years."""
    tcol = f"target_h{h}"
    target_year = (train["date"] + pd.Timedelta(weeks=h)).dt.year
    years = sorted(target_year.unique())[-CALIBRATION_YEARS:]
    preds, ys = [], []
    for year in years:
        fit_part, cal_part = train[target_year < year], train[target_year == year]
        if fit_part.empty or cal_part.empty:
            continue
        m = make_model("poisson").fit(fit_part[FEATURES], fit_part[tcol])
        preds.append(np.clip(m.predict(cal_part[FEATURES]), 0, None))
        ys.append(cal_part[tcol].to_numpy())
    pred, y = np.concatenate(preds), np.concatenate(ys)
    resid = y - pred
    bins = np.digitize(pred, INTERVAL_BIN_EDGES[1:-1])
    lo_q, hi_q = config.INTERVAL
    lo_off, hi_off = [], []
    for b in range(len(INTERVAL_BIN_EDGES) - 1):
        r = resid[bins == b] if (bins == b).sum() >= 30 else resid  # fall back to all residuals
        lo_off.append(float(np.quantile(r, lo_q)))
        hi_off.append(float(np.quantile(r, hi_q)))
    return {"edges": INTERVAL_BIN_EDGES, "lo_off": lo_off, "hi_off": hi_off, "years": [int(y) for y in years]}


def fit_horizon(train: pd.DataFrame, h: int, intervals: bool = True) -> dict:
    X, y = train[FEATURES], train[f"target_h{h}"]
    models = {"mean": make_model("poisson").fit(X, y)}
    if intervals:
        models["interval"] = _calibrate(train, h)
    return models


def train_bundle(feat: pd.DataFrame, end_date: str, data_hash: str = "", horizons=config.HORIZONS) -> dict:
    t0 = time.perf_counter()
    models = {h: fit_horizon(training_rows(feat, h, end=end_date), h) for h in horizons}
    return {
        "models": models,
        "features": FEATURES,
        "horizons": tuple(horizons),
        "train_end": end_date,
        "data_hash": data_hash,
        "sklearn_version": sklearn.__version__,
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "train_seconds": round(time.perf_counter() - t0, 2),
        "seasonal_ref": seasonal_reference(feat, end_date),
    }


def predict(bundle: dict, X: pd.DataFrame, h: int) -> pd.DataFrame:
    """Point forecast + 80% interval. Quantile lines are sorted so lo <= pred <= hi."""
    m = bundle["models"][h]
    pred = np.clip(m["mean"].predict(X[bundle["features"]]), 0, None)
    if "interval" in m:
        cal = m["interval"]
        b = np.digitize(pred, cal["edges"][1:-1])
        lo = np.clip(pred + np.take(cal["lo_off"], b), 0, None)
        hi = pred + np.take(cal["hi_off"], b)
    else:
        lo = hi = pred
    lo, hi = np.minimum(lo, pred), np.maximum(hi, pred)
    return pd.DataFrame({"pred": pred, "lo": lo, "hi": hi}, index=X.index)


def save_bundle(bundle: dict, path=config.MODEL_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, path, compress=3)


def load_bundle(path=config.MODEL_PATH, data_hash: str | None = None) -> dict | None:
    """Load a saved bundle; return None if missing, stale or from another sklearn version."""
    if not path.exists():
        return None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error")  # treat version-mismatch warnings as stale
            bundle = joblib.load(path)
    except Exception as exc:  # noqa: BLE001 - any unpickling problem means retrain
        log.warning("Saved model unusable (%s); will retrain", exc)
        return None
    if bundle.get("sklearn_version") != sklearn.__version__:
        return None
    if data_hash and bundle.get("data_hash") != data_hash:
        return None
    return bundle


def load_or_train(feat: pd.DataFrame, data_hash: str) -> dict:
    """Fast path: load serialized models. Slow path (~5 s): retrain and save."""
    bundle = load_bundle(data_hash=data_hash)
    if bundle is None:
        log.info("Training models (no valid saved bundle found)")
        bundle = train_bundle(feat, config.SHIP_TRAIN_END, data_hash)
        try:
            save_bundle(bundle)
        except OSError as exc:
            log.warning("Could not save model bundle: %s", exc)
    return bundle

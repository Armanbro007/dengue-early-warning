"""Train, save, load and run the dengue forecasting models.

One model per horizon (2, 3, 4 weeks ahead), each a HistGradientBoosting
regressor with a Poisson loss (cases are non-negative counts, 58% zeros),
plus two quantile models (10th / 90th percentile) for an 80% interval.
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


def make_model(loss: str = "poisson", quantile: float | None = None) -> HistGradientBoostingRegressor:
    kwargs = dict(config.MODEL_PARAMS, loss=loss, monotonic_cst={c: MONOTONIC.get(c, 0) for c in FEATURES})
    if quantile is not None:
        kwargs["quantile"] = quantile
    return HistGradientBoostingRegressor(**kwargs)


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


def fit_horizon(train: pd.DataFrame, h: int, intervals: bool = True) -> dict:
    X, y = train[FEATURES], train[f"target_h{h}"]
    models = {"mean": make_model("poisson").fit(X, y)}
    if intervals:
        lo_q, hi_q = config.INTERVAL
        models["lo"] = make_model("quantile", lo_q).fit(X, y)
        models["hi"] = make_model("quantile", hi_q).fit(X, y)
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
    Xf = X[bundle["features"]]
    pred = np.clip(m["mean"].predict(Xf), 0, None)
    lo = np.clip(m["lo"].predict(Xf), 0, None) if "lo" in m else pred
    hi = np.clip(m["hi"].predict(Xf), 0, None) if "hi" in m else pred
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

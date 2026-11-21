"""Driver breakdown: why is this ward's risk high?

Method (group ablation, easy to explain): start from a *reference* week, i.e. typical
weather for this time of year and a typical ward. For each driver group (rainfall,
humidity, temperature, ward vulnerability) we swap the ward's real values for the
reference values and see how much the forecast drops. That drop is the group's
contribution. Whatever is left over (groups interacting) is shown as "Combined
effects", so the bars always add up exactly to the forecast.

All variants for all wards are scored in ONE batched predict call (fast).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .features import FEATURE_GROUPS, add_rain_derived
from .model import predict

DRIVER_GROUPS = [g for g in FEATURE_GROUPS if g != "Season"]


def _reference_rows(bundle: dict, X: pd.DataFrame) -> pd.DataFrame:
    ref = bundle["seasonal_ref"]
    return ref.reindex(X["woy"].to_numpy()).set_index(X.index)


def explain(bundle: dict, X: pd.DataFrame, h: int) -> pd.DataFrame:
    """Return one row per ward: baseline, contribution per driver group, combined, prediction."""
    X = X.copy()
    ref = _reference_rows(bundle, X)
    variants = {"full": X}
    base = X.copy()
    for g in DRIVER_GROUPS:
        cols = FEATURE_GROUPS[g]
        v = X.copy()
        v[cols] = ref[cols].to_numpy()
        variants[g] = v
        base[cols] = ref[cols].to_numpy()
    variants["baseline"] = base

    stacked = pd.concat(list(variants.values()), keys=list(variants.keys()))
    preds = predict(bundle, stacked, h)["pred"]

    out = pd.DataFrame(index=X.index)
    full = preds.loc["full"].to_numpy()
    out["baseline"] = preds.loc["baseline"].to_numpy()
    contrib_sum = np.zeros(len(X))
    for g in DRIVER_GROUPS:
        out[g] = full - preds.loc[g].to_numpy()
        contrib_sum += out[g].to_numpy()
    out["Combined effects"] = full - out["baseline"] - contrib_sum
    out["prediction"] = full
    out["main_driver"] = out[DRIVER_GROUPS].idxmax(axis=1).where(out[DRIVER_GROUPS].max(axis=1) > 0.25, "Seasonal norm")

    # Plain-language evidence for the rainfall driver
    breeding = X[["rain_lag_1", "rain_lag_2", "rain_lag_3"]].sum(axis=1)
    normal = ref[["rain_lag_1", "rain_lag_2", "rain_lag_3"]].sum(axis=1)
    out["breeding_rain_mm"] = breeding
    out["breeding_rain_normal_mm"] = normal
    return out


def apply_rain_whatif(X: pd.DataFrame, extra_mm: float) -> pd.DataFrame:
    """What if this week gets `extra_mm` more rain? Rebuild the dependent rain totals."""
    X = X.copy()
    X["rain_lag_0"] = (X["rain_lag_0"] + extra_mm).clip(lower=0)
    return add_rain_derived(X)

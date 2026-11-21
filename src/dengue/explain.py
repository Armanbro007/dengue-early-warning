"""Driver breakdown: why is this ward's risk high?

Method: exact Shapley values over 4 driver *groups* (rainfall, humidity,
temperature, ward vulnerability), measured against a reference week.

* Reference ("baseline") = typical weather for this week of the year and a
  typical ward (medians from the training years). Its forecast is the seasonal norm.
* For every subset of groups we swap the ward's real values in and the rest to
  the reference (2^4 = 16 variants), score them all in ONE batched predict call,
  and average each group's marginal effect over all orders it could be added.
* Result: baseline + sum(contributions) == forecast, exactly. Because the
  Poisson model is multiplicative, a simple one-at-a-time swap would double-count;
  Shapley shares the overlap fairly. 60 wards x 16 variants = 960 rows, ~10 ms.
"""
from __future__ import annotations

from itertools import product
from math import factorial

import numpy as np
import pandas as pd

from .features import FEATURE_GROUPS, add_rain_derived
from .model import predict

DRIVER_GROUPS = [g for g in FEATURE_GROUPS if g != "Season"]


def _reference_rows(bundle: dict, X: pd.DataFrame) -> pd.DataFrame:
    ref = bundle["seasonal_ref"]
    return ref.reindex(X["woy"].to_numpy()).set_index(X.index)


def explain(bundle: dict, X: pd.DataFrame, h: int) -> pd.DataFrame:
    """One row per ward: baseline, Shapley contribution per driver group, prediction."""
    n = len(DRIVER_GROUPS)
    ref = _reference_rows(bundle, X)
    masks = list(product((0, 1), repeat=n))  # 1 = use the ward's real values
    variants = []
    for mask in masks:
        v = X.copy()
        for on, g in zip(mask, DRIVER_GROUPS):
            if not on:
                cols = FEATURE_GROUPS[g]
                v[cols] = ref[cols].to_numpy()
        variants.append(v)
    preds = predict(bundle, pd.concat(variants, keys=range(len(masks))), h)["pred"]
    f = {mask: preds.loc[i].to_numpy() for i, mask in enumerate(masks)}

    out = pd.DataFrame(index=X.index)
    out["baseline"] = f[(0,) * n]
    for i, g in enumerate(DRIVER_GROUPS):
        phi = np.zeros(len(X))
        for mask in masks:
            if mask[i]:
                continue
            k = sum(mask)
            weight = factorial(k) * factorial(n - k - 1) / factorial(n)
            with_i = mask[:i] + (1,) + mask[i + 1:]
            phi += weight * (f[with_i] - f[mask])
        out[g] = phi
    out["prediction"] = f[(1,) * n]
    top = out[DRIVER_GROUPS]
    out["main_driver"] = top.idxmax(axis=1).where(top.max(axis=1) > 0.25, "Seasonal norm")

    # Plain-language evidence for the rainfall driver: rain in the last 3 weeks is what
    # breeds the mosquitoes behind cases 2-4 weeks from now.
    window = ["rain_lag_0", "rain_lag_1", "rain_lag_2"]
    out["breeding_rain_mm"] = X[window].sum(axis=1)
    out["breeding_rain_normal_mm"] = ref[window].sum(axis=1)
    return out


def apply_rain_whatif(X: pd.DataFrame, extra_mm: float) -> pd.DataFrame:
    """What if this week gets `extra_mm` more rain? Rebuild the dependent rain totals."""
    X = X.copy()
    X["rain_lag_0"] = (X["rain_lag_0"] + extra_mm).clip(lower=0)
    return add_rain_derived(X)

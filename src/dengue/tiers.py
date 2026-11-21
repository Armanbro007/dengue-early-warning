"""Turn predicted case counts into Low / Medium / High / Critical risk tiers."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import TIER_MIN_CASES, TIERS

_THRESHOLDS = [TIER_MIN_CASES[t] for t in TIERS]


def tier_index(cases) -> np.ndarray:
    """0=Low, 1=Medium, 2=High, 3=Critical."""
    return np.searchsorted(_THRESHOLDS, np.asarray(cases, dtype=float), side="right") - 1


def tier_of(cases) -> np.ndarray:
    return np.array(TIERS, dtype=object)[tier_index(cases)]


def add_tiers(df: pd.DataFrame) -> pd.DataFrame:
    """Adds tier + an early 'could reach Critical' flag from the interval's upper bound.

    Officers would rather check a false alarm than miss an outbreak, so a ward whose
    90th-percentile forecast crosses the Critical line is flagged even if its
    central forecast is lower.
    """
    df = df.copy()
    df["tier"] = tier_of(df["pred"])
    df["tier_rank"] = tier_index(df["pred"])
    df["critical_watch"] = (df["hi"] >= TIER_MIN_CASES["Critical"]) & (df["tier"] != "Critical")
    return df

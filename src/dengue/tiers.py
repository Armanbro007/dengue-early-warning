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
    """Adds the tier plus two early-warning flags.

    * near_critical: High, and the forecast is within 25% of the Critical line.
    * escalating: the ward is Low/Medium *now* (this week's reported cases) but is
      forecast High/Critical, i.e. exactly the wards where acting early pays off.
    """
    df = df.copy()
    df["tier"] = tier_of(df["pred"])
    df["tier_rank"] = tier_index(df["pred"])
    df["near_critical"] = (df["tier"] == "High") & (df["pred"] >= 0.75 * TIER_MIN_CASES["Critical"])
    if "cases_now" in df:
        now_rank = pd.Series(tier_index(df["cases_now"].fillna(0)), index=df.index)
        df["tier_now"] = np.where(df["cases_now"].notna(), tier_of(df["cases_now"].fillna(0)), None)
        df["escalating"] = df["cases_now"].notna() & (now_rank <= 1) & (df["tier_rank"] >= 2)
    else:
        df["tier_now"], df["escalating"] = None, False
    return df

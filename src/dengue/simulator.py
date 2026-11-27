"""Module 3: what if we send larvicide / fogging crews? A model-driven counterfactual.

Idea: our forecast model learned that rain from the last 0-6 weeks drives cases
2-4 weeks later (standing water -> larvae -> mosquitoes -> infections). A crew
destroys part of that standing water. So we ask the SAME trained model:
"what would you forecast if this ward had X% less breeding water from the last
3 weeks of rain?"

  coverage(c) = 1 - (1 - 0.20)^c      1 crew 20%, 2 crews 36%, 3 crews 49%, 4 crews 59%
  treated rain_lag_k = rain_lag_k x (1 - coverage), for k = 0, 1, 2 (+ rolling sums rebuilt)
  cases prevented   = forecast(no crews) - forecast(with crews), at 2, 3 and 4 weeks ahead
  beds / saline saved = cases prevented x the learned per-case ratios
  ROI               = cases prevented over weeks 2-4 / crews sent

The 20%-per-crew figure is an ASSUMPTION in config.CREW_COVERAGE; the size of
the effect in each ward comes from the model (wet, dense, poorly drained wards
gain most). Every crew level 0-4 for every ward and every horizon is ONE batched
predict call (60 x 5 x 3 = 900 rows, ~30 ms).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config
from .features import add_rain_derived
from .model import predict


def coverage(crews) -> np.ndarray:
    return 1 - (1 - config.CREW_COVERAGE) ** np.asarray(crews, dtype=float)


def treat(rows: pd.DataFrame, crews) -> pd.DataFrame:
    """Copy of the feature rows with crews' share of breeding water removed."""
    X = rows.copy()
    keep = 1 - coverage(crews)
    for k in config.BREEDING_RAIN_LAGS:
        X[f"rain_lag_{k}"] = X[f"rain_lag_{k}"] * keep
    return add_rain_derived(X)


def effect_table(bundle: dict, rows: pd.DataFrame, horizons=config.HORIZONS) -> pd.DataFrame:
    """Forecast for every ward x crew level (0..MAX) x horizon in one batch.

    Returns one row per (ward_id, crews) with cases_h{h} columns and cases_2to4 total.
    """
    levels = range(config.MAX_CREWS_PER_WARD + 1)
    batch = pd.concat([treat(rows, c) for c in levels], keys=list(levels), names=["crews", "row"])
    out = pd.DataFrame({"ward_id": np.tile(rows["ward_id"].to_numpy(), len(levels)),
                        "crews": batch.index.get_level_values("crews")})
    for h in horizons:
        out[f"cases_h{h}"] = predict(bundle, batch, h)["pred"].to_numpy()
    out["cases_2to4"] = out[[f"cases_h{h}" for h in horizons]].sum(axis=1)
    return out


def simulate(effects: pd.DataFrame, plan: dict[str, int], ratios: dict[str, float]) -> pd.DataFrame:
    """Before/after for each ward in `plan` ({ward_id: crews})."""
    base = effects[effects["crews"] == 0].set_index("ward_id")
    rows = []
    for ward, c in plan.items():
        c = int(min(max(c, 0), config.MAX_CREWS_PER_WARD))
        after = effects[(effects["ward_id"] == ward) & (effects["crews"] == c)].iloc[0]
        r = {"ward_id": ward, "crews": c, "coverage_pct": round(100 * float(coverage(c)), 0)}
        for h in config.HORIZONS:
            r[f"before_h{h}"], r[f"after_h{h}"] = base.at[ward, f"cases_h{h}"], after[f"cases_h{h}"]
        r["cases_before"], r["cases_after"] = base.at[ward, "cases_2to4"], after["cases_2to4"]
        r["cases_prevented"] = r["cases_before"] - r["cases_after"]
        r["beds_saved"] = r["cases_prevented"] * ratios["hospital_beds_required"]
        r["saline_saved"] = r["cases_prevented"] * ratios["saline_bags_needed"]
        r["roi"] = r["cases_prevented"] / c if c else 0.0
        rows.append(r)
    return pd.DataFrame(rows)


def roi_ranking(effects: pd.DataFrame) -> pd.DataFrame:
    """Cases prevented over weeks 2-4 by ONE crew in each ward, best first."""
    e = effects.pivot(index="ward_id", columns="crews", values="cases_2to4")
    r = pd.DataFrame({"cases_no_crew": e[0], "prevented_by_1_crew": e[0] - e[1],
                      f"prevented_by_{config.MAX_CREWS_PER_WARD}_crews": e[0] - e[config.MAX_CREWS_PER_WARD]})
    return r.sort_values("prevented_by_1_crew", ascending=False).reset_index()


def best_plan(effects: pd.DataFrame, crews: int, eligible: list[str] | None = None) -> dict[str, int]:
    """Send crews one at a time, each to the ward where the NEXT crew prevents the most cases.

    Because each extra crew in the same ward clears less, this spreads crews sensibly.
    """
    e = effects.pivot(index="ward_id", columns="crews", values="cases_2to4")
    if eligible is not None:
        e = e.loc[[w for w in eligible if w in e.index]]
    plan = dict.fromkeys(e.index, 0)
    for _ in range(int(crews)):
        gains = {w: e.at[w, c] - e.at[w, c + 1] for w, c in plan.items() if c < config.MAX_CREWS_PER_WARD}
        if not gains:
            break
        w = max(gains, key=gains.get)
        if gains[w] <= 1e-9:
            break  # no ward benefits any more
        plan[w] += 1
    return {w: c for w, c in plan.items() if c > 0}

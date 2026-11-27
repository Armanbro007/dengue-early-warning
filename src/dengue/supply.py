"""Module 1: turn forecast cases into supplies, then share scarce stock by priority.

Step 1  Ratios.  The onsite data says what every ward-week needed. Supplies grow
        with cases, so we learn one number per item from the training years:
        ratio = total item / total cases (2.38 saline bags, 1.15 kits, 0.29 beds per
        case). Checked on 2024-2025: round(cases x ratio) is off by under 0.03 units.
Step 2  Demand.  need = round(forecast cases x ratio) for each ward.
Step 3  Scarcity.  The officer says how much stock the region has (30-100% of total
        need). Wards are served in priority order, highest tier first, then by
        "crowded cases" = forecast cases x (ward density / median density), so a
        dense ward with the same cases goes first. Each ward gets all it needs until
        the stock runs out, in two rounds:
          round 1 (lifeline): every ward, in priority order, gets 50% of its need;
          round 2 (top-up):   what is left tops wards up to 100%, in priority order.
        So the riskiest, most crowded wards are filled first, but no ward with
        patients is left with nothing while stock remains. Below 100% = deficit;
        below the 50% lifeline = CRITICAL deficit.

Everything is plain pandas arithmetic: no network, no randomness, under 5 ms.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config
from .data import TARGET

ITEMS = config.SUPPLY_ITEMS
# Ratios measured on the onsite dataset; used only if a CSV without supply columns is loaded.
FALLBACK_RATIOS = {"saline_bags_needed": 2.378, "diagnostic_kits_needed": 1.147, "hospital_beds_required": 0.29}


def learn_ratios(raw: pd.DataFrame, end: str = config.SHIP_TRAIN_END) -> dict[str, float]:
    """Units of each item per dengue case, learned from the training years only."""
    train = raw[raw["date"] <= pd.Timestamp(end)]
    ratios = {}
    for item in ITEMS:
        rows = train[train[item].notna()] if item in train else train.iloc[:0]
        cases = rows[TARGET].sum()  # only weeks that report this item (weekly updates may not)
        ratios[item] = float(rows[item].sum() / cases) if cases > 0 else FALLBACK_RATIOS[item]
    return ratios


def bed_capacity(raw: pd.DataFrame, end: str = config.SHIP_TRAIN_END) -> pd.Series:
    """ASSUMPTION (the data has no bed counts). Two simple rules:

    1. City pool: the dengue beds a city needed in 95% of training weeks (it coped then).
    2. Hospitals follow people, not mosquitoes: the pool is split between the city's wards
       by population density. So wet, badly drained wards overflow while drier wards in the
       same city have room, which is exactly when routing patients helps.
    """
    train = raw[raw["date"] <= pd.Timestamp(end)]
    col = "hospital_beds_required"
    weekly = (train.groupby(["city", "date"])[col].sum() if col in train
              else train.groupby(["city", "date"])[TARGET].sum() * FALLBACK_RATIOS[col])
    pool = weekly.groupby("city").quantile(config.BED_CAPACITY_QUANTILE)
    wards = raw.drop_duplicates("ward_id").set_index("ward_id")
    share = wards["population_density_sqkm"] / wards.groupby("city")["population_density_sqkm"].transform("sum")
    beds = np.floor(share * wards["city"].map(pool) + 0.5).clip(lower=config.MIN_WARD_BEDS)
    return beds.astype(int).rename("bed_capacity")


def demand(fc: pd.DataFrame, ratios: dict[str, float], cautious: bool = False) -> pd.DataFrame:
    """One row per ward: cases we plan for and the units of each item they need.

    cautious=True plans for the top of the 80% forecast range ("a bad week") instead of the
    expected number, which is what a surge planner would stock for.
    """
    d = fc[["ward_id", "city", "population_density_sqkm", "tier", "tier_rank", "pred", "lo", "hi"]].copy()
    # Context the dispatch notices quote (issue date, risk now, main reason), when the forecast has it
    for col in ("date", "tier_now", "main_driver", "breeding_rain_mm", "breeding_rain_normal_mm"):
        if col in fc:
            d[col] = fc[col].to_numpy()
    d["plan_cases"] = (d["hi"] if cautious else d["pred"]).clip(lower=0)
    for item in ITEMS:
        # Round half up (same rule as the dataset), never negative.
        d[f"need_{item}"] = np.floor(d["plan_cases"] * ratios[item] + 0.5).astype(int)
    return d


def priority_order(d: pd.DataFrame) -> pd.DataFrame:
    """Highest tier first; inside a tier, most crowded cases first."""
    d = d.copy()
    density = d["population_density_sqkm"] / d["population_density_sqkm"].median()
    d["priority_score"] = (d["plan_cases"] * density).round(2)
    d = d.sort_values(["tier_rank", "priority_score"], ascending=False).reset_index(drop=True)
    d["priority"] = np.arange(1, len(d) + 1)
    return d


def greedy_fill(need: pd.Series, stock: int) -> pd.Series:
    """Give each ward (already in priority order) everything it asks for until stock runs out."""
    before = need.cumsum() - need  # stock used by higher-priority wards
    return need.clip(upper=(stock - before).clip(lower=0)).astype(int)


def priority_fill(need: pd.Series, stock: int, lifeline: float = config.CRITICAL_FILL) -> pd.Series:
    """Round 1: a lifeline share for every ward. Round 2: top up to 100%. Both in priority order."""
    round1 = greedy_fill(np.ceil(need * lifeline).astype(int), stock)
    round2 = greedy_fill(need - round1, stock - int(round1.sum()))
    return round1 + round2


def allocate(d: pd.DataFrame, stock_pct: float) -> tuple[pd.DataFrame, dict]:
    """Share each consumable's regional stock (stock_pct % of total need) by priority.

    Returns the ward table (in priority order) and a per-item summary.
    """
    d = priority_order(d)
    summary = {}
    for item in config.CONSUMABLES:
        need = d[f"need_{item}"]
        stock = int(np.floor(need.sum() * stock_pct / 100))
        d[f"alloc_{item}"] = priority_fill(need, stock)
        d[f"short_{item}"] = need - d[f"alloc_{item}"]
        summary[item] = {"need": int(need.sum()), "stock": stock, "allocated": int(d[f"alloc_{item}"].sum()),
                         "short": int(d[f"short_{item}"].sum()), "wards_short": int((d[f"short_{item}"] > 0).sum())}
    fills = [np.where(d[f"need_{i}"] > 0, d[f"alloc_{i}"] / d[f"need_{i}"].clip(lower=1), 1.0) for i in config.CONSUMABLES]
    d["fill_pct"] = (100 * np.minimum.reduce(fills)).round(0)  # the worst-supplied item decides
    d["deficit"] = np.select([d["fill_pct"] < 100 * config.CRITICAL_FILL, d["fill_pct"] < 100],
                             ["CRITICAL", "Short"], "Fully supplied")
    return d, summary

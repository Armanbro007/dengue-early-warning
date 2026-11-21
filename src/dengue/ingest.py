"""Add new weekly data (the "live update"): validate, merge, retrain.

New rows are stored in data/updates.csv, never written into the official file,
so the system can always be reset. Rows for an existing (ward, week) replace
the old values, e.g. when late case reports arrive.

CLI:  python scripts/ingest.py path/to/new_weeks.csv
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import pandas as pd

from . import config
from .data import REQUIRED_COLS, file_hash, load_raw, validate
from .features import add_targets, build_features
from .model import load_or_train


@dataclass
class UpdateSummary:
    rows: int
    new_rows: int
    replaced_rows: int
    new_wards: list
    weeks: tuple
    warnings: list


def check_update(new: pd.DataFrame) -> UpdateSummary:
    """Compare an update with the current data without changing anything."""
    new = validate(new)
    current = load_raw(allow_download=False)
    key_cur = set(zip(current["ward_id"], current["date"]))
    keys = list(zip(new["ward_id"], new["date"]))
    replaced = sum(k in key_cur for k in keys)
    new_wards = sorted(set(new["ward_id"]) - set(current["ward_id"]))
    warnings = []
    if new[["rainfall_mm", "avg_temp_c", "relative_humidity_pct"]].isna().any().any():
        warnings.append("Some weather values are missing and were interpolated within each ward.")
    if (new["date"].dt.weekday != 0).any():
        warnings.append("Some dates are not Mondays; the dataset uses Monday week starts.")
    gap = (new["date"].min() - current["date"].max()).days
    if gap > 7:
        warnings.append(f"There is a {gap // 7 - 1}-week gap after the last known week; lag features will be missing there.")
    if new_wards:
        warnings.append(f"New wards {new_wards} need at least 7 weeks of history before they can be forecast.")
    return UpdateSummary(len(new), len(new) - replaced, replaced, new_wards,
                         (new["date"].min(), new["date"].max()), warnings)


def apply_update(new: pd.DataFrame) -> UpdateSummary:
    summary = check_update(new)
    new = validate(new)[REQUIRED_COLS]
    if config.UPDATES_PATH.exists():
        old = pd.read_csv(config.UPDATES_PATH, parse_dates=["date"])
        new = pd.concat([old, new], ignore_index=True).drop_duplicates(["ward_id", "date"], keep="last")
    config.UPDATES_PATH.parent.mkdir(parents=True, exist_ok=True)
    new.sort_values(["ward_id", "date"]).to_csv(config.UPDATES_PATH, index=False, date_format="%Y-%m-%d")
    return summary


def reset_updates() -> None:
    config.UPDATES_PATH.unlink(missing_ok=True)


def retrain() -> dict:
    """Rebuild features and models for the current data. Returns timing info."""
    t0 = time.perf_counter()
    feat = add_targets(build_features(load_raw()))
    bundle = load_or_train(feat, file_hash(), force=True)
    return {"seconds": round(time.perf_counter() - t0, 1), "trained_through": bundle["train_end"]}


def template_csv() -> str:
    """The latest week of data as an example of the expected format."""
    raw = load_raw(allow_download=False)
    last = raw[raw["date"] == raw["date"].max()]
    return last[REQUIRED_COLS].to_csv(index=False, date_format="%Y-%m-%d")

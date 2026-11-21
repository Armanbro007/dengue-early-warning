"""Load and validate the ward-week dataset.

Local CSV first (fast, offline). If it is missing, download the official
Google Sheet once and cache it to disk, so the sheet is never hit twice.
"""
from __future__ import annotations

import hashlib
import io
import logging
from pathlib import Path

import pandas as pd

from . import config
from .http import download_text

log = logging.getLogger(__name__)

WEATHER_COLS = ["avg_temp_c", "max_temp_c", "min_temp_c", "rainfall_mm", "relative_humidity_pct"]
STATIC_COLS = ["population_density_sqkm", "water_logging_risk_index", "sanitation_score"]
TARGET = "dengue_cases"
REQUIRED_COLS = ["date", "city", "ward_id", *STATIC_COLS, *WEATHER_COLS, TARGET]


def download_dataset(path: Path = config.DATA_PATH) -> Path:
    """Fetch the official sheet as CSV (one request, with retries) and save it."""
    log.info("Local dataset missing; downloading official sheet once")
    text = download_text("google-sheet", config.SHEET_CSV_URL)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def validate(df: pd.DataFrame) -> pd.DataFrame:
    """Check schema and clean defensively so new or messy data cannot break the pipeline."""
    df = df.rename(columns=lambda c: c.strip().lower())
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Dataset is missing required columns: {missing}")

    df = df[REQUIRED_COLS].copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for col in [*STATIC_COLS, *WEATHER_COLS, TARGET]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["date", "ward_id"])
    df = df.drop_duplicates(["ward_id", "date"], keep="last")
    df = df.sort_values(["ward_id", "date"]).reset_index(drop=True)

    # Physical sanity bounds
    df["rainfall_mm"] = df["rainfall_mm"].clip(lower=0)
    df["relative_humidity_pct"] = df["relative_humidity_pct"].clip(0, 100)

    # Short weather gaps: interpolate within each ward only (never across wards)
    df[WEATHER_COLS] = df.groupby("ward_id")[WEATHER_COLS].transform(
        lambda s: s.interpolate(limit=2, limit_direction="both")
    )
    # Ward attributes are constant per ward: fill any gap from the same ward
    df[STATIC_COLS] = df.groupby("ward_id")[STATIC_COLS].transform(lambda s: s.ffill().bfill())
    return df


def load_raw(path: Path = config.DATA_PATH, allow_download: bool = True) -> pd.DataFrame:
    if not path.exists():
        if not allow_download:
            raise FileNotFoundError(path)
        download_dataset(path)
    return validate(pd.read_csv(path))


def load_from_bytes(data: bytes) -> pd.DataFrame:
    """Validate an uploaded CSV (used for new weekly data in the live system)."""
    return validate(pd.read_csv(io.BytesIO(data)))


def file_hash(path: Path = config.DATA_PATH) -> str:
    """Short content hash: models/caches are rebuilt only when the data changes."""
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:12]

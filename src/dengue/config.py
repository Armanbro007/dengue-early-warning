"""Central configuration: paths, horizons, tier thresholds and split dates.

Everything tunable lives here so the rest of the code has no magic numbers.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

# ---- Data ---------------------------------------------------------------
DATA_PATH = ROOT / "data" / "bangladesh_dengue.csv"
# New weekly data added through the dashboard or scripts/ingest.py (kept separate
# from the official file so it can always be reset).
UPDATES_PATH = ROOT / "data" / "updates.csv"
# Official dataset (Google Sheet). Used only if the bundled CSV is missing.
SHEET_ID = "1QFI0ACJRvJQkiQT3LfGHklM3g4PgaJWUt8xSVU07NIE"
SHEET_CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

CACHE_DIR = ROOT / ".cache"
MODELS_DIR = ROOT / "models"
MODEL_PATH = MODELS_DIR / "dengue_models.joblib"
METRICS_PATH = MODELS_DIR / "metrics.json"

# ---- Forecasting --------------------------------------------------------
# Rain -> breeding (7-14 days) -> incubation -> symptoms: 2-4 week lag.
HORIZONS = (2, 3, 4)  # weeks ahead
DEFAULT_HORIZON = 3

# Chronological split (never shuffled)
TRAIN_END = "2022-12-31"   # train: 2016-2022
VAL_YEAR = 2023            # validation: tuning + tier thresholds
TEST_START = "2024-01-01"  # test: 2024-2025, untouched until the final report
BACKTEST_YEARS = (2019, 2020, 2021, 2022, 2023, 2024, 2025)

# Shipped model is trained on 2016-2023 so 2024-2025 stays a true hold-out
# that the dashboard can replay week by week.
SHIP_TRAIN_END = "2023-12-31"

MODEL_PARAMS = dict(
    max_iter=300,
    learning_rate=0.05,
    max_leaf_nodes=31,
    min_samples_leaf=40,
    l2_regularization=1.0,
    random_state=42,
)
INTERVAL = (0.10, 0.90)  # 80% prediction interval

# ---- Risk tiers (predicted cases per ward per week) ---------------------
# Set from the historical distribution: ~p66 / p78 / p90 of weekly ward cases.
TIERS = ("Low", "Medium", "High", "Critical")
TIER_MIN_CASES = {"Low": 0.0, "Medium": 2.0, "High": 5.0, "Critical": 10.0}
# Status palette (always shown with the tier name, never colour alone)
TIER_COLORS = {
    "Low": "#5B8DEF",
    "Medium": "#D9A82E",
    "High": "#E95A2C",
    "Critical": "#A61E4D",
}

# ---- Network / cost controls --------------------------------------------
ALLOW_NETWORK = os.getenv("ALLOW_NETWORK", "1") != "0"
HTTP_TIMEOUT_S = 8
HTTP_MAX_RETRIES = 4
WEATHER_CACHE_TTL_H = 6
CIRCUIT_BREAKER_FAILS = 3
CIRCUIT_BREAKER_COOLDOWN_S = 600

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
LLM_DAILY_CALL_BUDGET = int(os.getenv("LLM_DAILY_CALL_BUDGET", "50"))
LLM_MAX_OUTPUT_TOKENS = 300

# City centroids (approximate) for the live weather forecast.
CITY_COORDS = {
    "Dhaka North": (23.83, 90.42),
    "Dhaka South": (23.72, 90.41),
    "Chattogram": (22.36, 91.78),
    "Gazipur": (24.00, 90.42),
    "Narayanganj": (23.62, 90.50),
}

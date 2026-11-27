"""Write sample dispatch notices (SMS, WhatsApp, printable briefs) to /exports. Works offline.

Usage:  python scripts/export_dispatch.py
        python scripts/export_dispatch.py --as-of 2025-06-02 --weeks 3 --stock 60 --crews 20 --beds 80
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("ALLOW_NETWORK", "0")  # exports never need the internet

import pandas as pd  # noqa: E402

from dengue.dispatch import write_exports  # noqa: E402
from dengue.engine import Engine  # noqa: E402
from dengue.operations import Settings  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", default="2025-06-02", help="week the forecast is made (replay)")
    ap.add_argument("--weeks", type=int, default=3, help="weeks ahead (2, 3 or 4)")
    ap.add_argument("--stock", type=float, default=60, help="regional stock, %% of need (30-100)")
    ap.add_argument("--crews", type=int, default=20, help="spraying crews available")
    ap.add_argument("--beds", type=float, default=80, help="share of usual dengue beds free (30-100)")
    ap.add_argument("--cautious", action="store_true", help="plan for the top of the forecast range")
    a = ap.parse_args()

    t0 = time.perf_counter()
    engine = Engine.load()
    plan = engine.plan(a.as_of, a.weeks, settings=Settings(a.stock, a.crews, a.beds, a.cautious))
    week = pd.Timestamp(a.as_of) + pd.Timedelta(weeks=a.weeks)  # the week the notices are about
    paths = write_exports(plan, week)
    print(f"Wrote {len(paths)} files to exports/ in {time.perf_counter() - t0:.1f}s:")
    for p in paths:
        print("  ", p.name)


if __name__ == "__main__":
    main()

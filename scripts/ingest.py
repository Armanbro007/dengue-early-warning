"""Add new weekly data and retrain:  python scripts/ingest.py new_weeks.csv [--reset]"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402

from dengue.ingest import apply_update, reset_updates, retrain  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="?", help="CSV with the same columns as the official dataset")
    ap.add_argument("--reset", action="store_true", help="remove all added updates")
    args = ap.parse_args()
    if args.reset:
        reset_updates()
        print("Updates removed; back to the official dataset.")
    elif args.csv:
        s = apply_update(pd.read_csv(args.csv))
        print(f"Added {s.new_rows} new rows, replaced {s.replaced_rows}, weeks {s.weeks[0]:%Y-%m-%d} to {s.weeks[1]:%Y-%m-%d}")
        for w in s.warnings:
            print("  warning:", w)
    else:
        ap.error("give a CSV path or --reset")
    info = retrain()
    print(f"Models retrained through {info['trained_through']} in {info['seconds']} s")


if __name__ == "__main__":
    main()

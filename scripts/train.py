"""Rebuild everything from the raw CSV: features -> evaluation -> shipped models.

Usage:  python scripts/train.py            (full run with year-by-year backtest)
        python scripts/train.py --quick    (skip the backtest, ~10 s)
        python scripts/train.py --all-data (ship a model trained on every year; use
                                            this in production once evaluation is done)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dengue import config  # noqa: E402
from dengue.data import file_hash, load_raw  # noqa: E402
from dengue.evaluate import backtest_by_year, evaluate_split  # noqa: E402
from dengue.features import add_targets, build_features, lag_correlations  # noqa: E402
from dengue.model import predict, save_bundle, train_bundle  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="skip year-by-year backtest")
    ap.add_argument("--all-data", action="store_true", help="train shipped model on all years")
    args = ap.parse_args()

    t0 = time.perf_counter()
    raw = load_raw()
    feat = add_targets(build_features(raw))
    data_hash = file_hash()
    print(f"Loaded {len(raw):,} rows, {raw.ward_id.nunique()} wards, "
          f"{raw.date.min():%Y-%m-%d} to {raw.date.max():%Y-%m-%d} ({time.perf_counter() - t0:.1f}s)")

    # 1) Validation: train 2016-2022, score 2023 (used to choose params/thresholds)
    val_bundle = train_bundle(feat, config.TRAIN_END, data_hash)
    val = evaluate_split(val_bundle, feat, f"{config.VAL_YEAR}-01-01", f"{config.VAL_YEAR}-12-31")

    # 2) Shipped model: train 2016-2023, score the untouched 2024-2025 test set
    ship_end = str(raw.date.max().date()) if args.all_data else config.SHIP_TRAIN_END
    bundle = train_bundle(feat, ship_end, data_hash)
    test = evaluate_split(train_bundle(feat, config.SHIP_TRAIN_END, data_hash), feat, config.TEST_START) \
        if args.all_data else evaluate_split(bundle, feat, config.TEST_START)

    # 3) Inference speed: score all 60 wards for one week
    week = feat[feat.date == feat.date.max()]
    t1 = time.perf_counter()
    for _ in range(20):
        predict(bundle, week, config.DEFAULT_HORIZON)
    infer_ms = (time.perf_counter() - t1) / 20 * 1000

    backtest = [] if args.quick else backtest_by_year(feat)
    save_bundle(bundle)

    metrics = {
        "data_hash": data_hash,
        "rows": len(raw),
        "wards": int(raw.ward_id.nunique()),
        "split": {"train": "2016-2022", "validation": str(config.VAL_YEAR), "test": "2024-2025",
                  "shipped_model_trained_through": ship_end},
        "validation": val,
        "test": test,
        "backtest": backtest,
        "lag_correlations": lag_correlations(raw).round(3).to_dict(orient="records"),
        "timing": {"train_shipped_seconds": bundle["train_seconds"],
                   "inference_ms_all_wards": round(infer_ms, 2),
                   "model_file_kb": round(config.MODEL_PATH.stat().st_size / 1024, 1)},
    }
    config.METRICS_PATH.write_text(json.dumps(metrics, indent=2, default=float))

    print(f"Shipped model trained through {ship_end} in {bundle['train_seconds']}s; "
          f"inference {infer_ms:.1f} ms for 60 wards; file {metrics['timing']['model_file_kb']} KB")
    for h in config.HORIZONS:
        t = test[h]
        print(f"  h={h}w  test MAE {t['model']['mae']:.3f} (persistence {t['persistence']['mae']:.3f}, "
              f"last-year {t['last_year']['mae']:.3f})  RMSE {t['model']['rmse']:.3f}  "
              f"High+ recall {t['model']['high_critical_recall']:.0%}  80% PI coverage {t['model']['interval_coverage']:.0%}")
    print(f"Done in {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()

import sys
from pathlib import Path

import numpy as np
import pytest

from dengue.data import load_raw
from dengue.explain import DRIVER_GROUPS, apply_rain_whatif, explain
from dengue.features import add_targets, build_features
from dengue.model import predict, train_bundle, training_rows
from dengue.tiers import tier_of


@pytest.fixture(scope="module")
def feat():
    return add_targets(build_features(load_raw(allow_download=False)))


@pytest.fixture(scope="module")
def bundle(feat):
    return train_bundle(feat, "2021-12-31", horizons=(3,))


def test_training_rows_never_include_future_targets(feat):
    rows = training_rows(feat, 3, end="2021-12-31")
    assert (rows["date"] + np.timedelta64(3, "W")).max() <= np.datetime64("2021-12-31")


def test_predictions_are_valid_intervals(bundle, feat):
    week = feat[feat.date == "2024-08-05"]
    p = predict(bundle, week, 3)
    assert len(p) == 60
    assert (p["lo"] <= p["pred"]).all() and (p["pred"] <= p["hi"]).all() and (p["lo"] >= 0).all()


def test_driver_breakdown_adds_up(bundle, feat):
    week = feat[feat.date == "2024-08-05"]
    e = explain(bundle, week, 3)
    total = e["baseline"] + e[DRIVER_GROUPS].sum(axis=1)
    assert np.allclose(total, e["prediction"])


def test_more_rain_never_lowers_risk(bundle, feat):
    week = feat[feat.date == "2024-06-03"]
    base = predict(bundle, week, 3)["pred"]
    wetter = predict(bundle, apply_rain_whatif(week, 80), 3)["pred"]
    assert (wetter >= base - 1e-9).all()


def test_tiers():
    assert list(tier_of([0, 1.9, 2, 4.9, 5, 9.9, 10, 40])) == [
        "Low", "Low", "Medium", "Medium", "High", "High", "Critical", "Critical"]

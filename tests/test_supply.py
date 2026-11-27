"""Module 1: supply ratios, demand and priority allocation under scarcity."""
import numpy as np
import pandas as pd
import pytest

from dengue import config, supply
from dengue.data import load_raw


@pytest.fixture(scope="module")
def raw():
    return load_raw(allow_download=False)


def fake_forecast(preds, tiers, density):
    n = len(preds)
    return pd.DataFrame({"ward_id": [f"W{i}" for i in range(n)], "city": "Gazipur",
                         "population_density_sqkm": density, "tier": tiers,
                         "tier_rank": [config.TIERS.index(t) for t in tiers],
                         "pred": preds, "lo": np.array(preds) * 0.5, "hi": np.array(preds) * 1.5})


def test_ratios_are_learned_and_match_unseen_years(raw):
    r = supply.learn_ratios(raw)
    assert r["saline_bags_needed"] == pytest.approx(2.38, abs=0.02)
    assert r["diagnostic_kits_needed"] == pytest.approx(1.15, abs=0.02)
    assert r["hospital_beds_required"] == pytest.approx(0.29, abs=0.02)
    test = raw[raw.date >= config.TEST_START]  # 2024-2025, never used to learn the ratios
    for item, k in r.items():
        err = (np.floor(test.dengue_cases * k + 0.5) - test[item]).abs().mean()
        assert err < 0.05, item


def test_bed_capacity_is_positive_for_every_ward(raw):
    cap = supply.bed_capacity(raw)
    assert len(cap) == 60 and (cap >= config.MIN_WARD_BEDS).all()


def test_full_stock_means_no_deficit():
    d = supply.demand(fake_forecast([10, 5, 1], ["Critical", "High", "Low"], [40000] * 3), supply.FALLBACK_RATIOS)
    a, s = supply.allocate(d, 100)
    assert (a["deficit"] == "Fully supplied").all()
    assert s["saline_bags_needed"]["short"] == 0


def test_scarcity_serves_risky_and_dense_wards_first():
    # Same cases, different density: the denser ward must rank first. Critical outranks both.
    fc = fake_forecast([10, 10, 4], ["High", "High", "Critical"], [30000, 70000, 30000])
    a, s = supply.allocate(supply.demand(fc, supply.FALLBACK_RATIOS), 60)
    assert list(a["ward_id"]) == ["W2", "W1", "W0"]
    item = "saline_bags_needed"
    assert a[f"alloc_{item}"].sum() == s[item]["stock"] <= s[item]["need"]
    assert (a[f"alloc_{item}"] <= a[f"need_{item}"]).all()
    # Lifeline: every ward gets at least half before anyone is topped up
    assert (a[f"alloc_{item}"] >= np.ceil(a[f"need_{item}"] * 0.5)).all()
    top, last = a.iloc[0], a.iloc[-1]
    assert top[f"alloc_{item}"] == top[f"need_{item}"]  # top priority topped up to 100%
    assert last[f"alloc_{item}"] < last[f"need_{item}"] and last["deficit"] == "Short"


def test_severe_scarcity_flags_critical_deficits():
    fc = fake_forecast([10, 10, 10, 10], ["High"] * 4, [40000] * 4)
    a, _ = supply.allocate(supply.demand(fc, supply.FALLBACK_RATIOS), 30)
    assert (a["deficit"] == "CRITICAL").any()
    assert a.iloc[0]["fill_pct"] >= 50  # top priority still gets its lifeline


def test_priority_fill_never_exceeds_stock():
    need = pd.Series([7, 3, 0, 12, 5])
    for stock in range(0, 30):
        got = supply.priority_fill(need, stock)
        assert got.sum() == min(stock, need.sum()) and (got <= need).all()

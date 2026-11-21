import numpy as np
import pandas as pd
import pytest

from dengue.data import validate
from dengue.features import FEATURES, add_targets, build_features


def _toy() -> pd.DataFrame:
    dates = pd.date_range("2020-01-06", periods=10, freq="W-MON")
    rows = []
    for ward, base in [("A", 0.0), ("B", 1000.0)]:
        for i, d in enumerate(dates):
            rows.append(dict(
                date=d, city="X", ward_id=ward, population_density_sqkm=1000,
                water_logging_risk_index=0.5, sanitation_score=0.5,
                avg_temp_c=25 + i, max_temp_c=30 + i, min_temp_c=20 + i,
                rainfall_mm=base + i, relative_humidity_pct=70, dengue_cases=i,
            ))
    return validate(pd.DataFrame(rows))


def test_lags_are_per_ward_and_never_cross_wards():
    feat = build_features(_toy())
    b = feat[feat.ward_id == "B"].reset_index(drop=True)
    # First rows of ward B must be NaN, not ward A's last values
    assert np.isnan(b.loc[0, "rain_lag_1"])
    assert np.isnan(b.loc[2, "rain_lag_3"])
    # Lag k of week i equals the same ward's rain at week i-k
    assert b.loc[5, "rain_lag_3"] == 1000 + 2
    assert b.loc[9, "rain_lag_6"] == 1000 + 3


def test_rolling_sums_match_lags():
    feat = build_features(_toy())
    row = feat[feat.ward_id == "A"].iloc[8]
    assert row["rain_sum_4wk"] == pytest.approx(8 + 7 + 6 + 5)


def test_targets_look_forward_within_ward_only():
    feat = add_targets(build_features(_toy()), horizons=(3,))
    a = feat[feat.ward_id == "A"].reset_index(drop=True)
    assert a.loc[0, "target_h3"] == 3
    assert np.isnan(a.loc[8, "target_h3"])  # beyond ward A's history, not ward B's


def test_all_model_features_exist():
    feat = build_features(_toy())
    assert set(FEATURES) <= set(feat.columns)


def test_validate_rejects_missing_columns():
    with pytest.raises(ValueError):
        validate(pd.DataFrame({"date": ["2020-01-01"], "ward_id": ["A"]}))

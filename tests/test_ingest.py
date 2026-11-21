"""Live update path: a new week can be merged, forecast and reset."""
import pandas as pd
import pytest

from dengue import config
from dengue.data import file_hash, load_raw
from dengue.ingest import apply_update, check_update, reset_updates


@pytest.fixture
def sandbox(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "UPDATES_PATH", tmp_path / "updates.csv")
    monkeypatch.setattr(config, "MODEL_PATH", tmp_path / "model.joblib")


def _next_week():
    raw = load_raw(allow_download=False)
    last = raw[raw["date"] == raw["date"].max()].copy()
    last["date"] = last["date"] + pd.Timedelta(weeks=1)
    last["rainfall_mm"] = 150.0
    return last


def test_new_week_is_merged_and_changes_the_data_hash(sandbox):
    before = file_hash()
    week = _next_week()
    s = check_update(week)
    assert s.new_rows == 60 and s.replaced_rows == 0 and not s.new_wards
    apply_update(week)
    raw = load_raw(allow_download=False)
    assert raw["date"].max() == week["date"].max()
    assert file_hash() != before
    reset_updates()
    assert file_hash() == before


def test_resubmitted_week_replaces_old_values(sandbox):
    week = _next_week()
    apply_update(week)
    week["dengue_cases"] = 99
    s = check_update(week)
    assert s.replaced_rows == 60
    apply_update(week)
    raw = load_raw(allow_download=False)
    assert (raw[raw["date"] == week["date"].max()]["dengue_cases"] == 99).all()


def test_bad_file_is_rejected(sandbox):
    with pytest.raises(ValueError):
        check_update(pd.DataFrame({"date": ["2026-01-05"], "rain": [3]}))

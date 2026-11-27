"""Module 3 + the combined plan: crews reduce model forecasts; plan numbers are consistent."""
import pytest

from dengue import config, simulator
from dengue.engine import Engine
from dengue.operations import Settings

AS_OF = "2025-06-02"


@pytest.fixture(scope="module")
def engine():
    return Engine.load()


@pytest.fixture(scope="module")
def effects(engine):
    return engine.crew_effects(AS_OF)


def test_coverage_has_diminishing_returns():
    c = simulator.coverage([0, 1, 2, 3, 4])
    assert c[0] == 0 and c[1] == pytest.approx(0.2)
    gains = c[1:] - c[:-1]
    assert all(a > b for a, b in zip(gains, gains[1:]))


def test_more_crews_never_increase_forecast(effects):
    e = effects.pivot(index="ward_id", columns="crews", values="cases_2to4")
    assert len(e) == 60
    for c in range(config.MAX_CREWS_PER_WARD):
        assert (e[c + 1] <= e[c] + 1e-9).all()
    assert (e[0] - e[1]).max() > 0.5  # the model really responds to less breeding water


def test_best_plan_uses_crews_and_ranks_by_roi(effects, engine):
    plan = simulator.best_plan(effects, 12)
    assert sum(plan.values()) == 12 and max(plan.values()) <= config.MAX_CREWS_PER_WARD
    sim = simulator.simulate(effects, plan, engine.supply_ratios)
    assert (sim["cases_prevented"] > 0).all()
    assert sim["beds_saved"].sum() == pytest.approx(sim["cases_prevented"].sum() * engine.supply_ratios["hospital_beds_required"])
    ranking = simulator.roi_ranking(effects)
    assert ranking["prevented_by_1_crew"].is_monotonic_decreasing
    assert ranking.iloc[0]["ward_id"] in plan  # the best single-crew ward gets a crew


def test_full_plan_is_consistent(engine, effects):
    p = engine.plan(AS_OF, 3, settings=Settings(stock_pct=40, crews=15, beds_pct=60), effects=effects)
    w = p.wards
    assert len(w) == 60 and w["priority"].tolist() == list(range(1, 61))
    assert w["crews_assigned"].sum() == 15
    for item, s in p.supply_summary.items():
        assert w[f"alloc_{item}"].sum() == s["stock"]
    # Overflow stays inside each city and is fully accounted for
    assert (p.transfers.empty or (p.transfers["from_ward"].str[:3] == p.transfers["to_ward"].str[:3]).all())
    assert (w["overflow"] == w["sent_out"] + w["net_bed_deficit"]).all()
    assert len(p.alerts) > 0

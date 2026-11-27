"""Smoke test: every dashboard page and every Actions step renders without an exception (offline)."""
import pytest
from streamlit.testing.v1 import AppTest

from dengue import config

PAGES = ["views/report.py", "views/actions.py", "views/more.py", "views/reality.py", "views/risk_board.py",
         "views/ward_detail.py", "views/heatmap.py", "views/accuracy.py"]
STEPS = ["crews", "supplies", "beds", "notices"]


@pytest.fixture(scope="module")
def app():
    config.ALLOW_NETWORK = config.NETWORK_FROM_ENV = False
    at = AppTest.from_file("../app.py", default_timeout=120).run()
    yield at
    config.ALLOW_NETWORK = config.NETWORK_FROM_ENV = True


def test_report_answers_the_main_question(app):
    assert not app.exception, [e.value for e in app.exception]
    # default replay week: 2 Jun 2025, 3 weeks ahead
    assert app.title[0].value == "46 of 60 wards may reach high dengue risk by 23 June"


def test_ward_priorities_metrics(app):
    app.switch_page("views/risk_board.py").run()
    assert not app.exception, [e.value for e in app.exception]
    assert app.title[0].value == "Which wards need help first"
    assert [m.label for m in app.metric][:2] == ["Critical wards", "High-risk wards"]


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(app, page):
    app.switch_page(page).run()
    assert not app.exception, [e.value for e in app.exception]
    assert app.title, f"{page} rendered no title"


@pytest.mark.parametrize("step", STEPS)
def test_every_action_step_renders(app, step):
    app.switch_page("views/actions.py").run()
    app.session_state["step"] = step
    app.run()
    assert not app.exception, (step, [e.value for e in app.exception])


def test_crew_result_updates_as_soon_as_the_number_changes(app):
    app.switch_page("views/actions.py").run()
    app.session_state["step"] = "crews"
    app.run()

    def answer():
        return next(m.value for m in app.markdown if "dw-answer" in m.value)
    app.number_input(key="act_crews").set_value(5).run()
    few = answer()
    app.number_input(key="act_crews").set_value(40).run()
    assert answer() != few and "40 crews" in answer()


def test_stock_slider_changes_deficit_alerts(app):
    app.switch_page("views/actions.py").run()
    app.session_state["step"] = "supplies"
    app.run()
    app.slider(key="act_stock").set_value(30).run()
    assert any("CRITICAL" in e.value or "Deficit" in e.value for e in [*app.error, *app.warning])
    app.slider(key="act_stock").set_value(100).run()
    assert any("fully supplied" in s.value for s in app.success)


def test_reality_check_switch(app):
    app.switch_page("views/report.py").run()
    app.toggle(key="rc_on").set_value(True).run()
    assert not app.exception, [e.value for e in app.exception]
    assert any("Accuracy: 43 of 52" in m.value for m in app.markdown)
    app.toggle(key="rc_on").set_value(False).run()

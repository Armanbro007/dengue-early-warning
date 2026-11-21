"""Smoke test: every dashboard page renders without an exception (offline)."""
import pytest
from streamlit.testing.v1 import AppTest

from dengue import config

PAGES = ["views/risk_board.py", "views/ward_detail.py", "views/heatmap.py", "views/accuracy.py",
         "views/live_forecast.py", "views/data_update.py"]


@pytest.fixture(scope="module")
def app():
    config.ALLOW_NETWORK = False  # the live page must still work with no network
    at = AppTest.from_file("../app.py", default_timeout=120).run()
    yield at
    config.ALLOW_NETWORK = True


def test_overview_answers_the_main_question(app):
    assert not app.exception, [e.value for e in app.exception]
    assert app.title[0].value == "Dengue outlook for 23 June"  # default replay week: 2 Jun 2025, 3 weeks ahead
    page = " ".join(m.value for m in app.markdown)
    assert "wards likely to reach high dengue risk" in page


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

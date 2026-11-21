"""Smoke test: every dashboard page renders without an exception (offline)."""
import pytest
from streamlit.testing.v1 import AppTest

from dengue import config

PAGES = ["views/ward_detail.py", "views/heatmap.py", "views/accuracy.py", "views/live_forecast.py"]


@pytest.fixture(scope="module")
def app():
    config.ALLOW_NETWORK = False  # the live page must still work with no network
    at = AppTest.from_file("../app.py", default_timeout=120).run()
    yield at
    config.ALLOW_NETWORK = True


def test_risk_board_renders(app):
    assert not app.exception, [e.value for e in app.exception]
    assert app.title[0].value == "Ward Risk Board"
    assert [m.label for m in app.metric][:2] == ["Critical wards", "High wards"]


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(app, page):
    app.switch_page(page).run()
    assert not app.exception, [e.value for e in app.exception]
    assert app.title, f"{page} rendered no title"

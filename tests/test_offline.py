"""Module 5: the offline kill switch. With ALL sockets blocked (no Wi-Fi, no DNS, no API),
forecasting, allocation, bed routing, the crew simulator, dispatch notices, exports and
every dashboard page must still work, with zero crashes."""
import socket

import pytest
from streamlit.testing.v1 import AppTest

from dengue import briefing, config, dispatch
from dengue.engine import Engine
from dengue.operations import Settings

OPS_PAGES = ["views/allocation.py", "views/overflow.py", "views/simulator.py", "views/dispatch.py",
             "views/live_forecast.py", "views/risk_board.py", "views/overview.py"]


class NoInternet(OSError):
    pass


@pytest.fixture()
def no_internet(monkeypatch):
    """Like pulling the network cable: any attempt to connect or resolve a name fails.
    The network setting stays ON, so this tests the failure path, not just the off switch."""
    def boom(*a, **k):
        raise NoInternet("network unreachable (test kill switch)")
    monkeypatch.setattr(socket.socket, "connect", boom)
    monkeypatch.setattr(socket, "getaddrinfo", boom)
    monkeypatch.setattr(socket, "create_connection", boom)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "fake-key-so-the-llm-path-is-tried")
    monkeypatch.setattr(config, "ALLOW_NETWORK", True)
    monkeypatch.setattr(config, "NETWORK_FROM_ENV", True)
    yield


def test_core_math_runs_with_no_internet(no_internet, tmp_path):
    engine = Engine.load()
    plan = engine.plan("2025-06-02", 3, settings=Settings(stock_pct=30, crews=10, beds_pct=50))
    assert len(plan.wards) == 60 and len(plan.alerts) > 0
    assert plan.transfers["patients"].sum() > 0
    paths = dispatch.write_exports(plan, "2025-06-23", tmp_path)
    assert (tmp_path / "commissioner_briefs.html").exists() and len(paths) >= 8


def test_llm_falls_back_to_template_with_no_internet(no_internet):
    fc = Engine.load().forecast("2025-06-02", 3)
    text, source = briefing.get_briefing(briefing.build_facts(fc, "2025-06-02", 3, None), use_llm=True)
    assert text and source.startswith(("template", "cache"))


def test_every_page_renders_with_no_internet(no_internet):
    at = AppTest.from_file("../app.py", default_timeout=180).run()
    assert not at.exception, [e.value for e in at.exception]
    for page in OPS_PAGES:
        at.switch_page(page).run()
        assert not at.exception, (page, [e.value for e in at.exception])
        assert at.title, page


def test_offline_toggle_cuts_network_in_the_app():
    at = AppTest.from_file("../app.py", default_timeout=180).run()
    at.toggle(key="offline").set_value(True).run()
    assert config.ALLOW_NETWORK is False
    at.switch_page("views/allocation.py").run()
    assert not at.exception and any("Offline mode" in i.value for i in at.info)
    at.toggle(key="offline").set_value(False).run()
    assert config.ALLOW_NETWORK is config.NETWORK_FROM_ENV

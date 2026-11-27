"""Module 5: the offline kill switch. With every connection that would leave this computer
blocked (no Wi-Fi, no DNS, no API), forecasting, allocation, bed routing, the crew simulator,
dispatch notices, exports and every dashboard page must still work, with zero crashes."""
import socket

import pytest
from streamlit.testing.v1 import AppTest

from dengue import briefing, config, dispatch
from dengue.engine import Engine
from dengue.operations import Settings

OPS_PAGES = ["views/report.py", "views/actions.py", "views/reality.py", "views/more.py", "views/risk_board.py"]
STEPS = ["crews", "supplies", "beds", "notices"]


class NoInternet(OSError):
    pass


LOOPBACK = ("127.", "::1", "localhost")


def _is_local(host) -> bool:
    if isinstance(host, bytes):
        host = host.decode()
    return host is None or (isinstance(host, str) and host.startswith(LOOPBACK))


@pytest.fixture()
def no_internet(monkeypatch):
    """Like pulling the network cable: any connection or name lookup that would leave this
    computer fails. Loopback (127.0.0.1) keeps working, as it does with Wi-Fi off: the app
    itself is served on localhost, and on Windows asyncio needs it for its internal socket pair.
    The network setting stays ON, so this tests the failure path, not just the off switch."""
    real_connect, real_lookup, real_create = socket.socket.connect, socket.getaddrinfo, socket.create_connection

    def boom(target):
        raise NoInternet(f"network unreachable (test kill switch): {target}")

    def connect(sock, address, *a, **k):
        if sock.family == getattr(socket, "AF_UNIX", None) or _is_local(address[0]):
            return real_connect(sock, address, *a, **k)
        boom(address)

    def getaddrinfo(host, *a, **k):
        return real_lookup(host, *a, **k) if _is_local(host) else boom(host)

    def create_connection(address, *a, **k):
        return real_create(address, *a, **k) if _is_local(address[0]) else boom(address)

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(socket, "create_connection", create_connection)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "fake-key-so-the-llm-path-is-tried")
    monkeypatch.setattr(config, "ALLOW_NETWORK", True)
    monkeypatch.setattr(config, "NETWORK_FROM_ENV", True)
    yield


def test_core_math_runs_with_no_internet(no_internet, tmp_path):
    with pytest.raises(NoInternet):  # the kill switch really blocks the outside world
        socket.create_connection(("api.open-meteo.com", 443), timeout=2)
    with pytest.raises(NoInternet):
        socket.getaddrinfo("generativelanguage.googleapis.com", 443)
    a, b = socket.socketpair()  # while this computer still talks to itself
    a.close()
    b.close()
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
    at.switch_page("views/actions.py").run()
    for step in STEPS:
        at.session_state["step"] = step
        at.run()
        assert not at.exception, (step, [e.value for e in at.exception])


def test_offline_toggle_cuts_network_in_the_app():
    at = AppTest.from_file("../app.py", default_timeout=180).run()
    at.toggle(key="offline").set_value(True).run()
    assert config.ALLOW_NETWORK is False
    at.switch_page("views/actions.py").run()
    at.session_state["step"] = "notices"
    at.run()
    assert not at.exception and any("Offline mode" in i.value for i in at.info)
    at.toggle(key="offline").set_value(False).run()
    assert config.ALLOW_NETWORK is config.NETWORK_FROM_ENV

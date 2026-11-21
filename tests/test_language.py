"""The English/Bangla switch changes the text but keeps the user's settings."""
from streamlit.testing.v1 import AppTest

from dengue import config


def test_switching_language_keeps_settings():
    config.ALLOW_NETWORK = False
    at = AppTest.from_file("../app.py", default_timeout=120).run()
    assert not at.exception
    at.selectbox(key="city_en").set_value("Chattogram")
    at.select_slider(key="as_of_en").set_value("7 Jul 2025").run()

    at.segmented_control(key="lang").set_value("bn").run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.selectbox(key="city_bn").value == "চট্টগ্রাম"
    assert at.select_slider(key="as_of_bn").value == "৭ জুলাই ২০২৫"
    assert "ডেঙ্গু" in at.title[0].value  # Bangla title

    at.segmented_control(key="lang").set_value("en").run()
    assert at.selectbox(key="city_en").value == "Chattogram"
    assert at.select_slider(key="as_of_en").value == "7 Jul 2025"
    assert at.title[0].value == "Dengue outlook for 28 July"
    config.ALLOW_NETWORK = True


def test_every_page_renders_in_bangla():
    config.ALLOW_NETWORK = False
    at = AppTest.from_file("../app.py", default_timeout=120).run()
    at.segmented_control(key="lang").set_value("bn").run()
    for page in ["views/risk_board.py", "views/ward_detail.py", "views/heatmap.py", "views/accuracy.py",
                 "views/live_forecast.py", "views/data_update.py"]:
        at.switch_page(page).run()
        assert not at.exception, (page, [e.value for e in at.exception])
        assert any("ঀ" <= ch <= "৿" for ch in at.title[0].value), f"{page} title is not in Bangla"
    config.ALLOW_NETWORK = True

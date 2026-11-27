"""Module 4: notices carry the plan's numbers, SMS fits 160 chars, exports are written."""
import pandas as pd
import pytest

from dengue import dispatch
from dengue.engine import Engine
from dengue.operations import Settings

WEEK = pd.Timestamp("2025-06-23")


@pytest.fixture(scope="module")
def plan():
    return Engine.load().plan("2025-06-02", 3, settings=Settings(stock_pct=40, crews=12, beds_pct=50))


def test_sms_is_one_plain_message_with_the_numbers(plan):
    for _, r in plan.wards.iterrows():
        text = dispatch.sms(r, WEEK)
        assert len(text) <= dispatch.SMS_LIMIT and text.isascii()
        assert f"Saline {int(r['alloc_saline_bags_needed'])}/{int(r['need_saline_bags_needed'])}" in text


def test_whatsapp_and_brief_list_allocated_vs_required_and_crews(plan):
    r = plan.wards.iloc[0]
    wa = dispatch.whatsapp(r, WEEK)
    assert f"Saline bags: {int(r['alloc_saline_bags_needed'])} / {int(r['need_saline_bags_needed'])}" in wa
    assert f"{int(r['crews_assigned'])} assigned" in wa
    page = dispatch.brief_html(plan.wards.head(3), WEEK)
    assert page.count("class=page") == 3 and "Spraying crews" in page and "Deficit" in page


def test_critical_status_when_city_has_no_beds(plan):
    no_bed = plan.wards[plan.wards["net_bed_deficit"] > 0]
    assert len(no_bed), "50% beds free should leave some patients without a bed"
    r = no_bed.iloc[0]
    assert "CRITICAL" in dispatch.sms(r, WEEK) and "NO BED" in dispatch.whatsapp(r, WEEK)


def test_bangla_sms_uses_bangla_digits(plan):
    text = dispatch.sms_bangla(plan.wards.iloc[0], WEEK)
    assert "ডেঙ্গুওয়াচ" in text and not any(ch.isdigit() and ch.isascii() for ch in text)


def test_exports_written(plan, tmp_path):
    paths = dispatch.write_exports(plan, WEEK, tmp_path)
    names = {p.name for p in paths}
    assert {"sms_messages.csv", "whatsapp_messages.txt", "commissioner_briefs.html", "manifest.json"} <= names
    assert len(pd.read_csv(tmp_path / "sms_messages.csv")) == 60

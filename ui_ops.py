"""Shared pieces of the four command-center pages: resource controls and the cached plan."""
from __future__ import annotations

import pandas as pd
import streamlit as st

import ui_text as tx
from dengue import config
from dengue.operations import Plan, Settings
from ui_common import get_engine, html


def L(en: str, bn: str) -> str:
    """Pick the text for the current language."""
    return bn if tx.lang() == "bn" else en


def ops_controls() -> Settings:
    """Scarcity controls in the sidebar. Plain numbers, so they survive language and page changes."""
    sb, ss = st.sidebar, st.session_state
    # Widget state is dropped when the page changes, so the chosen values live in "v_" keys:
    # a change is copied there at once (on_change), and every page's widget starts from it.
    for k, v in (("ops_stock", 60), ("ops_crews", 20), ("ops_beds", 80), ("ops_cautious", False)):
        ss.setdefault(f"v_{k}", v)
        ss[k] = ss[f"v_{k}"]

    def keep(k):
        return dict(key=k, on_change=lambda: ss.__setitem__(f"v_{k}", ss[k]))
    html(f'<div class="dw-side-label">{L("Resources on hand", "হাতে থাকা সম্পদ")}</div>', sb)
    stock = sb.slider(L("Regional stock (% of need)", "আঞ্চলিক মজুত (চাহিদার %)"), 30, 100, step=5, **keep("ops_stock"),
                      help=L("Saline and test kits in the regional store, as a share of what all wards need.",
                             "সব ওয়ার্ডের মোট চাহিদার কত শতাংশ স্যালাইন ও কিট মজুত আছে।"))
    crews = sb.number_input(L("Spraying crews available", "স্প্রে দল সংখ্যা"), 0, 240, step=1, **keep("ops_crews"),
                            help=L("Larvicide / fogging teams you can send this week (max 4 per ward).",
                                   "এ সপ্তাহে পাঠানো যায় এমন লার্ভিসাইড/ফগিং দল (প্রতি ওয়ার্ডে সর্বোচ্চ ৪টি)।"))
    beds = sb.slider(L("Dengue beds free (% of usual)", "খালি ডেঙ্গু শয্যা (স্বাভাবিকের %)"), 30, 100, step=5,
                     **keep("ops_beds"), help=L("Share of each ward's usual dengue beds that is free this week.",
                                            "প্রতিটি ওয়ার্ডের স্বাভাবিক ডেঙ্গু শয্যার কত শতাংশ খালি।"))
    cautious = sb.toggle(L("Plan for a bad week", "খারাপ সপ্তাহ ধরে পরিকল্পনা"), **keep("ops_cautious"),
                         help=L("Use the top of the forecast range instead of the expected number.",
                                "প্রত্যাশিত সংখ্যার বদলে পূর্বাভাসের ঊর্ধ্বসীমা ধরে হিসাব।"))
    return Settings(float(stock), int(crews), float(beds), bool(cautious))


@st.cache_data(show_spinner=False, max_entries=64)
def cached_effects(as_of: str, city: str | None) -> pd.DataFrame:
    return get_engine().crew_effects(as_of, city)


@st.cache_data(show_spinner=False, max_entries=128)
def cached_plan(as_of: str, h: int, city: str | None, stock: float, crews: int, beds: float, cautious: bool) -> Plan:
    return get_engine().plan(as_of, h, city, Settings(stock, crews, beds, cautious), effects=cached_effects(as_of, city))


def current_plan() -> tuple[Plan, dict, pd.Timestamp]:
    """(plan, shared controls, target week) for the page being shown."""
    c = st.session_state["controls"]
    s = ops_controls()
    plan = cached_plan(str(c["as_of"].date()), c["horizon"], c["city"], s.stock_pct, s.crews, s.beds_pct, s.cautious)
    return plan, c, c["as_of"] + pd.Timedelta(weeks=c["horizon"])


def ward(w: str) -> str:
    return tx.ward(w)


def offline_badge() -> None:
    if not config.ALLOW_NETWORK:
        st.info(L("Offline mode: no internet is used. Forecasts, allocation, routing and notices all run on this computer.",
                  "অফলাইন মোড: কোনো ইন্টারনেট লাগছে না। পূর্বাভাস, বণ্টন, রোগী স্থানান্তর ও নোটিশ সব এই কম্পিউটারেই চলছে।"),
                icon=":material/wifi_off:")

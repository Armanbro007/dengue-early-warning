"""DengueWatch entry point.  Run:  streamlit run app.py

Two main tabs: Report (what is coming, ward by ward) and Actions (what to do about it, step by step).
Everything else sits under More."""
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="DengueWatch", page_icon=str(Path(__file__).parent / "static" / "favicon.png"),
                   layout="wide", initial_sidebar_state="collapsed")

import ui_text as tx  # noqa: E402
from ui_common import get_engine, inject_css  # noqa: E402
from ui_reality import panel, toggle  # noqa: E402
from ui_shell import L, shell  # noqa: E402

inject_css()

MAIN = [
    st.Page("views/report.py", title=L("Report", "রিপোর্ট"), icon=":material/monitoring:", default=True),
    st.Page("views/actions.py", title=L("Actions", "পদক্ষেপ"), icon=":material/task_alt:"),
    st.Page("views/more.py", title=L("More", "আরও"), icon=":material/apps:"),
]
MORE = [  # reached from the More tab
    st.Page("views/risk_board.py", title=tx.t("page_wards"), icon=":material/format_list_numbered:"),
    st.Page("views/ward_detail.py", title=tx.t("page_why"), icon=":material/help:"),
    st.Page("views/heatmap.py", title=tx.t("page_calendar"), icon=":material/calendar_month:"),
    st.Page("views/accuracy.py", title=tx.t("page_accuracy"), icon=":material/verified:"),
    st.Page("views/reality.py", title=L("Reality check", "বাস্তবের সঙ্গে মিলিয়ে দেখা"), icon=":material/fact_check:"),
]
pages = st.navigation(MAIN + MORE, position="hidden")  # registered before the (slow, first-run) model load
engine = get_engine()
st.session_state["controls"] = shell(engine, MAIN, pages)
toggle()  # floating "Reality check" switch, bottom right
pages.run()
panel()  # its comparison card, only while the switch is on

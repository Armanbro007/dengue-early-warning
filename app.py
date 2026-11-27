"""DengueWatch dashboard entry point.  Run:  streamlit run app.py"""
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="DengueWatch", page_icon=str(Path(__file__).parent / "static" / "favicon.png"), layout="wide")

import ui_text as tx  # noqa: E402
from ui_common import brand, engine_footer, get_engine, html, inject_css, sidebar_controls, top_bar  # noqa: E402

inject_css()

SECTIONS = {
    "nav_early": [
        st.Page("views/overview.py", title=tx.t("page_overview"), icon=":material/space_dashboard:", default=True),
        st.Page("views/risk_board.py", title=tx.t("page_wards"), icon=":material/format_list_numbered:"),
        st.Page("views/ward_detail.py", title=tx.t("page_why"), icon=":material/help:"),
        st.Page("views/heatmap.py", title=tx.t("page_calendar"), icon=":material/calendar_month:"),
    ],
    "nav_ops": [
        st.Page("views/allocation.py", title=tx.t("page_alloc"), icon=":material/inventory_2:"),
        st.Page("views/overflow.py", title=tx.t("page_beds"), icon=":material/local_hospital:"),
        st.Page("views/simulator.py", title=tx.t("page_sim"), icon=":material/pest_control:"),
        st.Page("views/dispatch.py", title=tx.t("page_dispatch"), icon=":material/send:"),
    ],
    "nav_more": [
        st.Page("views/live_forecast.py", title=tx.t("page_live"), icon=":material/cloud:"),
        st.Page("views/accuracy.py", title=tx.t("page_accuracy"), icon=":material/verified:"),
        st.Page("views/data_update.py", title=tx.t("page_data"), icon=":material/upload_file:"),
    ],
}
pages = st.navigation(SECTIONS, position="hidden")  # registered before the (slow, first-run) model load
engine = get_engine()
top_bar()

with st.sidebar:
    html(brand())
    for name, items in SECTIONS.items():
        html(f'<div class="dw-side-label">{tx.t(name)}</div>')
        for p in items:
            with st.container(key=f"nav_{p.url_path or 'home'}"):
                st.page_link(p)
    cur = pages.url_path or "home"  # highlight the current page as a dark pill
    html(f'<style>.st-key-nav_{cur} a{{background:#111318 !important;}} .st-key-nav_{cur} a span{{color:#fff !important;}}</style>')
st.session_state["controls"] = sidebar_controls(engine)
engine_footer(engine)
pages.run()

"""DengueWatch dashboard entry point.  Run:  streamlit run app.py"""
import streamlit as st

st.set_page_config(page_title="DengueWatch", page_icon=":material/water_drop:", layout="wide")

from ui_common import BRAND, engine_footer, get_engine, inject_css, sidebar_controls  # noqa: E402

inject_css()
engine = get_engine()

SECTIONS = {
    "Early warning": [
        st.Page("views/overview.py", title="Overview", icon=":material/home:", default=True),
        st.Page("views/risk_board.py", title="Ward priorities", icon=":material/format_list_numbered:"),
        st.Page("views/ward_detail.py", title="Why this ward?", icon=":material/help:"),
        st.Page("views/heatmap.py", title="Season calendar", icon=":material/calendar_month:"),
    ],
    "More": [
        st.Page("views/live_forecast.py", title="Live forecast", icon=":material/cloud:"),
        st.Page("views/accuracy.py", title="How accurate is it?", icon=":material/verified:"),
        st.Page("views/data_update.py", title="Add weekly data", icon=":material/upload_file:"),
    ],
}
pages = st.navigation(SECTIONS, position="hidden")

# Sidebar: brand first, then our own navigation, then the shared settings.
with st.sidebar:
    st.markdown("".join(x.strip() for x in BRAND.splitlines()), unsafe_allow_html=True)
    for name, items in SECTIONS.items():
        st.markdown(f'<div class="dw-side-label">{name}</div>', unsafe_allow_html=True)
        for p in items:
            st.page_link(p)
st.session_state["controls"] = sidebar_controls(engine)
engine_footer(engine)
pages.run()

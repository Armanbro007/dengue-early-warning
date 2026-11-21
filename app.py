"""DengueWatch dashboard entry point.  Run:  streamlit run app.py"""
import streamlit as st

st.set_page_config(page_title="DengueWatch", page_icon="🦟", layout="wide")

from ui_common import engine_footer, get_engine, sidebar_controls  # noqa: E402

engine = get_engine()

pages = st.navigation(
    {
        "Early warning": [
            st.Page("views/risk_board.py", title="Ward Risk Board", icon=":material/warning:", default=True),
            st.Page("views/ward_detail.py", title="Ward Drivers & What-if", icon=":material/insights:"),
            st.Page("views/heatmap.py", title="Season Heatmap", icon=":material/grid_on:"),
        ],
        "Live & validation": [
            st.Page("views/live_forecast.py", title="Live Forecast (API)", icon=":material/cloud:"),
            st.Page("views/accuracy.py", title="Model Accuracy", icon=":material/fact_check:"),
        ],
    }
)

st.sidebar.markdown("## 🦟 DengueWatch")
st.sidebar.caption("Ward-level dengue early warning, 2-4 weeks ahead")
st.session_state["controls"] = sidebar_controls(engine)
engine_footer(engine)
pages.run()

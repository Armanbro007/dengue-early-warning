"""Shared Streamlit helpers: cached engine, sidebar state, chart styling."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from dengue import config  # noqa: E402
from dengue.engine import Engine  # noqa: E402

TIER_COLORS = config.TIER_COLORS
INK, INK2, MUTED, GRID, AXIS = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
BLUE = "#2a78d6"
DRIVER_COLORS = {  # categorical slots in fixed order
    "Rainfall (0-6 wks ago)": "#2a78d6",
    "Humidity": "#1baf7a",
    "Temperature": "#eb6834",
    "Ward vulnerability": "#6250d6",
}


@st.cache_resource(show_spinner="Loading data and models...")
def get_engine() -> Engine:
    return Engine.load()


@st.cache_data(show_spinner=False, max_entries=256)
def cached_forecast(as_of: str, h: int, city: str | None, extra_rain: float = 0.0) -> pd.DataFrame:
    return get_engine().forecast(as_of, h, city, extra_rain)


def style_fig(fig: go.Figure, height: int = 360, legend: bool = True) -> go.Figure:
    fig.update_layout(
        height=height, margin=dict(l=8, r=8, t=84 if legend else 44, b=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#fcfcfb",
        font=dict(color=INK2, size=13), hoverlabel=dict(bgcolor="white", font_color=INK),
        showlegend=legend, legend=dict(orientation="h", yanchor="bottom", y=1.01, x=0, title=None),
        title=dict(font=dict(color=INK, size=15), x=0, xanchor="left", y=0.98, yanchor="top", pad=dict(l=4)),
    )
    fig.update_xaxes(gridcolor=GRID, linecolor=AXIS, zeroline=False, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, linecolor=AXIS, zeroline=False, tickfont=dict(color=MUTED))
    return fig


def tier_badge(tier: str) -> str:
    color = TIER_COLORS[tier]
    ink = "#0b0b0b" if tier == "Medium" else "#ffffff"
    return (f"<span style='background:{color};color:{ink};padding:2px 10px;border-radius:999px;"
            f"font-weight:600;font-size:0.85rem'>{tier}</span>")


def fmt_week(ts) -> str:
    return pd.Timestamp(ts).strftime("%d %b %Y")


def sidebar_controls(engine: Engine) -> dict:
    """Controls shared by every page (kept in session state across pages)."""
    weeks = engine.forecast_weeks()
    # Default: 2 June 2025, just before the 2025 season took off (all wards still Low).
    demo = pd.Timestamp("2025-06-02")
    default_week = demo if demo in weeks else weeks[-1]
    st.sidebar.markdown("### Forecast settings")
    city = st.sidebar.selectbox("City corporation", ["All cities", *engine.cities], key="city")
    if "as_of" not in st.session_state:
        st.session_state["as_of"] = default_week
    as_of = st.sidebar.select_slider(
        "Issue forecast on week of", options=weeks, format_func=fmt_week, key="as_of",
        help="The dashboard replays history: pick any week and see what the system would have said.",
    )
    horizon = st.sidebar.radio(
        "Forecast horizon", config.HORIZONS, index=config.HORIZONS.index(config.DEFAULT_HORIZON),
        format_func=lambda h: f"{h} weeks ahead", horizontal=True, key="horizon",
    )
    unseen = pd.Timestamp(as_of) > engine.train_end
    st.sidebar.caption(
        ("Replaying a week the model never saw during training (2024-2025 hold-out)."
         if unseen else "Note: this week is inside the training period (2016-2023).")
    )
    return {"city": None if city == "All cities" else city, "city_label": city,
            "as_of": pd.Timestamp(as_of), "horizon": int(horizon), "unseen": unseen}


def engine_footer(engine: Engine) -> None:
    from dengue.briefing import llm_status
    from dengue.http import STATS

    b = engine.bundle
    llm = llm_status()
    with st.sidebar.expander("Efficiency & system status"):
        st.markdown(
            f"- Models: joblib, trained through **{b['train_end']}** in {b['train_seconds']} s\n"
            f"- Data + model load: **{engine.load_seconds * 1000:.0f} ms** (once per server)\n"
            f"- External API calls this session: **{STATS.calls}** (retries {STATS.retries}, failures {STATS.failures})\n"
            f"- LLM briefing: **{'on, ' + llm['model'] if llm['enabled'] else 'off (template)'}**; "
            f"today {llm['calls']}/{llm['budget']} calls, {llm['input_tokens'] + llm['output_tokens']} tokens"
        )

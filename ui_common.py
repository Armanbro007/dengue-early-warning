"""Shared Streamlit helpers: cached engine, design system, sidebar and chart styling."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from dengue import config  # noqa: E402
from dengue.engine import Engine  # noqa: E402

# ---- Design tokens ("Calm light") --------------------------------------------
INK, INK2, MUTED = "#1F2926", "#5E6A66", "#8A938F"
GRID, AXIS, SURFACE = "#EEEBE4", "#D9D5CC", "#FFFFFF"
ACCENT, ACCENT_SOFT = "#1F6F6A", "#E6F0EE"
RAIN = "#3F7FA6"            # rainfall bars
UP, DOWN = "#C0573A", ACCENT  # "pushes risk up" / "pulls risk down"
SANS = "'Plus Jakarta Sans', 'Segoe UI', system-ui, sans-serif"
SERIF = "Newsreader, Georgia, 'Times New Roman', serif"
TIER_COLORS = config.TIER_COLORS  # chart fills, always shown with the tier name
BLUE = RAIN  # kept for older imports

# Plain-language names for the model's driver groups.
DRIVER_LABELS = {
    "Rainfall (0-6 wks ago)": "Recent rain",
    "Humidity": "Humidity",
    "Temperature": "Temperature",
    "Ward vulnerability": "Drainage, crowding & sanitation",
    "Seasonal norm": "Normal for the season",
}
TIER_MEANING = {
    "Low": "fewer than 2 cases a week",
    "Medium": "2 to 5 cases a week",
    "High": "5 to 10 cases a week",
    "Critical": "10 or more cases a week",
}

_ICON_PATHS = {
    "rain": '<path d="M16.5 14.5h.5a3.5 3.5 0 0 0 .5-6.97A5.5 5.5 0 0 0 6.6 8.3 3.6 3.6 0 0 0 7 15.5"/>'
            '<path d="M8.5 17.5 7.5 20M12.5 16.5l-1 2.5M16.5 17.5l-1 2.5"/>',
    "clock": '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    "pulse": '<path d="M3 12h4l2.2-5 4.4 10 2.2-5H21"/>',
    "bell": '<path d="M6 16.5V11a6 6 0 0 1 12 0v5.5l1.5 1.5h-15z"/><path d="M10 20.5a2 2 0 0 0 4 0"/>',
    "drop": '<path d="M12 3.5s6 6.4 6 10.5a6 6 0 0 1-12 0c0-4.1 6-10.5 6-10.5z"/>',
    "check": '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
}


def icon(name: str, size: int = 22) -> str:
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            f'{_ICON_PATHS[name]}</svg>')


CSS = """
<style>
:root{
  --dw-bg:#FBFAF7; --dw-surface:#FFFFFF; --dw-ink:#1F2926; --dw-ink2:#5E6A66; --dw-muted:#8A938F;
  --dw-line:rgba(31,41,38,.09); --dw-line2:rgba(31,41,38,.14);
  --dw-accent:#1F6F6A; --dw-accent-soft:#E6F0EE;
  --dw-serif:Newsreader, Georgia, 'Times New Roman', serif;
  --dw-ease:cubic-bezier(.16,1,.3,1);
}
/* Streamlit chrome: keep it quiet */
[data-testid="stToolbarActions"], [data-testid="stMainMenu"], [data-testid="stAppDeployButton"],
.stAppDeployButton, #MainMenu, footer, [data-testid="stDecoration"], [data-testid="stStatusWidget"] {display:none !important;}
header[data-testid="stHeader"]{background:transparent;}
[data-testid="stMainBlockContainer"]{max-width:1240px; padding-top:2.6rem; padding-bottom:5rem;}
/* Typography */
h1{letter-spacing:-0.025em; line-height:1.08 !important; font-size:clamp(2.1rem, 3.6vw, 3rem) !important;
   text-wrap:balance; font-weight:500 !important; padding-top:.2rem !important;}
h2{letter-spacing:-0.015em; font-size:1.65rem !important; text-wrap:balance;}
h3{letter-spacing:-0.01em; font-size:1.3rem !important;}
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li{line-height:1.65;}
[data-testid="stCaptionContainer"]{color:var(--dw-ink2) !important;}
/* Metric tiles */
[data-testid="stMetric"]{background:var(--dw-surface); border:1px solid var(--dw-line); border-radius:14px;
  padding:16px 18px 14px; transition:box-shadow .25s var(--dw-ease);}
[data-testid="stMetric"]:hover{box-shadow:0 2px 12px rgba(31,41,38,.05);}
[data-testid="stMetricLabel"] p{color:var(--dw-ink2); font-size:.86rem; font-weight:500;}
[data-testid="stMetricValue"]{font-family:var(--dw-serif); font-size:2.15rem !important; letter-spacing:-0.02em;}
/* Bordered containers become calm cards */
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]){border-radius:14px;}
[data-testid="stExpander"] details{border-radius:12px; border-color:var(--dw-line2); background:var(--dw-surface);}
[data-testid="stPlotlyChart"]{background:var(--dw-surface); border:1px solid var(--dw-line); border-radius:14px; padding:6px 8px 2px;}
[data-testid="stDataFrame"]{border-radius:12px; overflow:hidden;}
button[kind="primary"], [data-testid="stBaseButton-primary"]{transition:transform .15s var(--dw-ease);}
button:active{transform:scale(.98);}
[data-testid="stMainBlockContainer"] [data-testid="stPageLink"] a{background:var(--dw-surface); border:1px solid var(--dw-line);
  border-radius:12px; padding:14px 16px; transition:box-shadow .25s var(--dw-ease), border-color .25s var(--dw-ease);}
[data-testid="stMainBlockContainer"] [data-testid="stPageLink"] a:hover{border-color:var(--dw-accent); box-shadow:0 4px 18px rgba(31,41,38,.06);}
[data-testid="stMainBlockContainer"] [data-testid="stPageLink"] a span{color:var(--dw-ink); font-weight:500;}
/* Sidebar */
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"]{padding-top:1.2rem;}
section[data-testid="stSidebar"] [data-testid="stPageLink"] a{border-radius:8px; padding:5px 10px; margin:1px 0;}
section[data-testid="stSidebar"] [data-testid="stPageLink"] a span{font-size:.93rem;}
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p{font-weight:600; font-size:.86rem;}
.dw-brand{display:flex; align-items:center; gap:10px; margin:0 0 4px 2px;}
.dw-brand-mark{width:34px; height:34px; border-radius:10px; background:var(--dw-accent); color:#fff;
  display:flex; align-items:center; justify-content:center; flex:none;}
.dw-brand-name{font-family:var(--dw-serif); font-size:1.42rem; font-weight:600; color:var(--dw-ink); letter-spacing:-0.01em; line-height:1.1;}
.dw-brand-tag{font-size:.78rem; color:var(--dw-ink2); line-height:1.35; margin-top:2px;}
.dw-side-label{font-size:.7rem; text-transform:uppercase; letter-spacing:.14em; color:var(--dw-muted); font-weight:600; margin:14px 0 2px 10px;}
.dw-side-note{font-size:.8rem; line-height:1.5; color:var(--dw-ink2); background:var(--dw-surface);
  border:1px solid var(--dw-line); border-radius:10px; padding:10px 12px; margin-top:6px;}
.dw-side-note b{color:var(--dw-ink);}
/* Page header */
.dw-eyebrow{display:inline-flex; align-items:center; gap:6px; font-size:.7rem; letter-spacing:.14em; text-transform:uppercase;
  font-weight:600; color:var(--dw-accent); background:var(--dw-accent-soft); border-radius:999px; padding:4px 11px; margin-bottom:2px;}
.dw-lead{font-size:1.1rem; line-height:1.6; color:var(--dw-ink2); max-width:70ch; margin:-.2rem 0 1.4rem; text-wrap:pretty;}
.dw-lead b{color:var(--dw-ink); font-weight:600;}
.dw-section{font-family:var(--dw-serif); font-size:1.5rem; font-weight:500; letter-spacing:-0.015em; color:var(--dw-ink); margin:2.4rem 0 .2rem;}
.dw-section-sub{color:var(--dw-ink2); font-size:.95rem; margin:0 0 1rem; max-width:72ch;}
/* Cards and grids */
.dw-grid{display:grid; gap:14px; grid-template-columns:repeat(auto-fit, minmax(210px, 1fr));}
.dw-grid.wide{grid-template-columns:repeat(auto-fit, minmax(300px, 1fr));}
.dw-card{background:var(--dw-surface); border:1px solid var(--dw-line); border-radius:14px; padding:18px 20px;
  transition:box-shadow .25s var(--dw-ease), transform .25s var(--dw-ease);}
.dw-card:hover{box-shadow:0 4px 18px rgba(31,41,38,.06);}
.dw-card h4{font-family:var(--dw-serif); font-weight:600; font-size:1.18rem; margin:0 0 2px; padding:0; color:var(--dw-ink); letter-spacing:-0.01em;}
.dw-meta{font-size:.82rem; color:var(--dw-ink2);}
.dw-big{font-family:var(--dw-serif); font-size:2rem; line-height:1.1; color:var(--dw-ink); letter-spacing:-0.02em; font-weight:500;}
.dw-big small{font-family:'Plus Jakarta Sans', system-ui, sans-serif; font-size:.88rem; color:var(--dw-ink2); letter-spacing:0; margin-left:2px;}
.dw-big .of{font-size:1.15rem; color:var(--dw-muted);}
.dw-grid.five{grid-template-columns:repeat(5, minmax(0, 1fr));}
.dw-change{display:flex; align-items:flex-end; gap:10px; margin:12px 0 14px;}
.dw-change .k{font-size:.72rem; color:var(--dw-muted); margin-bottom:3px;}
.dw-change .ar{color:var(--dw-muted); padding-bottom:2px;}
.dw-row{display:flex; align-items:center; gap:8px; flex-wrap:wrap;}
.dw-sep{color:var(--dw-muted);}
.dw-reason{margin-top:12px; padding-top:10px; border-top:1px solid var(--dw-line); font-size:.85rem; color:var(--dw-ink2);}
.dw-reason b{color:var(--dw-ink); font-weight:600;}
/* Tier pills (soft tint + name, never colour alone) */
.dw-pill{display:inline-flex; align-items:center; gap:6px; border-radius:999px; padding:2px 10px 2px 8px; font-size:.78rem; font-weight:600; white-space:nowrap; line-height:1.6;}
.dw-pill::before{content:""; width:7px; height:7px; border-radius:50%; background:currentColor; opacity:.85;}
.dw-pill.t-Low{background:#EAF3EC; color:#2F6B3F;}
.dw-pill.t-Medium{background:#FBF1D9; color:#7F5A0C;}
.dw-pill.t-High{background:#FBE7DC; color:#A2441C;}
.dw-pill.t-Critical{background:#F8E3E5; color:#8E2833;}
/* Stacked tier bar */
.dw-stack{display:flex; gap:2px; height:10px; border-radius:999px; overflow:hidden; background:#F1EEE8; margin:12px 0 8px;}
.dw-stack span{display:block; height:100%;}
.dw-legend{display:flex; flex-wrap:wrap; gap:6px 16px; font-size:.82rem; color:var(--dw-ink2); margin-top:10px;}
/* How-it-works steps */
.dw-steps{display:grid; grid-template-columns:repeat(4, 1fr); gap:14px;}
.dw-step{position:relative; background:var(--dw-surface); border:1px solid var(--dw-line); border-radius:14px; padding:18px 18px 16px;}
.dw-step .ic{width:40px; height:40px; border-radius:12px; background:var(--dw-accent-soft); color:var(--dw-accent);
  display:flex; align-items:center; justify-content:center; margin-bottom:12px;}
.dw-step .when{font-size:.7rem; letter-spacing:.12em; text-transform:uppercase; color:var(--dw-muted); font-weight:600;}
.dw-step .what{font-family:var(--dw-serif); font-size:1.15rem; color:var(--dw-ink); font-weight:600; margin:2px 0 4px;}
.dw-step p{font-size:.86rem; color:var(--dw-ink2); line-height:1.5; margin:0;}
.dw-step.hl{background:var(--dw-accent); border-color:var(--dw-accent);}
.dw-step.hl .ic{background:rgba(255,255,255,.14); color:#fff;}
.dw-step.hl .when{color:rgba(255,255,255,.7);} .dw-step.hl .what{color:#fff;} .dw-step.hl p{color:rgba(255,255,255,.85);}
/* Callout */
.dw-callout{display:flex; gap:12px; align-items:flex-start; background:var(--dw-surface); border:1px solid var(--dw-line);
  border-left:3px solid var(--dw-accent); border-radius:10px; padding:12px 16px; color:var(--dw-ink2); font-size:.93rem; max-width:860px;}
.dw-callout svg{color:var(--dw-accent); flex:none; margin-top:2px;}
.dw-callout b{color:var(--dw-ink);}
/* Reason bars (driver breakdown) */
.dw-bars{display:flex; flex-direction:column; gap:10px;}
.dw-bar{display:grid; grid-template-columns:minmax(150px, 1.1fr) 2fr 84px; align-items:center; gap:12px; font-size:.9rem;}
.dw-bar .lbl{color:var(--dw-ink);}
.dw-bar .trk{position:relative; height:12px; background:#F3F0EA; border-radius:999px;}
.dw-bar .trk::after{content:""; position:absolute; left:50%; top:-4px; bottom:-4px; width:1px; background:var(--dw-line2);}
.dw-bar .fill{position:absolute; top:0; bottom:0; border-radius:999px;}
.dw-bar .val{text-align:right; font-variant-numeric:tabular-nums; color:var(--dw-ink2); font-weight:600;}
.dw-bar.total{border-top:1px solid var(--dw-line); padding-top:10px;}
.dw-bar.total .lbl, .dw-bar.total .val{color:var(--dw-ink); font-weight:700;}
/* Gentle entry motion */
@media (prefers-reduced-motion: no-preference){
  .dw-card, .dw-step, .dw-callout{animation:dw-up .6s var(--dw-ease) both;}
  .dw-grid > *:nth-child(2), .dw-steps > *:nth-child(2){animation-delay:.06s;}
  .dw-grid > *:nth-child(3), .dw-steps > *:nth-child(3){animation-delay:.12s;}
  .dw-grid > *:nth-child(4), .dw-steps > *:nth-child(4){animation-delay:.18s;}
  .dw-grid > *:nth-child(n+5){animation-delay:.24s;}
  @keyframes dw-up{from{opacity:0; transform:translateY(10px);} to{opacity:1; transform:none;}}
}
@media (max-width: 1100px){ .dw-grid.five{grid-template-columns:repeat(3, minmax(0, 1fr));} }
@media (max-width: 900px){ .dw-steps{grid-template-columns:repeat(2, 1fr);} }
@media (max-width: 560px){ .dw-steps, .dw-grid.five{grid-template-columns:1fr;} .dw-bar{grid-template-columns:1fr 1.4fr 64px;} }
</style>
"""


def inject_css() -> None:
    st.html(CSS)


def html(s: str) -> None:
    """Render an HTML snippet. Lines are joined so Markdown never treats indentation as code."""
    st.markdown("".join(line.strip() for line in s.splitlines()), unsafe_allow_html=True)


# ---- Formatting helpers -------------------------------------------------------
def fmt_week(ts) -> str:
    return pd.Timestamp(ts).strftime("%d %b %Y").lstrip("0")


def fmt_day(ts) -> str:
    t = pd.Timestamp(ts)
    return f"{t.day} {t:%B}"


def ward_name(ward_id: str) -> str:
    return str(ward_id).replace("_", " ")


def driver_name(group: str) -> str:
    return DRIVER_LABELS.get(group, group)


def about(x: float) -> str:
    x = float(x)
    return "less than 1" if x < 1 else f"{round(x):.0f}"


def case_range(lo: float, hi: float) -> str:
    return f"{math.floor(max(lo, 0)):.0f}–{math.ceil(hi):.0f}"


def tier_pill(tier: str) -> str:
    return f'<span class="dw-pill t-{tier}">{tier}</span>'


tier_badge = tier_pill  # older name


def page_header(eyebrow: str, title: str, lead: str = "") -> None:
    html(f'<span class="dw-eyebrow">{eyebrow}</span>')
    st.title(title, anchor=False)
    if lead:
        html(f'<p class="dw-lead">{lead}</p>')


def section(title: str, sub: str = "") -> None:
    html(f'<div class="dw-section">{title}</div>' + (f'<p class="dw-section-sub">{sub}</p>' if sub else ""))


def tier_legend() -> str:
    return ('<div class="dw-legend">' + "".join(
        f'<span>{tier_pill(t)} {TIER_MEANING[t]}</span>' for t in config.TIERS) + "</div>")


# ---- Data access --------------------------------------------------------------
@st.cache_resource(show_spinner="Loading data and models...")
def get_engine() -> Engine:
    return Engine.load()


@st.cache_data(show_spinner=False, max_entries=256)
def cached_forecast(as_of: str, h: int, city: str | None, extra_rain: float = 0.0) -> pd.DataFrame:
    return get_engine().forecast(as_of, h, city, extra_rain)


# ---- Charts -------------------------------------------------------------------
def style_fig(fig: go.Figure, height: int = 360, legend: bool = True) -> go.Figure:
    has_title = bool(fig.layout.title.text)
    fig.update_layout(
        height=height, margin=dict(l=8, r=12, t=(78 if legend else 52) if has_title else (40 if legend else 12), b=8),
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        font=dict(family=SANS, color=INK2, size=13),
        hoverlabel=dict(bgcolor="white", bordercolor=AXIS, font=dict(family=SANS, color=INK, size=13)),
        showlegend=legend, legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, title=None, font=dict(size=12)),
        title=dict(font=dict(family=SERIF, color=INK, size=19), x=0.01, xanchor="left", y=0.97, yanchor="top"),
    )
    fig.update_xaxes(gridcolor=GRID, linecolor=AXIS, zeroline=False, tickfont=dict(color=MUTED, size=12),
                     title_font=dict(size=12, color=INK2))
    fig.update_yaxes(gridcolor=GRID, linecolor="rgba(0,0,0,0)", zeroline=False, tickfont=dict(color=MUTED, size=12),
                     title_font=dict(size=12, color=INK2))
    return fig


def tier_cell_style(v) -> str:
    soft = {"Low": ("#EAF3EC", "#2F6B3F"), "Medium": ("#FBF1D9", "#7F5A0C"),
            "High": ("#FBE7DC", "#A2441C"), "Critical": ("#F8E3E5", "#8E2833")}
    if v not in soft:
        return ""
    bg, fg = soft[v]
    return f"background-color:{bg};color:{fg};font-weight:600"


# ---- Sidebar ------------------------------------------------------------------
BRAND = f"""
<div class="dw-brand"><div class="dw-brand-mark">{icon("drop", 20)}</div>
<div><div class="dw-brand-name">DengueWatch</div></div></div>
<div class="dw-brand-tag">Warns city health teams about dengue 2–4 weeks before cases rise</div>
"""


def sidebar_controls(engine: Engine) -> dict:
    """Controls shared by every page (kept in session state across pages)."""
    weeks = engine.forecast_weeks()
    # Default: 2 June 2025, just before the 2025 season took off (56 of 60 wards still Low).
    demo = pd.Timestamp("2025-06-02")
    default_week = demo if demo in weeks else weeks[-1]
    sb = st.sidebar
    html_sb = lambda s: sb.markdown("".join(x.strip() for x in s.splitlines()), unsafe_allow_html=True)  # noqa: E731
    html_sb('<div class="dw-side-label">Settings</div>')
    city = sb.selectbox("City", ["All cities", *engine.cities], key="city")
    if "as_of" not in st.session_state:
        st.session_state["as_of"] = default_week
    as_of = sb.select_slider(
        "Pretend today is", options=weeks, format_func=fmt_week, key="as_of",
        help="DengueWatch replays past weeks, so you can compare its warning with what really happened. "
             "Pick any week from 2016 to 2025.",
    )
    horizon = sb.radio(
        "Look ahead (weeks)", config.HORIZONS, index=config.HORIZONS.index(config.DEFAULT_HORIZON),
        format_func=str, horizontal=True, key="horizon",
        help="How far ahead to forecast. 3 weeks matches how long rain takes to turn into dengue cases.",
    )
    unseen = pd.Timestamp(as_of) > engine.train_end
    html_sb(
        f'<div class="dw-side-note"><b>Replay of {fmt_week(as_of)}.</b> The model never saw this week while '
        f"learning, so you can check its warning against what really happened.</div>"
        if unseen else
        f'<div class="dw-side-note"><b>{fmt_week(as_of)}</b> was part of the data the model learned from '
        f"(2016–2023). Pick a week in 2024 or 2025 for a fair test.</div>"
    )
    return {"city": None if city == "All cities" else city, "city_label": city,
            "as_of": pd.Timestamp(as_of), "horizon": int(horizon), "unseen": unseen}


def engine_footer(engine: Engine) -> None:
    from dengue.briefing import llm_status
    from dengue.http import STATS

    b = engine.bundle
    llm = llm_status()
    with st.sidebar.expander("Speed and system status"):
        st.markdown(
            f"- Models trained through **{b['train_end']}** in {b['train_seconds']} s\n"
            f"- Data and models load in **{engine.load_seconds * 1000:.0f} ms** (once per server)\n"
            f"- Internet calls this session: **{STATS.calls}** (retries {STATS.retries}, failures {STATS.failures})\n"
            f"- AI wording for briefings: **{'on, ' + llm['model'] if llm['enabled'] else 'off (template)'}**; "
            f"today {llm['calls']}/{llm['budget']} calls, {llm['input_tokens'] + llm['output_tokens']} tokens"
        )

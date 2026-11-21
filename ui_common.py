"""Shared Streamlit helpers: cached engine, design system ("soft glass"), sidebar, top bar and chart styling."""
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
import ui_text as tx  # noqa: E402

# ---- Design tokens ---------------------------------------------------------------
INK, INK2, MUTED = "#111318", "#4B5160", "#8B909C"
GRID, AXIS, SURFACE = "#E6E8EC", "#D6D9DF", "rgba(0,0,0,0)"
ACCENT, ACCENT_SOFT = "#111318", "#E9EAEE"
RAIN = "#8FA3BF"           # rainfall bars (slate, not a tier colour)
UP, DOWN = "#E95A2C", "#5B8DEF"  # "pushes risk up" / "pulls risk down"
SANS = "Geist, 'Noto Sans Bengali', 'Segoe UI', system-ui, sans-serif"
SERIF = SANS  # kept for older imports
TIER_COLORS = config.TIER_COLORS
TIER_SOFT = {"Low": ("#E6EEFD", "#2F5FC4"), "Medium": ("#FBF1D6", "#8A6510"),
             "High": ("#FDE6DB", "#B5401A"), "Critical": ("#F8DDE6", "#8E1A42")}
BLUE = RAIN

TIER_MEANING = {"Low": "fewer than 2 cases a week", "Medium": "2 to 5 cases a week",
                "High": "5 to 10 cases a week", "Critical": "10 or more cases a week"}
TIER_MEANING_BN = {"Low": "সপ্তাহে ২ জনের কম রোগী", "Medium": "সপ্তাহে ২–৫ জন রোগী", "High": "সপ্তাহে ৫–১০ জন রোগী",
                   "Critical": "সপ্তাহে ১০ বা তার বেশি রোগী"}

_ICON_PATHS = {
    "rain": '<path d="M16.5 14.5h.5a3.5 3.5 0 0 0 .5-6.97A5.5 5.5 0 0 0 6.6 8.3 3.6 3.6 0 0 0 7 15.5"/>'
            '<path d="M8.5 17.5 7.5 20M12.5 16.5l-1 2.5M16.5 17.5l-1 2.5"/>',
    "clock": '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    "pulse": '<path d="M3 12h4l2.2-5 4.4 10 2.2-5H21"/>',
    "bell": '<path d="M6 16.5V11a6 6 0 0 1 12 0v5.5l1.5 1.5h-15z"/><path d="M10 20.5a2 2 0 0 0 4 0"/>',
    "drop": '<path d="M12 3.5s6 6.4 6 10.5a6 6 0 0 1-12 0c0-4.1 6-10.5 6-10.5z"/>',
    "mosquito": '<path d="M13.6 10.4 5.5 18.5" stroke-width="2.4"/><circle cx="15.6" cy="8.4" r="1.9"/><path d="M17 7l4-4"/>'
                '<path d="M12.6 11.4C11.6 7.2 9.2 4.4 7 4.8c-1 2 1.2 5.2 5.6 6.6z"/>'
                '<path d="M12.6 11.4C8.4 10.4 4.8 11 3.6 12.8c.8 1.7 4.8 1.7 9-1.4z"/>'
                '<path d="M14 12.2l2.8 2.4.8 4.6M15.8 10.4l3.4 1.2 1.6 3"/>',
    "list": '<path d="M9 6.5h11M9 12h11M9 17.5h11"/><circle cx="4.5" cy="6.5" r=".9"/><circle cx="4.5" cy="12" r=".9"/>'
            '<circle cx="4.5" cy="17.5" r=".9"/>',
    "note": '<path d="M6 3.5h9l4 4V20.5H6z"/><path d="M14.5 3.5v4.5H19M9 12h7M9 16h5"/>',
    "bars": '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    "grid": '<rect x="3.5" y="3.5" width="7" height="7" rx="2"/><rect x="13.5" y="3.5" width="7" height="7" rx="2"/>'
            '<rect x="3.5" y="13.5" width="7" height="7" rx="2"/><rect x="13.5" y="13.5" width="7" height="7" rx="2"/>',
    "upload": '<path d="M12 15.5V4M7.5 8.5 12 4l4.5 4.5"/><path d="M4 15v3.5A2 2 0 0 0 6 20.5h12a2 2 0 0 0 2-2V15"/>',
    "download": '<path d="M12 4v11.5M7.5 11 12 15.5 16.5 11"/><path d="M4 15v3.5A2 2 0 0 0 6 20.5h12a2 2 0 0 0 2-2V15"/>',
    "sliders": '<path d="M4 7h10M18 7h2M4 17h4M12 17h8"/><circle cx="16" cy="7" r="2"/><circle cx="10" cy="17" r="2"/>',
    "check": '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "arrow_ur": '<path d="M7 17 17 7M9 7h8v8"/>',
    "trend": '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
    "map": '<path d="M9 4 3 6.5v13L9 17l6 2.5 6-2.5v-13L15 6.5 9 4z"/><path d="M9 4v13M15 6.5v13"/>',
    "target": '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4.5"/><circle cx="12" cy="12" r=".8"/>',
}


def icon(name: str, size: int = 20) -> str:
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            f'{_ICON_PATHS[name]}</svg>')


CSS = """
<style>
:root{
  --ink:#111318; --ink2:#4B5160; --muted:#8B909C; --line:rgba(17,19,24,.08); --line2:rgba(17,19,24,.13);
  --glass:rgba(255,255,255,.66); --glass-b:rgba(255,255,255,.85);
  --shadow:0 1px 0 rgba(255,255,255,.9) inset, 0 22px 44px -30px rgba(17,19,24,.35);
  --mono:'Geist Mono', ui-monospace, monospace;
  --ease:cubic-bezier(.16,1,.3,1);
}
/* Canvas: soft grey with large light pools, like frosted acrylic */
.stApp{background:
  radial-gradient(46rem 34rem at 14% 6%, rgba(255,255,255,.95), rgba(255,255,255,0) 62%),
  radial-gradient(40rem 30rem at 92% 10%, rgba(210,217,234,.95), rgba(210,217,234,0) 62%),
  radial-gradient(52rem 38rem at 72% 100%, rgba(255,255,255,.85), rgba(255,255,255,0) 60%),
  radial-gradient(34rem 28rem at 0% 100%, rgba(222,216,238,.6), rgba(222,216,238,0) 60%),
  #E7E8ED !important; background-attachment:fixed !important;}
[data-testid="stToolbarActions"], [data-testid="stMainMenu"], [data-testid="stAppDeployButton"],
.stAppDeployButton, #MainMenu, footer, [data-testid="stDecoration"], [data-testid="stStatusWidget"] {display:none !important;}
header[data-testid="stHeader"], header[data-testid="stHeader"] *{background:transparent; pointer-events:none !important;}
header[data-testid="stHeader"] button, header[data-testid="stHeader"] button *{pointer-events:auto !important;}
[data-testid="stMainBlockContainer"]{max-width:1340px; padding-top:1.6rem; padding-bottom:4rem;}
/* Type */
h1{font-size:2.05rem !important; letter-spacing:-0.035em; line-height:1.1 !important; font-weight:650 !important; padding:0 !important;}
h2{letter-spacing:-0.03em;} h3{letter-spacing:-0.02em;}
[data-testid="stMarkdownContainer"] p{line-height:1.6;}
[data-testid="stCaptionContainer"]{color:var(--ink2) !important;}
/* ---- Sidebar as a floating glass panel ---- */
section[data-testid="stSidebar"]{background:transparent !important; border:none !important;}
section[data-testid="stSidebar"] > div{background:transparent !important;}
[data-testid="stSidebarContent"]{background:var(--glass); backdrop-filter:blur(22px) saturate(160%); -webkit-backdrop-filter:blur(22px) saturate(160%);
  border:1px solid var(--glass-b); border-radius:28px; margin:14px 0 14px 14px; box-shadow:var(--shadow); height:calc(100% - 28px) !important;}
[data-testid="stSidebarUserContent"]{padding-top:.4rem;}
[data-testid="stSidebarContent"] [data-testid="stPageLink"] a{border-radius:999px; padding:7px 14px; margin:1px 0; transition:background .2s var(--ease);}
[data-testid="stSidebarContent"] [data-testid="stPageLink"] a span{font-size:.92rem; color:var(--ink2);}
[data-testid="stSidebarContent"] [data-testid="stPageLink"] a:hover{background:rgba(17,19,24,.05);}
[data-testid="stSidebarContent"] [data-testid="stPageLink"] a[aria-current="page"],
[data-testid="stSidebarContent"] [data-testid="stPageLink"] a.dw-active{background:var(--ink) !important;}
[data-testid="stSidebarContent"] [data-testid="stPageLink"] a[aria-current="page"] span,
[data-testid="stSidebarContent"] [data-testid="stPageLink"] a.dw-active span{color:#fff !important;}
[data-testid="stSidebarContent"] [data-testid="stWidgetLabel"] p{font-weight:550; font-size:.84rem; color:var(--ink2);}
[data-testid="stSidebarContent"] [data-baseweb="select"] > div{background:#fff; border-radius:999px; border:1px solid var(--line);}
.dw-brand{display:flex; align-items:center; gap:10px; margin:2px 0 6px 6px;}
.dw-brand-mark{width:36px; height:36px; border-radius:12px; background:var(--ink); color:#fff; display:grid; place-items:center; flex:none;}
.dw-brand-name{font-size:1.18rem; font-weight:700; color:var(--ink); letter-spacing:-0.03em; line-height:1.1;}
.dw-brand-tag{font-size:.74rem; color:var(--muted); margin-top:1px;}
.dw-side-label{font-family:var(--mono); font-size:.66rem; text-transform:uppercase; letter-spacing:.14em; color:var(--muted); margin:16px 0 4px 14px;}
.dw-side-note{font-size:.78rem; line-height:1.5; color:var(--ink2); background:rgba(255,255,255,.7); border:1px solid var(--line);
  border-radius:16px; padding:10px 12px; margin-top:8px;}
.dw-side-note b{color:var(--ink);}
/* ---- Segmented controls as pills (language switch, look-ahead) ---- */
[data-testid="stButtonGroup"] > div{background:rgba(255,255,255,.75); border:1px solid var(--line); border-radius:999px; padding:3px; gap:2px;}
[data-testid="stButtonGroup"] button{border:none !important; border-radius:999px !important; min-height:32px; padding:2px 14px !important; box-shadow:none !important;}
[data-testid="stButtonGroup"] button[aria-checked="false"]{background:transparent !important; color:var(--ink2) !important;}
[data-testid="stButtonGroup"] button[aria-checked="true"]{background:var(--ink) !important; color:#fff !important;}
[data-testid="stButtonGroup"] button[aria-checked="true"] p{color:#fff !important;}
/* ---- Top bar ---- */
.st-key-topbar{margin-bottom:.6rem;}
.dw-eyebrow{font-family:var(--mono); font-size:.72rem; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); margin:0 0 6px;}
.dw-lead{font-size:1.02rem; line-height:1.6; color:var(--ink2); max-width:74ch; margin:0 0 1.2rem; text-wrap:pretty;}
.dw-lead b{color:var(--ink); font-weight:600;}
/* ---- Cards ---- */
.gc, [class*="st-key-glass"], .dw-card, .dw-step, .dw-callout, [data-testid="stMetric"]{
  background:var(--glass); backdrop-filter:blur(18px) saturate(150%); -webkit-backdrop-filter:blur(18px) saturate(150%);
  border:1px solid var(--glass-b) !important; border-radius:26px; box-shadow:var(--shadow);}
.gc{padding:22px 24px; height:100%;}
[class*="st-key-glass"]{padding:20px 22px 8px;}
.dk{background:radial-gradient(30rem 18rem at 100% 0%, #2A2E38 0%, #15171C 60%); color:#fff; border-radius:26px; padding:22px 24px;
  box-shadow:0 26px 50px -28px rgba(17,19,24,.6); height:100%;}
.ch{display:flex; align-items:flex-start; justify-content:space-between; gap:12px; margin-bottom:14px;}
.ch h3{font-size:1.06rem !important; font-weight:600 !important; margin:0 !important; padding:0 !important; color:var(--ink); letter-spacing:-0.02em;}
.ch p{font-size:.82rem; color:var(--muted); margin:2px 0 0;}
.dk .ch h3{color:#fff;} .dk .ch p{color:rgba(255,255,255,.55);}
.ib{width:34px; height:34px; border-radius:50%; border:1px solid var(--line2); display:grid; place-items:center; color:var(--ink2); flex:none; background:rgba(255,255,255,.6);}
.dk .ib{border-color:rgba(255,255,255,.18); color:#fff; background:rgba(255,255,255,.06);}
.big{font-size:3.6rem; font-weight:650; letter-spacing:-0.05em; line-height:1; font-variant-numeric:tabular-nums;}
.big .of{font-size:1.6rem; color:rgba(255,255,255,.45); letter-spacing:-0.02em; font-weight:500;}
.bigsub{font-size:.95rem; color:rgba(255,255,255,.72); margin:10px 0 18px; max-width:30ch; line-height:1.45;}
.tiles{display:grid; grid-template-columns:repeat(4, 1fr); gap:8px;}
.tile{background:rgba(255,255,255,.07); border:1px solid rgba(255,255,255,.09); border-radius:16px; padding:12px 12px 10px;}
.tile.hl{background:#fff; color:var(--ink);}
.tile .v{font-size:1.45rem; font-weight:650; letter-spacing:-0.03em; font-variant-numeric:tabular-nums;}
.tile .k{font-size:.72rem; opacity:.66; margin-top:2px; line-height:1.3;}
.mono{font-family:var(--mono); font-size:.72rem; letter-spacing:.04em; color:var(--muted);}
/* Ring */
.ring{display:flex; align-items:center; gap:18px;}
.ring svg{flex:none;}
.ring p{font-size:.88rem; color:var(--ink2); line-height:1.5; margin:0;}
.ring b{color:var(--ink);}
/* City rows */
.crow{display:grid; grid-template-columns:1fr auto; gap:4px 12px; padding:11px 0; border-top:1px solid var(--line);}
.crow:first-of-type{border-top:none; padding-top:2px;}
.crow .n{font-weight:550; font-size:.92rem;}
.crow .c{font-size:.85rem; color:var(--ink2); font-variant-numeric:tabular-nums;}
.crow .c b{color:var(--ink); font-weight:650;}
.dw-stack{grid-column:1 / -1; display:flex; gap:2px; height:8px; border-radius:999px; overflow:hidden; background:rgba(17,19,24,.06);}
.dw-stack span{display:block; height:100%;}
/* Pastel ward cards */
.wgrid{display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:12px;}
.wc{border-radius:22px; padding:16px 16px 14px; border:1px solid rgba(255,255,255,.7); transition:transform .3s var(--ease), box-shadow .3s var(--ease);}
.wc:hover{transform:translateY(-2px); box-shadow:0 18px 30px -24px rgba(17,19,24,.45);}
.wc .top{display:flex; justify-content:space-between; align-items:flex-start;}
.wc .nm{font-weight:650; font-size:1rem; letter-spacing:-0.02em;}
.wc .ct{font-size:.76rem; color:var(--ink2); opacity:.85;}
.wc .chg{display:inline-flex; align-items:center; gap:4px; background:rgba(255,255,255,.75); border-radius:999px; padding:3px 4px; font-size:.74rem; color:var(--ink2); margin:12px 0 10px;}
.wc .v{font-size:1.9rem; font-weight:650; letter-spacing:-0.04em; line-height:1; font-variant-numeric:tabular-nums;}
.wc .v small{font-size:.8rem; font-weight:500; letter-spacing:0; color:var(--ink2); margin-left:4px;}
.wc .bar{height:6px; border-radius:999px; background:rgba(255,255,255,.75); margin:12px 0 10px; overflow:hidden;}
.wc .bar span{display:block; height:100%; border-radius:999px;}
.wc .ft{display:flex; justify-content:space-between; gap:8px; font-size:.74rem; color:var(--ink2);}
.wc .ft .pl{background:rgba(255,255,255,.8); border-radius:999px; padding:3px 9px; white-space:nowrap;}
/* Tier pills */
.dw-pill{display:inline-flex; align-items:center; gap:6px; border-radius:999px; padding:2px 10px 2px 8px; font-size:.74rem; font-weight:600; white-space:nowrap; line-height:1.6;}
.dw-pill::before{content:""; width:6px; height:6px; border-radius:50%; background:currentColor;}
.dw-pill.t-Low{background:#E6EEFD; color:#2F5FC4;} .dw-pill.t-Medium{background:#FBF1D6; color:#8A6510;}
.dw-pill.t-High{background:#FDE6DB; color:#B5401A;} .dw-pill.t-Critical{background:#F8DDE6; color:#8E1A42;}
.wc .dw-pill{background:#fff;}
.dw-legend{display:flex; flex-wrap:wrap; gap:6px 16px; font-size:.8rem; color:var(--ink2); margin-top:12px;}
/* Steps timeline */
.steps{display:grid; grid-template-columns:repeat(4, 1fr); gap:18px; position:relative; margin-top:6px;}
.steps::before{content:""; position:absolute; top:21px; left:22px; right:12%; height:1px;
  background:repeating-linear-gradient(90deg, rgba(17,19,24,.22) 0 5px, transparent 5px 11px);}
.st{position:relative;}
.st .ic{width:44px; height:44px; border-radius:50%; background:#fff; border:1px solid var(--line); display:grid; place-items:center; color:var(--ink); margin-bottom:12px;}
.st.hl .ic{background:var(--ink); color:#fff; border-color:var(--ink);}
.st .w{font-family:var(--mono); font-size:.68rem; letter-spacing:.06em; text-transform:uppercase; color:var(--muted);}
.st .t{font-weight:600; font-size:.98rem; margin:2px 0 3px; letter-spacing:-0.01em;}
.st p{font-size:.83rem; color:var(--ink2); line-height:1.45; margin:0;}
/* Page links styled as pill buttons */
[data-testid="stMainBlockContainer"] [data-testid="stPageLink"] a{background:var(--ink); border-radius:999px; padding:6px 8px 6px 16px;}
[data-testid="stMainBlockContainer"] [data-testid="stPageLink"] a span{color:#fff !important; font-weight:550; font-size:.86rem;}
[data-testid="stMainBlockContainer"] [data-testid="stPageLink"] a:hover{background:#2A2D35;}
/* Older page components, restyled */
.dw-grid{display:grid; gap:14px; grid-template-columns:repeat(auto-fit, minmax(210px, 1fr));}
.dw-grid.wide{grid-template-columns:repeat(auto-fit, minmax(300px, 1fr));}
.dw-grid.five{grid-template-columns:repeat(5, minmax(0, 1fr));}
.dw-card{padding:18px 20px;}
.dw-card h4{font-weight:650; font-size:1.05rem; margin:0 0 2px; padding:0; letter-spacing:-0.02em;}
.dw-meta{font-size:.82rem; color:var(--ink2);}
.dw-big{font-size:2rem; line-height:1.1; letter-spacing:-0.04em; font-weight:650;}
.dw-big small{font-size:.86rem; color:var(--ink2); letter-spacing:0; font-weight:500; margin-left:2px;}
.dw-big .of{font-size:1.15rem; color:var(--muted);}
.dw-row{display:flex; align-items:center; gap:8px; flex-wrap:wrap;}
.dw-sep{color:var(--muted);}
.dw-reason{margin-top:12px; padding-top:10px; border-top:1px solid var(--line); font-size:.85rem; color:var(--ink2);}
.dw-reason b{color:var(--ink); font-weight:600;}
.dw-change{display:flex; align-items:flex-end; gap:10px; margin:12px 0 14px;}
.dw-change .k{font-size:.72rem; color:var(--muted); margin-bottom:3px;}
.dw-change .ar{color:var(--muted); padding-bottom:2px;}
.dw-section{font-size:1.3rem; font-weight:650; letter-spacing:-0.03em; color:var(--ink); margin:2rem 0 .1rem;}
.dw-section-sub{color:var(--ink2); font-size:.92rem; margin:0 0 .9rem; max-width:72ch;}
.dw-steps{display:grid; grid-template-columns:repeat(4, 1fr); gap:14px;}
.dw-step{padding:18px;} .dw-step .ic{width:40px; height:40px; border-radius:50%; background:#fff; display:grid; place-items:center; margin-bottom:10px;}
.dw-step .what{font-weight:600; margin:2px 0 4px;} .dw-step p{font-size:.85rem; color:var(--ink2); margin:0;}
.dw-callout{display:flex; gap:12px; align-items:flex-start; padding:12px 16px; color:var(--ink2); font-size:.92rem; max-width:900px;}
.dw-callout b{color:var(--ink);}
.dw-bars{display:flex; flex-direction:column; gap:10px;}
.dw-bar{display:grid; grid-template-columns:minmax(150px, 1.1fr) 2fr 84px; align-items:center; gap:12px; font-size:.9rem;}
.dw-bar .trk{position:relative; height:10px; background:rgba(17,19,24,.06); border-radius:999px;}
.dw-bar .trk::after{content:""; position:absolute; left:50%; top:-4px; bottom:-4px; width:1px; background:var(--line2);}
.dw-bar .fill{position:absolute; top:0; bottom:0; border-radius:999px;}
.dw-bar .val{text-align:right; font-variant-numeric:tabular-nums; color:var(--ink2); font-weight:600;}
.dw-bar.total{border-top:1px solid var(--line); padding-top:10px;} .dw-bar.total .val{color:var(--ink);}
[data-testid="stMetric"]{padding:16px 18px 14px;}
/* A row of st.metric tiles inside a dark card (key="dark_..."), matching the overview hero */
[class*="st-key-dark"]{background:radial-gradient(30rem 18rem at 100% 0%, #2A2E38 0%, #15171C 60%); border-radius:26px;
  padding:14px; box-shadow:0 26px 50px -28px rgba(17,19,24,.6);}
[class*="st-key-dark"] [data-testid="stMetric"]{background:rgba(255,255,255,.07); border:1px solid rgba(255,255,255,.09) !important;
  box-shadow:none; backdrop-filter:none; -webkit-backdrop-filter:none; border-radius:18px;}
[class*="st-key-dark"] [data-testid="stMetricLabel"] p{color:rgba(255,255,255,.66) !important;}
[class*="st-key-dark"] [data-testid="stMetricValue"]{color:#fff;}
[class*="st-key-dark"] [data-testid="stMetricLabel"] svg{color:rgba(255,255,255,.5);}
[class*="st-key-dark"] [data-testid="stColumn"]:nth-child(3) [data-testid="stMetric"]{background:#fff; border-color:#fff !important;}
[class*="st-key-dark"] [data-testid="stColumn"]:nth-child(3) [data-testid="stMetricLabel"] p{color:var(--ink2) !important;}
[class*="st-key-dark"] [data-testid="stColumn"]:nth-child(3) [data-testid="stMetricValue"]{color:var(--ink);}
[class*="st-key-dark"] [data-testid="stColumn"]:nth-child(3) [data-testid="stMetricLabel"] svg{color:var(--muted);}
.dk .dw-big{color:#fff;} .dk .dw-meta{color:rgba(255,255,255,.66);}
.gc .dw-bars{margin-top:4px;}
[data-testid="stMetricLabel"] p{color:var(--ink2); font-size:.84rem;}
[data-testid="stMetricValue"]{font-size:2rem !important; letter-spacing:-0.04em;}
[data-testid="stPlotlyChart"]{border-radius:20px;}
[data-testid="stExpander"] details{border-radius:20px; background:var(--glass); border:1px solid var(--glass-b);}
/* Motion */
@media (prefers-reduced-motion: no-preference){
  .gc, .dk, .wc, [class*="st-key-glass"]{animation:dw-up .7s var(--ease) both;}
  .wgrid > *:nth-child(2){animation-delay:.05s;} .wgrid > *:nth-child(3){animation-delay:.1s;}
  .wgrid > *:nth-child(4){animation-delay:.15s;} .wgrid > *:nth-child(5){animation-delay:.2s;} .wgrid > *:nth-child(6){animation-delay:.25s;}
  @keyframes dw-up{from{opacity:0; transform:translateY(12px);} to{opacity:1; transform:none;}}
}
@media (max-width: 1100px){ .wgrid{grid-template-columns:repeat(2, minmax(0,1fr));} .dw-grid.five{grid-template-columns:repeat(3, minmax(0,1fr));} }
@media (max-width: 700px){ .wgrid, .steps, .dw-steps, .dw-grid.five{grid-template-columns:1fr;} .steps::before{display:none;} .tiles{grid-template-columns:repeat(2,1fr);} }
</style>
"""


def inject_css() -> None:
    st.html(CSS)


def html(s: str, where=None) -> None:
    """Render an HTML snippet. Lines are joined so Markdown never treats indentation as code."""
    (where or st).markdown("".join(line.strip() for line in s.splitlines()), unsafe_allow_html=True)


# ---- Formatting helpers (language-aware) ---------------------------------------
def fmt_week(ts) -> str:
    return tx.date(ts)


def fmt_day(ts) -> str:
    return tx.day(ts)


def ward_name(ward_id: str) -> str:
    return tx.ward(ward_id)


def driver_name(group: str) -> str:
    return tx.driver(group)


def about(x: float) -> str:
    x = float(x)
    if x < 1:
        return "<1"
    return tx.num(round(x), "{:.0f}")


def case_range(lo: float, hi: float) -> str:
    return tx.num(f"{math.floor(max(lo, 0)):.0f}–{math.ceil(hi):.0f}")


def tier_pill(tier: str) -> str:
    return f'<span class="dw-pill t-{tier}">{tx.tier(tier)}</span>'


tier_badge = tier_pill  # older name


def page_header(eyebrow: str, title: str, lead: str = "") -> None:
    slot = st.session_state.get("_title_slot") or st.container()
    with slot:
        html(f'<div class="dw-eyebrow">{eyebrow}</div>')
        st.title(title, anchor=False)
    if lead:
        html(f'<p class="dw-lead">{lead}</p>')


def section(title: str, sub: str = "") -> None:
    html(f'<div class="dw-section">{title}</div>' + (f'<p class="dw-section-sub">{sub}</p>' if sub else ""))


def tier_legend() -> str:
    meaning = TIER_MEANING_BN if tx.lang() == "bn" else TIER_MEANING
    return ('<div class="dw-legend">' + "".join(
        f'<span>{tier_pill(t)} {meaning[t]}</span>' for t in config.TIERS) + "</div>")


# ---- Data access ----------------------------------------------------------------
@st.cache_resource(show_spinner="Loading data and models...")
def get_engine() -> Engine:
    return Engine.load()


@st.cache_data(show_spinner=False, max_entries=256)
def cached_forecast(as_of: str, h: int, city: str | None, extra_rain: float = 0.0) -> pd.DataFrame:
    return get_engine().forecast(as_of, h, city, extra_rain)


# ---- Charts ---------------------------------------------------------------------
def _nice_ticks(lo: float, hi: float, n: int = 5) -> tuple[list, int]:
    hi = hi if hi > lo else lo + 1
    raw = (hi - lo) / n
    mag = 10 ** math.floor(math.log10(raw))
    step = next(k * mag for k in (1, 2, 2.5, 5, 10) if k * mag >= raw)
    start = math.floor(lo / step) * step
    decimals = 0
    while not float(round(step * 10 ** decimals, 9)).is_integer():
        decimals += 1
    return [start + i * step for i in range(int((hi - start) / step) + 2)], decimals


def bangla_axes(fig: go.Figure) -> None:
    """Plotly always draws Latin digits, so numeric axes get explicit Bangla tick labels in Bangla mode."""
    for ax in ("x", "y"):
        layout_ax = getattr(fig.layout, f"{ax}axis")
        if layout_ax.tickvals is not None or layout_ax.type in ("date", "category"):
            continue
        vals = []
        for tr in fig.data:
            if tr.type not in ("bar", "scatter"):
                continue
            col = getattr(tr, ax, None)
            if col is None:
                continue
            ser = pd.Series(list(col))
            if pd.api.types.is_datetime64_any_dtype(ser) or ser.map(lambda v: isinstance(v, (str, pd.Timestamp))).any():
                vals = None
                break
            vals += pd.to_numeric(ser, errors="coerce").dropna().tolist()
            if tr.type == "bar":
                vals.append(0.0)
        if not vals:
            continue
        ticks, dec = _nice_ticks(min(vals), max(vals))
        fig.update_layout({f"{ax}axis": dict(tickvals=ticks, ticktext=[tx.num(f"{v:,.{dec}f}") for v in ticks])})


def style_fig(fig: go.Figure, height: int = 360, legend: bool = True) -> go.Figure:
    has_title = bool(fig.layout.title.text)
    fig.update_layout(
        height=height, margin=dict(l=6, r=10, t=(76 if legend else 50) if has_title else (36 if legend else 10), b=6),
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        font=dict(family=SANS, color=INK2, size=12),
        hoverlabel=dict(bgcolor="white", bordercolor=AXIS, font=dict(family=SANS, color=INK, size=12)),
        showlegend=legend, legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, title=None, font=dict(size=12)),
        title=dict(font=dict(family=SANS, color=INK, size=16), x=0.01, xanchor="left", y=0.97, yanchor="top"),
    )
    fig.update_xaxes(gridcolor=GRID, linecolor=AXIS, zeroline=False, tickfont=dict(color=MUTED, size=11),
                     title_font=dict(size=11, color=INK2))
    fig.update_yaxes(gridcolor=GRID, linecolor="rgba(0,0,0,0)", zeroline=False, tickfont=dict(color=MUTED, size=11),
                     title_font=dict(size=11, color=INK2))
    if tx.lang() == "bn":
        bangla_axes(fig)
    return fig


def card_head(title: str, sub: str = "", ic: str = "") -> str:
    """Card header: title and a muted line on the left, a round icon on the right."""
    return (f'<div class="ch"><div><h3>{title}</h3>' + (f'<p>{sub}</p>' if sub else "") + "</div>"
            + (f'<div class="ib">{icon(ic, 16)}</div>' if ic else "") + "</div>")


_TIER_OF_LABEL = {**{t: t for t in TIER_SOFT}, **{tx.TIER_BN[t]: t for t in TIER_SOFT}}


def tier_cell_style(v) -> str:
    """Soft tier colours for a table cell holding a tier name in either language."""
    if v not in _TIER_OF_LABEL:
        return ""
    bg, fg = TIER_SOFT[_TIER_OF_LABEL[v]]
    return f"background-color:{bg};color:{fg};font-weight:600"


# ---- Top bar and sidebar ----------------------------------------------------------
def top_bar() -> None:
    """Title slot (filled by each page) on the left, language switch on the right."""
    bar = st.container(key="topbar", horizontal=True, vertical_alignment="bottom", gap="medium")
    st.session_state["_title_slot"] = bar.container(width="stretch")
    if "lang" not in st.session_state:
        st.session_state["lang"] = "en"
    if st.session_state["lang"] == "bn":  # Geist Mono has no Bangla letters: use the Bangla sans for small labels
        st.html("<style>.mono,.dw-eyebrow,.dw-side-label,.st .w{font-family:'Noto Sans Bengali',sans-serif !important;"
                "letter-spacing:0 !important; font-size:.8rem !important;}</style>")
    bar.segmented_control("Language", list(tx.LANGS), format_func=tx.LANGS.get, key="lang", required=True,
                          label_visibility="collapsed", width="content")


def brand() -> str:
    return (f'<div class="dw-brand"><div class="dw-brand-mark">{icon("mosquito", 22)}</div>'
            f'<div><div class="dw-brand-name">DengueWatch</div><div class="dw-brand-tag">{tx.t("brand_tag")}</div></div></div>')


def keep_choice(name: str, values: list, label_of, default):
    """Options as text in the current language, with the choice kept when the language changes.

    Returns (labels, label -> value, widget key). Store the picked value with remember(name, value)."""
    ss, lg = st.session_state, tx.lang()
    labels = [label_of(v) for v in values]
    key = f"{name}_{lg}"
    if ss.get(f"_{name}_lang") != lg:
        ss.pop(key, None)
    if key not in ss or ss[key] not in labels:
        prev = ss.get(f"v_{name}", default)
        ss[key] = label_of(prev if prev in values else default)
    ss[f"_{name}_lang"] = lg
    return labels, dict(zip(labels, values)), key


def remember(name: str, value):
    st.session_state[f"v_{name}"] = value
    return value


def sidebar_controls(engine: Engine) -> dict:
    """Controls shared by every page (kept in session state across pages and languages)."""
    weeks = engine.forecast_weeks()
    demo = pd.Timestamp("2025-06-02")  # just before the 2025 season took off (56 of 60 wards still Low)
    default_week = demo if demo in weeks else weeks[-1]
    sb = st.sidebar
    ss = st.session_state
    lg = tx.lang()

    def widget(name: str, values: list, label_of, default):
        # Options are shown as text in the current language. Each language gets its own widget key, and its
        # starting value comes from the language-neutral copy, so switching language never resets a setting.
        labels = [label_of(v) for v in values]
        key = f"{name}_{lg}"
        if ss.get("_controls_lang") != lg:
            ss.pop(key, None)
        if key not in ss or ss[key] not in labels:
            ss[key] = label_of(ss.get(f"v_{name}", default))
        return labels, dict(zip(labels, values)), key

    html(f'<div class="dw-side-label">{tx.t("settings")}</div>', sb)
    labels, back, key = widget("city", ["All cities", *engine.cities], tx.city, "All cities")
    city = back[sb.selectbox(tx.t("city"), labels, key=key)]
    labels, back, key = widget("as_of", weeks, tx.date, default_week)
    as_of = back[sb.select_slider(tx.t("replay"), options=labels, key=key, help=tx.t("replay_help"))]
    labels, back, key = widget("horizon", list(config.HORIZONS), lambda h: tx.t("ahead_fmt", h=tx.num(h)),
                               config.DEFAULT_HORIZON)
    horizon = back[sb.segmented_control(tx.t("ahead"), labels, required=True, key=key, help=tx.t("ahead_help"))]
    ss["v_city"], ss["v_as_of"], ss["v_horizon"], ss["_controls_lang"] = city, as_of, horizon, lg
    unseen = pd.Timestamp(as_of) > engine.train_end
    html(f'<div class="dw-side-note">{tx.t("note_unseen" if unseen else "note_seen", date=tx.date(as_of))}</div>', sb)
    return {"city": None if city == "All cities" else city, "city_label": tx.city(city),
            "as_of": pd.Timestamp(as_of), "horizon": int(horizon), "unseen": unseen}


def engine_footer(engine: Engine) -> None:
    from dengue.briefing import llm_status
    from dengue.http import STATS

    b = engine.bundle
    llm = llm_status()
    state = tx.t("st_llm_on", model=llm["model"]) if llm["enabled"] else tx.t("st_llm_off")
    n = tx.num
    with st.sidebar.expander(tx.t("status")):
        st.markdown("\n".join("- " + line for line in (
            tx.t("st_trained", date=tx.date(b["train_end"]), s=n(f"{b['train_seconds']}")),
            tx.t("st_load", ms=n(engine.load_seconds * 1000)),
            tx.t("st_calls", n=n(STATS.calls), r=n(STATS.retries), f=n(STATS.failures)),
            tx.t("st_llm", state=state, c=n(llm["calls"]), b=n(llm["budget"]),
                 tok=n(llm["input_tokens"] + llm["output_tokens"])),
        )))

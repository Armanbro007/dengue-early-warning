"""The app shell: one top bar with the brand, the three main tabs (Report, Actions, More),
the report-week settings and the language switch. No sidebar, so a first-time visitor sees
only what matters."""
from __future__ import annotations

import pandas as pd
import streamlit as st

import ui_text as tx
from dengue import config
from ui_common import brand, html, sidebar_controls

SHELL_CSS = """
<style>
/* No sidebar in the simple layout */
section[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="stExpandSidebarButton"]{display:none !important;}
[data-testid="stMainBlockContainer"]{padding-top:1.1rem;}
/* Top bar: brand, tabs, settings, language */
.st-key-shell{background:var(--glass); backdrop-filter:blur(18px) saturate(150%); -webkit-backdrop-filter:blur(18px) saturate(150%);
  border:1px solid var(--glass-b); border-radius:999px; box-shadow:var(--shadow); padding:8px 10px 8px 14px; margin-bottom:1.4rem;}
.st-key-shell .dw-brand{margin:0 6px 0 0;}
.st-key-shell .dw-brand-mark{width:34px; height:34px; border-radius:11px;}
.st-key-navpills{background:rgba(17,19,24,.045); border-radius:999px; padding:4px; gap:2px !important;}
.st-key-navpills [data-testid="stPageLink"] a{background:transparent !important; border-radius:999px !important; padding:7px 18px !important;
  transition:background .2s var(--ease);}
.st-key-navpills [data-testid="stPageLink"] a:hover{background:rgba(17,19,24,.06) !important;}
.st-key-navpills [data-testid="stPageLink"] a span{color:var(--ink2) !important; font-weight:550 !important; font-size:.95rem !important;}
.st-key-shell [data-testid="stPopover"] button{border-radius:999px; border:1px solid var(--line2); background:#fff; min-height:38px;}
.dw-net{display:inline-flex; align-items:center; gap:7px; font-size:.8rem; color:var(--ink2); white-space:nowrap; padding:0 6px;}
.dw-net i{width:8px; height:8px; border-radius:50%; background:#2E8B57; box-shadow:0 0 0 3px rgba(46,139,87,.15);}
.dw-net.off i{background:#8B909C; box-shadow:0 0 0 3px rgba(139,144,156,.18);}
/* Start-here guide */
.dw-guide{display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:14px;}
.dw-guide .g{display:flex; gap:12px; align-items:flex-start;}
.dw-guide .n{flex:none; width:30px; height:30px; border-radius:50%; background:var(--ink); color:#fff; display:grid; place-items:center;
  font-weight:650; font-size:.88rem;}
.dw-guide .t{font-weight:600; font-size:.95rem; color:var(--ink); margin-bottom:2px;}
.dw-guide p{font-size:.84rem; color:var(--ink2); margin:0; line-height:1.45;}
/* Plain-language answer line */
.dw-answer{font-size:1.28rem; line-height:1.45; letter-spacing:-0.02em; color:var(--ink); max-width:60ch; margin:0 0 .3rem; text-wrap:pretty;}
.dw-answer b{font-weight:650;}
.dw-why{display:flex; gap:10px; align-items:flex-start; padding:10px 0; border-top:1px solid var(--line); font-size:.9rem; color:var(--ink2); line-height:1.5;}
.dw-why:first-of-type{border-top:none;}
.dw-why .ar{flex:none; width:26px; height:26px; border-radius:50%; display:grid; place-items:center; font-size:.85rem; font-weight:700;}
.dw-why .ar.up{background:#FDE6DB; color:#B5401A;} .dw-why .ar.down{background:#E6EEFD; color:#2F5FC4;}
.dw-why b{color:var(--ink); font-weight:600;}
.dw-todo{display:flex; flex-direction:column; gap:8px; margin:4px 0 2px;}
.dw-todo div{display:flex; gap:10px; align-items:center; font-size:.92rem; color:var(--ink);}
.dw-todo .ic{flex:none; width:30px; height:30px; border-radius:10px; background:#fff; border:1px solid var(--line); display:grid; place-items:center; color:var(--ink);}
.dw-firstrow{display:grid; grid-template-columns:minmax(0,1fr) auto; gap:4px 12px; align-items:center; padding:11px 0; border-top:1px solid var(--line);}
.dw-firstrow:first-of-type{border-top:none; padding-top:2px;}
.dw-firstrow .nm{font-weight:600; font-size:.95rem; color:var(--ink);}
.dw-firstrow .sub{font-size:.8rem; color:var(--ink2);}
.dw-tierbar{display:flex; height:12px; border-radius:999px; overflow:hidden; gap:2px; margin:16px 0 10px; background:rgba(255,255,255,.08);}
.dw-tierbar span{display:block; height:100%;}
.dw-tierkey{display:flex; flex-wrap:wrap; gap:6px 14px; font-size:.8rem; color:rgba(255,255,255,.72);}
.dw-tierkey b{color:#fff; font-weight:650; margin-right:3px;}
.dw-tierkey i{display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:6px;}
/* Steps on the Actions page */
.st-key-stepper [data-testid="stButtonGroup"] > div{padding:4px;}
.st-key-stepper [data-testid="stButtonGroup"] button{min-height:40px; padding:4px 18px !important;}
.st-key-stepper [data-testid="stButtonGroup"] button p{font-size:.92rem; font-weight:550;}
.dw-crewrow{display:grid; grid-template-columns:minmax(0,1.4fr) auto minmax(0,1fr); gap:12px; align-items:center; padding:10px 0;
  border-top:1px solid var(--line); font-size:.92rem;}
.dw-crewrow:first-of-type{border-top:none;}
.dw-crewrow .nm{font-weight:600; color:var(--ink);} .dw-crewrow .sub{font-size:.78rem; color:var(--ink2);}
.dw-crewrow .dots{display:flex; gap:4px;} .dw-crewrow .dots i{width:14px; height:14px; border-radius:5px; background:#2E8B57;}
.dw-crewrow .dots i.e{background:rgba(17,19,24,.1);}
.dw-crewrow .gain{text-align:right; color:var(--ink2); font-variant-numeric:tabular-nums;} .dw-crewrow .gain b{color:#1F7A4A;}
.dw-soon{display:inline-block; font-size:.72rem; font-weight:600; color:#8A6510; background:#FBF1D6; border-radius:6px; padding:2px 8px; margin-left:6px; vertical-align:middle;}
.dw-tile{height:100%;}
.dw-tile p{font-size:.88rem; color:var(--ink2); line-height:1.5; margin:0 0 12px;}
@media (max-width: 760px){ .dw-guide{grid-template-columns:1fr;} .st-key-shell{border-radius:26px;} .dk{min-height:0 !important;} }
</style>
"""


def L(en: str, bn: str) -> str:
    """Pick the text for the current language."""
    return bn if tx.lang() == "bn" else en


def _current_label(engine) -> str:
    """Text for the settings button: the report week and look-ahead now chosen (read from the widgets' state)."""
    ss, lg = st.session_state, tx.lang()
    weeks = engine.forecast_weeks()
    demo = pd.Timestamp("2025-06-02")
    week = ss.get(f"as_of_{lg}") if ss.get("_controls_lang") == lg else None
    week = week or tx.date(ss.get("v_as_of", demo if demo in weeks else weeks[-1]))
    return L(f"Week of {week}", f"{week} সপ্তাহ")


def _offline_toggle(where) -> bool:
    """Kill switch for the live judging test: cuts every internet call at once."""
    ss = st.session_state
    ss.setdefault("v_offline", not config.NETWORK_FROM_ENV)
    ss["offline"] = ss["v_offline"]
    off = where.toggle(tx.t("offline"), key="offline", help=tx.t("offline_help"),
                       on_change=lambda: ss.__setitem__("v_offline", ss["offline"]))
    config.ALLOW_NETWORK = config.NETWORK_FROM_ENV and not off
    return off


def shell(engine, main_pages: list, current) -> dict:
    """Draw the top bar and return the shared controls (report week, look-ahead, city)."""
    st.html(SHELL_CSS)
    st.session_state["_title_slot"] = None
    if "lang" not in st.session_state:
        st.session_state["lang"] = "en"
    bar = st.container(key="shell", horizontal=True, vertical_alignment="center", gap="small")
    with bar:
        html(brand())
        nav = st.container(key="navpills", horizontal=True, width="content", gap=None)
        for p in main_pages:
            with nav.container(key=f"nav_{p.url_path or 'report'}", width="content"):
                st.page_link(p)
        st.space("stretch")
        net = st.empty()
        with bar.popover(_current_label(engine), icon=":material/calendar_month:"):
            st.markdown(L("**Which week do you want to see?**", "**কোন সপ্তাহ দেখতে চান?**"))
            st.caption(L("The data runs from 2016 to the end of 2025. Pick any week to replay it as if it were today.",
                         "তথ্য আছে ২০১৬ থেকে ২০২৫ সালের শেষ পর্যন্ত। যেকোনো সপ্তাহকে আজ ধরে আবার দেখুন।"))
            controls = sidebar_controls(engine, where=st.container())
            st.divider()
            off = _offline_toggle(st)
        bar.segmented_control("Language", list(tx.LANGS), format_func=tx.LANGS.get, key="lang", required=True,
                              label_visibility="collapsed", width="content")
    on = config.ALLOW_NETWORK
    net.markdown(f'<span class="dw-net{"" if on else " off"}"><i></i>'
                 f'{L("Works offline", "অফলাইনেও চলে") if on else L("Offline mode", "অফলাইন মোড")}</span>',
                 unsafe_allow_html=True)
    cur = current.url_path or "report"
    html(f'<style>.st-key-navpills .st-key-nav_{cur} [data-testid="stPageLink"] a{{background:#111318 !important;}}'
         f'.st-key-navpills .st-key-nav_{cur} [data-testid="stPageLink"] a span{{color:#fff !important;}}</style>')
    if tx.lang() == "bn":  # Geist Mono has no Bangla letters: use the Bangla sans for small labels
        st.html("<style>.mono,.dw-eyebrow,.dw-side-label,.st .w{font-family:'Noto Sans Bengali',sans-serif !important;"
                "letter-spacing:0 !important; font-size:.8rem !important;}</style>")
    controls["offline"] = off
    return controls


def start_here() -> None:
    """Three-step guide for a first-time visitor. Hidden once they press 'Got it'."""
    if st.session_state.get("guide_done"):
        return
    steps = [(L("See what is coming", "কী আসছে দেখুন"),
              L("This page shows which wards may get more dengue cases in 3 weeks.", "এই পাতায় দেখুন ৩ সপ্তাহ পর কোন ওয়ার্ডে ডেঙ্গু বাড়তে পারে।")),
             (L("Tap a ward to see why", "ওয়ার্ডে চাপ দিয়ে কারণ দেখুন"),
              L("Each coloured square is one ward. Tap it to read the reason in plain words.", "প্রতিটি রঙিন ঘর একটি ওয়ার্ড। চাপ দিলে সহজ ভাষায় কারণ দেখাবে।")),
             (L("Go to Actions", "পদক্ষেপে যান"),
              L("Answer a few questions there and get a plan for crews, supplies, beds and notices.",
                "সেখানে কয়েকটি প্রশ্নের উত্তর দিন, স্প্রে দল, সরবরাহ, শয্যা ও নোটিশের পরিকল্পনা পাবেন।"))]
    with st.container(key="glass_guide"):
        html('<div class="dw-guide">' + "".join(
            f'<div class="g"><div class="n">{tx.num(i)}</div><div><div class="t">{t}</div><p>{p}</p></div></div>'
            for i, (t, p) in enumerate(steps, 1)) + "</div>")
        st.button(L("Got it", "বুঝেছি"), key="guide_ok", type="tertiary",
                  on_click=lambda: st.session_state.__setitem__("guide_done", True))

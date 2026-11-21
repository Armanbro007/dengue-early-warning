"""Live forecast: this week's real weather from Open-Meteo (one call, cached, with fallbacks)."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dengue import config, weather_api
from dengue.config import TIERS
from ui_common import (driver_name, fmt_week, get_engine, html, icon, page_header, section,
                       style_fig, tier_cell_style, tier_legend, ward_name)

engine = get_engine()
c = st.session_state["controls"]
h = c["horizon"]

page_header(
    "Live forecast", "This week's warning, from real weather",
    "The same model, fed with this week's measured and forecast weather instead of the replayed dataset. "
    f"One internet call covers all five cities and is saved for {config.WEATHER_CACHE_TTL_H} hours. If the "
    "connection fails, DengueWatch uses the last saved forecast, then typical weather for this time of year.",
)


@st.cache_data(ttl=600, show_spinner="Fetching weather (1 call for all cities)...")
def load_weather(nonce: int):
    return weather_api.get_weekly_weather(get_engine().raw, force_refresh=bool(nonce))


top_row = st.columns([3, 1])
if top_row[1].button("Refresh weather now", icon=":material/refresh:", help="Skips the saved copy and makes one new call"):
    st.session_state["wx_nonce"] = st.session_state.get("wx_nonce", 0) + 1
res = load_weather(st.session_state.get("wx_nonce", 0))

TITLES = {"live": "Live weather", "cache": "Saved weather", "stale-cache": "Offline: using the last saved weather",
          "climatology": "Offline: using typical weather"}
head = TITLES[res.source]
ok = res.source in ("live", "cache")
with top_row[0]:
    html(f'<div class="dw-callout" style="border-left-color:{"#1F6F6A" if ok else "#D4A52F"}">'
         f'{icon("check" if ok else "clock", 20)}<div><b>{head}.</b><br>'
         f'<span class="dw-meta">{res.message}</span></div></div>')

fc = engine.forecast_from_city_weather(res.weekly, h)
if c["city"]:
    fc = fc[fc["city"] == c["city"]]
as_of = fc["date"].max()

section(f"Expected risk in the week of {fmt_week(as_of + pd.Timedelta(weeks=h))}",
        f"Forecast made on {fmt_week(as_of)}, {h} weeks ahead.")
k = st.columns(4)
for i, t in enumerate(TIERS[::-1]):
    k[i].metric(f"{t} wards", int((fc["tier"] == t).sum()))

a, b = st.columns([3, 2], gap="large")
with a:
    wk = res.weekly if not c["city"] else res.weekly[res.weekly["city"] == c["city"]]
    fig = go.Figure()
    for city, color in zip(sorted(wk["city"].unique()), ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]):
        d = wk[wk["city"] == city]
        fig.add_scatter(x=d["date"], y=d["rainfall_mm"], name=city, mode="lines+markers",
                        line=dict(color=color, width=2), marker=dict(size=8, line=dict(color="white", width=2)),
                        hovertemplate=f"{city}, week of %{{x|%d %b}}: %{{y:.0f}} mm<extra></extra>")
    fig.update_layout(title="Weekly rain feeding the model", yaxis_title="Rain (mm per week)")
    st.plotly_chart(style_fig(fig, height=360), width="stretch")
with b:
    top = fc.head(12).assign(ward=lambda d: d["ward_id"].map(ward_name), reason=lambda d: d["main_driver"].map(driver_name))
    st.dataframe(
        top[["ward", "tier", "pred", "reason"]].style.map(tier_cell_style, subset=["tier"]).format({"pred": "{:.1f}"}),
        hide_index=True, width="stretch", height=380,
        column_config={"ward": "Ward", "tier": "Risk", "pred": st.column_config.NumberColumn("Cases", help="Expected cases"),
                       "reason": "Main reason"},
    )
html(tier_legend())
st.caption("November is the dry season in Bangladesh, so live risk is expected to be low now. "
           "The same steps turn monsoon rain into early warnings from June onward.")

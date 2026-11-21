"""Live Forecast: real weather from Open-Meteo (one call, cached, with fallbacks)."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dengue import config, weather_api
from dengue.config import TIERS
from ui_common import BLUE, TIER_COLORS, fmt_week, get_engine, style_fig

engine = get_engine()
c = st.session_state["controls"]
h = c["horizon"]

st.title("Live Forecast")
st.caption("Uses this week's real and forecast weather instead of the historical dataset. "
           "One API call covers all 5 cities; the result is cached for "
           f"{config.WEATHER_CACHE_TTL_H} hours. If the network fails, the app falls back to the last "
           "saved forecast, then to typical weather for this time of year.")

refresh = st.button("Refresh weather now", help="Ignores the cache and makes one new API call")


@st.cache_data(ttl=600, show_spinner="Fetching weather (1 API call)...")
def load_weather(nonce: int):
    return weather_api.get_weekly_weather(get_engine().raw, force_refresh=bool(nonce))


if refresh:
    st.session_state["wx_nonce"] = st.session_state.get("wx_nonce", 0) + 1
res = load_weather(st.session_state.get("wx_nonce", 0))

badge = {"live": "success", "cache": "success", "stale-cache": "warning", "climatology": "warning"}[res.source]
getattr(st, badge)(f"Weather source: **{res.source}**. {res.message}")

fc = engine.forecast_from_city_weather(res.weekly, h)
if c["city"]:
    fc = fc[fc["city"] == c["city"]]
as_of = fc["date"].max()
st.markdown(f"Forecast issued week of **{fmt_week(as_of)}** for week of **{fmt_week(as_of + pd.Timedelta(weeks=h))}**")

k = st.columns(4)
for i, t in enumerate(TIERS[::-1]):
    k[i].metric(f"{t} wards", int((fc["tier"] == t).sum()))

a, b = st.columns([3, 2], gap="large")
with a:
    wk = res.weekly if not c["city"] else res.weekly[res.weekly["city"] == c["city"]]
    fig = go.Figure()
    for city, color in zip(sorted(wk["city"].unique()), [BLUE, "#eb6834", "#1baf7a", "#eda100", "#6250d6"]):
        d = wk[wk["city"] == city]
        fig.add_scatter(x=d["date"], y=d["rainfall_mm"], name=city, mode="lines+markers",
                        line=dict(color=color, width=2), marker=dict(size=8),
                        hovertemplate=f"{city}, week of %{{x|%d %b}}: %{{y:.0f}} mm<extra></extra>")
    fig.update_layout(title="Weekly rainfall feeding the model (observed + forecast)", yaxis_title="mm / week")
    st.plotly_chart(style_fig(fig, height=360), use_container_width=True)
with b:
    st.dataframe(
        fc[["ward_id", "city", "tier", "pred", "lo", "hi", "main_driver"]].head(15)
        .style.map(lambda v: f"background-color:{TIER_COLORS.get(v, '')};color:{'#0b0b0b' if v == 'Medium' else '#fff'};font-weight:600", subset=["tier"])
        .format({"pred": "{:.1f}", "lo": "{:.1f}", "hi": "{:.1f}"}),
        hide_index=True, use_container_width=True, height=360,
        column_config={"ward_id": "Ward", "city": "City", "tier": "Tier", "pred": "Forecast", "lo": "Low", "hi": "High",
                       "main_driver": "Main driver"},
    )
st.caption("November is dry season in Bangladesh, so live risk is expected to be Low now. "
           "The same pipeline turns monsoon rain into early warnings from June onward.")

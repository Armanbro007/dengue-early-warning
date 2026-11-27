"""The ward map: all 60 wards as coloured squares, grouped by city, that can be tapped.

The dataset has no ward coordinates, so this is an honest grid, not a fake geographic map."""
from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ui_text as tx
from ui_common import INK, style_fig

CITY_ORDER = ["Dhaka North", "Dhaka South", "Chattogram", "Gazipur", "Narayanganj"]


def layout(wards: pd.DataFrame, per_row: int = 10) -> tuple[pd.DataFrame, list, float]:
    """x/y grid position for each ward (needs ward_id and city columns)."""
    tiles, labels, y = [], [], 0.0
    for city in [c for c in CITY_ORDER if c in set(wards["city"])]:
        d = wards[wards["city"] == city].sort_values("ward_id")
        labels.append((city, y))
        for i, w in enumerate(d.itertuples()):
            tiles.append(dict(ward_id=w.ward_id, x=i % per_row, y=y + i // per_row))
        y += math.ceil(len(d) / per_row) + 0.45
    return pd.DataFrame(tiles), labels, y


def ward_map(wards: pd.DataFrame, color: dict, text_color: dict, hover: dict, key: str,
             selected: str | None = None) -> str | None:
    """Draw the grid. color/text_color/hover map ward_id -> value. Returns the ward tapped this run, if any."""
    tiles, labels, height = layout(wards)
    fig = go.Figure()
    fig.add_scatter(
        x=tiles["x"], y=tiles["y"], mode="markers+text",
        text=[tx.num(w.split("_Ward_")[1]) for w in tiles["ward_id"]],
        textfont=dict(color=[text_color[w] for w in tiles["ward_id"]], size=12, family="Geist, sans-serif"),
        marker=dict(symbol="square", size=31, color=[color[w] for w in tiles["ward_id"]], line=dict(width=0)),
        hovertext=[hover[w] for w in tiles["ward_id"]], hoverinfo="text",
        selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=1)), showlegend=False)
    if selected is not None:
        sel = tiles[tiles["ward_id"] == selected]
        fig.add_scatter(x=sel["x"], y=sel["y"], mode="markers", hoverinfo="skip", showlegend=False,
                        marker=dict(symbol="square-open", size=40, color=INK, line=dict(width=2.5)))
    for city, yy in labels:
        fig.add_annotation(x=-0.75, y=yy, text=f"<b>{tx.city(city)}</b>", showarrow=False, xanchor="right",
                           font=dict(size=12, color=INK))
    fig.update_xaxes(visible=False, range=[-3.4, 9.6], fixedrange=True)
    fig.update_yaxes(visible=False, autorange="reversed", fixedrange=True)
    fig.update_layout(dragmode=False, clickmode="event+select")
    ev = st.plotly_chart(style_fig(fig, height=int(height * 46) + 30, legend=False), key=key, on_select="rerun",
                         selection_mode="points", width="stretch", config={"displayModeBar": False})
    pts = ev.selection.points if ev and ev.selection else []
    last = f"_{key}_last"
    if pts and pts[0].get("curve_number", 0) == 0:
        picked = tiles.iloc[pts[0].get("point_index", pts[0].get("point_number", 0))]["ward_id"]
        if picked != st.session_state.get(last):
            st.session_state[last] = picked
            return picked
    elif not pts:
        st.session_state[last] = None
    return None

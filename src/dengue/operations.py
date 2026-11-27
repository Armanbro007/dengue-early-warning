"""One call that turns a forecast into an operational plan for every ward.

    forecast -> supplies needed -> stock shared by priority (module 1)
             -> beds needed vs beds free -> overflow routed inside each city (module 2)
             -> crews sent where each one prevents the most cases (module 3)
    plan     -> SMS / WhatsApp / printable brief per ward (module 4, dispatch.py)

All of it is local arithmetic plus the local model: it never touches the network
(module 5), so it keeps working when Wi-Fi or the Gemini API is cut.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import config, overflow, simulator, supply


@dataclass
class Settings:
    stock_pct: float = 100.0     # regional stock of saline and kits, % of total need (30-100)
    crews: int = 20              # larvicide / fogging crews available
    beds_pct: float = 100.0      # share of each ward's usual dengue beds that is free (30-100)
    cautious: bool = False       # plan for the top of the forecast range instead of the expected value


@dataclass
class Plan:
    settings: Settings
    wards: pd.DataFrame          # one row per ward, priority order: needs, allocations, beds, crews, flags
    supply_summary: dict
    transfers: pd.DataFrame
    cities: pd.DataFrame
    crew_plan: dict = field(default_factory=dict)
    effects: pd.DataFrame | None = None

    @property
    def alerts(self) -> pd.DataFrame:
        """Wards short of supplies or beds, in priority order (shown as live warnings)."""
        w = self.wards
        return w[(w["deficit"] != "Fully supplied") | (w["net_bed_deficit"] > 0)]


def build_plan(fc: pd.DataFrame, rows: pd.DataFrame, bundle: dict, ratios: dict, capacity: pd.Series,
               s: Settings, effects: pd.DataFrame | None = None) -> Plan:
    """fc: forecast table (Engine.forecast). rows: the same wards' feature rows (for the crew model)."""
    # Module 1: supplies
    need = supply.demand(fc, ratios, s.cautious)
    w, summary = supply.allocate(need, s.stock_pct)

    # Module 2: beds and overflow routing inside each city
    w["bed_capacity"] = w["ward_id"].map(capacity).fillna(config.MIN_WARD_BEDS).astype(int)
    w["beds_available"] = np.floor(w["bed_capacity"] * s.beds_pct / 100).astype(int)
    routed, transfers, cities = overflow.route(
        w[["ward_id", "city"]].assign(beds_needed=w["need_hospital_beds_required"], beds_available=w["beds_available"]))
    for col in ("overflow", "sent_out", "received", "net_deficit", "headroom_left", "utilisation_pct"):
        w[col if col != "net_deficit" else "net_bed_deficit"] = routed[col].to_numpy()
    w["sent_to"] = w["ward_id"].map(transfers.groupby("from_ward")["to_ward"].agg(", ".join)).fillna("")

    # Module 3 (+ crew part of module 1): each crew goes where it prevents the most cases
    if effects is None:
        effects = simulator.effect_table(bundle, rows)
    crew_plan = simulator.best_plan(effects, s.crews)
    w["crews_needed"] = w["tier"].map(config.CREWS_NEEDED).fillna(0).astype(int)
    w["crews_assigned"] = w["ward_id"].map(crew_plan).fillna(0).astype(int)
    w["crews_short"] = (w["crews_needed"] - w["crews_assigned"]).clip(lower=0)
    sim = simulator.simulate(effects, crew_plan, ratios).set_index("ward_id") if crew_plan else pd.DataFrame()
    w["cases_prevented"] = w["ward_id"].map(sim["cases_prevented"]).fillna(0.0) if len(sim) else 0.0
    return Plan(s, w, summary, transfers, cities, crew_plan, effects)

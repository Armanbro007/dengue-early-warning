"""Module 2: hospital surge. Send patients from full wards to wards with free beds,
strictly inside the same city (Dhaka North, Dhaka South, Chattogram, Gazipur,
Narayanganj). Patients never cross a city boundary.

For each city:
  1. overflow = beds needed - beds available, for every ward that is over.
     headroom = beds available - beds needed, for every ward with room.
  2. Take the ward with the biggest overflow. Send its patients to the ward with
     the most free beds, then the next, until it fits or the city has no room left.
  3. Repeat for the next overflowing ward.
What is still left over is the ward's NET deficit: the city is full and needs
extra beds (field ward, other city). Greedy, deterministic, a few ms for 60 wards.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def route(beds: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """beds: ward_id, city, beds_needed, beds_available.

    Returns (wards, transfers, cities):
      wards     + overflow, sent_out, received, net_deficit, headroom_left, utilisation_pct
      transfers  from_ward, to_ward, city, patients
      cities     beds_needed, beds_available, utilisation_pct, headroom_left, net_deficit, transfers
    """
    w = beds.copy()
    w["overflow"] = (w["beds_needed"] - w["beds_available"]).clip(lower=0).astype(int)
    w["sent_out"], w["received"] = 0, 0
    room = (w["beds_available"] - w["beds_needed"]).clip(lower=0).astype(int)
    moves = []
    for city, idx in w.groupby("city").groups.items():
        senders = w.loc[idx].sort_values("overflow", ascending=False)
        for s, row in senders[senders["overflow"] > 0].iterrows():
            left = int(row["overflow"])
            while left > 0:
                free = room.loc[idx]
                r = free.idxmax()
                if free[r] <= 0:
                    break  # the whole city is full
                n = int(min(left, free[r]))
                moves.append({"from_ward": row["ward_id"], "to_ward": w.at[r, "ward_id"], "city": city, "patients": n})
                room[r] -= n
                w.at[r, "received"] += n
                w.at[s, "sent_out"] += n
                left -= n
    w["net_deficit"] = w["overflow"] - w["sent_out"]
    w["headroom_left"] = room
    w["beds_used"] = w["beds_needed"] - w["sent_out"] + w["received"] - w["net_deficit"]
    w["utilisation_pct"] = np.where(w["beds_available"] > 0, 100 * w["beds_used"] / w["beds_available"].clip(lower=1), 0).round(0)

    transfers = pd.DataFrame(moves, columns=["from_ward", "to_ward", "city", "patients"])
    cities = w.groupby("city").agg(beds_needed=("beds_needed", "sum"), beds_available=("beds_available", "sum"),
                                   headroom_left=("headroom_left", "sum"), net_deficit=("net_deficit", "sum"),
                                   wards_over=("overflow", lambda s: int((s > 0).sum())))
    cities["transfers"] = transfers.groupby("city")["patients"].sum().reindex(cities.index).fillna(0).astype(int)
    cities["utilisation_pct"] = (100 * cities["beds_needed"] / cities["beds_available"].clip(lower=1)).round(0)
    return w, transfers, cities.reset_index()

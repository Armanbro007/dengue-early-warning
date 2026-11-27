"""Module 2: overflow patients move only inside their own city, and numbers add up."""
import pandas as pd

from dengue.overflow import route


def beds(rows):
    return pd.DataFrame(rows, columns=["ward_id", "city", "beds_needed", "beds_available"])


def test_overflow_goes_to_the_ward_with_most_room_in_the_same_city():
    w, t, c = route(beds([("A1", "A", 9, 5), ("A2", "A", 1, 4), ("A3", "A", 2, 6), ("B1", "B", 0, 50)]))
    assert set(t["city"]) == {"A"} and "B1" not in set(t["to_ward"])  # never crosses a city
    assert t.iloc[0]["to_ward"] == "A3"  # most free beds first
    assert t["patients"].sum() == 4
    assert w.set_index("ward_id").at["A1", "net_deficit"] == 0


def test_full_city_reports_net_deficit_and_zero_headroom():
    w, t, c = route(beds([("A1", "A", 10, 4), ("A2", "A", 3, 4)]))
    city = c.set_index("city").loc["A"]
    assert city["transfers"] == 1 and city["headroom_left"] == 0 and city["net_deficit"] == 5
    assert city["utilisation_pct"] == round(100 * 13 / 8)


def test_beds_are_conserved():
    w, t, c = route(beds([(f"W{i}", "X", n, a) for i, (n, a) in enumerate([(6, 2), (0, 5), (4, 4), (1, 3)])]))
    assert w["sent_out"].sum() == w["received"].sum() == t["patients"].sum()
    assert (w["beds_used"] <= w["beds_available"]).all()
    assert (w["headroom_left"] >= 0).all()

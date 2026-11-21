"""Bangla names, digits and dates shared by the dashboard and the officer briefing (no Streamlit here)."""
from __future__ import annotations

import pandas as pd

BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
MONTHS_BN = ["জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন", "জুলাই", "আগস্ট", "সেপ্টেম্বর",
             "অক্টোবর", "নভেম্বর", "ডিসেম্বর"]
CITY_BN = {"Dhaka North": "ঢাকা উত্তর", "Dhaka South": "ঢাকা দক্ষিণ", "Chattogram": "চট্টগ্রাম",
           "Gazipur": "গাজীপুর", "Narayanganj": "নারায়ণগঞ্জ", "All cities": "সব সিটি করপোরেশন"}
# City corporations, in the possessive form used in Bangla news and office letters ("ডিএনসিসির ১৯ নং ওয়ার্ড").
CORP_OF_BN = {"DNCC": "ডিএনসিসির", "DSCC": "ডিএসসিসির", "CCC": "চসিকের", "GCC": "গাসিকের", "NCC": "নাসিকের"}
TIER_BN = {"Low": "কম", "Medium": "মাঝারি", "High": "উচ্চ", "Critical": "অতি উচ্চ"}


def bn_digits(s) -> str:
    return str(s).translate(BN_DIGITS)


def bn_date(ts) -> str:
    d = pd.Timestamp(ts)
    return bn_digits(f"{d.day} {MONTHS_BN[d.month - 1]} {d.year}")


def bn_ward(ward: str) -> str:
    """'DNCC_Ward_07' or 'DNCC Ward 07' -> 'ডিএনসিসির ৭ নং ওয়ার্ড'. Anything else is returned as given."""
    parts = str(ward).replace("_", " ").split()
    if len(parts) == 3 and parts[1] == "Ward" and parts[2].isdigit():
        return f"{CORP_OF_BN.get(parts[0], parts[0])} {bn_digits(int(parts[2]))} নং ওয়ার্ড"
    return str(ward)

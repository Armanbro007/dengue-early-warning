"""English and Bangla text for the dashboard, plus number and date formatting per language.

The Bangla is written the way a Bangladeshi city corporation health office would say it, not word for word.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from dengue.i18n import BN_DIGITS, CITY_BN, MONTHS_BN, TIER_BN, bn_ward  # noqa: E402

LANGS = {"en": "EN", "bn": "বাংলা"}
_CITY_OF_BN = {"Dhaka North": "ঢাকা উত্তরের", "Dhaka South": "ঢাকা দক্ষিণের", "Chattogram": "চট্টগ্রামের",
               "Gazipur": "গাজীপুরের", "Narayanganj": "নারায়ণগঞ্জের", "All cities": "পাঁচ সিটি করপোরেশনের"}
_DRIVER = {
    "en": {"Rainfall (0-6 wks ago)": "Recent rain", "Humidity": "Humidity", "Temperature": "Temperature",
           "Ward vulnerability": "Drainage, crowding & sanitation", "Seasonal norm": "Normal for the season"},
    "bn": {"Rainfall (0-6 wks ago)": "সাম্প্রতিক বৃষ্টিপাত", "Humidity": "আর্দ্রতা", "Temperature": "তাপমাত্রা",
           "Ward vulnerability": "জলাবদ্ধতা, ঘনবসতি ও স্যানিটেশন", "Seasonal norm": "এ সময়ের স্বাভাবিক মাত্রা"},
}

TEXT = {
    "en": {
        # ---- chrome and settings
        "brand_tag": "Dengue early warning",
        "nav_early": "Early warning", "nav_more": "More", "nav_ops": "Command center",
        "page_alloc": "Supplies & crews", "page_beds": "Hospital beds", "page_sim": "What-if crews",
        "page_dispatch": "Dispatch notices",
        "page_overview": "Overview", "page_wards": "Ward priorities", "page_why": "Why this ward?",
        "page_calendar": "Season calendar", "page_live": "Live forecast", "page_accuracy": "How accurate is it?",
        "page_data": "Add weekly data",
        "settings": "Settings", "city": "City", "replay": "Pretend today is", "ahead": "Look ahead",
        "ahead_fmt": "{h} wk",
        "replay_help": "DengueWatch replays past weeks, so you can compare its warning with what really happened.",
        "ahead_help": "How far ahead to forecast. 3 weeks matches how long rain takes to turn into dengue cases.",
        "note_unseen": "<b>Replay of {date}.</b> The model never saw this week while learning, so its warning can be checked against what really happened.",
        "note_seen": "<b>{date}</b> was part of the training data (2016–2023). Pick a week in 2024 or 2025 for a fair test.",
        "status": "Speed and system status",
        "st_trained": "Models trained through **{date}** in {s} s",
        "st_load": "Data and models load in **{ms} ms** (once per server)",
        "st_calls": "Internet calls this session: **{n}** (retries {r}, failures {f})",
        "st_llm": "AI wording for briefings: **{state}**; today {c}/{b} calls, {tok} tokens",
        "st_llm_on": "on, {model}", "st_llm_off": "off (template)",
        "more": "more", "less": "less",
        "area_all": "all five cities", "area_all_long": "all five city corporations",
        # ---- shared table and chart labels
        "col_ward": "Ward", "col_city": "City", "col_today": "Today", "col_in": "In {h} weeks",
        "col_pred": "Expected cases", "col_range": "Likely range", "col_reason": "Main reason",
        "col_rain": "Rain, last 3 weeks vs normal", "col_actual": "What really happened",
        "col_actual_help": "Real cases that week. Shown when replaying past weeks.",
        "col_risk": "Risk", "col_cases": "Cases", "col_cases_help": "Expected cases",
        "rain_axis": "Rain (mm per week)",
        # ---- overview
        "ov_eyebrow": "Forecast made {date} · {h} weeks ahead",
        "ov_title": "Dengue outlook for {day}",
        "ov_card_label": "In {h} weeks",
        "ov_big_sub": "wards likely to reach high dengue risk by {day}",
        "ov_none_sub": "No ward is expected to reach high risk by {day}",
        "ov_t_critical": "Critical", "ov_t_high": "High", "ov_t_worse": "Getting worse", "ov_t_cases": "Cases expected",
        "ov_trend": "Cases across {area}",
        "ov_trend_sub": "Real weekly cases, the forecast for {day} (dot) and what really happened (ring)",
        "ov_trend_real": "Real cases", "ov_trend_fc": "Forecast",
        "ov_check": "Reality check",
        "ov_check_text": "<b>{hit} of {real}</b> wards that really reached high risk were flagged {h} weeks earlier.",
        "ov_check_future": "On 2024–2025, years it never saw, DengueWatch flagged <b>{pct}</b> of high-risk weeks in advance.",
        "ov_caught": "caught",
        "ov_cities": "By city",
        "ov_cities_sub": "Wards at high or critical risk in {h} weeks",
        "ov_act": "Act on these wards first",
        "ov_act_sub": "Calm today, expected to get much worse",
        "ov_watch": "Wards to watch",
        "ov_see_all": "See all wards",
        "ov_today": "Today", "ov_in_h": "In {h} wk",
        "ov_cases": "cases expected", "ov_likely": "likely {lo}–{hi}",
        "ov_rain": "rain",
        "ov_how": "How DengueWatch sees it coming",
        "ov_how_sub": "Dengue follows the rain by about three weeks. That delay is the warning window.",
        "step1_when": "Week 0", "step1_what": "It rains", "step1_text": "Water collects in drains, tyres and rooftops.",
        "step2_when": "Weeks 1–2", "step2_what": "Mosquitoes breed", "step2_text": "Eggs become biting Aedes mosquitoes in 7–14 days.",
        "step3_when": "Weeks 2–4", "step3_what": "People fall sick", "step3_text": "Fever, tests and hospital visits follow.",
        "step4_when": "Week 0", "step4_what": "DengueWatch warns", "step4_text": "It reads this week's rain and names the wards at risk.",
        # ---- ward priorities
        "rb_eyebrow": "Ward priorities · week of {date}",
        "rb_title": "Which wards need help first",
        "rb_lead": "All {n} wards in {area}, ranked by how many dengue cases DengueWatch expects in the week of <b>{date}</b>. "
                   "Use it to decide where larvicide teams, clean-up drives and hospital supplies go first.",
        "rb_m_crit": "Critical wards", "rb_m_crit_help": "Expected to have {n} or more cases a week",
        "rb_m_high": "High-risk wards", "rb_m_high_help": "Expected to have {a} to {b} cases a week",
        "rb_m_worse": "Getting worse",
        "rb_m_worse_help": "Low or medium risk today, but expected to be high or critical. Acting here early pays off most.",
        "rb_m_cases": "Cases expected", "rb_m_cases_help": "Total across these wards in the week of {date}",
        "rb_chart": "Top 15 wards by expected cases", "rb_chart_sub": "Bars show expected cases, thin lines the likely range",
        "rb_axis": "Expected dengue cases, week of {date}",
        "rb_hover": "<b>%{y}</b>, %{customdata[3]}<br>About %{customdata[4]} cases expected"
                    "<br>Likely %{customdata[0]}–%{customdata[1]}<br>Main reason: %{customdata[2]}",
        "rb_brief": "Action briefing", "rb_brief_sub": "A short note an officer can forward to field teams.",
        "rb_ai": "Reword with AI (optional, needs an API key)",
        "rb_ai_help": "Off: instant template. On: one cached AI call that only sees the numbers above. "
                      "Falls back to the template on any error.",
        "rb_src": "Written by: {src}. Built only from the forecast numbers.",
        "src_template": "template", "src_cache": "saved AI text", "src_llm": "AI",
        "rb_all": "All wards", "rb_all_sub": "Expected cases, the likely range and the main reason for each ward.",
        "rb_f_all": "All wards", "rb_f_high": "High and critical", "rb_f_worse": "Getting worse",
        "rb_none": "No ward matches this filter for the chosen week.",
        "rb_download": "Download the priority list (CSV)",
        # ---- why this ward
        "wd_eyebrow": "Why this ward?",
        "wd_pick": "Choose a ward (highest risk first)",
        "wd_lead": "DengueWatch expects about <b>{n} dengue cases</b> here in the week of {date} (likely {range}), compared "
                   "with about {base} for a typical ward at this time of year. {reason} It had {mm} mm of rain in the last "
                   "3 weeks, {pct}% {dir} than normal.",
        "wd_reason": "The biggest reason is <b>{d}</b>.", "wd_reason_none": "Nothing pushes it much above normal.",
        "wd_real": "What really happened", "wd_real_cases": "{n} cases",
        "wd_push": "What pushes this forecast up or down",
        "wd_push_sub": "Cases added ({r}) or removed ({l}) by this ward's own conditions.",
        "wd_right": "right", "wd_left": "left",
        "wd_norm": "Normal for the season", "wd_norm_sub": "a typical ward, typical weather", "wd_total": "Expected cases",
        "wd_shap": "Each number is an exact share of the forecast (a Shapley value), so they always add up to the total.",
        "wd_clock": "Rain now, cases later",
        "wd_clock_sub": "Shaded weeks: the rain that matters most for the forecast week",
        "wd_rain_name": "Weekly rain", "wd_rain_hover": "Week of {d}: {mm} mm",
        "wd_today": "today", "wd_fweek": "forecast<br>week",
        "wd_clock_cap": "Standing water needs 7 to 14 days to produce adult mosquitoes, then infection and symptoms "
                        "take another 1 to 2 weeks.",
        "wd_whatif": "What if this week is wetter or drier?",
        "wd_whatif_sub": "Move the slider to re-run the forecast for this ward with more or less rain this week.",
        "wd_slider": "Change in this week's rain (mm)",
        "wd_with": "With {mm} mm {dir} rain this week",
        "wd_new": "cases expected ({diff} compared with now)",
        "wd_now": "Now", "wd_with_rain": "With this rain",
        "wd_try": "Try +100 mm to see a very wet week, or −80 mm for a dry one. More rain can never lower the forecast: "
                  "the model is built that way on purpose.",
        "wd_track": "Track record in {year}",
        "wd_track_sub": "What DengueWatch forecast {h} weeks ahead for {ward}, against what really happened.",
        "wd_t_range": "Likely range", "wd_t_fc": "Forecast, made {h} weeks earlier", "wd_t_real": "Real cases",
        "wd_t_axis": "Cases per week",
        # ---- season calendar
        "hm_eyebrow": "Season calendar",
        "hm_title": "How the {year} dengue season unfolded, ward by ward",
        "hm_lead": "Each row is a ward and each column is a week from April to November. The colour shows the risk level "
                   "DengueWatch warned about {h} weeks before that week. Read left to right to see an outbreak spread "
                   "and to plan teams city by city.",
        "hm_season": "Season",
        "hm_v_fc": "What we forecast", "hm_v_real": "What really happened", "hm_v_off": "Where we were off",
        "hm_train": "{year} is part of the data the model learned from. Pick 2024 or 2025 to see forecasts on years it never saw.",
        "hm_cb": "Forecast minus real",
        "hm_hover_off": "{ward}<br>Week of {d}<br>Off by {v} cases",
        "hm_hover": "{ward}<br>Week of {d}<br>Forecast {p} cases · real {a}",
        "hm_note_off": "Warm cells: the forecast was too high. Cool cells: it was too low. Pale cells: close to right. "
                       "Most misses are a few cases in the busiest weeks.",
        "hm_note_fc": "Compare this with “What really happened” to see how closely the warnings matched reality.",
        "hm_note_real": "Real case counts, coloured with the same risk levels, so you can compare them with the forecast.",
        "hm_group": "Wards are grouped by city, busiest first.",
        # ---- live forecast
        "lv_eyebrow": "Live forecast",
        "lv_title": "This week's warning, from real weather",
        "lv_lead": "The same model, fed with this week's measured and forecast weather instead of the replayed dataset. "
                   "One internet call covers all five cities and is saved for {ttl} hours. If the connection fails, "
                   "DengueWatch uses the last saved forecast, then typical weather for this time of year.",
        "lv_spin": "Fetching weather (1 call for all cities)...",
        "lv_refresh": "Refresh weather now", "lv_refresh_help": "Skips the saved copy and makes one new call",
        "lv_src_live": "Live weather", "lv_src_cache": "Saved weather",
        "lv_src_stale-cache": "Offline: using the last saved weather", "lv_src_climatology": "Offline: using typical weather",
        "lv_section": "Expected risk in the week of {date}",
        "lv_section_sub": "Forecast made on {date}, {h} weeks ahead.",
        "lv_m": "{tier} wards",
        "lv_rain": "Weekly rain feeding the model", "lv_rain_sub": "Measured and forecast rain in each city",
        "lv_rain_hover": "{city}, week of {d}: {mm} mm",
        "lv_top": "Highest expected cases", "lv_top_sub": "The 12 wards to watch first",
        "lv_cap": "November is the dry season in Bangladesh, so live risk is expected to be low now. "
                  "The same steps turn monsoon rain into early warnings from June onward.",
        # ---- accuracy
        "ac_eyebrow": "How accurate is it?",
        "ac_title": "Tested on two years it had never seen",
        "ac_lead": "DengueWatch learned from 2016–2023. It was then scored once on <b>2024 and 2025</b>, using only the data "
                   "that would have been available each week. Nothing was shuffled, so it could never peek at the future. "
                   "Numbers below are for forecasts <b>{h} weeks ahead</b>.",
        "ac_c1_label": "cases per ward per week",
        "ac_c1_text": "Average miss in the monsoon season (June–October). A simple “same as this week” guess misses by {p}, "
                      "so DengueWatch is {pct}% closer.",
        "ac_c2_label": "of high-risk weeks caught",
        "ac_c2_text": "Of all the ward-weeks that really turned high or critical, this share was flagged in advance.",
        "ac_c3_label": "inside the likely range",
        "ac_c3_text": "How often the real count landed inside the range we show. We aim for 80%, so the ranges are honest.",
        "ac_c4_big": "{w} of {n}", "ac_c4_label": "years beaten",
        "ac_c4_all": "Re-trained each year from {a} to {b} on earlier years only, it beat the simple guess every time.",
        "ac_c4_some": "Years in which it beat the simple guess, re-trained each year on earlier years only.",
        "ac_bt": "Better than a simple guess, every year", "ac_bt_sub": "Average miss per ward per week. Lower is better.",
        "ac_simple": "Simple guess (same as this week)", "ac_miss_axis": "Average miss (cases)",
        "ac_bt_hover": "{y}: misses by {v} cases",
        "ac_lag": "Why three weeks?", "ac_lag_sub": "How closely cases follow the weather of earlier weeks.",
        "var_Rainfall": "Rainfall", "var_Temperature": "Temperature", "var_Humidity": "Humidity",
        "ac_peak": "rain peaks at {n} weeks",
        "ac_lag_x": "Weeks between the weather and the cases", "ac_lag_y": "Correlation",
        "ac_lag_cap": "Rain lines up with dengue cases best about 3 weeks later: the time for water to breed mosquitoes, "
                      "plus infection and symptoms. That is why the default forecast looks 3 weeks ahead.",
        "ac_tech": "Technical details: error metrics, baselines and the tier confusion matrix",
        "ac_m_model": "DengueWatch", "ac_m_persist": "Naive: same as this week", "ac_m_last": "Naive: same week last year",
        "ac_col_h": "Horizon", "ac_col_m": "Method", "ac_col_mae_s": "MAE Jun–Oct", "ac_col_mae": "MAE all weeks",
        "ac_col_rmse": "RMSE", "ac_col_tacc": "Tier accuracy", "ac_col_rec": "High/Critical recall",
        "ac_weeks": "{h} weeks",
        "ac_table": "**Test set 2024–2025 against simple baselines** (MAE and RMSE in cases per ward per week)",
        "ac_scatter": "Forecast against real cases, 2024–2025", "ac_real": "Real cases", "ac_fc": "Forecast cases",
        "ac_cm": "Risk level: real (rows) vs forecast (columns)", "ac_cm_x": "Forecast level", "ac_cm_y": "Real level",
        "ac_speed": "Speed: shipped models train in {t} s on a laptop CPU; all 60 wards are scored in {ms} ms; "
                    "the model file is {kb} KB.",
        # ---- add weekly data
        "du_eyebrow": "Add weekly data",
        "du_title": "Keep the forecast up to date",
        "du_lead": "Each week, a health office uploads the latest ward reports: cases and weather. DengueWatch checks the "
                   "file, adds it and re-learns in about 15 seconds. New rows are kept apart from the official dataset, "
                   "so you can always go back.",
        "du_m_wards": "Wards", "du_m_latest": "Latest week in the data", "du_m_trained": "Model has learned up to",
        "du_steps": "Three steps", "du_steps_sub": "Problems are listed before anything is changed.",
        "du_step": "Step {n}",
        "du_s1": "Download the template", "du_s1_t": "It has the right columns and the latest week as an example.",
        "du_s2": "Fill in the new week", "du_s2_t": "One row per ward: cases, rain, humidity and temperature.",
        "du_s3": "Upload, check and retrain", "du_s3_t": "DengueWatch checks every row, then re-learns in seconds.",
        "du_dl": "Download the template (CSV)",
        "du_up": "Upload new weekly rows (CSV with the same columns as the official dataset)",
        "du_bad": "This file can't be used: {e}",
        "du_ok": "{rows} rows look good: {new} new and {rep} that update existing values. Weeks {a} to {b}.",
        "du_apply": "Add these rows and retrain", "du_spin": "Adding rows and retraining...",
        "du_done": "Done. The model has now learned up to {d} ({s} s). Pick the new week under “{replay}” to see its forecast.",
        "du_reset": "Go back to the official dataset",
        "du_reset_done": "Uploaded rows removed. The model has learned up to {d}.",
    },
    "bn": {
        # ---- chrome and settings
        "brand_tag": "ডেঙ্গু আগাম সতর্কতা ব্যবস্থা",
        "nav_early": "আগাম সতর্কতা", "nav_more": "অন্যান্য", "nav_ops": "কমান্ড সেন্টার",
        "page_alloc": "সরবরাহ ও স্প্রে দল", "page_beds": "হাসপাতালের শয্যা", "page_sim": "স্প্রে দলের প্রভাব",
        "page_dispatch": "নির্দেশনা পাঠানো",
        "page_overview": "সার্বিক চিত্র", "page_wards": "ওয়ার্ডভিত্তিক অগ্রাধিকার", "page_why": "ঝুঁকির কারণ",
        "page_calendar": "মৌসুমের চিত্র", "page_live": "চলতি পূর্বাভাস", "page_accuracy": "পূর্বাভাসের নির্ভুলতা",
        "page_data": "সাপ্তাহিক তথ্য হালনাগাদ",
        "settings": "সেটিংস", "city": "সিটি করপোরেশন", "replay": "পূর্বাভাসের তারিখ", "ahead": "পূর্বাভাসের সময়সীমা",
        "ahead_fmt": "{h} সপ্তাহ",
        "replay_help": "পুরোনো যেকোনো সপ্তাহ বেছে নিন। সে সময় DengueWatch কী সতর্কতা দিত আর বাস্তবে কী ঘটেছিল, "
                       "দুটো মিলিয়ে দেখতে পারবেন।",
        "ahead_help": "কত সপ্তাহ আগের পূর্বাভাস দেখতে চান। বৃষ্টির পর ডেঙ্গু রোগী বাড়তে সাধারণত তিন সপ্তাহের মতো সময় লাগে।",
        "note_unseen": "<b>{date} সপ্তাহের পর্যালোচনা।</b> মডেল প্রশিক্ষণে এই সপ্তাহের তথ্য ব্যবহার করা হয়নি, "
                       "তাই পূর্বাভাসটি প্রকৃত তথ্যের সঙ্গে নিরপেক্ষভাবে মিলিয়ে দেখা যায়।",
        "note_seen": "<b>{date}</b> সপ্তাহের তথ্য মডেল প্রশিক্ষণে ব্যবহৃত হয়েছে (২০১৬–২০২৩)। নিরপেক্ষ যাচাইয়ের জন্য "
                     "২০২৪ বা ২০২৫ সালের কোনো সপ্তাহ বেছে নিন।",
        "status": "সিস্টেমের অবস্থা ও গতি",
        "st_trained": "মডেল **{date}** পর্যন্ত তথ্যে প্রশিক্ষিত, সময় লেগেছে {s} সেকেন্ড",
        "st_load": "তথ্য ও মডেল লোড হতে লাগে **{ms} মিলিসেকেন্ড** (সার্ভার চালুর সময় একবার)",
        "st_calls": "এই সেশনে ইন্টারনেট কল: **{n}টি** (পুনরায় চেষ্টা {r}, ব্যর্থ {f})",
        "st_llm": "ব্রিফিংয়ে এআই-এর ভাষা: **{state}**; আজ {c}/{b}টি কল, {tok} টোকেন",
        "st_llm_on": "চালু, {model}", "st_llm_off": "বন্ধ (টেমপ্লেট)",
        "more": "বেশি", "less": "কম",
        "area_all": "পাঁচ সিটি করপোরেশন", "area_all_long": "পাঁচ সিটি করপোরেশন",
        # ---- shared table and chart labels
        "col_ward": "ওয়ার্ড", "col_city": "সিটি করপোরেশন", "col_today": "এখন", "col_in": "{h} সপ্তাহ পর",
        "col_pred": "সম্ভাব্য রোগী", "col_range": "সম্ভাব্য পরিসর", "col_reason": "প্রধান কারণ",
        "col_rain": "গত ৩ সপ্তাহের বৃষ্টি (স্বাভাবিকের তুলনায়)", "col_actual": "প্রকৃত রোগী",
        "col_actual_help": "ওই সপ্তাহে প্রকৃত শনাক্ত রোগী। অতীতের সপ্তাহ বাছাই করলে দেখা যায়।",
        "col_risk": "ঝুঁকি", "col_cases": "রোগী", "col_cases_help": "সম্ভাব্য রোগী",
        "rain_axis": "বৃষ্টিপাত (মিমি/সপ্তাহ)",
        # ---- overview
        "ov_eyebrow": "{date} তারিখে প্রকাশিত · {h} সপ্তাহের আগাম পূর্বাভাস",
        "ov_title": "{day} নাগাদ ডেঙ্গু পরিস্থিতি",
        "ov_card_label": "আগামী {h} সপ্তাহে",
        "ov_big_sub": "ওয়ার্ডে {day} নাগাদ ডেঙ্গুর উচ্চ ঝুঁকি দেখা দিতে পারে",
        "ov_none_sub": "{day} নাগাদ কোনো ওয়ার্ডে উচ্চ ঝুঁকির আশঙ্কা নেই",
        "ov_t_critical": "অতি উচ্চ ঝুঁকি", "ov_t_high": "উচ্চ ঝুঁকি", "ov_t_worse": "ঝুঁকি বাড়ছে",
        "ov_t_cases": "সম্ভাব্য রোগী",
        "ov_trend": "{area_of} সাপ্তাহিক রোগী",
        "ov_trend_sub": "প্রতি সপ্তাহে শনাক্ত রোগী, সঙ্গে {day} তারিখের পূর্বাভাস (বিন্দু) ও প্রকৃত সংখ্যা (বৃত্ত)",
        "ov_trend_real": "শনাক্ত রোগী", "ov_trend_fc": "পূর্বাভাস",
        "ov_check": "পূর্বাভাস কতটা মিলেছে",
        "ov_check_text": "বাস্তবে উচ্চ ঝুঁকিতে পৌঁছানো {real}টি ওয়ার্ডের মধ্যে <b>{hit}টি</b> {h} সপ্তাহ আগেই "
                         "চিহ্নিত করা গিয়েছিল।",
        "ov_check_future": "মডেলের কাছে অজানা ২০২৪–২০২৫ সালের তথ্যে উচ্চ ঝুঁকির সপ্তাহগুলোর <b>{pct}</b> "
                           "আগেভাগেই শনাক্ত হয়েছে।",
        "ov_caught": "শনাক্ত",
        "ov_cities": "সিটি করপোরেশনভিত্তিক চিত্র",
        "ov_cities_sub": "{h} সপ্তাহ পর উচ্চ বা অতি উচ্চ ঝুঁকিতে থাকা ওয়ার্ড",
        "ov_act": "যেসব ওয়ার্ডে অগ্রাধিকার ভিত্তিতে ব্যবস্থা নিতে হবে",
        "ov_act_sub": "বর্তমানে পরিস্থিতি নিয়ন্ত্রণে, তবে দ্রুত অবনতির আশঙ্কা",
        "ov_watch": "যেসব ওয়ার্ড নজরে রাখতে হবে",
        "ov_see_all": "সব ওয়ার্ডের তালিকা দেখুন",
        "ov_today": "এখন", "ov_in_h": "{h} সপ্তাহ পর",
        "ov_cases": "জন সম্ভাব্য রোগী", "ov_likely": "সম্ভাব্য {lo}–{hi} জন",
        "ov_rain": "বৃষ্টিপাত",
        "ov_how": "DengueWatch কীভাবে আগাম সতর্ক করে",
        "ov_how_sub": "বৃষ্টির প্রায় তিন সপ্তাহ পর ডেঙ্গু রোগী বাড়ে। এই সময়টুকুই প্রস্তুতি নেওয়ার সুযোগ।",
        "step1_when": "প্রথম সপ্তাহ", "step1_what": "বৃষ্টিপাত",
        "step1_text": "নালা, পরিত্যক্ত টায়ার, ফুলের টব ও ছাদে পানি জমে।",
        "step2_when": "১–২ সপ্তাহ পর", "step2_what": "এডিস মশার প্রজনন",
        "step2_text": "জমা পানিতে ৭–১৪ দিনের মধ্যে ডিম থেকে পূর্ণাঙ্গ মশা হয়।",
        "step3_when": "২–৪ সপ্তাহ পর", "step3_what": "রোগী বাড়ে",
        "step3_text": "জ্বর, পরীক্ষা ও হাসপাতালে ভর্তি বাড়তে থাকে।",
        "step4_when": "প্রথম সপ্তাহেই", "step4_what": "DengueWatch-এর সতর্কতা",
        "step4_text": "এ সপ্তাহের বৃষ্টির তথ্য দেখেই ঝুঁকিপূর্ণ ওয়ার্ড চিহ্নিত করে।",
        # ---- ward priorities
        "rb_eyebrow": "ওয়ার্ডভিত্তিক অগ্রাধিকার · {date} থেকে শুরু হওয়া সপ্তাহ",
        "rb_title": "কোন ওয়ার্ডে আগে ব্যবস্থা নিতে হবে",
        "rb_lead": "{area_of} মোট {n}টি ওয়ার্ড, <b>{date}</b> থেকে শুরু হওয়া সপ্তাহে সম্ভাব্য ডেঙ্গু রোগীর সংখ্যা "
                   "অনুযায়ী সাজানো। লার্ভিসাইডিং দল, পরিচ্ছন্নতা অভিযান ও হাসপাতালের সরবরাহ কোথায় আগে পাঠাতে হবে, "
                   "তা ঠিক করতে এই তালিকা ব্যবহার করুন।",
        "rb_m_crit": "অতি উচ্চ ঝুঁকির ওয়ার্ড", "rb_m_crit_help": "সপ্তাহে {n} বা তার বেশি রোগীর আশঙ্কা",
        "rb_m_high": "উচ্চ ঝুঁকির ওয়ার্ড", "rb_m_high_help": "সপ্তাহে {a}–{b} জন রোগীর আশঙ্কা",
        "rb_m_worse": "ঝুঁকি বাড়ছে",
        "rb_m_worse_help": "এখন ঝুঁকি কম বা মাঝারি, তবে উচ্চ বা অতি উচ্চ ঝুঁকিতে পৌঁছানোর আশঙ্কা। এসব ওয়ার্ডে "
                           "আগেভাগে ব্যবস্থা নিলে সবচেয়ে বেশি সুফল মেলে।",
        "rb_m_cases": "সম্ভাব্য রোগী", "rb_m_cases_help": "{date} থেকে শুরু হওয়া সপ্তাহে এসব ওয়ার্ডে মোট",
        "rb_chart": "সম্ভাব্য রোগী অনুযায়ী শীর্ষ ১৫ ওয়ার্ড", "rb_chart_sub": "দণ্ডে সম্ভাব্য রোগী, সরু রেখায় সম্ভাব্য পরিসর",
        "rb_axis": "সম্ভাব্য ডেঙ্গু রোগী ({date} থেকে শুরু হওয়া সপ্তাহ)",
        "rb_hover": "<b>%{y}</b>, %{customdata[3]}<br>সম্ভাব্য রোগী: আনুমানিক %{customdata[4]} জন"
                    "<br>সম্ভাব্য পরিসর: %{customdata[0]}–%{customdata[1]} জন<br>প্রধান কারণ: %{customdata[2]}",
        "rb_brief": "করণীয় নির্দেশনা", "rb_brief_sub": "মাঠপর্যায়ের দলকে পাঠানোর উপযোগী সংক্ষিপ্ত নির্দেশনা।",
        "rb_ai": "এআই দিয়ে ভাষা সাজান (ঐচ্ছিক, API key লাগবে)",
        "rb_ai_help": "বন্ধ থাকলে তাৎক্ষণিক টেমপ্লেট। চালু করলে একটি এআই কল হয়, যা শুধু ওপরের সংখ্যাগুলো দেখে এবং "
                      "ফল সংরক্ষিত থাকে। কোনো সমস্যা হলে টেমপ্লেটেই ফিরে যায়।",
        "rb_src": "লিখেছে: {src}। শুধু পূর্বাভাসের সংখ্যা থেকে তৈরি।",
        "src_template": "টেমপ্লেট", "src_cache": "সংরক্ষিত এআই লেখা", "src_llm": "এআই",
        "rb_all": "সব ওয়ার্ড", "rb_all_sub": "প্রতিটি ওয়ার্ডের সম্ভাব্য রোগী, সম্ভাব্য পরিসর ও প্রধান কারণ।",
        "rb_f_all": "সব ওয়ার্ড", "rb_f_high": "উচ্চ ও অতি উচ্চ ঝুঁকি", "rb_f_worse": "ঝুঁকি বাড়ছে",
        "rb_none": "এ সপ্তাহে বাছাই করা শর্তে কোনো ওয়ার্ড নেই।",
        "rb_download": "অগ্রাধিকার তালিকা ডাউনলোড (CSV)",
        # ---- why this ward
        "wd_eyebrow": "ঝুঁকির কারণ",
        "wd_pick": "ওয়ার্ড বাছাই করুন (বেশি ঝুঁকির ওয়ার্ড আগে)",
        "wd_lead": "{date} থেকে শুরু হওয়া সপ্তাহে এই ওয়ার্ডে আনুমানিক <b>{n} জন ডেঙ্গু রোগী</b> শনাক্ত হতে পারে "
                   "(সম্ভাব্য {range} জন)। এ সময়ে একটি সাধারণ ওয়ার্ডে রোগী থাকে আনুমানিক {base} জন। {reason} "
                   "গত ৩ সপ্তাহে এখানে {mm} মিলিমিটার বৃষ্টি হয়েছে, যা স্বাভাবিকের চেয়ে {pct}% {dir}।",
        "wd_reason": "ঝুঁকি বাড়ার প্রধান কারণ <b>{d}</b>।",
        "wd_reason_none": "স্বাভাবিকের চেয়ে ঝুঁকি বাড়ানোর মতো বড় কোনো কারণ নেই।",
        "wd_real": "প্রকৃত পরিস্থিতি", "wd_real_cases": "{n} জন রোগী",
        "wd_push": "কোন কারণে পূর্বাভাস বাড়ছে বা কমছে",
        "wd_push_sub": "এই ওয়ার্ডের নিজস্ব পরিস্থিতির কারণে যত রোগী বাড়ছে ({r}) বা কমছে ({l})।",
        "wd_right": "ডানে", "wd_left": "বাঁয়ে",
        "wd_norm": "এ সময়ের স্বাভাবিক মাত্রা", "wd_norm_sub": "সাধারণ ওয়ার্ড, স্বাভাবিক আবহাওয়া",
        "wd_total": "সম্ভাব্য রোগী",
        "wd_shap": "প্রতিটি সংখ্যা পূর্বাভাসের নির্দিষ্ট অংশ (শ্যাপলি ভ্যালু), তাই সব যোগ করলে মোট সংখ্যাই পাওয়া যায়।",
        "wd_clock": "আজকের বৃষ্টি, কয়েক সপ্তাহ পরের রোগী",
        "wd_clock_sub": "ছায়াঘেরা সপ্তাহগুলোর বৃষ্টিই পূর্বাভাসের সপ্তাহের জন্য সবচেয়ে গুরুত্বপূর্ণ",
        "wd_rain_name": "সাপ্তাহিক বৃষ্টিপাত", "wd_rain_hover": "{d} থেকে শুরু সপ্তাহ: {mm} মিমি",
        "wd_today": "আজ", "wd_fweek": "পূর্বাভাসের<br>সপ্তাহ",
        "wd_clock_cap": "জমা পানিতে ডিম থেকে পূর্ণাঙ্গ মশা হতে ৭–১৪ দিন লাগে, এরপর সংক্রমণ ও উপসর্গ দেখা দিতে "
                        "আরও ১–২ সপ্তাহ।",
        "wd_whatif": "এ সপ্তাহে বৃষ্টি বেশি বা কম হলে কী হবে?",
        "wd_whatif_sub": "স্লাইডার সরিয়ে দেখুন, এ সপ্তাহে বৃষ্টি বাড়লে বা কমলে এই ওয়ার্ডের পূর্বাভাস কীভাবে বদলায়।",
        "wd_slider": "এ সপ্তাহের বৃষ্টিতে পরিবর্তন (মিমি)",
        "wd_with": "এ সপ্তাহে {mm} মিমি বৃষ্টি {dir} হলে",
        "wd_new": "জন সম্ভাব্য রোগী (এখনকার তুলনায় {diff})",
        "wd_now": "এখন", "wd_with_rain": "এই বৃষ্টিতে",
        "wd_try": "খুব বৃষ্টির সপ্তাহ দেখতে +১০০ মিমি, আর শুকনো সপ্তাহ দেখতে −৮০ মিমি দিয়ে দেখুন। বৃষ্টি বাড়লে "
                  "পূর্বাভাস কখনো কমে না; মডেলটি ইচ্ছা করেই এভাবে তৈরি।",
        "wd_track": "{year} সালে পূর্বাভাস কতটা মিলেছে",
        "wd_track_sub": "{ward}: {h} সপ্তাহ আগে দেওয়া পূর্বাভাস বনাম প্রকৃত রোগী।",
        "wd_t_range": "সম্ভাব্য পরিসর", "wd_t_fc": "{h} সপ্তাহ আগের পূর্বাভাস", "wd_t_real": "প্রকৃত রোগী",
        "wd_t_axis": "সাপ্তাহিক রোগী",
        # ---- season calendar
        "hm_eyebrow": "মৌসুমের চিত্র",
        "hm_title": "{year} সালের ডেঙ্গু মৌসুম: ওয়ার্ডভিত্তিক চিত্র",
        "hm_lead": "প্রতিটি সারি একটি ওয়ার্ড, প্রতিটি কলাম এপ্রিল থেকে নভেম্বরের একটি সপ্তাহ। রং দেখায়, ওই সপ্তাহের "
                   "{h} সপ্তাহ আগে DengueWatch কোন মাত্রার ঝুঁকির সতর্কতা দিয়েছিল। বাঁ থেকে ডানে দেখলে বোঝা যায় "
                   "প্রাদুর্ভাব কীভাবে ছড়িয়েছে, আর সিটি করপোরেশনভিত্তিক দল পরিকল্পনাও সহজ হয়।",
        "hm_season": "মৌসুম (সাল)",
        "hm_v_fc": "পূর্বাভাস", "hm_v_real": "প্রকৃত পরিস্থিতি", "hm_v_off": "পূর্বাভাসের ভুল",
        "hm_train": "{year} সালের তথ্য মডেল প্রশিক্ষণে ব্যবহৃত হয়েছে। মডেলের অজানা বছরের পূর্বাভাস দেখতে "
                    "২০২৪ বা ২০২৫ বেছে নিন।",
        "hm_cb": "পূর্বাভাস − প্রকৃত",
        "hm_hover_off": "{ward}<br>{d} থেকে শুরু সপ্তাহ<br>পার্থক্য {v} জন",
        "hm_hover": "{ward}<br>{d} থেকে শুরু সপ্তাহ<br>পূর্বাভাস {p} জন · প্রকৃত {a} জন",
        "hm_note_off": "কমলা ঘর: পূর্বাভাস বেশি ছিল। নীলচে ঘর: কম ছিল। হালকা ঘর: প্রায় সঠিক। বেশির ভাগ ভুল "
                       "সবচেয়ে ব্যস্ত সপ্তাহগুলোতে, তা-ও কয়েকজন রোগীর।",
        "hm_note_fc": "সতর্কতা বাস্তবের সঙ্গে কতটা মিলেছে, তা দেখতে “প্রকৃত পরিস্থিতি” অংশের সঙ্গে মিলিয়ে নিন।",
        "hm_note_real": "প্রকৃত রোগীর সংখ্যা, একই ঝুঁকির রঙে দেখানো, যাতে পূর্বাভাসের সঙ্গে সহজে তুলনা করা যায়।",
        "hm_group": "ওয়ার্ডগুলো সিটি করপোরেশন অনুযায়ী সাজানো, বেশি রোগীর ওয়ার্ড আগে।",
        # ---- live forecast
        "lv_eyebrow": "চলতি পূর্বাভাস",
        "lv_title": "সর্বশেষ আবহাওয়ার তথ্যে এ সপ্তাহের সতর্কতা",
        "lv_lead": "একই মডেল, তবে পুরোনো ডেটাসেটের বদলে এ সপ্তাহের মাপা ও পূর্বাভাসিত আবহাওয়ার তথ্য দিয়ে চালানো। "
                   "একটি ইন্টারনেট কলেই পাঁচ সিটি করপোরেশনের তথ্য আসে এবং তা {ttl} ঘণ্টা সংরক্ষিত থাকে। সংযোগ না পেলে "
                   "DengueWatch সর্বশেষ সংরক্ষিত তথ্য, তা-ও না থাকলে এ সময়ের স্বাভাবিক আবহাওয়া ব্যবহার করে।",
        "lv_spin": "আবহাওয়ার তথ্য আনা হচ্ছে (সব সিটির জন্য একটি কল)...",
        "lv_refresh": "আবহাওয়ার তথ্য হালনাগাদ করুন", "lv_refresh_help": "সংরক্ষিত তথ্য বাদ দিয়ে নতুন করে একবার তথ্য আনে",
        "lv_src_live": "সরাসরি আবহাওয়ার তথ্য", "lv_src_cache": "সংরক্ষিত আবহাওয়ার তথ্য",
        "lv_src_stale-cache": "অফলাইন: সর্বশেষ সংরক্ষিত তথ্য ব্যবহার করা হচ্ছে",
        "lv_src_climatology": "অফলাইন: এ সময়ের স্বাভাবিক আবহাওয়া ব্যবহার করা হচ্ছে",
        "lv_msg_live": "Open-Meteo থেকে সরাসরি পূর্বাভাস: পাঁচ সিটি করপোরেশনের জন্য একটি API কল।",
        "lv_msg_cache": "{age} ঘণ্টা আগে সংরক্ষিত পূর্বাভাস (প্রতি {ttl} ঘণ্টায় হালনাগাদ হয়)। কোনো API কল লাগেনি।",
        "lv_msg_stale-cache": "আবহাওয়ার API-তে সংযোগ পাওয়া যাচ্ছে না। {age} ঘণ্টা আগের সর্বশেষ সংরক্ষিত পূর্বাভাস "
                              "ব্যবহার করা হচ্ছে।",
        "lv_msg_climatology": "আবহাওয়ার API-তে সংযোগ পাওয়া যাচ্ছে না, সংরক্ষিত পূর্বাভাসও নেই। এ সময়ের স্বাভাবিক "
                              "আবহাওয়া ব্যবহার করা হচ্ছে।",
        "lv_section": "{date} থেকে শুরু হওয়া সপ্তাহের সম্ভাব্য ঝুঁকি",
        "lv_section_sub": "পূর্বাভাস দেওয়া হয়েছে {date}, {h} সপ্তাহ আগে।",
        "lv_m": "{tier} ঝুঁকির ওয়ার্ড",
        "lv_rain": "মডেলে ব্যবহৃত সাপ্তাহিক বৃষ্টিপাত", "lv_rain_sub": "প্রতিটি সিটি করপোরেশনের মাপা ও পূর্বাভাসিত বৃষ্টি",
        "lv_rain_hover": "{city}, {d} থেকে শুরু সপ্তাহ: {mm} মিমি",
        "lv_top": "সম্ভাব্য রোগী সবচেয়ে বেশি", "lv_top_sub": "আগে নজর দেওয়ার মতো ১২টি ওয়ার্ড",
        "lv_cap": "নভেম্বরে বাংলাদেশে শুষ্ক মৌসুম, তাই এখন ঝুঁকি কম থাকাই স্বাভাবিক। জুন থেকে বর্ষার বৃষ্টি শুরু হলে "
                  "একই প্রক্রিয়ায় আগাম সতর্কতা পাওয়া যাবে।",
        # ---- accuracy
        "ac_eyebrow": "পূর্বাভাসের নির্ভুলতা",
        "ac_title": "মডেলের অজানা দুই বছরের তথ্যে যাচাই",
        "ac_lead": "DengueWatch ২০১৬–২০২৩ সালের তথ্য থেকে শিখেছে। এরপর <b>২০২৪ ও ২০২৫</b> সালের তথ্যে একবারই যাচাই "
                   "করা হয়েছে, যেখানে প্রতি সপ্তাহে কেবল সে সময় পর্যন্ত পাওয়া তথ্যই ব্যবহার করা হয়েছে। তথ্য এলোমেলো "
                   "করা হয়নি, তাই ভবিষ্যতের তথ্য আগেভাগে দেখার সুযোগ ছিল না। নিচের সংখ্যাগুলো <b>{h} সপ্তাহের আগাম</b> "
                   "পূর্বাভাসের।",
        "ac_c1_label": "জন রোগী, প্রতি ওয়ার্ডে প্রতি সপ্তাহে",
        "ac_c1_text": "বর্ষা মৌসুমে (জুন–অক্টোবর) গড় ভুল। “এ সপ্তাহের মতোই থাকবে” ধরে নেওয়া সাধারণ অনুমানে ভুল হয় "
                      "{p} জন, অর্থাৎ DengueWatch {pct}% বেশি নির্ভুল।",
        "ac_c2_label": "উচ্চ ঝুঁকির সপ্তাহ আগেই শনাক্ত",
        "ac_c2_text": "যেসব ওয়ার্ডে যে সপ্তাহগুলোতে বাস্তবে উচ্চ বা অতি উচ্চ ঝুঁকি দেখা দিয়েছিল, তার এই অংশ "
                      "আগেভাগেই চিহ্নিত হয়েছিল।",
        "ac_c3_label": "সম্ভাব্য পরিসরের মধ্যে",
        "ac_c3_text": "প্রকৃত রোগীর সংখ্যা কতবার দেখানো পরিসরের মধ্যে ছিল। লক্ষ্য ৮০%, তাই পরিসরগুলো বাস্তবসম্মত।",
        "ac_c4_big": "{n}টির মধ্যে {w}টি", "ac_c4_label": "বছরেই সাধারণ অনুমানের চেয়ে ভালো",
        "ac_c4_all": "{a} থেকে {b} পর্যন্ত প্রতিবছর শুধু আগের বছরগুলোর তথ্যে নতুন করে প্রশিক্ষণ দেওয়া হয়েছে, "
                     "এবং প্রতিবারই সাধারণ অনুমানের চেয়ে ভালো ফল দিয়েছে।",
        "ac_c4_some": "যে কয় বছর সাধারণ অনুমানের চেয়ে ভালো ফল দিয়েছে (প্রতিবছর শুধু আগের বছরগুলোর তথ্যে প্রশিক্ষিত)।",
        "ac_bt": "প্রতিবছরই সাধারণ অনুমানের চেয়ে ভালো", "ac_bt_sub": "প্রতি ওয়ার্ডে প্রতি সপ্তাহে গড় ভুল। যত কম, তত ভালো।",
        "ac_simple": "সাধারণ অনুমান (এ সপ্তাহের মতোই)", "ac_miss_axis": "গড় ভুল (রোগী)",
        "ac_bt_hover": "{y}: গড় ভুল {v} জন",
        "ac_lag": "কেন তিন সপ্তাহ?", "ac_lag_sub": "আগের সপ্তাহগুলোর আবহাওয়ার সঙ্গে রোগীর সংখ্যার মিল কতটা।",
        "var_Rainfall": "বৃষ্টিপাত", "var_Temperature": "তাপমাত্রা", "var_Humidity": "আর্দ্রতা",
        "ac_peak": "বৃষ্টির প্রভাব সবচেয়ে বেশি {n} সপ্তাহ পর",
        "ac_lag_x": "আবহাওয়া ও রোগীর মধ্যে ব্যবধান (সপ্তাহ)", "ac_lag_y": "সহসম্পর্ক",
        "ac_lag_cap": "বৃষ্টির প্রায় ৩ সপ্তাহ পর ডেঙ্গু রোগীর সঙ্গে সবচেয়ে বেশি মিল দেখা যায়: জমা পানিতে মশা জন্মাতে "
                      "এবং সংক্রমণের পর উপসর্গ দেখা দিতে এই সময় লাগে। তাই পূর্বাভাস সাধারণত ৩ সপ্তাহ আগে দেওয়া হয়।",
        "ac_tech": "কারিগরি বিবরণ: ত্রুটির মাপকাঠি, তুলনামূলক পদ্ধতি ও কনফিউশন ম্যাট্রিক্স",
        "ac_m_model": "DengueWatch", "ac_m_persist": "সাধারণ অনুমান: এ সপ্তাহের মতো",
        "ac_m_last": "সাধারণ অনুমান: গত বছরের একই সপ্তাহ",
        "ac_col_h": "সময়সীমা", "ac_col_m": "পদ্ধতি", "ac_col_mae_s": "MAE (জুন–অক্টোবর)", "ac_col_mae": "MAE (সব সপ্তাহ)",
        "ac_col_rmse": "RMSE", "ac_col_tacc": "ঝুঁকির মাত্রায় নির্ভুলতা", "ac_col_rec": "উচ্চ/অতি উচ্চ শনাক্তের হার",
        "ac_weeks": "{h} সপ্তাহ",
        "ac_table": "**২০২৪–২০২৫ সালের যাচাই: সাধারণ অনুমানের সঙ্গে তুলনা** (MAE ও RMSE: প্রতি ওয়ার্ডে প্রতি সপ্তাহে রোগী)",
        "ac_scatter": "পূর্বাভাস বনাম প্রকৃত রোগী, ২০২৪–২০২৫", "ac_real": "প্রকৃত রোগী", "ac_fc": "পূর্বাভাসিত রোগী",
        "ac_cm": "ঝুঁকির মাত্রা: প্রকৃত (সারি) বনাম পূর্বাভাস (কলাম)", "ac_cm_x": "পূর্বাভাসের মাত্রা",
        "ac_cm_y": "প্রকৃত মাত্রা",
        "ac_speed": "গতি: সাধারণ ল্যাপটপের সিপিইউতে মডেল প্রশিক্ষণে লাগে {t} সেকেন্ড; ৬০টি ওয়ার্ডের পূর্বাভাস হয় "
                    "{ms} মিলিসেকেন্ডে; মডেল ফাইলের আকার {kb} কেবি।",
        # ---- add weekly data
        "du_eyebrow": "সাপ্তাহিক তথ্য হালনাগাদ",
        "du_title": "পূর্বাভাস হালনাগাদ রাখুন",
        "du_lead": "প্রতি সপ্তাহে স্বাস্থ্য বিভাগ ওয়ার্ডভিত্তিক সর্বশেষ তথ্য (রোগী ও আবহাওয়া) আপলোড করে। DengueWatch "
                   "ফাইলটি যাচাই করে, তথ্য যুক্ত করে এবং প্রায় ১৫ সেকেন্ডে মডেলকে নতুন করে প্রশিক্ষণ দেয়। নতুন তথ্য মূল "
                   "ডেটাসেট থেকে আলাদা রাখা হয়, তাই যেকোনো সময় আগের অবস্থায় ফেরা যায়।",
        "du_m_wards": "ওয়ার্ড", "du_m_latest": "তথ্যের সর্বশেষ সপ্তাহ", "du_m_trained": "প্রশিক্ষণে ব্যবহৃত শেষ সপ্তাহ",
        "du_steps": "তিনটি ধাপ", "du_steps_sub": "কোনো পরিবর্তনের আগেই সমস্যাগুলো তালিকা আকারে দেখানো হয়।",
        "du_step": "ধাপ {n}",
        "du_s1": "টেমপ্লেট ডাউনলোড করুন", "du_s1_t": "এতে সঠিক কলাম এবং উদাহরণ হিসেবে সর্বশেষ সপ্তাহের তথ্য আছে।",
        "du_s2": "নতুন সপ্তাহের তথ্য পূরণ করুন", "du_s2_t": "প্রতিটি ওয়ার্ডের জন্য এক সারি: রোগী, বৃষ্টিপাত, আর্দ্রতা ও তাপমাত্রা।",
        "du_s3": "আপলোড, যাচাই ও পুনঃপ্রশিক্ষণ", "du_s3_t": "প্রতিটি সারি যাচাইয়ের পর কয়েক সেকেন্ডেই মডেল নতুন করে শেখে।",
        "du_dl": "টেমপ্লেট ডাউনলোড (CSV)",
        "du_up": "নতুন সাপ্তাহিক তথ্য আপলোড করুন (মূল ডেটাসেটের মতো একই কলামসহ CSV)",
        "du_bad": "এই ফাইলটি ব্যবহার করা যাচ্ছে না: {e}",
        "du_ok": "{rows}টি সারি ঠিক আছে: {new}টি নতুন এবং {rep}টি আগের তথ্য হালনাগাদ করবে। সময়কাল: {a} থেকে {b}।",
        "du_apply": "তথ্য যুক্ত করে মডেল পুনঃপ্রশিক্ষণ দিন", "du_spin": "তথ্য যুক্ত ও মডেল পুনঃপ্রশিক্ষণ চলছে...",
        "du_done": "সম্পন্ন। মডেল এখন {d} পর্যন্ত তথ্যে প্রশিক্ষিত ({s} সেকেন্ড)। নতুন সপ্তাহের পূর্বাভাস দেখতে "
                   "“{replay}” থেকে সপ্তাহটি বেছে নিন।",
        "du_reset": "মূল ডেটাসেটে ফিরে যান",
        "du_reset_done": "আপলোড করা তথ্য সরানো হয়েছে। মডেল এখন {d} পর্যন্ত তথ্যে প্রশিক্ষিত।",
    },
}


def lang() -> str:
    return st.session_state.get("lang", "en")


def t(key: str, **kw) -> str:
    s = TEXT[lang()].get(key) or TEXT["en"][key]
    return s.format(**kw) if kw else s


def num(x, fmt: str = "{:,.0f}") -> str:
    s = fmt.format(x) if not isinstance(x, str) else x
    return s.translate(BN_DIGITS) if lang() == "bn" else s


def date(ts) -> str:
    d = pd.Timestamp(ts)
    if lang() == "bn":
        return num(f"{d.day} {MONTHS_BN[d.month - 1]} {d.year}")
    return f"{d.day} {d:%b %Y}"


def day(ts) -> str:
    d = pd.Timestamp(ts)
    return num(f"{d.day} {MONTHS_BN[d.month - 1]}") if lang() == "bn" else f"{d.day} {d:%B}"


def short(ts) -> str:
    """Short day and month for chart ticks and hovers: '2 Jun' / '২ জুন'."""
    d = pd.Timestamp(ts)
    return num(f"{d.day} {MONTHS_BN[d.month - 1]}") if lang() == "bn" else f"{d.day} {d:%b}"


def city(name: str) -> str:
    return CITY_BN.get(name, name) if lang() == "bn" else name


def city_of(name: str | None) -> str:
    """Bangla possessive form of a city ('ঢাকা দক্ষিণের'); English returns the plain name."""
    name = name or "All cities"
    return _CITY_OF_BN.get(name, name) if lang() == "bn" else name


def tier(name: str) -> str:
    return TIER_BN.get(name, name) if lang() == "bn" else name


def driver(group: str) -> str:
    return _DRIVER[lang()].get(group, group)


def month_ticks(start, end) -> tuple[list, list]:
    """Month tick positions and labels for chart axes in the current language."""
    ms = pd.date_range(pd.Timestamp(start).to_period("M").to_timestamp(), end, freq="MS")
    names = [(MONTHS_BN[m.month - 1] if lang() == "bn" else f"{m:%b}") for m in ms]
    return list(ms), names


def week_ticks(dates, every: int = 2) -> tuple[list, list]:
    """Every n-th week as a tick, labelled '2 Jun' / '২ জুন'."""
    ds = sorted(pd.to_datetime(pd.Series(list(dates))).unique())[::every]
    return list(ds), [short(d) for d in ds]


def ward(ward_id: str) -> str:
    if lang() == "bn":
        return bn_ward(ward_id)
    corp, _, n = str(ward_id).partition("_Ward_")
    return f"{corp} Ward {n}"

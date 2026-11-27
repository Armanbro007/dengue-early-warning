"""More: everything that is useful but not needed on a first visit."""
import streamlit as st

import ui_text as tx
from dengue import config
from ui_common import card_head, get_engine, html, page_header
from ui_shell import L

engine = get_engine()
b = engine.bundle
page_header(L("More", "আরও"), L("Details, history and settings", "বিস্তারিত, পুরোনো তথ্য ও সেটিংস"),
            L("You do not need these pages to use DengueWatch. They are here for when you want to dig deeper.",
              "DengueWatch ব্যবহারে এগুলো লাগে না। আরও গভীরে দেখতে চাইলে এখানে আসুন।"))

TILES = [
    ("views/risk_board.py", "list", L("All wards as a table", "সব ওয়ার্ডের তালিকা"),
     L("Sort and download every ward's forecast.", "প্রতিটি ওয়ার্ডের পূর্বাভাস সাজিয়ে দেখুন ও ডাউনলোড করুন।")),
    ("views/heatmap.py", "grid", L("Season calendar", "মৌসুমি ক্যালেন্ডার"),
     L("Every ward, every week of a year, on one screen.", "এক পাতায় সারা বছরের প্রতিটি ওয়ার্ড।")),
    ("views/accuracy.py", "check", L("How accurate is it?", "পূর্বাভাস কতটা নির্ভুল?"),
     L("Tested on 2024 and 2025, years the model never saw.", "মডেলের অজানা ২০২৪ ও ২০২৫ সালে যাচাই।")),
    ("views/reality.py", "target", L("Reality check: forecast vs what happened", "বাস্তবের সঙ্গে মিলিয়ে দেখা"),
     L("Replay a past week: who was warned, what really happened, what acting early would have saved.",
       "অতীতের সপ্তাহ: কে সতর্কতা পেয়েছিল, কী ঘটেছিল, আগে ব্যবস্থা নিলে কী বাঁচত।")),
    ("views/ward_detail.py", "note", L("One ward in depth", "একটি ওয়ার্ড বিস্তারিত"),
     L("Past forecasts against what really happened, week by week.", "আগের পূর্বাভাস বনাম বাস্তব, সপ্তাহে সপ্তাহে।")),
]
cols = st.columns(2, gap="small")
for i, (page, ic, title, text) in enumerate(TILES):
    with cols[i % 2], st.container(key=f"glass_more_{i}"):
        html(card_head(title, "", ic) + f'<div class="dw-tile"><p>{text}</p></div>')
        st.page_link(page, label=L("Open", "খুলুন"), icon=":material/arrow_forward:", icon_position="right")

st.write("")
cols = st.columns(2, gap="small")
for i, (ic, title, text) in enumerate([
    ("upload", L("Update weekly data", "সাপ্তাহিক তথ্য যোগ"),
     L("Add a new week of cases and weather and get a fresh report.", "নতুন সপ্তাহের তথ্য দিয়ে নতুন রিপোর্ট।")),
    ("rain", L("Live weather forecast", "সরাসরি আবহাওয়া পূর্বাভাস"),
     L("Use this week's real weather from the internet.", "ইন্টারনেট থেকে এ সপ্তাহের আবহাওয়া।")),
]):
    with cols[i], st.container(key=f"glass_soon_{i}"):
        html(card_head(f'{title}<span class="dw-soon">{L("Coming soon", "শিগগিরই আসছে")}</span>', "", ic)
             + f'<div class="dw-tile"><p>{text}</p></div>')

st.write("")
with st.container(key="glass_status"):
    html(card_head(L("System status", "সিস্টেমের অবস্থা"), "", "sliders"))
    st.markdown("\n".join("- " + line for line in (
        tx.t("st_trained", date=tx.date(b["train_end"]), s=tx.num(f"{b['train_seconds']}")),
        tx.t("st_load", ms=tx.num(engine.load_seconds * 1000)),
        L("Internet: " + ("allowed (used only for optional extras)" if config.ALLOW_NETWORK else "off. Everything still works."),
          "ইন্টারনেট: " + ("চালু (শুধু ঐচ্ছিক কাজে)" if config.ALLOW_NETWORK else "বন্ধ। সব কাজ চলছে।")),
    )))

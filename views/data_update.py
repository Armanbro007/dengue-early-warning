"""Add weekly data: the live-update path. Upload new weeks, check, merge, retrain."""
import pandas as pd
import streamlit as st

from dengue.data import has_updates, load_from_bytes
from dengue.ingest import apply_update, check_update, reset_updates, retrain, template_csv
from ui_common import get_engine, html, page_header, section

engine = get_engine()

page_header(
    "Add weekly data", "Keep the forecast up to date",
    "Each week, a health office uploads the latest ward reports: cases and weather. DengueWatch checks the file, "
    "adds it and re-learns in about 15 seconds. New rows are kept apart from the official dataset, so you can "
    "always go back.",
)

raw = engine.raw
k = st.columns(3)
k[0].metric("Wards", raw["ward_id"].nunique())
k[1].metric("Latest week in the data", f"{raw['date'].max():%d %b %Y}")
k[2].metric("Model has learned up to", pd.Timestamp(engine.bundle["train_end"]).strftime("%d %b %Y"))

steps = [("1", "Download the template", "It has the right columns and the latest week as an example."),
         ("2", "Fill in the new week", "One row per ward: cases, rain, humidity and temperature."),
         ("3", "Upload, check and retrain", "Problems are listed before anything is changed.")]
section("Three steps")
html('<div class="dw-steps" style="grid-template-columns:repeat(3,1fr)">' + "".join(
    f'<div class="dw-step"><div class="ic" style="font-family:var(--dw-serif);font-size:1.2rem">{n}</div>'
    f'<div class="what">{what}</div><p>{text}</p></div>' for n, what, text in steps) + "</div>")
st.write("")

st.download_button("Download the template (CSV)", template_csv().encode(), file_name="weekly_update_template.csv",
                   mime="text/csv", icon=":material/download:")
up = st.file_uploader("Upload new weekly rows (CSV with the same columns as the official dataset)", type="csv")
if up is not None:
    try:
        new = load_from_bytes(up.getvalue())
        s = check_update(new)
    except ValueError as exc:
        st.error(f"This file can't be used: {exc}")
        st.stop()
    st.success(f"{s.rows} rows look good: {s.new_rows} new and {s.replaced_rows} that update existing values. "
               f"Weeks {s.weeks[0]:%d %b %Y} to {s.weeks[1]:%d %b %Y}.")
    for w in s.warnings:
        st.warning(w)
    st.dataframe(new.head(10), hide_index=True, width="stretch")
    if st.button("Add these rows and retrain", type="primary"):
        with st.spinner("Adding rows and retraining..."):
            apply_update(new)
            info = retrain()
        st.cache_resource.clear()
        st.cache_data.clear()
        st.success(f"Done. The model has now learned up to {info['trained_through']} ({info['seconds']} s). "
                   "Pick the new week under “Pretend today is” to see its forecast.")

if has_updates():
    st.divider()
    if st.button("Go back to the official dataset"):
        reset_updates()
        info = retrain()
        st.cache_resource.clear()
        st.cache_data.clear()
        st.success(f"Uploaded rows removed. The model has learned up to {info['trained_through']}.")

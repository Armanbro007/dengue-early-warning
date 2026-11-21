"""Add Weekly Data: the live-update path. Upload new weeks, check, merge, retrain."""
import pandas as pd
import streamlit as st

from dengue.data import has_updates, load_from_bytes
from dengue.ingest import apply_update, check_update, reset_updates, retrain, template_csv
from ui_common import get_engine

engine = get_engine()

st.title("Add Weekly Data")
st.caption("Each week, a health office uploads the latest ward reports (cases and weather). "
           "The system checks the file, merges it and retrains in seconds. New rows are stored "
           "separately from the official dataset, so you can always reset.")

raw = engine.raw
k = st.columns(3)
k[0].metric("Wards", raw["ward_id"].nunique())
k[1].metric("Latest week in data", f"{raw['date'].max():%d %b %Y}")
k[2].metric("Model trained through", pd.Timestamp(engine.bundle["train_end"]).strftime("%d %b %Y"))

st.download_button("Download a template (latest week, correct columns)", template_csv().encode(),
                   file_name="weekly_update_template.csv", mime="text/csv")

up = st.file_uploader("Upload new weekly rows (CSV, same columns as the official dataset)", type="csv")
if up is not None:
    try:
        new = load_from_bytes(up.getvalue())
        s = check_update(new)
    except ValueError as exc:
        st.error(f"File rejected: {exc}")
        st.stop()
    st.success(f"{s.rows} valid rows: {s.new_rows} new, {s.replaced_rows} replace existing values. "
               f"Weeks {s.weeks[0]:%d %b %Y} to {s.weeks[1]:%d %b %Y}.")
    for w in s.warnings:
        st.warning(w)
    st.dataframe(new.head(10), hide_index=True, use_container_width=True)
    if st.button("Merge and retrain", type="primary"):
        with st.spinner("Merging and retraining..."):
            apply_update(new)
            info = retrain()
        st.cache_resource.clear()
        st.cache_data.clear()
        st.success(f"Done. Models retrained through {info['trained_through']} in {info['seconds']} s. "
                   "Pick the new week in the sidebar to see its forecast.")

if has_updates():
    st.divider()
    if st.button("Reset to the official dataset"):
        reset_updates()
        info = retrain()
        st.cache_resource.clear()
        st.cache_data.clear()
        st.success(f"Updates removed. Models retrained through {info['trained_through']}.")

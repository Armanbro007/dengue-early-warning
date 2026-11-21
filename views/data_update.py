"""Add weekly data: the live-update path. Upload new weeks, check, merge, retrain."""
import pandas as pd
import streamlit as st

import ui_text as tx
from dengue.data import has_updates, load_from_bytes
from dengue.ingest import apply_update, check_update, reset_updates, retrain, template_csv
from ui_common import card_head, get_engine, html, icon, page_header

engine = get_engine()
n = tx.num

page_header(tx.t("du_eyebrow"), tx.t("du_title"), tx.t("du_lead"))

raw = engine.raw
with st.container(key="dark_data"):
    k = st.columns(3)
    k[0].metric(tx.t("du_m_wards"), n(raw["ward_id"].nunique()))
    k[1].metric(tx.t("du_m_latest"), tx.date(raw["date"].max()))
    k[2].metric(tx.t("du_m_trained"), tx.date(engine.bundle["train_end"]))
st.write("")

steps = [("download", 1, ""), ("note", 2, ""), ("upload", 3, " hl")]
html(f'<div class="gc">{card_head(tx.t("du_steps"), tx.t("du_steps_sub"))}'
     '<div class="steps" style="grid-template-columns:repeat(3,1fr)">' + "".join(
         f'<div class="st{cls}"><div class="ic">{icon(ic, 20)}</div><div class="w">{tx.t("du_step", n=n(i))}</div>'
         f'<div class="t">{tx.t(f"du_s{i}")}</div><p>{tx.t(f"du_s{i}_t")}</p></div>' for ic, i, cls in steps)
     + "</div></div>")
st.write("")

with st.container(key="glass_upload"):
    st.download_button(tx.t("du_dl"), template_csv().encode(), file_name="weekly_update_template.csv",
                       mime="text/csv", icon=":material/download:")
    up = st.file_uploader(tx.t("du_up"), type="csv")
    if up is not None:
        try:
            new = load_from_bytes(up.getvalue())
            s = check_update(new)
        except ValueError as exc:
            st.error(tx.t("du_bad", e=exc))
            st.stop()
        st.success(tx.t("du_ok", rows=n(s.rows), new=n(s.new_rows), rep=n(s.replaced_rows),
                        a=tx.date(s.weeks[0]), b=tx.date(s.weeks[1])))
        for w in s.warnings:
            st.warning(w)
        st.dataframe(new.head(10), hide_index=True, width="stretch")
        if st.button(tx.t("du_apply"), type="primary"):
            with st.spinner(tx.t("du_spin")):
                apply_update(new)
                info = retrain()
            st.cache_resource.clear()
            st.cache_data.clear()
            st.success(tx.t("du_done", d=tx.date(pd.Timestamp(info["trained_through"])), s=n(f"{info['seconds']}"),
                            replay=tx.t("replay")))

    if has_updates():
        st.divider()
        if st.button(tx.t("du_reset")):
            reset_updates()
            info = retrain()
            st.cache_resource.clear()
            st.cache_data.clear()
            st.success(tx.t("du_reset_done", d=tx.date(pd.Timestamp(info["trained_through"]))))

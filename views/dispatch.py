"""Module 4 page: ward dispatch notices (SMS, WhatsApp, printable brief) from the current plan."""
import io
import zipfile

import streamlit as st

import ui_text as tx
from dengue import dispatch
from ui_common import card_head, html, page_header
from ui_ops import L, current_plan, offline_badge, ward

plan, c, target = current_plan()
w, n = plan.wards, tx.num
notes = dispatch.notices(plan, target)

page_header(
    L(f"Dispatch · week of {tx.date(target)}", f"নির্দেশনা · {tx.date(target)} সপ্তাহ"),
    L("Send each ward its orders", "প্রতিটি ওয়ার্ডে নির্দেশনা পাঠান"),
    L("Every notice is filled from the plan by a fixed template, so it works with no internet and no AI: forecast cases, supplies "
      "allocated vs required, deficit alerts, bed transfers and spraying crews.",
      "প্রতিটি নোটিশ নির্দিষ্ট টেমপ্লেটে পরিকল্পনা থেকে তৈরি হয়, তাই ইন্টারনেট বা এআই ছাড়াই কাজ করে: সম্ভাব্য রোগী, "
      "বরাদ্দ বনাম চাহিদা, ঘাটতির সতর্কতা, রোগী স্থানান্তর ও স্প্রে দল।"),
)
offline_badge()

with st.container(key="dark_dispatch"):
    k = st.columns(4)
    counts = notes["status"].value_counts()
    k[0].metric(L("Notices ready", "প্রস্তুত নোটিশ"), n(len(notes)))
    k[1].metric(L("Critical deficit", "জরুরি ঘাটতি"), n(int(counts.get("CRITICAL DEFICIT", 0))))
    k[2].metric(L("Shortage", "ঘাটতি"), n(int(counts.get("SHORTAGE", 0))))
    k[3].metric(L("Fully covered", "পর্যাপ্ত"), n(int(counts.get("OK", 0))))
st.write("")

left, right = st.columns([2, 3], gap="small")
with left, st.container(key="glass_dispatch_pick"):
    html(card_head(L("Pick a ward", "ওয়ার্ড বাছুন"), L("Listed in priority order",
                                                     "অগ্রাধিকার অনুযায়ী"), "bell"))
    only_bad = st.toggle(L("Only wards with a problem", "শুধু সমস্যাগ্রস্ত ওয়ার্ড"), value=False, key="dp_bad")
    opts = notes[notes["status"] != "OK"] if only_bad else notes
    pick = st.selectbox(L("Ward", "ওয়ার্ড"), opts["ward_id"].tolist(),
                        format_func=lambda x: f"#{int(notes.set_index('ward_id').at[x, 'priority'])} {ward(x)}", key="dp_ward")
    row = notes.set_index("ward_id").loc[pick]
    badge = {"CRITICAL DEFICIT": "error", "SHORTAGE": "warning", "OK": "success"}[row["status"]]
    getattr(st, badge)(f"{L('Status', 'অবস্থা')}: **{row['status']}**")
    st.markdown(f"**SMS** ({len(row['sms'])}/160)")
    st.code(row["sms"], language=None, wrap_lines=True)
    st.markdown(L("**Bangla SMS** (field staff)", "**বাংলা এসএমএস** (মাঠকর্মী)"))
    st.code(row["sms_bangla"], language=None, wrap_lines=True)

with right, st.container(key="glass_dispatch_msg"):
    tabs = st.tabs([L("WhatsApp", "হোয়াটসঅ্যাপ"), L("Printable brief", "প্রিন্টযোগ্য ব্রিফ"), L("City digest", "সিটির সারাংশ")])
    with tabs[0]:
        st.code(row["whatsapp"], language=None, wrap_lines=True)
    with tabs[1]:
        one = w[w["ward_id"] == pick]
        page = dispatch.brief_html(one, target, f"Dispatch brief {pick}")
        if hasattr(st, "iframe"):  # our own template HTML (values escaped), shown as it will print
            st.iframe(page, height=560)
        else:
            import streamlit.components.v1 as components
            components.html(page, height=560, scrolling=True)
        b = st.columns(2)
        b[0].download_button(L("Download HTML", "HTML ডাউনলোড"), page.encode(), f"brief_{pick}.html", "text/html",
                             icon=":material/download:")
        pdf = dispatch.brief_pdf(one, target)
        if pdf:
            b[1].download_button(L("Download PDF", "PDF ডাউনলোড"), pdf, f"brief_{pick}.pdf", "application/pdf",
                                 icon=":material/picture_as_pdf:")
    with tabs[2]:
        st.code(dispatch.city_digest(plan, target), language=None, wrap_lines=True)

st.write("")
with st.container(key="glass_dispatch_all"):
    html(card_head(L("All notices", "সব নোটিশ"), L("Download everything for the dispatch desk",
                                                   "ডিসপ্যাচ ডেস্কের জন্য সব একসাথে ডাউনলোড"), "download"))
    st.dataframe(notes[["priority", "ward_id", "city", "status", "sms"]].assign(ward_id=notes["ward_id"].map(ward)),
                 hide_index=True, width="stretch", height=300)

    def bundle() -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("sms_messages.csv", notes[["priority", "ward_id", "city", "status", "sms"]].to_csv(index=False))
            z.writestr("sms_bangla.txt", "\n\n".join(f"[{a}]\n{b}" for a, b in zip(notes["ward_id"], notes["sms_bangla"])))
            z.writestr("whatsapp_messages.txt", "\n\n-----\n\n".join(notes["whatsapp"]))
            z.writestr("city_digest_whatsapp.txt", dispatch.city_digest(plan, target))
            z.writestr("commissioner_briefs.html", dispatch.brief_html(w, target))
            pdf_all = dispatch.brief_pdf(w, target)
            if pdf_all:
                z.writestr("commissioner_briefs.pdf", pdf_all)
            z.writestr("dispatch_plan.csv", w.round(2).to_csv(index=False))
            z.writestr("bed_transfers.csv", plan.transfers.to_csv(index=False))
        return buf.getvalue()

    st.download_button(L("Download all notices (ZIP)", "সব নোটিশ ডাউনলোড (ZIP)"), bundle(), f"dispatch_{target:%Y-%m-%d}.zip",
                       "application/zip", icon=":material/folder_zip:", type="primary")

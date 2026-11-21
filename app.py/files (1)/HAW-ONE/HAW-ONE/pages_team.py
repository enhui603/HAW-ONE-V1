"""Team-only page (open with ?team=1). English only. Reports, stall controls, promo posts."""
import hmac
import os
from datetime import datetime

import streamlit as st

import hawkers
import store
from pages_seller import process_media


def _secret(name):
    try:
        return st.secrets.get(name)
    except Exception:
        return None


def team_page():
    st.title("HAW-ONE team")
    pw = _secret("team_password")
    if not pw:
        st.error("Set `team_password` in your Streamlit secrets to use this page.")
        return
    if not st.session_state.get("team_ok"):
        with st.form("team_login"):
            entered = st.text_input("Team password", type="password")
            ok = st.form_submit_button("Open", type="primary")
        if ok:
            if hmac.compare_digest(entered, pw):
                st.session_state["team_ok"] = True
                st.rerun()
            else:
                st.error("Wrong password.")
        return

    tab_r, tab_s, tab_p, tab_c = st.tabs(["Reports", "Stalls", "Promo posts", "Trial codes"])

    with tab_r:
        reports = store.get_reports()
        if not reports:
            st.info("No reports yet.")
        for r in reports:
            stall = store.get_user(r["stall_id"])
            who = store.get_user(r["reporter_id"])
            with st.container(border=True):
                st.markdown(f"**{stall['stall'] if stall else 'Deleted stall'}** · {r['reason']} · "
                            f"status: `{r['status']}`")
                st.caption(f"By {store.display_name(who)} · {r['time']}")
                if r["note"]:
                    st.write(r["note"])
                if r.get("screenshot") and os.path.exists(store.media_path(r["screenshot"])):
                    st.image(store.media_path(r["screenshot"]), width=300)
                with st.expander("Latest posts from this stall (saved with the report)"):
                    for p in r["snapshot"]:
                        st.caption(f"{p['channel']} · {p['time']}")
                        if p["text"]:
                            st.write(p["text"])
                        for im in p["images"]:
                            if os.path.exists(store.media_path(im)):
                                st.image(store.media_path(im), width=200)
                c1, c2, c3 = st.columns(3)
                c1.button("Mark reviewed", key=f"tr_{r['id']}", on_click=store.set_report_status,
                          args=(r["id"], "reviewed"))
                if stall:
                    paused = stall.get("suspended")
                    c2.button("Unpause stall" if paused else "Pause stall", key=f"tp_{r['id']}",
                              on_click=store.set_flag, args=(stall["id"], "suspended", not paused))

    with tab_s:
        for s in store.stalls(include_suspended=True):
            c1, c2 = st.columns([4, 1], vertical_alignment="center")
            c1.markdown(f"**{s['stall']}** · {s['centre']} · {s['unit']} · {s['email']}"
                        f"{'  (paused)' if s.get('suspended') else ''}")
            c2.button("Unpause" if s.get("suspended") else "Pause", key=f"ts_{s['id']}",
                      on_click=store.set_flag, args=(s["id"], "suspended", not s.get("suspended")))

    with tab_p:
        st.caption("Posts here show in the Hawkers News & Social Feed with a 'Promoted' tag.")
        with st.form("promo_form", clear_on_submit=True):
            centre = st.selectbox("Hawker centre", hawkers.centre_names() or ["—"])
            text = st.text_area("Text")
            photos = st.file_uploader("Photos", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
            video = st.file_uploader("Video (max 30 sec)", type=["mp4", "mov", "m4v"])
            link = st.text_input("Link (optional)")
            ok = st.form_submit_button("Post promo", type="primary")
        if ok:
            if link.strip() and not link.strip().lower().startswith(("http://", "https://")):
                st.error("Link must start with http.")
            elif not text.strip() and not photos and video is None:
                st.error("Add some text, a photo or a video.")
            else:
                imgs, vname, err = process_media(photos, video)
                if err:
                    st.error(err)
                else:
                    store.add_post("feed", "team", text, imgs, vname, link=link.strip(), label=centre)
                    st.success("Posted.")
        for p in store.get_posts("feed", "team"):
            with st.container(border=True):
                st.markdown(f"**{p.get('label')}** · {p['time']}")
                st.write(p["text"])
                st.button("Delete", key=f"td_{p['id']}", on_click=store.delete_post, args=(p["id"], "team"))

    with tab_c:
        total, used = store.invite_counts()
        st.metric("Trial codes used", f"{used} / {total}")
        st.caption("The plain codes are in TRIAL_CODES_PRIVATE.csv (keep that file off GitHub).")

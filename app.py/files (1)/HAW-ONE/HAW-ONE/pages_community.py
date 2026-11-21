"""Visitor side: community broadcast (WhatsApp-style), stall pages, social feed, ratings, profiles."""
import html
import os
from collections import Counter
from datetime import datetime

import streamlit as st

import store
import ui
from i18n import t, fmt_date
from ui import go, nav_bar, page_header, menu_card, section_title, divider, chip

SOCIAL_OK = ("http://", "https://")


# =====================================================================
# small callbacks
# =====================================================================
def _react(pid, emoji):
    u = ui.me()
    if u:
        store.react(pid, u["id"], emoji)


def _follow(stall_id):
    u = ui.me()
    if u and u["role"] == "visitor":
        store.toggle_follow(u["id"], stall_id)


def _open_report(stall_id):
    st.session_state["report_for"] = stall_id


def _close_report():
    st.session_state["report_for"] = None


def _visible(p):
    a = store.get_user(p["author_id"])
    return not (a and a.get("suspended"))


# =====================================================================
# building blocks
# =====================================================================
def reactions_bar(p, kp):
    u = ui.me()
    rx = p.get("reactions", {})
    counts = Counter(rx.values())
    mine = rx.get(u["id"]) if u else None
    with st.container(key=f"react_{kp}_{p['id']}"):
        cols = st.columns(len(ui.EMOJIS))
        for i, e in enumerate(ui.EMOJIS):
            n = counts.get(e, 0)
            pre = "rs_" if mine == e else "r_"
            cols[i].button(f"{e} {n}" if n else e, key=f"{pre}{kp}_{p['id']}_{i}", disabled=u is None,
                           on_click=_react, args=(p["id"], e), use_container_width=True)
    if u is None:
        st.caption(t("login_to_react"))


def comments_block(p, kp, expanded=False):
    u = ui.me()
    cs = p.get("comments", [])
    with st.expander(t("comments", n=len(cs)), expanded=expanded):
        for c in cs:
            a = store.get_user(c["uid"])
            when = fmt_date(datetime.fromisoformat(c["time"]))
            badge = ""
            if a and a["role"] == "visitor":
                badge = " " + ui.rank_badge(store.rank_info(store.rating_count(a["id"])))
            st.markdown(f"**{html.escape(store.display_name(a))}**{badge} · <small>{when}</small>",
                        unsafe_allow_html=True)
            st.write(c["text"])
        if u:
            with st.form(f"cf_{kp}_{p['id']}", clear_on_submit=True):
                txt = st.text_input(t("add_comment"), max_chars=300)
                ok = st.form_submit_button(t("send"))
            if ok and txt.strip():
                store.add_comment(p["id"], u["id"], txt)
                st.rerun()
        else:
            st.caption(t("comment_login"))


def author_header(p, kp, link=True):
    a = store.get_user(p["author_id"])
    promo = p["author_id"] == "team"
    name = store.display_name(a) if a else (p.get("label") or "HAW-ONE")
    posted = datetime.fromisoformat(p["time"])
    when = f"{fmt_date(posted)}, {posted.strftime('%H:%M')}"
    c1, c2 = st.columns([3, 2], vertical_alignment="center")
    c1.markdown(f"<div class='who'>{ui.avatar_html(a.get('logo') if a else None, 44)}"
                f"<div><b>{html.escape(name)}</b><br><small>{when}</small></div></div>", unsafe_allow_html=True)
    if promo:
        c2.markdown(chip(t("promo_tag"), "upcoming"), unsafe_allow_html=True)
    elif a and link:
        c2.button(t("view_profile"), key=f"p_vp_{kp}_{p['id']}", on_click=go, args=("v_stall",),
                  kwargs={"stall_id": a["id"]}, use_container_width=True)


def post_card(p, kp, owner_id=None, link=True, comments=None, expand_comments=False, open_btn=False):
    """One post. comments=None means 'only for social-feed posts'."""
    if comments is None:
        comments = p["channel"] == "feed"
    with st.container(border=True):
        author_header(p, kp, link=link)
        if p["kind"] == "closure":
            ui.closure_box(p["start"], p["end"], p.get("text", ""))
        elif p.get("text"):
            st.write(p["text"])
        ui.media_block(p)
        if p.get("link", "").lower().startswith(SOCIAL_OK):
            st.link_button(t("follow_on"), p["link"])
        reactions_bar(p, kp)
        if comments:
            comments_block(p, kp, expanded=expand_comments)
        row = st.columns(2)
        if open_btn:
            row[0].button(t("open"), key=f"p_open_{kp}_{p['id']}", on_click=go, args=("v_post",),
                          kwargs={"post_id": p["id"]}, use_container_width=True)
        if owner_id and owner_id == p["author_id"]:
            row[1].button(t("delete"), key=f"b_del_{kp}_{p['id']}", on_click=store.delete_post,
                          args=(p["id"], owner_id), use_container_width=True)


def feed_list(kp, owner_id=None, author_id=None):
    posts = [p for p in store.get_posts("feed", author_id) if _visible(p)]
    if not posts:
        st.info(t("no_posts_feed"))
    for p in posts:
        post_card(p, kp, owner_id=owner_id, open_btn=False)
    st.caption(t("promo_note"))


def follow_button(stall_id, key):
    u = ui.me()
    if u and u["role"] == "visitor":
        on = stall_id in u.get("subs", [])
        st.button(t("subscribed") if on else t("subscribe"), key=key, on_click=_follow, args=(stall_id,),
                  use_container_width=True)


def rating_line(stall_id):
    avg, n = store.avg_rating(stall_id)
    if not n:
        return f"<small>{html.escape(t('no_ratings'))}</small>"
    return f"{ui.stars_html(avg)} <b>{avg:.1f}</b> <small>({n})</small>"


# =====================================================================
# VISITOR HOME
# =====================================================================
def visitor_home():
    nav_bar("p")
    page_header(t("visitor"), t("v_sub"), "haw_sim")
    if not ui.me():
        st.info(t("guest_note"))
    items = [("fav", "star", "fav_title", "fav_desc", "v_fav"),
             ("sched", "calendar", "sched_title", "sched_desc", "v_sched"),
             ("near", "pin", "near_title", "near_desc", "v_near"),
             ("news", "news", "news_title", "news_desc", "v_feed")]
    for i in range(0, len(items), 2):
        for col, (key, icon, title, desc, target) in zip(st.columns(2, gap="large"), items[i:i + 2]):
            with col:
                menu_card("pink", key, icon, t(title), t(desc), t("open"), on_click=go, args=(target,))


# =====================================================================
# COMMUNITY LIST  (followed stalls first, then "discover more")
# =====================================================================
def stall_row(s, kp):
    today = ui.today_sg()
    closures = store.closures_for(s["id"], today)
    with st.container(border=True):
        c1, c2, c3 = st.columns([1, 4, 2], vertical_alignment="center")
        c1.markdown(ui.avatar_html(s.get("logo"), 56), unsafe_allow_html=True)
        extra = ""
        if closures:
            c = closures[0]
            s0, e0 = datetime.fromisoformat(c["start"]).date(), datetime.fromisoformat(c["end"]).date()
            txt = (t("closed_now", end=fmt_date(e0)) if s0 <= today <= e0
                   else t("closed_range", start=fmt_date(s0), end=fmt_date(e0)))
            extra = "<br>" + chip(txt, "now" if s0 <= today <= e0 else "tbc")
        c2.markdown(f"<b>{html.escape(s['stall'])}</b><br><small>{html.escape(s['centre'])} · "
                    f"{html.escape(s['unit'])}</small><br>{rating_line(s['id'])}{extra}", unsafe_allow_html=True)
        with c3:
            st.button(t("open"), key=f"p_open_{kp}_{s['id']}", on_click=go, args=("v_channel",),
                      kwargs={"channel_id": s["id"]}, use_container_width=True)
            follow_button(s["id"], f"p_fol_{kp}_{s['id']}")


def community_list():
    nav_bar("p")
    page_header(t("fav_title"), t("fav_sub"), "haw_sim")
    u = ui.me()
    if not u:
        st.info(t("guest_note"))
    allst = store.stalls()
    if not allst:
        st.info(t("no_stalls"))
        return
    subs = u.get("subs", []) if (u and u["role"] == "visitor") else []
    favs = [s for s in allst if s["id"] in subs]
    others = [s for s in allst if s["id"] not in subs]
    section_title(t("your_favs"), "star")
    if favs:
        for s in favs:
            stall_row(s, "fav")
    else:
        st.caption(t("no_favs"))
    if others:
        section_title(t("discover"), "search")
        for s in others:
            stall_row(s, "oth")


# =====================================================================
# CHANNEL  (read + react only, like a WhatsApp community broadcast)
# =====================================================================
def stall_header(s, big=False):
    c1, c2 = st.columns([1, 4], vertical_alignment="center")
    c1.markdown(ui.avatar_html(s.get("logo"), 88 if big else 64), unsafe_allow_html=True)
    c2.markdown(f"<p class='page-title'>{html.escape(s['stall'])}</p><p class='page-sub'>"
                f"{html.escape(s['centre'])} · {html.escape(s['unit'])}<br>{rating_line(s['id'])}</p>",
                unsafe_allow_html=True)


def report_form(s):
    u = ui.me()
    with st.container(border=True):
        st.markdown(f"**{html.escape(t('report_title', stall=s['stall']))}**")
        if not u or u["role"] != "visitor":
            st.info(t("report_login"))
            st.button(t("cancel"), key="link_cancel_report", on_click=_close_report)
            return
        labels = {"Violent": t("r_violent"), "Unrelated": t("r_unrelated"), "Others": t("r_other")}
        with st.form(f"report_{s['id']}"):
            reason = st.radio(t("reason"), list(labels.keys()), format_func=lambda k: labels[k])
            note = st.text_area(t("report_note"))
            shot = st.file_uploader(t("report_ss"), type=["png", "jpg", "jpeg"])
            c1, c2 = st.columns(2)
            send = c1.form_submit_button(t("send_report"), type="primary")
            cancel = c2.form_submit_button(t("cancel"))
        if send:
            if reason == "Others" and not note.strip():
                st.error(t("err_report_other"))
            else:
                img = store.save_image(shot.getvalue()) if shot else None
                store.add_report(s["id"], u["id"], reason, note, img)
                st.session_state["report_for"] = None
                st.success(t("report_sent"))
        elif cancel:
            _close_report()
            st.rerun()


def report_link(s):
    if st.session_state.get("report_for") == s["id"]:
        report_form(s)
    else:
        st.button(t("report_link"), key="link_report", on_click=_open_report, args=(s["id"],))


def channel_page():
    nav_bar("p")
    s = store.get_user(st.session_state.get("channel_id"))
    if not s or s["role"] != "seller" or s.get("suspended"):
        st.info(t("suspended"))
        return
    stall_header(s)
    a, b = st.columns(2)
    with a:
        follow_button(s["id"], "p_fol_channel")
    b.button(t("view_profile"), key="p_vp_channel", on_click=go, args=("v_stall",),
             kwargs={"stall_id": s["id"]}, use_container_width=True)
    if not ui.me():
        st.info(t("guest_note"))

    today = ui.today_sg()
    closures = store.closures_for(s["id"], today)
    for c in closures:                                   # pinned at the top
        ui.closure_box(c["start"], c["end"], c.get("text", ""), today)
    pinned = {c["id"] for c in closures}
    posts = [p for p in store.get_posts("broadcast", s["id"]) if p["id"] not in pinned]
    if not posts and not closures:
        st.info(t("no_updates"))
    for p in posts:
        post_card(p, "ch", link=False, comments=False)
    divider()
    report_link(s)


# =====================================================================
# STALL PROFILE  (community on top, then grid of social posts + ratings)
# =====================================================================
def _tile_html(p):
    imgs = p.get("images", [])
    if imgs:
        th = store.media_path(store.thumb_name(imgs[0]))
        if os.path.exists(th):
            return f"<div class='tile' style=\"background-image:url('data:image/jpeg;base64,{ui.b64_file(th)}')\"></div>"
    if p.get("video"):
        return f"<div class='tile video'>{html.escape(t('video_tile'))}</div>"
    return f"<div class='tile'>{html.escape((p.get('text') or '')[:70])}</div>"


def post_grid(posts, kp):
    if not posts:
        st.info(t("no_posts_feed"))
        return
    for i in range(0, len(posts), 3):
        with st.container(key=f"react_grid_{kp}_{i}"):          # keeps 3 tiles in a row on phones
            for col, p in zip(st.columns(3), posts[i:i + 3]):
                with col:
                    st.markdown(_tile_html(p), unsafe_allow_html=True)
                    st.button(t("view"), key=f"p_g_{kp}_{p['id']}", on_click=go, args=("v_post",),
                              kwargs={"post_id": p["id"]}, use_container_width=True)


def review_card(r, mode):
    """mode 'reviewer' = show who wrote it (stall page); 'stall' = show which stall (profile page)."""
    with st.container(border=True):
        if mode == "reviewer":
            v = store.get_user(r["uid"])
            if v:
                info = store.rank_info(store.rating_count(v["id"]))
                c1, c2 = st.columns([1, 4], vertical_alignment="center")
                c1.markdown(ui.avatar_html(v.get("avatar"), 48, ring=info["color"]), unsafe_allow_html=True)
                with c2:
                    st.button(v["username"], key=f"p_rv_{r['id']}", on_click=go, args=("v_profile",),
                              kwargs={"profile_id": v["id"]})
                    st.markdown(ui.rank_badge(info), unsafe_allow_html=True)
        else:
            s = store.get_user(r["stall_id"])
            if s:
                st.button(s["stall"], key=f"p_rs_{r['id']}", on_click=go, args=("v_stall",),
                          kwargs={"stall_id": s["id"]})
        st.markdown(f"{ui.stars_html(r['stars'])} <small>{fmt_date(datetime.fromisoformat(r['time']))}</small>",
                    unsafe_allow_html=True)
        if r.get("comment"):
            st.write(r["comment"])
        if r.get("image") and os.path.exists(store.media_path(r["image"])):
            st.image(store.media_path(r["image"]), width=260)


def ratings_tab(s):
    u = ui.me()
    avg, n = store.avg_rating(s["id"])
    if n:
        st.markdown(f"{ui.stars_html(avg)} **{avg:.1f}** ({n})", unsafe_allow_html=True)
    if u and u["role"] == "visitor":
        section_title(t("rate_title"), "star")
        mine = store.my_rating(s["id"], u["id"])
        with st.form(f"rate_{s['id']}"):
            stars = st.radio(t("your_stars"), [1, 2, 3], index=(mine["stars"] - 1 if mine else 2),
                             horizontal=True, format_func=lambda k: "★" * k)
            comment = st.text_area(t("your_comment"), value=mine["comment"] if mine else "", max_chars=500)
            photo = st.file_uploader(t("add_photo"), type=["png", "jpg", "jpeg"])
            ok = st.form_submit_button(t("submit_rating"), type="primary")
        st.caption(t("rate_once"))
        if ok:
            img = store.save_image(photo.getvalue()) if photo else None
            store.rate(s["id"], u["id"], stars, comment, img)
            st.success(t("rating_saved"))
    else:
        st.caption(t("rate_login"))
    divider()
    rs = store.ratings_for(s["id"])
    if not rs:
        st.info(t("no_ratings"))
    for r in rs:
        review_card(r, "reviewer")


def stall_page(show_nav=True):
    if show_nav:
        nav_bar("p")
    s = store.get_user(st.session_state.get("stall_id"))
    if not s or s["role"] != "seller" or s.get("suspended"):
        st.info(t("suspended"))
        return
    stall_header(s, big=True)
    follow_button(s["id"], "p_fol_stall")

    with st.container(border=True):                       # community broadcast at the top
        section_title(t("community"), "megaphone")
        today = ui.today_sg()
        for c in store.closures_for(s["id"], today)[:2]:
            ui.closure_box(c["start"], c["end"], c.get("text", ""), today)
        latest = [p for p in store.get_posts("broadcast", s["id"]) if p["kind"] != "closure"][:1]
        if latest:
            st.write((latest[0]["text"] or "")[:160])
            st.caption(fmt_date(datetime.fromisoformat(latest[0]["time"])))
        elif not store.closures_for(s["id"], today):
            st.caption(t("no_updates"))
        st.button(t("open_community"), key="p_open_ch", on_click=go, args=("v_channel",),
                  kwargs={"channel_id": s["id"]}, use_container_width=True)

    tab_posts, tab_rate = st.tabs([t("grid_posts"), t("ratings")])
    with tab_posts:
        post_grid([p for p in store.get_posts("feed", s["id"])], "stall")
    with tab_rate:
        ratings_tab(s)
    divider()
    report_link(s)


# =====================================================================
# POST DETAIL + SOCIAL FEED + COMMENTOR PROFILE
# =====================================================================
def post_page():
    nav_bar("p")
    p = store.get_post(st.session_state.get("post_id"))
    if not p or not _visible(p):
        st.info(t("no_posts_feed"))
        return
    post_card(p, "detail", expand_comments=True)


def feed_page():
    nav_bar("p")
    page_header(t("news_title"), t("news_desc"), "haw_sim")
    if not ui.me():
        st.info(t("guest_note"))
    feed_list("feed")


def profile_page():
    nav_bar("p")
    v = store.get_user(st.session_state.get("profile_id"))
    if not v:
        st.info(t("no_reviews"))
        return
    if v["role"] == "seller":
        st.session_state["stall_id"] = v["id"]
        stall_page(show_nav=False)
        return
    n = store.rating_count(v["id"])
    info = store.rank_info(n)
    c1, c2 = st.columns([1, 3], vertical_alignment="center")
    c1.markdown(ui.avatar_html(v.get("avatar"), 96, ring=info["color"]), unsafe_allow_html=True)
    c2.markdown(f"<p class='page-title'>{html.escape(v['username'])}</p>"
                f"{ui.rank_badge(info)}<br><small>{html.escape(t('rated_count', n=n))}</small>",
                unsafe_allow_html=True)
    if info["next_name"]:
        st.progress(min(1.0, (n - info["start"]) / (info["next_at"] - info["start"])))
        st.caption(t("rank_progress", n=info["to_next"], rank=info["next_name"]))
    else:
        st.caption(t("top_rank"))
    ladder = "".join(
        f"<span class='badge' style='background:{c};color:{'#3B2A33' if c == '#E0A800' else '#fff'};"
        f"opacity:{1 if i == info['index'] else .35}'>{html.escape(name)} {lo}+</span> "
        for i, (lo, name, c) in enumerate(store.RANKS))
    st.markdown(ladder, unsafe_allow_html=True)
    divider()
    section_title(t("reviews"), "star")
    rs = store.ratings_by(v["id"])
    if not rs:
        st.info(t("no_reviews"))
    for r in rs:
        review_card(r, "stall")

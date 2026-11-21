"""Seller admin: community broadcast, social feed, hawker calculator."""
import os
import uuid
from datetime import datetime

import pandas as pd
import streamlit as st

import store
import ui
from i18n import t, fmt_date, MONTHS, cur_lang
from pages_community import post_card, feed_list
from ui import go, divider, section_title, reset_to

LEDGER_FILE = os.path.join(store.DATA, "ledger.csv")
LEDGER_COLS = ["uid", "id", "date", "type", "amount", "description"]


def process_media(photos, video):
    """Checks + saves uploads. Returns (image_names, video_name, error_key)."""
    vdata = None
    if video is not None:
        vdata = video.getvalue()
        err = store.check_video(vdata)
        if err:
            return [], None, err
    imgs = []
    for up in (photos or [])[:4]:
        name = store.save_image(up.getvalue())
        if not name:
            store.remove_media(imgs)
            return [], None, "err_photo"
        imgs.append(name)
    vname = store.save_video(vdata, video.name) if vdata else None
    return imgs, vname, None


# =====================================================================
def seller_admin():
    u = ui.me()
    if not u or u["role"] != "seller":
        reset_to("seller_home")
        st.rerun()
    ui.nav_bar("b")
    c1, c2 = st.columns([1, 5], vertical_alignment="center")
    c1.markdown(ui.avatar_html(u.get("logo"), 72), unsafe_allow_html=True)
    c2.markdown(f"<p class='page-title'>{u['stall']}</p><p class='page-sub'>{u['centre']} · {u['unit']}</p>",
                unsafe_allow_html=True)
    st.button(t("my_page"), key="b_mypage", on_click=go, args=("v_stall",), kwargs={"stall_id": u["id"]})
    if u.get("suspended"):
        st.warning(t("suspended"))

    tab_bc, tab_feed, tab_calc = st.tabs([t("tab_bc"), t("tab_feed"), t("tab_calc")])
    with tab_bc:
        broadcast_tab(u)
    with tab_feed:
        feed_tab(u)
    with tab_calc:
        calculator_tab(u["id"])


# =====================================================================
# BROADCAST
# =====================================================================
def broadcast_tab(u):
    section_title(t("bc_post"), "megaphone")
    st.caption(t("post_cap"))
    with st.form("bc_form", clear_on_submit=True):
        text = st.text_area(t("caption_label"), placeholder=t("caption_ph"))
        photos = st.file_uploader(t("photos"), type=["png", "jpg", "jpeg"], accept_multiple_files=True)
        video = st.file_uploader(t("video"), type=["mp4", "mov", "m4v"])
        sent = st.form_submit_button(t("post_btn"), type="primary")
    if sent:
        if u.get("suspended"):
            st.error(t("suspended"))
        elif not text.strip() and not photos and video is None:
            st.error(t("err_empty"))
        else:
            imgs, vname, err = process_media(photos, video)
            if err:
                st.error(t(err))
            else:
                store.add_post("broadcast", u["id"], text, imgs, vname)
                st.success(t("posted"))

    divider()
    section_title(t("closure_title"), "lock")
    with st.form("closure_form", clear_on_submit=True):
        today = ui.today_sg()
        dates = st.date_input(t("closure_dates"), value=(today, today))
        note = st.text_input(t("closure_note"))
        ok = st.form_submit_button(t("announce"), type="primary")
    if ok:
        if u.get("suspended"):
            st.error(t("suspended"))
        elif not (isinstance(dates, (tuple, list)) and len(dates) == 2):
            st.error(t("err_dates"))
        else:
            store.add_post("broadcast", u["id"], note, kind="closure",
                           start=dates[0].isoformat(), end=dates[1].isoformat())
            st.success(t("posted"))

    divider()
    section_title(t("public_bc"), "news")
    posts = store.get_posts("broadcast", u["id"])
    if not posts:
        st.info(t("no_posts_seller"))
    for p in posts:
        post_card(p, "own", owner_id=u["id"])


# =====================================================================
# SOCIAL FEED (only registered hawkers can post here)
# =====================================================================
def feed_tab(u):
    section_title(t("feed_new"), "news")
    with st.form("feed_form", clear_on_submit=True):
        text = st.text_area(t("feed_text"))
        photos = st.file_uploader(t("photos"), type=["png", "jpg", "jpeg"], accept_multiple_files=True,
                                  key="feed_photos")
        video = st.file_uploader(t("video"), type=["mp4", "mov", "m4v"], key="feed_video")
        link = st.text_input(t("social_link"), placeholder="https://instagram.com/…")
        sent = st.form_submit_button(t("post_btn"), type="primary")
    if sent:
        link = link.strip()
        if u.get("suspended"):
            st.error(t("suspended"))
        elif not text.strip() and not photos and video is None:
            st.error(t("err_empty"))
        elif link and not link.lower().startswith(("http://", "https://")):
            st.error(t("err_link"))
        else:
            imgs, vname, err = process_media(photos, video)
            if err:
                st.error(t(err))
            else:
                store.add_post("feed", u["id"], text, imgs, vname, link=link)
                st.success(t("posted"))
    divider()
    feed_list("sfeed", owner_id=u["id"])


# =====================================================================
# HAWKER CALCULATOR
# =====================================================================
def _load_ledger():
    if os.path.exists(LEDGER_FILE):
        return pd.read_csv(LEDGER_FILE, dtype={"uid": str, "id": str})
    return pd.DataFrame(columns=LEDGER_COLS)


def _save_ledger(df):
    df.to_csv(LEDGER_FILE, index=False)


def calculator_tab(uid):
    section_title(t("add_entry"), "plus")
    with st.form("ledger_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns([1.3, 1.2, 1, 2])
        d = c1.date_input(t("date"), value=ui.today_sg())
        typ = c2.selectbox(t("type"), ["Earning", "Expense"], format_func=lambda k: t(k))
        amt = c3.number_input(t("amt"), min_value=0.0, step=0.5, format="%.2f")
        desc = c4.text_input(t("desc"), placeholder=t("desc_ph"))
        added = st.form_submit_button(t("add_btn"), type="primary")
    if added:
        if amt <= 0:
            st.error(t("err_amt"))
        else:
            df = _load_ledger()
            row = {"uid": uid, "id": uuid.uuid4().hex[:8], "date": d.isoformat(), "type": typ,
                   "amount": float(amt), "description": desc.strip()}
            _save_ledger(pd.concat([df, pd.DataFrame([row])], ignore_index=True))
            st.success(t("saved"))

    divider()
    section_title(t("your_numbers"), "chart")
    df = _load_ledger()
    mine = df[df["uid"] == uid].copy()
    mine["date"] = pd.to_datetime(mine["date"])
    mine["amount"] = mine["amount"].astype(float)

    view = st.radio(t("view"), ["Daily", "Monthly", "Yearly"], horizontal=True, format_func=lambda k: t(k))
    today = ui.today_sg()
    years = sorted(set(mine["date"].dt.year.tolist()) | {today.year})
    month_name = lambda m: MONTHS[cur_lang()][m - 1]

    if view == "Daily":
        day = st.date_input(t("pick_day"), value=today, key="calc_day")
        sel, group = mine[mine["date"].dt.date == day], None
    elif view == "Monthly":
        a, b = st.columns(2)
        y = a.selectbox(t("year"), years, index=years.index(today.year), key="calc_m_year")
        m = b.selectbox(t("month"), list(range(1, 13)), index=today.month - 1, format_func=month_name,
                        key="calc_month")
        sel = mine[(mine["date"].dt.year == y) & (mine["date"].dt.month == m)]
        group = sel["date"].dt.day
    else:
        y = st.selectbox(t("year"), years, index=years.index(today.year), key="calc_y_year")
        sel = mine[mine["date"].dt.year == y]
        group = sel["date"].dt.month

    earn = sel.loc[sel["type"] == "Earning", "amount"].sum()
    exp = sel.loc[sel["type"] == "Expense", "amount"].sum()
    m1, m2, m3 = st.columns(3)
    m1.metric(t("m_earn"), f"S${earn:,.2f}")
    m2.metric(t("m_exp"), f"S${exp:,.2f}")
    m3.metric(t("m_net"), f"S${earn - exp:,.2f}")

    if sel.empty:
        st.info(t("no_entries"))
        return
    if group is not None:
        chart = (sel.assign(period=group).groupby(["period", "type"])["amount"].sum()
                 .unstack(fill_value=0).reindex(columns=["Earning", "Expense"], fill_value=0))
        chart.columns = [t("Earning"), t("Expense")]
        st.bar_chart(chart)

    show = sel.sort_values("date")
    st.dataframe(pd.DataFrame({
        t("date"): show["date"].apply(fmt_date),
        t("type"): show["type"].map(lambda k: t(k)),
        t("amt"): show["amount"],
        t("desc"): show["description"],
    }), hide_index=True, use_container_width=True)

    with st.expander(t("delete_entry")):
        labels = {r["id"]: f"{fmt_date(r['date'])} · {t(r['type'])} · S${r['amount']:.2f} · {r['description']}"
                  for _, r in show.iterrows()}
        pick = st.selectbox(t("choose_entry"), list(labels.keys()), format_func=lambda k: labels[k])
        if st.button(t("delete_sel"), key="b_del_entry"):
            _save_ledger(_load_ledger().query("id != @pick"))
            st.rerun()

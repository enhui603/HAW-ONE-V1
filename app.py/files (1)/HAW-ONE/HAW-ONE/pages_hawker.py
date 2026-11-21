"""Hawker Schedule (cleaning + closures) and the Nearby Hawker map. Uses hawker_centres_final.csv."""
import html
from datetime import datetime

import pandas as pd
import streamlit as st

import hawkers
import store
import ui
from i18n import t, fmt_date
from ui import go, nav_bar, page_header, section_title, divider


def _region_chip(region):
    c = store.REGION_COLORS[region]
    return (f"<span class='chip' style='background:{c}33'><i style='display:inline-block;width:.7rem;height:.7rem;"
            f"border-radius:50%;background:{c};border:2px solid {ui.INK};margin-right:.4rem'></i>"
            f"{html.escape(t(region))}</span>")


def show_map(df, height=420):
    kw = dict(latitude="lat", longitude="lon", color="color", size="size")
    try:
        st.map(df, height=height, **kw)
    except TypeError:
        st.map(df, **kw)


def _point(row, color=ui.INK, size=700):
    return pd.DataFrame([{"lat": row["latitude_hc"], "lon": row["longitude_hc"], "color": color, "size": size}])


def _pick_region(label_key="region"):
    r = st.pills(t(label_key), ["all", "north", "south", "east", "west"], default="all",
                 format_func=lambda x: t(x))
    return r or "all"


# =====================================================================
# SCHEDULE
# =====================================================================
def schedule_page():
    nav_bar("p")
    page_header(t("sched_title"), t("sched_desc"), "haw_sim")
    hc = hawkers.load_hawkers()
    today = ui.today_sg()
    tab1, tab2 = st.tabs([t("tab_clean"), t("tab_closure")])
    with tab1:
        if hc is None:
            st.warning(t("no_data"))
        else:
            cleaning_tab(hc, today)
    with tab2:
        closure_tab(hc, today)


def cleaning_tab(hc, today):
    section_title(t("soon_title"), "sparkle")
    up = hawkers.upcoming_cleaning(hc, today)
    st.markdown(f"**{html.escape(t('affected_n', n=up['name'].nunique()))}**")
    if up.empty:
        st.info(t("none_soon"))
    else:
        region = _pick_region()
        f = up if region == "all" else up[up["region"] == region]
        letters = sorted(set(f["letter"]))
        letter = st.pills(t("letter"), ["all"] + letters, default="all",
                          format_func=lambda x: t("all") if x == "all" else x) or "all"
        if letter != "all":
            f = f[f["letter"] == letter]
        f = f.reset_index(drop=True)
        if f.empty:
            st.info(t("none_soon"))
        else:
            i = st.selectbox(t("pick_centre"), list(range(len(f))),
                             format_func=lambda k: f"{f.loc[k, 'name']} · {fmt_date(f.loc[k, 'start'])}")
            r = f.loc[i]
            s, e = r["start"].date(), r["end"].date()
            now = s <= today <= e
            with st.container(border=True):
                st.markdown(f"**{html.escape(r['name'])}**")
                st.caption(r["address"])
                st.markdown(_region_chip(r["region"]) + ui.chip(t("st_now") if now else t("st_upcoming"),
                                                               "now" if now else "upcoming"),
                            unsafe_allow_html=True)
                span = fmt_date(r["start"]) if s == e else f"{fmt_date(r['start'])} → {fmt_date(r['end'])}"
                if now:
                    st.metric(span, t("st_now"), delta=t("ends_in", n=(e - today).days), delta_color="off")
                    total = max((e - s).days, 1)
                    st.progress(min(1.0, (today - s).days / total))
                else:
                    st.metric(span, t("in_days", n=(s - today).days))
                row = hc.loc[r["idx"]]
                show_map(_point(row, store.REGION_COLORS[row["region"]], 500), height=220)

    divider()
    section_title(t("find_centre"), "search")
    choice = st.selectbox(t("pick_centre"), hawkers.centre_names(), key="clean_find")
    row = hc[hc["name"] == choice].iloc[0]
    if bool(row["closed_all_2026"]):
        st.warning(t("closed_2026"))
    cols = st.columns(2)
    for i, q in enumerate(hawkers.QUARTERS):
        s, e, d = hawkers.window(row, q)
        status = hawkers.status_of(s, e, today)
        with cols[i % 2]:
            with st.container(border=True):
                st.markdown(f"**{html.escape(t('quarter', n=i + 1))}**")
                if s is None:
                    st.write("—")
                else:
                    st.write(fmt_date(s) if s == e else f"{fmt_date(s)} → {fmt_date(e)}")
                st.markdown(ui.chip(t("st_" + status), status), unsafe_allow_html=True)
    if bool(row["other_works_in_2026"]):
        st.info(t("works_2026", start=fmt_date(row["other_works_startdate"]), end=fmt_date(row["other_works_enddate"])))
    st.caption(t("data_note"))


def closure_tab(hc, today):
    if hc is not None:
        section_title(t("long_closures"), "lock")
        lc = hawkers.long_closures(hc)
        lc["status"] = [hawkers.status_of(a, b, today) for a, b in
                        zip(lc["other_works_startdate"], lc["other_works_enddate"])]
        pick = st.pills(t("view"), ["all", "now", "upcoming", "done"], default="all",
                        format_func=lambda x: t("all") if x == "all" else t("st_" + x), key="closure_filter") or "all"
        f = lc if pick == "all" else lc[lc["status"] == pick]
        f = f.reset_index(drop=True)
        if f.empty:
            st.info(t("no_works"))
        else:
            i = st.selectbox(t("pick_closure"), list(range(len(f))),
                             format_func=lambda k: f"{f.loc[k, 'name']} · {fmt_date(f.loc[k, 'other_works_startdate'])}",
                             key=f"closure_pick_{pick}")
            r = f.loc[i]
            s, e = r["other_works_startdate"].date(), r["other_works_enddate"].date()
            with st.container(border=True):
                st.markdown(f"**{html.escape(r['name'])}**")
                st.caption(r["address_myenv"])
                st.markdown(_region_chip(r["region"]) + ui.chip(t("st_" + r["status"]), r["status"]),
                            unsafe_allow_html=True)
                span = f"{fmt_date(r['other_works_startdate'])} → {fmt_date(r['other_works_enddate'])}"
                if r["status"] == "now":
                    st.metric(span, t("st_now"), delta=t("days_left", n=(e - today).days), delta_color="off")
                    st.progress(min(1.0, max(0.0, (today - s).days / max((e - s).days, 1))))
                elif r["status"] == "upcoming":
                    st.metric(span, t("in_days", n=(s - today).days))
                else:
                    st.metric(span, t("st_done"))
                if bool(r["closed_all_2026"]):
                    st.warning(t("closed_2026"))
                show_map(_point(r, store.REGION_COLORS[r["region"]], 500), height=220)
        divider()

    section_title(t("stall_closures"), "megaphone")
    shown = 0
    for p in store.get_posts("broadcast"):
        if p["kind"] != "closure" or not p.get("end") or p["end"] < today.isoformat():
            continue
        a = store.get_user(p["author_id"])
        if not a or a.get("suspended"):
            continue
        shown += 1
        with st.container(border=True):
            st.button(f"{a['stall']} · {a['centre']}", key=f"p_cl_{p['id']}", on_click=go, args=("v_channel",),
                      kwargs={"channel_id": a["id"]})
            ui.closure_box(p["start"], p["end"], p.get("text", ""), today)
    if not shown:
        st.info(t("none_stall_closures"))


# =====================================================================
# NEARBY (Singapore map only: no GPS, no tracking)
# =====================================================================
def nearby_page():
    nav_bar("p")
    page_header(t("near_title"), t("near_desc"), "haw_sim")
    hc = hawkers.load_hawkers()
    if hc is None:
        st.warning(t("no_data"))
        return
    today = ui.today_sg()

    region = _pick_region()
    f = hc if region == "all" else hc[hc["region"] == region]
    f = f.sort_values("name").reset_index(drop=True)

    legend = "".join(f"<span><i style='background:{c}'></i>{html.escape(t(r))}</span>"
                     for r, c in store.REGION_COLORS.items())
    st.markdown(f"<div class='legend'>{legend}</div>", unsafe_allow_html=True)

    pts = pd.DataFrame({"lat": f["latitude_hc"], "lon": f["longitude_hc"],
                        "color": f["region"].map(store.REGION_COLORS),
                        "size": (250 + f["stalls"] * 5).clip(300, 1400)})
    section_title(t("pick_centre"), "pin")
    i = st.selectbox(t("pick_centre"), list(range(len(f))), format_func=lambda k: f.loc[k, "name"],
                     label_visibility="collapsed", key=f"near_pick_{region}")
    r = f.loc[i]
    pts = pd.concat([pts, _point(r, ui.INK, 900)], ignore_index=True)       # selected centre on top
    show_map(pts, height=460)
    st.caption(t("size_note"))

    with st.container(border=True):
        st.markdown(f"**{html.escape(r['name'])}**")
        st.caption(r["address_myenv"])
        st.markdown(_region_chip(r["region"]), unsafe_allow_html=True)
        station = str(r["STATION_NA"]).title().replace(" Mrt", " MRT").replace(" Lrt", " LRT")
        st.write(t("walk_from", min=int(round(r["walk_min"])), station=station))
        st.write(t("stalls_count", food=int(r["no_of_food_stalls"]), market=int(r["no_of_market_stalls"])))
        if bool(r["closed_all_2026"]):
            st.warning(t("closed_2026"))
        else:
            nxt = hawkers.next_cleaning(r, today)
            st.write(t("next_clean", date=fmt_date(nxt)) if nxt is not None else t("no_more_clean"))
            if bool(r["other_works_in_2026"]):
                st.info(t("works_2026", start=fmt_date(r["other_works_startdate"]),
                          end=fmt_date(r["other_works_enddate"])))

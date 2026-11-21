"""Shared look, navigation, login state and small UI helpers."""
import base64
import html
import os
import time
from datetime import date, datetime

import streamlit as st

import store
from i18n import t

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
ICONS = os.path.join(ASSETS, "icons")

BLUE = "#5B9BD5"   # Haw Bo  (seller)
PINK = "#E8587A"   # Haw Sim (visitor)
INK = "#3B2A33"
CREAM = "#FFF8F0"

SIZES = {"A": 100, "A+": 125, "A++": 150}
DEFAULT_SIZE = "A+"
NAV_KEYS = ["channel_id", "stall_id", "post_id", "profile_id"]
EMOJIS = ["👍", "❤️", "😋", "😮", "🙏"]


# =====================================================================
# files / icons / small html bits
# =====================================================================
@st.cache_data
def b64_file(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def icon_html(name, size=40):
    path = os.path.join(ICONS, f"{name}.svg")
    if not os.path.exists(path):
        return ""
    return (f"<img src='data:image/svg+xml;base64,{b64_file(path)}' width='{size}' height='{size}' "
            f"class='icon' alt=''>")


def section_title(text, icon):
    st.markdown(f"<div class='sec'>{icon_html(icon, 40)}<h3>{html.escape(text)}</h3></div>",
                unsafe_allow_html=True)


def divider():
    path = os.path.join(ASSETS, "divider.svg")
    if os.path.exists(path):
        st.markdown(f"<img class='wave' src='data:image/svg+xml;base64,{b64_file(path)}' alt=''>",
                    unsafe_allow_html=True)
    else:
        st.divider()


def chip(text, cls="done"):
    return f"<span class='chip {cls}'>{html.escape(text)}</span>"


def stars_html(n, total=3):
    n = int(round(n))
    return f"<span class='stars'>{'★' * n}{'☆' * (total - n)}</span>"


def rank_badge(info):
    dark_text = info["color"] == "#E0A800"
    style = f"background:{info['color']};color:{'#3B2A33' if dark_text else '#fff'}"
    return f"<span class='badge' style='{style}'>{html.escape(info['name'])}</span>"


def avatar_html(name, size=48, ring=INK):
    path = store.media_path(name) if name else None
    if path and os.path.exists(path):
        return (f"<img class='avatar' src='data:image/jpeg;base64,{b64_file(path)}' "
                f"style='width:{size}px;height:{size}px;border-color:{ring}' alt=''>")
    return (f"<div class='avatar ph' style='width:{size}px;height:{size}px;border-color:{ring}'>"
            f"{icon_html('bowl', int(size * .6))}</div>")


def today_sg():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Singapore")).date()
    except Exception:
        return date.today()


# =====================================================================
# style
# =====================================================================
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;700&family=Noto+Sans+Tamil:wght@400;700&display=swap');
html { font-size: __PCT__% !important; }
:root, .stApp { color-scheme: light; }

.stApp, .stApp p, .stApp label, .stApp li, .stApp h1, .stApp h2, .stApp h3, .stApp h4,
.stApp button, .stApp input, .stApp textarea, .stApp a,
.stApp [data-baseweb="select"] div, .stApp [data-testid="stMetricValue"],
.stApp [data-testid="stMetricLabel"], .stApp [role="tab"], .stApp table {
    font-family: 'Fredoka', 'Noto Sans SC', 'Noto Sans Tamil', sans-serif !important;
}
[data-testid="stHeader"] { background: transparent; }
.stApp { background: url(data:image/jpeg;base64,__BG__) center / cover fixed; }
.block-container {
    max-width: 1000px; margin-top: 2rem; padding: 2rem 2.5rem 2.5rem;
    background: __CREAM__; border: 4px solid __INK__; border-radius: 32px; box-shadow: 10px 10px 0 __INK__;
}
@media (max-width: 640px) { .block-container { padding: 1.2rem 1rem 1.5rem; margin-top: .5rem; } }
.stApp p, .stApp label, .stApp li, .stApp h1, .stApp h2, .stApp h3, .stApp h4 { color: __INK__; }

.title { text-align:center; font-size:4rem; font-weight:700; letter-spacing:4px; color:__INK__; margin:0; line-height:1.1; }
.title span { color:__PINK__; display:inline-block; animation: wiggle 2.4s ease-in-out infinite; }
.tagline { text-align:center; font-size:1.25rem; color:__INK__; margin:.3rem 0 1.5rem; }
.role-name { text-align:center; font-size:1.5rem; font-weight:600; color:__INK__; margin:.2rem 0 0; }
.role-desc { text-align:center; color:__INK__; opacity:.8; margin:0 0 .6rem; }
.card-icon { text-align:center; }
.page-title { font-size:2rem; font-weight:700; color:__INK__; margin:0; }
.page-sub { color:__INK__; opacity:.8; margin:0 0 1rem; }
.sec { display:flex; align-items:center; gap:.7rem; margin:.6rem 0 .3rem; }
.sec h3 { margin:0; padding:0; color:__INK__; font-weight:600; }
.wave { width:100%; height:18px; margin:.8rem 0; display:block; }
.chip { display:inline-block; padding:.15rem .8rem; border-radius:999px; font-weight:600; border:2px solid __INK__; font-size:.85rem; margin:.1rem .2rem .1rem 0; }
.chip.done { background:#E5E1E3; } .chip.now { background:__PINK__; color:white; }
.chip.upcoming { background:#CFE3F7; } .chip.tbc { background:#FFE9A8; }
.badge { display:inline-block; padding:.1rem .7rem; border-radius:999px; font-weight:600; font-size:.85rem; }
.stars { color:#E0A800; letter-spacing:2px; font-size:1.1em; }
.avatar { border-radius:50%; object-fit:cover; border:3px solid __INK__; display:block; background:#fff; }
.avatar.ph { display:flex; align-items:center; justify-content:center; }
.who { display:flex; align-items:center; gap:.7rem; }
.who b { font-size:1.05rem; color:__INK__; }
.tile { aspect-ratio:1/1; border-radius:14px; border:3px solid __INK__; background-size:cover; background-position:center;
        display:flex; align-items:center; justify-content:center; text-align:center; padding:.5rem; overflow:hidden;
        font-size:.85rem; color:__INK__; background-color:#FDEBF0; }
.tile.video { background:linear-gradient(135deg, __PINK__, __BLUE__); color:#fff; font-weight:600; font-size:1.1rem; }
.closure { border:3px solid __INK__; border-radius:16px; padding:.6rem 1rem; background:#FFE1E6; color:__INK__; font-weight:600; margin:.4rem 0; }
.closure.soon { background:#FFF1C9; }
.legend { display:flex; flex-wrap:wrap; gap:.4rem .9rem; margin:.4rem 0; }
.legend span { display:inline-flex; align-items:center; gap:.4rem; font-weight:600; color:__INK__; }
.legend i { width:1rem; height:1rem; border-radius:50%; border:2px solid __INK__; display:inline-block; }

/* nav + small rows stay on one line on phones */
.st-key-navbar [data-testid="stHorizontalBlock"], .st-key-topbar [data-testid="stHorizontalBlock"],
[class*="st-key-react_"] [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: .4rem !important; }
.st-key-navbar [data-testid="stColumn"], .st-key-topbar [data-testid="stColumn"], [class*="st-key-react_"] [data-testid="stColumn"],
.st-key-navbar [data-testid="column"], .st-key-topbar [data-testid="column"], [class*="st-key-react_"] [data-testid="column"] {
    min-width: 0 !important; flex: 1 1 0 !important; width: auto !important;
}

/* role / menu cards */
[class*="st-key-card_blue"], [class*="st-key-card_pink"] {
    border: 3px solid __INK__; border-radius: 24px; padding: 1rem; margin-bottom: .6rem;
    transition: transform .2s ease, box-shadow .2s ease;
}
[class*="st-key-card_blue"] { background: #EAF3FC; } [class*="st-key-card_pink"] { background: #FDEBF0; }
[class*="st-key-card_blue"]:hover, [class*="st-key-card_pink"]:hover { transform: translateY(-6px) scale(1.01); box-shadow: 6px 8px 0 __INK__; }
[class*="st-key-card_"] [data-testid="stImage"] { display:flex; justify-content:center; }

/* buttons: b_ = blue (seller side), p_ = pink (visitor side) */
[class*="st-key-b_"] button, [class*="st-key-p_"] button, [data-testid="stLinkButton"] a {
    color: white !important; font-weight: 600; border: 3px solid __INK__; border-radius: 999px; box-shadow: 3px 3px 0 __INK__;
    transition: transform .15s ease, box-shadow .15s ease, filter .15s ease;
}
[class*="st-key-b_"] button p, [class*="st-key-p_"] button p, [data-testid="stLinkButton"] a p { color: white !important; }
[class*="st-key-b_"] button { background: __BLUE__; } [class*="st-key-p_"] button { background: __PINK__; }
[data-testid="stLinkButton"] a { background: __BLUE__; }
[class*="st-key-b_"] button:hover, [class*="st-key-p_"] button:hover, [data-testid="stLinkButton"] a:hover {
    filter: brightness(1.08); color: white; border-color: __INK__; transform: translateY(-2px); box-shadow: 3px 5px 0 __INK__; }
[class*="st-key-b_"] button:active, [class*="st-key-p_"] button:active { transform: translate(2px, 2px); box-shadow: 1px 1px 0 __INK__; }

/* home button, emoji reactions, small text links */
.st-key-h_home button { border: 3px solid __INK__; border-radius: 999px; background: #fff; font-weight: 600; box-shadow: 3px 3px 0 __INK__; }
[class*="st-key-r_"] button, [class*="st-key-rs_"] button {
    border: 2px solid __INK__; border-radius: 999px; background: #fff; padding: .1rem .3rem; min-height: 0; font-weight: 600; }
[class*="st-key-rs_"] button { background: #FFD6E0; box-shadow: 2px 2px 0 __INK__; }
[class*="st-key-link_"] button { background: none; border: none; box-shadow: none; text-decoration: underline; padding: 0; min-height: 0; }
[class*="st-key-link_"] button p { font-size: .8rem; color: #6b5b63 !important; }

/* animations */
@keyframes fadeUp { from { opacity:0; transform: translateY(18px); } to { opacity:1; transform:none; } }
@keyframes bob { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-8px); } }
@keyframes wiggle { 0%,100% { transform: rotate(-6deg); } 50% { transform: rotate(6deg) scale(1.15); } }
.title, .tagline, .page-title, .page-sub, .sec, .wave, .closure { animation: fadeUp .5s ease both; }
[class*="st-key-card_"] { animation: fadeUp .55s ease both; }
[data-testid="stColumn"]:nth-child(2) [class*="st-key-card_"] { animation-delay: .12s; }
[data-testid="stVerticalBlockBorderWrapper"] { animation: fadeUp .45s ease both; }
[data-testid="stTabs"] { animation: fadeUp .45s ease both; }
[class*="st-key-card_"] [data-testid="stImage"] img, [class*="st-key-mascot_"] img { animation: bob 3.2s ease-in-out infinite; }
@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
</style>
"""


def inject_css():
    pct = SIZES.get(st.session_state.get("fsize", DEFAULT_SIZE), 125)
    bg = b64_file(os.path.join(ASSETS, "background.jpg"))
    css = (CSS.replace("__PCT__", str(pct)).replace("__BG__", bg).replace("__INK__", INK)
           .replace("__PINK__", PINK).replace("__BLUE__", BLUE).replace("__CREAM__", CREAM))
    st.markdown(css, unsafe_allow_html=True)


# =====================================================================
# navigation + login state
# =====================================================================
def go(view, **ids):
    ss = st.session_state
    hist = ss.setdefault("hist", [])
    hist.append((ss.get("view", "landing"), {k: ss.get(k) for k in NAV_KEYS}))
    del hist[:-30]
    ss["view"] = view
    for k, v in ids.items():
        ss[k] = v


def back():
    ss = st.session_state
    hist = ss.get("hist", [])
    if hist:
        view, ids = hist.pop()
        ss["view"] = view
        for k, v in ids.items():
            ss[k] = v
    else:
        ss["view"] = "landing"


def home():
    st.session_state["hist"] = []
    st.session_state["view"] = "landing"


def reset_to(view):
    """Jump somewhere and make Back go straight to the start page."""
    st.session_state["hist"] = [("landing", {})]
    st.session_state["view"] = view


def me():
    uid = st.session_state.get("auth")
    if not uid:
        return None
    u = store.get_user(uid)
    if not u:
        st.session_state["auth"] = None
    return u


def login_user(uid):
    st.session_state["auth"] = uid
    st.session_state["guest"] = False
    st.session_state["fails"] = 0


def logout():
    ss = st.session_state
    ss["auth"] = None
    ss["guest"] = False
    ss["hist"] = []
    ss["view"] = "landing"


def login_locked():
    return time.time() < st.session_state.get("lock_until", 0)


def login_failed():
    ss = st.session_state
    ss["fails"] = ss.get("fails", 0) + 1
    if ss["fails"] >= 5:
        ss["lock_until"] = time.time() + 60
        ss["fails"] = 0


def open_own_profile():
    u = me()
    if not u:
        return
    if u["role"] == "seller":
        go("v_stall", stall_id=u["id"])
    else:
        go("v_profile", profile_id=u["id"])


def nav_bar(color="p"):
    """Back + Home on every page, plus who is logged in."""
    u = me()
    with st.container(key="navbar"):
        c = st.columns(2)
        c[0].button(t("back"), key=f"{color}_back", on_click=back, use_container_width=True)
        c[1].button(t("nav_home"), key="h_home", on_click=home, use_container_width=True)
        if u:
            d = st.columns([2, 1.2, 1.2], vertical_alignment="center")
            d[0].markdown(f"**{html.escape(t('hi', name=store.display_name(u)))}**")
            d[1].button(t("profile"), key="l_profile", on_click=open_own_profile, use_container_width=True)
            d[2].button(t("logout"), key="l_logout", on_click=logout, use_container_width=True)


def top_bar():
    with st.container(key="topbar"):
        left, right = st.columns([1.3, 1], vertical_alignment="center")
        left.radio(t("text_size"), list(SIZES.keys()), key="fsize", horizontal=True)
        from i18n import LANGS, LANG_NAMES
        right.selectbox(t("language"), LANGS, key="lang", format_func=lambda c: LANG_NAMES[c])


def page_header(title, subtitle, mascot):
    c1, c2 = st.columns([1, 6], vertical_alignment="center")
    with c1:
        with st.container(key="mascot_head"):
            st.image(os.path.join(ASSETS, f"{mascot}.png"), width=110)
    c2.markdown(f"<p class='page-title'>{html.escape(title)}</p><p class='page-sub'>{html.escape(subtitle)}</p>",
                unsafe_allow_html=True)


def menu_card(color, key, icon, title, desc, button_label, on_click=None, args=(), kwargs=None, link=None):
    prefix = "b" if color == "blue" else "p"
    with st.container(key=f"card_{color}_{key}"):
        st.markdown(f"<div class='card-icon'>{icon_html(icon, 72)}</div>", unsafe_allow_html=True)
        st.markdown(f"<p class='role-name'>{html.escape(title)}</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='role-desc'>{html.escape(desc)}</p>", unsafe_allow_html=True)
        if link:
            st.link_button(button_label, link, use_container_width=True)
        else:
            st.button(button_label, key=f"{prefix}_{key}", use_container_width=True,
                      on_click=on_click, args=args, kwargs=kwargs or {})


# =====================================================================
# email codes
# =====================================================================
def mail_cfg():
    try:
        cfg = st.secrets.get("smtp")
        return dict(cfg) if cfg else None
    except Exception:
        return None


def deliver_code(email, code):
    """Returns 'sent', 'demo' (no email set up yet, so the code is shown on screen) or 'fail'."""
    cfg = mail_cfg()
    if not cfg:
        return "demo"
    ok = store.send_email(cfg, email, f"HAW-ONE code: {code}",
                          f"Your HAW-ONE code is {code}\nIt works for 10 minutes.\n"
                          "If you did not ask for it, you can ignore this email.")
    return "sent" if ok else "fail"


def show_code_notice(status, email, code):
    if status == "sent":
        st.success(t("sent_to", email=email))
    elif status == "demo":
        st.warning(t("demo_code", code=code))
    else:
        st.error(t("mail_fail"))


# =====================================================================
# post media + closure banners
# =====================================================================
def media_block(p):
    imgs = [store.media_path(i) for i in p.get("images", []) if os.path.exists(store.media_path(i))]
    for i in range(0, len(imgs), 3):
        row = imgs[i:i + 3]
        for col, path in zip(st.columns(len(row)), row):
            col.image(path, use_container_width=True)
    v = p.get("video")
    if v and os.path.exists(store.media_path(v)):
        st.video(store.media_path(v))


def closure_box(start, end, note="", today=None):
    from i18n import fmt_date
    today = today or today_sg()
    s = datetime.fromisoformat(start).date()
    e = datetime.fromisoformat(end).date()
    if s <= today <= e:
        text = t("closed_now", end=fmt_date(e))
        cls = "closure"
    else:
        text = t("closed_range", start=fmt_date(s), end=fmt_date(e))
        cls = "closure soon"
    extra = f"<div style='font-weight:400'>{html.escape(note)}</div>" if note else ""
    st.markdown(f"<div class='{cls}'>{html.escape(text)}{extra}</div>", unsafe_allow_html=True)

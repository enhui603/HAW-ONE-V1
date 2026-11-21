"""Seller + visitor accounts: menus, login, register, forgot password."""
import streamlit as st

import hawkers
import store
import ui
from i18n import t
from ui import go, nav_bar, page_header, menu_card, reset_to

NEA_URL = "https://www.nea.gov.sg/our-services/hawker-management/becoming-a-hawker"


def _color(role):
    return "b" if role == "seller" else "p"


def _mascot(role):
    return "haw_bo" if role == "seller" else "haw_sim"


# =====================================================================
# SELLER MENU
# =====================================================================
def seller_home():
    nav_bar("b")
    page_header(t("seller"), t("seller_sub"), "haw_bo")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        menu_card("blue", "login", "login", t("login_title"), t("login_desc"), t("login_btn"),
                  on_click=go, args=("seller_login",))
    with c2:
        menu_card("blue", "reg", "plus", t("reg_title"), t("reg_desc"), t("register"),
                  on_click=go, args=("seller_register_code",))
    menu_card("blue", "bid", "bid", t("bid_title"), t("bid_desc"), t("bid_btn"), link=NEA_URL)


# =====================================================================
# VISITOR MENU (register as commentor / log in / guest)
# =====================================================================
def _guest():
    st.session_state["guest"] = True
    st.session_state["auth"] = None
    go("visitor_home")


def visitor_gate():
    nav_bar("p")
    page_header(t("visitor"), t("v_sub"), "haw_sim")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        menu_card("pink", "reg", "plus", t("gate_register"), t("gate_register_desc"), t("register"),
                  on_click=go, args=("visitor_register_form",))
    with c2:
        menu_card("pink", "login", "login", t("login_btn"),
                  t("gate_login_desc"), t("login_btn"), on_click=go, args=("visitor_login",))
    menu_card("pink", "guest", "search", t("gate_guest"), t("gate_guest_desc"), t("continue"), on_click=_guest)


# =====================================================================
# LOGIN
# =====================================================================
def login_page(role):
    c = _color(role)
    nav_bar(c)
    page_header(t("login_title") if role == "seller" else t("login_btn"), t("login_sub"), _mascot(role))
    with st.form(f"login_{role}"):
        email = st.text_input(t("email"))
        pw = st.text_input(t("password"), type="password")
        ok = st.form_submit_button(t("login_btn"), type="primary")
    if ok:
        if ui.login_locked():
            st.error(t("err_wait"))
        else:
            user = store.verify_login(email, pw, role)
            if user and user.get("suspended"):
                st.error(t("suspended"))
            elif user:
                ui.login_user(user["id"])
                if role == "seller":
                    reset_to("seller_admin")
                else:
                    reset_to("visitor_home")
                st.rerun()
            else:
                ui.login_failed()
                st.error(t("err_login"))
    st.button(t("forgot"), key=f"link_forgot_{role}", on_click=go, args=(f"{role}_forgot",))
    if role == "visitor":
        st.button(t("register"), key="link_reg_v", on_click=go, args=("visitor_register_form",))
    else:
        st.button(t("register"), key="link_reg_s", on_click=go, args=("seller_register_code",))


def seller_login():
    login_page("seller")


def visitor_login():
    login_page("visitor")


# =====================================================================
# FORGOT PASSWORD  (email -> 6-digit code -> new password)
# =====================================================================
def forgot_page(role):
    c = _color(role)
    nav_bar(c)
    page_header(t("forgot"), t("login_sub"), _mascot(role))
    key = f"reset_{role}"
    ss = st.session_state

    if key not in ss:
        with st.form(f"forgot_{role}"):
            email = st.text_input(t("email"))
            go_btn = st.form_submit_button(t("send_code"), type="primary")
        if go_btn:
            if not store.valid_email(email):
                st.error(t("err_email"))
            else:
                user = store.find_by_email(email)
                if user and user["role"] == role:
                    code, ch = store.new_challenge({"uid": user["id"]})
                    status = ui.deliver_code(user["email"], code)
                    ss[key] = {"ch": ch, "email": user["email"], "status": status, "code": code}
                else:
                    ss[key] = {"ch": None, "email": email.strip(), "status": "none", "code": ""}
                st.rerun()
        return

    info = ss[key]
    if info["status"] == "none":
        st.info(t("forgot_sent"))
    else:
        ui.show_code_notice(info["status"], info["email"], info["code"])
    with st.form(f"reset_form_{role}"):
        code_in = st.text_input(t("code_field"))
        pw1 = st.text_input(t("new_password"), type="password")
        pw2 = st.text_input(t("password2"), type="password")
        ok = st.form_submit_button(t("reset_btn"), type="primary")
    if ok:
        if len(pw1) < 8:
            st.error(t("err_pw_short"))
        elif pw1 != pw2:
            st.error(t("err_pw_match"))
        elif info["ch"] and store.check_challenge(info["ch"], code_in):
            store.set_password(info["ch"]["payload"]["uid"], pw1)
            del ss[key]
            st.success(t("pw_updated"))
            reset_to(f"{role}_login")
            st.rerun()
        else:
            st.error(t("bad_code"))
    st.button(t("resend"), key=f"link_resend_{role}", on_click=lambda: ss.pop(key, None))


def seller_forgot():
    forgot_page("seller")


def visitor_forgot():
    forgot_page("visitor")


# =====================================================================
# SELLER REGISTER:  trial code -> details
# =====================================================================
def seller_register_code():
    nav_bar("b")
    page_header(t("reg_title"), t("trial_hint"), "haw_bo")
    with st.form("trial_form"):
        code = st.text_input(t("trial_code"), placeholder="HAW-XXXX-XXXX")
        ok = st.form_submit_button(t("continue"), type="primary")
    if ok:
        if ui.login_locked():
            st.error(t("err_wait"))
        elif store.invite_valid(code):
            st.session_state["trial_code"] = code
            go("seller_register_form")
            st.rerun()
        else:
            ui.login_failed()
            st.error(t("bad_trial"))


def seller_register_form():
    nav_bar("b")
    page_header(t("reg_title"), t("reg_desc"), "haw_bo")
    code = st.session_state.get("trial_code")
    if not code or not store.invite_valid(code):
        st.error(t("bad_trial"))
        return
    names = hawkers.centre_names() or ["—"]
    with st.form("seller_reg_form"):
        stall = st.text_input(t("stall_name"))
        logo = st.file_uploader(t("stall_logo"), type=["png", "jpg", "jpeg"])
        centre = st.selectbox(t("col_centre"), names)
        unit = st.text_input(t("unit_no"), placeholder="#01-23")
        email = st.text_input(t("email"))
        pw1 = st.text_input(t("password"), type="password")
        pw2 = st.text_input(t("password2"), type="password")
        ok = st.form_submit_button(t("register"), type="primary")
    if not ok:
        return
    if not (stall.strip() and unit.strip() and email.strip() and pw1):
        st.error(t("err_fields"))
    elif logo is None:
        st.error(t("need_logo"))
    elif not store.valid_email(email):
        st.error(t("err_email"))
    elif store.find_by_email(email):
        st.error(t("err_taken_email"))
    elif len(pw1) < 8:
        st.error(t("err_pw_short"))
    elif pw1 != pw2:
        st.error(t("err_pw_match"))
    else:
        logo_name = store.save_avatar(logo.getvalue())
        if not logo_name:
            st.error(t("err_photo"))
            return
        user = store.create_seller(stall, logo_name, centre, unit, email, pw1)
        store.invite_use(code, user["id"])
        st.session_state.pop("trial_code", None)
        reset_to("seller_registered")
        st.rerun()


def seller_registered():
    nav_bar("b")
    page_header(t("reg_title"), t("reg_done"), "haw_bo")
    st.success(t("reg_done"))
    st.button(t("login_btn"), key="b_goto_login", on_click=reset_to, args=("seller_login",))


# =====================================================================
# VISITOR REGISTER:  details -> email OTP -> account
# =====================================================================
def visitor_register_form():
    nav_bar("p")
    page_header(t("gate_register"), t("gate_register_desc"), "haw_sim")
    with st.form("visitor_reg_form"):
        username = st.text_input(t("username"))
        avatar = st.file_uploader(t("avatar"), type=["png", "jpg", "jpeg"])
        email = st.text_input(t("email"))
        pw1 = st.text_input(t("password"), type="password")
        pw2 = st.text_input(t("password2"), type="password")
        ok = st.form_submit_button(t("send_code"), type="primary")
    if not ok:
        return
    if not (username.strip() and email.strip() and pw1):
        st.error(t("err_fields"))
    elif not store.valid_username(username.strip()):
        st.error(t("err_username"))
    elif store.find_by_username(username):
        st.error(t("err_username_taken"))
    elif avatar is None:
        st.error(t("need_avatar"))
    elif not store.valid_email(email):
        st.error(t("err_email"))
    elif store.find_by_email(email):
        st.error(t("err_taken_email"))
    elif len(pw1) < 8:
        st.error(t("err_pw_short"))
    elif pw1 != pw2:
        st.error(t("err_pw_match"))
    else:
        code, ch = store.new_challenge()
        status = ui.deliver_code(email.strip().lower(), code)
        st.session_state["reg_pending"] = {
            "username": username.strip(), "email": email.strip().lower(), "pw": store.hash_password(pw1),
            "avatar": avatar.getvalue(), "ch": ch, "status": status, "code": code}
        go("visitor_register_otp")
        st.rerun()


def _resend_otp():
    p = st.session_state.get("reg_pending")
    if p:
        code, ch = store.new_challenge()
        p.update(ch=ch, code=code, status=ui.deliver_code(p["email"], code))


def visitor_register_otp():
    nav_bar("p")
    page_header(t("verify"), t("code_field"), "haw_sim")
    p = st.session_state.get("reg_pending")
    if not p:
        st.error(t("bad_code"))
        return
    ui.show_code_notice(p["status"], p["email"], p["code"])
    with st.form("otp_form"):
        code_in = st.text_input(t("code_field"))
        ok = st.form_submit_button(t("verify"), type="primary")
    if ok:
        if not store.check_challenge(p["ch"], code_in):
            st.error(t("bad_code"))
        elif store.find_by_username(p["username"]) or store.find_by_email(p["email"]):
            st.error(t("err_username_taken"))
        else:
            av = store.save_avatar(p["avatar"])
            store.create_visitor(p["username"], av, p["email"], p["pw"])
            st.session_state.pop("reg_pending", None)
            reset_to("visitor_registered")
            st.rerun()
    st.button(t("resend"), key="link_resend_otp", on_click=_resend_otp)


def visitor_registered():
    nav_bar("p")
    page_header(t("gate_register"), t("reg_done"), "haw_sim")
    st.success(t("reg_done"))
    st.button(t("login_btn"), key="p_goto_login", on_click=reset_to, args=("visitor_login",))

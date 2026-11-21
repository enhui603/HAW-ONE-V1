import os

import streamlit as st

HERE = os.path.dirname(os.path.abspath(__file__))
st.set_page_config(page_title="HAW-ONE", page_icon=os.path.join(HERE, "assets", "haw_sim.png"), layout="wide")

import pages_account as acc          # noqa: E402
import pages_community as com        # noqa: E402
import pages_hawker as haw           # noqa: E402
import pages_seller as sel           # noqa: E402
import pages_team as team            # noqa: E402
import ui                            # noqa: E402
from i18n import t                   # noqa: E402

ss = st.session_state
ss.setdefault("lang", "en")
ss.setdefault("fsize", ui.DEFAULT_SIZE)
ss.setdefault("view", "landing")
ss.setdefault("hist", [])
ss.setdefault("auth", None)

ui.inject_css()

# Team page: open the app with ?team=1
if st.query_params.get("team"):
    team.team_page()
    st.stop()

ui.top_bar()


def _enter(role):
    u = ui.me()
    if role == "seller":
        ui.go("seller_admin" if (u and u["role"] == "seller") else "seller_home")
    else:
        ui.go("visitor_home" if (u and u["role"] == "visitor") else "visitor_gate")


def landing():
    st.markdown("<p class='title'>HAW<span>-</span>ONE</p>", unsafe_allow_html=True)
    st.markdown(f"<p class='tagline'>{t('tagline')}</p>", unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="large")
    with c1:
        with st.container(key="card_blue_seller"):
            st.image(os.path.join(ui.ASSETS, "haw_bo.png"), width=230)
            st.markdown(f"<p class='role-name'>{t('seller')}</p><p class='role-desc'>{t('seller_desc')}</p>",
                        unsafe_allow_html=True)
            st.button(t("btn_seller"), key="b_seller", use_container_width=True, on_click=_enter, args=("seller",))
    with c2:
        with st.container(key="card_pink_visitor"):
            st.image(os.path.join(ui.ASSETS, "haw_sim.png"), width=230)
            st.markdown(f"<p class='role-name'>{t('visitor')}</p><p class='role-desc'>{t('visitor_desc')}</p>",
                        unsafe_allow_html=True)
            st.button(t("btn_visitor"), key="p_visitor", use_container_width=True, on_click=_enter, args=("visitor",))


VIEWS = {
    "landing": landing,
    # seller
    "seller_home": acc.seller_home, "seller_login": acc.seller_login, "seller_forgot": acc.seller_forgot,
    "seller_register_code": acc.seller_register_code, "seller_register_form": acc.seller_register_form,
    "seller_registered": acc.seller_registered, "seller_admin": sel.seller_admin,
    # visitor accounts
    "visitor_gate": acc.visitor_gate, "visitor_login": acc.visitor_login, "visitor_forgot": acc.visitor_forgot,
    "visitor_register_form": acc.visitor_register_form, "visitor_register_otp": acc.visitor_register_otp,
    "visitor_registered": acc.visitor_registered,
    # visitor pages
    "visitor_home": com.visitor_home, "v_fav": com.community_list, "v_channel": com.channel_page,
    "v_stall": com.stall_page, "v_post": com.post_page, "v_profile": com.profile_page, "v_feed": com.feed_page,
    "v_sched": haw.schedule_page, "v_near": haw.nearby_page,
}

VIEWS.get(ss["view"], landing)()

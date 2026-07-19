"""
NovaGrid Electronics - Admin Authentication
Simple username/password login gate for the Admin Dashboard panel.
Credentials are checked against the AdminUser table seeded in the DB.
Demo credentials: admin / novagrid@123
"""

import streamlit as st

from database.db_setup import get_session, AdminUser


def is_admin_logged_in():
    return st.session_state.get("admin_logged_in", False)


def login_form():
    st.markdown("### 🔐 Admin Login")
    st.caption("Demo credentials — Username: `admin`  |  Password: `novagrid@123`")
    with st.form("admin_login_form", clear_on_submit=False):
        username = st.text_input("Username", key="admin_username_input")
        password = st.text_input("Password", type="password", key="admin_password_input")
        submitted = st.form_submit_button("Login", use_container_width=True)

    if submitted:
        session = get_session()
        user = (session.query(AdminUser)
                .filter(AdminUser.username == username, AdminUser.password == password)
                .first())
        session.close()
        if user:
            st.session_state["admin_logged_in"] = True
            st.rerun()
        else:
            st.error("Invalid username or password. Please try again.")


def logout_button():
    if st.button("🚪 Logout", use_container_width=True, key="admin_logout_btn"):
        st.session_state["admin_logged_in"] = False
        st.rerun()

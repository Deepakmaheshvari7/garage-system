"""
Per-page role guards. Called at the top of every page file as defense-in-depth.
The sidebar nav is already role-filtered in main.py, but these guards ensure
a user who somehow deep-links to a page URL still gets blocked.
"""
import streamlit as st
import api_client as api


def require_login():
    if not api.is_authenticated():
        st.error("Please log in to continue.")
        st.stop()


def require_role(*allowed_roles: str):
    require_login()
    if st.session_state.get("role") not in allowed_roles:
        st.error("⛔ You don't have permission to view this page.")
        st.stop()


# Kept as no-op for any lingering calls in page files
def render_sidebar_account_info():
    pass

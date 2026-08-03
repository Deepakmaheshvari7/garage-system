"""
Thin wrapper around the FastAPI backend, used by all Streamlit pages.
Handles auth headers, consistent error display, and response caching
to avoid redundant API calls on every Streamlit rerun.
"""
import os

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def _headers() -> dict:
    token = st.session_state.get("access_token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def login(username: str, password: str) -> bool:
    try:
        resp = requests.post(
            f"{API_BASE_URL}/api/auth/login",
            data={"username": username, "password": password},
            timeout=10,
        )
    except requests.exceptions.RequestException as exc:
        st.error(f"Could not reach the server: {exc}")
        return False

    if resp.status_code == 200:
        data = resp.json()
        st.session_state["access_token"] = data["access_token"]
        st.session_state["role"] = data["role"]
        st.session_state["username"] = data["username"]
        st.session_state["user_id"] = data["user_id"]
        return True

    st.error(resp.json().get("detail", "Login failed"))
    return False


def logout():
    for key in ("access_token", "role", "username", "user_id"):
        st.session_state.pop(key, None)
    # Clear all cached data on logout so the next user gets fresh data
    get_cached.clear()


def is_authenticated() -> bool:
    return "access_token" in st.session_state


# ---------------------------------------------------------------------------
# Cached GET — for read-heavy endpoints that don't change every second.
# ttl=30 means data is re-fetched from the API at most once every 30 seconds.
# The cache is keyed on (path, token) so different users never share data.
# Call invalidate_cache() after any write operation to force a fresh fetch.
# ---------------------------------------------------------------------------
@st.cache_data(ttl=30, show_spinner=False)
def get_cached(path: str, token: str, params_key: str = ""):
    """
    Cached version of GET. Use for dashboard metrics, inventory list,
    job card list — anything that's read-only and can tolerate being
    30 seconds stale.

    Don't use this for anything that must reflect the latest state
    immediately after a write (use plain get() there instead, or call
    invalidate_cache() after your write).
    """
    resp = requests.get(
        f"{API_BASE_URL}{path}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    if resp.status_code >= 400:
        return None
    return resp.json()


def invalidate_cache():
    """Call this after any create/update/delete so the next read is fresh."""
    get_cached.clear()


def get(path: str, params: dict | None = None):
    """Uncached GET — use for data that must always be current."""
    resp = requests.get(
        f"{API_BASE_URL}{path}", headers=_headers(), params=params, timeout=15
    )
    return _handle(resp)


def get_fast(path: str, params: dict | None = None):
    """
    Cached GET — use for list/read endpoints on pages that load slowly.
    Falls back to uncached if not authenticated.
    """
    token = st.session_state.get("access_token", "")
    if not token:
        return get(path, params)
    params_key = str(sorted(params.items())) if params else ""
    return get_cached(path, token, params_key)


def post(path: str, json: dict | None = None, files=None, data=None):
    resp = requests.post(
        f"{API_BASE_URL}{path}",
        headers=_headers(),
        json=json,
        files=files,
        data=data,
        timeout=30,
    )
    result = _handle(resp)
    if result is not None:
        invalidate_cache()
    return result


def patch(path: str, json: dict | None = None):
    resp = requests.patch(
        f"{API_BASE_URL}{path}", headers=_headers(), json=json, timeout=15
    )
    result = _handle(resp)
    if result is not None:
        invalidate_cache()
    return result


def delete(path: str):
    resp = requests.delete(f"{API_BASE_URL}{path}", headers=_headers(), timeout=15)
    result = _handle(resp)
    if result is not None:
        invalidate_cache()
    return result


def get_raw(path: str, params: dict | None = None):
    """For binary responses like PDF downloads. Returns the raw response object."""
    return requests.get(
        f"{API_BASE_URL}{path}", headers=_headers(), params=params, timeout=30
    )


def get_quiet(path: str):
    """GET that returns (status_code, json_body) without showing any error.
    Used for lookups where 404 is an expected outcome, not a failure."""
    try:
        resp = requests.get(
            f"{API_BASE_URL}{path}", headers=_headers(), timeout=10
        )
    except requests.exceptions.RequestException:
        return None, None
    try:
        body = resp.json()
    except Exception:
        body = None
    return resp.status_code, body


def _handle(resp: requests.Response):
    if resp.status_code == 401:
        st.warning("Your session has expired. Please log in again.")
        logout()
        st.rerun()
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        st.error(f"Error: {detail}")
        return None
    if resp.status_code == 204:
        return True
    return resp.json()

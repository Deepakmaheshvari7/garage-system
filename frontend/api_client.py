"""
Thin wrapper around the FastAPI backend, used by all Streamlit pages.
Handles auth headers, consistent error display, refresh token rotation,
native URL query params session persistence, and response caching.
"""
import os
import time
from typing import Callable, Optional

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Default time-to-live (seconds) for cached GETs.
_CACHE_TTL = 30
_fast_cache: dict[tuple[str, str, str], tuple[float, object]] = {}


def init_session() -> bool:
    """
    Restores session from st.query_params if st.session_state is empty.
    Uses the secure refresh_token to obtain a valid access token.
    """
    if "access_token" in st.session_state:
        return True

    # Check if a refresh token was persisted in st.query_params
    refresh_token = st.query_params.get("auth")
    if refresh_token:
        try:
            resp = requests.post(
                f"{API_BASE_URL}/api/auth/refresh",
                json={"refresh_token": refresh_token},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                st.session_state["access_token"] = data["access_token"]
                st.session_state["refresh_token"] = data.get("refresh_token") or refresh_token
                st.session_state["role"] = data["role"]
                st.session_state["username"] = data["username"]
                st.session_state["user_id"] = data["user_id"]
                return True
            else:
                # Token expired or invalid, clear query params
                st.query_params.clear()
        except requests.exceptions.RequestException:
            pass

    return False


def _cache_key(path: str, params: dict | None) -> tuple[str, str, str]:
    token = st.session_state.get("access_token", "")
    if params:
        params_key = str(sorted(params.items()))
    else:
        params_key = ""
    return token, path, params_key


def _headers() -> dict:
    token = st.session_state.get("access_token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def refresh_access_token() -> bool:
    """Attempt to obtain a new access token using the stored refresh token."""
    refresh_token = st.session_state.get("refresh_token") or st.query_params.get("auth")
    if not refresh_token:
        return False
    try:
        resp = requests.post(
            f"{API_BASE_URL}/api/auth/refresh",
            json={"refresh_token": refresh_token},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            st.session_state["access_token"] = data["access_token"]
            st.session_state["role"] = data["role"]
            st.session_state["username"] = data["username"]
            st.session_state["user_id"] = data["user_id"]
            if data.get("refresh_token"):
                st.session_state["refresh_token"] = data["refresh_token"]
                st.query_params["auth"] = data["refresh_token"]
            return True
    except requests.exceptions.RequestException:
        pass
    return False


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
        st.session_state["refresh_token"] = data.get("refresh_token")
        st.session_state["role"] = data["role"]
        st.session_state["username"] = data["username"]
        st.session_state["user_id"] = data["user_id"]

        # Persist session refresh token in query params for seamless reload
        if data.get("refresh_token"):
            st.query_params["auth"] = data["refresh_token"]
        return True

    st.error(resp.json().get("detail", "Login failed"))
    return False


def logout():
    for key in ("access_token", "refresh_token", "role", "username", "user_id"):
        st.session_state.pop(key, None)
    # Clear cache and URL query params
    _fast_cache.clear()
    st.query_params.clear()


def is_authenticated() -> bool:
    if "access_token" in st.session_state:
        return True
    return init_session()


def _handle(resp: requests.Response, retry_fn: Optional[Callable[[], requests.Response]] = None):
    if resp.status_code == 401:
        # Attempt auto-refresh using refresh_token if available
        if refresh_access_token():
            if retry_fn:
                try:
                    new_resp = retry_fn()
                    return _handle(new_resp, retry_fn=None)
                except requests.exceptions.RequestException:
                    pass
            st.rerun()
            return None
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


def get(path: str, params: dict | None = None):
    """Uncached GET — use for data that must always be current."""
    def _do():
        return requests.get(
            f"{API_BASE_URL}{path}", headers=_headers(), params=params, timeout=15
        )
    try:
        resp = _do()
        return _handle(resp, retry_fn=_do)
    except requests.exceptions.RequestException as exc:
        st.error(f"Could not reach the server: {exc}")
        return None


def get_fast(path: str, params: dict | None = None):
    """
    Cached GET for list/read endpoints. Serves from cache when fresh (within
    _CACHE_TTL seconds) or after a write to a different path. Falls back to an
    uncached get() if the user isn't authenticated.
    """
    if not st.session_state.get("access_token"):
        return get(path, params)

    key = _cache_key(path, params)
    now = time.monotonic()
    entry = _fast_cache.get(key)
    if entry is not None:
        ts, value = entry
        if now - ts < _CACHE_TTL:
            return value

    def _do():
        return requests.get(
            f"{API_BASE_URL}{path}", headers=_headers(), params=params, timeout=15
        )

    try:
        resp = _do()
    except requests.exceptions.RequestException as exc:
        st.error(f"Could not reach the server: {exc}")
        return None

    if resp.status_code == 401:
        if refresh_access_token():
            try:
                resp = _do()
            except requests.exceptions.RequestException:
                return None
        else:
            _fast_cache[key] = (now, None)
            _handle(resp)
            return None

    if resp.status_code >= 400:
        _fast_cache[key] = (now, None)
        _handle(resp)
        return None

    try:
        value = resp.json()
    except Exception:
        value = None

    _fast_cache[key] = (now, value)
    return value


def invalidate_cache(*prefixes: str):
    """Drop cached GET entries so the next read is fresh."""
    if not prefixes:
        _fast_cache.clear()
        return
    stale = [k for k in _fast_cache if any(k[1].startswith(p) for p in prefixes)]
    for k in stale:
        _fast_cache.pop(k, None)


def _cache_prefixes_for_write(path: str) -> tuple[str, ...] | None:
    if path.startswith("/api/jobcards"):
        prefixes = ["/api/jobcards", "/api/dashboard"]
        if "/parts" in path:
            prefixes.append("/api/inventory")
        return tuple(prefixes)
    if path.startswith("/api/inventory"):
        return "/api/inventory", "/api/dashboard"
    if path.startswith("/api/billing"):
        return "/api/jobcards", "/api/dashboard"
    return None


def _invalidate_after_write(path: str):
    prefixes = _cache_prefixes_for_write(path)
    if prefixes is None:
        invalidate_cache()
    else:
        invalidate_cache(*prefixes)


def post(path: str, json: dict | None = None, files=None, data=None):
    def _do():
        return requests.post(
            f"{API_BASE_URL}{path}",
            headers=_headers(),
            json=json,
            files=files,
            data=data,
            timeout=30,
        )
    try:
        resp = _do()
        result = _handle(resp, retry_fn=_do)
        if result is not None:
            _invalidate_after_write(path)
        return result
    except requests.exceptions.RequestException as exc:
        st.error(f"Could not reach the server: {exc}")
        return None


def patch(path: str, json: dict | None = None):
    def _do():
        return requests.patch(
            f"{API_BASE_URL}{path}", headers=_headers(), json=json, timeout=15
        )
    try:
        resp = _do()
        result = _handle(resp, retry_fn=_do)
        if result is not None:
            _invalidate_after_write(path)
        return result
    except requests.exceptions.RequestException as exc:
        st.error(f"Could not reach the server: {exc}")
        return None


def delete(path: str):
    def _do():
        return requests.delete(f"{API_BASE_URL}{path}", headers=_headers(), timeout=15)
    try:
        resp = _do()
        result = _handle(resp, retry_fn=_do)
        if result is not None:
            _invalidate_after_write(path)
        return result
    except requests.exceptions.RequestException as exc:
        st.error(f"Could not reach the server: {exc}")
        return None


def get_raw(path: str, params: dict | None = None):
    """For binary responses like PDF downloads. Returns the raw response object."""
    def _do():
        return requests.get(
            f"{API_BASE_URL}{path}", headers=_headers(), params=params, timeout=30
        )
    try:
        resp = _do()
        if resp.status_code == 401 and refresh_access_token():
            resp = _do()
        return resp
    except requests.exceptions.RequestException as exc:
        st.error(f"Could not reach the server: {exc}")
        return None


def get_quiet(path: str):
    """GET that returns (status_code, json_body) without showing any error."""
    try:
        resp = requests.get(
            f"{API_BASE_URL}{path}", headers=_headers(), timeout=10
        )
        if resp.status_code == 401 and refresh_access_token():
            resp = requests.get(
                f"{API_BASE_URL}{path}", headers=_headers(), timeout=10
            )
        try:
            body = resp.json()
        except Exception:
            body = None
        return resp.status_code, body
    except requests.exceptions.RequestException:
        return None, None

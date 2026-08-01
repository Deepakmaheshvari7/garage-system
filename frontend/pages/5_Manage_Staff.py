import streamlit as st

import api_client as api
from auth_guard import require_role

require_role("Admin")

st.title("Manage Staff")

# ── Add new staff member ───────────────────────────────────────────────────────
with st.expander("Add New Staff Member"):
    with st.form("add_staff_form", clear_on_submit=True):
        s1, s2 = st.columns(2)
        new_username = s1.text_input("Username", placeholder="e.g. rajesh_desk")
        new_role = s2.selectbox("Role", ["Mechanic", "Desk", "Admin"])
        s3, s4 = st.columns(2)
        new_password = s3.text_input("Password", type="password")
        confirm_password = s4.text_input("Confirm Password", type="password")
        submitted = st.form_submit_button("Create Account", type="primary",
                                          use_container_width=True)

    if submitted:
        errors = []
        if not new_username.strip():
            errors.append("Username is required.")
        if len(new_password) < 6:
            errors.append("Password must be at least 6 characters.")
        if new_password != confirm_password:
            errors.append("Passwords do not match.")
        if errors:
            for e in errors:
                st.warning(e)
        else:
            result = api.post("/api/auth/register", json={
                "username": new_username.strip(),
                "password": new_password,
                "role": new_role,
            })
            if result:
                st.success(f"Account created for **{new_username}** ({new_role}).")
                api.invalidate_cache()
                st.rerun()

st.divider()

# ── Staff list ─────────────────────────────────────────────────────────────────
staff = api.get("/api/users") or []

if not staff:
    st.info("No staff accounts found.")
    st.stop()

current_user_id = st.session_state.get("user_id")

ROLE_ICON = {"Admin": "🔑", "Desk": "🖥️", "Mechanic": "🔧"}

for member in staff:
    uid = member["user_id"]
    icon = ROLE_ICON.get(member["role"], "👤")
    is_self = uid == current_user_id

    col1, col2, col3 = st.columns([3, 1, 2])

    with col1:
        st.markdown(f"**{icon} {member['username']}**")
        st.caption(f"{member['role']}  ·  ID #{uid}"
                   + ("  (you)" if is_self else ""))

    with col2:
        if not is_self:
            if st.button("Remove", key=f"del_{uid}",
                         help="Delete this staff account"):
                st.session_state[f"confirm_delete_{uid}"] = True

        if st.session_state.get(f"confirm_delete_{uid}"):
            st.warning(f"Delete **{member['username']}**?")
            d1, d2 = st.columns(2)
            if d1.button("Yes, delete", key=f"yes_del_{uid}", type="primary"):
                if api.delete(f"/api/users/{uid}"):
                    st.success(f"Deleted {member['username']}.")
                    st.session_state.pop(f"confirm_delete_{uid}", None)
                    api.invalidate_cache()
                    st.rerun()
            if d2.button("Cancel", key=f"no_del_{uid}"):
                st.session_state.pop(f"confirm_delete_{uid}", None)
                st.rerun()

    with col3:
        with st.popover("Reset Password", use_container_width=True):
            with st.form(f"reset_pw_{uid}"):
                new_pw = st.text_input("New Password", type="password",
                                       key=f"npw_{uid}")
                if st.form_submit_button("Reset", type="primary",
                                         use_container_width=True):
                    if len(new_pw) < 6:
                        st.error("Min 6 characters.")
                    else:
                        result = api.patch(
                            f"/api/users/{uid}/password",
                            json={"new_password": new_pw}
                        )
                        if result:
                            st.success("Password updated!")

    st.divider()

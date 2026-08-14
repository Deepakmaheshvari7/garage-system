import streamlit as st
import api_client as api
from auth_guard import require_role

require_role("Admin", "Desk")

st.title("Job Cards")

left, right = st.columns([1, 2], gap="large")

# ── LEFT: Job list ─────────────────────────────────────────────────────────────
with left:
    def _reset_job_page():
        st.session_state["jobcards_page"] = 1

    status_filter = st.selectbox(
        "Filter", ["All", "Open", "In-Progress", "Ready_For_Billing", "Completed"],
        label_visibility="collapsed",
        key="jobcards_status_filter",
        on_change=_reset_job_page,
    )
    page = st.session_state.get("jobcards_page", 1)
    page_size = st.session_state.get("jobcards_page_size", 25)
    list_params = {"page": page, "page_size": page_size}
    if status_filter != "All":
        list_params["status"] = status_filter
    jobs_payload = api.get_fast("/api/jobcards", params=list_params) or {}
    jobs = jobs_payload.get("items", []) if isinstance(jobs_payload, dict) else jobs_payload or []

    if isinstance(jobs_payload, dict):
        total_pages = jobs_payload.get("total_pages", 1)
        total_jobs = jobs_payload.get("total", 0)
        st.caption(f"Page {page} of {total_pages} — {total_jobs} total jobs")
        nav = st.columns([1, 1])
        if nav[0].button("← Prev", disabled=page <= 1):
            st.session_state["jobcards_page"] = max(1, page - 1)
            st.rerun()
        if nav[1].button("Next →", disabled=page >= total_pages):
            st.session_state["jobcards_page"] = min(total_pages, page + 1)
            st.rerun()

    STATUS_ICON = {"Open": "🟡", "In-Progress": "🔵",
                   "Ready_For_Billing": "🟠", "Completed": "🟢"}
    for j in jobs:
        label = f"{STATUS_ICON.get(j['status'], '⚪')} #{j['job_id']} — {j['vehicle_reg']}"
        if j.get("customer_name"):
            label += f"\n{j['customer_name']}"
        if st.button(label, key=f"job_{j['job_id']}", use_container_width=True):
            st.session_state["selected_job_id"] = j["job_id"]
            st.rerun()

    with st.expander("New Job Card"):
        mechanics = api.get("/api/users", params={"role": "Mechanic"}) or []
        mech_opts = {"— Unassigned —": None}
        mech_opts.update({m["username"]: m["user_id"] for m in mechanics})

        with st.form("create_job_form", clear_on_submit=True):
            cust_name  = st.text_input("Customer Name")
            cust_phone = st.text_input("Phone Number")
            vehicle_reg = st.text_input("Vehicle Reg. No. *", placeholder="MP09AB1234")
            mech_label  = st.selectbox("Assign Mechanic", list(mech_opts.keys()))
            labor_charge = st.number_input("Labour Charge (₹)", min_value=0.0,
                                           value=0.0, step=50.0)
            create_btn = st.form_submit_button("Create Job", type="primary",
                                               use_container_width=True)

        if create_btn:
            if not vehicle_reg.strip():
                st.warning("Vehicle Reg. is required.")
            else:
                chosen_mech_id = mech_opts[mech_label]

                # Re-fetch the mechanic list right before submitting so a
                # mechanic deleted since page-load is caught here with a clean
                # message instead of a DB FK violation on the backend.
                if chosen_mech_id is not None:
                    fresh = api.get("/api/users", params={"role": "Mechanic"}) or []
                    valid_ids = {m["user_id"] for m in fresh}
                    if chosen_mech_id not in valid_ids:
                        st.error(
                            f"Mechanic '{mech_label}' is no longer available. "
                            "The list has been refreshed — please pick again."
                        )
                        st.rerun()

                res = api.post("/api/jobcards", json={
                    "customer_name":  cust_name.strip() or None,
                    "customer_phone": cust_phone.strip() or None,
                    "vehicle_reg":    vehicle_reg.strip().upper(),
                    "mechanic_id":    chosen_mech_id,
                    "labor_charge":   float(labor_charge),
                })
                # Only treat as success when we actually got a job_id back.
                # api.post returns None on error (and already showed st.error),
                # so guard against both None and a malformed/truthy body.
                if isinstance(res, dict) and res.get("job_id"):
                    st.session_state["selected_job_id"] = res["job_id"]
                    st.success(f"Job #{res['job_id']} created!")
                    st.rerun()

# ── RIGHT: Job workbench ──────────────────────────────────────────────────────
with right:
    selected_id = st.session_state.get("selected_job_id")
    if not selected_id:
        st.info("Select a job from the list, or create a new one.")
        st.stop()

    job = api.get(f"/api/jobcards/{selected_id}")
    if not job:
        st.error("Job not found.")
        st.stop()

    is_done = job["status"] == "Completed"

    STATUS_BADGE = {"Open": "🟡 Open", "In-Progress": "🔵 In Progress",
                    "Ready_For_Billing": "🟠 Ready for Billing", "Completed": "🟢 Completed"}

    h1, h2 = st.columns([2, 1])
    with h1:
        st.subheader(f"Job #{job['job_id']} — {job['vehicle_reg']}")
        st.caption(f"Customer: {job.get('customer_name') or '—'}  ·  "
                   f"📞 {job.get('customer_phone') or '—'}  ·  "
                   f"Mechanic: {job.get('mechanic_name') or 'Unassigned'}")
    with h2:
        st.markdown(f"#### {STATUS_BADGE.get(job['status'], job['status'])}")

    st.divider()

    if not is_done:
        # ── Add Part (server-side catalog search) ───────────────────────────
        st.markdown("**Add Part**")
        part_search = st.text_input(
            "Find a part",
            placeholder="Search by name, part no., brand, model or category…",
            key=f"part_search_{job['job_id']}",
            label_visibility="collapsed",
        ).strip()

        def _part_label(i):
            lbl = i["name"]
            if i.get("part_number"):
                lbl += f" [{i['part_number']}]"
            if i.get("brand"):
                lbl += f" — {i['brand']}"
            if i.get("bike_model"):
                lbl += f" ({i['bike_model']})"
            lbl += f"  ·  stock: {i['stock_quantity']}  ·  #{i['part_id']}"
            return lbl

        if len(part_search) < 2:
            st.caption("Type at least 2 characters to search the full inventory catalog.")
        else:
            inv_payload = api.get_fast(
                "/api/inventory",
                params={
                    "page": 1,
                    "page_size": 50,
                    "search": part_search,
                    "in_stock_only": True,
                },
            ) or {}
            inventory = inv_payload.get("items", []) if isinstance(inv_payload, dict) else inv_payload
            part_opts = {_part_label(i): i for i in inventory}
            total_matches = inv_payload.get("total", len(inventory)) if isinstance(inv_payload, dict) else len(inventory)
            if total_matches:
                st.caption(f"{total_matches} in-stock match(es)" + (" — showing the first 50." if total_matches > 50 else "."))

        if len(part_search) >= 2 and part_opts:
            p1, p2, p3 = st.columns([3, 1, 1])
            sel_lbl  = p1.selectbox(
                "Part", list(part_opts.keys()),
                                index=None,
                placeholder="Type to search — name, part no., brand or model…",
                label_visibility="collapsed",
                key=f"part_pick_{job['job_id']}",
            )
            sel_part = part_opts.get(sel_lbl) if sel_lbl else None
            max_qty  = max(1, sel_part["stock_quantity"]) if sel_part else 1
            qty      = p2.number_input(
                "Qty", min_value=1, max_value=max_qty, value=1, step=1,
                label_visibility="collapsed",
                key=f"part_qty_{job['job_id']}",
                disabled=(sel_part is None),
                help=f"Up to {max_qty} in stock" if sel_part else "Select a part first",
            )
            add_ok   = p3.button("Add", use_container_width=True,
                                 disabled=(sel_part is None),
                                 key=f"part_add_{job['job_id']}")
            if add_ok and sel_part:
                res = api.post(f"/api/jobcards/{job['job_id']}/parts",
                               json={"part_id": sel_part["part_id"],
                                     "quantity_used": int(qty)})
                if res:
                    st.success(f"Added {qty} × {sel_part['name']}")
                    st.rerun()
        elif len(part_search) >= 2:
            st.info("No in-stock parts match that search.")

        # Labour charge
        st.markdown("**Labour Charge**")
        l1, l2 = st.columns([2, 1])
        new_charge = l1.number_input(
            "Labour (₹)", min_value=0.0,
            value=float(job["labor_charge"]),
            step=50.0, format="%.0f",
            label_visibility="collapsed",
            help="Enter the total labour charge for this job"
        )
        if l2.button("Update", use_container_width=True):
            if api.patch(f"/api/jobcards/{job['job_id']}/labor",
                         json={"labor_charge": new_charge}):
                st.success("Labour charge updated.")
                st.rerun()

        st.divider()

    # Parts used — with inline quantity stepper (no delete/re-add needed)
    st.markdown("**Parts Used**")
    if job["parts_used"]:
        for p in job["parts_used"]:
            # Flat single-level columns — Streamlit forbids nesting columns
            # inside columns, so the − / qty / + stepper gets its own columns
            # at the top level instead of a sub-column block.
            if not is_done:
                c1, cm, cv, cp, c3, c4, c5 = st.columns([3, 1, 1, 1, 1, 1, 1])
            else:
                c1, cv, c3, c4, c5 = st.columns([3, 2, 1, 1, 1])
            c1.write(f"**{p['part_name']}**")

            if not is_done:
                # Inline qty editor: − / qty / + updates stock by the delta.
                if cm.button("−", key=f"dec_{p['mapping_id']}",
                             help="Decrease quantity",
                             disabled=(p["quantity_used"] <= 1)):
                    if api.patch(f"/api/jobcards/{job['job_id']}/parts/{p['mapping_id']}",
                                 json={"quantity_used": p["quantity_used"] - 1}):
                        st.rerun()
                cv.markdown(f"<div style='text-align:center'>×{p['quantity_used']}</div>",
                            unsafe_allow_html=True)
                if cp.button("+", key=f"inc_{p['mapping_id']}",
                             help="Increase quantity"):
                    if api.patch(f"/api/jobcards/{job['job_id']}/parts/{p['mapping_id']}",
                                 json={"quantity_used": p["quantity_used"] + 1}):
                        st.rerun()
            else:
                cv.write(f"×{p['quantity_used']}")

            c3.write(f"₹{p['selling_price']:.0f}")
            c4.write(f"**₹{p['line_total']:.0f}**")
            if not is_done:
                if c5.button("✕", key=f"rm_{p['mapping_id']}",
                             help="Remove & restore stock"):
                    if api.delete(f"/api/jobcards/{job['job_id']}/parts/{p['mapping_id']}"):
                        st.rerun()
    else:
        st.caption("No parts added yet.")

    # Running total
    st.divider()
    t1, t2, t3 = st.columns(3)
    t1.metric("Parts Total",    f"₹{job['parts_total']:,.0f}")
    t2.metric("Labour Charge",  f"₹{job['labor_charge']:,.0f}")
    t3.metric("Grand Total",    f"₹{job['grand_total']:,.0f}")

    st.divider()

    if not is_done:
        st.markdown("**Update Status**")
        opts = ["Open", "In-Progress", "Ready_For_Billing", "Completed"]
        s1, s2 = st.columns([2, 1])
        new_status = s1.selectbox("Status", opts, index=opts.index(job["status"]),
                                  label_visibility="collapsed")
        if s2.button("Update Status", use_container_width=True, type="primary"):
            if api.patch(f"/api/jobcards/{job['job_id']}/status",
                         json={"status": new_status}):
                st.success(f"Status → {new_status}")
                st.rerun()
    else:
        st.success("Job completed. Go to **Billing** to generate the invoice.")

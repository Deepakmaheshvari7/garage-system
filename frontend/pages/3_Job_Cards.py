import streamlit as st
import api_client as api
from auth_guard import require_role

require_role("Admin", "Desk")

st.title("🛠️ Job Cards")

left, right = st.columns([1, 2], gap="large")

# ── LEFT: Job list ─────────────────────────────────────────────────────────────
with left:
    st.subheader("All Jobs")
    status_filter = st.selectbox(
        "Filter", ["All", "Open", "In-Progress", "Ready_For_Billing", "Completed"],
        label_visibility="collapsed"
    )
    jobs = api.get_fast("/api/jobcards") or []
    if status_filter != "All":
        jobs = [j for j in jobs if j["status"] == status_filter]

    STATUS_ICON = {"Open": "🟡", "In-Progress": "🔵",
                   "Ready_For_Billing": "🟠", "Completed": "🟢"}
    for j in jobs:
        label = f"{STATUS_ICON.get(j['status'], '⚪')} #{j['job_id']} — {j['vehicle_reg']}"
        if j.get("customer_name"):
            label += f"\n{j['customer_name']}"
        if st.button(label, key=f"job_{j['job_id']}", use_container_width=True):
            st.session_state["selected_job_id"] = j["job_id"]
            st.rerun()

    st.divider()

    with st.expander("➕ New Job Card"):
        mechanics = api.get("/api/users", params={"role": "Mechanic"}) or []
        mech_opts = {"— Unassigned —": None}
        mech_opts.update({m["username"]: m["user_id"] for m in mechanics})

        with st.form("create_job_form", clear_on_submit=True):
            st.markdown("**Customer**")
            cust_name  = st.text_input("Customer Name")
            cust_phone = st.text_input("Phone Number")
            st.markdown("**Vehicle**")
            vehicle_reg = st.text_input("Vehicle Reg. No. *", placeholder="MP09AB1234")
            mech_label  = st.selectbox("Assign Mechanic", list(mech_opts.keys()))
            st.markdown("**Labour Charge (₹)**")
            labor_charge = st.number_input("Labour Charge", min_value=0.0,
                                           value=0.0, step=50.0,
                                           label_visibility="collapsed")
            create_btn = st.form_submit_button("Create Job", type="primary",
                                               use_container_width=True)

        if create_btn:
            if not vehicle_reg.strip():
                st.warning("Vehicle Reg. is required.")
            else:
                res = api.post("/api/jobcards", json={
                    "customer_name":  cust_name.strip() or None,
                    "customer_phone": cust_phone.strip() or None,
                    "vehicle_reg":    vehicle_reg.strip().upper(),
                    "mechanic_id":    mech_opts[mech_label],
                    "labor_charge":   float(labor_charge),
                })
                if res:
                    st.session_state["selected_job_id"] = res["job_id"]
                    st.success(f"Job #{res['job_id']} created!")
                    st.rerun()

# ── RIGHT: Job workbench ──────────────────────────────────────────────────────
with right:
    selected_id = st.session_state.get("selected_job_id")
    if not selected_id:
        st.markdown("""
            <div style='text-align:center;padding:80px 0;color:#64748B;'>
                <div style='font-size:48px;'>🛠️</div>
                <div style='font-size:15px;margin-top:12px;'>
                    Select a job or create a new one.
                </div>
            </div>
        """, unsafe_allow_html=True)
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
        st.markdown(f"### Job #{job['job_id']} — {job['vehicle_reg']}")
        st.markdown(f"**Customer:** {job.get('customer_name') or '—'} "
                    f"&nbsp; 📞 {job.get('customer_phone') or '—'}")
        st.markdown(f"**Mechanic:** {job.get('mechanic_name') or 'Unassigned'}")
    with h2:
        st.markdown("**Status**")
        st.markdown(f"### {STATUS_BADGE.get(job['status'], job['status'])}")

    st.divider()

    if not is_done:
        # Add part
        st.subheader("➕ Add Part")
        inventory = api.get_fast("/api/inventory") or []
        search = st.text_input("Search by name or part number", key="part_search",
                               label_visibility="collapsed",
                               placeholder="Type to search parts...")
        filtered = [i for i in inventory
                    if search.lower() in i["name"].lower()
                    or search.lower() in (i.get("part_number") or "").lower()
                    ] if search else inventory

        in_stock  = [i for i in filtered if i["stock_quantity"] > 0]
        out_stock = [i for i in filtered if i["stock_quantity"] == 0]
        part_opts = {
            f"{i['name']}"
            + (f" [{i['part_number']}]" if i.get("part_number") else "")
            + (f" — {i.get('brand','')}" if i.get("brand") else "")
            + f"  (stock: {i['stock_quantity']})": i
            for i in (in_stock + out_stock)
        }

        if part_opts:
            p1, p2, p3 = st.columns([3, 1, 1])
            sel_lbl  = p1.selectbox("Part", list(part_opts.keys()),
                                    label_visibility="collapsed")
            sel_part = part_opts[sel_lbl]
            qty      = p2.number_input("Qty", min_value=1, value=1, step=1,
                                       label_visibility="collapsed")
            add_ok   = p3.button("Add ➕", use_container_width=True,
                                 disabled=(sel_part["stock_quantity"] == 0))
            if sel_part["stock_quantity"] == 0:
                st.warning(f"⚠️ '{sel_part['name']}' is out of stock.")
            if add_ok:
                res = api.post(f"/api/jobcards/{job['job_id']}/parts",
                               json={"part_id": sel_part["part_id"],
                                     "quantity_used": int(qty)})
                if res:
                    st.success(f"Added {qty} × {sel_part['name']}")
                    st.rerun()

        st.divider()

        # Labour charge
        st.subheader("💰 Labour Charge")
        l1, l2 = st.columns([2, 1])
        new_charge = l1.number_input(
            "Labour (₹)", min_value=0.0,
            value=float(job["labor_charge"]),
            step=50.0, format="%.0f",
            label_visibility="collapsed",
            help="Enter the total labour charge for this job"
        )
        if l2.button("Update ✔️", use_container_width=True):
            if api.patch(f"/api/jobcards/{job['job_id']}/labor",
                         json={"labor_charge": new_charge}):
                st.success("Labour charge updated.")
                st.rerun()

        st.divider()

    # Parts used
    st.subheader("📋 Parts Used")
    if job["parts_used"]:
        for p in job["parts_used"]:
            c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1])
            c1.write(f"**{p['part_name']}**")
            c2.write(f"×{p['quantity_used']}")
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
    t3.metric("💰 Grand Total", f"₹{job['grand_total']:,.0f}")

    st.divider()

    if not is_done:
        st.subheader("📌 Update Status")
        opts = ["Open", "In-Progress", "Ready_For_Billing", "Completed"]
        s1, s2 = st.columns([2, 1])
        new_status = s1.selectbox("Status", opts, index=opts.index(job["status"]),
                                  label_visibility="collapsed")
        if s2.button("Update ✅", use_container_width=True, type="primary"):
            if api.patch(f"/api/jobcards/{job['job_id']}/status",
                         json={"status": new_status}):
                st.success(f"Status → {new_status}")
                st.rerun()
    else:
        st.success("✅ Job completed. Go to **Billing** to generate the invoice.")

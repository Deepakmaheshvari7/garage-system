import streamlit as st
import pandas as pd
import api_client as api
from auth_guard import require_role

require_role("Admin", "Desk")

st.title("Billing")

# /api/jobcards returns a paginated envelope: {"items": [...], "total": N, ...}.
# Pull a large page so all billable jobs are available, then read .items.
jobs_payload = api.get_fast("/api/jobcards", params={"page": 1, "page_size": 200}) or {}
jobs = jobs_payload.get("items", []) if isinstance(jobs_payload, dict) else jobs_payload
billable = [j for j in jobs if j["status"] in ("Ready_For_Billing", "Completed")]

if not billable:
    st.info("No jobs are ready for billing yet. "
            "Mark a job as 'Ready for Billing' from the Job Cards page first.")
    st.stop()

STATUS_BADGE = {"Ready_For_Billing": "🟠 Ready for Billing", "Completed": "🟢 Completed"}
job_labels = {
    f"#{j['job_id']} — {j['vehicle_reg']}  ({STATUS_BADGE.get(j['status'], j['status'])})": j
    for j in billable
}
selected_label = st.selectbox("Select Job", list(job_labels.keys()))
job = job_labels[selected_label]

st.divider()

# Always fresh for billing
preview = api.get(f"/api/billing/jobcards/{job['job_id']}/preview")
if not preview:
    st.stop()

# Customer & Vehicle
c1, c2 = st.columns(2)
with c1:
    st.markdown("**Customer**")
    st.write(preview['customer_name'])
    st.caption(f"📞 {preview['customer_phone']}")
with c2:
    st.markdown("**Vehicle**")
    st.write(preview['vehicle_reg'])
    st.caption(f"Mechanic: {preview['mechanic_name']}")

st.divider()

# Line items
st.markdown("**Parts & Labour**")
rows = []
for p in preview["parts"]:
    rows.append({
        "Description": p["name"],
        "Qty":         p["quantity"],
        "Rate (₹)":    p["unit_price"],
        "Amount (₹)":  p["line_total"],
    })

labor = float(preview.get("labor_charge", 0))
if labor > 0:
    rows.append({
        "Description": "Labour Charges",
        "Qty":         "—",
        "Rate (₹)":    "—",
        "Amount (₹)":  f"{labor:.2f}",
    })

if rows:
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
else:
    st.caption("No parts or labour recorded.")

st.divider()

# Totals
t1, t2 = st.columns(2)
t1.metric("Parts Total",   f"₹{preview['parts_subtotal']}")
t2.metric("Grand Total",   f"₹{preview['grand_total']}")
if labor > 0:
    st.caption(f"Labour charge: ₹{labor:.2f}")

st.divider()

if st.button("Generate PDF Invoice", type="primary", use_container_width=True):
    with st.spinner("Generating invoice..."):
        resp = api.get_raw(f"/api/billing/jobcards/{job['job_id']}/invoice")
    if resp.status_code == 200:
        api.invalidate_cache()
        st.download_button(
            label="⬇️ Download Invoice PDF",
            data=resp.content,
            file_name=f"invoice_SPM_job_{job['job_id']}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
        st.success("Invoice generated. Job marked Completed.")
    else:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        st.error(f"Could not generate invoice: {detail}")

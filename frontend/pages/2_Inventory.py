import io

import pandas as pd
import streamlit as st

import api_client as api
from auth_guard import require_login, render_sidebar_account_info

require_login()
render_sidebar_account_info()

st.title("Inventory")

role = st.session_state["role"]
is_admin = role == "Admin"

# --- Bulk import (Admin & Desk) ---
if role in ("Admin", "Desk"):
    with st.expander("Bulk import from supplier catalog (.xlsx / .csv)"):
        # Downloadable blank template with the exact column order the importer expects
        TEMPLATE_COLS = ["part_number", "name", "category", "brand", "bike_model",
                         "stock_quantity", "min_threshold", "cost_price", "selling_price"]
        template_df = pd.DataFrame(columns=TEMPLATE_COLS)
        try:
            buf = io.BytesIO()
            template_df.to_excel(buf, index=False, engine="openpyxl")
            st.download_button(
                "📥 Download blank template (.xlsx)",
                data=buf.getvalue(),
                file_name="inventory_template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except ImportError:
            # openpyxl not installed — fall back to CSV (opens fine in Excel)
            st.download_button(
                "📥 Download blank template (.csv)",
                data=template_df.to_csv(index=False),
                file_name="inventory_template.csv",
                mime="text/csv",
            )
        st.caption(
            "Fill in the template and upload it below. "
            "**Required:** name, selling_price. "
            "**part_number** must be unique — duplicates are skipped. "
            "cost_price is optional (Admin-only)."
        )
        uploaded = st.file_uploader("Choose a file", type=["xlsx", "xls", "csv"])
        if uploaded is not None and st.button("Import"):
            files = {"file": (uploaded.name, uploaded.getvalue())}
            result = api.post("/api/inventory/upload", files=files)
            if result:
                st.success(f"Imported {result['inserted']} parts.")
                if result["errors"]:
                    st.warning(f"{len(result['skipped_rows'])} row(s) skipped:")
                    for err in result["errors"]:
                        st.text(err)
                st.rerun()

# --- Add a single new part (Admin only) ---
CATEGORIES = ["Engine", "Body", "Electrical", "Consumable", "Transmission", "Accessories"]
BRANDS = ["Bajaj", "TVS", "Hero", "Honda", "Royal Enfield", "Suzuki", "Yamaha", "Universal"]


if is_admin:
    # ── Real-time Part Number check — always visible, fires on blur/Enter ──
    pn_input = st.text_input(
        "Part Number", placeholder="e.g. BJ-ENG-0042",
        key="pn_lookup",
        help="Type a Part Number and press Enter / click away. If it already "
             "exists you'll get an Edit button; if not, the Add Part form opens.",
    )
    pn = pn_input.strip()
    existing_part = None
    if pn:
        status, body = api.get_quiet(f"/api/inventory/by-part-number/{pn}")
        if status == 200 and body:
            existing_part = body

    if existing_part:
        st.warning(
            f"⚠️ Part Number **{pn}** already exists: **{existing_part['name']}** "
            f"(stock: {existing_part['stock_quantity']}). "
            "A duplicate will not be created."
        )
        if st.button("✏️ Edit Part", type="primary", key="edit_from_lookup"):
            st.session_state["edit_part"] = existing_part
    elif pn:
        st.success(f"✅ Part Number **{pn}** is available — fill in the rest below.")

    # ── Edit panel (replaces the add form when a part is being edited) ──
    editing = st.session_state.get("edit_part")
    if editing:
        st.subheader(f"Edit Part — {editing['name']}")
        with st.form("edit_part_form"):
            c1, c2 = st.columns(2)
            e_pn = c1.text_input("Part Number", value=editing.get("part_number") or "")
            e_name = c2.text_input("Part Name *", value=editing.get("name") or "")
            c3, c4 = st.columns(2)
            cur_cat = editing.get("category")
            e_category = c3.selectbox(
                "Category *", CATEGORIES,
                index=CATEGORIES.index(cur_cat) if cur_cat in CATEGORIES else 0,
            )
            e_min = c4.number_input("Min Stock Alert", min_value=0, step=1,
                                    value=int(editing.get("min_threshold") or 5))
            c5, c6 = st.columns(2)
            cur_brand = editing.get("brand")
            e_brand = c5.selectbox(
                "Brand", ["— Select —"] + BRANDS,
                index=(BRANDS.index(cur_brand) + 1) if cur_brand in BRANDS else 0,
            )
            e_model = c6.text_input("Model Name", value=editing.get("bike_model") or "")
            c7, c8, c9 = st.columns(3)
            e_cost = c7.number_input("Cost Price (₹)", min_value=0.0, step=1.0,
                                     value=float(editing.get("cost_price") or 0.0))
            e_sell = c8.number_input("Selling Price (₹) *", min_value=0.0, step=1.0,
                                     value=float(editing.get("selling_price") or 0.0))
            e_qty = c9.number_input("Current Quantity", min_value=0, step=1,
                                    value=int(editing.get("stock_quantity") or 0))
            save_col, cancel_col = st.columns(2)
            saved = save_col.form_submit_button("💾 Save changes", use_container_width=True, type="primary")
            cancelled = cancel_col.form_submit_button("✖ Cancel", use_container_width=True)

        if cancelled:
            st.session_state.pop("edit_part", None)
            st.rerun()
        if saved:
            errs = []
            if not e_name.strip():
                errs.append("Part Name is required.")
            if e_sell <= 0:
                errs.append("Selling Price must be greater than 0.")
            if errs:
                for e in errs:
                    st.warning(e)
            else:
                payload = {
                    "part_number": e_pn.strip() or None,
                    "name": e_name.strip(),
                    "category": e_category,
                    "min_threshold": int(e_min),
                    "brand": e_brand if e_brand != "— Select —" else None,
                    "bike_model": e_model.strip() or None,
                    "cost_price": e_cost or None,
                    "selling_price": e_sell,
                    "stock_quantity": int(e_qty),
                }
                if api.patch(f"/api/inventory/{editing['part_id']}", json=payload):
                    st.session_state.pop("edit_part", None)
                    st.success(f"'{e_name}' updated.")
                    st.rerun()

    # ── Add Part form — only shown when NOT editing and PN is not taken ──
    elif not existing_part:
        with st.expander("Add a new part", expanded=bool(pn)):
            with st.form("add_part_form", clear_on_submit=True):
                name = st.text_input("Part Name *", placeholder="e.g. Clutch Plate Set")
                c3, c4 = st.columns(2)
                category = c3.selectbox("Category *", CATEGORIES)
                min_threshold = c4.number_input("Min Stock Alert", min_value=0, value=5, step=1,
                                                help="You'll be alerted when stock falls to or below this number")

                c5, c6 = st.columns(2)
                brand = c5.selectbox("Brand", ["— Select —"] + BRANDS)
                bike_model = c6.text_input("Model Name", placeholder="e.g. Splendor, Pulsar 150")

                c7, c8, c9 = st.columns(3)
                cost_price = c7.number_input("Cost Price (₹)", min_value=0.0, value=0.0, step=1.0,
                                             help="What you paid the supplier — only visible to Admin")
                selling_price = c8.number_input("Selling Price (₹) *", min_value=0.0, value=0.0, step=1.0)
                stock_quantity = c9.number_input("Current Quantity", min_value=0, value=0, step=1)

                submitted = st.form_submit_button("Add Part", use_container_width=True, type="primary")

            if submitted:
                errors = []
                if not name.strip():
                    errors.append("Part Name is required.")
                if selling_price <= 0:
                    errors.append("Selling Price must be greater than 0.")
                if errors:
                    for e in errors:
                        st.warning(e)
                else:
                    payload = {
                        "part_number": pn or None,
                        "name": name.strip(),
                        "category": category,
                        "min_threshold": int(min_threshold),
                        "brand": brand if brand != "— Select —" else None,
                        "bike_model": bike_model.strip() or None,
                        "cost_price": cost_price or None,
                        "selling_price": selling_price,
                        "stock_quantity": int(stock_quantity),
                    }
                    if api.post("/api/inventory", json=payload):
                        st.success(f"'{name}' added to inventory.")
                        st.rerun()

st.divider()

# --- Inventory grid ---
st.subheader("Current Inventory")

# Low-stock filter. Turned on automatically when arriving from the
# Dashboard's "View Low Stock Items" button (which sets the session flag),
# and can also be toggled manually here.
default_low = st.session_state.pop("show_low_stock", False)
fcol1, fcol2 = st.columns([3, 1])
search = fcol1.text_input("Search by name or category", "",
                          label_visibility="collapsed",
                          placeholder="🔍 Search by name, category, brand...")
low_only = fcol2.checkbox("Low stock only", value=default_low)

# Cached — inventory list is expensive on large catalogs and doesn't change
# every second. Cache is auto-invalidated after any add/edit/import.
items = api.get_fast("/api/inventory")

if items:
    df = pd.DataFrame(items)

    # Reorder columns for a cleaner display
    admin_cols = ["part_id", "part_number", "name", "category", "brand", "bike_model",
                  "stock_quantity", "min_threshold", "cost_price", "selling_price", "is_low_stock"]
    public_cols = ["part_id", "part_number", "name", "category", "brand", "bike_model",
                   "stock_quantity", "selling_price", "is_low_stock"]
    ordered = admin_cols if is_admin else public_cols
    display_cols = [c for c in ordered if c in df.columns]
    df = df[display_cols]

    # Apply the low-stock filter first so search narrows within it
    if low_only and "is_low_stock" in df.columns:
        df = df[df["is_low_stock"] == True]
        st.caption(f"Showing {len(df)} low-stock item(s).")

    if search:
        mask = (
            df["name"].str.contains(search, case=False, na=False)
            | df["category"].fillna("").str.contains(search, case=False, na=False)
            | df["brand"].fillna("").str.contains(search, case=False, na=False)
            | df["bike_model"].fillna("").str.contains(search, case=False, na=False)
            | df["part_number"].fillna("").str.contains(search, case=False, na=False)
        )
        df = df[mask]

    if is_admin:
        st.caption("Admins can edit prices and thresholds inline below, then click Save changes.")
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            hide_index=True,
            disabled=["part_id", "is_low_stock"],
            key="inventory_editor",
        )
        if st.button("💾 Save changes"):
            changes = 0
            original_by_id = {row["part_id"]: row for row in items}
            for _, row in edited_df.iterrows():
                original = original_by_id.get(row["part_id"])
                if not original:
                    continue
                diff = {}
                for field in ["part_number", "name", "category", "brand", "bike_model",
                               "stock_quantity", "min_threshold", "cost_price", "selling_price"]:
                    new_val = row.get(field)
                    old_val = original.get(field)
                    new_is_empty = new_val is None or (isinstance(new_val, float) and pd.isna(new_val))
                    old_is_empty = old_val is None or (isinstance(old_val, float) and pd.isna(old_val))
                    if new_is_empty and old_is_empty:
                        continue
                    if new_is_empty != old_is_empty or new_val != old_val:
                        diff[field] = None if new_is_empty else new_val
                if diff:
                    if api.patch(f"/api/inventory/{row['part_id']}", json=diff):
                        changes += 1
            if changes:
                st.success(f"Saved {changes} change(s).")
                st.rerun()
            else:
                st.info("No changes detected.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No inventory items yet. Add one above or import a supplier catalog.")

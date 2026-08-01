import pandas as pd
import plotly.express as px
import streamlit as st

import api_client as api
from auth_guard import require_role

require_role("Admin")

st.title("📊 Dashboard")

with st.spinner("Loading..."):
    metrics  = api.get_fast("/api/dashboard/metrics")
    inv_cats = api.get_fast("/api/dashboard/inventory-by-category")
    top_sell = api.get_fast("/api/dashboard/top-selling")

# ── Business Summary ──────────────────────────────────────────────────────────
st.subheader("💼 Business Summary")
if metrics:
    c1, c2, c3 = st.columns(3)
    c1.metric("Today's Revenue",
              f"₹{metrics['revenue_today']:,.0f}")
    c2.metric("Active Jobs",
              metrics["active_jobs"])
    c3.metric(f"Revenue — {metrics.get('month_name', 'This Month')}",
              f"₹{metrics['revenue_month']:,.0f}")

st.divider()

# ── Inventory Summary ─────────────────────────────────────────────────────────
st.subheader("📦 Inventory Summary")
if metrics:
    ic1, ic2 = st.columns(2)

    with ic1:
        st.metric("Total Inventory Items", metrics["total_items"])
        if st.button("📋 View All Inventory", use_container_width=True):
            st.switch_page("pages/2_Inventory.py")

    with ic2:
        low = metrics["low_stock_count"]
        st.metric("Low Stock Items", low)
        if low > 0:
            if st.button("⚠️ View Low Stock Items", use_container_width=True):
                st.session_state["show_low_stock"] = True
                st.switch_page("pages/2_Inventory.py")

st.divider()

# ── Charts ────────────────────────────────────────────────────────────────────
ch1, ch2 = st.columns(2)

with ch1:
    st.subheader("📊 Inventory by Category")
    if inv_cats:
        df_cat = pd.DataFrame(inv_cats)
        fig = px.pie(df_cat, names="category", values="count", hole=0.4,
                     color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), showlegend=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("No inventory data yet.")

with ch2:
    st.subheader("🏆 Top Selling Parts (Last 30 Days)")
    if top_sell:
        df_top = pd.DataFrame(top_sell)
        fig2 = px.bar(df_top, x="quantity_sold", y="name", orientation="h",
                      color="quantity_sold",
                      color_continuous_scale=["#dce3ea", "#1a3c6e"],
                      labels={"quantity_sold": "Qty Sold", "name": ""})
        fig2.update_layout(margin=dict(l=10, r=10, t=10, b=10),
                           coloraxis_showscale=False,
                           yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.caption("No sales data in the last 30 days yet.")

st.divider()

# ── Revenue Trend ─────────────────────────────────────────────────────────────
st.subheader("📈 Revenue Trend — Last 30 Days")
trend = api.get_fast("/api/dashboard/revenue-trend")
if trend:
    df_trend = pd.DataFrame(trend)
    fig3 = px.line(df_trend, x="date", y="revenue", markers=True,
                   color_discrete_sequence=["#1a3c6e"])
    fig3.update_layout(margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.caption("No completed jobs in the last 30 days yet.")

if st.button("🔄 Refresh Dashboard"):
    api.invalidate_cache()
    st.rerun()

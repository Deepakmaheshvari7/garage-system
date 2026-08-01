import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import api_client as api
from auth_guard import require_role

require_role("Admin")

st.title("📊 Dashboard")

# ── Shared dark chart layout ──────────────────────────────────────────────────
CHART_COLORS = ["#3B82F6", "#06B6D4", "#10B981", "#F59E0B", "#EF4444",
                "#8B5CF6", "#EC4899", "#14B8A6"]

DARK_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#94A3B8", family="Inter"),
    margin=dict(l=10, r=10, t=10, b=10),
    colorway=CHART_COLORS,
)

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
        fig = px.pie(df_cat, names="category", values="count", hole=0.45,
                     color_discrete_sequence=CHART_COLORS)
        fig.update_traces(textposition="inside", textinfo="percent+label",
                          textfont=dict(color="#F8FAFC", size=11))
        fig.update_layout(**DARK_LAYOUT, showlegend=True,
                          legend=dict(font=dict(color="#94A3B8")))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("No inventory data yet.")

with ch2:
    st.subheader("🏆 Top Selling Parts (Last 30 Days)")
    if top_sell:
        df_top = pd.DataFrame(top_sell)
        fig2 = px.bar(df_top, x="quantity_sold", y="name", orientation="h",
                      color="quantity_sold",
                      color_continuous_scale=["#1A2332", "#3B82F6"],
                      labels={"quantity_sold": "Qty Sold", "name": ""})
        fig2.update_layout(**DARK_LAYOUT,
                           coloraxis_showscale=False,
                           yaxis=dict(autorange="reversed",
                                      gridcolor="#2D3748"),
                           xaxis=dict(gridcolor="#2D3748"))
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
                   color_discrete_sequence=["#3B82F6"])
    fig3.update_traces(line=dict(width=2.5), marker=dict(size=5))
    fig3.update_layout(**DARK_LAYOUT,
                       xaxis=dict(gridcolor="#2D3748"),
                       yaxis=dict(gridcolor="#2D3748"))
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.caption("No completed jobs in the last 30 days yet.")

if st.button("🔄 Refresh Dashboard"):
    api.invalidate_cache()
    st.rerun()

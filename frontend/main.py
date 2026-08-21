"""
Streamlit frontend — Shri Parvati Motors
"""
import base64, os, threading, time

# ── Demo mode flag — set SHOW_DEMO_CREDENTIALS=true ONLY on the Render demo ──
SHOW_DEMO_CREDENTIALS = os.getenv("SHOW_DEMO_CREDENTIALS", "false").lower() in ("true", "1", "yes")
import requests
import streamlit as st
import api_client as api

st.set_page_config(
    page_title="Shri Parvati Motors",
    page_icon="🏍️",
    layout="wide",
)

# ── Keep-alive: ping the backend so Render's free tier doesn't sleep ─────────
@st.cache_resource(ttl=None)
def _start_keepalive():
    def _ping():
        while True:
            try:
                requests.get(f"{api.API_BASE_URL}/docs", timeout=5)
            except Exception:
                pass
            time.sleep(600)  # every 10 minutes
    t = threading.Thread(target=_ping, daemon=True)
    t.start()
    return True

_start_keepalive()

# ── Global design layer — minimal, works with Streamlit's native layout ──────
st.markdown("""
    <style>
        /* ── Typography ────────────────────────────────────────────────── */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"], .stApp {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont,
                         'Segoe UI', sans-serif !important;
        }

        h1 { font-size: 1.6rem !important; font-weight: 700 !important;
             letter-spacing: -0.02em; }
        h2, h3 { font-weight: 600 !important; letter-spacing: -0.01em; }

        /* ── Native header: invisible, keep sidebar expand clickable ───── */
        [data-testid="stHeader"] {
            background: transparent !important;
            pointer-events: none !important;
        }
        [data-testid="stHeader"] [data-testid="stToolbar"],
        [data-testid="stHeader"] [data-testid="stDecoration"] {
            display: none !important;
        }
        [data-testid="stSidebarCollapsedControl"] {
            pointer-events: auto !important;
            top: 4.2rem !important;
            left: 0.6rem !important;
            z-index: 10000000 !important;
        }

        /* ── Fixed full-width top brand bar ────────────────────────────── */
        .top-brand-bar {
            position: fixed;
            top: 0; left: 0; right: 0;
            z-index: 9999999;
            background: rgba(11, 18, 32, 0.85);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            padding: 10px 24px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        }

        /* ── Main content: room for the brand bar, comfortable width ───── */
        .block-container {
            padding-top: 5.5rem !important;
            padding-bottom: 3rem !important;
            max-width: 1100px;
        }

        /* ── Sidebar: clear of the brand bar, logout pinned to bottom ──── */
        [data-testid="stSidebar"] > div:first-child {
            height: 100%;
            padding-top: 4.5rem;
        }
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
            height: 100%;
        }
        [data-testid="stSidebarNav"] { flex: 1 1 auto; }
        [data-testid="stSidebar"] .stElementContainer:has(.logout-anchor) {
            margin-top: auto;
        }
        [data-testid="stSidebar"] .stElementContainer:has(.logout-anchor)
        + .stElementContainer {
            padding-bottom: 1rem;
        }

        /* ── Hide Streamlit Cloud "Manage app" button ──────────────────── */
        [data-testid="stAppDeployButton"],
        .stAppDeployButton,
        [class*="deployButton"],
        [class*="DeployButton"] {
            display: none !important;
        }
    </style>
""", unsafe_allow_html=True)

# ── Hide sidebar on login ────────────────────────────────────────────────────
if not api.is_authenticated():
    st.markdown("""
        <style>
            [data-testid="stSidebar"]       { display: none !important; }
            [data-testid="collapsedControl"] { display: none !important; }
        </style>
    """, unsafe_allow_html=True)


def _logo_b64():
    logo_path = os.path.join(os.path.dirname(__file__), "Maa_Parvati.png")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None


def render_login():
    # Centre the login card
    _, col, _ = st.columns([1, 1.6, 1])
    with col:
        b64 = _logo_b64()
        img_tag = (f'<img src="data:image/png;base64,{b64}" '
                   f'style="width:120px;height:120px;object-fit:contain;'
                   f'border-radius:8px;" />'
                   if b64 else '<span style="font-size:48px;">🏍️</span>')

        st.markdown(f"""
            <div style="display:flex;align-items:center;gap:14px;
                        justify-content:center;margin-bottom:6px;margin-top:40px;">
                {img_tag}
                <div>
                    <div style="font-size:32px;font-weight:700;
                                color:#EF4444;line-height:1.2;">
                        श्री पार्वती मोटर्स
                    </div>
                    <div style="font-size:22px;font-weight:600;
                                color:#3B82F6;letter-spacing:1px;">
                        SHRI PARVATI MOTORS
                    </div>
                    <div style="font-size:10px;color:#94A3B8;margin-top:1px;">
                        TVS Authorised Service Center
                    </div>
                </div>
            </div>
            <p style="text-align:center;color:#64748B;font-size:12px;margin-bottom:20px;">
                Staff Portal
            </p>
        """, unsafe_allow_html=True)

        # Pre-fill credentials if a demo quick-fill button was clicked
        default_user = st.session_state.pop("_demo_user", "")
        default_pass = st.session_state.pop("_demo_pass", "")

        with st.form("login_form"):
            username = st.text_input("Username", value=default_user,
                                     placeholder="Enter your username")
            password = st.text_input("Password", value=default_pass, type="password",
                                     placeholder="Enter your password")
            submitted = st.form_submit_button("Sign In", use_container_width=True,
                                              type="primary")
        if submitted:
            if not username or not password:
                st.warning("Please enter both username and password.")
            elif api.login(username, password):
                st.rerun()

        # ── Demo credentials panel — only shown when SHOW_DEMO_CREDENTIALS=true ──
        if SHOW_DEMO_CREDENTIALS:
            st.markdown("""
                <div style="
                    background: rgba(59, 130, 246, 0.07);
                    border: 1px solid rgba(59, 130, 246, 0.25);
                    border-radius: 10px;
                    padding: 14px 16px;
                    margin-top: 14px;
                ">
                    <div style="font-weight:600;color:#60A5FA;font-size:12px;
                                margin-bottom:8px;letter-spacing:0.03em;">
                        💡 DEMO LOGIN CREDENTIALS
                    </div>
                    <table style="width:100%;border-collapse:collapse;font-size:11px;">
                        <thead>
                            <tr style="color:#64748B;">
                                <td style="padding:2px 6px;">Role</td>
                                <td style="padding:2px 6px;">Username</td>
                                <td style="padding:2px 6px;">Password</td>
                            </tr>
                        </thead>
                        <tbody style="color:#CBD5E1;">
                            <tr>
                                <td style="padding:3px 6px;color:#FBBF24;font-weight:600;">👑 Admin</td>
                                <td style="padding:3px 6px;"><code style="background:#1E293B;padding:1px 4px;border-radius:3px;">demo_admin</code></td>
                                <td style="padding:3px 6px;"><code style="background:#1E293B;padding:1px 4px;border-radius:3px;">Demo@Admin1</code></td>
                            </tr>
                            <tr>
                                <td style="padding:3px 6px;color:#34D399;font-weight:600;">📋 Desk</td>
                                <td style="padding:3px 6px;"><code style="background:#1E293B;padding:1px 4px;border-radius:3px;">demo_desk1</code></td>
                                <td style="padding:3px 6px;"><code style="background:#1E293B;padding:1px 4px;border-radius:3px;">Demo@Desk1</code></td>
                            </tr>
                            <tr>
                                <td style="padding:3px 6px;color:#A78BFA;font-weight:600;">🔧 Mechanic</td>
                                <td style="padding:3px 6px;"><code style="background:#1E293B;padding:1px 4px;border-radius:3px;">demo_mech1</code></td>
                                <td style="padding:3px 6px;"><code style="background:#1E293B;padding:1px 4px;border-radius:3px;">Demo@Mech1</code></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            """, unsafe_allow_html=True)

            st.caption("Quick fill & sign in:")
            c1, c2, c3 = st.columns(3)
            if c1.button("👑 Admin", use_container_width=True, key="demo_fill_admin"):
                st.session_state["_demo_user"] = "demo_admin"
                st.session_state["_demo_pass"] = "Demo@Admin1"
                st.rerun()
            if c2.button("📋 Desk", use_container_width=True, key="demo_fill_desk"):
                st.session_state["_demo_user"] = "demo_desk1"
                st.session_state["_demo_pass"] = "Demo@Desk1"
                st.rerun()
            if c3.button("🔧 Mechanic", use_container_width=True, key="demo_fill_mech"):
                st.session_state["_demo_user"] = "demo_mech1"
                st.session_state["_demo_pass"] = "Demo@Mech1"
                st.rerun()


def build_navigation():
    role = st.session_state["role"]
    dashboard    = st.Page("pages/1_Dashboard.py",    title="Dashboard",    icon="📊")
    inventory    = st.Page("pages/2_Inventory.py",    title="Inventory",    icon="📦")
    job_cards    = st.Page("pages/3_Job_Cards.py",    title="Job Cards",    icon="🛠️")
    billing      = st.Page("pages/4_Billing.py",      title="Billing",      icon="🧾")
    manage_staff = st.Page("pages/5_Manage_Staff.py", title="Manage Staff", icon="👥")

    if role == "Admin":
        pages   = {"Overview": [dashboard], "Operations": [job_cards, billing],
                   "Management": [inventory, manage_staff]}
        default = dashboard
    else:
        pages   = {"Operations": [job_cards, billing]}
        default = job_cards

    default._default = True
    return st.navigation(pages)


def main():
    api.init_session()

    if not api.is_authenticated():
        render_login()
        return

    # ── Top brand bar: logo + company name (left), user chip (right) ─────
    b64 = _logo_b64()
    img_tag = (f'<img src="data:image/png;base64,{b64}" '
               f'style="width:38px;height:38px;border-radius:8px;'
               f'object-fit:contain;" />'
               if b64 else '<span style="font-size:26px;">🏍️</span>')
    st.markdown(f"""
        <div class="top-brand-bar">
            <div style="display:flex;align-items:center;gap:10px;">
                {img_tag}
                <div>
                    <div style="font-size:16px;font-weight:700;color:#F8FAFC;
                                line-height:1.2;letter-spacing:-0.01em;">
                        Shri Parvati Motors
                    </div>
                    <div style="font-size:10px;color:#94A3B8;margin-top:1px;">
                        TVS Authorised Service Center
                    </div>
                </div>
            </div>
            <div style="display:flex;align-items:center;gap:9px;
                        background:#1A2332;border:1px solid #2D3748;
                        border-radius:999px;padding:5px 14px 5px 6px;">
                <div style="width:26px;height:26px;border-radius:50%;
                            background:#3B82F6;color:#fff;font-size:11px;
                            font-weight:600;display:flex;align-items:center;
                            justify-content:center;flex-shrink:0;">
                    {st.session_state['username'][0].upper()}
                </div>
                <div style="line-height:1.2;">
                    <div style="font-size:13px;font-weight:600;color:#F8FAFC;">
                        {st.session_state['username']}
                    </div>
                    <div style="font-size:10px;color:#94A3B8;">
                        {st.session_state['role']}
                    </div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    nav = build_navigation()
    nav.run()

    # ── Logout pinned to the absolute bottom of the sidebar ──────────────
    with st.sidebar:
        # Marker paragraph lets CSS locate & pin this block to the bottom
        st.markdown('<span class="logout-anchor"></span>',
                    unsafe_allow_html=True)
        if st.button("Sign Out", use_container_width=True):
            api.logout()
            st.rerun()


if __name__ == "__main__":
    main()

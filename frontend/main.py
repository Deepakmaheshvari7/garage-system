"""
Streamlit frontend — Shri Parvati Motors
"""
import base64, os
import streamlit as st
import api_client as api

st.set_page_config(
    page_title="Shri Parvati Motors",
    page_icon="🏍️",
    layout="wide",
)

# ── Global minimalist theme ──────────────────────────────────────────────────
st.markdown("""
    <style>
        /* ── Typography & base ─────────────────────────────────────────── */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"], .stApp {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont,
                         'Segoe UI', sans-serif !important;
            color: #1f2933;
        }

        .stApp { background: #fafbfc; }

        h1, h2, h3 {
            font-weight: 600 !important;
            letter-spacing: -0.01em;
            color: #111827 !important;
        }
        h1 { font-size: 1.6rem !important; }
        h2, h3 { font-size: 1.15rem !important; }

        /* ── Native header: invisible, but keep the sidebar expand ─────
           control clickable so a collapsed sidebar can be restored ──── */
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
            background: #ffffff;
            border: 1px solid #eceef1;
            border-radius: 8px;
        }

        /* ── Fixed full-width top brand bar ──────────────────────────── */
        .top-brand-bar {
            position: fixed;
            top: 0; left: 0; right: 0;
            z-index: 9999999;
            background: #ffffff;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            padding: 8px 24px;
            border-bottom: 1px solid #eceef1;
        }

        /* ── Main content breathing room ───────────────────────────────── */
        .block-container {
            padding-top: 5rem !important;
            padding-bottom: 3rem !important;
            max-width: 1200px;
        }

        /* ── Sidebar ───────────────────────────────────────────────────── */
        [data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid #eceef1;
        }
        [data-testid="stSidebar"] > div:first-child {
            height: 100%;
            padding-top: 4.5rem;
        }
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
            height: 100%;
            gap: 0.5rem;
        }
        /* Nav fills the middle so the logout block sinks to the bottom */
        [data-testid="stSidebarNav"] {
            flex: 1 1 auto;
        }
        /* Pin the logout block (marked by .logout-anchor) to the bottom */
        [data-testid="stSidebar"] .stElementContainer:has(.logout-anchor) {
            margin-top: auto;
            padding-top: 0.75rem;
            border-top: 1px solid #eceef1;
        }
        [data-testid="stSidebar"] .stElementContainer:has(.logout-anchor)
        + .stElementContainer {
            padding-bottom: 1rem;
        }

        /* ── Sidebar nav links ─────────────────────────────────────────── */
        [data-testid="stSidebarNav"] a {
            border-radius: 8px;
            padding: 0.45rem 0.75rem;
            margin: 1px 0;
            color: #4b5563 !important;
            font-weight: 500;
            transition: background 0.15s ease;
        }
        [data-testid="stSidebarNav"] a:hover {
            background: #f3f4f6;
        }
        [data-testid="stSidebarNav"] a[aria-current="page"] {
            background: #eef2f7;
            color: #1a3c6e !important;
            font-weight: 600;
        }
        [data-testid="stSidebarNav"] span[data-testid="stSidebarNavSeparator"] {
            border-color: #eceef1;
        }

        /* ── Buttons ───────────────────────────────────────────────────── */
        .stButton > button {
            border-radius: 8px;
            border: 1px solid #e5e7eb;
            background: #ffffff;
            color: #374151;
            font-weight: 500;
            padding: 0.45rem 1rem;
            transition: all 0.15s ease;
        }
        .stButton > button:hover {
            border-color: #cbd2d9;
            background: #f9fafb;
            color: #111827;
        }
        .stButton > button[kind="primary"],
        .stFormSubmitButton > button[kind="primary"] {
            background: #1a3c6e;
            border-color: #1a3c6e;
            color: #ffffff;
        }
        .stButton > button[kind="primary"]:hover,
        .stFormSubmitButton > button[kind="primary"]:hover {
            background: #16325c;
            border-color: #16325c;
        }

        /* ── Inputs ────────────────────────────────────────────────────── */
        .stTextInput input, .stNumberInput input,
        .stSelectbox [data-baseweb="select"] > div,
        .stTextArea textarea {
            border-radius: 8px !important;
            border-color: #e5e7eb !important;
        }

        /* ── Metrics ───────────────────────────────────────────────────── */
        [data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #eceef1;
            border-radius: 12px;
            padding: 1rem 1.25rem;
        }
        [data-testid="stMetricLabel"] { color: #6b7280; font-weight: 500; }
        [data-testid="stMetricValue"] { color: #111827; font-weight: 600; }

        /* ── Dataframes / tables — visually lightweight ────────────────── */
        [data-testid="stDataFrame"],
        [data-testid="stTable"] {
            border: 1px solid #eceef1;
            border-radius: 12px;
            overflow: hidden;
        }

        /* ── Dividers & captions ───────────────────────────────────────── */
        hr { border-color: #eceef1 !important; margin: 2rem 0 !important; }
        .stCaption, small { color: #9ca3af !important; }

        /* ── Alerts — softer ───────────────────────────────────────────── */
        [data-testid="stAlert"] {
            border-radius: 10px;
            border: 1px solid #eceef1;
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
                                color:#c0392b;line-height:1.2;">
                        श्री पार्वती मोटर्स
                    </div>
                    <div style="font-size:22px;font-weight:600;
                                color:#1a3c6e;letter-spacing:1px;">
                        SHRI PARVATI MOTORS
                    </div>
                    <div style="font-size:10px;color:#888;margin-top:1px;">
                        TVS Authorised Service Center
                    </div>
                </div>
            </div>
            <p style="text-align:center;color:#aaa;font-size:12px;margin-bottom:20px;">
                Staff Portal
            </p>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password",
                                     placeholder="Enter your password")
            submitted = st.form_submit_button("Sign In", use_container_width=True,
                                              type="primary")
        if submitted:
            if not username or not password:
                st.warning("Please enter both username and password.")
            elif api.login(username, password):
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
                    <div style="font-size:16px;font-weight:700;color:#111827;
                                line-height:1.2;letter-spacing:-0.01em;">
                        Shri Parvati Motors
                    </div>
                    <div style="font-size:10px;color:#9ca3af;margin-top:1px;">
                        TVS Authorised Service Center
                    </div>
                </div>
            </div>
            <div style="display:flex;align-items:center;gap:9px;
                        background:#f6f7f9;border:1px solid #eceef1;
                        border-radius:999px;padding:5px 14px 5px 6px;">
                <div style="width:26px;height:26px;border-radius:50%;
                            background:#1a3c6e;color:#fff;font-size:11px;
                            font-weight:600;display:flex;align-items:center;
                            justify-content:center;flex-shrink:0;">
                    {st.session_state['username'][0].upper()}
                </div>
                <div style="line-height:1.2;">
                    <div style="font-size:13px;font-weight:600;color:#111827;">
                        {st.session_state['username']}
                    </div>
                    <div style="font-size:10px;color:#9ca3af;">
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

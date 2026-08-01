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

# ── Global design system — premium dark SaaS theme ───────────────────────────
st.markdown("""
    <style>
        /* ══════════════════════════════════════════════════════════════════
           DESIGN TOKENS
           ══════════════════════════════════════════════════════════════════ */
        :root {
            --bg-primary:    #0B1220;
            --bg-secondary:  #111827;
            --surface:       #1A2332;
            --surface-elev:  #243042;
            --border:        #2D3748;
            --text-primary:  #F8FAFC;
            --text-secondary:#CBD5E1;
            --text-muted:    #94A3B8;
            --accent:        #3B82F6;
            --cyan:          #06B6D4;
            --success:       #10B981;
            --warning:       #F59E0B;
            --danger:        #EF4444;
            --radius:        12px;
            --radius-sm:     8px;
            --transition:    200ms ease;
        }

        /* ── Typography & base ─────────────────────────────────────────── */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"], .stApp {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont,
                         'Segoe UI', sans-serif !important;
            color: var(--text-primary);
        }

        .stApp { background: var(--bg-primary); }

        h1, h2, h3 {
            font-weight: 700 !important;
            letter-spacing: -0.02em;
            color: var(--text-primary) !important;
        }
        h1 { font-size: 1.5rem !important; }
        h2, h3 { font-size: 1.1rem !important; }

        p, span, label, .stMarkdown, [data-testid="stMarkdownContainer"] {
            color: var(--text-secondary);
        }

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
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            color: var(--text-secondary);
        }

        /* ── Fixed full-width top brand bar ────────────────────────────── */
        .top-brand-bar {
            position: fixed;
            top: 0; left: 0; right: 0;
            z-index: 9999999;
            background: rgba(17, 24, 39, 0.85);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            padding: 10px 24px;
            border-bottom: 1px solid var(--border);
        }

        /* ── Main content ──────────────────────────────────────────────── */
        .block-container {
            padding-top: 5.5rem !important;
            padding-bottom: 3rem !important;
            max-width: 1200px;
        }

        /* ── Sidebar ───────────────────────────────────────────────────── */
        [data-testid="stSidebar"] {
            background: var(--bg-secondary);
            border-right: 1px solid var(--border);
        }
        [data-testid="stSidebar"] > div:first-child {
            height: 100%;
            padding-top: 4.5rem;
        }
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
            height: 100%;
            gap: 0.4rem;
        }
        [data-testid="stSidebarNav"] { flex: 1 1 auto; }
        [data-testid="stSidebar"] .stElementContainer:has(.logout-anchor) {
            margin-top: auto;
            padding-top: 0.75rem;
            border-top: 1px solid var(--border);
        }
        [data-testid="stSidebar"] .stElementContainer:has(.logout-anchor)
        + .stElementContainer {
            padding-bottom: 1rem;
        }

        /* ── Sidebar nav links ─────────────────────────────────────────── */
        [data-testid="stSidebarNav"] a {
            border-radius: var(--radius-sm);
            padding: 0.5rem 0.75rem;
            margin: 2px 0;
            color: var(--text-muted) !important;
            font-weight: 500;
            transition: all var(--transition);
        }
        [data-testid="stSidebarNav"] a:hover {
            background: var(--surface);
            color: var(--text-primary) !important;
        }
        [data-testid="stSidebarNav"] a[aria-current="page"] {
            background: var(--surface-elev);
            color: var(--accent) !important;
            font-weight: 600;
            box-shadow: inset 2px 0 0 var(--accent);
        }
        [data-testid="stSidebarNav"] span[data-testid="stSidebarNavSeparator"] {
            border-color: var(--border);
        }

        /* ── Buttons ───────────────────────────────────────────────────── */
        .stButton > button {
            border-radius: var(--radius-sm);
            border: 1px solid var(--border);
            background: var(--surface);
            color: var(--text-secondary);
            font-weight: 500;
            padding: 0.5rem 1rem;
            transition: all var(--transition);
        }
        .stButton > button:hover {
            border-color: var(--accent);
            background: var(--surface-elev);
            color: var(--text-primary);
            box-shadow: 0 0 12px rgba(59, 130, 246, 0.15);
        }
        .stButton > button[kind="primary"],
        .stFormSubmitButton > button[kind="primary"] {
            background: var(--accent);
            border-color: var(--accent);
            color: #ffffff;
        }
        .stButton > button[kind="primary"]:hover,
        .stFormSubmitButton > button[kind="primary"]:hover {
            background: #2563EB;
            border-color: #2563EB;
            box-shadow: 0 0 16px rgba(59, 130, 246, 0.3);
        }

        /* ── Inputs ────────────────────────────────────────────────────── */
        .stTextInput input, .stNumberInput input,
        .stSelectbox [data-baseweb="select"] > div,
        .stTextArea textarea {
            border-radius: var(--radius-sm) !important;
            border-color: var(--border) !important;
            background: var(--surface) !important;
            color: var(--text-primary) !important;
            transition: border-color var(--transition);
        }
        .stTextInput input:focus, .stNumberInput input:focus,
        .stTextArea textarea:focus {
            border-color: var(--accent) !important;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15) !important;
        }

        /* ── Metrics — elevated cards ──────────────────────────────────── */
        [data-testid="stMetric"] {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 1.25rem 1.5rem;
            transition: all var(--transition);
        }
        [data-testid="stMetric"]:hover {
            border-color: var(--accent);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3),
                        0 0 12px rgba(59, 130, 246, 0.08);
        }
        [data-testid="stMetricLabel"] {
            color: var(--text-muted) !important;
            font-weight: 500;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        [data-testid="stMetricValue"] {
            color: var(--text-primary) !important;
            font-weight: 700;
            font-size: 1.5rem;
        }

        /* ── Dataframes / tables ───────────────────────────────────────── */
        [data-testid="stDataFrame"],
        [data-testid="stTable"] {
            border: 1px solid var(--border);
            border-radius: var(--radius);
            overflow: hidden;
        }

        /* ── Expanders ─────────────────────────────────────────────────── */
        [data-testid="stExpander"] {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
        }
        [data-testid="stExpander"] summary {
            color: var(--text-secondary);
            font-weight: 500;
        }
        [data-testid="stExpander"] summary:hover {
            color: var(--text-primary);
        }

        /* ── Containers with border ────────────────────────────────────── */
        [data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--surface);
            border: 1px solid var(--border) !important;
            border-radius: var(--radius) !important;
        }

        /* ── Dividers & captions ───────────────────────────────────────── */
        hr { border-color: var(--border) !important; margin: 2rem 0 !important; }
        .stCaption, small { color: var(--text-muted) !important; }

        /* ── Alerts ────────────────────────────────────────────────────── */
        [data-testid="stAlert"] {
            border-radius: var(--radius-sm);
            border: 1px solid var(--border);
            background: var(--surface);
        }

        /* ── Popover ───────────────────────────────────────────────────── */
        [data-testid="stPopover"] > div {
            background: var(--surface-elev);
            border: 1px solid var(--border);
            border-radius: var(--radius);
        }

        /* ── Tabs ──────────────────────────────────────────────────────── */
        .stTabs [data-baseweb="tab-list"] {
            gap: 4px;
            border-bottom: 1px solid var(--border);
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: var(--radius-sm) var(--radius-sm) 0 0;
            color: var(--text-muted);
            font-weight: 500;
        }
        .stTabs [data-baseweb="tab"][aria-selected="true"] {
            color: var(--accent);
            border-bottom-color: var(--accent);
        }

        /* ── Checkbox / toggle ─────────────────────────────────────────── */
        .stCheckbox label { color: var(--text-secondary) !important; }

        /* ── File uploader ─────────────────────────────────────────────── */
        [data-testid="stFileUploader"] {
            background: var(--surface);
            border: 1px dashed var(--border);
            border-radius: var(--radius);
        }

        /* ── Hide Streamlit Cloud "Manage app" button ──────────────────── */
        [data-testid="stAppDeployButton"],
        .stAppDeployButton,
        [class*="deployButton"],
        [class*="DeployButton"] {
            display: none !important;
        }

        /* ── Scrollbar ─────────────────────────────────────────────────── */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: var(--bg-primary); }
        ::-webkit-scrollbar-thumb {
            background: var(--border);
            border-radius: 3px;
        }
        ::-webkit-scrollbar-thumb:hover { background: var(--surface-elev); }

        /* ── Selectbox dropdown ────────────────────────────────────────── */
        [data-baseweb="popover"] {
            background: var(--surface-elev) !important;
            border: 1px solid var(--border) !important;
            border-radius: var(--radius-sm) !important;
        }
        [data-baseweb="menu"] li {
            color: var(--text-secondary) !important;
        }
        [data-baseweb="menu"] li:hover {
            background: var(--surface) !important;
            color: var(--text-primary) !important;
        }

        /* ══════════════════════════════════════════════════════════════════
           SPACING SYSTEM — 8px grid, consistent padding everywhere
           ══════════════════════════════════════════════════════════════════ */

        /* ── Headings: space below so content doesn't touch ────────────── */
        h1 { margin-bottom: 1rem !important; }
        h2, h3 { margin-bottom: 0.75rem !important; }
        h4, h5, h6 { margin-bottom: 0.5rem !important; }

        /* ── Subheader spacing ─────────────────────────────────────────── */
        [data-testid="stSubheader"], .stSubheader {
            margin-top: 1.5rem !important;
            margin-bottom: 0.75rem !important;
        }

        /* ── Expanders: proper internal padding ────────────────────────── */
        [data-testid="stExpander"] {
            padding: 0 !important;
            overflow: hidden;
        }
        [data-testid="stExpander"] summary {
            padding: 1rem 1.25rem !important;
        }
        [data-testid="stExpander"] [data-testid="stExpanderDetails"],
        [data-testid="stExpander"] > div > div:last-child {
            padding: 0 1.25rem 1.25rem 1.25rem !important;
        }

        /* ── Forms: internal spacing ───────────────────────────────────── */
        [data-testid="stForm"] {
            padding: 1.25rem !important;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
        }
        [data-testid="stForm"] > div {
            gap: 0.75rem;
        }

        /* ── Alerts: comfortable padding ───────────────────────────────── */
        [data-testid="stAlert"] {
            padding: 1rem 1.25rem !important;
        }

        /* ── Popover content padding ───────────────────────────────────── */
        [data-testid="stPopover"] > div {
            padding: 1rem 1.25rem !important;
        }

        /* ── File uploader: internal padding ───────────────────────────── */
        [data-testid="stFileUploader"] {
            padding: 1.25rem !important;
        }
        [data-testid="stFileUploader"] section {
            padding: 1rem !important;
        }

        /* ── Data editor / dataframe cell padding ──────────────────────── */
        [data-testid="stDataFrame"] > div,
        [data-testid="stTable"] > div {
            padding: 0.5rem !important;
        }

        /* ── Bordered containers (st.container(border=True)) ───────────── */
        [data-testid="stVerticalBlockBorderWrapper"] {
            padding: 1.25rem !important;
        }

        /* ── Metric cards: already padded, ensure consistency ──────────── */
        [data-testid="stMetric"] {
            padding: 1.25rem 1.5rem !important;
        }

        /* ── Widget spacing: gap between stacked widgets ───────────────── */
        .stTextInput, .stNumberInput, .stSelectbox, .stTextArea,
        .stCheckbox, .stRadio, .stSlider, .stDateInput, .stTimeInput,
        .stFileUploader, .stMultiSelect {
            margin-bottom: 0.5rem;
        }

        /* ── Button spacing ────────────────────────────────────────────── */
        .stButton { margin-bottom: 0.25rem; }

        /* ── Column gaps ───────────────────────────────────────────────── */
        [data-testid="stHorizontalBlock"] {
            gap: 1rem !important;
        }

        /* ── Divider: consistent vertical rhythm ───────────────────────── */
        hr { margin: 2rem 0 !important; }

        /* ── Caption: slight top margin ────────────────────────────────── */
        .stCaption { margin-top: 0.25rem !important; }

        /* ── Toast notifications ───────────────────────────────────────── */
        [data-testid="stToast"] {
            padding: 0.75rem 1.25rem !important;
            border-radius: var(--radius-sm) !important;
        }

        /* ── Tab content padding ───────────────────────────────────────── */
        .stTabs [data-baseweb="tab-panel"] {
            padding-top: 1rem !important;
        }

        /* ── Sidebar internal padding ──────────────────────────────────── */
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
            padding: 0 0.75rem;
        }

        /* ── Login form card ───────────────────────────────────────────── */
        .stForm [data-testid="stFormSubmitButton"] {
            margin-top: 0.5rem;
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

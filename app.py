import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import sqlite3
import hashlib
import secrets
import os


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gramseva.db")

st.set_page_config(
    page_title="GramSeva",
    page_icon="🏡",
    layout="wide"
)

SERVICE_OPTIONS = {
    "🏛️ Government Services": [
        "Government scheme information",
        "Online application assistance",
        "Government portal navigation"
    ],
    "💳 Digital Payments": [
        "UPI payment assistance",
        "Bill payment assistance",
        "Digital transaction support"
    ],
    "🖨️ Printing & Scanning": [
        "Document printing",
        "Document scanning",
        "PDF creation"
    ],
    "📄 Document Assistance": [
        "Online form assistance",
        "Document upload assistance",
        "Basic document preparation"
    ],
    "📞 Tele-Service": [
        "Video consultation",
        "Remote service assistance",
        "Digital help desk"
    ],
    "📸 Photo & ID Services": [
        "Digital photograph",
        "ID-size photograph",
        "Basic ID document preparation"
    ]
}

SERVICE_FEES = {
    "🏛️ Government Services": 20,
    "💳 Digital Payments": 10,
    "🖨️ Printing & Scanning": 30,
    "📄 Document Assistance": 25,
    "📞 Tele-Service": 50,
    "📸 Photo & ID Services": 40
}

STATUS_FLOW = ["Submitted", "In Progress", "Completed", "Cancelled"]

SEED_TRANSACTIONS = [
    ("2026-08-01", "Government Services", 20),
    ("2026-08-01", "Printing & Scanning", 30),
    ("2026-08-02", "Digital Payments", 10),
    ("2026-08-02", "Printing & Scanning", 40),
    ("2026-08-03", "Document Assistance", 25),
    ("2026-08-03", "Tele-Service", 50),
    ("2026-08-04", "Government Services", 20),
    ("2026-08-05", "Digital Payments", 15),
    ("2026-08-06", "Printing & Scanning", 35),
    ("2026-08-07", "Document Assistance", 25),
    ("2026-08-08", "Photo & ID Services", 40),
    ("2026-08-09", "Government Services", 20),
    ("2026-08-10", "Tele-Service", 50),
    ("2026-08-11", "Digital Payments", 10),
    ("2026-08-11", "Printing & Scanning", 30),
]


# =========================================================
# DATABASE LAYER
# =========================================================
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000
    ).hex()
    return pwd_hash, salt


def verify_password(password, salt, stored_hash):
    test_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(test_hash, stored_hash)


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mobile TEXT UNIQUE NOT NULL,
            village TEXT,
            preferred_language TEXT DEFAULT 'English',
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            service TEXT,
            option TEXT,
            notes TEXT,
            status TEXT DEFAULT 'Submitted',
            created_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            service TEXT,
            amount INTEGER
        )
    """)

    conn.commit()

    # Seed demo transactions (only once)
    cur.execute("SELECT COUNT(*) AS c FROM transactions")
    if cur.fetchone()["c"] == 0:
        cur.executemany(
            "INSERT INTO transactions (date, service, amount) VALUES (?, ?, ?)",
            SEED_TRANSACTIONS
        )
        conn.commit()

    # Seed a default admin account (only once)
    cur.execute("SELECT COUNT(*) AS c FROM users WHERE role = 'admin'")
    if cur.fetchone()["c"] == 0:
        pwd_hash, salt = hash_password("admin123")
        cur.execute("""
            INSERT INTO users (name, mobile, village, preferred_language,
                                password_hash, salt, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'admin', ?)
        """, ("Kiosk Admin", "admin", "HQ", "English", pwd_hash, salt,
              datetime.now().isoformat()))
        conn.commit()

    # Demo kiosk operator account
    cur.execute("SELECT COUNT(*) AS c FROM users WHERE role = 'operator'")
    if cur.fetchone()["c"] == 0:
        pwd_hash, salt = hash_password("operator123")
        cur.execute("""
            INSERT INTO users (name, mobile, village, preferred_language,
                                password_hash, salt, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'operator', ?)
        """, ("Kiosk Operator", "operator", "Demo Village", "English",
              pwd_hash, salt, datetime.now().isoformat()))
        conn.commit()

    conn.close()


def create_user(name, mobile, village, language, password):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE mobile = ?", (mobile,))
    if cur.fetchone():
        conn.close()
        return False, "An account with this mobile number already exists."

    pwd_hash, salt = hash_password(password)
    cur.execute("""
        INSERT INTO users (name, mobile, village, preferred_language,
                            password_hash, salt, role, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'user', ?)
    """, (name, mobile, village, language, pwd_hash, salt,
          datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return True, "Account created successfully. You can now log in."


def authenticate(mobile, password):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE mobile = ?", (mobile,))
    row = cur.fetchone()
    conn.close()
    if row and verify_password(password, row["salt"], row["password_hash"]):
        user = dict(row)
        user.pop("password_hash", None)
        user.pop("salt", None)
        return user
    return None


def create_request(user_id, service, option, notes):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS c FROM requests")
    count = cur.fetchone()["c"]
    request_id = f"GS{1001 + count}"
    cur.execute("""
        INSERT INTO requests (request_id, user_id, service, option, notes,
                               status, created_at)
        VALUES (?, ?, ?, ?, ?, 'Submitted', ?)
    """, (request_id, user_id, service, option, notes,
          datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return request_id


def get_user_requests(user_id):
    conn = get_conn()
    df = pd.read_sql_query(
        "SELECT * FROM requests WHERE user_id = ? ORDER BY created_at DESC",
        conn, params=(user_id,)
    )
    conn.close()
    return df


def get_all_requests():
    conn = get_conn()
    df = pd.read_sql_query("""
        SELECT r.request_id, r.service, r.option, r.notes, r.status,
               r.created_at, u.name, u.mobile, u.village
        FROM requests r
        JOIN users u ON r.user_id = u.id
        ORDER BY r.created_at DESC
    """, conn)
    conn.close()
    return df


def update_request_status(request_id, new_status):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE requests SET status = ? WHERE request_id = ?",
        (new_status, request_id)
    )
    conn.commit()
    conn.close()


def get_transactions_df():
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM transactions", conn)
    conn.close()
    return df


def get_kiosk_stats():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS c FROM users WHERE role = 'user'")
    total_users = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) AS c FROM requests")
    total_requests = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) AS c FROM requests WHERE status = 'Submitted'")
    pending_requests = cur.fetchone()["c"]
    conn.close()
    return total_users, total_requests, pending_requests


init_db()


# =========================================================
# STYLES
# =========================================================
st.markdown("""
<style>
.block-container {
    padding-top: 1.5rem;
    max-width: 1400px;
}
.hero {
    padding: 34px;
    border-radius: 24px;
    background: linear-gradient(135deg, #12355b, #2563eb, #7c3aed);
    color: white;
    margin-bottom: 25px;
    box-shadow: 0 15px 35px rgba(37,99,235,.20);
}
.hero h1 { margin: 0; font-size: 44px; font-weight: 800; }
.hero p { font-size: 17px; opacity: .92; }
.pill {
    display: inline-block;
    padding: 6px 12px;
    border-radius: 20px;
    background: rgba(255,255,255,.17);
    font-size: 12px;
    margin-bottom: 10px;
}
.card {
    padding: 22px;
    border-radius: 18px;
    border: 1px solid rgba(128,128,128,.22);
    background: rgba(128,128,128,.06);
    min-height: 175px;
}
.card:hover { border-color: #4f8cff; }
.icon { font-size: 34px; }
.card-title { font-size: 19px; font-weight: 700; margin: 8px 0; }
.card-text { opacity: .72; font-size: 14px; line-height: 1.5; }
.section { font-size: 24px; font-weight: 750; margin: 25px 0 14px; }
.quick {
    padding: 15px 18px;
    border-radius: 14px;
    border: 1px solid rgba(128,128,128,.20);
    background: rgba(128,128,128,.05);
}
.status-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 700;
}
.status-Submitted { background: rgba(59,130,246,.18); color: #3b82f6; }
.status-InProgress, .status-In-Progress { background: rgba(245,158,11,.18); color: #f59e0b; }
.status-Completed { background: rgba(34,197,94,.18); color: #22c55e; }
.status-Cancelled { background: rgba(239,68,68,.18); color: #ef4444; }
div[data-testid="stMetric"] {
    border: 1px solid rgba(128,128,128,.20);
    border-radius: 15px;
    padding: 14px;
    background: rgba(128,128,128,.05);
}
[data-testid="stSidebar"] { border-right: 1px solid rgba(128,128,128,.18); }

/* ===== GramSeva animations ===== */
@keyframes fadeUp {
    from { opacity: 0; transform: translateY(18px); }
    to { opacity: 1; transform: translateY(0); }
}
@keyframes floatBlob {
    0%, 100% { transform: translateY(0) rotate(0deg); }
    50% { transform: translateY(-12px) rotate(4deg); }
}
@keyframes pulseGlow {
    0%, 100% { box-shadow: 0 0 0 rgba(99,102,241,0); }
    50% { box-shadow: 0 0 28px rgba(99,102,241,.18); }
}
.hero, .card, .quick, [data-testid="stMetric"], .stTabs, .stDataFrame {
    animation: fadeUp .65s ease both;
}
.hero {
    position: relative;
    overflow: hidden;
    animation: fadeUp .65s ease both, pulseGlow 3s ease-in-out infinite;
}
.hero::after {
    content: "";
    position: absolute;
    width: 180px; height: 180px;
    right: -45px; top: -60px;
    border-radius: 50%;
    background: rgba(255,255,255,.12);
    animation: floatBlob 5s ease-in-out infinite;
}
.card {
    transition: transform .25s ease, box-shadow .25s ease, border-color .25s ease;
}
.card:hover {
    transform: translateY(-7px) scale(1.01);
    box-shadow: 0 14px 30px rgba(37,99,235,.16);
}
.stButton > button {
    transition: transform .2s ease, box-shadow .2s ease;
}
.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(37,99,235,.20);
}
div[data-testid="stMetric"] {
    transition: transform .2s ease, box-shadow .2s ease;
}
div[data-testid="stMetric"]:hover {
    transform: translateY(-4px);
    box-shadow: 0 10px 24px rgba(99,102,241,.15);
}
[data-testid="stDataFrame"] {
    border-radius: 16px;
    overflow: hidden;
    border: 1px solid rgba(99,102,241,.20);
}
[data-testid="stDataFrame"] [role="columnheader"] {
    background: linear-gradient(90deg, #4f46e5, #7c3aed) !important;
    color: white !important;
    font-weight: 700 !important;
}
div[data-baseweb="tab-list"] button[aria-selected="true"] {
    background: linear-gradient(90deg, #4f46e5, #7c3aed);
    color: white;
    border-radius: 10px;
}
.role-card {
    padding: 16px;
    border-radius: 16px;
    background: linear-gradient(135deg, rgba(79,70,229,.10), rgba(236,72,153,.08));
    border: 1px solid rgba(99,102,241,.18);
    margin-bottom: 14px;
}
.login-badge {
    display: inline-block;
    padding: 5px 10px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: .5px;
    background: linear-gradient(90deg, #4f46e5, #ec4899);
    color: white;
}
</style>
""", unsafe_allow_html=True)


def status_class(status):
    return "status-" + status.replace(" ", "")


# =========================================================
# SESSION STATE
# =========================================================
if "user" not in st.session_state:
    st.session_state.user = None


# =========================================================
# AUTH SCREEN (shown when nobody is logged in)
# =========================================================
def render_auth_screen():
    st.markdown("""
    <div class="hero">
        <div class="pill">DIGITAL ACCESS • RURAL FIRST</div>
        <h1>🏡 GramSeva</h1>
        <p>Essential digital services, available closer to the people who need them.</p>
    </div>
    """, unsafe_allow_html=True)

    left, right = st.columns([1.05, 0.95], gap="large")

    with left:
        st.markdown('<div class="section">Choose your access</div>', unsafe_allow_html=True)

        login_role = st.radio(
            "Login as",
            ["👤 Resident", "🧑‍💼 Kiosk Operator", "🛡️ Admin"],
            horizontal=True,
            label_visibility="collapsed"
        )

        role_map = {
            "👤 Resident": ("user", "Resident Login", "Access services and track your requests."),
            "🧑‍💼 Kiosk Operator": ("operator", "Operator Login", "Manage kiosk requests and assist residents."),
            "🛡️ Admin": ("admin", "Admin Login", "View operations, requests and analytics.")
        }
        selected_role, role_title, role_desc = role_map[login_role]

        st.markdown(
            f'<div class="role-card"><span class="login-badge">{role_title.upper()}</span>'
            f'<h3>{role_title}</h3><p>{role_desc}</p></div>',
            unsafe_allow_html=True
        )

        tab_login, tab_signup = st.tabs(["🔑 Login", "🆕 Resident Sign Up"])

        with tab_login:
            with st.form("login_form"):
                mobile = st.text_input(
                    "Mobile / Login ID",
                    placeholder="Enter your mobile number or demo login ID"
                )
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button(
                    f"Log in as {role_title.replace(' Login', '')}",
                    type="primary", width="stretch"
                )

            if submitted:
                if not mobile or not password:
                    st.error("Please enter your login ID and password.")
                else:
                    user = authenticate(mobile.strip(), password)
                    if user and user["role"] == selected_role:
                        st.session_state.user = user
                        st.success(f"Welcome, {user['name']}! 🎉")
                        st.balloons()
                        st.rerun()
                    elif user:
                        st.error(
                            f"This account is registered as {user['role']}. "
                            "Please choose the correct login option."
                        )
                    else:
                        st.error("Invalid login ID or password.")

            if selected_role == "admin":
                st.caption("Demo Admin → ID: `admin` · Password: `admin123`")
            elif selected_role == "operator":
                st.caption("Demo Operator → ID: `operator` · Password: `operator123`")
            else:
                st.caption("Residents can create a free account from the Sign Up tab.")

        with tab_signup:
            if selected_role != "user":
                st.info("Resident registration is available only from the Resident login option.")
            else:
                with st.form("signup_form"):
                    name = st.text_input("Full Name")
                    mobile_su = st.text_input("Mobile Number", key="signup_mobile")
                    village = st.text_input("Village / Area")
                    language = st.selectbox("Preferred Language", ["English", "Hindi", "Marathi"])
                    password_su = st.text_input("Create Password", type="password", key="signup_password")
                    confirm = st.text_input("Confirm Password", type="password")
                    signup_submitted = st.form_submit_button(
                        "Create Resident Account", type="primary", width="stretch"
                    )

                if signup_submitted:
                    if not all([name, mobile_su, village, password_su, confirm]):
                        st.error("Please fill in all fields.")
                    elif len(password_su) < 4:
                        st.error("Password must be at least 4 characters.")
                    elif password_su != confirm:
                        st.error("Passwords do not match.")
                    else:
                        ok, msg = create_user(
                            name, mobile_su.strip(), village, language, password_su
                        )
                        if ok:
                            st.success(msg)
                        else:
                            st.error(msg)

    with right:
        st.markdown('<div class="section">GramSeva access levels</div>', unsafe_allow_html=True)
        items = [
            ("👤", "Resident", "Create requests, use digital services and track status."),
            ("🧑‍💼", "Kiosk Operator", "Handle day-to-day service requests and resident assistance."),
            ("🛡️", "Admin", "Monitor the complete kiosk and access analytics."),
        ]
        for icon, title, desc in items:
            st.markdown(f"""
            <div class="card" style="margin-bottom:14px; min-height:auto;">
                <div class="icon">{icon}</div>
                <div class="card-title">{title}</div>
                <div class="card-text">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("""
        <div class="quick">
            <b>✨ Prototype features</b><br>
            Animated dashboard • Role-based access • Request tracking •
            Colorful Plotly analytics • Interactive tables • SQLite database
        </div>
        """, unsafe_allow_html=True)


def completion_celebration(request_id, service):
    """Show a longer completion animation before the active queue refreshes."""
    st.markdown(f"""
    <style>
    @keyframes successPop {{
        0% {{ opacity: 0; transform: scale(.55) translateY(25px); }}
        55% {{ opacity: 1; transform: scale(1.08) translateY(0); }}
        100% {{ opacity: 1; transform: scale(1); }}
    }}
    @keyframes successGlow {{
        0%, 100% {{ box-shadow: 0 0 15px rgba(34,197,94,.12); }}
        50% {{ box-shadow: 0 0 55px rgba(34,197,94,.42); }}
    }}
    @keyframes checkDraw {{
        0% {{ transform: scale(0) rotate(-45deg); opacity: 0; }}
        70% {{ transform: scale(1.18) rotate(0); opacity: 1; }}
        100% {{ transform: scale(1) rotate(0); opacity: 1; }}
    }}
    .completion-overlay {{
        margin: 25px 0;
        padding: 42px 28px;
        border-radius: 28px;
        text-align: center;
        background: linear-gradient(135deg, #ecfdf5, #dbeafe, #f5f3ff);
        border: 2px solid rgba(34,197,94,.35);
        animation: successPop .75s ease both, successGlow 2s ease-in-out infinite;
    }}
    .completion-check {{
        width: 92px;
        height: 92px;
        margin: 0 auto 18px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        background: linear-gradient(135deg, #22c55e, #16a34a);
        color: white;
        font-size: 48px;
        font-weight: 900;
        animation: checkDraw .7s .2s ease both;
        box-shadow: 0 12px 30px rgba(22,163,74,.28);
    }}
    .completion-title {{
        font-size: 30px;
        font-weight: 850;
        color: #166534;
        margin-bottom: 8px;
    }}
    .completion-subtitle {{
        font-size: 16px;
        color: #365314;
        margin-bottom: 5px;
    }}
    .completion-id {{
        display: inline-block;
        margin-top: 12px;
        padding: 7px 14px;
        border-radius: 999px;
        background: rgba(255,255,255,.8);
        font-weight: 800;
        color: #4f46e5;
    }}
    </style>

    <div class="completion-overlay">
        <div class="completion-check">✓</div>
        <div class="completion-title">🎉 Request Completed!</div>
        <div class="completion-subtitle">
            The service has been successfully completed.
        </div>
        <div class="completion-subtitle"><b>{service}</b></div>
        <div class="completion-id">{request_id}</div>
    </div>
    """, unsafe_allow_html=True)

    # Keep the celebration on screen for about 5 seconds.
    import time
    time.sleep(5)

# =========================================================
# MAIN APP (shown after login)
# =========================================================
def render_main_app():
    user = st.session_state.user
    is_admin = user["role"] == "admin"
    is_operator = user["role"] == "operator"
    can_manage_requests = is_admin or is_operator

    with st.sidebar:
        st.markdown("## 🏡 GramSeva")
        st.caption("Rural Digital Service Kiosk")
        st.divider()

        st.markdown(f"**{user['name']}**")
        st.caption(f"📱 {user['mobile']} · {'Admin' if is_admin else ('Kiosk Operator' if is_operator else 'Resident')}")

        if st.button("🚪 Log Out", width="stretch"):
            st.session_state.user = None
            st.rerun()

        st.divider()

        nav_options = ["🏠 Home", "🧑‍💻 Services", "📋 My Requests"]
        if can_manage_requests:
            nav_options += ["🛠️ Request Management"]
        if is_admin:
            nav_options += ["📊 Kiosk Analytics"]
        nav_options += ["ℹ️ About Product"]

        page = st.radio("Navigate", nav_options)

        st.divider()
        st.markdown("### 🟢 Kiosk Status")
        st.success("Online")
        st.caption("All core modules operational")

        st.divider()
        st.selectbox("🌐 Language", ["English", "हिन्दी", "मराठी"],
                     index=["English", "हिन्दी", "मराठी"].index(user.get("preferred_language", "English"))
                     if user.get("preferred_language") in ["English", "हिन्दी", "मराठी"] else 0)

        st.divider()
        st.caption("Connected to live database")

    # ---------------- HOME ----------------
    if page == "🏠 Home":
        st.markdown(f"""
        <div class="hero">
            <div class="pill">DIGITAL ACCESS • RURAL FIRST</div>
            <h1>🏡 GramSeva</h1>
            <p>Welcome back, {user['name']}! Essential digital services, available closer to you.</p>
        </div>
        """, unsafe_allow_html=True)

        total_users, total_requests, pending_requests = get_kiosk_stats()
        my_requests = get_user_requests(user["id"])

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Services", len(SERVICE_OPTIONS))
        with c2:
            st.metric("Registered Residents", total_users)
        with c3:
            st.metric("Total Requests", total_requests)
        with c4:
            st.metric("Your Requests", len(my_requests))

        st.markdown('<div class="section">Quick Access</div>', unsafe_allow_html=True)
        items = [
            ("🏛️", "Government Services", "Online forms, schemes and portal assistance."),
            ("💳", "Digital Payments", "UPI, bills and transaction support."),
            ("🖨️", "Print & Scan", "Print, scan and create digital documents."),
        ]
        cols = st.columns(3)
        for i, (icon, title, desc) in enumerate(items):
            with cols[i]:
                st.markdown(f"""
                <div class="card">
                    <div class="icon">{icon}</div>
                    <div class="card-title">{title}</div>
                    <div class="card-text">{desc}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown('<div class="section">Explore More</div>', unsafe_allow_html=True)
        tab1, tab2, tab3 = st.tabs(["📄 Documents", "📞 Tele-Service", "📸 Photo & ID"])
        with tab1:
            st.write("Assistance with forms, uploads, scanning and document preparation.")
            st.progress(82, text="Document module readiness")
        with tab2:
            st.write("Connect users with remote assistance and digital help services.")
            st.info("Remote support module ready for demonstration.")
        with tab3:
            st.write("Capture and prepare basic digital photographs and ID documents.")
            st.info("Photo and ID module ready for demonstration.")

        if len(my_requests) > 0:
            st.markdown('<div class="section">Your Recent Requests</div>', unsafe_allow_html=True)
            for _, row in my_requests.head(3).iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.write(f"**{row['request_id']}** · {row['service']}")
                        st.caption(row['option'])
                    with c2:
                        st.markdown(
                            f'<span class="status-badge {status_class(row["status"])}">{row["status"]}</span>',
                            unsafe_allow_html=True
                        )

    # ---------------- SERVICES ----------------
    elif page == "🧑‍💻 Services":
        st.title("🧑‍💻 Digital Services")
        st.write("Choose the service you need. Your details are pulled from your account.")

        selected_service = st.selectbox("Select a service", list(SERVICE_OPTIONS.keys()))
        selected_option = st.selectbox("Choose what you need", SERVICE_OPTIONS[selected_service])

        st.markdown(f"""
        <div class="quick">
            <b>Estimated service fee:</b> ₹{SERVICE_FEES[selected_service]}
            &nbsp; • &nbsp; Final amount may vary
        </div>
        """, unsafe_allow_html=True)

        st.write("")

        with st.form("service_form"):
            st.subheader("Confirm Your Details")
            col1, col2 = st.columns(2)
            with col1:
                st.text_input("Full Name", value=user["name"], disabled=True)
                st.text_input("Mobile Number", value=user["mobile"], disabled=True)
            with col2:
                st.text_input("Village / Area", value=user["village"] or "", disabled=True)
                st.text_input("Preferred Language", value=user.get("preferred_language", "English"), disabled=True)

            notes = st.text_area(
                "Additional information",
                placeholder="Enter any details required for this service..."
            )

            submitted = st.form_submit_button("Submit Service Request", type="primary")

        if submitted:
            clean_service = selected_service.split(" ", 1)[1]
            request_id = create_request(user["id"], clean_service, selected_option, notes)
            st.success(f"Request submitted successfully! Your Request ID is **{request_id}**.")
            st.info("Please keep your Request ID for future reference. Check its status under 'My Requests'.")

    # ---------------- MY REQUESTS ----------------
    elif page == "📋 My Requests":
        st.title("📋 My Service Requests")

        df_requests = get_user_requests(user["id"])

        if df_requests.empty:
            st.info("No requests submitted yet. Go to Services to create one.")
        else:
            status_filter = st.multiselect(
                "Filter by status", STATUS_FLOW, default=STATUS_FLOW
            )
            df_requests = df_requests[df_requests["status"].isin(status_filter)]

            for _, row in df_requests.iterrows():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2, 4, 1])
                    with c1:
                        st.markdown(f"### {row['request_id']}")
                        st.caption(datetime.fromisoformat(row["created_at"]).strftime("%d %b %Y, %I:%M %p"))
                    with c2:
                        st.write(f"**Service:** {row['service']}")
                        st.write(f"**Option:** {row['option']}")
                        if row["notes"]:
                            st.write(f"**Notes:** {row['notes']}")
                    with c3:
                        st.markdown(
                            f'<span class="status-badge {status_class(row["status"])}">{row["status"]}</span>',
                            unsafe_allow_html=True
                        )


    elif page == "🛠️ Request Management" and can_manage_requests:
        st.title("🛠️ Request Management")
        st.caption("Manage and update resident service requests.")

        df_all = get_all_requests()

        if df_all.empty:
            st.info("No requests have been submitted yet.")
        else:
            if is_operator:
                # Operators work only on the active queue.
                # Completed/cancelled records remain in SQLite history.
                status_filter = st.multiselect(
                    "Active request status",
                    ["Submitted", "In Progress"],
                    default=["Submitted", "In Progress"],
                    key="operator_status_filter"
                )
            else:
                status_filter = st.multiselect(
                    "Filter by status",
                    STATUS_FLOW,
                    default=STATUS_FLOW,
                    key="admin_status_filter"
                )

            df_all = df_all[df_all["status"].isin(status_filter)]

            for _, row in df_all.iterrows():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2, 4, 2])
                    with c1:
                        st.markdown(f"### {row['request_id']}")
                        st.caption(datetime.fromisoformat(row["created_at"]).strftime("%d %b %Y, %I:%M %p"))
                    with c2:
                        st.write(f"**{row['name']}** · {row['mobile']} · {row['village']}")
                        st.write(f"**Service:** {row['service']} — {row['option']}")
                        if row["notes"]:
                            st.caption(f"Notes: {row['notes']}")
                    with c3:
                        new_status = st.selectbox(
                            "Update status",
                            STATUS_FLOW,
                            index=STATUS_FLOW.index(row["status"]) if row["status"] in STATUS_FLOW else 0,
                            key=f"status_{row['request_id']}"
                        )
                        if st.button("Save", key=f"save_{row['request_id']}"):
                            update_request_status(row["request_id"], new_status)

                            if new_status == "Completed":
                                # Show celebration first. The record stays in SQLite
                                # for history/analytics, but disappears from the
                                # active request queue after the animation.
                                completion_celebration(
                                    row["request_id"],
                                    row["service"]
                                )
                                st.rerun()
                            else:
                                st.success(
                                    f"{row['request_id']} updated to {new_status}"
                                )
                                st.rerun()

  
    elif page == "📊 Kiosk Analytics" and is_admin:
        st.title("📊 Kiosk Analytics")
        st.caption("Live dashboard for kiosk operators and administrators.")

        df = get_transactions_df()
        df["date"] = pd.to_datetime(df["date"])

        selected_services = st.multiselect(
            "Filter services", sorted(df["service"].unique()),
            default=sorted(df["service"].unique())
        )
        df = df[df["service"].isin(selected_services)].copy()

        if df.empty:
            st.warning("Select at least one service.")
            st.stop()

        total_revenue = df["amount"].sum()
        total_transactions = len(df)
        average_transaction = df["amount"].mean()
        total_users, total_requests, pending_requests = get_kiosk_stats()

        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.metric("Total Revenue", f"₹{total_revenue:,.0f}")
        with c2:
            st.metric("Transactions", total_transactions)
        with c3:
            st.metric("Avg. Transaction", f"₹{average_transaction:,.0f}")
        with c4:
            st.metric("Registered Residents", total_users)
        with c5:
            st.metric("Pending Requests", pending_requests)

        daily = df.groupby("date", as_index=False)["amount"].sum()
        fig = px.line(
            daily, x="date", y="amount", markers=True, title="📈 Daily Revenue",
            template="plotly_white"
        )
        fig.update_traces(
            line_width=4, marker_size=9,
            hovertemplate="₹%{y:,.0f}<extra></extra>"
        )
        fig.update_layout(
            xaxis_title="Date", yaxis_title="Revenue (₹)",
            hovermode="x unified", transition_duration=500,
            margin=dict(l=10, r=10, t=55, b=10)
        )
        st.plotly_chart(fig, width="stretch")

        col1, col2 = st.columns(2)
        with col1:
            service_revenue = (
                df.groupby("service", as_index=False)["amount"].sum()
                .sort_values("amount", ascending=False)
            )
            fig2 = px.bar(
                service_revenue, x="service", y="amount",
                title="💰 Revenue by Service", color="service",
                color_discrete_sequence=px.colors.qualitative.Bold,
                template="plotly_white"
            )
            fig2.update_layout(
                showlegend=False, transition_duration=500,
                margin=dict(l=10, r=10, t=55, b=10)
            )
            fig2.update_traces(
                marker_line_width=1.5,
                hovertemplate="%{x}<br>₹%{y:,.0f}<extra></extra>"
            )
            st.plotly_chart(fig2, width="stretch")
        with col2:
            service_count = df["service"].value_counts().reset_index()
            service_count.columns = ["service", "transactions"]
            fig3 = px.pie(
                service_count, names="service", values="transactions",
                title="🥧 Service Usage",
                color_discrete_sequence=px.colors.qualitative.Set3,
                hole=0.38
            )
            fig3.update_traces(
                textposition="inside", textinfo="percent+label",
                hovertemplate="%{label}<br>%{value} transactions<extra></extra>"
            )
            fig3.update_layout(
                transition_duration=500,
                margin=dict(l=10, r=10, t=55, b=10)
            )
            st.plotly_chart(fig3, width="stretch")

        df_requests_all = get_all_requests()
        if not df_requests_all.empty:
            status_counts = (
                df_requests_all["status"].value_counts()
                .reindex(STATUS_FLOW, fill_value=0)
                .reset_index()
            )
            status_counts.columns = ["status", "requests"]

            fig4 = px.bar(
                status_counts, x="status", y="requests",
                title="📋 Request Status Overview", color="status",
                color_discrete_sequence=px.colors.qualitative.Safe,
                template="plotly_white"
            )
            fig4.update_layout(
                showlegend=False, transition_duration=500,
                margin=dict(l=10, r=10, t=55, b=10)
            )
            fig4.update_traces(
                marker_line_width=1.5,
                hovertemplate="%{x}<br>%{y} requests<extra></extra>"
            )
            st.plotly_chart(fig4, width="stretch")

        st.subheader("Recent Transactions")
        styled_tx = (
            df.sort_values("date", ascending=False)
              .style
              .format({"amount": "₹{:,.0f}"})
              .background_gradient(subset=["amount"], cmap="PuBuGn")
              .set_properties(**{"padding": "8px"})
        )
        st.dataframe(styled_tx, width="stretch", hide_index=True)

        st.subheader("All Resident Requests")
        df_requests_all = get_all_requests()
        if df_requests_all.empty:
            st.info("No resident requests yet.")
        else:
            styled_requests = (
                df_requests_all.style
                .set_properties(**{"padding": "8px"})
            )
        st.dataframe(styled_requests, width="stretch", hide_index=True)

   
    elif page == "ℹ️ About Product":
        st.title("ℹ️ About GramSeva")
        st.markdown("""
        ### The Problem
        Rural communities may have limited convenient access to basic digital
        services such as printing, scanning, online applications and digital
        assistance.

        ### Our Solution
        **GramSeva** is a modular self-service kiosk that brings multiple essential
        digital services closer to the user, backed by a real account system so
        residents can track every request they make.

        ### Modular Design
        - 🖨️ Printing and scanning
        - 💳 Payment support
        - 📸 Photo and ID services
        - 📞 Tele-service
        - 🔐 Authenticated resident accounts

        ### Target Market
        - Rural communities
        - Remote areas
        - NGOs
        - Government programs
        - Local service operators
        - Regions with limited digital infrastructure

        ### Business Model
        **Hardware + Service Fees + Software Subscription + Institutional Partnerships**

        ### Global Potential
        The same concept can be adapted to communities around the world where
        essential digital services are difficult to access locally.
        """)
        st.success(
            "🎯 Goal: Make essential digital services accessible without requiring "
            "people to travel long distances for simple tasks."
        )

    st.divider()
    st.caption("GramSeva • Made by Jahnvi Srivastava")



if st.session_state.user is None:
    render_auth_screen()

else:
    render_main_app()

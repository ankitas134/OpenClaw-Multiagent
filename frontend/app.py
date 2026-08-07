import os
import time
import requests
import streamlit as st

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION & HIGH-CONTRAST DARK THEME
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="OpenClaw Platform - AI Agent Portal",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject High-Contrast CSS Theme
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Modern Dark Canvas with Mesh Gradient */
    .stApp {
        background: radial-gradient(circle at 50% 0%, #1e1b4b 0%, #0f172a 45%, #090d16 100%) !important;
        color: #f8fafc !important;
    }

    /* Glassmorphic Sidebar */
    [data-testid="stSidebar"] {
        background: rgba(15, 23, 42, 0.85) !important;
        backdrop-filter: blur(16px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    }

    [data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }

    /* Sleek Navigation Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px !important;
        background: rgba(30, 41, 59, 0.7) !important;
        backdrop-filter: blur(12px) !important;
        padding: 6px 10px !important;
        border-radius: 16px !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
    }

    .stTabs [data-baseweb="tab"] {
        color: #94a3b8 !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        padding: 10px 18px !important;
        border-radius: 10px !important;
        background: transparent !important;
        transition: all 0.2s ease !important;
    }

    .stTabs [aria-selected="true"] {
        color: #ffffff !important;
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.35) !important;
    }

    /* Buttons Styling */
    .stButton button {
        border-radius: 12px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }

    .stButton button[kind="primary"] {
        background: linear-gradient(135deg, #6366f1 0%, #4338ca 100%) !important;
        border: none !important;
        box-shadow: 0 4px 14px rgba(99, 102, 241, 0.3) !important;
    }

    .stButton button[kind="primary"]:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.45) !important;
    }

    .stButton button[kind="secondary"] {
        background: rgba(30, 41, 59, 0.7) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: #f8fafc !important;
    }

    .stButton button[kind="secondary"]:hover {
        background: rgba(51, 65, 85, 0.9) !important;
        border-color: rgba(129, 140, 248, 0.3) !important;
    }

    /* Chat Messages Premium Bubbles */
    [data-testid="stChatMessage"] {
        background: rgba(30, 41, 59, 0.75) !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px !important;
        padding: 16px 20px !important;
        margin-bottom: 12px !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2) !important;
    }

    [data-testid="stChatMessage"]:has([aria-label*="user"]), [data-testid="stChatMessage"]:nth-child(odd) {
        border-left: 3px solid #818cf8 !important;
    }

    [data-testid="stChatMessage"] * {
        color: #f8fafc !important;
        font-size: 15px !important;
        line-height: 1.6 !important;
    }

    /* Expanders & Forms */
    .stExpander {
        background: rgba(30, 41, 59, 0.6) !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px !important;
        overflow: hidden !important;
    }

    /* Input Fields */
    .stTextInput input, .stTextArea textarea, div[data-baseweb="select"] > div {
        background: rgba(15, 23, 42, 0.8) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 10px !important;
    }

    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #818cf8 !important;
        box-shadow: 0 0 10px rgba(129, 140, 248, 0.25) !important;
    }

    /* Header Banner */
    .claw-header {
        background: linear-gradient(135deg, #3730a3 0%, #5b21b6 50%, #1e40af 100%);
        border: 1px solid rgba(255, 255, 255, 0.15);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
        border-radius: 18px;
        padding: 20px 28px;
        margin-bottom: 24px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    /* Status Badges */
    .badge-running {
        background: linear-gradient(135deg, #059669 0%, #10b981 100%);
        color: #ffffff !important;
        padding: 5px 16px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 0.5px;
        box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
    }

    .badge-pending {
        background: linear-gradient(135deg, #d97706 0%, #f59e0b 100%);
        color: #ffffff !important;
        padding: 5px 16px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 700;
        box-shadow: 0 2px 8px rgba(245, 158, 11, 0.3);
    }

    .badge-stopped {
        background: linear-gradient(135deg, #475569 0%, #64748b 100%);
        color: #ffffff !important;
        padding: 5px 16px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 700;
    }

    .badge-starting {
        background: linear-gradient(135deg, #0284c7 0%, #0ea5e9 100%);
        color: #ffffff !important;
        padding: 5px 16px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 700;
        box-shadow: 0 2px 8px rgba(14, 165, 233, 0.3);
    }

    .badge-stopping {
        background: linear-gradient(135deg, #b45309 0%, #d97706 100%);
        color: #ffffff !important;
        padding: 5px 16px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 700;
        box-shadow: 0 2px 8px rgba(217, 119, 6, 0.3);
    }

    .badge-failed {
        background: linear-gradient(135deg, #b91c1c 0%, #ef4444 100%);
        color: #ffffff !important;
        padding: 5px 16px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 700;
        box-shadow: 0 2px 8px rgba(239, 68, 68, 0.3);
    }

    .badge-devmode {
        background: linear-gradient(135deg, #7e22ce 0%, #a855f7 100%);
        color: #ffffff !important;
        padding: 5px 16px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 700;
        box-shadow: 0 2px 8px rgba(168, 85, 247, 0.3);
    }

    /* Hide Streamlit Chrome */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# SESSION STATE RECOVERY
# -----------------------------------------------------------------------------
if "token" not in st.session_state:
    st.session_state["token"] = None
if "user" not in st.session_state:
    st.session_state["user"] = None
if "current_team" not in st.session_state:
    st.session_state["current_team"] = None

query_token = st.query_params.get("token")
if query_token and not st.session_state.get("token"):
    try:
        me_res = requests.get(f"{API_BASE}/api/auth/me", headers={"Authorization": f"Bearer {query_token}"})
        if me_res.status_code == 200:
            me_data = me_res.json()
            st.session_state["token"] = query_token
            st.session_state["user"] = {
                "id": me_data["id"],
                "email": me_data["email"],
                "name": me_data["name"],
                "teams": me_data.get("teams", [])
            }
            if me_data.get("teams") and not st.session_state.get("current_team"):
                st.session_state["current_team"] = me_data["teams"][0]
        else:
            st.query_params.clear()
    except Exception:
        pass

def get_headers():
    headers = {}
    if st.session_state["token"]:
        headers["Authorization"] = f"Bearer {st.session_state['token']}"
    return headers

def parse_response_error(res, default_msg: str) -> str:
    try:
        data = res.json()
        return data.get("detail", default_msg)
    except Exception:
        return f"{default_msg} (Server returned {res.status_code})"

def get_status_badge_info(status: str):
    """Maps a raw backend agent status to a (css_class, display_label, short_icon) tuple."""
    mapping = {
        "running": ("badge-running", "RUNNING", "[Running]"),
        "starting": ("badge-starting", "STARTING...", "[Starting]"),
        "stopping": ("badge-stopping", "STOPPING...", "[Stopping]"),
        "stopped": ("badge-stopped", "STOPPED", "[Stopped]"),
        "failed": ("badge-failed", "FAILED", "[Failed]"),
        "unsandboxed (dev mode)": ("badge-devmode", "DEV MODE", "[Dev Mode]"),
    }
    return mapping.get(status, ("badge-stopped", status.upper(), f"[{status.capitalize()}]"))

# -----------------------------------------------------------------------------
# AUTHENTICATION SCREEN (COMPACT & HIGH CONTRAST)
# -----------------------------------------------------------------------------
if not st.session_state["token"]:
    st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
    
    col_a, col_b, col_c = st.columns([1, 2.2, 1])

    with col_b:
        st.markdown("""
        <div style='text-align: center; margin-bottom: 24px;'>
            <h1 style='font-size: 38px; font-weight: 800; color: #818cf8;'>OpenClaw</h1>
            <p style='color: #cbd5e1; font-size: 15px; margin-top: 4px;'>Enterprise AI Agent Orchestration & RAG Platform</p>
        </div>
        """, unsafe_allow_html=True)

        auth_tab1, auth_tab2 = st.tabs(["Sign In", "Register Account"])

        with auth_tab1:
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            login_email = st.text_input("Email Address", key="login_email", placeholder="admin@example.com")
            login_password = st.text_input("Password", type="password", key="login_password", placeholder="••••••••")

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            if st.button("Sign In to Portal", type="primary", use_container_width=True):
                if not login_email or not login_password:
                    st.warning("Please fill in both Email Address and Password.")
                else:
                    try:
                        res = requests.post(f"{API_BASE}/api/auth/login", json={"email": login_email, "password": login_password})
                        if res.status_code == 200:
                            data = res.json()
                            st.session_state["token"] = data["access_token"]
                            st.session_state["user"] = data["user"]
                            st.query_params["token"] = data["access_token"]
                            
                            me_res = requests.get(f"{API_BASE}/api/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"})
                            if me_res.status_code == 200:
                                me_data = me_res.json()
                                st.session_state["user"]["teams"] = me_data["teams"]
                                if me_data["teams"]:
                                    # Prefer team with active agents if available
                                    selected_t = me_data["teams"][0]
                                    for t in me_data["teams"]:
                                        ag_res = requests.get(f"{API_BASE}/api/agents?teamId={t['teamId']}", headers={"Authorization": f"Bearer {data['access_token']}"})
                                        if ag_res.status_code == 200 and len(ag_res.json()) > 0:
                                            selected_t = t
                                            break
                                    st.session_state["current_team"] = selected_t
                            st.success("Successfully logged in!")
                            st.rerun()
                        else:
                            st.error(parse_response_error(res, "Login failed"))
                    except Exception as e:
                        st.error(f"Connection error: {e}")

        with auth_tab2:
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            reg_name = st.text_input("Full Name", key="reg_name", placeholder="John Doe")
            reg_email = st.text_input("Email Address", key="reg_email", placeholder="john@company.com")
            reg_password = st.text_input("Password", type="password", key="reg_password", placeholder="Create strong password")

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            if st.button("Register New Account", use_container_width=True):
                if not reg_name or not reg_email or not reg_password:
                    st.warning("Please complete all registration fields.")
                else:
                    try:
                        res = requests.post(f"{API_BASE}/api/auth/register", json={"name": reg_name, "email": reg_email, "password": reg_password})
                        if res.status_code in [200, 201]:
                            st.success("Registration successful! Switch to 'Sign In' tab to log in.")
                        else:
                            st.error(parse_response_error(res, "Registration failed"))
                    except Exception as e:
                        st.error(f"Connection error: {e}")

    st.stop()

# -----------------------------------------------------------------------------
# MAIN PORTAL INTERFACE
# -----------------------------------------------------------------------------
user = st.session_state["user"]
teams = user.get("teams", [])

# Sidebar Navigation
with st.sidebar:
    st.markdown("""
    <div style='display: flex; align-items: center; gap: 12px; margin-bottom: 16px;'>
        <div style='font-size: 24px; font-weight: 800; color: #818cf8;'>[OC]</div>
        <div>
            <h3 style='margin:0; font-weight: 800; color: #ffffff;'>OpenClaw</h3>
            <span style='color: #818cf8; font-size: 13px; font-weight: 600;'>Python Platform</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"**{user['name']}**")
    st.markdown(f"`{user['email']}`")
    st.divider()

    # Fetch live team memberships for current user
    try:
        me_res = requests.get(f"{API_BASE}/api/auth/me", headers=get_headers())
        if me_res.status_code == 200:
            me_data = me_res.json()
            teams = me_data.get("teams", [])
            st.session_state["user"]["teams"] = teams
    except Exception:
        pass

    if teams:
        team_options = {}
        for t in teams:
            role_lbl = t.get('role', 'member').upper()
            label = f"{t['name']} ({role_lbl} - #{t['teamId'][:4]})"
            team_options[label] = t
        
        # If current_team has 0 agents, auto-switch to team with agents
        cur_t = st.session_state.get("current_team")
        if cur_t:
            ag_check = requests.get(f"{API_BASE}/api/agents?teamId={cur_t['teamId']}", headers=get_headers())
            if ag_check.status_code == 200 and len(ag_check.json()) == 0:
                for t in teams:
                    if t["teamId"] != cur_t["teamId"]:
                        other_check = requests.get(f"{API_BASE}/api/agents?teamId={t['teamId']}", headers=get_headers())
                        if other_check.status_code == 200 and len(other_check.json()) > 0:
                            st.session_state["current_team"] = t
                            cur_t = t
                            break

        cur_team_id = st.session_state.get("current_team", {}).get("teamId") if st.session_state.get("current_team") else None
        cur_t_idx = 0
        for idx, (tname, tval) in enumerate(team_options.items()):
            if tval["teamId"] == cur_team_id:
                cur_t_idx = idx
                break

        opt_keys = list(team_options.keys())

        selected_team_name = st.selectbox(
            "Active Team Workspace",
            options=opt_keys,
            index=cur_t_idx
        )
        st.session_state["current_team"] = team_options[selected_team_name]
        
        # Sidebar Chat History List (ChatGPT Style)
        t_id = st.session_state["current_team"]["teamId"]
        sb_agents_res = requests.get(f"{API_BASE}/api/agents?teamId={t_id}", headers=get_headers())
        sb_agents = sb_agents_res.json() if sb_agents_res.status_code == 200 else []
        
        if sb_agents:
            st.markdown("---")
            st.markdown("### Chat Conversations")
            
            # Target agent selector in sidebar if multiple agents
            sb_agent_names = {a["name"]: a["id"] for a in sb_agents}
            
            # Sync default index with session_state
            cur_agent_id = st.session_state.get("selected_agent_id", sb_agents[0]["id"])
            cur_sb_index = 0
            for idx, (aname, aid) in enumerate(sb_agent_names.items()):
                if aid == cur_agent_id:
                    cur_sb_index = idx
                    break

            sb_selected_agent_name = st.selectbox("Active Agent", options=list(sb_agent_names.keys()), index=cur_sb_index, key="sb_active_agent_sel")
            sb_agent_id = sb_agent_names[sb_selected_agent_name]
            st.session_state["selected_agent_id"] = sb_agent_id
            
            # New Chat Button
            if st.button("+ New Conversation", key="sb_new_chat_btn", use_container_width=True, type="primary"):
                new_th = f"thread_{int(time.time())}"
                st.session_state[f"active_thread_{sb_agent_id}"] = new_th
                st.rerun()

            # List existing threads in sidebar
            threads_res = requests.get(f"{API_BASE}/api/agents/{sb_agent_id}/threads", headers=get_headers())
            sb_threads = threads_res.json() if threads_res.status_code == 200 else []
            if "main" not in sb_threads:
                sb_threads.insert(0, "main")

            active_th = st.session_state.get(f"active_thread_{sb_agent_id}", "main")
            if active_th not in sb_threads:
                sb_threads.insert(1, active_th)
            st.session_state[f"active_thread_{sb_agent_id}"] = active_th
            
            for th in sb_threads[:10]:
                col_th_btn, col_del_btn = st.columns([3.8, 1.2])
                with col_th_btn:
                    label = "Main" if th == "main" else f"{th.replace('thread_', 'Chat #')}"
                    is_active = (th == active_th)
                    btn_type = "primary" if is_active else "secondary"
                    if st.button(label, key=f"sb_th_{th}_{sb_agent_id}", use_container_width=True, type=btn_type):
                        st.session_state[f"active_thread_{sb_agent_id}"] = th
                        st.rerun()
                with col_del_btn:
                    if st.button("Delete", key=f"del_th_{th}_{sb_agent_id}", help="Delete Chat Thread"):
                        requests.delete(f"{API_BASE}/api/agents/{sb_agent_id}/threads/{th}", headers=get_headers())
                        if st.session_state.get(f"active_thread_{sb_agent_id}") == th:
                            st.session_state[f"active_thread_{sb_agent_id}"] = "main"
                        st.rerun()
    else:
        st.warning("No active team found.")

    st.divider()

    if st.button("Sign Out", type="secondary", use_container_width=True):
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()

current_team = st.session_state["current_team"]
if not current_team:
    st.error("Please select a team from the sidebar.")
    st.stop()

team_id = current_team["teamId"]

# Workspace Top Banner
st.markdown(f"""
<div class='claw-header'>
    <div>
        <h2>Team Workspace: {current_team['name']}</h2>
        <span style='color: #e0e7ff; font-size: 14px;'>Role: <b>{current_team.get('role', 'owner').upper()}</b> | Execution Mode: <b>Docker Sandboxed</b></span>
    </div>
    <div>
        <span style='background: rgba(255,255,255,0.2); color: white; padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: 700;'>
            Groq Llama-3.3 Engine & Whisper Voice STT
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

# Main Navigation Tabs
tab_agents, tab_docs, tab_team, tab_assistant, tab_audit = st.tabs([
    "Agent Hub", 
    "Document Library", 
    "Team Guidelines", 
    "Context Assistant", 
    "Audit Logs"
])

# -----------------------------------------------------------------------------
# TAB 1: AGENT HUB
# -----------------------------------------------------------------------------
with tab_agents:
    col_list, col_detail = st.columns([1, 2.2])

    with col_list:
        st.subheader("Your Team Agents")

        with st.expander("+ Create New Agent", expanded=False):
            with st.form("create_agent_form"):
                new_agent_name = st.text_input("Agent Name", placeholder="e.g. Finance Assistant")
                new_agent_task = st.text_area("Task Context / Goal", placeholder="Summarize financial reports.", height=80)
                new_agent_vis = st.selectbox("Visibility", ["team", "personal"])
                
                docs_res = requests.get(f"{API_BASE}/api/documents/{team_id}", headers=get_headers())
                available_docs = docs_res.json() if docs_res.status_code == 200 else []
                doc_map = {d["filename"]: d["id"] for d in available_docs}
                selected_doc_names = st.multiselect("Attach Reference Documents", options=list(doc_map.keys()))

                submit_create = st.form_submit_button("Spin Up Agent", use_container_width=True)

                if submit_create and new_agent_name:
                    selected_doc_ids = [doc_map[name] for name in selected_doc_names]
                    payload = {
                        "teamId": team_id,
                        "name": new_agent_name,
                        "taskContext": new_agent_task,
                        "visibility": new_agent_vis,
                        "documentIds": selected_doc_ids
                    }
                    c_res = requests.post(f"{API_BASE}/api/agents", json=payload, headers=get_headers())
                    if c_res.status_code in [200, 201, 202]:
                        st.success(f"Agent '{new_agent_name}' created!")
                        st.rerun()
                    else:
                        st.error(parse_response_error(c_res, "Failed to create agent."))

        # List Agents
        agents_res = requests.get(f"{API_BASE}/api/agents?teamId={team_id}", headers=get_headers())
        agents_list = agents_res.json() if agents_res.status_code == 200 else []

        if not agents_list:
            st.info("No agents created yet. Click '+ Create New Agent' above!")
            selected_agent_id = None
        else:
            agent_map = {}
            for a in agents_list:
                _, _, status_icon = get_status_badge_info(a['status'])
                agent_map[f"{status_icon} {a['name']} ({a['status']})"] = a["id"]
            
            default_id = st.session_state.get("selected_agent_id", agents_list[0]["id"])
            default_index = 0
            for idx, (lbl, aid) in enumerate(agent_map.items()):
                if aid == default_id:
                    default_index = idx
                    break

            selected_agent_label = st.radio("Select Agent to Manage", options=list(agent_map.keys()), index=default_index, key="hub_agent_radio")
            selected_agent_id = agent_map[selected_agent_label]
            st.session_state["selected_agent_id"] = selected_agent_id

    with col_detail:
        if selected_agent_id:
            a_res = requests.get(f"{API_BASE}/api/agents/{selected_agent_id}", headers=get_headers())
            if a_res.status_code == 200:
                agent = a_res.json()

                status_class, status_label, _ = get_status_badge_info(agent['status'])
                
                st.markdown(f"""
                <div style='display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px;'>
                    <h2 style='margin:0; font-size: 26px; font-weight: 700; color: #ffffff;'>{agent['name']}</h2>
                    <div>
                        <span class='{status_class}'>{status_label}</span>
                        <span style='background: rgba(255,255,255,0.12); color: #ffffff; padding: 4px 12px; border-radius: 12px; font-size: 13px; font-weight: 600; margin-left: 8px;'>
                            {agent['visibility'].capitalize()}
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Task Context Brief
                with st.expander("View Operational Task Brief (MEMORY.md)", expanded=False):
                    if agent['taskContext']:
                        st.markdown(agent['taskContext'])
                    else:
                        st.caption("No specific task context specified for this agent.")

                # Sandbox Controls & Visibility Toggle
                col_btn1, col_btn2, col_btn3 = st.columns(3)
                with col_btn1:
                    if st.button("Start Sandbox Container", key="start_btn", use_container_width=True, type="primary"):
                        st_res = requests.post(f"{API_BASE}/api/agents/{selected_agent_id}/start", headers=get_headers())
                        if st_res.status_code in [200, 202]:
                            st.success("Sandbox container spinup queued!")
                            st.rerun()
                        else:
                            st.error(parse_response_error(st_res, "Failed to start agent."))
                with col_btn2:
                    if st.button("Stop Sandbox Container", key="stop_btn", use_container_width=True):
                        sp_res = requests.post(f"{API_BASE}/api/agents/{selected_agent_id}/stop", headers=get_headers())
                        if sp_res.status_code in [200, 202]:
                            st.warning("Stop signal queued.")
                            st.rerun()
                        else:
                            st.error(parse_response_error(sp_res, "Failed to stop agent."))
                with col_btn3:
                    if agent['visibility'] == 'personal':
                        if st.button("Share Agent with Team", key="share_team_btn", use_container_width=True):
                            v_res = requests.patch(f"{API_BASE}/api/agents/{selected_agent_id}/visibility", json={"visibility": "team"}, headers=get_headers())
                            if v_res.status_code == 200:
                                st.success("Agent is now shared with team!")
                                st.rerun()
                            else:
                                st.error(parse_response_error(v_res, "Failed to update visibility."))
                    else:
                        if st.button("Make Agent Personal (Private)", key="make_priv_btn", use_container_width=True):
                            v_res = requests.patch(f"{API_BASE}/api/agents/{selected_agent_id}/visibility", json={"visibility": "personal"}, headers=get_headers())
                            if v_res.status_code == 200:
                                st.info("Agent is now private to you.")
                                st.rerun()
                            else:
                                st.error(parse_response_error(v_res, "Failed to update visibility."))

                st.divider()

                # Active Chat Thread View (Controlled via Sidebar ChatGPT List)
                th_key = f"active_thread_{selected_agent_id}"
                active_thread_id = st.session_state.get(th_key, "main")
                
                col_head1, col_head2 = st.columns([3.2, 1])
                with col_head1:
                    display_th = "Main Conversation" if active_thread_id == "main" else active_thread_id.replace("thread_", "Chat #")
                    st.subheader(f"Conversation: {display_th}")
                with col_head2:
                    st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
                    if st.button("Delete Chat", key=f"del_hdr_{selected_agent_id}_{active_thread_id}", type="secondary", use_container_width=True):
                        requests.delete(f"{API_BASE}/api/agents/{selected_agent_id}/threads/{active_thread_id}", headers=get_headers())
                        st.session_state[th_key] = "main"
                        st.rerun()

                msgs_res = requests.get(f"{API_BASE}/api/agents/{selected_agent_id}/messages?threadId={active_thread_id}", headers=get_headers())
                messages = msgs_res.json() if msgs_res.status_code == 200 else []

                chat_container = st.container(height=320)
                with chat_container:
                    if not messages:
                        st.info("Send a message below to start chatting with this agent.")
                    else:
                        for m in messages:
                            with st.chat_message(m["sender"]):
                                st.write(m["text"])

                # Live Voice-to-Text Speech Input Widget
                with st.expander("Live Microphone Speech Input (Groq Whisper STT)", expanded=True):
                    st.caption("Click the microphone button below to record your voice live, then click Transcribe.")
                    
                    audio_bytes = None
                    if hasattr(st, "audio_input"):
                        rec = st.audio_input("Live Microphone Recorder", key=f"audio_input_mic_{selected_agent_id}_{active_thread_id}")
                        if rec:
                            audio_bytes = rec.getvalue()
                    else:
                        try:
                            from audio_recorder_streamlit import audio_recorder
                            audio_bytes = audio_recorder(text="Click Mic to Record Voice", recording_color="#ef4444", neutral_color="#6366f1", icon_name="microphone", icon_size="2x")
                        except Exception:
                            audio_bytes = None

                    if audio_bytes and len(audio_bytes) > 2000:
                        if st.button("Transcribe & Send Live Voice Message", type="primary", use_container_width=True, key=f"send_voice_{selected_agent_id}_{active_thread_id}"):
                            with st.spinner("Transcribing English speech via Groq Whisper..."):
                                try:
                                    files = {"file": ("recording.wav", audio_bytes, "audio/wav")}
                                    tr_res = requests.post(f"{API_BASE}/api/voice/transcribe", files=files, headers=get_headers())
                                    if tr_res.status_code == 200:
                                        transcribed_text = tr_res.json().get("text", "").strip()
                                        if transcribed_text:
                                            st.success(f"Recognized Speech: '{transcribed_text}'")
                                            # Send transcribed text as message
                                            post_res = requests.post(
                                                f"{API_BASE}/api/agents/{selected_agent_id}/messages",
                                                json={"text": transcribed_text, "threadId": active_thread_id},
                                                headers=get_headers()
                                            )
                                            if post_res.status_code in [200, 201, 202]:
                                                # Poll for LLM response
                                                start_time = time.time()
                                                initial_count = len(messages)
                                                while time.time() - start_time < 6.0:
                                                    time.sleep(0.5)
                                                    poll_res = requests.get(f"{API_BASE}/api/agents/{selected_agent_id}/messages?threadId={active_thread_id}", headers=get_headers())
                                                    if poll_res.status_code == 200:
                                                        current_msgs = poll_res.json()
                                                        if len(current_msgs) > initial_count + 1 or (current_msgs and current_msgs[-1]["sender"] == "agent"):
                                                            break
                                                st.rerun()
                                        else:
                                            st.warning("No speech detected. Please speak clearly into your microphone.")
                                    else:
                                        st.error(parse_response_error(tr_res, "Speech transcription failed."))
                                except Exception as ex:
                                    st.error(f"Voice transcription error: {ex}")

                is_agent_running = (agent['status'] == 'running')
                if not is_agent_running:
                    st.warning("Agent sandbox container is currently STOPPED. Click 'Start Sandbox Container' above to enable chat execution.")

                chat_placeholder = "Ask a question or issue a command..." if is_agent_running else "Agent sandbox container is STOPPED. Click 'Start Sandbox Container' above to chat."
                
                if prompt := st.chat_input(chat_placeholder, disabled=not is_agent_running):
                    post_res = requests.post(
                        f"{API_BASE}/api/agents/{selected_agent_id}/messages",
                        json={"text": prompt, "threadId": active_thread_id},
                        headers=get_headers()
                    )
                    if post_res.status_code in [200, 201, 202]:
                        # Poll for up to 40 seconds for the Celery LLM worker reply to finish
                        with st.spinner("Agent is thinking..."):
                            start_time = time.time()
                            initial_count = len(messages)
                            got_reply = False
                            while time.time() - start_time < 40.0:
                                time.sleep(0.5)
                                poll_res = requests.get(f"{API_BASE}/api/agents/{selected_agent_id}/messages?threadId={active_thread_id}", headers=get_headers())
                                if poll_res.status_code == 200:
                                    current_msgs = poll_res.json()
                                    if len(current_msgs) > initial_count + 1 or (current_msgs and current_msgs[-1]["sender"] == "agent"):
                                        got_reply = True
                                        break
                            if not got_reply:
                                st.warning("The agent is taking longer than usual to respond. It will appear once ready — try refreshing shortly.")
                        st.rerun()
                    else:
                        st.error(parse_response_error(post_res, "Failed to send message."))

# -----------------------------------------------------------------------------
# TAB 2: DOCUMENT LIBRARY
# -----------------------------------------------------------------------------
with tab_docs:
    st.header("Document Knowledge Base")
    st.caption("Upload company policies, PDFs, and text files for RAG grounding.")
    
    col_up, col_dlist = st.columns([1, 1.8])

    with col_up:
        with st.form("upload_doc_form"):
            st.subheader("Upload New File")
            uploaded_file = st.file_uploader("Choose PDF, DOCX, TXT, or MD", type=["pdf", "docx", "txt", "md"])
            doc_vis = st.selectbox("Visibility", ["team", "personal"], key="doc_vis_sel")
            submit_up = st.form_submit_button("Upload & Process Embeddings", use_container_width=True)

            if submit_up:
                if uploaded_file:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type or "application/octet-stream")}
                    data = {"visibility": doc_vis}
                    up_res = requests.post(f"{API_BASE}/api/documents/{team_id}", files=files, data=data, headers=get_headers())
                    if up_res.status_code in [200, 201, 202]:
                        st.success(f"Uploaded '{uploaded_file.name}'! Vector extraction queued.")
                        st.rerun()
                    else:
                        st.error(parse_response_error(up_res, "Upload failed."))
                else:
                    st.warning("Please select a file to upload first.")

    with col_dlist:
        st.subheader("Stored Reference Documents")
        d_res = requests.get(f"{API_BASE}/api/documents/{team_id}", headers=get_headers())
        docs_data = d_res.json() if d_res.status_code == 200 else []

        if not docs_data:
            st.info("No documents uploaded for this team yet.")
        else:
            for doc in docs_data:
                with st.expander(f"{doc['filename']}  — Status: `{doc['extractionStatus']}`"):
                    st.write(f"**Size**: {doc['sizeBytes']} bytes | **Visibility**: `{doc['visibility']}`")
                    st.write(f"**Uploaded**: {doc['createdAt']}")
                    if st.button("Delete Document", key=f"del_{doc['id']}", type="secondary"):
                        del_res = requests.delete(f"{API_BASE}/api/documents/{team_id}/{doc['id']}", headers=get_headers())
                        if del_res.status_code in [200, 204]:
                            st.warning(f"Deleted {doc['filename']}")
                            st.rerun()
                        else:
                            st.error(parse_response_error(del_res, "Delete failed."))

# -----------------------------------------------------------------------------
# TAB 3: TEAM GUIDELINES
# -----------------------------------------------------------------------------
with tab_team:
    st.header(f"Standing Team Guidelines ({current_team['name']})")
    
    team_detail_res = requests.get(f"{API_BASE}/api/teams/{team_id}", headers=get_headers())
    if team_detail_res.status_code == 200:
        team_data = team_detail_res.json()
        
        st.info("Standing guidelines defined here are automatically injected into all agents operating under this team.")
        
        new_context = st.text_area("Standing Team Context Guidelines (Markdown)", value=team_data["contextMd"], height=220)
        if st.button("Save Standing Guidelines", type="primary"):
            u_res = requests.patch(f"{API_BASE}/api/teams/{team_id}/context", json={"context_md": new_context}, headers=get_headers())
            if u_res.status_code == 200:
                st.success("Team guidelines updated successfully!")
                st.rerun()
            else:
                st.error(parse_response_error(u_res, "Failed to save guidelines."))

        st.divider()
        st.subheader("Invite Team Members (Share Access to Agents)")
        st.caption("Add team members by email so multiple users can access and collaborate on this team's AI Agents.")
        
        with st.form("invite_member_form"):
            invite_email = st.text_input("User Email Address", placeholder="colleague@company.com")
            invite_role = st.selectbox("Role", ["member", "admin"])
            submit_invite = st.form_submit_button("Add Member to Team Workspace", type="primary")

            if submit_invite and invite_email:
                inv_res = requests.post(f"{API_BASE}/api/teams/{team_id}/members", json={"email": invite_email, "role": invite_role}, headers=get_headers())
                if inv_res.status_code == 200:
                    st.success(inv_res.json().get("message", "Member added!"))
                    st.rerun()
                else:
                    st.error(parse_response_error(inv_res, "Failed to add team member."))

# -----------------------------------------------------------------------------
# TAB 4: CONTEXT ASSISTANT
# -----------------------------------------------------------------------------
with tab_assistant:
    st.header("Context Brief Assistant")
    st.caption("Fill out the intake questionnaire to compile a structured MEMORY.md brief.")

    col_ca1, col_ca2 = st.columns([1.2, 1])

    with col_ca1:
        with st.form("context_compiler_form"):
            ca_goal = st.text_input("1. Core Objective / Agent Goal", placeholder="e.g. Process expense claims and enforce travel budget limits")
            ca_docs = st.text_input("2. Reference Files / Knowledge Base", placeholder="e.g. q2-expense-policy.pdf, travel-allowance.docx")
            ca_constraints = st.text_input("3. Implementation Constraints", placeholder="e.g. Strict daily meal cap of $75, no international travel")
            ca_audience = st.text_input("4. Intended Team / Audience", value=current_team["name"])

            submit_ca = st.form_submit_button("Compile Brief (MEMORY.md)", type="primary", use_container_width=True)

            if submit_ca and ca_goal:
                ca_payload = {
                    "goal": ca_goal,
                    "docs": ca_docs,
                    "constraints": ca_constraints,
                    "audience": ca_audience
                }
                ca_res = requests.post(f"{API_BASE}/api/context-assistant/compile", json=ca_payload, headers=get_headers())
                if ca_res.status_code == 200:
                    st.session_state["compiled_brief"] = ca_res.json()["compiledMd"]
                    st.success("Brief compiled!")
                else:
                    st.error(parse_response_error(ca_res, "Compilation failed."))

    with col_ca2:
        if "compiled_brief" in st.session_state and st.session_state["compiled_brief"]:
            brief_md = st.session_state["compiled_brief"]
            st.subheader("Generated Brief Preview")
            with st.container(height=260):
                st.markdown(brief_md)

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            if st.button("Apply as Standing Team Context", use_container_width=True):
                u_res = requests.patch(f"{API_BASE}/api/teams/{team_id}/context", json={"context_md": brief_md}, headers=get_headers())
                if u_res.status_code == 200:
                    st.success("Applied to Team Context Guidelines!")
                    st.rerun()
                else:
                    st.error(parse_response_error(u_res, "Failed to update team context."))

            agents_res = requests.get(f"{API_BASE}/api/agents?teamId={team_id}", headers=get_headers())
            team_agents = agents_res.json() if agents_res.status_code == 200 else []
            if team_agents:
                agent_options = {a["name"]: a["id"] for a in team_agents}
                target_agent_name = st.selectbox("Apply to Agent", options=list(agent_options.keys()), key="ca_target_agent")
                if st.button("Apply as Agent Task Context", use_container_width=True):
                    target_id = agent_options[target_agent_name]
                    a_ctx_res = requests.patch(f"{API_BASE}/api/agents/{target_id}/context", json={"taskContext": brief_md}, headers=get_headers())
                    if a_ctx_res.status_code == 200:
                        st.success(f"Applied to agent '{target_agent_name}'!")
                        st.rerun()
                    else:
                        st.error(parse_response_error(a_ctx_res, "Failed to update agent task context."))

# -----------------------------------------------------------------------------
# TAB 5: AUDIT LOGS
# -----------------------------------------------------------------------------
with tab_audit:
    st.header(f"Governance Audit Trail ({current_team['name']})")
    
    audit_res = requests.get(f"{API_BASE}/api/audit-logs?teamId={team_id}", headers=get_headers())
    if audit_res.status_code == 200:
        audit_data = audit_res.json()
        if audit_data:
            st.dataframe(audit_data, use_container_width=True)
        else:
            st.info("No audit logs recorded for this team yet.")
            
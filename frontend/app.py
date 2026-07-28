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
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject High-Contrast CSS Theme
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Force App Dark Background */
    .stApp {
        background: #0f172a !important;
        color: #f8fafc !important;
    }

    /* Sidebar Styling & High Contrast Colors */
    [data-testid="stSidebar"] {
        background-color: #1e293b !important;
        border-right: 1px solid rgba(255, 255, 255, 0.1) !important;
    }

    [data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }

    /* Navigation Tabs High Contrast */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px !important;
        background-color: #1e293b !important;
        padding: 8px 12px !important;
        border-radius: 12px !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
    }

    .stTabs [data-baseweb="tab"] {
        color: #94a3b8 !important;
        font-weight: 600 !important;
        font-size: 15px !important;
        padding: 8px 16px !important;
        border-radius: 8px !important;
        background: transparent !important;
    }

    .stTabs [aria-selected="true"] {
        color: #ffffff !important;
        background-color: #6366f1 !important;
    }

    /* Radio Buttons & Text Labels High Contrast */
    [data-testid="stRadio"] label, [data-testid="stRadio"] p, p, span, label, h1, h2, h3, h4, h5, h6 {
        color: #f8fafc !important;
    }

    /* Expanders High Contrast */
    .stExpander {
        background-color: #1e293b !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 12px !important;
    }

    .stExpander * {
        color: #f8fafc !important;
    }

    /* Chat Messages High Contrast Styling */
    [data-testid="stChatMessage"] {
        background-color: #1e293b !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 12px !important;
        padding: 12px 16px !important;
        margin-bottom: 8px !important;
    }

    [data-testid="stChatMessage"] * {
        color: #f8fafc !important;
    }

    /* Form Inputs High Contrast */
    .stTextInput input, .stTextArea textarea, .stSelectbox select, div[data-baseweb="select"] > div {
        background-color: #1e293b !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 8px !important;
    }

    .stTextInput input::placeholder, .stTextArea textarea::placeholder {
        color: #94a3b8 !important;
    }

    /* Card Containers */
    .claw-card {
        background: #1e293b;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
    }

    /* Header Banner */
    .claw-header {
        background: linear-gradient(90deg, #4f46e5 0%, #7c3aed 50%, #2563eb 100%);
        border-radius: 14px;
        padding: 18px 24px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    .claw-header h2 {
        color: #ffffff !important;
        margin: 0 !important;
        font-weight: 700 !important;
    }

    /* Status Badges */
    .badge-running {
        background-color: #10b981;
        color: #ffffff !important;
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 700;
        display: inline-block;
    }

    .badge-pending {
        background-color: #f59e0b;
        color: #ffffff !important;
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 700;
        display: inline-block;
    }

    .badge-stopped {
        background-color: #64748b;
        color: #ffffff !important;
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 700;
        display: inline-block;
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
            if me_data.get("teams"):
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

# -----------------------------------------------------------------------------
# AUTHENTICATION SCREEN (COMPACT & HIGH CONTRAST)
# -----------------------------------------------------------------------------
if not st.session_state["token"]:
    st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
    
    col_a, col_b, col_c = st.columns([1, 2.2, 1])

    with col_b:
        st.markdown("""
        <div style='text-align: center; margin-bottom: 24px;'>
            <h1 style='font-size: 38px; font-weight: 800; color: #818cf8;'>🤖 OpenClaw</h1>
            <p style='color: #cbd5e1; font-size: 15px; margin-top: 4px;'>Enterprise AI Agent Orchestration & RAG Platform</p>
        </div>
        """, unsafe_allow_html=True)

        auth_tab1, auth_tab2 = st.tabs(["🔐 Sign In", "📝 Register Account"])

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
                                    st.session_state["current_team"] = me_data["teams"][0]
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
        <div style='font-size: 32px;'>🤖</div>
        <div>
            <h3 style='margin:0; font-weight: 800; color: #ffffff;'>OpenClaw</h3>
            <span style='color: #818cf8; font-size: 13px; font-weight: 600;'>Python Platform</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"👤 **{user['name']}**")
    st.markdown(f"📧 `{user['email']}`")
    st.divider()

    if teams:
        team_options = {t["name"]: t for t in teams}
        selected_team_name = st.selectbox(
            "Active Team Workspace",
            options=list(team_options.keys()),
            index=0
        )
        st.session_state["current_team"] = team_options[selected_team_name]
    else:
        st.warning("No active team found.")

    st.divider()

    if st.button("🚪 Sign Out", type="secondary", use_container_width=True):
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
        <h2>🏢 Team Workspace: {current_team['name']}</h2>
        <span style='color: #e0e7ff; font-size: 14px;'>Role: <b>{current_team.get('role', 'owner').upper()}</b> | Execution Mode: <b>Docker Sandboxed</b></span>
    </div>
    <div>
        <span style='background: rgba(255,255,255,0.2); color: white; padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: 700;'>
            ⚡ Groq Llama-3.3 Engine
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

# Main Navigation Tabs
tab_agents, tab_docs, tab_team, tab_assistant, tab_audit = st.tabs([
    "🤖 Agent Hub", 
    "📁 Document Library", 
    "👥 Team Guidelines", 
    "✨ Context Assistant",
    "📜 Audit Logs"
])

# -----------------------------------------------------------------------------
# TAB 1: AGENT HUB
# -----------------------------------------------------------------------------
with tab_agents:
    col_list, col_detail = st.columns([1, 2.2])

    with col_list:
        st.subheader("Your Team Agents")

        with st.expander("➕ Create New Agent", expanded=False):
            with st.form("create_agent_form"):
                new_agent_name = st.text_input("Agent Name", placeholder="e.g. Finance Assistant")
                new_agent_task = st.text_area("Task Context / Goal", placeholder="Summarize financial reports.", height=80)
                new_agent_vis = st.selectbox("Visibility", ["team", "personal"])
                
                docs_res = requests.get(f"{API_BASE}/api/documents/{team_id}", headers=get_headers())
                available_docs = docs_res.json() if docs_res.status_code == 200 else []
                doc_map = {d["filename"]: d["id"] for d in available_docs}
                selected_doc_names = st.multiselect("Attach Reference Documents", options=list(doc_map.keys()))

                submit_create = st.form_submit_button("🚀 Spin Up Agent", use_container_width=True)

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
            st.info("No agents created yet. Click '➕ Create New Agent' above!")
            selected_agent_id = None
        else:
            agent_map = {}
            for a in agents_list:
                status_icon = "🟢" if a['status'] == 'running' else ("🟡" if a['status'] == 'pending' else "⚪")
                agent_map[f"{status_icon} {a['name']} ({a['status']})"] = a["id"]
            
            selected_agent_label = st.radio("Select Agent to Manage", options=list(agent_map.keys()))
            selected_agent_id = agent_map[selected_agent_label]

    with col_detail:
        if selected_agent_id:
            a_res = requests.get(f"{API_BASE}/api/agents/{selected_agent_id}", headers=get_headers())
            if a_res.status_code == 200:
                agent = a_res.json()

                status_class = f"badge-{agent['status']}" if agent['status'] in ['running', 'pending', 'stopped'] else "badge-stopped"
                
                st.markdown(f"""
                <div style='display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px;'>
                    <h2 style='margin:0; font-size: 26px; font-weight: 700; color: #ffffff;'>🤖 {agent['name']}</h2>
                    <div>
                        <span class='{status_class}'>{agent['status'].upper()}</span>
                        <span style='background: rgba(255,255,255,0.12); color: #ffffff; padding: 4px 12px; border-radius: 12px; font-size: 13px; font-weight: 600; margin-left: 8px;'>
                            {agent['visibility'].capitalize()}
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Task Context Brief
                with st.expander("📄 View Operational Task Brief (MEMORY.md)", expanded=False):
                    if agent['taskContext']:
                        st.markdown(agent['taskContext'])
                    else:
                        st.caption("No specific task context specified for this agent.")

                # Sandbox Controls
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("▶ Start Sandbox Container", key="start_btn", use_container_width=True, type="primary"):
                        st_res = requests.post(f"{API_BASE}/api/agents/{selected_agent_id}/start", headers=get_headers())
                        if st_res.status_code in [200, 202]:
                            st.success("Sandbox container spinup queued!")
                            st.rerun()
                        else:
                            st.error(parse_response_error(st_res, "Failed to start agent."))
                with col_btn2:
                    if st.button("⏹ Stop Sandbox Container", key="stop_btn", use_container_width=True):
                        sp_res = requests.post(f"{API_BASE}/api/agents/{selected_agent_id}/stop", headers=get_headers())
                        if sp_res.status_code in [200, 202]:
                            st.warning("Stop signal queued.")
                            st.rerun()
                        else:
                            st.error(parse_response_error(sp_res, "Failed to stop agent."))

                st.divider()

                # Multi-Thread Chat
                st.subheader("💬 Interactive Chat Threads")
                
                threads_res = requests.get(f"{API_BASE}/api/agents/{selected_agent_id}/threads", headers=get_headers())
                existing_threads = threads_res.json() if threads_res.status_code == 200 else []
                if "main" not in existing_threads:
                    existing_threads.insert(0, "main")

                col_th1, col_th2 = st.columns([3, 1])
                with col_th1:
                    selected_thread = st.selectbox(
                        "Active Thread",
                        options=existing_threads,
                        key=f"thread_sel_{selected_agent_id}"
                    )
                with col_th2:
                    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                    if st.button("➕ New Thread", key=f"new_th_{selected_agent_id}", use_container_width=True):
                        new_th_name = f"thread_{int(time.time())}"
                        st.session_state[f"active_thread_{selected_agent_id}"] = new_th_name
                        st.rerun()

                active_thread_id = st.session_state.get(f"active_thread_{selected_agent_id}", selected_thread)

                msgs_res = requests.get(f"{API_BASE}/api/agents/{selected_agent_id}/messages?threadId={active_thread_id}", headers=get_headers())
                messages = msgs_res.json() if msgs_res.status_code == 200 else []

                chat_container = st.container(height=320)
                with chat_container:
                    if not messages:
                        st.info("👋 Send a message below to start chatting with this agent!")
                    else:
                        for m in messages:
                            avatar = "👤" if m["sender"] == "user" else "🤖"
                            with st.chat_message(m["sender"], avatar=avatar):
                                st.write(m["text"])

                if prompt := st.chat_input("Ask a question or issue a command..."):
                    post_res = requests.post(
                        f"{API_BASE}/api/agents/{selected_agent_id}/messages",
                        json={"text": prompt, "threadId": active_thread_id},
                        headers=get_headers()
                    )
                    if post_res.status_code in [200, 201, 202]:
                        st.rerun()
                    else:
                        st.error(parse_response_error(post_res, "Failed to send message."))

# -----------------------------------------------------------------------------
# TAB 2: DOCUMENT LIBRARY
# -----------------------------------------------------------------------------
with tab_docs:
    st.header("📁 Document Knowledge Base")
    st.caption("Upload company policies, PDFs, and text files for RAG grounding.")
    
    col_up, col_dlist = st.columns([1, 1.8])

    with col_up:
        with st.form("upload_doc_form"):
            st.subheader("Upload New File")
            uploaded_file = st.file_uploader("Choose PDF, DOCX, TXT, or MD", type=["pdf", "docx", "txt", "md"])
            doc_vis = st.selectbox("Visibility", ["team", "personal"], key="doc_vis_sel")
            submit_up = st.form_submit_button("📤 Upload & Process Embeddings", use_container_width=True)

            if submit_up:
                if uploaded_file:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
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
                with st.expander(f"📄 {doc['filename']}  — Status: `{doc['extractionStatus']}`"):
                    st.write(f"**Size**: {doc['sizeBytes']} bytes | **Visibility**: `{doc['visibility']}`")
                    st.write(f"**Uploaded**: {doc['createdAt']}")
                    if st.button("🗑️ Delete Document", key=f"del_{doc['id']}", type="secondary"):
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
    st.header(f"👥 Standing Team Guidelines ({current_team['name']})")
    
    team_detail_res = requests.get(f"{API_BASE}/api/teams/{team_id}", headers=get_headers())
    if team_detail_res.status_code == 200:
        team_data = team_detail_res.json()
        
        st.info("💡 Standing guidelines defined here are automatically injected into all agents operating under this team.")
        
        new_context = st.text_area("Standing Team Context Guidelines (Markdown)", value=team_data["contextMd"], height=220)
        if st.button("💾 Save Standing Guidelines", type="primary"):
            u_res = requests.patch(f"{API_BASE}/api/teams/{team_id}/context", json={"context_md": new_context}, headers=get_headers())
            if u_res.status_code == 200:
                st.success("Team guidelines updated successfully!")
                st.rerun()
            else:
                st.error(parse_response_error(u_res, "Failed to save guidelines."))

# -----------------------------------------------------------------------------
# TAB 4: CONTEXT ASSISTANT
# -----------------------------------------------------------------------------
with tab_assistant:
    st.header("✨ Context Brief Assistant")
    st.caption("Fill out the intake questionnaire to compile a structured MEMORY.md brief.")

    col_ca1, col_ca2 = st.columns([1.2, 1])

    with col_ca1:
        with st.form("context_compiler_form"):
            ca_goal = st.text_input("1. Core Objective / Agent Goal", placeholder="e.g. Process expense claims and enforce travel budget limits")
            ca_docs = st.text_input("2. Reference Files / Knowledge Base", placeholder="e.g. q2-expense-policy.pdf, travel-allowance.docx")
            ca_constraints = st.text_input("3. Implementation Constraints", placeholder="e.g. Strict daily meal cap of $75, no international travel")
            ca_audience = st.text_input("4. Intended Team / Audience", value=current_team["name"])

            submit_ca = st.form_submit_button("✨ Compile Brief (MEMORY.md)", type="primary", use_container_width=True)

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
            if st.button("📋 Apply as Standing Team Context", use_container_width=True):
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
                if st.button("🤖 Apply as Agent Task Context", use_container_width=True):
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
    st.header(f"📜 Governance Audit Trail ({current_team['name']})")
    
    audit_res = requests.get(f"{API_BASE}/api/audit-logs?teamId={team_id}", headers=get_headers())
    if audit_res.status_code == 200:
        audit_data = audit_res.json()
        if audit_data:
            st.dataframe(audit_data, use_container_width=True)
        else:
            st.info("No audit logs recorded for this team yet.")

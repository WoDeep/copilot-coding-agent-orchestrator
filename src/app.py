"""
Swaibian Agentic Pipeline
Modern web UI for managing automated AI development workflows
"""

import streamlit as st
import pandas as pd
import subprocess
import os
import base64
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent))

# Paths - PROJECT_ROOT is the main project directory (parent of src/)
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"
ENV_PATH = PROJECT_ROOT / ".env"
ASSETS_DIR = PROJECT_ROOT / "assets"
LOGO_PATH = ASSETS_DIR / "swaibian_white.png"
AVATAR_PATH = ASSETS_DIR / "swaibian_Avatar_white.png"
THANKYOU_PATH = ASSETS_DIR / "thankyou.jpg"

# Check if setup is needed
from setup_wizard import is_setup_complete, render_setup_wizard

if not is_setup_complete(CONFIG_PATH, ENV_PATH):
    # Run setup wizard
    render_setup_wizard(CONFIG_PATH, ENV_PATH)
    st.stop()

# Setup complete - import main components
from automation_engine import AutomationEngine, WorkflowState, QueueItem
from daemon import get_daemon_status, start_daemon, stop_daemon, DaemonStatus, CooldownManager

# Page config
st.set_page_config(
    page_title="Swaibian Agentic Pipeline",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Modern CSS styling
st.markdown("""
<style>
    /* Import modern font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global styles */
    .stApp {
        font-family: 'Inter', sans-serif;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    }
    
    [data-testid="stSidebar"] * {
        color: #e8e8e8 !important;
    }
    
    [data-testid="stSidebar"] code {
        background: rgba(102, 126, 234, 0.3) !important;
        color: #a5b4fc !important;
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
        font-weight: 500;
    }
    
    [data-testid="stSidebar"] .stButton button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border: none;
        border-radius: 8px;
        color: white !important;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    [data-testid="stSidebar"] .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
    
    /* Main header styling */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        color: white;
    }
    
    .main-header h1 {
        color: white !important;
        margin: 0;
        font-weight: 300;
        font-family: 'Helvetica Neue', 'Arial', sans-serif;
        letter-spacing: 0.02em;
        display: flex;
        align-items: baseline;
    }
    
    .main-header h1 img {
        align-self: flex-end;
            padding-bottom: 4px;
        margin-bottom: 4px;
    }
    
    .main-header p {
        color: rgba(255,255,255,0.8) !important;
        margin: 0.5rem 0 0 0;
    }
    
    /* Tip button styling */
    .tip-button {
        position: absolute;
        top: 1rem;
        right: 1rem;
        background: rgba(255,255,255,0.2);
        border: 1px solid rgba(255,255,255,0.3);
        border-radius: 8px;
        padding: 0.4rem 0.8rem;
        color: white;
        font-size: 0.85rem;
        cursor: pointer;
        transition: all 0.3s ease;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
    }
    
    .tip-button:hover {
        background: rgba(255,255,255,0.3);
        transform: translateY(-1px);
    }
    
    .main-header {
        position: relative;
    }
    
    /* Metric cards */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
        padding: 1rem;
        border-radius: 12px;
        border-left: 4px solid #667eea;
    }
    
    [data-testid="stMetric"] label {
        color: #64748b !important;
        font-weight: 500;
    }
    
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #1e293b !important;
        font-weight: 700;
    }
    
    /* Status badges */
    .status-running {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 500;
        display: inline-block;
    }
    
    .status-stopped {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 500;
        display: inline-block;
    }
    
    .status-ready {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 500;
        display: inline-block;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: #656565;
        border-radius: 8px 8px 0 0;
        padding: 0.75rem 1.5rem;
        font-weight: 500;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
    }
    
    /* Compact queue item buttons */
    div[data-testid="column"] .stButton > button {
        padding: 0.25rem 0.6rem !important;
        min-height: unset !important;
    }
    
    /* Card container */
    .issue-card {
        background: white;
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.75rem;
        border: 1px solid #e2e8f0;
        transition: all 0.2s ease;
    }
    
    .issue-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        border-color: #667eea;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background: #f8fafc;
        border-radius: 8px;
    }
    
    /* Button styling */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    
    /* Primary action button */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border: none;
    }
    
    /* Divider */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, #e2e8f0, transparent);
        margin: 1.5rem 0;
    }
    
    /* Logo container */
    .logo-container {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 1rem 0;
    }
    
    .logo-container img {
        height: 50px;
    }
    
    /* Hide default streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Workflow log styling */
    .workflow-event {
        padding: 0.5rem;
        border-left: 3px solid #667eea;
        margin-bottom: 0.5rem;
        background: #f8fafc;
        border-radius: 0 8px 8px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'engine' not in st.session_state:
    st.session_state.engine = AutomationEngine(config_path=str(CONFIG_PATH))
    st.session_state.connected = False
    st.session_state.automation_thread = None

engine: AutomationEngine = st.session_state.engine

# Get repo info from config
REPO_OWNER = engine.config.get('github', {}).get('owner', '')
REPO_NAME = engine.config.get('github', {}).get('repo', '')
REPO_FULL = f"{REPO_OWNER}/{REPO_NAME}"


def sync_item_states_from_daemon():
    """Sync queue item states from daemon status file"""
    daemon_status = get_daemon_status()
    item_states = daemon_status.get('item_states', {})
    
    if not item_states:
        return
    
    for item in engine.state.queue:
        if item.issue_id in item_states:
            state_info = item_states[item.issue_id]
            # Update item state from daemon's tracked state
            try:
                item.state = WorkflowState(state_info['state'])
            except ValueError:
                pass  # Keep existing state if invalid
            
            if state_info.get('issue_number'):
                item.issue_number = state_info['issue_number']
            if state_info.get('pr_number'):
                item.pr_number = state_info['pr_number']
            if state_info.get('last_action'):
                item.last_action = state_info['last_action']
            if state_info.get('last_action_time'):
                from datetime import datetime as dt
                try:
                    item.last_action_time = dt.fromisoformat(state_info['last_action_time'])
                except:
                    pass


# ========== SIDEBAR ==========
with st.sidebar:
    # Logo and branding with link
    if AVATAR_PATH.exists():
        st.markdown(f'<a href="http://www.swaibian.com" target="_blank"><img src="data:image/png;base64,{base64.b64encode(open(AVATAR_PATH, "rb").read()).decode()}" width="60"></a>', unsafe_allow_html=True)
    
    st.markdown("### Swaibian Agentic Pipeline")
    st.caption(f"Managing: `{REPO_FULL}`")
    
    st.divider()
    
    # Connection status
    if not st.session_state.connected:
        if st.button("🔌 Connect to GitHub", use_container_width=True):
            with st.spinner("Connecting..."):
                if engine.connect():
                    st.session_state.connected = True
                    st.success(f"Connected as {engine.client.get_current_user()}")
                    # Auto-refresh to fetch issue titles on connect
                    engine.refresh_status()
                    st.rerun()
                else:
                    st.error("Connection failed. Check your GitHub token.")
    else:
        st.success("✅ Connected to GitHub")
        
        # Sync item states from daemon if running
        sync_item_states_from_daemon()
        
        # Refresh button
        if st.button("🔄 Refresh Status", use_container_width=True):
            engine.refresh_status()
            sync_item_states_from_daemon()
            st.rerun()
    
    st.divider()
    
    # ========== DAEMON CONTROLS ==========
    st.markdown("#### 🤖 Pipeline Agent")
    
    daemon_status = get_daemon_status()
    daemon_running = daemon_status.get('is_running', False)
    
    if daemon_running:
        st.markdown('<span class="status-running">● Running</span>', unsafe_allow_html=True)
        st.caption(f"PID: {daemon_status.get('pid')}")
        
        # Show cooldown status
        cooldown_info = daemon_status.get('cooldown', {})
        if cooldown_info:
            if cooldown_info.get('can_assign'):
                st.markdown('<span class="status-ready">Ready to assign</span>', unsafe_allow_html=True)
            else:
                mins = cooldown_info.get('minutes_remaining', 0)
                st.warning(f"⏳ Cooldown: {mins}m remaining")
                last = cooldown_info.get('last_assignment', {})
                if last:
                    st.caption(f"Last: {last.get('issue_id')}")
        
        if st.button("⏹️ Stop Pipeline", use_container_width=True, type="primary"):
            stop_daemon()
            st.toast("Pipeline stopped", icon="⏹️")
            st.rerun()
    else:
        st.markdown('<span class="status-stopped">● Stopped</span>', unsafe_allow_html=True)
        
        if st.button("▶️ Start Pipeline", use_container_width=True, type="primary", disabled=not st.session_state.connected):
            # Start daemon in background process
            SRC_DIR = Path(__file__).parent
            subprocess.Popen(
                [sys.executable, str(SRC_DIR / "daemon.py"), "start"],
                cwd=str(PROJECT_ROOT),
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            st.toast("Pipeline starting...", icon="▶️")
            import time
            time.sleep(2)  # Give it time to start
            st.rerun()
    
    st.divider()
    
    # Manual run once
    st.markdown("#### ⚡ Manual Control")
    
    if st.button("▶️ Run Once", use_container_width=True, disabled=not st.session_state.connected):
        with st.spinner("Processing..."):
            actions = engine.run_once()
            for action in actions:
                st.toast(action, icon="✅")
            st.rerun()
    
    st.divider()
    
    # Settings
    st.markdown("#### ⚙️ Settings")
    auto_merge = st.checkbox(
        "Auto-merge PRs",
        value=engine.config.get('automation', {}).get('auto_merge', True)
    )
    auto_assign = st.checkbox(
        "Auto-assign issues",
        value=engine.config.get('automation', {}).get('auto_assign_next', True)
    )
    skip_final_review = st.checkbox(
        "Skip final review",
        value=engine.config.get('automation', {}).get('skip_final_review', False),
        help="Skip the approval step and merge directly after Copilot applies changes"
    )
    cooldown_minutes = st.number_input(
        "Cooldown (min)",
        min_value=1,
        max_value=480,
        value=engine.config.get('automation', {}).get('cooldown_minutes', 60)
    )
    
    if st.button("💾 Save", use_container_width=True):
        engine.config.setdefault('automation', {})['auto_merge'] = auto_merge
        engine.config.setdefault('automation', {})['auto_assign_next'] = auto_assign
        engine.config.setdefault('automation', {})['skip_final_review'] = skip_final_review
        engine.config.setdefault('automation', {})['cooldown_minutes'] = cooldown_minutes
        engine._save_config()
        st.success("Saved!")
    
    st.divider()
    
    # Reset config option
    with st.expander("🔧 Advanced"):
        st.caption("Reset to run setup wizard")
        if st.button("🗑️ Reset", use_container_width=True):
            if CONFIG_PATH.exists():
                CONFIG_PATH.unlink()
            # Clear engine from session state to force reload
            if 'engine' in st.session_state:
                del st.session_state['engine']
            st.toast("Resetting...", icon="🔄")
            import time
            time.sleep(1)
            st.rerun()

    # FOSS Info
    st.divider()
    with st.expander("❤️ FOSS"):
        st.markdown("### Open Source Credits")
        st.markdown("This project is free and open source software (FOSS), built on the shoulders of giants.")
        
        foss_libs = [
            {"name": "Streamlit", "ver": ">=1.28.0", "lic": "Apache 2.0", "url": "https://streamlit.io"},
            {"name": "PyGithub", "ver": ">=2.1.1", "lic": "LGPL v3", "url": "https://github.com/PyGithub/PyGithub"},
            {"name": "PyYAML", "ver": ">=6.0", "lic": "MIT", "url": "https://pyyaml.org"},
            {"name": "Pandas", "ver": ">=2.0.0", "lic": "BSD 3-Clause", "url": "https://pandas.pydata.org"},
            {"name": "HTTPX", "ver": ">=0.25.0", "lic": "BSD 3-Clause", "url": "https://www.python-httpx.org"},
            {"name": "python-dotenv", "ver": ">=1.0.0", "lic": "BSD 3-Clause", "url": "https://github.com/theskumar/python-dotenv"},
        ]
        
        for lib in foss_libs:
            st.markdown(f"• **[{lib['name']}]({lib['url']})**")
            st.caption(f"License: {lib['lic']}")
            
        st.markdown("---")
        st.markdown("**[Copilot Coding Agent Orchestrator](https://github.com/WoDeep/copilot-coding-agent-orchestrator)**")
        st.caption("Copyright © 2025 WoDeep / Swaibian")
        st.caption("Licensed under MIT License")


# ========== MAIN CONTENT ==========

# Modern header with gradient and Swaibian logo
import base64
logo_path = LOGO_PATH
if logo_path.exists():
    with open(logo_path, "rb") as f:
        logo_b64 = base64.b64encode(f.read()).decode()
    header_logo = f'<a href="http://www.swaibian.com" target="_blank" style="text-decoration: none;"><img src="data:image/png;base64,{logo_b64}" style="height: 48px; vertical-align: bottom; margin-right: 8px;"></a>'
else:
    header_logo = ""

st.markdown(f"""
<div class="main-header">
    <h1>{header_logo}<span>- Swaibian Agentic Pipeline</span></h1>
    <p>Autonomous AI Development Workflow Management</p>
    <span class="tip-button" onclick="document.getElementById('tip-modal').style.display='block'">enjoy!!</span>
</div>
""", unsafe_allow_html=True)

# Tip modal with QR code
with st.popover("Support if you like it!", use_container_width=False):
    st.markdown("### Thank you for your support! 🙏")
    st.markdown("If you find this tool helpful, please consider leaving a small tip to help support free and open source solutions.")
    if THANKYOU_PATH.exists():
        st.image(str(THANKYOU_PATH), width=250)
    st.markdown("*Every contribution helps keep open source alive!*")

# Repository info
st.markdown(f"**Repository:** [`{REPO_FULL}`](https://github.com/{REPO_FULL})")

# Pipeline status banner
daemon_status = get_daemon_status()
if daemon_status.get('is_running'):
    last_cycle = daemon_status.get('last_cycle', 'N/A')
    actions = daemon_status.get('actions', [])
    
    with st.expander("🚀 Pipeline Status (Active)", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Last Cycle:** `{last_cycle}`")
            st.markdown(f"**Process ID:** `{daemon_status.get('pid')}`")
        with col2:
            cooldown = daemon_status.get('cooldown', {})
            if cooldown.get('can_assign'):
                st.markdown('<span class="status-ready">● Ready to assign</span>', unsafe_allow_html=True)
            else:
                st.warning(f"⏳ Cooldown: {cooldown.get('minutes_remaining', 0)}m")
        
        if actions:
            st.markdown("**Recent Actions:**")
            for action in actions:
                st.markdown(f"• {action}")

# Status overview - use daemon status if running, otherwise engine status
if st.session_state.connected:
    # Prefer daemon's queue_status if daemon is running (more accurate)
    if daemon_status.get('is_running') and 'queue_status' in daemon_status:
        queue_stats = daemon_status['queue_status']
        total = queue_stats.get('total', 0)
        in_progress = queue_stats.get('in_progress', 0)
        queued = queue_stats.get('queued', 0)
        completed = queue_stats.get('completed', 0)
    else:
        status = engine.get_current_status()
        total = status['total']
        in_progress = len(status['in_progress'])
        queued = len(status['queued'])
        completed = len(status['completed'])
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📋 Total", total)
    with col2:
        st.metric("🔄 Active", in_progress)
    with col3:
        st.metric("⏳ Queued", queued)
    with col4:
        st.metric("✅ Done", completed)
    
    # Show last update time
    if daemon_status.get('is_running'):
        last_cycle = daemon_status.get('last_cycle', 'N/A')
        if last_cycle != 'N/A':
            st.caption(f"Last daemon cycle: {last_cycle}")
    elif 'status' in dir() and status.get('last_check'):
        st.caption(f"Last updated: {status['last_check'].strftime('%H:%M:%S')}")

st.divider()

# Main tabs
tab1, tab2, tab3 = st.tabs(["📋 Queue", "🔄 In Progress", "✅ Completed"])


def state_badge(state: WorkflowState) -> str:
    """Get emoji badge for state"""
    badges = {
        WorkflowState.QUEUED: "⏳",
        WorkflowState.ASSIGNED: "🤖",
        WorkflowState.PR_OPEN: "📝",
        WorkflowState.REVIEW_REQUESTED: "👀",
        WorkflowState.REVIEWING: "🔍",
        WorkflowState.CHANGES_REQUESTED: "📝",
        WorkflowState.APPLYING_CHANGES: "⚙️",
        WorkflowState.APPROVED: "✅",
        WorkflowState.MERGED: "🎉",
        WorkflowState.COMPLETED: "🏁"
    }
    return badges.get(state, "❓")


def render_compact_queue_item(item: QueueItem, index: int, total: int, show_controls: bool = True):
    """Render a compact single-line queue item"""
    cols = st.columns([0.3, 4, 1.5, 0.8]) if show_controls else st.columns([0.3, 5.5])
    
    with cols[0]:
        st.markdown(f"<span style='color:#666;font-size:0.85rem;'>{index + 1}.</span>", unsafe_allow_html=True)
    
    with cols[1]:
        badge = state_badge(item.state)
        # Compact: title/ID + issue number on same line
        title = item.issue_title if item.issue_title else item.issue_id
        issue_link = f"[#{item.issue_number}](https://github.com/{REPO_FULL}/issues/{item.issue_number})" if item.issue_number else ""
        st.markdown(f"{badge} **{title}** {issue_link}", unsafe_allow_html=True)
    
    if show_controls:
        with cols[2]:
            # Compact arrow buttons in a row
            c1, c2 = st.columns(2)
            with c1:
                if index > 0:
                    if st.button("↑", key=f"up_{item.issue_id}", help="Move up"):
                        engine.move_item_up(item.issue_id)
                        st.rerun()
            with c2:
                if index < total - 1:
                    if st.button("↓", key=f"down_{item.issue_id}", help="Move down"):
                        engine.move_item_down(item.issue_id)
                        st.rerun()
        
        with cols[3]:
            if st.button("×", key=f"del_{item.issue_id}", help="Remove"):
                engine.remove_item(item.issue_id)
                st.toast(f"Removed {item.issue_id}", icon="🗑️")
                st.rerun()


with tab1:
    # Header with action buttons
    header_cols = st.columns([3, 1, 1])
    with header_cols[0]:
        st.subheader("📋 Issue Queue")
    
    queued_items = [i for i in engine.state.queue if i.state == WorkflowState.QUEUED]
    
    with header_cols[1]:
        if len(queued_items) >= 2:
            if st.button("🔄 Reverse", help="Flip the entire queue order", use_container_width=True):
                engine.reverse_queue()
                # Force reload from config to update session state
                engine.reload_queue_from_config()
                st.toast("Queue order reversed!", icon="🔄")
                st.rerun()
    
    with header_cols[2]:
        with st.popover("➕ Add", use_container_width=True):
            new_issue = st.text_input("Issue ID", placeholder="#123", key="add_issue_input")
            if st.button("Add to Queue", key="add_issue_btn"):
                if new_issue:
                    if engine.add_item(new_issue, 0):  # Add to top
                        st.toast(f"Added {new_issue}", icon="✅")
                        st.rerun()
                    else:
                        st.error("Already in queue")
    
    st.caption("Processed top→bottom. Use arrows to reorder.")
    
    if not queued_items:
        st.info("No issues in queue. All items are in progress or completed!")
    else:
        # Clean list with arrow buttons (native Streamlit)
        for idx, item in enumerate(queued_items):
            render_compact_queue_item(item, idx, len(queued_items))


with tab2:
    st.subheader("🔄 In Progress")
    
    in_progress = [i for i in engine.state.queue 
                   if i.state not in [WorkflowState.QUEUED, WorkflowState.MERGED, WorkflowState.COMPLETED]]
    
    if not in_progress:
        st.info("No issues currently in progress.")
    else:
        # Get workflow history from daemon status
        workflow_histories = {}
        if daemon_status:
            for issue_id, item_state in daemon_status.get('item_states', {}).items():
                if 'workflow_history' in item_state:
                    workflow_histories[issue_id] = item_state['workflow_history']
        
        for item in in_progress:
            with st.container():
                col1, col2, col3 = st.columns([3, 4, 2])
                
                with col1:
                    badge = state_badge(item.state)
                    # Show issue title if available, otherwise just ID
                    if item.issue_title:
                        st.write(f"{badge} **{item.issue_title}**")
                    else:
                        st.write(f"{badge} **{item.issue_id}**")
                    if item.issue_number:
                        st.markdown(f"[Issue #{item.issue_number}](https://github.com/{REPO_FULL}/issues/{item.issue_number})")
                
                with col2:
                    st.write(f"**State:** {item.state.value.replace('_', ' ').title()}")
                    if item.pr_number:
                        st.markdown(f"[PR #{item.pr_number}](https://github.com/{REPO_FULL}/pull/{item.pr_number})")
                    if item.last_action:
                        st.caption(f"Last: {item.last_action}")
                
                with col3:
                    # Manual action buttons based on state
                    if item.state == WorkflowState.REVIEW_REQUESTED and item.pr_number:
                        if st.button("🔄 Reassign to Copilot", key=f"reassign_{item.issue_id}"):
                            if engine.client and engine.client.request_review_from_copilot(item.pr_number):
                                st.success("Reassigned!")
                                st.rerun()
                    
                    if item.state == WorkflowState.CHANGES_REQUESTED and item.pr_number:
                        if st.button("💬 Apply Changes", key=f"apply_{item.issue_id}"):
                            if engine.client and engine.client.comment_apply_changes(item.pr_number):
                                st.success("Comment added!")
                                st.rerun()
                    
                    if item.state == WorkflowState.APPROVED and item.pr_number:
                        if st.button("🔀 Merge PR", key=f"merge_{item.issue_id}"):
                            if engine.client and engine.client.merge_pr(item.pr_number):
                                st.success("Merged!")
                                st.rerun()
                
                # Workflow History Log
                history = workflow_histories.get(item.issue_id, [])
                if history:
                    with st.expander(f"📋 Workflow Log ({len(history)} events)", expanded=False):
                        for event in reversed(history):  # Show newest first
                            timestamp = event.get('timestamp', 'N/A')
                            event_text = event.get('event', 'Unknown')
                            state = event.get('state', '')
                            pr = event.get('pr_number', '')
                            
                            # Format timestamp nicely
                            try:
                                from datetime import datetime
                                dt = datetime.fromisoformat(timestamp)
                                time_str = dt.strftime('%H:%M:%S')
                                date_str = dt.strftime('%Y-%m-%d')
                            except:
                                time_str = timestamp
                                date_str = ""
                            
                            pr_info = f" (PR #{pr})" if pr else ""
                            st.markdown(f"**{time_str}** - {event_text}{pr_info}")
                            if date_str:
                                st.caption(f"{date_str} | State: {state}")
                
                st.divider()


with tab3:
    st.subheader("✅ Completed")
    
    completed = [i for i in engine.state.queue 
                 if i.state in [WorkflowState.MERGED, WorkflowState.COMPLETED]]
    
    if not completed:
        st.info("No completed issues yet.")
    else:
        # Show as a compact table
        data = []
        for item in completed:
            # Show title if available, otherwise issue_id
            display_name = item.issue_title if item.issue_title else item.issue_id
            data.append({
                "Issue": display_name,
                "Issue #": item.issue_number,
                "PR #": item.pr_number,
                "Completed": item.last_action_time.strftime('%Y-%m-%d %H:%M') if item.last_action_time else "N/A"
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        if len(engine.state.queue) > 0:
            st.metric("Progress", f"{len(completed)}/{len(engine.state.queue)}", 
                      delta=f"{len(completed)/len(engine.state.queue)*100:.1f}%")


# ========== FOOTER ==========
st.divider()

# Error log
if engine.state.errors:
    with st.expander("⚠️ Recent Errors"):
        for error in engine.state.errors[-5:]:
            st.error(error)

# Quick links
st.markdown("#### 🔗 Quick Links")
col1, col2, col3 = st.columns(3)
with col1:
    st.link_button("📋 Issues", f"https://github.com/{REPO_FULL}/issues", use_container_width=True)
with col2:
    st.link_button("🔀 PRs", f"https://github.com/{REPO_FULL}/pulls", use_container_width=True)
with col3:
    st.link_button("📊 Repo", f"https://github.com/{REPO_FULL}", use_container_width=True)

# Branding footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #64748b; font-size: 0.85rem;">
    <p>Powered by <strong>Swaibian</strong> • Autonomous AI Development</p>
</div>
""", unsafe_allow_html=True)

# Auto-refresh logic
if st.session_state.connected and daemon_status.get('is_running'):
    import time
    
    # Store the state we just rendered
    current_last_cycle = daemon_status.get('last_cycle')
    current_action_count = len(daemon_status.get('actions', []))
    
    # Create a placeholder for the watcher loop
    # We use a loop that checks for changes every few seconds
    # This keeps the script running (watching) but only triggers a full rerun when data changes
    
    check_interval = 5  # Check every 5 seconds
    
    # We use an empty container to hold the loop
    with st.empty():
        while True:
            time.sleep(check_interval)
            
            try:
                # Check for updates
                new_status = get_daemon_status()
                new_cycle = new_status.get('last_cycle')
                new_action_count = len(new_status.get('actions', []))
                
                # If cycle timestamp changed or number of actions changed, trigger refresh
                if new_cycle != current_last_cycle or new_action_count != current_action_count:
                    st.rerun()
            except Exception:
                # If reading fails (e.g. file lock), just ignore and try next time
                pass

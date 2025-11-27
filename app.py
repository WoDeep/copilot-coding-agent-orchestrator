"""
GitHub Copilot Coding Agent Orchestrator
Streamlit web UI for managing automated development workflows
"""

import streamlit as st
import pandas as pd
import subprocess
import os
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent))

# Paths
SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR / "config.yaml"
ENV_PATH = SCRIPT_DIR / ".env"

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
    page_title="Copilot Orchestrator",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    st.title("🤖 Copilot Orchestrator")
    st.caption(f"Repository: {REPO_FULL}")
    
    st.divider()
    
    # Connection status
    if not st.session_state.connected:
        if st.button("🔌 Connect to GitHub", use_container_width=True):
            with st.spinner("Connecting..."):
                if engine.connect():
                    st.session_state.connected = True
                    st.success(f"Connected as {engine.client.get_current_user()}")
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
    st.subheader("🤖 Background Daemon")
    
    daemon_status = get_daemon_status()
    daemon_running = daemon_status.get('is_running', False)
    
    if daemon_running:
        st.success(f"✅ Daemon Running (PID: {daemon_status.get('pid')})")
        
        # Show cooldown status
        cooldown_info = daemon_status.get('cooldown', {})
        if cooldown_info:
            if cooldown_info.get('can_assign'):
                st.info("⏱️ Ready to assign next issue")
            else:
                mins = cooldown_info.get('minutes_remaining', 0)
                st.warning(f"⏳ Cooldown: {mins} minutes remaining")
                last = cooldown_info.get('last_assignment', {})
                if last:
                    st.caption(f"Last assigned: {last.get('issue_id')}")
        
        if st.button("⏹️ Stop Daemon", use_container_width=True, type="primary"):
            stop_daemon()
            st.toast("Daemon stopped", icon="⏹️")
            st.rerun()
    else:
        st.warning("⏹️ Daemon Stopped")
        
        if st.button("▶️ Start Daemon", use_container_width=True, type="primary", disabled=not st.session_state.connected):
            # Start daemon in background process
            subprocess.Popen(
                [sys.executable, str(SCRIPT_DIR / "daemon.py"), "start"],
                cwd=str(SCRIPT_DIR),
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            st.toast("Daemon starting...", icon="▶️")
            import time
            time.sleep(2)  # Give it time to start
            st.rerun()
    
    st.divider()
    
    # Manual run once
    st.subheader("⚡ Manual Control")
    
    if st.button("▶️ Run Once (Manual)", use_container_width=True, disabled=not st.session_state.connected):
        with st.spinner("Processing..."):
            actions = engine.run_once()
            for action in actions:
                st.toast(action, icon="✅")
            st.rerun()
    
    st.divider()
    
    # Settings
    st.subheader("⚙️ Settings")
    auto_merge = st.checkbox(
        "Auto-merge approved PRs",
        value=engine.config.get('automation', {}).get('auto_merge', True)
    )
    auto_assign = st.checkbox(
        "Auto-assign next issue",
        value=engine.config.get('automation', {}).get('auto_assign_next', True)
    )
    cooldown_minutes = st.number_input(
        "Cooldown (minutes)",
        min_value=1,
        max_value=480,
        value=engine.config.get('automation', {}).get('cooldown_minutes', 60)
    )
    
    if st.button("💾 Save Settings", use_container_width=True):
        engine.config.setdefault('automation', {})['auto_merge'] = auto_merge
        engine.config.setdefault('automation', {})['auto_assign_next'] = auto_assign
        engine.config.setdefault('automation', {})['cooldown_minutes'] = cooldown_minutes
        engine._save_config()
        st.success("Settings saved!")
    
    st.divider()
    
    # Reset config option
    with st.expander("🔧 Advanced"):
        st.caption("Reset configuration to run setup wizard again")
        if st.button("🗑️ Reset Config", use_container_width=True):
            if CONFIG_PATH.exists():
                CONFIG_PATH.unlink()
            st.toast("Configuration reset. Reloading...", icon="🔄")
            import time
            time.sleep(1)
            st.rerun()


# ========== MAIN CONTENT ==========

# Header with status
st.title("🤖 Copilot Coding Agent Orchestrator")
st.caption(f"Managing: **{REPO_FULL}**")

# Daemon status banner
daemon_status = get_daemon_status()
if daemon_status.get('is_running'):
    last_cycle = daemon_status.get('last_cycle', 'N/A')
    actions = daemon_status.get('actions', [])
    
    with st.expander("🤖 Daemon Status (Running)", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Last Cycle:** {last_cycle}")
            st.write(f"**PID:** {daemon_status.get('pid')}")
        with col2:
            cooldown = daemon_status.get('cooldown', {})
            if cooldown.get('can_assign'):
                st.success("Ready to assign")
            else:
                st.warning(f"Cooldown: {cooldown.get('minutes_remaining', 0)} min remaining")
        
        if actions:
            st.write("**Recent Actions:**")
            for action in actions:
                st.write(f"- {action}")

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
        st.metric("📋 Total Issues", total)
    with col2:
        st.metric("🔄 In Progress", in_progress)
    with col3:
        st.metric("⏳ Queued", queued)
    with col4:
        st.metric("✅ Completed", completed)
    
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


def render_queue_item(item: QueueItem, index: int, total: int, show_controls: bool = True):
    """Render a single queue item"""
    col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 1, 0.5])
    
    with col1:
        badge = state_badge(item.state)
        st.write(f"{badge} **{item.issue_id}**")
        if item.issue_number:
            st.caption(f"Issue #{item.issue_number}")
    
    with col2:
        st.write(item.state.value.replace("_", " ").title())
        if item.pr_number:
            st.caption(f"PR #{item.pr_number}")
    
    with col3:
        if item.last_action:
            st.caption(item.last_action)
            if item.last_action_time:
                st.caption(item.last_action_time.strftime('%H:%M'))
    
    with col4:
        if show_controls:
            subcol1, subcol2 = st.columns(2)
            with subcol1:
                if index > 0:
                    if st.button("⬆️", key=f"up_{item.issue_id}", help="Move up"):
                        engine.move_item_up(item.issue_id)
                        st.rerun()
            with subcol2:
                if index < total - 1:
                    if st.button("⬇️", key=f"down_{item.issue_id}", help="Move down"):
                        engine.move_item_down(item.issue_id)
                        st.rerun()
    
    with col5:
        if show_controls:
            if st.button("🗑️", key=f"del_{item.issue_id}", help="Remove from queue"):
                engine.remove_item(item.issue_id)
                st.toast(f"Removed {item.issue_id} from queue", icon="🗑️")
                st.rerun()


with tab1:
    st.subheader("📋 Issue Queue")
    st.caption("Issues are processed top to bottom. Use arrows to reorder.")
    
    queued_items = [i for i in engine.state.queue if i.state == WorkflowState.QUEUED]
    
    if not queued_items:
        st.info("No issues in queue. All items are in progress or completed!")
    else:
        for idx, item in enumerate(queued_items):
            with st.container():
                render_queue_item(item, idx, len(queued_items))
                st.divider()
    
    # Add item form
    with st.expander("➕ Add Issue to Queue"):
        new_issue = st.text_input("Issue ID or Number", placeholder="#123 or TC-P-01")
        position = st.number_input("Position (0 = top)", min_value=0, value=len(queued_items))
        if st.button("Add to Queue"):
            if new_issue:
                if engine.add_item(new_issue, position):
                    st.success(f"Added {new_issue} to queue")
                    st.rerun()
                else:
                    st.error("Issue already in queue or invalid")


with tab2:
    st.subheader("🔄 In Progress")
    
    in_progress = [i for i in engine.state.queue 
                   if i.state not in [WorkflowState.QUEUED, WorkflowState.MERGED, WorkflowState.COMPLETED]]
    
    if not in_progress:
        st.info("No issues currently in progress.")
    else:
        for item in in_progress:
            with st.container():
                col1, col2, col3 = st.columns([3, 4, 2])
                
                with col1:
                    badge = state_badge(item.state)
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
            data.append({
                "Issue ID": item.issue_id,
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

# Quick actions
st.caption("Quick Actions")
col1, col2, col3 = st.columns(3)
with col1:
    st.link_button("📋 GitHub Issues", f"https://github.com/{REPO_FULL}/issues")
with col2:
    st.link_button("🔀 Pull Requests", f"https://github.com/{REPO_FULL}/pulls")
with col3:
    st.link_button("📊 Repository", f"https://github.com/{REPO_FULL}")

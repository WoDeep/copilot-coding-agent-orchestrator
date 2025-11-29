"""
Setup Wizard for GitHub Copilot Coding Agent Orchestrator
Handles first-time setup and configuration
"""

import streamlit as st
from pathlib import Path
from github import Github
import yaml
from typing import Optional


def check_token_valid(token: str) -> tuple[bool, Optional[str], Optional[object]]:
    """Check if a GitHub token is valid and return user info"""
    try:
        gh = Github(token)
        user = gh.get_user()
        username = user.login
        return True, username, gh
    except Exception as e:
        return False, str(e), None


def get_user_repos(gh: object) -> list[dict]:
    """Get repositories the user has access to"""
    repos = []
    try:
        # Get repos where user has push access (can create issues, PRs)
        for repo in gh.get_user().get_repos(affiliation='owner,collaborator,organization_member'):
            try:
                # Check if we have admin or push access
                perms = repo.permissions
                if perms and (perms.push or perms.admin):
                    repos.append({
                        'full_name': repo.full_name,
                        'name': repo.name,
                        'owner': repo.owner.login,
                        'description': repo.description or '',
                        'private': repo.private,
                        'open_issues': repo.open_issues_count
                    })
            except:
                continue
    except Exception as e:
        st.error(f"Error fetching repositories: {e}")
    return repos


def get_repo_issues(gh: object, owner: str, repo: str, state: str = "open") -> list[dict]:
    """Get issues from a repository"""
    issues = []
    try:
        repository = gh.get_repo(f"{owner}/{repo}")
        for issue in repository.get_issues(state=state):
            # Skip pull requests (they show up as issues too)
            if issue.pull_request is None:
                issues.append({
                    'number': issue.number,
                    'title': issue.title,
                    'state': issue.state,
                    'assignee': issue.assignee.login if issue.assignee else None,
                    'labels': [l.name for l in issue.labels],
                    'created_at': issue.created_at.strftime('%Y-%m-%d'),
                    'url': issue.html_url
                })
    except Exception as e:
        st.error(f"Error fetching issues: {e}")
    return issues


def save_config(config: dict, config_path: Path):
    """Save configuration to YAML file"""
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)


def save_env(token: str, env_path: Path):
    """Save GitHub token to .env file"""
    with open(env_path, 'w') as f:
        f.write(f"GITHUB_TOKEN={token}\n")


def render_setup_wizard(config_path: Path, env_path: Path) -> bool:
    """
    Render the setup wizard UI.
    Returns True if setup is complete and ready to use main app.
    """
    st.set_page_config(
        page_title="Copilot Orchestrator Setup",
        page_icon="🚀",
        layout="centered"
    )
    
    st.title("🚀 GitHub Copilot Coding Agent Orchestrator")
    st.subheader("Setup Wizard")
    
    # Initialize session state for wizard
    if 'setup_step' not in st.session_state:
        st.session_state.setup_step = 1
    if 'setup_token' not in st.session_state:
        st.session_state.setup_token = ""
    if 'setup_gh' not in st.session_state:
        st.session_state.setup_gh = None
    if 'setup_username' not in st.session_state:
        st.session_state.setup_username = ""
    if 'setup_repos' not in st.session_state:
        st.session_state.setup_repos = []
    if 'setup_selected_repo' not in st.session_state:
        st.session_state.setup_selected_repo = None
    if 'setup_issues' not in st.session_state:
        st.session_state.setup_issues = []
    if 'setup_selected_issues' not in st.session_state:
        st.session_state.setup_selected_issues = []
    if 'setup_config' not in st.session_state:
        st.session_state.setup_config = {}
    
    # Progress indicator
    steps = ["GitHub Token", "Select Repository", "Select Issues", "Configure", "Complete"]
    current_step = st.session_state.setup_step
    
    # Show progress
    progress_cols = st.columns(len(steps))
    for i, (col, step_name) in enumerate(zip(progress_cols, steps)):
        step_num = i + 1
        with col:
            if step_num < current_step:
                st.success(f"✅ {step_name}")
            elif step_num == current_step:
                st.info(f"👉 {step_name}")
            else:
                st.caption(f"⏳ {step_name}")
    
    st.divider()
    
    # ========== STEP 1: GitHub Token ==========
    if current_step == 1:
        st.header("Step 1: GitHub Personal Access Token")
        st.markdown("""
        To use the Copilot Orchestrator, you need a GitHub Personal Access Token with the following permissions:
        - `repo` - Full control of repositories
        - `workflow` - Update GitHub Action workflows
        
        [Create a token here](https://github.com/settings/tokens/new?description=Copilot%20Orchestrator&scopes=repo,workflow)
        """)
        
        token = st.text_input(
            "Enter your GitHub Personal Access Token",
            type="password",
            value=st.session_state.setup_token,
            help="Your token will be stored locally in .env file"
        )
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("Verify Token", type="primary", disabled=not token):
                with st.spinner("Verifying token..."):
                    valid, result, gh = check_token_valid(token)
                    if valid:
                        st.session_state.setup_token = token
                        st.session_state.setup_gh = gh
                        st.session_state.setup_username = result
                        st.success(f"✅ Authenticated as **{result}**")
                        st.session_state.setup_step = 2
                        st.rerun()
                    else:
                        st.error(f"❌ Invalid token: {result}")
    
    # ========== STEP 2: Select Repository ==========
    elif current_step == 2:
        st.header("Step 2: Select Repository")
        st.markdown(f"Logged in as **{st.session_state.setup_username}**")
        
        # Fetch repos if not cached
        if not st.session_state.setup_repos:
            with st.spinner("Fetching your repositories..."):
                st.session_state.setup_repos = get_user_repos(st.session_state.setup_gh)
        
        repos = st.session_state.setup_repos
        
        if not repos:
            st.warning("No repositories found with push access.")
            if st.button("⬅️ Back"):
                st.session_state.setup_step = 1
                st.rerun()
        else:
            # Create display options
            repo_options = {r['full_name']: r for r in repos}
            
            selected = st.selectbox(
                "Choose a repository",
                options=list(repo_options.keys()),
                format_func=lambda x: f"{x} {'🔒' if repo_options[x]['private'] else '🌐'} ({repo_options[x]['open_issues']} open issues)"
            )
            
            if selected:
                repo_info = repo_options[selected]
                st.caption(f"Description: {repo_info['description'] or 'No description'}")
            
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("⬅️ Back"):
                    st.session_state.setup_step = 1
                    st.rerun()
            with col2:
                if st.button("Next ➡️", type="primary", disabled=not selected):
                    st.session_state.setup_selected_repo = repo_options[selected]
                    st.session_state.setup_issues = []  # Reset issues
                    st.session_state.setup_step = 3
                    st.rerun()
    
    # ========== STEP 3: Select Issues ==========
    elif current_step == 3:
        repo = st.session_state.setup_selected_repo
        st.header("Step 3: Select Issues for Queue")
        st.markdown(f"Repository: **{repo['full_name']}**")
        
        # Fetch issues if not cached
        if not st.session_state.setup_issues:
            with st.spinner("Fetching issues..."):
                st.session_state.setup_issues = get_repo_issues(
                    st.session_state.setup_gh,
                    repo['owner'],
                    repo['name']
                )
        
        issues = st.session_state.setup_issues
        
        if not issues:
            st.warning("No open issues found in this repository.")
            st.info("You can add issues to the queue later from the main dashboard.")
            selected_issues = []
        else:
            st.markdown("Select the issues you want Copilot to work on (in order):")
            
            # Multi-select with checkboxes
            selected_issues = []
            for issue in issues:
                col1, col2, col3 = st.columns([0.5, 3, 1])
                with col1:
                    checked = st.checkbox(
                        "",
                        key=f"issue_{issue['number']}",
                        value=issue['number'] in [i['number'] for i in st.session_state.setup_selected_issues]
                    )
                    if checked:
                        selected_issues.append(issue)
                with col2:
                    labels_str = " ".join([f"`{l}`" for l in issue['labels'][:3]]) if issue['labels'] else ""
                    st.markdown(f"**#{issue['number']}** - {issue['title']} {labels_str}")
                with col3:
                    assignee = issue['assignee'] or "Unassigned"
                    st.caption(assignee)
            
            st.session_state.setup_selected_issues = selected_issues
            st.caption(f"Selected: {len(selected_issues)} issues")
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("⬅️ Back"):
                st.session_state.setup_step = 2
                st.rerun()
        with col2:
            if st.button("Next ➡️", type="primary"):
                st.session_state.setup_selected_issues = selected_issues
                st.session_state.setup_step = 4
                st.rerun()
    
    # ========== STEP 4: Configure Settings ==========
    elif current_step == 4:
        st.header("Step 4: Configure Settings")
        
        repo = st.session_state.setup_selected_repo
        issues = st.session_state.setup_selected_issues
        
        st.markdown(f"**Repository:** {repo['full_name']}")
        st.markdown(f"**Issues in queue:** {len(issues)}")
        
        st.divider()
        
        st.subheader("Automation Settings")
        
        target_branch = st.text_input(
            "Target Branch",
            value="main",
            help="Branch where Copilot will create PRs targeting"
        )
        
        cooldown_minutes = st.number_input(
            "Cooldown between assignments (minutes)",
            min_value=1,
            max_value=480,
            value=20,
            help="Wait time between assigning issues to Copilot"
        )
        
        auto_merge = st.checkbox(
            "Auto-merge approved PRs",
            value=True,
            help="Automatically merge PRs once they're approved"
        )
        
        auto_assign = st.checkbox(
            "Auto-assign next issue",
            value=True,
            help="Automatically assign the next issue after cooldown"
        )
        
        skip_final_review = st.checkbox(
            "Skip final review (Auto-approve)",
            value=True,
            help="Skip the final human/Copilot review step and merge immediately after changes are applied"
        )
        
        poll_interval = st.number_input(
            "Poll interval (seconds)",
            min_value=30,
            max_value=300,
            value=60,
            help="How often to check for updates"
        )
        
        st.divider()
        
        st.subheader("Agent Instructions (Optional)")
        agent_instructions = st.text_area(
            "Custom instructions for Copilot",
            value="",
            height=150,
            help="These instructions will be added as a comment when assigning issues"
        )
        
        # Build config
        config = {
            'github': {
                'owner': repo['owner'],
                'repo': repo['name'],
                'target_branch': target_branch
            },
            'automation': {
                'cooldown_minutes': cooldown_minutes,
                'auto_merge': auto_merge,
                'auto_assign_next': auto_assign,
                'poll_interval': poll_interval,
                'skip_final_review': skip_final_review
            },
            'issue_queue': [f"#{i['number']}" for i in issues],
            'issue_numbers': {f"#{i['number']}": i['number'] for i in issues}
        }
        
        if agent_instructions.strip():
            config['agent_instructions'] = agent_instructions
        
        st.session_state.setup_config = config
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("⬅️ Back"):
                st.session_state.setup_step = 3
                st.rerun()
        with col2:
            if st.button("Complete Setup ✅", type="primary"):
                st.session_state.setup_step = 5
                st.rerun()
    
    # ========== STEP 5: Complete ==========
    elif current_step == 5:
        st.header("Step 5: Setup Complete!")
        
        config = st.session_state.setup_config
        
        st.success("Your configuration is ready!")
        
        with st.expander("Review Configuration", expanded=True):
            st.json(config)
        
        st.warning("Click 'Save & Start' to save your configuration and launch the orchestrator.")
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("⬅️ Back"):
                st.session_state.setup_step = 4
                st.rerun()
        with col2:
            if st.button("💾 Save & Start", type="primary"):
                with st.spinner("Saving configuration..."):
                    # Save token to .env
                    save_env(st.session_state.setup_token, env_path)
                    
                    # Save config to YAML
                    save_config(config, config_path)
                    
                    st.success("✅ Configuration saved!")
                    st.balloons()
                    
                    # Clear setup state
                    for key in list(st.session_state.keys()):
                        if key.startswith('setup_'):
                            del st.session_state[key]
                    
                    # Clear engine to force reload with new config
                    if 'engine' in st.session_state:
                        del st.session_state['engine']
                    
                    st.info("Restarting application...")
                    import time
                    time.sleep(2)
                    st.rerun()
    
    return False  # Setup not complete


def is_setup_complete(config_path: Path, env_path: Path) -> bool:
    """Check if setup has been completed"""
    # Check if config exists and has required fields
    if not config_path.exists():
        return False
    
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        # Check for required config keys
        if not config:
            return False
        if 'github' not in config:
            return False
        if 'owner' not in config.get('github', {}):
            return False
        if 'repo' not in config.get('github', {}):
            return False
        
        # Check for token
        if not env_path.exists():
            return False
        
        return True
    except:
        return False

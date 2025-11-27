# GitHub Copilot Coding Agent Orchestrator

A Streamlit web application to manage and automate GitHub Copilot development workflows. Configure any repository and let the orchestrator automatically assign issues to Copilot, manage PRs, and track progress.

## Features

- 🔧 **Setup Wizard**: Easy first-time configuration with guided setup
- 📋 **Queue Management**: View, reorder, add, and remove issues from the development queue
- 🔄 **Status Monitoring**: Real-time status of all issues and PRs
- 🤖 **Background Daemon**: Start/stop automated workflow processing with UI controls
- ⏱️ **Cooldown System**: Rate-limit issue assignments (configurable)
- 📝 **Agent Instructions**: Automatically include implementation guidelines when assigning
- 🔌 **MCP Integration**: Uses GitHub's official MCP Server for Copilot assignment

## Quick Start

### 1. Start the Application

```bash
cd scripts/swaibian_automation
./start.sh
```

This will:
- Create a virtual environment (first run only)
- Install dependencies
- Start the Streamlit server at http://localhost:8642

### 2. Run the Setup Wizard

On first launch, you'll be guided through a 5-step setup wizard:

1. **GitHub Token**: Enter your Personal Access Token
2. **Repository**: Select which repository to automate
3. **Issues**: Choose which issues to add to the queue
4. **Configure**: Set automation preferences (cooldown, auto-merge, etc.)
5. **Complete**: Review and start using the orchestrator

### 3. Token Requirements

Your GitHub Personal Access Token needs these permissions:
- `repo` (full control of private repositories)
- `workflow` (if you need to trigger workflows)

## How It Works

### The Automation Loop

When the daemon is running, it polls at regular intervals and:

1. **When Copilot requests your review** → Auto-reassign review to Copilot
2. **When Copilot suggests changes** → Auto-comment "@copilot apply changes"
3. **When PR is approved** → Auto-merge into target branch
4. **When PR is merged** → Wait for cooldown, then assign next issue to Copilot

### Cooldown System

To prevent overwhelming the system, there's a configurable cooldown between issue assignments:

- After assigning an issue, the daemon waits before assigning the next
- Other actions (review reassignment, applying changes, merging) have no cooldown
- You can adjust the cooldown time in the UI Settings

### Agent Instructions

When assigning issues to Copilot, the system includes detailed implementation instructions that you can customize:

- Implementation workflow
- Testing requirements
- Documentation requirements
- Any custom guidelines for your project

These are configured in `config.yaml` under `agent_instructions`.

## MCP Client

This automation uses the **GitHub Remote MCP Server** at `https://api.githubcopilot.com/mcp/` 
to properly assign issues to Copilot. This is the same API that VS Code and other IDEs use.

### Available MCP Tools

- `assign_copilot_to_issue` - Assign Copilot to work on an issue
- `request_copilot_review` - Request Copilot to review a PR
- Plus 38 other GitHub tools (issues, PRs, repos, etc.)

### CLI Usage

```bash
# List available tools
python mcp_client.py list-tools

# Assign Copilot to an issue (after setup)
python mcp_client.py assign OWNER REPO ISSUE_NUMBER
```

## Dashboard Controls

### Sidebar Controls

| Control | Description |
|---------|-------------|
| 🔌 Connect to GitHub | Authenticate with your token |
| 🔄 Refresh Status | Manually refresh issue/PR status |
| ▶️ Start Daemon | Start background automation |
| ⏹️ Stop Daemon | Stop background automation |
| ▶️ Run Once | Execute one automation cycle manually |

### Queue Tab
- View all queued issues
- Use ⬆️/⬇️ buttons to reorder
- Add new issues to the queue

### In Progress Tab
- See all active issues (assigned, PR open, reviewing, etc.)
- Manual action buttons for each state

### Completed Tab
- View all completed issues
- Track overall progress

## Configuration

After running the setup wizard, your `config.yaml` will be generated:

```yaml
github:
  owner: YourUsername      # Repository owner
  repo: YourRepo           # Repository name
  target_branch: main      # Target branch for PRs

automation:
  poll_interval: 60        # seconds between checks
  auto_merge: true         # auto-merge approved PRs
  auto_assign_next: true   # auto-assign next issue after merge
  cooldown_minutes: 60     # minimum time between assignments

agent_instructions: |
  Your custom implementation instructions...

issue_queue:
  - ISSUE-1
  - ISSUE-2
  # ... your queue order
```

### Resetting Configuration

To re-run the setup wizard:
1. Click "Reset Config" in the Advanced Settings section of the sidebar
2. Or delete `config.yaml` and `.env` files manually

## CLI Usage

You can also control the daemon directly:

```bash
# Start daemon
python daemon.py start

# Stop daemon  
python daemon.py stop

# Check status
python daemon.py status

# Run automation once (without daemon)
python automation_engine.py --once
```

## Files

```
scripts/swaibian_automation/
├── app.py                 # Streamlit dashboard
├── setup_wizard.py        # First-time setup wizard
├── daemon.py              # Background daemon process
├── automation_engine.py   # Core automation logic
├── github_client.py       # GitHub API client
├── mcp_client.py          # MCP protocol client
├── config.yaml            # Configuration (generated)
├── .env                   # GitHub token (generated)
├── requirements.txt       # Python dependencies
├── start.sh              # Start script
├── daemon.pid            # PID file (when running)
├── daemon_status.json    # Status file (when running)
├── daemon.log            # Log file
└── README.md             # This file
```

## Branch Strategy

This automation uses an integration branch pattern:

```
main (stable) ← manual merge when ready
    ↑
target_branch (integration) ← auto-merged PRs from Copilot
    ↑
feature branches (created by Copilot)
```

This keeps `main` stable while development happens on your target branch.

## Troubleshooting

### "Connection failed"
- Check that your GitHub token is valid
- Ensure the token has `repo` permissions

### "Daemon won't start"
- Check `daemon.log` for errors
- Ensure no stale `daemon.pid` file exists
- Verify GitHub token is set in `.env`

### "Cooldown seems stuck"
- Check `last_assignment.json` for the timestamp
- You can delete this file to reset the cooldown

### "Issue not found"
- Make sure the issue ID is correct
- Refresh status in the UI

### "Setup wizard not appearing"
- Delete `config.yaml` to restart setup
- Or use "Reset Config" in Advanced Settings

## Requirements

- Python 3.9+
- GitHub Personal Access Token with `repo` permissions
- GitHub Copilot subscription (for issue assignment to work)

## License

MIT License

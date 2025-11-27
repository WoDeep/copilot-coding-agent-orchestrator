<p align="center">
  <img src="assets/swaibian_white.png" alt="Swaibian Logo" width="200"/>
</p>

<h1 align="center">🚀 Swaibian Agentic Pipeline</h1>

<p align="center">
  <strong>Autonomous AI-powered development workflows with GitHub Copilot</strong>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#how-it-works">How It Works</a> •
  <a href="#configuration">Configuration</a> •
  <a href="#contributing">Contributing</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python 3.9+"/>
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License: MIT"/>
  <img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg" alt="PRs Welcome"/>
  <img src="https://img.shields.io/github/stars/WoDeep/copilot-coding-agent-orchestrator?style=social" alt="GitHub Stars"/>
</p>

---

## ✨ Features

- 🔧 **Setup Wizard** - Easy first-time configuration with guided setup
- 📋 **Queue Management** - View, reorder, add, and remove issues from the development queue
- 🔄 **Real-time Monitoring** - Live status of all issues and PRs with workflow history
- 🤖 **Autonomous Pipeline** - Start/stop automated workflow processing
- ⏱️ **Smart Cooldowns** - Rate-limit issue assignments (configurable)
- 📝 **Agent Instructions** - Automatically include implementation guidelines
- 🔌 **MCP Integration** - Uses GitHub's official MCP Server for Copilot assignment
- ✨ **Auto-Apply Changes** - Detects Copilot reviews and triggers change application

## 🚀 Quick Start

### 1. Start the Application

```bash
./start.sh
```

This will:
- Create a virtual environment (first run only)
- Install dependencies
- Start the Streamlit server at http://localhost:8642

### 2. Run the Setup Wizard

On first launch, you'll be guided through a 5-step setup wizard:

1. **GitHub Token** - Enter your Personal Access Token
2. **Repository** - Select which repository to automate
3. **Issues** - Choose which issues to add to the queue
4. **Configure** - Set automation preferences (cooldown, auto-merge, etc.)
5. **Complete** - Review and start using the pipeline

### 3. Token Requirements

Your GitHub Personal Access Token needs these permissions:
- `repo` (full control of private repositories)
- `workflow` (if you need to trigger workflows)
- GitHub Copilot subscription (for issue assignment)

## ⚙️ How It Works

### The Automation Loop

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Copilot wants  │ ──► │ Auto-reassign    │ ──► │ Copilot reviews │
│  your review    │     │ review to Copilot│     │ and suggests    │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
┌─────────────────┐     ┌──────────────────┐     ┌────────▼────────┐
│   Start next    │ ◄── │   Auto-merge     │ ◄── │ Auto-apply      │
│   issue         │     │   approved PR    │     │ changes         │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

When the pipeline is running, it polls at regular intervals and:

1. **When Copilot requests your review** → Auto-reassign review to Copilot
2. **When Copilot suggests changes** → Auto-comment "@copilot apply changes"
3. **When PR is approved** → Auto-merge into target branch
4. **When PR is merged** → Wait for cooldown, then assign next issue

### Cooldown System

To prevent overwhelming the system, there's a configurable cooldown between issue assignments:
- Cooldown triggers after a PR is **merged** (not when assigned)
- Other actions (review reassignment, applying changes, merging) have no cooldown
- Adjustable in the UI Settings

## 📁 Project Structure

```
copilot-coding-agent-orchestrator/
├── src/                      # Source code
│   ├── app.py                # Streamlit dashboard
│   ├── setup_wizard.py       # First-time setup
│   ├── daemon.py             # Background daemon
│   ├── automation_engine.py  # Core automation logic
│   ├── github_client.py      # GitHub API client
│   └── mcp_client.py         # MCP protocol client
├── assets/                   # Branding assets
│   ├── swaibian_white.png
│   ├── swaibian_Avatar_white.png
│   └── thankyou.jpg
├── .github/                  # GitHub templates
│   ├── CODEOWNERS
│   ├── CONTRIBUTING.md
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
├── config.example.yaml       # Example configuration
├── .env.example              # Example environment
├── requirements.txt          # Python dependencies
├── start.sh                  # Start script
├── LICENSE                   # MIT License
└── README.md                 # This file
```

## 🔧 Configuration

After running the setup wizard, your `config.yaml` will be generated:

```yaml
github:
  owner: YourUsername
  repo: YourRepo
  target_branch: main

automation:
  poll_interval: 60          # seconds between checks
  auto_merge: true           # auto-merge approved PRs
  auto_assign_next: true     # auto-assign next issue after merge
  cooldown_minutes: 60       # minimum time between assignments

agent_instructions: |
  Your custom implementation instructions...

issue_queue:
  - ISSUE-1
  - ISSUE-2
```

## 🖥️ CLI Usage

Control the daemon directly from the command line:

```bash
# Start daemon
python src/daemon.py start

# Stop daemon
python src/daemon.py stop

# Check status
python src/daemon.py status

# Run automation once
python src/automation_engine.py --once
```

### MCP Client

```bash
# List available tools
python src/mcp_client.py list-tools

# Assign Copilot to an issue
python src/mcp_client.py assign OWNER REPO ISSUE_NUMBER
```

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](.github/CONTRIBUTING.md) first.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add: amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 🔒 Security

Some files are protected and require owner approval to modify:
- `assets/**` - Branding and logos
- `README.md` - Documentation
- `LICENSE` - License file

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Support

If you find this project helpful, consider:

<p align="center">
  <a href="https://github.com/WoDeep/copilot-coding-agent-orchestrator">
    <img src="https://img.shields.io/github/stars/WoDeep/copilot-coding-agent-orchestrator?style=social" alt="Star on GitHub"/>
  </a>
</p>

<p align="center">
  <img src="assets/thankyou.jpg" alt="Thank You" width="200"/>
</p>

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/WoDeep">Swaibian</a>
</p>

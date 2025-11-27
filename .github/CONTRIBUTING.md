# Contributing to Swaibian Agentic Pipeline

Thank you for your interest in contributing! 🎉

## How to Contribute

### Reporting Bugs

1. Check existing issues to avoid duplicates
2. Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md)
3. Include reproduction steps and environment details

### Suggesting Features

1. Use the [feature request template](.github/ISSUE_TEMPLATE/feature_request.md)
2. Explain the use case and expected behavior

### Code Contributions

1. **Fork** the repository
2. **Create a branch** for your feature: `git checkout -b feature/your-feature-name`
3. **Make your changes** in the `src/` directory
4. **Test** your changes locally
5. **Commit** with clear messages: `git commit -m "Add: description of change"`
6. **Push** to your fork: `git push origin feature/your-feature-name`
7. **Create a Pull Request** using our template

### Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/copilot-coding-agent-orchestrator.git
cd copilot-coding-agent-orchestrator

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy example configs
cp config.example.yaml config.yaml
cp .env.example .env

# Run the app
./start.sh
```

### Code Style

- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and small
- Follow PEP 8 guidelines

### Commit Message Format

```
Type: Short description

Longer description if needed.

Types:
- Add: New feature
- Fix: Bug fix
- Update: Improvements to existing features
- Refactor: Code restructuring
- Docs: Documentation changes
```

## Protected Files

The following files are protected and require owner approval:
- `assets/**` - Branding and logos
- `README.md` - Main documentation
- `LICENSE` - License file
- `.github/**` - GitHub configuration

## Questions?

Open an issue or reach out to the maintainers!

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/WoDeep">Swaibian</a>
</p>

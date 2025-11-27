#!/bin/bash
# Start the GitHub Copilot Coding Agent Orchestrator

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

echo "🤖 Starting GitHub Copilot Coding Agent Orchestrator..."
echo "   Open http://localhost:8642 in your browser"
echo ""
echo "   Press Ctrl+C to stop"
echo ""

streamlit run app.py --server.port 8642

#!/bin/bash
# Restart the GitHub Copilot Coding Agent Orchestrator (UI + Daemon)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🔄 Restarting GitHub Copilot Coding Agent Orchestrator..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Stop existing daemon if running
echo "🛑 Stopping existing daemon..."
python3 src/daemon.py stop 2>/dev/null || true
sleep 1

# Kill any existing Streamlit processes on our port
echo "🛑 Stopping existing UI..."
pkill -f "streamlit run src/app.py" 2>/dev/null || true
lsof -ti:8642 | xargs kill -9 2>/dev/null || true
sleep 1

# Start the daemon
echo "🚀 Starting daemon..."
python3 src/daemon.py start
sleep 2

# Check daemon status
if [ -f "daemon.pid" ]; then
    PID=$(cat daemon.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "✅ Daemon started (PID: $PID)"
    else
        echo "⚠️  Daemon may not have started correctly"
    fi
else
    echo "⚠️  Daemon PID file not found"
fi

echo ""
echo "🤖 Starting UI..."
echo "   Open http://localhost:8642 in your browser"
echo ""
echo "   Press Ctrl+C to stop the UI (daemon will continue running)"
echo ""

streamlit run src/app.py --server.port 8642

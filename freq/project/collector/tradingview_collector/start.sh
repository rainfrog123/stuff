#!/bin/bash
# TradingView 5s collector startup script

set -e

PYTHON="/allah/freqtrade/.venv/bin/python3"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SESSION="collector"

# Validate environment
[[ -f "$PYTHON" ]] || { echo "❌ Python not found: $PYTHON"; exit 1; }
[[ -f "$SCRIPT_DIR/main.py" ]] || { echo "❌ main.py not found"; exit 1; }

# Install dependencies if needed
$PYTHON -c "import websocket, pandas, tabulate" 2>/dev/null || {
    echo "📦 Installing dependencies..."
    $PYTHON -m pip install -q websocket-client pandas tabulate
}

# Setup and start
mkdir -p /allah/data/logs
tmux kill-session -t $SESSION 2>/dev/null || true

echo "🚀 Starting TradingView 5s collector..."
tmux new-session -d -s $SESSION "cd $SCRIPT_DIR && $PYTHON main.py"

echo "✅ Started! Commands:"
echo "   📊 View data: $PYTHON viewer.py"  
echo "   🔍 Attach: tmux attach -t $SESSION"
echo "   🛑 Stop: tmux kill-session -t $SESSION"
echo "   📋 Logs: tail -f /allah/data/logs/collector.log" 
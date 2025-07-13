#!/bin/bash
# TradingView 5-second data collector runner

# Paths
FREQTRADE_VENV="/allah/freqtrade/.venv/bin/python3"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
COLLECTOR_SCRIPT="$SCRIPT_DIR/collector_tv.py"
DATA_DIR="$SCRIPT_DIR"
LOGS_DIR="$DATA_DIR/logs"
SESSION_NAME="tv_collector"

# Check requirements
if [ ! -f "$FREQTRADE_VENV" ]; then
    echo "ERROR: Freqtrade venv not found at $FREQTRADE_VENV"
    exit 1
fi

if [ ! -f "$COLLECTOR_SCRIPT" ]; then
    echo "ERROR: collector_tv.py not found"
    exit 1
fi

# Setup directories
mkdir -p "$LOGS_DIR"
chmod 777 "$LOGS_DIR"

# Install dependencies if needed
$FREQTRADE_VENV -c "import websocket, numpy, psutil, memory_profiler, pandas" 2>/dev/null || {
    echo "Installing dependencies..."
    $FREQTRADE_VENV -m pip install websocket-client numpy psutil memory-profiler pandas aiosqlite
}

# Kill existing session and start new one
tmux kill-session -t $SESSION_NAME 2>/dev/null
echo "Starting TradingView 5s data collector..."
tmux new-session -d -s $SESSION_NAME
tmux send-keys -t $SESSION_NAME "cd $SCRIPT_DIR && $FREQTRADE_VENV $COLLECTOR_SCRIPT" Enter

echo "✅ TradingView Data Collector Started!"
echo "📈 Session: $SESSION_NAME"
echo "🔍 Attach: tmux attach -t $SESSION_NAME"
echo "🛑 Stop: tmux kill-session -t $SESSION_NAME"
echo ""
echo "📋 Monitor logs:"
echo "   tail -f $LOGS_DIR/tv_collector.log"
echo ""
echo "🎭 This collector uses:"
echo "   - TradingView WebSocket 5s candles"
echo "   - Millisecond timestamp precision"
echo "   - Direct DB storage via MarketDatabase" 
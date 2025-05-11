#!/bin/bash
# Run script for WebSocket server in tmux

# Set paths
FREQTRADE_VENV="/allah/freqtrade/.venv/bin/python3"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
WEBSOCKET_SCRIPT="$SCRIPT_DIR/db_websocket_server.py"
DATA_DIR="/allah/data"
LOGS_DIR="$DATA_DIR/logs"
SESSION_NAME="ws_server"

# Check if Freqtrade virtual environment exists
if [ ! -f "$FREQTRADE_VENV" ]; then
    echo "Error: Freqtrade virtual environment not found at $FREQTRADE_VENV"
    exit 1
fi

# Create data and logs directories if they don't exist
mkdir -p "$DATA_DIR"
mkdir -p "$LOGS_DIR"

# Check if required Python packages are installed
$FREQTRADE_VENV -m pip install websockets pandas --quiet

# Kill existing tmux session if it exists
tmux kill-session -t $SESSION_NAME 2>/dev/null

# Create a new tmux session
echo "Starting WebSocket server in tmux session: $SESSION_NAME"
echo "This server enables real-time updates from the database to FreqTrade"

# Create detached tmux session
tmux new-session -d -s $SESSION_NAME

# Send command to the session
tmux send-keys -t $SESSION_NAME "$FREQTRADE_VENV $WEBSOCKET_SCRIPT" Enter

echo "WebSocket server started in tmux session."
echo "To attach to the session: tmux attach -t $SESSION_NAME"
echo "To detach from session: press Ctrl+B, then D" 
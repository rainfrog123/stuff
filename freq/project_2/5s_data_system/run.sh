#!/bin/bash
# Run script for 5-second data collection system using WebSockets in tmux

# Set paths
FREQTRADE_VENV="/allah/freqtrade/.venv/bin/python3"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
COLLECTOR_SCRIPT="$SCRIPT_DIR/collector.py"
DATA_DIR="/allah/data"
LOGS_DIR="$DATA_DIR/logs"
SESSION_NAME="data_collector"

# Check if Freqtrade virtual environment exists
if [ ! -f "$FREQTRADE_VENV" ]; then
    echo "Error: Freqtrade virtual environment not found at $FREQTRADE_VENV"
    exit 1
fi

# Create data and logs directories if they don't exist
mkdir -p "$DATA_DIR"
mkdir -p "$LOGS_DIR"

# Set proper permissions for data directory
chmod 777 "$DATA_DIR"
chmod 777 "$LOGS_DIR"

# Kill existing tmux session if it exists
tmux kill-session -t $SESSION_NAME 2>/dev/null

# Create a new tmux session
echo "Starting 5-second data collection system in tmux session: $SESSION_NAME"
echo "Data will be saved to $DATA_DIR"
echo "Logs will be saved to $LOGS_DIR"
echo "Only keeping 10 minutes of 5s data"

# Create detached tmux session
tmux new-session -d -s $SESSION_NAME

# Send command to the session
tmux send-keys -t $SESSION_NAME "$FREQTRADE_VENV $COLLECTOR_SCRIPT" Enter

echo "Data collector started in tmux session."
echo "To attach to the session: tmux attach -t $SESSION_NAME"
echo "To detach from session: press Ctrl+B, then D" 
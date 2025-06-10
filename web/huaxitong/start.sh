#!/bin/bash

# Appointment Monitor Startup Script
# This script starts the appointment monitor in a tmux session

SESSION_NAME="appointment_monitor"
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
PYTHON_PATH="/allah/freqtrade/.venv/bin/python3"

echo "🚀 Starting monitor..."

# Check if tmux is installed
if ! command -v tmux &> /dev/null; then
    echo "❌ Error: tmux is not installed. Please install it first:"
    echo "   sudo apt-get install tmux"
    exit 1
fi

# Check if Python virtual environment exists
if [ ! -f "$PYTHON_PATH" ]; then
    echo "❌ Error: Python virtual environment not found at $PYTHON_PATH"
    echo "   Please check the path or create the virtual environment"
    exit 1
fi

# Check if monitor script exists
if [ ! -f "$SCRIPT_DIR/monitor_appointments.py" ]; then
    echo "❌ Error: monitor_appointments.py not found in $SCRIPT_DIR"
    exit 1
fi

# Kill existing session if it exists
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "🔄 Killing existing session: $SESSION_NAME"
    tmux kill-session -t "$SESSION_NAME"
fi

# Install requirements if requirements.txt exists
if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    cd "$SCRIPT_DIR"
    $PYTHON_PATH -m pip install -r requirements.txt > /dev/null 2>&1
fi

# Create new tmux session and start the monitor
tmux new-session -d -s "$SESSION_NAME" -c "$SCRIPT_DIR"
tmux send-keys -t "$SESSION_NAME" "cd '$SCRIPT_DIR'" Enter
tmux send-keys -t "$SESSION_NAME" "$PYTHON_PATH monitor_appointments.py" Enter

echo "✅ Monitor started in tmux session: $SESSION_NAME"
echo ""
echo "📋 Useful commands:"
echo "   tail -f $SCRIPT_DIR/reg.log          # Monitor regular logs"
echo "   tail -f $SCRIPT_DIR/success.log      # Monitor success alerts"  
echo "   tail -f $SCRIPT_DIR/reg.log $SCRIPT_DIR/success.log  # Monitor both"
echo "   tmux attach -t $SESSION_NAME         # View monitor session"
echo "   ./stop.sh                            # Stop monitor" 
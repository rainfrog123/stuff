#!/bin/bash

# Stop Appointment Monitor Script

SESSION_NAME="appointment_monitor"
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

echo "🛑 Stopping monitor..."

# Check if session exists
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    tmux kill-session -t "$SESSION_NAME"
    echo "✅ Monitor stopped"
else
    echo "ℹ️  No active session found"
fi

# Clear log files
cd "$SCRIPT_DIR"
> success.log
> reg.log
echo "🧹 Logs cleared" 
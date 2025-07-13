#!/bin/bash

# Stop Hospital Monitor Script with Safety Monitor Cleanup

SESSION_NAME="hospital_monitor"
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
SAFETY_PID_FILE="$SCRIPT_DIR/.monitor_safety.pid"

echo "🛑 Stopping hospital monitor and safety systems..."

# Stop safety monitor first
if [ -f "$SAFETY_PID_FILE" ]; then
    safety_pid=$(cat "$SAFETY_PID_FILE" 2>/dev/null)
    if [ -n "$safety_pid" ] && kill -0 "$safety_pid" 2>/dev/null; then
        echo "🛡️ Stopping safety monitor (PID: $safety_pid)..."
        kill "$safety_pid" 2>/dev/null
        sleep 2
        # Force kill if still running
        if kill -0 "$safety_pid" 2>/dev/null; then
            kill -9 "$safety_pid" 2>/dev/null
        fi
    fi
    rm -f "$SAFETY_PID_FILE"
    echo "✅ Safety monitor stopped"
else
    echo "ℹ️ No safety monitor PID file found"
fi

# Check if session exists and stop it
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "🔄 Stopping tmux session: $SESSION_NAME"
    tmux kill-session -t "$SESSION_NAME"
    echo "✅ Monitor session stopped"
else
    echo "ℹ️ No active monitor session found"
fi

# Kill any remaining monitoring processes as backup
monitor_pids=$(pgrep -f "hospital_monitor.py" 2>/dev/null)
if [ -n "$monitor_pids" ]; then
    echo "🧹 Cleaning up remaining monitor processes..."
    echo "$monitor_pids" | xargs kill 2>/dev/null
    sleep 2
    # Force kill if still running
    remaining_pids=$(pgrep -f "hospital_monitor.py" 2>/dev/null)
    if [ -n "$remaining_pids" ]; then
        echo "$remaining_pids" | xargs kill -9 2>/dev/null
    fi
    echo "✅ Cleanup completed"
fi

# Clear log files
cd "$SCRIPT_DIR"
if [ -f "success.log" ]; then
    > success.log
    echo "🧹 success.log cleared"
fi
if [ -f "reg.log" ]; then
    > reg.log
    echo "🧹 reg.log cleared"
fi

echo "✅ 🦷 Hospital monitor systems stopped and cleaned up" 
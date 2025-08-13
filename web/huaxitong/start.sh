#!/bin/bash

# Appointment Monitor Startup Script with Safety Protection
# This script starts the appointment monitor in a tmux session with built-in safety limits

SESSION_NAME="appointment_monitor"
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
PYTHON_PATH="/allah/freqtrade/.venv/bin/python3"

# 🛡️ SAFETY CONFIGURATION
MAX_RUNTIME_HOURS=24
MAX_CPU_PERCENT=30
MAX_MEMORY_MB=200
MAX_LOG_SIZE_MB=50
SAFETY_CHECK_INTERVAL=60
SAFETY_PID_FILE="$SCRIPT_DIR/.monitor_safety.pid"

echo "🚀 Starting monitor with safety protection..."

# Function to check if process is running
check_process() {
    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        return 0
    fi
    return 1
}

# Function to get resource usage
get_resource_usage() {
    local pid=$(tmux list-panes -t "$SESSION_NAME" -F "#{pane_pid}" 2>/dev/null)
    if [ -n "$pid" ]; then
        # Get child Python process
        local python_pid=$(pgrep -P "$pid" python3 2>/dev/null | head -1)
        if [ -n "$python_pid" ]; then
            local cpu=$(ps -p "$python_pid" -o %cpu= 2>/dev/null | tr -d ' ')
            local mem=$(ps -p "$python_pid" -o rss= 2>/dev/null | tr -d ' ')
            local mem_mb=$((mem / 1024))
            echo "$cpu,$mem_mb"
            return 0
        fi
    fi
    echo "0,0"
    return 1
}

# Function to check log file sizes
check_log_sizes() {
    local reg_size=0
    local success_size=0
    
    if [ -f "$SCRIPT_DIR/reg.log" ]; then
        reg_size=$(du -m "$SCRIPT_DIR/reg.log" 2>/dev/null | cut -f1)
    fi
    if [ -f "$SCRIPT_DIR/success.log" ]; then
        success_size=$(du -m "$SCRIPT_DIR/success.log" 2>/dev/null | cut -f1)
    fi
    
    if (( reg_size > MAX_LOG_SIZE_MB || success_size > MAX_LOG_SIZE_MB )); then
        echo "Log files too large: reg.log=${reg_size}MB, success.log=${success_size}MB"
        return 1
    fi
    return 0
}

# Safety monitoring function (runs in background)
safety_monitor() {
    local start_time=$(date +%s)
    local check_count=0
    
    # Create PID file
    echo $$ > "$SAFETY_PID_FILE"
    
    echo "🛡️ Safety monitor started (PID: $$)"
    
    while true; do
        sleep $SAFETY_CHECK_INTERVAL
        check_count=$((check_count + 1))
        current_time=$(date +%s)
        runtime_hours=$(( (current_time - start_time) / 3600 ))
        
        # Check if main session still exists
        if ! check_process; then
            echo "ℹ️ Monitor session ended normally"
            break
        fi
        
        # Get resource usage
        IFS=',' read -r cpu_usage mem_usage <<< "$(get_resource_usage)"
        
        # Check various limits
        exceeded=""
        if (( runtime_hours >= MAX_RUNTIME_HOURS )); then
            exceeded="Runtime limit exceeded (${runtime_hours}h >= ${MAX_RUNTIME_HOURS}h)"
        elif (( $(echo "$cpu_usage > $MAX_CPU_PERCENT" | bc -l 2>/dev/null || echo 0) )); then
            exceeded="CPU limit exceeded (${cpu_usage}% > ${MAX_CPU_PERCENT}%)"
        elif (( mem_usage > MAX_MEMORY_MB )); then
            exceeded="Memory limit exceeded (${mem_usage}MB > ${MAX_MEMORY_MB}MB)"
        elif ! check_log_sizes; then
            exceeded="Log size limit exceeded (>${MAX_LOG_SIZE_MB}MB)"
        fi
        
        if [ -n "$exceeded" ]; then
            echo "🚨 SAFETY LIMIT EXCEEDED: $exceeded"
            echo "⛔ Automatically stopping monitor for safety..."
            
            # Kill the monitor session
            tmux kill-session -t "$SESSION_NAME" 2>/dev/null
            
            # Clean up logs
            echo "🧹 Cleaning up oversized logs..."
            if [ -f "$SCRIPT_DIR/reg.log" ]; then
                tail -n 1000 "$SCRIPT_DIR/reg.log" > "$SCRIPT_DIR/reg.log.tmp" && mv "$SCRIPT_DIR/reg.log.tmp" "$SCRIPT_DIR/reg.log"
            fi
            if [ -f "$SCRIPT_DIR/success.log" ]; then
                tail -n 1000 "$SCRIPT_DIR/success.log" > "$SCRIPT_DIR/success.log.tmp" && mv "$SCRIPT_DIR/success.log.tmp" "$SCRIPT_DIR/success.log"
            fi
            
            echo "⛔ Monitor terminated automatically due to safety limits"
            break
        fi
        
        # Status update every 10 checks (10 minutes by default)
        if (( check_count % 10 == 0 )); then
            timestamp=$(date '+%Y-%m-%d %H:%M:%S')
            echo "📊 [$timestamp] Safety check #${check_count}: Runtime ${runtime_hours}h, CPU ${cpu_usage}%, RAM ${mem_usage}MB ✅"
        fi
    done
    
    # Clean up PID file
    rm -f "$SAFETY_PID_FILE"
    echo "🛡️ Safety monitor stopped"
}

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

# Check if bc is available for floating point comparisons
if ! command -v bc &> /dev/null; then
    echo "⚠️ Warning: 'bc' not found, installing for safety calculations..."
    apt-get update && apt-get install -y bc >/dev/null 2>&1
fi

# Kill existing session if it exists
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "🔄 Killing existing session: $SESSION_NAME"
    tmux kill-session -t "$SESSION_NAME"
fi

# Kill existing safety monitor if running
if [ -f "$SAFETY_PID_FILE" ]; then
    old_safety_pid=$(cat "$SAFETY_PID_FILE" 2>/dev/null)
    if [ -n "$old_safety_pid" ] && kill -0 "$old_safety_pid" 2>/dev/null; then
        echo "🔄 Stopping existing safety monitor (PID: $old_safety_pid)"
        kill "$old_safety_pid" 2>/dev/null
    fi
    rm -f "$SAFETY_PID_FILE"
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

# Start safety monitor in background
safety_monitor &
SAFETY_MONITOR_PID=$!

echo "✅ Monitor started in tmux session: $SESSION_NAME"
echo "🛡️ Safety monitor active (PID: $SAFETY_MONITOR_PID) with limits:"
echo "   📊 Max CPU: ${MAX_CPU_PERCENT}%"
echo "   🧠 Max Memory: ${MAX_MEMORY_MB}MB"
echo "   ⏱️ Max Runtime: ${MAX_RUNTIME_HOURS}h"
echo "   📄 Max Log Size: ${MAX_LOG_SIZE_MB}MB"
echo "   🔍 Check Interval: ${SAFETY_CHECK_INTERVAL}s"
echo ""
echo "📋 Useful commands:"
echo "   tail -f $SCRIPT_DIR/reg.log          # Monitor regular logs"
echo "   tail -f $SCRIPT_DIR/success.log      # Monitor success alerts"  
echo "   tail -f $SCRIPT_DIR/reg.log $SCRIPT_DIR/success.log  # Monitor both"
echo "   tmux attach -t $SESSION_NAME         # View monitor session"
echo "   ./stop.sh                            # Stop monitor"
echo "   ps aux | grep monitor                # Check safety monitor"
echo ""
echo "🚨 The safety monitor will automatically stop the process if limits are exceeded!" 
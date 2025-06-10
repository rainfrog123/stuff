#!/bin/bash

# Restart Appointment Monitor Script
# Stops the current monitor and starts a fresh one

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

echo "🔄 Restarting monitor..."

# Stop the monitor and clear logs  
"$SCRIPT_DIR/stop.sh"

# Brief pause to ensure clean shutdown
sleep 1

# Start the monitor
"$SCRIPT_DIR/start.sh"

echo "🎉 Restart completed!" 
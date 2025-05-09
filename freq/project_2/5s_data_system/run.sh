#!/bin/bash
# Run script for 5-second data collection system

# Set paths
FREQTRADE_VENV="/allah/freqtrade/.venv/bin/python3"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
COLLECTOR_SCRIPT="$SCRIPT_DIR/collector.py"

# Check if Freqtrade virtual environment exists
if [ ! -f "$FREQTRADE_VENV" ]; then
    echo "Error: Freqtrade virtual environment not found at $FREQTRADE_VENV"
    exit 1
fi

# Create data and logs directories if they don't exist
mkdir -p "$SCRIPT_DIR/data"
mkdir -p "$SCRIPT_DIR/logs"

# Activate virtual environment and run collector
echo "Starting 5-second data collection system..."
exec "$FREQTRADE_VENV" "$COLLECTOR_SCRIPT" 
#!/bin/bash
# Run script for 5-second data viewer

# Set paths
FREQTRADE_VENV="/allah/freqtrade/.venv/bin/python3"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VIEWER_SCRIPT="$SCRIPT_DIR/view_data.py"
DATA_DIR="/allah/data"
LOGS_DIR="$DATA_DIR/logs"

# Check if Freqtrade virtual environment exists
if [ ! -f "$FREQTRADE_VENV" ]; then
    echo "Error: Freqtrade virtual environment not found at $FREQTRADE_VENV"
    exit 1
fi

# Check if data directory exists
if [ ! -d "$DATA_DIR" ]; then
    echo "Warning: Data directory at $DATA_DIR does not exist. Data access may fail."
fi

# Execute viewer with arguments
echo "Accessing market data from $DATA_DIR"
echo "Logs located at $LOGS_DIR"
exec "$FREQTRADE_VENV" "$VIEWER_SCRIPT" "$@" 
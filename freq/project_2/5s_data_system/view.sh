#!/bin/bash
# Run script for 5-second data viewer

# Set paths
FREQTRADE_VENV="/allah/freqtrade/.venv/bin/python3"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VIEWER_SCRIPT="$SCRIPT_DIR/view_data.py"

# Check if Freqtrade virtual environment exists
if [ ! -f "$FREQTRADE_VENV" ]; then
    echo "Error: Freqtrade virtual environment not found at $FREQTRADE_VENV"
    exit 1
fi

# Execute viewer with arguments
exec "$FREQTRADE_VENV" "$VIEWER_SCRIPT" "$@" 
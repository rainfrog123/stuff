#!/bin/bash
# Run the 5s trade collector using FreqTrade's Python environment

# Default config file
CONFIG_FILE="sample_config.json"

# Path to FreqTrade's virtual environment Python
FREQTRADE_PYTHON="/allah/freqtrade/.venv/bin/python3"

# Function to show usage
function show_usage {
  echo "Usage: $0 [options]"
  echo "Options:"
  echo "  -c, --config CONFIG_FILE  Use specific config file (default: sample_config.json)"
  echo "  -d, --daemon              Run as daemon process"
  echo "  -h, --help                Show this help message"
  echo ""
  echo "Example:"
  echo "  $0 --config my_config.json --daemon"
}

# Parse command line arguments
DAEMON_MODE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -c|--config)
      if [[ -n "$2" && "$2" != -* ]]; then
        CONFIG_FILE="$2"
        shift 2
      else
        echo "Error: config file name is required"
        show_usage
        exit 1
      fi
      ;;
    -d|--daemon)
      DAEMON_MODE="--daemon"
      shift
      ;;
    -h|--help)
      show_usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      show_usage
      exit 1
      ;;
  esac
done

# Check if config file exists
if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "Error: Config file $CONFIG_FILE not found"
  exit 1
fi

# Read config from JSON file
if ! command -v jq &> /dev/null; then
  echo "Warning: jq not installed, using default configuration"
  echo "Running: $FREQTRADE_PYTHON trade_collector.py $DAEMON_MODE"
  $FREQTRADE_PYTHON trade_collector.py $DAEMON_MODE
  exit $?
fi

# Extract configuration using jq
EXCHANGE=$(jq -r '.exchange // "binance"' "$CONFIG_FILE")
PAIRS=$(jq -r '.pairs | map(@sh) | join(" ")' "$CONFIG_FILE" | tr -d \'\")
DB_PATH=$(jq -r '.db_path // "user_data/data/5s_candles.sqlite"' "$CONFIG_FILE")
API_KEY=$(jq -r '.api_key // ""' "$CONFIG_FILE")
API_SECRET=$(jq -r '.api_secret // ""' "$CONFIG_FILE")
UPDATE_INTERVAL=$(jq -r '.update_interval // 5' "$CONFIG_FILE")
RETENTION_DAYS=$(jq -r '.retention_days // 14' "$CONFIG_FILE")
ENABLE_WS=$(jq -r '.enable_websocket // true' "$CONFIG_FILE")
HISTORY_HOURS=$(jq -r '.initial_history_hours // 24' "$CONFIG_FILE")

# Build the command
CMD="$FREQTRADE_PYTHON trade_collector.py --exchange $EXCHANGE --pairs $PAIRS --db-path $DB_PATH"

# Add optional parameters
[[ -n "$API_KEY" && "$API_KEY" != "YOUR_API_KEY_HERE" ]] && CMD="$CMD --api-key $API_KEY"
[[ -n "$API_SECRET" && "$API_SECRET" != "YOUR_API_SECRET_HERE" ]] && CMD="$CMD --api-secret $API_SECRET"
[[ -n "$UPDATE_INTERVAL" ]] && CMD="$CMD --update-interval $UPDATE_INTERVAL"
[[ -n "$RETENTION_DAYS" ]] && CMD="$CMD --retention-days $RETENTION_DAYS"
[[ "$ENABLE_WS" == "false" ]] && CMD="$CMD --disable-websocket"
[[ -n "$HISTORY_HOURS" ]] && CMD="$CMD --history-hours $HISTORY_HOURS"
[[ -n "$DAEMON_MODE" ]] && CMD="$CMD $DAEMON_MODE"

# Display the command (hide API credentials)
DISPLAY_CMD=$(echo "$CMD" | sed -E 's/--api-(key|secret) [^ ]+/--api-\1 ****/g')
echo "Running: $DISPLAY_CMD"

# Execute the command
$CMD
exit $? 
# 5-Second Data Collection System

This system collects real-time trading data at 5-second intervals using Binance's WebSocket API through ccxtpro. It stores both raw trade data and aggregated 5-second candles in a local SQLite database for later use with trading algorithms.

## Features

- Real-time collection of trade data via WebSocket connections
- Automatic aggregation of trades into 5-second candles
- Persistent storage in SQLite database
- Support for multiple trading pairs
- Automatic reconnection on WebSocket disconnects
- Historical data backfilling on startup
- Data maintenance to limit storage consumption
- Utilities for data export and resampling to higher timeframes

## Directory Structure

```
5s_data_system/
├── config.py           # Configuration settings
├── database.py         # Database operations
├── collector.py        # Main data collection system
├── data_access.py      # Utilities for accessing stored data
├── data/               # Directory for the SQLite database
└── logs/               # Log files
```

## Installation

1. Make sure you have Python 3.8+ installed

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Configure your API credentials and other settings in `config.py`

## Usage

### Starting the Data Collector

```bash
python collector.py
```

This will:
1. Connect to the exchange using the provided API credentials
2. Fetch historical data for initialization
3. Start WebSocket connections for real-time data
4. Process and store both trades and candles in the database

### Accessing Collected Data

You can use the `data_access.py` module to retrieve and export data:

```python
from data_access import DataAccess
from datetime import datetime, timedelta

# Initialize data access
data = DataAccess()

# Get information about available data
info = data.get_latest_data_info()
print(info)

# Get 5-second candles for a symbol
symbol = "ETH/USDT"
end_time = datetime.now()
start_time = end_time - timedelta(hours=1)  # Last hour
candles = data.get_candles(symbol, start_time, end_time)

# Resample to a higher timeframe
candles_1m = data.resample_candles(symbol, "1m", start_time, end_time)

# Export to CSV
data.export_to_csv(symbol, data_type="candles", timeframe="5s", 
                   start_time=start_time, end_time=end_time)
```

## Configuration

Edit the `config.py` file to customize:

- Exchange credentials
- Trading pairs to collect
- Data storage settings
- Logging options
- Reconnection parameters

## Database Schema

### Trades Table
- `id`: Trade ID (primary key)
- `symbol`: Trading pair symbol
- `timestamp`: Unix timestamp in milliseconds
- `datetime`: Human-readable date and time
- `price`: Trade price
- `amount`: Trade amount
- `side`: Buy or sell
- `info`: Additional trade information (JSON)

### Candles Table
- `id`: Auto-incrementing ID (primary key)
- `symbol`: Trading pair symbol
- `timestamp`: Unix timestamp in milliseconds
- `datetime`: Human-readable date and time
- `open`: Opening price
- `high`: Highest price
- `low`: Lowest price
- `close`: Closing price
- `volume`: Trading volume

## Integration with Trading Strategies

The collected 5-second data can be easily integrated with trading strategies:

1. Use the `data_access.py` module to load historical data
2. Implement technical indicators on the 5-second timeframe
3. Test strategies that can benefit from faster reaction times

## Troubleshooting

- Check the log files in the `logs/` directory for detailed information
- If the WebSocket connections are unstable, adjust the reconnection parameters in `config.py`
- For database performance issues, consider pruning older data more aggressively 
# 5-Second Candle Data Collector for FreqTrade

This package provides a solution for using 5-second OHLCV candles in FreqTrade strategies, which is not natively supported by most exchanges.

## Overview

The system consists of two main components:

1. **Trade Collector (`trade_collector.py`)**: A standalone process that continuously fetches trade data from exchanges and converts them into 5-second candles stored in a SQLite database.

2. **FreqTrade Adapter (`freqtrade_adapter.py`)**: A custom data provider for FreqTrade that reads from the 5s candle database and makes the data available to your strategies.

This approach allows you to:
- Use 5-second candles in your strategies for ultra-short timeframe trading
- Maintain a continuous history of 5s candles even when exchanges don't provide them
- Run your strategies with a mix of standard timeframes (1m, 5m, etc.) and custom 5s data

## Installation

1. Create the data collector directory in your FreqTrade installation:

```bash
mkdir -p user_data/data_collector
```

2. Copy the files from this repository to your FreqTrade installation:

```bash
cp trade_collector.py user_data/data_collector/
cp freqtrade_adapter.py user_data/
```

3. Make the collector executable:

```bash
chmod +x user_data/data_collector/trade_collector.py
```

## Usage

### Step 1: Start the Data Collector

The data collector needs to run continuously to collect trade data and generate 5s candles:

```bash
cd user_data/data_collector
./trade_collector.py --exchange binance --pairs BTC/USDT:USDT ETH/USDT:USDT
```

Options:
- `--exchange`: Exchange name (default: binance)
- `--pairs`: Trading pairs to collect data for
- `--db-path`: Path to the SQLite database (default: ../user_data/data/5s_candles.sqlite)
- `--update-interval`: Seconds between updates (default: 5)
- `--retention-days`: Days to keep data (default: 14, use 0 to keep forever)
- `--history-hours`: Hours of historical data to fetch on startup (default: 24)
- `--daemon`: Run as a daemon process

For production use, you should run the collector as a background service. Here's an example using systemd:

```
[Unit]
Description=FreqTrade 5s Candle Collector
After=network.target

[Service]
User=yourusername
WorkingDirectory=/path/to/freqtrade/user_data/data_collector
ExecStart=/path/to/freqtrade/.venv/bin/python3 trade_collector.py --exchange binance --pairs BTC/USDT:USDT ETH/USDT:USDT --daemon
Restart=always
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

### Step 2: Configure FreqTrade

Modify your FreqTrade config.json to use the custom data provider:

```json
{
    "max_open_trades": 10,
    "stake_currency": "USDT",
    "stake_amount": "unlimited",
    "timeframe": "1m",
    
    "data_provider": {
        "class": "user_data.freqtrade_adapter:External5sDataProvider",
        "config": {
            "db_path": "user_data/data/5s_candles.sqlite",
            "lookback_candles": 100,
            "cache_timeout": 5
        }
    },
    
    "exchange": {
        "name": "binance",
        "key": "your-api-key",
        "secret": "your-api-secret",
        "pair_whitelist": [
            "BTC/USDT:USDT",
            "ETH/USDT:USDT"
        ]
    }
}
```

### Step 3: Create a Strategy Using 5s Data

Create a strategy that uses both standard timeframes and 5s data:

```python
from freqtrade.strategy import IStrategy
import talib.abstract as ta
from functools import reduce

class FiveSecondScalper(IStrategy):
    timeframe = '1m'  # Required standard timeframe
    
    # Strategy parameters
    buy_rsi = 30
    sell_rsi = 70
    
    minimal_roi = {
        "0": 0.005
    }
    stoploss = -0.01
    
    def populate_indicators(self, dataframe, metadata):
        # Standard 1m indicators
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # Get 5s dataframe if available
        if hasattr(self, 'dp_5s') and self.dp_5s:
            try:
                # Get 5s data
                df_5s = self.dp_5s.get_5s_dataframe(metadata['pair'])
                
                if not df_5s.empty:
                    # Calculate 5s-specific indicators
                    df_5s['rsi_5s'] = ta.RSI(df_5s, timeperiod=7)
                    
                    # Get latest 5s values
                    latest_5s = df_5s.iloc[-1].to_dict()
                    
                    # Add 5s indicators to 1m dataframe
                    dataframe['rsi_5s'] = latest_5s['rsi_5s']
                    dataframe['5s_close'] = latest_5s['close']
                    
            except Exception as e:
                print(f"Error processing 5s data: {e}")
                
        return dataframe
    
    def populate_buy_trend(self, dataframe, metadata):
        conditions = []
        
        # If 5s data is available, use it
        if 'rsi_5s' in dataframe.columns:
            conditions.append(dataframe['rsi_5s'] < self.buy_rsi)
        else:
            conditions.append(dataframe['rsi'] < self.buy_rsi)
        
        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'buy'
            ] = 1
        
        return dataframe
    
    def populate_sell_trend(self, dataframe, metadata):
        conditions = []
        
        # If 5s data is available, use it
        if 'rsi_5s' in dataframe.columns:
            conditions.append(dataframe['rsi_5s'] > self.sell_rsi)
        else:
            conditions.append(dataframe['rsi'] > self.sell_rsi)
        
        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'sell'
            ] = 1
        
        return dataframe
```

## Testing 5s Data Availability

You can test if 5s data is available by running:

```bash
cd user_data
python freqtrade_adapter.py
```

This will show information about the available 5s candles in the database.

## Limitations

- Not all exchanges provide comprehensive trade history
- During periods of low trading volume, there might be gaps in the 5s candle data
- Higher resource usage compared to standard FreqTrade (CPU, memory, and disk space)
- The system requires running an additional process (the data collector)

## Troubleshooting

1. **No 5s data available**: Make sure the trade collector is running and has collected enough data.

2. **Database not found**: Check the path to the SQLite database in both the collector and FreqTrade config.

3. **Missing trade history**: Some exchanges limit the amount of trade history you can fetch. Adjust the `--history-hours` parameter accordingly.

4. **High CPU usage**: Decrease the update frequency by increasing the `--update-interval` parameter.

5. **Missing data for a pair**: Verify the pair is correctly specified and that the exchange has sufficient trading volume.

## Database Maintenance

The collector automatically manages database size by removing old data based on the retention period. You can also manually manage the database using SQLite tools:

```bash
# Vacuum the database to reclaim disk space
sqlite3 user_data/data/5s_candles.sqlite "VACUUM;"

# Check database size
du -h user_data/data/5s_candles.sqlite
```

## Advanced Uses

- Use WebSocket connections for even faster data collection (implement in the `_init_websocket` method)
- Implement additional indicators specific to 5s timeframes
- Combine multiple timeframes (e.g., 5s, 1m, and 5m) for sophisticated strategies
- Add additional data sources beyond trades (order book depth, etc.)

## License

This project is licensed under MIT License. 
#!/usr/bin/env python3
"""
CCXT Historical and Recent Trades Demo
This script demonstrates how to properly fetch both historical and recent trades using CCXT
"""

import ccxt
import time
from datetime import datetime, timedelta
import pandas as pd
from pprint import pprint

# Initialize Binance exchange
exchange = ccxt.binance({
    'enableRateLimit': True,
})

symbol = 'BTC/USDT'

print(f"Fetching trades for {symbol}")

# PART 1: Fetch the most recent trades (newest first)
print("\n--- Most Recent Trades ---")
recent_trades = exchange.fetch_trades(symbol, limit=5)
for trade in recent_trades:
    print(f"ID: {trade['id']}, Timestamp: {datetime.fromtimestamp(trade['timestamp']/1000).strftime('%Y-%m-%d %H:%M:%S.%f')}, Price: {trade['price']}, Amount: {trade['amount']}")

# PART 2: Fetch historical trades using 'since' parameter
print("\n--- Historical Trades ---")
# Get timestamp for 30 minutes ago
since_ts = int((datetime.now() - timedelta(minutes=30)).timestamp() * 1000)
print(f"Fetching trades since: {datetime.fromtimestamp(since_ts/1000).strftime('%Y-%m-%d %H:%M:%S')}")

historical_trades = exchange.fetch_trades(symbol, since=since_ts, limit=5)
for trade in historical_trades:
    print(f"ID: {trade['id']}, Timestamp: {datetime.fromtimestamp(trade['timestamp']/1000).strftime('%Y-%m-%d %H:%M:%S.%f')}, Price: {trade['price']}, Amount: {trade['amount']}")

# PART 3: Pagination example for fetching multiple pages of historical data
print("\n--- Pagination Example ---")
all_trades = []
since = since_ts
for i in range(3):  # Fetch 3 pages
    print(f"Fetching page {i+1} from timestamp {datetime.fromtimestamp(since/1000).strftime('%Y-%m-%d %H:%M:%S')}")
    trades = exchange.fetch_trades(symbol, since=since, limit=100)
    if not trades:
        print("No more trades to fetch")
        break
    
    all_trades.extend(trades)
    print(f"Got {len(trades)} trades")
    
    # For the next iteration, use the timestamp of the last trade + 1ms
    since = trades[-1]['timestamp'] + 1
    
    # Respect rate limits with a small delay between requests
    time.sleep(exchange.rateLimit / 1000)

print(f"Total trades fetched across pages: {len(all_trades)}")
if all_trades:
    oldest = datetime.fromtimestamp(all_trades[0]['timestamp']/1000).strftime('%Y-%m-%d %H:%M:%S.%f')
    newest = datetime.fromtimestamp(all_trades[-1]['timestamp']/1000).strftime('%Y-%m-%d %H:%M:%S.%f')
    print(f"Timespan: {oldest} to {newest}")

# PART 4: Converting trades to 5-second candles
print("\n--- Converting Trades to 5-Second Candles ---")
if all_trades:
    # Convert trades to DataFrame
    df = pd.DataFrame(all_trades)
    
    # Convert timestamp to datetime
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # Create 5-second bins
    df.set_index('datetime', inplace=True)
    
    # Resample to 5-second candles
    ohlcv = df.resample('5S').agg({
        'price': ['first', 'max', 'min', 'last'],
        'amount': 'sum',
        'cost': 'sum'  # cost is price * amount
    })
    
    # Flatten column names
    ohlcv.columns = ['open', 'high', 'low', 'close', 'volume', 'cost']
    
    # Remove rows with NaN values (periods with no trades)
    ohlcv = ohlcv.dropna()
    
    print(f"Generated {len(ohlcv)} 5-second candles")
    print(ohlcv.head()) 
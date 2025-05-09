#!/usr/bin/env python3
import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time

def get_1s_candles(exchange_id, symbol, start_time, end_time=None, limit=1000):
    """
    Fetch 1-second candles from the exchange
    """
    # Initialize exchange
    exchange_class = getattr(ccxt, exchange_id)
    exchange = exchange_class({
        'enableRateLimit': True,  # Important to avoid rate limits
    })
    
    # Check if exchange supports fetchOHLCV
    if not exchange.has['fetchOHLCV']:
        raise Exception(f"{exchange_id} does not support fetchOHLCV")
    
    # Check timeframes supported by the exchange
    if '1s' not in exchange.timeframes:
        print(f"Available timeframes: {exchange.timeframes}")
        raise Exception(f"{exchange_id} does not support 1s timeframe")
    
    # Convert datetime to timestamp in ms
    since = int(start_time.timestamp() * 1000)
    if end_time:
        until = int(end_time.timestamp() * 1000)
    else:
        until = int(datetime.now().timestamp() * 1000)
    
    print(f"Fetching 1s candles for {symbol} from {start_time} to {end_time or 'now'}")
    
    # Fetch candles
    candles = []
    current_since = since
    
    while current_since < until:
        try:
            new_candles = exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe='1s',
                since=current_since,
                limit=limit
            )
            
            if not new_candles:
                break
                
            candles.extend(new_candles)
            
            # Update the since parameter for the next iteration
            if len(new_candles) > 0:
                current_since = new_candles[-1][0] + 1  # Add 1ms to avoid duplicates
            else:
                break
                
            print(f"Fetched {len(new_candles)} candles. Total: {len(candles)}")
            
            # Respect rate limits
            time.sleep(exchange.rateLimit / 1000)
            
        except Exception as e:
            print(f"Error fetching candles: {e}")
            break
    
    # Convert to DataFrame
    if candles:
        df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    else:
        return pd.DataFrame()

def aggregate_to_5s(df_1s):
    """
    Aggregate 1-second candles to 5-second candles
    """
    if df_1s.empty:
        return pd.DataFrame()
    
    # Make sure the data is sorted by timestamp
    df_1s = df_1s.sort_values('timestamp')
    
    # Create 5-second groups based on timestamp
    df_1s['group'] = (df_1s['timestamp'] // 5000) * 5000
    
    # Aggregate data
    df_5s = df_1s.groupby('group').agg({
        'timestamp': 'first',
        'datetime': 'first',
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).reset_index(drop=True)
    
    return df_5s

def main():
    # Exchange configuration
    exchange_id = 'binance'  # or 'kucoin', 'bybit', etc.
    symbol = 'BTC/USDT'
    start_time = datetime.now() - timedelta(minutes=5)  # Get data from the last 5 minutes
    
    try:
        # Try to fetch 1-second data
        df_1s = get_1s_candles(exchange_id, symbol, start_time)
        
        if df_1s.empty:
            print(f"No 1-second data available from {exchange_id} for {symbol}")
            return
            
        print("\n--- 1-second candles sample ---")
        print(df_1s.head())
        
        # Aggregate to 5-second
        df_5s = aggregate_to_5s(df_1s)
        
        print("\n--- Aggregated 5-second candles sample ---")
        print(df_5s.head())
        
        print(f"\nSuccessfully fetched {len(df_1s)} 1s candles and aggregated to {len(df_5s)} 5s candles")
        
    except Exception as e:
        print(f"ERROR: {e}")
        
        # If 1s not available, check what timeframes are available
        try:
            exchange_class = getattr(ccxt, exchange_id)
            exchange = exchange_class({'enableRateLimit': True})
            print(f"\nTimeframes supported by {exchange_id}:")
            print(exchange.timeframes)
        except Exception as e2:
            print(f"Could not get timeframes: {e2}")

if __name__ == "__main__":
    main() 
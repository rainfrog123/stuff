#!/usr/bin/env python3
import ccxt
import pandas as pd
from datetime import datetime, timedelta
import time

def fetch_live_1s_data(exchange_id='binance', symbol='BTC/USDT', limit=10):
    """
    Fetch the most recent 1-second candles from the exchange
    """
    # Initialize exchange
    exchange_class = getattr(ccxt, exchange_id)
    exchange = exchange_class({
        'enableRateLimit': True,
    })
    
    # Check if exchange supports fetchOHLCV
    if not exchange.has['fetchOHLCV']:
        raise Exception(f"{exchange_id} does not support fetchOHLCV")
    
    # Check timeframes supported by the exchange
    if '1s' not in exchange.timeframes:
        print(f"Available timeframes: {exchange.timeframes}")
        raise Exception(f"{exchange_id} does not support 1s timeframe")
    
    # Fetch the most recent candles (no 'since' parameter)
    print(f"Fetching most recent {limit} 1s candles for {symbol}...")
    
    candles = exchange.fetch_ohlcv(
        symbol=symbol,
        timeframe='1s',
        limit=limit
    )
    
    # Convert to DataFrame
    if candles:
        df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        # Calculate age (how old the data is)
        now = datetime.now()
        df['age_seconds'] = ((now - df['datetime']).dt.total_seconds()).astype(int)
        return df
    else:
        return pd.DataFrame()

def continuous_fetch(exchange_id='binance', symbol='BTC/USDT', iterations=5, delay=2):
    """
    Continuously fetch live data to demonstrate it's updating
    """
    print(f"Starting continuous fetch of 1s data from {exchange_id} for {symbol}")
    print(f"Will fetch {iterations} times with {delay} second delay between fetches")
    
    for i in range(iterations):
        print(f"\n--- Fetch #{i+1} at {datetime.now().strftime('%H:%M:%S.%f')[:-3]} ---")
        
        try:
            # Get the latest 5 candles
            df = fetch_live_1s_data(exchange_id, symbol, limit=5)
            
            if df.empty:
                print(f"No live data available from {exchange_id} for {symbol}")
                return
                
            # Print with age information to show how fresh the data is
            print(df[['datetime', 'age_seconds', 'open', 'high', 'low', 'close', 'volume']])
            
            # Show the time range of the data
            if len(df) > 1:
                time_span = (df['timestamp'].max() - df['timestamp'].min()) / 1000
                print(f"Time span of data: {time_span:.1f} seconds")
            
            if i < iterations - 1:
                print(f"Waiting {delay} seconds before next fetch...")
                time.sleep(delay)
                
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
            break

def main():
    # Run the continuous fetching demo
    continuous_fetch()
    
    # Also demonstrate aggregation to 5s
    print("\n\n--- Demonstrating 1s to 5s aggregation with live data ---")
    
    try:
        # Get more data for aggregation demo
        df_1s = fetch_live_1s_data(limit=30)
        
        if df_1s.empty:
            print("No data available for aggregation demo")
            return
            
        print(f"\nFetched {len(df_1s)} recent 1s candles")
        
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
            'volume': 'sum',
            'age_seconds': 'min'  # Use the age of the most recent data
        }).reset_index(drop=True)
        
        print("\n--- Aggregated 5-second candles from live data ---")
        print(df_5s[['datetime', 'age_seconds', 'open', 'high', 'low', 'close', 'volume']])
        
    except Exception as e:
        print(f"ERROR in aggregation demo: {e}")

if __name__ == "__main__":
    main() 
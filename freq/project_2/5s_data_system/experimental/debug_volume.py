#!/usr/bin/env python3
"""
Debug script to investigate volume discrepancies between calculated candles and TradingView
"""

import sqlite3
import pandas as pd
import argparse
import sys
from datetime import datetime, timedelta
import os
import json

# Database paths
TRADES_DB_PATH = "/allah/data/trades.db"
CANDLES_DB_PATH = "/allah/data/candles_5s.db"

def connect_to_db(db_path):
    """Connect to the database and return the connection"""
    if not os.path.exists(db_path):
        print(f"Error: Database file {db_path} not found.")
        sys.exit(1)
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)

def get_trades_by_timestamp(conn, symbol, start_timestamp, end_timestamp):
    """Get trades between specific timestamps"""
    cursor = conn.cursor()
    
    query = """
    SELECT * FROM trades 
    WHERE symbol = ? AND timestamp >= ? AND timestamp < ?
    ORDER BY timestamp ASC
    """
    
    try:
        cursor.execute(query, (symbol, start_timestamp, end_timestamp))
        rows = cursor.fetchall()
        
        # Convert to pandas DataFrame
        trades_data = []
        for row in rows:
            trade = dict(row)
            trades_data.append(trade)
        
        return pd.DataFrame(trades_data)
    
    except sqlite3.Error as e:
        print(f"Error querying trades: {e}")
        return None

def get_candle_by_timestamp(conn, symbol, candle_timestamp):
    """Get a specific candle by timestamp"""
    cursor = conn.cursor()
    
    query = """
    SELECT * FROM candles 
    WHERE symbol = ? AND timestamp = ?
    """
    
    try:
        cursor.execute(query, (symbol, candle_timestamp))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    except sqlite3.Error as e:
        print(f"Error querying candle: {e}")
        return None

def normalize_timestamp(timestamp_ms, interval_sec=5):
    """Normalize timestamp to 5-second interval (same as in collector.py)"""
    timestamp_sec = timestamp_ms / 1000
    normalized_sec = int(timestamp_sec // interval_sec) * interval_sec
    return int(normalized_sec * 1000)

def recalculate_candle(trades_df):
    """Recalculate candle OHLCV from trades data"""
    if trades_df is None or trades_df.empty:
        return None
    
    # Copy the dataframe to avoid modifying the original
    df = trades_df.copy()
    
    # Sort by timestamp
    df = df.sort_values(by='timestamp')
    
    # Calculate OHLCV
    open_price = df.iloc[0]['price']
    high_price = df['price'].max()
    low_price = df['price'].min()
    close_price = df.iloc[-1]['price']
    volume = df['amount'].sum()
    
    return {
        'open': open_price,
        'high': high_price,
        'low': low_price,
        'close': close_price,
        'volume': volume
    }

def analyze_volume_discrepancy(symbol, time_str):
    """Analyze volume discrepancy for a specific candle time"""
    try:
        # Parse the time string to get timestamp
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        timestamp_ms = int(dt.timestamp() * 1000)
        normalized_ts = normalize_timestamp(timestamp_ms)
        
        # Get candle from database
        candles_conn = connect_to_db(CANDLES_DB_PATH)
        candle = get_candle_by_timestamp(candles_conn, symbol, normalized_ts)
        candles_conn.close()
        
        if candle is None:
            print(f"No candle found for {symbol} at {time_str}")
            return
        
        # Get trades for this candle's time period
        trades_conn = connect_to_db(TRADES_DB_PATH)
        start_ts = normalized_ts
        end_ts = normalized_ts + 5000  # 5 seconds
        trades_df = get_trades_by_timestamp(trades_conn, symbol, start_ts, end_ts)
        trades_conn.close()
        
        # Print analysis
        print(f"\n=== Analysis for {symbol} at {time_str} (Timestamp: {normalized_ts}) ===")
        
        # Print stored candle data
        print("\nStored Candle Data:")
        print(f"Open: {candle['open']}")
        print(f"High: {candle['high']}")
        print(f"Low: {candle['low']}")
        print(f"Close: {candle['close']}")
        print(f"Volume: {candle['volume']}")
        
        # Report TradingView volume for comparison
        tv_volume = get_tradingview_volume(time_str)
        if tv_volume:
            print(f"TradingView Volume: {tv_volume}")
            print(f"Difference: {candle['volume'] - tv_volume} ({(candle['volume'] - tv_volume)/candle['volume']*100:.2f}%)")
        
        # Recalculate candle from trades
        if trades_df is not None and not trades_df.empty:
            recalculated = recalculate_candle(trades_df)
            
            print("\nRecalculated from Trades:")
            print(f"Open: {recalculated['open']}")
            print(f"High: {recalculated['high']}")
            print(f"Low: {recalculated['low']}")
            print(f"Close: {recalculated['close']}")
            print(f"Volume: {recalculated['volume']}")
            
            print("\nTrades count:", len(trades_df))
            print("First trade time:", datetime.fromtimestamp(trades_df.iloc[0]['timestamp']/1000))
            print("Last trade time:", datetime.fromtimestamp(trades_df.iloc[-1]['timestamp']/1000))
            
            # Calculate sum of all amounts as detailed check
            trade_amounts = trades_df['amount'].tolist()
            print("\nDetailed Trade Amounts:")
            for i, amount in enumerate(trade_amounts):
                print(f"Trade {i+1}: {amount}")
            print(f"Sum of all amounts: {sum(trade_amounts)}")
            
            # Try to extract info JSON if available
            if 'info' in trades_df.columns:
                try:
                    print("\nAnalyzing 'info' field:")
                    for i, info_str in enumerate(trades_df['info']):
                        if info_str:
                            info = json.loads(info_str)
                            if 'q' in info:
                                print(f"Trade {i+1} raw quantity ('q'): {info['q']}")
                except Exception as e:
                    print(f"Error parsing info field: {e}")
                    
        else:
            print("\nNo trades found for this time period")
    
    except Exception as e:
        print(f"Error during analysis: {e}")

def get_tradingview_volume(time_str):
    """Return the TradingView volume for the given timestamp based on known values"""
    # Map of known timestamps to TradingView volumes
    known_volumes = {
        "2025-05-10 18:32:15": 144,
        "2025-05-10 18:32:20": 598,
        "2025-05-10 18:32:25": 407,
        "2025-05-10 18:20:50": 1420,
        "2025-05-10 18:20:55": 3240,
        "2025-05-10 18:21:00": 691
    }
    return known_volumes.get(time_str)

def main():
    parser = argparse.ArgumentParser(description="Debug volume discrepancies in candles")
    parser.add_argument("--symbol", default="ETH/USDT", help="Symbol to analyze")
    parser.add_argument("--time", required=True, help="Candle time (YYYY-MM-DD HH:MM:SS)")
    
    args = parser.parse_args()
    
    analyze_volume_discrepancy(args.symbol, args.time)

if __name__ == "__main__":
    main() 
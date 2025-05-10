#!/usr/bin/env python3
"""
Script to test different time bucketing approaches to match TradingView's volume
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

def get_all_trades_around_time(conn, symbol, center_time_str, window_seconds=30):
    """Get all trades within a window around a specific time"""
    try:
        # Parse the time string
        center_time = datetime.strptime(center_time_str, "%Y-%m-%d %H:%M:%S")
        
        # Calculate the window boundaries
        start_time = center_time - timedelta(seconds=window_seconds)
        end_time = center_time + timedelta(seconds=window_seconds)
        
        # Convert to timestamps
        start_ts = int(start_time.timestamp() * 1000)
        end_ts = int(end_time.timestamp() * 1000)
        
        # Query trades
        cursor = conn.cursor()
        query = """
        SELECT * FROM trades 
        WHERE symbol = ? AND timestamp >= ? AND timestamp <= ?
        ORDER BY timestamp ASC
        """
        
        cursor.execute(query, (symbol, start_ts, end_ts))
        rows = cursor.fetchall()
        
        # Convert to pandas DataFrame
        trades_data = []
        for row in rows:
            trade = dict(row)
            # If info is present, parse it
            if 'info' in trade and trade['info']:
                try:
                    trade['info_parsed'] = json.loads(trade['info'])
                except:
                    pass
            trades_data.append(trade)
        
        df = pd.DataFrame(trades_data)
        
        # Add datetime column for easier analysis
        if not df.empty and 'timestamp' in df.columns:
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        return df
    
    except Exception as e:
        print(f"Error getting trades: {e}")
        return None

def try_different_buckets(trades_df, target_volume, interval_sec=5):
    """Try different bucket boundaries to match target volume"""
    if trades_df is None or trades_df.empty:
        print("No trades data available for analysis")
        return
    
    print(f"\nSearching for time bucket that gives volume: {target_volume}")
    print(f"Total trades available for analysis: {len(trades_df)}")
    
    # Try different offsets (in milliseconds)
    offsets_to_try = range(-4000, 4000, 100)  # Try offsets from -4s to +4s
    
    best_match = None
    best_diff = float('inf')
    
    results = []
    
    for offset_ms in offsets_to_try:
        # Create custom normalize_timestamp function with this offset
        def custom_normalize(ts_ms, offset=offset_ms):
            ts_sec = (ts_ms + offset) / 1000
            norm_sec = int(ts_sec // interval_sec) * interval_sec
            return int(norm_sec * 1000)
        
        # Apply to all timestamps
        trades_df['bucket'] = trades_df['timestamp'].apply(custom_normalize)
        
        # Extract target bucket time (18:32:20 corresponds to 1746901940000)
        target_time = datetime.strptime("2025-05-10 18:32:20", "%Y-%m-%d %H:%M:%S")
        target_ts = int(target_time.timestamp() * 1000)
        bucket_ts = custom_normalize(target_ts)
        
        # Filter for just this bucket
        bucket_trades = trades_df[trades_df['bucket'] == bucket_ts]
        bucket_volume = bucket_trades['amount'].sum() if not bucket_trades.empty else 0
        
        # Record the result
        diff = abs(bucket_volume - target_volume)
        results.append({
            'offset_ms': offset_ms,
            'bucket_start': datetime.fromtimestamp(bucket_ts/1000),
            'volume': bucket_volume,
            'diff': diff,
            'trade_count': len(bucket_trades)
        })
        
        # Check if this is the best match so far
        if diff < best_diff:
            best_diff = diff
            best_match = {
                'offset_ms': offset_ms,
                'bucket_start': datetime.fromtimestamp(bucket_ts/1000),
                'bucket_end': datetime.fromtimestamp((bucket_ts + 5000)/1000),
                'volume': bucket_volume,
                'diff': diff,
                'trade_count': len(bucket_trades),
                'trades': bucket_trades.sort_values('timestamp')
            }
    
    # Convert results to dataframe for better display
    results_df = pd.DataFrame(results)
    
    # Sort by difference
    results_df = results_df.sort_values('diff')
    
    # Display top 10 closest matches
    print("\nTop 10 closest matches to TradingView volume:")
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    print(results_df.head(10)[['offset_ms', 'bucket_start', 'volume', 'diff', 'trade_count']])
    
    # Display details of the best match
    if best_match:
        print(f"\nBest match found with offset: {best_match['offset_ms']}ms")
        print(f"Bucket time: {best_match['bucket_start']} to {best_match['bucket_end']}")
        print(f"Volume: {best_match['volume']} (diff: {best_match['diff']} from target {target_volume})")
        print(f"Number of trades: {best_match['trade_count']}")
        
        # Show trades in this bucket if reasonable number
        if 0 < best_match['trade_count'] <= 50:
            print("\nTrades in this bucket:")
            trade_display = best_match['trades'][['datetime', 'price', 'amount', 'side']]
            print(trade_display)
        
        # Display total amount from trades
        print(f"\nSum of amounts: {best_match['trades']['amount'].sum()}")
        
        # Check first and last trade times
        if not best_match['trades'].empty:
            first_trade = best_match['trades'].iloc[0]
            last_trade = best_match['trades'].iloc[-1]
            print(f"First trade: {first_trade['datetime']} - {first_trade['amount']}")
            print(f"Last trade: {last_trade['datetime']} - {last_trade['amount']}")

def main():
    parser = argparse.ArgumentParser(description="Test different time bucketing to match TradingView")
    parser.add_argument("--symbol", default="ETH/USDT", help="Symbol to analyze")
    parser.add_argument("--time", default="2025-05-10 18:32:20", help="Center time for analysis")
    parser.add_argument("--target", type=float, default=598.0, help="Target volume to match")
    parser.add_argument("--direct", action="store_true", help="Use direct timestamp comparison")
    
    args = parser.parse_args()
    
    # Connect to database
    conn = connect_to_db(TRADES_DB_PATH)
    
    try:
        if args.direct:
            # Direct timestamp analysis for specific candle
            direct_timestamp_analysis(conn, args.symbol, args.time, args.target)
        else:
            # Get trades around the target time
            trades_df = get_all_trades_around_time(conn, args.symbol, args.time, window_seconds=30)
            
            # Try different bucket approaches
            try_different_buckets(trades_df, args.target)
    
    finally:
        conn.close()

def direct_timestamp_analysis(conn, symbol, time_str, target_volume):
    """Directly analyze a specific timestamp range for different offsets"""
    try:
        # Parse the time string
        target_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        target_ts = int(target_time.timestamp() * 1000)
        
        # Create a range of offsets to try (from -3s to +3s)
        offsets = range(-3000, 3100, 100)
        results = []
        
        print(f"Analyzing timestamp {time_str} ({target_ts}) for volume closest to {target_volume}")
        
        for offset_ms in offsets:
            # Adjust timestamp with offset
            adjusted_ts = target_ts + offset_ms
            
            # Get volume for a 5-second interval
            cursor = conn.cursor()
            query = """
            SELECT COUNT(*) as trade_count, SUM(amount) as volume 
            FROM trades 
            WHERE symbol = ? AND timestamp >= ? AND timestamp < ?
            """
            
            cursor.execute(query, (symbol, adjusted_ts, adjusted_ts + 5000))
            row = cursor.fetchone()
            
            # Get the trades for debugging
            cursor.execute("""
            SELECT timestamp, price, amount FROM trades 
            WHERE symbol = ? AND timestamp >= ? AND timestamp < ?
            ORDER BY timestamp
            LIMIT 5
            """, (symbol, adjusted_ts, adjusted_ts + 5000))
            
            trade_examples = cursor.fetchall()
            
            trade_count = row[0] or 0
            volume = row[1] or 0
            diff = abs(volume - target_volume)
            
            start_time = datetime.fromtimestamp(adjusted_ts/1000)
            end_time = datetime.fromtimestamp((adjusted_ts + 5000)/1000)
            
            results.append({
                'offset_ms': offset_ms,
                'start_time': start_time,
                'end_time': end_time,
                'trade_count': trade_count,
                'volume': volume,
                'diff': diff,
                'trade_examples': trade_examples
            })
        
        # Sort by difference
        results.sort(key=lambda x: x['diff'])
        
        # Display top 10 matches
        print("\nTop 10 matches:")
        for i, result in enumerate(results[:10]):
            print(f"{i+1}. Offset: {result['offset_ms']}ms")
            print(f"   Time range: {result['start_time']} to {result['end_time']}")
            print(f"   Volume: {result['volume']} (diff: {result['diff']} from target {target_volume})")
            print(f"   Trade count: {result['trade_count']}")
            
            # Show a few trades if available
            if result['trade_examples']:
                print("   Sample trades:")
                for ts, price, amount in result['trade_examples']:
                    dt = datetime.fromtimestamp(ts/1000)
                    print(f"   - {dt}: price={price}, amount={amount}")
            print()
        
        # Print recommendation
        best_match = results[0]
        print(f"RECOMMENDATION: Use offset of {best_match['offset_ms']}ms to get volume {best_match['volume']}")
        print(f"This makes the candle time: {best_match['start_time']} to {best_match['end_time']}")
        
    except Exception as e:
        print(f"Error in direct timestamp analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 
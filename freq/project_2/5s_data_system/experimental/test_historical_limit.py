#!/usr/bin/env python3
"""
Test script to investigate the Binance historical trades fetch limitations
and implement a solution to fetch a larger amount of historical data.
"""

import asyncio
import sys
import os
import time
from datetime import datetime, timedelta
import pandas as pd
import ccxt
import ccxt.pro as ccxtpro

# Add parent directory to path so we can import from config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import EXCHANGE_CREDENTIALS

async def test_fetch_single_request():
    """Test how many trades we get in a single fetch_trades request."""
    # Initialize exchange
    print("Testing single fetch_trades request limit...")
    exchange = ccxt.binance(EXCHANGE_CREDENTIALS)
    
    # Symbol and timeframe
    symbol = 'ETH/USDT'
    
    # Calculate time range (last hour)
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(hours=1)).timestamp() * 1000)
    
    print(f"Fetching trades for {symbol} from {datetime.fromtimestamp(start_time/1000)} to {datetime.fromtimestamp(end_time/1000)}")
    
    # Fetch trades
    trades = exchange.fetch_trades(symbol, since=start_time)
    
    print(f"Retrieved {len(trades)} trades in a single request")
    if trades:
        first_trade_time = datetime.fromtimestamp(trades[0]['timestamp']/1000)
        last_trade_time = datetime.fromtimestamp(trades[-1]['timestamp']/1000)
        print(f"First trade: {first_trade_time}")
        print(f"Last trade: {last_trade_time}")
        print(f"Time range covered: {last_trade_time - first_trade_time}")
    
    # Check if there's an explicit limit parameter
    try:
        params = {'limit': 100}
        trades_limited = exchange.fetch_trades(symbol, since=start_time, params=params)
        print(f"With limit=100: Retrieved {len(trades_limited)} trades")
    except Exception as e:
        print(f"Error testing limit parameter: {e}")
    
    return len(trades)

async def fetch_trades_with_pagination(symbol, start_time, end_time=None, max_trades=10000):
    """
    Fetch historical trades with pagination to overcome API limits.
    
    Args:
        symbol: Trading pair symbol
        start_time: Start time in milliseconds
        end_time: End time in milliseconds (default: current time)
        max_trades: Maximum number of trades to fetch
        
    Returns:
        List of trades
    """
    if end_time is None:
        end_time = int(datetime.now().timestamp() * 1000)
    
    exchange = ccxt.binance(EXCHANGE_CREDENTIALS)
    
    all_trades = []
    current_since = start_time
    batch_count = 1
    
    print(f"Fetching historical trades for {symbol} using pagination")
    print(f"Time range: {datetime.fromtimestamp(start_time/1000)} to {datetime.fromtimestamp(end_time/1000)}")
    
    while current_since < end_time and len(all_trades) < max_trades:
        # Print progress
        print(f"Batch {batch_count}: Fetching from {datetime.fromtimestamp(current_since/1000)}")
        
        # Fetch batch of trades
        params = {'limit': 1000}  # Maximum limit for Binance
        trades_batch = exchange.fetch_trades(symbol, since=current_since, params=params)
        
        if not trades_batch:
            print("No more trades to fetch")
            break
            
        print(f"Retrieved {len(trades_batch)} trades")
        
        # Check if we've reached the end
        if len(trades_batch) == 0:
            break
            
        # Store the trades
        all_trades.extend(trades_batch)
        
        # Update the 'since' parameter for the next iteration
        # Use the timestamp of the last trade + 1 ms
        last_trade_time = trades_batch[-1]['timestamp']
        current_since = last_trade_time + 1
        
        # Add small delay to avoid rate limiting
        time.sleep(0.5)
        
        batch_count += 1
        
        # Check if we've reached the desired count
        if len(all_trades) >= max_trades:
            print(f"Reached maximum trade count ({max_trades})")
            break
    
    print(f"Total trades fetched: {len(all_trades)}")
    return all_trades

async def test_fetch_hours_of_data(hours=6):
    """Test fetching multiple hours of historical data."""
    # Symbol and timeframe
    symbol = 'ETH/USDT'
    
    # Calculate time range
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(hours=hours)).timestamp() * 1000)
    
    # Fetch trades with pagination
    trades = await fetch_trades_with_pagination(symbol, start_time, end_time, max_trades=10000)
    
    # Display results
    print(f"\nSummary of {hours} hours of historical data:")
    if trades:
        first_trade_time = datetime.fromtimestamp(trades[0]['timestamp']/1000)
        last_trade_time = datetime.fromtimestamp(trades[-1]['timestamp']/1000)
        print(f"First trade: {first_trade_time}")
        print(f"Last trade: {last_trade_time}")
        print(f"Time range covered: {last_trade_time - first_trade_time}")
        print(f"Total trades: {len(trades)}")
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame([{
            'timestamp': trade['timestamp'],
            'datetime': pd.to_datetime(trade['timestamp'], unit='ms'),
            'price': trade['price'],
            'amount': trade['amount']
        } for trade in trades])
        
        # Group by hour to see distribution
        df['hour'] = df['datetime'].dt.floor('H')
        hourly_counts = df.groupby('hour').size()
        
        print("\nHourly trade distribution:")
        for hour, count in hourly_counts.items():
            print(f"{hour}: {count} trades")
    
    return trades

async def test_real_time_collection():
    """Test real-time trade collection using WebSockets."""
    print("\nTesting real-time trade collection via WebSockets...")
    exchange = ccxtpro.binance(EXCHANGE_CREDENTIALS)
    
    symbol = 'ETH/USDT'
    trade_count = 0
    start_time = time.time()
    duration = 30  # seconds to collect
    
    try:
        # Load markets
        await exchange.load_markets()
        print(f"Connected to {exchange.id} WebSocket API")
        
        # Collect trades for specified duration
        while time.time() - start_time < duration:
            trades = await exchange.watch_trades(symbol)
            trade_count += len(trades)
            print(f"Received {len(trades)} trades. Total: {trade_count}")
            
            # Brief pause to avoid flooding output
            await asyncio.sleep(1)
            
    except Exception as e:
        print(f"Error in WebSocket collection: {e}")
    finally:
        # Close connection
        await exchange.close()
        
    print(f"Collected {trade_count} trades in {duration} seconds")

async def main():
    """Run all tests."""
    print("===== HISTORICAL TRADE FETCH LIMIT TESTS =====")
    single_fetch_count = await test_fetch_single_request()
    
    print("\n===== PAGINATED HISTORICAL DATA FETCH TEST =====")
    await test_fetch_hours_of_data(hours=6)
    
    print("\n===== REAL-TIME TRADE COLLECTION TEST =====")
    await test_real_time_collection()
    
    print("\n===== RECOMMENDATIONS =====")
    print(f"1. Single fetch_trades request limit appears to be {single_fetch_count} trades")
    print("2. To fetch more historical data, implement pagination as shown in fetch_trades_with_pagination()")
    print("3. For initial historical backfill, use pagination with appropriate sleep times to avoid rate limiting")
    print("4. WebSocket connection provides efficient real-time updates after initial backfill")
    
if __name__ == "__main__":
    asyncio.run(main()) 
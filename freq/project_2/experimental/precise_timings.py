#!/usr/bin/env python3
"""
Simplified test script focusing on precise timing requirements.
This script verifies if we can get trade data from exactly 2 seconds ago.
"""
import logging
import time
from datetime import datetime, timezone
import pandas as pd
import ccxt

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger()

def main():
    # Record the exact script execution time
    execution_time = datetime.now(timezone.utc)
    logger.info(f"Script execution time: {execution_time.strftime('%H:%M:%S.%f')[:-3]}")
    
    # Initialize exchange
    exchange = ccxt.binance({'enableRateLimit': True})
    
    # Start time measurement for API call
    start_time = time.time()
    
    # Fetch the most recent trades (will be the last ~1-2 minutes worth)
    try:
        trades = exchange.fetch_trades('ETH/USDT', limit=1000)
        api_call_duration = time.time() - start_time
        logger.info(f"API call took {api_call_duration:.3f} seconds, fetched {len(trades)} trades")
    except Exception as e:
        logger.error(f"Error fetching trades: {e}")
        return
    
    # Exit if no trades
    if not trades:
        logger.error("No trades fetched. Exiting.")
        return
    
    # Convert to DataFrame for easier analysis
    trades_df = pd.DataFrame(trades)
    trades_df['datetime'] = pd.to_datetime(trades_df['timestamp'], unit='ms', utc=True)
    
    # Calculate how many seconds ago each trade occurred
    trades_df['seconds_ago'] = (execution_time - trades_df['datetime']).dt.total_seconds()
    
    # Check for the newest/latest trade
    newest_trade = trades_df.loc[trades_df['timestamp'].idxmax()]
    newest_time = newest_trade['datetime']
    data_freshness = (execution_time - newest_time).total_seconds()
    
    logger.info(f"Newest trade timestamp: {newest_time.strftime('%H:%M:%S.%f')[:-3]}")
    logger.info(f"Data freshness: {data_freshness:.3f} seconds")
    logger.info(f"Total data delay (incl. API call): {data_freshness + api_call_duration:.3f} seconds")
    
    # Find trades at specific time points
    for seconds in [1, 2, 3, 5, 10]:
        # Look for trades that happened around X seconds ago (±0.5s window)
        target_time = execution_time - pd.Timedelta(seconds=seconds)
        window_trades = trades_df[
            (trades_df['seconds_ago'] > seconds - 0.5) & 
            (trades_df['seconds_ago'] < seconds + 0.5)
        ]
        
        if not window_trades.empty:
            logger.info(f"\nFound {len(window_trades)} trades from ~{seconds} seconds ago:")
            for _, row in window_trades.iterrows():
                exact_seconds_ago = row['seconds_ago']
                logger.info(f"  Time: {row['datetime'].strftime('%H:%M:%S.%f')[:-3]} "
                          f"({exact_seconds_ago:.3f} seconds ago), "
                          f"Price: {row['price']}")
        else:
            logger.info(f"\nNo trades found from ~{seconds} seconds ago")
    
    # Find trades at exactly 2 seconds ago (narrow 0.1s window)
    target_time = execution_time - pd.Timedelta(seconds=2)
    precise_trades = trades_df[
        (trades_df['seconds_ago'] > 1.9) & 
        (trades_df['seconds_ago'] < 2.1)
    ]
    
    if not precise_trades.empty:
        logger.info(f"\n✅ PRECISION TEST PASSED: Found {len(precise_trades)} trades from exactly 2±0.1 seconds ago:")
        for _, row in precise_trades.iterrows():
            logger.info(f"  Time: {row['datetime'].strftime('%H:%M:%S.%f')[:-3]} "
                      f"({row['seconds_ago']:.3f} seconds ago)")
    else:
        # Try with a wider window
        wider_window_trades = trades_df[
            (trades_df['seconds_ago'] > 1.5) & 
            (trades_df['seconds_ago'] < 2.5)
        ]
        
        if not wider_window_trades.empty:
            logger.info(f"\n⚠️ PRECISION TEST PARTIAL: Found trades within 2±0.5 seconds:")
            for _, row in wider_window_trades.iterrows():
                logger.info(f"  Time: {row['datetime'].strftime('%H:%M:%S.%f')[:-3]} "
                          f"({row['seconds_ago']:.3f} seconds ago)")
        else:
            logger.info("\n❌ PRECISION TEST FAILED: Could not find trades from 2±0.5 seconds ago")
    
    # Show the distribution of trades by time
    logger.info("\nTrade distribution (seconds ago):")
    for i in range(10):
        bucket_trades = trades_df[(trades_df['seconds_ago'] >= i) & (trades_df['seconds_ago'] < i+1)]
        logger.info(f"  {i}-{i+1}s ago: {len(bucket_trades)} trades")

if __name__ == "__main__":
    main() 
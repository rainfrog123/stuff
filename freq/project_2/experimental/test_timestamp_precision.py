#!/usr/bin/env python3
"""
Test script to verify the timestamp precision of trade data.
This script checks if we can get data from exactly N seconds ago with precise timestamps.
"""
import time
import logging
from datetime import datetime, timezone
import pandas as pd
from typing import List, Dict
import ccxt

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('timestamp_precision_test')

def fetch_recent_trades(exchange_name: str, symbol: str) -> List[Dict]:
    """Fetch the most recent trades from the exchange."""
    # Initialize exchange
    exchange_config = {'enableRateLimit': True}
    exchange = getattr(ccxt, exchange_name)(exchange_config)
    
    try:
        # Fetch most recent trades (max 1000)
        trades = exchange.fetch_trades(symbol, limit=1000)
        logger.info(f"Fetched {len(trades)} trades")
        return trades
    except Exception as e:
        logger.error(f"Error fetching trades: {str(e)}")
        return []

def main():
    # Record exact script execution time
    execution_time = datetime.now(timezone.utc)
    logger.info(f"Script execution time: {execution_time}")
    logger.info(f"Timestamp (ms): {int(execution_time.timestamp() * 1000)}")
    
    # Configuration
    exchange_name = 'binance'
    symbol = 'ETH/USDT'  # Example symbol
    
    # Fetch trades
    start_time = time.time()
    trades = fetch_recent_trades(exchange_name, symbol)
    api_call_duration = time.time() - start_time
    logger.info(f"API call duration: {api_call_duration:.3f} seconds")
    
    if not trades:
        logger.error("Failed to fetch trades. Exiting.")
        return
    
    # Sort trades by timestamp (newest first)
    trades.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Get current time after fetching data
    after_fetch_time = datetime.now(timezone.utc)
    
    # Get timestamps of the most recent trades
    logger.info("\nMost recent trade timestamps:")
    for i, trade in enumerate(trades[:10]):
        trade_time = datetime.fromtimestamp(trade['timestamp']/1000, tz=timezone.utc)
        time_diff = execution_time - trade_time
        logger.info(f"Trade {i+1}: {trade_time} (Diff: {time_diff.total_seconds():.3f} seconds ago)")
    
    # Create a DataFrame for analysis
    trades_df = pd.DataFrame(trades)
    trades_df['datetime'] = pd.to_datetime(trades_df['timestamp'], unit='ms', utc=True)
    
    # Calculate the time difference between execution and each trade
    trades_df['seconds_ago'] = (execution_time - trades_df['datetime']).dt.total_seconds()
    
    # Check for trades within specific time ranges
    last_2sec = trades_df[trades_df['seconds_ago'] < 2]
    last_5sec = trades_df[trades_df['seconds_ago'] < 5]
    
    logger.info(f"\nTrades in the last 2 seconds: {len(last_2sec)}")
    logger.info(f"Trades in the last 5 seconds: {len(last_5sec)}")
    
    # Calculate the freshness of the latest data
    if not trades_df.empty:
        newest_trade = trades_df.iloc[0]
        newest_time = newest_trade['datetime']
        freshness = (execution_time - newest_time).total_seconds()
        logger.info(f"\nNewest trade timestamp: {newest_time}")
        logger.info(f"Data freshness: {freshness:.3f} seconds")
        
        # Calculate the time delay including API call duration
        total_delay = freshness + api_call_duration
        logger.info(f"Total data delay (incl. API call): {total_delay:.3f} seconds")
        
        # Precision check - can we get data from exactly N seconds ago
        # Check if we have trades from 2-3 seconds ago
        target_range = trades_df[(trades_df['seconds_ago'] > 2) & (trades_df['seconds_ago'] < 3)]
        if not target_range.empty:
            logger.info("\nPRECISION TEST PASSED: Found trades from exactly 2-3 seconds ago:")
            for idx, row in target_range.iterrows():
                logger.info(f"  Trade at {row['datetime']} - {row['seconds_ago']:.3f} seconds before execution")
        else:
            logger.info("\nPRECISION TEST INCONCLUSIVE: No trades found in the 2-3 second range")
            
        # Check various time ranges to see distribution
        for i in range(10):
            range_trades = trades_df[(trades_df['seconds_ago'] > i) & (trades_df['seconds_ago'] < i+1)]
            logger.info(f"Trades {i}-{i+1} seconds ago: {len(range_trades)}")

    # Verify current 5s candle
    if not trades_df.empty:
        # Get current 5s candle timestamp (floor to 5s)
        now = datetime.now(timezone.utc)
        current_5s = now.replace(microsecond=0)
        current_5s = current_5s.replace(second=current_5s.second - current_5s.second % 5)
        
        logger.info(f"\nCurrent 5s candle timestamp: {current_5s}")
        
        # Find trades in the current 5s candle - correct the timezone handling
        trades_df['candle_time'] = trades_df['datetime'].dt.floor('5s')
        current_candle_time = pd.Timestamp(current_5s).tz_localize(timezone.utc)
        current_candle_trades = trades_df[trades_df['candle_time'] == current_candle_time]
        
        logger.info(f"Trades in current 5s candle: {len(current_candle_trades)}")
        
        # Find trades in the previous 5s candle
        prev_5s = current_5s.replace(second=current_5s.second - 5)
        prev_candle_time = pd.Timestamp(prev_5s).tz_localize(timezone.utc)
        prev_candle_trades = trades_df[trades_df['candle_time'] == prev_candle_time]
        
        logger.info(f"Trades in previous 5s candle: {len(prev_candle_trades)}")
        
        # Check if we have data from exactly 2 seconds ago
        target_time = execution_time - pd.Timedelta(seconds=2)
        target_time_floor = target_time.replace(microsecond=0)
        target_time_trades = trades_df[(trades_df['datetime'] <= target_time) & 
                                      (trades_df['datetime'] > target_time - pd.Timedelta(seconds=1))]
        
        logger.info(f"\nTrades from exactly 2 seconds ago (at {target_time_floor}):")
        if not target_time_trades.empty:
            for idx, row in target_time_trades.iterrows():
                logger.info(f"  {row['datetime']} (price: {row['price']})")
            logger.info("CONFIRMATION: Successfully retrieved trades from exactly 2 seconds ago!")
        else:
            logger.info("  No trades found exactly 2 seconds ago")

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Simple test script to fetch recent trades and convert them to 5-second candles.
This script tests if we can retrieve at least 1 minute of 5s candle data.
"""
import sys
import os
import time
import logging
from datetime import datetime, timedelta
import pandas as pd
from typing import List, Dict, Any
import ccxt

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('test_5s_candles')

def fetch_recent_trades(exchange_name: str, symbol: str) -> List[Dict]:
    """Fetch the most recent trades from the exchange."""
    logger.info(f"Fetching recent trades for {symbol} from {exchange_name}")
    
    # Initialize exchange
    exchange_config = {
        'enableRateLimit': True,
    }
    
    # You can add API keys here if needed for higher rate limits
    # exchange_config['apiKey'] = 'YOUR_API_KEY'
    # exchange_config['secret'] = 'YOUR_API_SECRET'
    
    exchange = getattr(ccxt, exchange_name)(exchange_config)
    
    try:
        # Fetch maximum allowed trades without using 'since' parameter
        # This is typically the most recent 1000 trades
        trades = exchange.fetch_trades(symbol, limit=1000)
        logger.info(f"Fetched {len(trades)} trades")
        return trades
    except Exception as e:
        logger.error(f"Error fetching trades: {str(e)}")
        return []

def convert_trades_to_candles(trades: List[Dict], timeframe: int = 5) -> pd.DataFrame:
    """Convert a list of trades to OHLCV candles of the specified timeframe in seconds."""
    logger.info(f"Converting {len(trades)} trades to {timeframe}s candles")
    
    if not trades:
        logger.warning("No trades to convert")
        return pd.DataFrame()
    
    # Convert trades to DataFrame
    trades_df = pd.DataFrame(trades)
    
    # Convert timestamp to datetime and set as index
    trades_df['datetime'] = pd.to_datetime(trades_df['timestamp'], unit='ms')
    
    # Create 5-second bins
    trades_df['bin'] = trades_df['datetime'].dt.floor(f'{timeframe}S')
    
    # Group by time bins and create OHLCV candles
    candles = trades_df.groupby('bin').agg({
        'price': ['first', 'max', 'min', 'last'],
        'amount': 'sum',
        'cost': 'sum'
    })
    
    # Flatten the multi-level columns
    candles.columns = ['open', 'high', 'low', 'close', 'volume', 'quote_volume']
    
    # Reset index to make bin a column
    candles = candles.reset_index()
    
    return candles

def main():
    # Configuration
    exchange_name = 'binance'
    symbol = 'ETH/USDT'  # Example symbol
    
    # Fetch trades (most recent available)
    trades = fetch_recent_trades(exchange_name, symbol)
    
    if not trades:
        logger.error("Failed to fetch trades. Exiting.")
        return
    
    # Get earliest and latest trade timestamps
    earliest = min(trades, key=lambda x: x['timestamp'])['timestamp']
    latest = max(trades, key=lambda x: x['timestamp'])['timestamp']
    
    # Convert timestamps to datetime for readability
    earliest_dt = datetime.fromtimestamp(earliest/1000)
    latest_dt = datetime.fromtimestamp(latest/1000)
    
    # Calculate duration
    duration_seconds = (latest - earliest) / 1000
    
    logger.info(f"Trade time range: {earliest_dt} to {latest_dt}")
    logger.info(f"Duration: {duration_seconds:.2f} seconds ({duration_seconds/60:.2f} minutes)")
    
    # Convert to 5-second candles
    candles = convert_trades_to_candles(trades, timeframe=5)
    
    if candles.empty:
        logger.error("Failed to create candles. Exiting.")
        return
    
    # Calculate how many 5s candles we have
    candle_count = len(candles)
    candle_duration = candle_count * 5
    
    logger.info(f"Created {candle_count} 5-second candles")
    logger.info(f"Candle time range: {candle_duration} seconds ({candle_duration/60:.2f} minutes)")
    
    # Display the last minute (12 candles) of data
    last_minute_candles = candles.tail(12)
    logger.info("\nLast minute of 5-second candles:")
    pd.set_option('display.max_rows', None)
    pd.set_option('display.width', 200)
    print(last_minute_candles.to_string())
    
    # Check if we have at least 1 minute of 5s candles
    if candle_count >= 12:
        logger.info("SUCCESS: Successfully retrieved at least 1 minute of 5s candle data!")
    else:
        logger.warning(f"WARNING: Retrieved only {candle_count} 5s candles, which is less than 1 minute (12 candles)")

if __name__ == "__main__":
    main() 
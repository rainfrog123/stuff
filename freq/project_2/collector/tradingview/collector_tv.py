#!/usr/bin/env python3
"""
TradingView 5-second candle collector
"""

import asyncio
import logging
from datetime import datetime, timedelta
from tv_5s_mod import TradingView5sCandleClient
from database import MarketDatabase
from settings import SYMBOLS, LOG_LEVEL, LOG_FILE

# Setup logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL), 
                   format='%(asctime)s - %(levelname)s - %(message)s',
                   handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()])
logger = logging.getLogger('tv_collector')

# Retention settings
RETENTION_HOURS = 3  # Keep only the last 3 hours of data
PRUNE_INTERVAL_MINUTES = 5  # Run pruning every 5 minutes

async def prune_old_data(db, symbol):
    """Prune data older than the retention period"""
    cutoff_time = datetime.now() - timedelta(hours=RETENTION_HOURS)
    cutoff_ms = int(cutoff_time.timestamp() * 1000)
    
    deleted = db.prune_old_data(symbol, cutoff_ms)
    if deleted > 0:
        logger.info(f"Pruned {deleted} candles older than {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')} ({RETENTION_HOURS} hours)")
    
    # Also run database optimization occasionally
    db.optimize_database()

async def main():
    logger.info("Starting TradingView 5s candle collector")
    logger.info(f"Data retention policy: {RETENTION_HOURS} hours")
    db = MarketDatabase()
    client = TradingView5sCandleClient()
    
    # Track when we last pruned data
    last_prune_time = datetime.now()
    
    try:
        symbol = SYMBOLS[0]  # Use the first symbol from settings
        logger.info(f"Collecting 5s candles for {symbol}")
        
        async for candle in client.candle_generator():
            # candle: {"time": datetime, "open": ..., "high": ..., "low": ..., "close": ..., "volume": ...}
            # Convert to DB format: [timestamp_ms, open, high, low, close, volume]
            ts_ms = int(candle["time"].timestamp() * 1000)
            db_row = [ts_ms, candle["open"], candle["high"], candle["low"], candle["close"], candle["volume"]]
            
            # Save to DB
            db.insert_candles([db_row], symbol)
            logger.info(f"Saved candle: {candle['time'].strftime('%H:%M:%S')} O:{candle['open']} H:{candle['high']} L:{candle['low']} C:{candle['close']} V:{candle['volume']}")
            
            # Check if it's time to prune old data
            now = datetime.now()
            if (now - last_prune_time).total_seconds() > PRUNE_INTERVAL_MINUTES * 60:
                logger.info("Running scheduled data pruning...")
                await prune_old_data(db, symbol)
                last_prune_time = now
                
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
    finally:
        logger.info("TradingView collector terminated")

if __name__ == "__main__":
    asyncio.run(main())

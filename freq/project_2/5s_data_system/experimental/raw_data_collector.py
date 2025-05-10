#!/usr/bin/env python3
"""
Raw Data Collector - Stores WebSocket trade data exactly as received.
This script connects to Binance WebSocket API, receives trade data and stores it
in its raw form in the database.
"""

import asyncio
import logging
import os
import sys
import time
import json
import sqlite3
from datetime import datetime
import ccxt.pro as ccxtpro
import signal

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("raw_data_collector.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("raw_collector")

# Exchange settings
EXCHANGE = "binance"
EXCHANGE_CREDENTIALS = {
    "apiKey": "ofQzX3gGAKS777NyYIovAy1XyqLzGC2UJPMh9jqIYEfieFRy3DCkZJl15VYA2zXo",
    "secret": "QVJpTFgHIEv74LmCT5clX8o1zAFEEqJqKpg2ePklObM1Ybv9iKNe8jvM7MRjoz07",
    "enableRateLimit": True,
    "options": {
        "defaultType": "future"
    }
}

# Symbol to watch
SYMBOL = "ETH/USDT"

# Database settings
DB_PATH = "/allah/data/raw_trades.db"

class RawDataCollector:
    """Collects and stores raw trade data from WebSocket"""
    
    def __init__(self, db_path=DB_PATH):
        """Initialize the collector"""
        self.db_path = db_path
        self.exchange = None
        self.trade_ids = set()
        self.total_trades = 0
        self.running = True
        
        # Initialize database
        self._init_database()
        
    def _init_database(self):
        """Initialize the database for storing raw trade data"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create raw_trades table with complete data structure
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS raw_trades (
            id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            datetime TEXT NOT NULL,
            price REAL NOT NULL,
            amount REAL NOT NULL,
            cost REAL,
            side TEXT,
            type TEXT,
            taker_or_maker TEXT,
            order_id TEXT,
            fee_cost REAL,
            fee_currency TEXT,
            raw_data TEXT NOT NULL,
            UNIQUE(id, symbol)
        )
        ''')
        
        # Create index for faster queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_raw_trades_ts ON raw_trades (timestamp)')
        
        conn.commit()
        conn.close()
        
        logger.info(f"Database initialized at {self.db_path}")
    
    def insert_trade(self, trade):
        """Insert a trade into the database with all raw data preserved"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Extract values with fallbacks for optional fields
            trade_id = str(trade['id'])
            symbol = trade['symbol']
            timestamp = int(trade['timestamp'])
            datetime_str = trade['datetime']
            price = float(trade['price'])
            amount = float(trade['amount'])
            
            # Optional fields
            cost = float(trade['cost']) if 'cost' in trade and trade['cost'] is not None else None
            side = trade['side'] if 'side' in trade else None
            trade_type = trade['type'] if 'type' in trade else None
            taker_or_maker = trade['takerOrMaker'] if 'takerOrMaker' in trade else None
            order_id = trade['order'] if 'order' in trade else None
            
            # Fee information
            fee_cost = None
            fee_currency = None
            if 'fee' in trade and trade['fee'] is not None:
                fee_cost = float(trade['fee']['cost']) if trade['fee']['cost'] is not None else None
                fee_currency = trade['fee']['currency'] if 'currency' in trade['fee'] else None
            
            # Raw data as JSON
            raw_data = json.dumps(trade)
            
            cursor.execute('''
            INSERT OR IGNORE INTO raw_trades 
            (id, symbol, timestamp, datetime, price, amount, cost, side, type, 
             taker_or_maker, order_id, fee_cost, fee_currency, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade_id, symbol, timestamp, datetime_str, price, amount, cost, side,
                trade_type, taker_or_maker, order_id, fee_cost, fee_currency, raw_data
            ))
            
            if cursor.rowcount > 0:
                self.total_trades += 1
                if self.total_trades % 100 == 0:
                    logger.info(f"Stored {self.total_trades} trades in database")
            
            conn.commit()
            return cursor.rowcount
            
        except Exception as e:
            logger.error(f"Error inserting trade: {e}")
            return 0
        finally:
            conn.close()
    
    def prune_old_data(self, cutoff_timestamp):
        """Remove data older than the specified cutoff timestamp"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                'DELETE FROM raw_trades WHERE timestamp < ?',
                (cutoff_timestamp,)
            )
            deleted = cursor.rowcount
            conn.commit()
            
            if deleted > 0:
                logger.info(f"Pruned {deleted} trades older than {datetime.fromtimestamp(cutoff_timestamp/1000)}")
            
            return deleted
        except Exception as e:
            logger.error(f"Error pruning old data: {e}")
            return 0
        finally:
            conn.close()
            
    async def init_exchange(self):
        """Initialize the exchange connection with CCXT"""
        try:
            # Initialize WebSocket exchange
            exchange_class = getattr(ccxtpro, EXCHANGE)
            self.exchange = exchange_class(EXCHANGE_CREDENTIALS)
            
            # Load markets for symbol normalization
            await self.exchange.load_markets()
            
            logger.info(f"Successfully connected to {EXCHANGE} exchange")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize exchange: {e}")
            return False
    
    async def maintenance_task(self):
        """Task to prune old data and maintain the database"""
        while self.running:
            try:
                # Keep only 10 minutes of data
                current_time_ms = int(time.time() * 1000)
                cutoff_time = current_time_ms - (10 * 60 * 1000)  # 10 minutes
                
                self.prune_old_data(cutoff_time)
                
                # Maintenance every minute
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Error in maintenance task: {e}")
                await asyncio.sleep(60)
    
    async def collect_trades(self):
        """Collect trades from WebSocket and store them with all raw data"""
        try:
            logger.info(f"Starting to collect raw trade data for {SYMBOL}")
            
            # Start maintenance task
            maintenance_task = asyncio.create_task(self.maintenance_task())
            
            # Watch trades until stopped
            while self.running:
                try:
                    # Get trades from WebSocket
                    trades = await self.exchange.watch_trades(SYMBOL)
                    
                    # Process and store new trades
                    new_trades = []
                    for trade in trades:
                        if trade['id'] not in self.trade_ids:
                            self.trade_ids.add(trade['id'])
                            new_trades.append(trade)
                    
                    # Insert new trades to database
                    for trade in new_trades:
                        self.insert_trade(trade)
                    
                    if new_trades:
                        logger.info(f"Received and stored {len(new_trades)} new trades")
                        # Print sample of raw data
                        if len(new_trades) > 0:
                            logger.debug(f"Sample trade: {json.dumps(new_trades[0], indent=2)}")
                    
                except Exception as e:
                    logger.error(f"Error processing trades: {e}")
                    await asyncio.sleep(1)
            
            # Cancel maintenance task when loop ends
            maintenance_task.cancel()
            
        except asyncio.CancelledError:
            logger.info("Trade collection task cancelled")
        except Exception as e:
            logger.error(f"Unexpected error in trade collection: {e}")
        finally:
            # Close exchange connection
            if self.exchange:
                await self.exchange.close()
                logger.info("Exchange connection closed")

async def main():
    """Main entry point for the raw data collector"""
    collector = RawDataCollector()
    
    # Initialize exchange
    if not await collector.init_exchange():
        logger.error("Failed to initialize exchange. Exiting.")
        return
    
    # Handle graceful shutdown
    def signal_handler():
        logger.info("Shutdown signal received")
        collector.running = False
    
    # Set up signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)
    
    # Start collecting trades
    await collector.collect_trades()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Exiting.")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}") 
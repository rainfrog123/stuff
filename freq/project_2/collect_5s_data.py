#!/usr/bin/env python3
"""
Independent 5s candle data collector for FreqTrade
Continuously collects trade data and builds 5s candles
Stores data in a SQLite database for easy access
"""
import time
import logging
import argparse
import sqlite3
import threading
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, List
import ccxt

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('5s_collector')

# Database path
DB_PATH = '/allah/freqtrade/user_data/data/5s_candles.sqlite'

class TradeCollector:
    def __init__(self, exchange_name: str, pairs: List[str], api_key=None, api_secret=None):
        self.exchange_name = exchange_name
        self.pairs = pairs
        
        # Initialize exchange
        exchange_class = getattr(ccxt, exchange_name)
        self.exchange = exchange_class({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
        })
        
        # Initialize database
        self.conn = sqlite3.connect(DB_PATH)
        self.create_tables()
        
        # Track last processed trade IDs to avoid duplicates
        self.last_trade_ids = {}
        
        # Load existing data for each pair
        self.initialize_from_db()
        
        logger.info(f"Initialized collector for {exchange_name} with {len(pairs)} pairs")
        
    def create_tables(self):
        """Create database tables if they don't exist"""
        cursor = self.conn.cursor()
        
        # Create candles table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS candles (
            pair TEXT,
            timestamp INTEGER,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            PRIMARY KEY (pair, timestamp)
        )
        ''')
        
        # Create index for faster queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pair_timestamp ON candles (pair, timestamp)')
        
        # Create metadata table for tracking last processed trade IDs
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS metadata (
            pair TEXT PRIMARY KEY,
            last_trade_id TEXT,
            last_update INTEGER
        )
        ''')
        
        self.conn.commit()
    
    def initialize_from_db(self):
        """Initialize last trade IDs from database"""
        cursor = self.conn.cursor()
        for pair in self.pairs:
            cursor.execute('SELECT last_trade_id FROM metadata WHERE pair = ?', (pair,))
            row = cursor.fetchone()
            if row:
                self.last_trade_ids[pair] = row[0]
            else:
                # No data for this pair yet
                self.last_trade_ids[pair] = None
    
    def fetch_trades(self, pair: str):
        """Fetch trades for a pair, handling pagination and rate limits"""
        try:
            since = None
            last_id = self.last_trade_ids.get(pair)
            
            # If we have a last trade ID, use it for pagination
            params = {}
            if last_id:
                # Different exchanges have different pagination mechanisms
                if self.exchange_name == 'binance':
                    params['fromId'] = last_id
                else:
                    # Default: use timestamp-based pagination
                    # Get candles for the last hour to ensure continuity
                    since = int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp() * 1000)
            else:
                # Initial fetch - get last hour of data
                since = int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp() * 1000)
            
            logger.debug(f"Fetching trades for {pair} since {since}, last_id={last_id}")
            trades = self.exchange.fetch_trades(pair, since=since, params=params, limit=1000)
            
            if trades:
                # Update last trade ID
                self.last_trade_ids[pair] = trades[-1]['id']
                
                # Update metadata in database
                cursor = self.conn.cursor()
                cursor.execute(
                    'INSERT OR REPLACE INTO metadata (pair, last_trade_id, last_update) VALUES (?, ?, ?)',
                    (pair, trades[-1]['id'], int(datetime.now(timezone.utc).timestamp() * 1000))
                )
                self.conn.commit()
            
            return trades
        except Exception as e:
            logger.error(f"Error fetching trades for {pair}: {e}")
            return []
    
    def convert_trades_to_ohlcv(self, trades, timeframe='5s'):
        """Convert trades to OHLCV candles with 5s intervals"""
        if not trades:
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame([{
            'timestamp': trade['timestamp'],
            'price': float(trade['price']),
            'amount': float(trade['amount'])
        } for trade in trades])
        
        # Convert timestamp to datetime and floor to 5s intervals
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['date'] = df['timestamp'].dt.floor('5s')
        
        # Group by 5s intervals
        ohlcv = df.groupby('date').agg({
            'price': ['first', 'max', 'min', 'last'],
            'amount': 'sum'
        }).reset_index()
        
        # Flatten multi-index
        ohlcv.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        
        # Convert date back to millisecond timestamp
        ohlcv['timestamp'] = ohlcv['date'].astype(np.int64) // 10**6
        
        return ohlcv
    
    def store_candles(self, pair: str, candles: pd.DataFrame):
        """Store candles in the database"""
        if candles.empty:
            return
        
        try:
            # Convert to list of tuples for SQL insertion
            records = [
                (pair, int(row['timestamp']), float(row['open']), float(row['high']), 
                 float(row['low']), float(row['close']), float(row['volume']))
                for _, row in candles.iterrows()
            ]
            
            # Insert into database (replace if exists)
            cursor = self.conn.cursor()
            cursor.executemany(
                'INSERT OR REPLACE INTO candles (pair, timestamp, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?)',
                records
            )
            self.conn.commit()
            logger.debug(f"Stored {len(records)} candles for {pair}")
        except Exception as e:
            logger.error(f"Error storing candles for {pair}: {e}")
    
    def process_pair(self, pair: str):
        """Process a single pair - fetch trades, convert to candles, store"""
        try:
            # Fetch trades
            trades = self.fetch_trades(pair)
            if not trades:
                return
            
            # Convert to candles
            candles = self.convert_trades_to_ohlcv(trades)
            if candles.empty:
                return
            
            # Store candles
            self.store_candles(pair, candles)
            
            logger.info(f"Processed {len(trades)} trades into {len(candles)} candles for {pair}")
        except Exception as e:
            logger.error(f"Error processing {pair}: {e}")
    
    def run_collection_loop(self, interval=10):
        """Run the collection loop for all pairs"""
        while True:
            start_time = time.time()
            
            for pair in self.pairs:
                try:
                    self.process_pair(pair)
                except Exception as e:
                    logger.error(f"Unexpected error processing {pair}: {e}")
            
            # Sleep until next interval
            elapsed = time.time() - start_time
            sleep_time = max(0.1, interval - elapsed)
            logger.debug(f"Collection cycle took {elapsed:.2f}s, sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)

def main():
    parser = argparse.ArgumentParser(description='5-second candle data collector for FreqTrade')
    parser.add_argument('--exchange', type=str, default='binance', help='Exchange name (ccxt)')
    parser.add_argument('--pairs', type=str, nargs='+', required=True, help='Trading pairs to collect')
    parser.add_argument('--api-key', type=str, help='API key (optional)')
    parser.add_argument('--api-secret', type=str, help='API secret (optional)')
    parser.add_argument('--interval', type=int, default=10, help='Collection interval in seconds')
    
    args = parser.parse_args()
    
    collector = TradeCollector(
        exchange_name=args.exchange,
        pairs=args.pairs,
        api_key=args.api_key,
        api_secret=args.api_secret
    )
    
    try:
        logger.info(f"Starting collection loop for {len(args.pairs)} pairs")
        collector.run_collection_loop(interval=args.interval)
    except KeyboardInterrupt:
        logger.info("Collection stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        collector.conn.close()

if __name__ == '__main__':
    main()
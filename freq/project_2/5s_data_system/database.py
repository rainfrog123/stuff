#!/usr/bin/env python3
"""
Database module for storing and retrieving market data.
"""

import logging
import sqlite3
import pandas as pd
from datetime import datetime
import json
import os
from contextlib import contextmanager

from config import DB_PATH, DATA_DIR

logger = logging.getLogger(__name__)

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

class MarketDatabase:
    """SQLite database for storing market data (trades and candles)."""
    
    def __init__(self, db_path=DB_PATH):
        """Initialize the database with the specified path."""
        self.db_path = db_path
        self._create_tables()
        logger.info(f"Initialized database at {db_path}")
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        try:
            yield conn
        finally:
            conn.close()
    
    def _create_tables(self):
        """Create necessary tables if they don't exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create trades table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                datetime TEXT NOT NULL,
                price REAL NOT NULL,
                amount REAL NOT NULL,
                side TEXT NOT NULL,
                info TEXT,
                UNIQUE(id, symbol)
            )
            ''')
            
            # Create index on timestamp and symbol for faster queries
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_ts_symbol ON trades (timestamp, symbol)')
            
            # Create candles table for aggregated 5s data
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS candles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                datetime TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                UNIQUE(timestamp, symbol)
            )
            ''')
            
            # Create index on timestamp and symbol for faster queries
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_candles_ts_symbol ON candles (timestamp, symbol)')
            
            conn.commit()
    
    def insert_trades(self, trades, symbol):
        """Insert multiple trades for a symbol into the database."""
        if not trades:
            return 0
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            inserted = 0
            
            for trade in trades:
                try:
                    # Convert trade info to JSON
                    info_json = json.dumps(trade['info']) if 'info' in trade else None
                    
                    cursor.execute('''
                    INSERT OR IGNORE INTO trades 
                    (id, symbol, timestamp, datetime, price, amount, side, info)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        str(trade['id']),
                        symbol,
                        int(trade['timestamp']),
                        trade['datetime'],
                        float(trade['price']),
                        float(trade['amount']),
                        trade['side'],
                        info_json
                    ))
                    if cursor.rowcount > 0:
                        inserted += 1
                except Exception as e:
                    logger.error(f"Error inserting trade {trade}: {e}")
            
            conn.commit()
            if inserted > 0:
                logger.debug(f"Inserted {inserted} new trades for {symbol}")
            return inserted
    
    def insert_candle(self, candle, symbol):
        """Insert a 5s candle for a symbol into the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                timestamp = int(candle[0])
                datetime_str = pd.to_datetime(timestamp, unit='ms').strftime('%Y-%m-%d %H:%M:%S.%f')
                
                cursor.execute('''
                INSERT OR REPLACE INTO candles 
                (symbol, timestamp, datetime, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    symbol,
                    timestamp,
                    datetime_str,
                    float(candle[1]),  # open
                    float(candle[2]),  # high
                    float(candle[3]),  # low
                    float(candle[4]),  # close
                    float(candle[5])   # volume
                ))
                
                conn.commit()
                return cursor.rowcount
            except Exception as e:
                logger.error(f"Error inserting candle {candle} for {symbol}: {e}")
                return 0
    
    def insert_candles(self, candles, symbol):
        """Insert multiple 5s candles for a symbol into the database."""
        if not candles:
            return 0
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            inserted = 0
            
            for candle in candles:
                try:
                    timestamp = int(candle[0])
                    datetime_str = pd.to_datetime(timestamp, unit='ms').strftime('%Y-%m-%d %H:%M:%S.%f')
                    
                    cursor.execute('''
                    INSERT OR REPLACE INTO candles 
                    (symbol, timestamp, datetime, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        symbol,
                        timestamp,
                        datetime_str,
                        float(candle[1]),  # open
                        float(candle[2]),  # high
                        float(candle[3]),  # low
                        float(candle[4]),  # close
                        float(candle[5])   # volume
                    ))
                    inserted += cursor.rowcount
                except Exception as e:
                    logger.error(f"Error inserting candle {candle} for {symbol}: {e}")
            
            conn.commit()
            if inserted > 0:
                logger.debug(f"Inserted {inserted} candles for {symbol}")
            return inserted
    
    def get_latest_trade_timestamp(self, symbol):
        """Get the timestamp of the latest trade for a symbol."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT MAX(timestamp) as max_ts FROM trades WHERE symbol = ?', (symbol,))
            result = cursor.fetchone()
            return result['max_ts'] if result and result['max_ts'] else 0
    
    def get_latest_candle_timestamp(self, symbol):
        """Get the timestamp of the latest candle for a symbol."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT MAX(timestamp) as max_ts FROM candles WHERE symbol = ?', (symbol,))
            result = cursor.fetchone()
            return result['max_ts'] if result and result['max_ts'] else 0
    
    def get_trades(self, symbol, start_time=None, end_time=None, limit=None):
        """Get trades for a symbol with optional time filtering."""
        query = 'SELECT * FROM trades WHERE symbol = ?'
        params = [symbol]
        
        if start_time:
            query += ' AND timestamp >= ?'
            params.append(start_time)
        
        if end_time:
            query += ' AND timestamp <= ?'
            params.append(end_time)
        
        query += ' ORDER BY timestamp ASC'
        
        if limit:
            query += ' LIMIT ?'
            params.append(limit)
        
        with self.get_connection() as conn:
            return pd.read_sql_query(query, conn, params=params)
    
    def get_candles(self, symbol, start_time=None, end_time=None, limit=None):
        """Get 5s candles for a symbol with optional time filtering."""
        query = 'SELECT * FROM candles WHERE symbol = ?'
        params = [symbol]
        
        if start_time:
            query += ' AND timestamp >= ?'
            params.append(start_time)
        
        if end_time:
            query += ' AND timestamp <= ?'
            params.append(end_time)
        
        query += ' ORDER BY timestamp ASC'
        
        if limit:
            query += ' LIMIT ?'
            params.append(limit)
        
        with self.get_connection() as conn:
            return pd.read_sql_query(query, conn, params=params)
    
    def prune_old_trades(self, symbol, max_trades):
        """Keep only the most recent max_trades for a symbol."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) as count FROM trades WHERE symbol = ?', (symbol,))
            count = cursor.fetchone()['count']
            
            if count > max_trades:
                # Get the timestamp to delete trades before
                cursor.execute('''
                SELECT timestamp FROM trades 
                WHERE symbol = ? 
                ORDER BY timestamp DESC 
                LIMIT 1 OFFSET ?
                ''', (symbol, max_trades - 1))
                
                result = cursor.fetchone()
                if result:
                    cutoff_timestamp = result['timestamp']
                    cursor.execute('DELETE FROM trades WHERE symbol = ? AND timestamp < ?', 
                                 (symbol, cutoff_timestamp))
                    deleted = cursor.rowcount
                    conn.commit()
                    logger.info(f"Pruned {deleted} old trades for {symbol}")
                    return deleted
            
            return 0 
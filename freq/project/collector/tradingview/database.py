#!/usr/bin/env python3
"""
Database module for storing and retrieving market data.
Split into separate databases for trades and candles.
"""

import logging
import sqlite3
import pandas as pd
from datetime import datetime
import json
import os
from contextlib import contextmanager

from settings import CANDLES_DB_PATH, DATA_DIR

logger = logging.getLogger(__name__)

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

class MarketDatabase:
    """
    Database manager for market data with candles only (trades removed).
    """
    
    def __init__(self, candles_db_path="/allah/data/tv_candles.db"):
        """Initialize the candles database with the specified path."""
        self.candles_db_path = candles_db_path
        self._create_tables()
        logger.info(f"Initialized candles database at {self.candles_db_path}")

    @contextmanager
    def get_candles_connection(self):
        """Context manager for candles database connections."""
        conn = sqlite3.connect(self.candles_db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        try:
            yield conn
        finally:
            conn.close()

    def _create_tables(self):
        """Create necessary tables if they don't exist (candles only)."""
        with self.get_candles_connection() as conn:
            cursor = conn.cursor()
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
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_candles_ts_symbol ON candles (timestamp, symbol)')
            conn.commit()
    
    def insert_candle(self, candle, symbol):
        """Insert a 5s candle for a symbol into the candles database."""
        with self.get_candles_connection() as conn:
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
        """Insert multiple 5s candles for a symbol into the candles database."""
        if not candles:
            return 0
        with self.get_candles_connection() as conn:
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
    
    def get_latest_candle_timestamp(self, symbol):
        """Get the timestamp of the latest candle for a symbol."""
        with self.get_candles_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT MAX(timestamp) as max_ts FROM candles WHERE symbol = ?', (symbol,))
            result = cursor.fetchone()
            return result['max_ts'] if result and result['max_ts'] else 0
    
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
        with self.get_candles_connection() as conn:
            return pd.read_sql_query(query, conn, params=params)
    
    def prune_old_data(self, symbol, cutoff_timestamp):
        """
        Remove candle data older than the specified cutoff timestamp.
        Args:
            symbol: The trading pair symbol.
            cutoff_timestamp: Remove data older than this timestamp (in milliseconds).
        Returns:
            Number of records deleted.
        """
        try:
            with self.get_candles_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'DELETE FROM candles WHERE symbol = ? AND timestamp < ?',
                    (symbol, cutoff_timestamp)
                )
                deleted = cursor.rowcount
                conn.commit()
                return deleted
        except Exception as e:
            logger.error(f"Error pruning old candles for {symbol}: {e}")
            return 0
    
    def optimize_database(self):
        """Perform optimization tasks on the candles database."""
        try:
            with self.get_candles_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('VACUUM')
                cursor.execute('ANALYZE')
                cursor.execute("SELECT COUNT(*) as count FROM candles")
                candles_count = cursor.fetchone()['count']
            logger.info(f"Candles database optimized. Current stats: {candles_count} candles")
            return True
        except Exception as e:
            logger.error(f"Error optimizing candles database: {e}")
            return False
    
    def close(self):
        """Close any remaining database resources."""
        pass 
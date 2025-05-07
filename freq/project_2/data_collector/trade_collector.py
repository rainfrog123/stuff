#!/usr/bin/env python3
"""
5-Second Candle Data Collector for FreqTrade
--------------------------------------------
This script continuously fetches trade data from exchanges and 
converts them into 5-second candles stored in a SQLite database.
It's designed to run as a background process to provide historical
and real-time 5s candle data for FreqTrade strategies.

Usage:
    python trade_collector.py 
    python trade_collector.py --exchange binance --pairs ETH/USDT:USDT BTC/USDT:USDT

Run with --help for all options.
"""
import os
import sys
import time
import json
import signal
import logging
import sqlite3
import argparse
import pandas as pd
import numpy as np
import websocket
import threading
import requests
from threading import Thread, Event
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Set, Optional, Any
import ccxt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(os.path.dirname(__file__), 'trade_collector.log'))
    ]
)
logger = logging.getLogger('trade_collector')

# Default settings
DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'user_data', 'data', '5s_candles.sqlite')
DEFAULT_TIMEFRAME = '5s'
DEFAULT_TRADE_LIMIT = 1000
DEFAULT_UPDATE_INTERVAL = 5  # seconds between updates
DEFAULT_RETENTION_DAYS = 14  # days to keep data
DEFAULT_INITIAL_HISTORY_HOURS = 24  # hours of historical data to fetch on startup
DEFAULT_EXCHANGE = 'binance'
DEFAULT_PAIRS = ['ETH/USDT:USDT']

class TradeCollector:
    """
    Collects trades from exchanges and converts them to 5-second OHLCV candles.
    Stores data in a SQLite database for use by FreqTrade strategies.
    """
    
    def __init__(
        self, 
        exchange_name: str = DEFAULT_EXCHANGE,
        pairs: List[str] = DEFAULT_PAIRS,
        db_path: str = DEFAULT_DB_PATH,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        update_interval: int = DEFAULT_UPDATE_INTERVAL,
        retention_days: int = DEFAULT_RETENTION_DAYS,
        enable_websocket: bool = True,
        initial_history_hours: int = DEFAULT_INITIAL_HISTORY_HOURS,
    ):
        self.exchange_name = exchange_name
        self.pairs = pairs
        self.db_path = db_path
        self.api_key = api_key
        self.api_secret = api_secret
        self.update_interval = update_interval
        self.retention_days = retention_days
        self.enable_websocket = enable_websocket
        self.initial_history_hours = initial_history_hours
        
        # Initialize database directory if it doesn't exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Initialize caches
        self.last_trade_ids: Dict[str, str] = {}
        self.last_update_times: Dict[str, datetime] = {}
        self.failed_pair_retries: Dict[str, int] = {}  # Track retry counts
        
        # State control
        self._stop_event = Event()
        self._threads: List[Thread] = []
        self._ws_clients: Dict[str, Any] = {}
        self._ws_connected = False
        self._trade_buffer: Dict[str, List[dict]] = {}  # Buffer for WebSocket trades
        self._buffer_lock = threading.Lock()  # Lock for thread-safe buffer access
        
        # Initialize exchange
        logger.info(f"Initializing {exchange_name} exchange...")
        exchange_class = getattr(ccxt, exchange_name)
        exchange_config = {
            'enableRateLimit': True,
        }
        
        if api_key and api_secret:
            exchange_config.update({
                'apiKey': api_key,
                'secret': api_secret,
            })
        
        self.exchange = exchange_class(exchange_config)
        self.exchange.load_markets()
        
        # Validate all pairs
        valid_pairs = []
        for pair in pairs:
            if pair in self.exchange.markets:
                valid_pairs.append(pair)
            else:
                logger.error(f"Pair {pair} not found on {exchange_name}, skipping")
        
        if not valid_pairs:
            raise ValueError(f"No valid pairs found for {exchange_name}")
        
        self.pairs = valid_pairs
        logger.info(f"Initialized with {len(valid_pairs)} valid pairs: {', '.join(valid_pairs)}")
        
        # Initialize database
        self._init_database()
        self._load_last_trade_data()
        
        # Initialize WebSocket if supported and enabled
        if self.enable_websocket:
            self._init_websocket()
    
    def _init_database(self):
        """Initialize the SQLite database with required tables"""
        logger.info(f"Initializing database at {self.db_path}")
        
        try:
            self.conn = sqlite3.connect(self.db_path)
            cursor = self.conn.cursor()
            
            # Create tables if they don't exist
            
            # Candles table - stores 5s OHLCV data
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
            
            # Create index for faster queries by timestamp range
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_candles_pair_timestamp ON candles (pair, timestamp)')
            
            # Metadata table - stores last processed trade info for each pair
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS metadata (
                pair TEXT PRIMARY KEY,
                last_trade_id TEXT,
                last_timestamp INTEGER,
                last_update INTEGER
            )
            ''')
            
            # Raw trades table (optional, for debugging and advanced needs)
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                pair TEXT,
                trade_id TEXT,
                timestamp INTEGER,
                price REAL,
                amount REAL,
                side TEXT,
                PRIMARY KEY (pair, trade_id)
            )
            ''')
            
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_pair_timestamp ON trades (pair, timestamp)')
            
            self.conn.commit()
            logger.info("Database initialized successfully")
            
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            raise RuntimeError(f"Failed to initialize database: {e}")
    
    def _load_last_trade_data(self):
        """Load the last trade IDs and timestamps from the database"""
        logger.info("Loading last trade data from database...")
        
        try:
            cursor = self.conn.cursor()
            for pair in self.pairs:
                cursor.execute(
                    'SELECT last_trade_id, last_timestamp FROM metadata WHERE pair = ?',
                    (pair,)
                )
                result = cursor.fetchone()
                
                if result:
                    self.last_trade_ids[pair] = result[0]
                    last_timestamp = result[1]
                    self.last_update_times[pair] = datetime.fromtimestamp(last_timestamp / 1000, tz=timezone.utc)
                    logger.info(f"Loaded last trade for {pair}: ID={result[0]}, Time={self.last_update_times[pair]}")
                else:
                    self.last_trade_ids[pair] = None
                    self.last_update_times[pair] = None
                    logger.info(f"No previous data for {pair}, will fetch initial history")
            
        except sqlite3.Error as e:
            logger.error(f"Error loading last trade data: {e}")
    
    def _init_websocket(self):
        """Initialize WebSocket connections for trade streams"""
        if self.exchange_name.lower() != 'binance':
            logger.warning(f"WebSocket support not implemented for {self.exchange_name}")
            return
        
        try:
            # Initialize buffers for each pair
            for pair in self.pairs:
                self._trade_buffer[pair] = []
            
            # Start WebSocket threads
            self._start_binance_websocket()
        except Exception as e:
            logger.error(f"Failed to initialize WebSocket: {e}")
    
    def _start_binance_websocket(self):
        """Start Binance WebSocket connections for trade streams"""
        # Start a WebSocket connection for each pair
        for pair in self.pairs:
            try:
                # Convert pair name to lowercase stream format (e.g. 'ETH/USDT:USDT' -> 'ethusdt')
                # For spot: remove colon part. For futures: handle differently
                market = self.exchange.market(pair)
                is_futures = market.get('swap', False) or market.get('future', False)
                
                # Format the symbol for WebSocket
                symbol = pair.split(':')[0] if ':' in pair else pair
                symbol = symbol.replace('/', '').lower()
                
                # Get the stream URL and stream name
                if is_futures:
                    stream_url = "wss://fstream.binance.com/ws"
                    stream_name = f"{symbol}@aggTrade"
                else:
                    stream_url = "wss://stream.binance.com:9443/ws"
                    stream_name = f"{symbol}@aggTrade"
                
                # Set up the WebSocket thread
                thread = Thread(
                    target=self._run_binance_websocket,
                    args=(stream_url, stream_name, pair, is_futures),
                    daemon=True
                )
                thread.start()
                self._threads.append(thread)
                
                logger.info(f"Started WebSocket for {pair} -> {stream_name}")
                
            except Exception as e:
                logger.error(f"Failed to start WebSocket for {pair}: {e}")
    
    def _run_binance_websocket(self, stream_url, stream_name, pair, is_futures):
        """Run the Binance WebSocket connection for a specific pair"""
        
        # Define WebSocket callbacks
        def on_message(ws, message):
            """Handle incoming WebSocket message"""
            try:
                data = json.loads(message)
                
                # For "aggTrade" streams
                if 'e' in data and data['e'] == 'aggTrade':
                    # Create a trade object in CCXT format
                    timestamp = data['E']  # Event time
                    trade = {
                        'id': data['a'],  # Aggregate trade ID
                        'timestamp': timestamp,
                        'datetime': datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc).isoformat(),
                        'symbol': pair,
                        'price': float(data['p']),
                        'amount': float(data['q']),
                        'side': 'sell' if data['m'] else 'buy',  # m is trade maker side
                    }
                    
                    # Add to buffer with thread safety
                    with self._buffer_lock:
                        self._trade_buffer[pair].append(trade)
                        buffer_len = len(self._trade_buffer[pair])
                    
                    # Process buffer if it reaches a certain size or periodically
                    if buffer_len >= 100:
                        self._process_trade_buffer(pair)
                        
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
        
        def on_error(ws, error):
            """Handle WebSocket error"""
            logger.error(f"WebSocket error: {error}")
            
        def on_close(ws, close_status_code, close_reason):
            """Handle WebSocket close"""
            logger.warning(f"WebSocket closed: {close_status_code} - {close_reason}")
            self._ws_connected = False
            
            # Reconnect after a delay if not stopping
            if not self._stop_event.is_set():
                logger.info(f"Reconnecting WebSocket for {pair} in 5 seconds...")
                time.sleep(5)
                self._run_binance_websocket(stream_url, stream_name, pair, is_futures)
        
        def on_open(ws):
            """Handle WebSocket open"""
            logger.info(f"WebSocket connected for {pair}")
            self._ws_connected = True
            
            # Subscribe to the trade stream
            subscribe_msg = {
                "method": "SUBSCRIBE",
                "params": [stream_name],
                "id": 1
            }
            ws.send(json.dumps(subscribe_msg))
            
        # Create and run WebSocket
        websocket.enableTrace(False)
        ws = websocket.WebSocketApp(
            stream_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )
        
        # Store the WebSocket client for later access
        self._ws_clients[pair] = ws
        
        # Run the WebSocket client in the current thread
        ws.run_forever(ping_interval=30, ping_timeout=10)
    
    def _process_trade_buffer(self, pair):
        """Process trade buffer for a pair and convert to candles"""
        with self._buffer_lock:
            # Get trades from buffer
            trades = self._trade_buffer[pair].copy()
            # Clear the buffer
            self._trade_buffer[pair] = []
        
        if not trades:
            return
        
        # Process trades and create candles
        self._process_and_store_trades(pair, trades)
        
        # Update metadata with the last trade
        last_trade = max(trades, key=lambda t: t['timestamp'])
        self.last_trade_ids[pair] = last_trade['id']
        self.last_update_times[pair] = datetime.fromtimestamp(last_trade['timestamp'] / 1000, tz=timezone.utc)
        
        self._update_metadata(
            pair,
            last_trade['id'],
            last_trade['timestamp']
        )
        
        logger.debug(f"Processed {len(trades)} WebSocket trades for {pair}")
    
    def fetch_initial_history(self, pair: str):
        """Fetch initial historical data for a pair that has no existing data"""
        logger.info(f"Fetching initial {self.initial_history_hours}h history for {pair}...")
        
        try:
            # Calculate start time
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=self.initial_history_hours)
            since_ms = int(start_time.timestamp() * 1000)
            
            # Fetch trades in batches
            all_trades = []
            last_timestamp = since_ms
            max_retries = 3
            retry_count = 0
            
            while True:
                try:
                    logger.info(f"Fetching trades for {pair} since {datetime.fromtimestamp(last_timestamp/1000, tz=timezone.utc)}")
                    trades = self.exchange.fetch_trades(
                        pair, 
                        since=last_timestamp, 
                        limit=DEFAULT_TRADE_LIMIT
                    )
                    
                    if not trades:
                        # No more trades available or reached current time
                        break
                    
                    all_trades.extend(trades)
                    logger.info(f"Fetched {len(trades)} trades, total: {len(all_trades)}")
                    
                    # Update last timestamp for next batch
                    last_timestamp = trades[-1]['timestamp'] + 1
                    
                    # If we've reached current time, stop
                    if last_timestamp >= int(end_time.timestamp() * 1000):
                        break
                    
                    # Don't hammer the API
                    time.sleep(1)
                    retry_count = 0
                    
                except Exception as e:
                    retry_count += 1
                    if retry_count >= max_retries:
                        logger.error(f"Failed to fetch trades after {max_retries} retries: {e}")
                        break
                    
                    logger.warning(f"Error fetching trades (retry {retry_count}/{max_retries}): {e}")
                    time.sleep(retry_count * 2)  # Exponential backoff
            
            logger.info(f"Fetched total of {len(all_trades)} historical trades for {pair}")
            
            if all_trades:
                # Process and store the trades
                self._process_and_store_trades(pair, all_trades)
                
                # Update metadata with the last trade info
                last_trade = all_trades[-1]
                self.last_trade_ids[pair] = last_trade['id']
                self.last_update_times[pair] = datetime.fromtimestamp(last_trade['timestamp'] / 1000, tz=timezone.utc)
                
                self._update_metadata(
                    pair, 
                    last_trade['id'], 
                    last_trade['timestamp']
                )
                
                logger.info(f"Initial history for {pair} processed and stored")
            else:
                logger.warning(f"No historical trades found for {pair}")
                
        except Exception as e:
            logger.error(f"Error fetching initial history for {pair}: {e}")
    
    def _process_and_store_trades(self, pair: str, trades: List[dict]):
        """Process trades and store both raw trades and derived candles"""
        if not trades:
            return
        
        try:
            # Convert to DataFrame
            trades_df = pd.DataFrame([{
                'id': t['id'],
                'timestamp': t['timestamp'],
                'datetime': t['datetime'],
                'price': float(t['price']),
                'amount': float(t['amount']),
                'side': t['side']
            } for t in trades])
            
            # Convert timestamp to datetime for easier processing
            trades_df['date'] = pd.to_datetime(trades_df['timestamp'], unit='ms')
            
            # Store raw trades (optional)
            self._store_raw_trades(pair, trades_df)
            
            # Convert to 5s candles and store
            candles_df = self._trades_to_candles(trades_df)
            if not candles_df.empty:
                self._store_candles(pair, candles_df)
            
            logger.debug(f"Processed {len(trades)} trades into {len(candles_df)} candles for {pair}")
            
        except Exception as e:
            logger.error(f"Error processing trades for {pair}: {e}")
    
    def _trades_to_candles(self, trades_df: pd.DataFrame) -> pd.DataFrame:
        """Convert trades DataFrame to 5-second OHLCV candles"""
        if trades_df.empty:
            return pd.DataFrame()
        
        # Floor timestamp to 5-second intervals
        trades_df['candle_time'] = trades_df['date'].dt.floor('5s')
        
        # Group by 5s intervals
        grouped = trades_df.groupby('candle_time')
        
        # Create OHLCV candles
        candles = pd.DataFrame({
            'date': grouped.indices.keys(),
            'open': grouped['price'].first(),
            'high': grouped['price'].max(),
            'low': grouped['price'].min(),
            'close': grouped['price'].last(),
            'volume': grouped['amount'].sum()
        })
        
        # Sort by date
        candles = candles.sort_values('date')
        
        # Convert date to timestamp (milliseconds)
        candles['timestamp'] = candles['date'].astype(np.int64) // 10**6
        
        return candles
    
    def _store_candles(self, pair: str, candles_df: pd.DataFrame):
        """Store OHLCV candles in the database"""
        if candles_df.empty:
            return
        
        try:
            # Convert to list of tuples for bulk insert
            candles_data = [
                (pair, int(row['timestamp']), float(row['open']), 
                 float(row['high']), float(row['low']), float(row['close']), 
                 float(row['volume']))
                for _, row in candles_df.iterrows()
            ]
            
            cursor = self.conn.cursor()
            cursor.executemany(
                '''
                INSERT OR REPLACE INTO candles 
                (pair, timestamp, open, high, low, close, volume) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', 
                candles_data
            )
            self.conn.commit()
            
            logger.debug(f"Stored {len(candles_data)} candles for {pair}")
            
        except sqlite3.Error as e:
            logger.error(f"Database error storing candles for {pair}: {e}")
    
    def _store_raw_trades(self, pair: str, trades_df: pd.DataFrame):
        """Store raw trades in the database (optional)"""
        if trades_df.empty:
            return
        
        try:
            # Convert to list of tuples for bulk insert
            trades_data = [
                (pair, str(row['id']), int(row['timestamp']), 
                 float(row['price']), float(row['amount']), row['side'])
                for _, row in trades_df.iterrows()
            ]
            
            cursor = self.conn.cursor()
            cursor.executemany(
                '''
                INSERT OR IGNORE INTO trades 
                (pair, trade_id, timestamp, price, amount, side) 
                VALUES (?, ?, ?, ?, ?, ?)
                ''', 
                trades_data
            )
            self.conn.commit()
            
            logger.debug(f"Stored {len(trades_data)} raw trades for {pair}")
            
        except sqlite3.Error as e:
            logger.error(f"Database error storing raw trades for {pair}: {e}")
    
    def _update_metadata(self, pair: str, last_trade_id: str, last_timestamp: int):
        """Update metadata record for a pair"""
        try:
            now = int(datetime.now(timezone.utc).timestamp() * 1000)
            
            cursor = self.conn.cursor()
            cursor.execute(
                '''
                INSERT OR REPLACE INTO metadata 
                (pair, last_trade_id, last_timestamp, last_update) 
                VALUES (?, ?, ?, ?)
                ''', 
                (pair, last_trade_id, last_timestamp, now)
            )
            self.conn.commit()
            
            logger.debug(f"Updated metadata for {pair}: last_trade_id={last_trade_id}, last_timestamp={last_timestamp}")
            
        except sqlite3.Error as e:
            logger.error(f"Database error updating metadata for {pair}: {e}")
    
    def fetch_new_trades(self, pair: str):
        """Fetch new trades for a pair since the last update"""
        # Skip if using WebSocket for this pair and it's connected
        if self.enable_websocket and self._ws_connected and pair in self._ws_clients:
            # Process any buffered trades from WebSocket
            self._process_trade_buffer(pair)
            return True
        
        try:
            logger.debug(f"Fetching new trades for {pair}...")
            
            # Determine parameters for fetching
            params = {}
            since = None
            
            if pair in self.last_trade_ids and self.last_trade_ids[pair]:
                # Different exchanges have different pagination mechanisms
                if self.exchange_name.lower() == 'binance':
                    # Binance can paginate using from_id
                    params['fromId'] = self.last_trade_ids[pair]
                else:
                    # Others use timestamp-based pagination
                    if pair in self.last_update_times and self.last_update_times[pair]:
                        # Add a small buffer to avoid missing trades
                        since_time = self.last_update_times[pair] - timedelta(seconds=30)
                        since = int(since_time.timestamp() * 1000)
            
            # Fetch trades
            trades = self.exchange.fetch_trades(
                pair, 
                since=since, 
                limit=DEFAULT_TRADE_LIMIT, 
                params=params
            )
            
            if trades:
                logger.info(f"Fetched {len(trades)} new trades for {pair}")
                
                # Filter out already processed trades if using timestamp-based pagination
                if since and pair in self.last_trade_ids:
                    last_id = self.last_trade_ids[pair]
                    trades = [t for t in trades if t['id'] > last_id]
                    logger.debug(f"Filtered to {len(trades)} new trades after last ID {last_id}")
                
                # Process and store the trades
                if trades:
                    self._process_and_store_trades(pair, trades)
                    
                    # Update metadata with the last trade info
                    last_trade = trades[-1]
                    self.last_trade_ids[pair] = last_trade['id']
                    self.last_update_times[pair] = datetime.fromtimestamp(last_trade['timestamp'] / 1000, tz=timezone.utc)
                    
                    self._update_metadata(
                        pair, 
                        last_trade['id'], 
                        last_trade['timestamp']
                    )
                    
                    # Reset failed retry counter on success
                    self.failed_pair_retries[pair] = 0
            else:
                logger.debug(f"No new trades for {pair}")
            
            return True
            
        except Exception as e:
            # Track retry count
            if pair not in self.failed_pair_retries:
                self.failed_pair_retries[pair] = 0
            
            self.failed_pair_retries[pair] += 1
            retry_count = self.failed_pair_retries[pair]
            
            logger.error(f"Error fetching trades for {pair} (retry {retry_count}): {e}")
            
            # If we've failed too many times, back off from this pair temporarily
            if retry_count > 5:
                logger.warning(f"Too many failures for {pair}, backing off for a while")
                # We'll still retry but log a warning
            
            return False
    
    def cleanup_old_data(self):
        """Remove old data from the database to manage size"""
        if self.retention_days <= 0:
            # Retention disabled
            return
        
        try:
            # Calculate cutoff timestamp
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
            cutoff_timestamp = int(cutoff_date.timestamp() * 1000)
            
            logger.info(f"Cleaning up data older than {cutoff_date}")
            
            cursor = self.conn.cursor()
            
            # Delete old candles
            cursor.execute(
                'DELETE FROM candles WHERE timestamp < ?', 
                (cutoff_timestamp,)
            )
            candles_deleted = cursor.rowcount
            
            # Delete old trades
            cursor.execute(
                'DELETE FROM trades WHERE timestamp < ?', 
                (cutoff_timestamp,)
            )
            trades_deleted = cursor.rowcount
            
            self.conn.commit()
            
            logger.info(f"Cleanup complete: removed {candles_deleted} candles and {trades_deleted} trades")
            
        except sqlite3.Error as e:
            logger.error(f"Database error during cleanup: {e}")
    
    def process_pair(self, pair: str):
        """Process updates for a single pair"""
        try:
            # Check if we need to fetch initial history
            if pair not in self.last_trade_ids or self.last_trade_ids[pair] is None:
                self.fetch_initial_history(pair)
            else:
                # Fetch new trades since last update
                self.fetch_new_trades(pair)
                
        except Exception as e:
            logger.error(f"Error processing {pair}: {e}")
    
    def run_collection_loop(self):
        """Main collection loop - runs continuously until stopped"""
        logger.info(f"Starting collection loop for {len(self.pairs)} pairs...")
        
        cleanup_countdown = 60  # Run cleanup every ~60 cycles
        
        while not self._stop_event.is_set():
            cycle_start = time.time()
            
            # For each pair, check if we need to process trades
            # When using WebSocket, we'll process buffered trades
            for pair in self.pairs:
                if self._stop_event.is_set():
                    break
                
                try:
                    # If WebSocket is enabled and connected, we'll process buffered trades
                    # Otherwise, fall back to REST API
                    if (self.enable_websocket and pair in self._ws_clients and 
                        self._ws_clients[pair].sock and self._ws_clients[pair].sock.connected):
                        self._process_trade_buffer(pair)
                    else:
                        self.process_pair(pair)
                        
                except Exception as e:
                    logger.error(f"Unexpected error processing {pair}: {e}")
            
            # Periodically clean up old data
            cleanup_countdown -= 1
            if cleanup_countdown <= 0:
                self.cleanup_old_data()
                cleanup_countdown = 60  # Reset countdown
            
            # Calculate sleep time
            elapsed = time.time() - cycle_start
            sleep_time = max(0.1, self.update_interval - elapsed)
            
            logger.debug(f"Collection cycle took {elapsed:.2f}s, sleeping for {sleep_time:.2f}s")
            
            # Wait for the next cycle or until stopped
            self._stop_event.wait(sleep_time)
    
    def start(self):
        """Start the collector in a background thread"""
        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("Starting trade collector...")
        
        # Start main collection thread
        collection_thread = Thread(target=self.run_collection_loop)
        collection_thread.daemon = True
        collection_thread.start()
        self._threads.append(collection_thread)
        
        logger.info("Collector started successfully")
        
        return collection_thread
    
    def stop(self):
        """Stop the collector"""
        logger.info("Stopping trade collector...")
        
        # Signal threads to stop
        self._stop_event.set()
        
        # Close WebSocket connections
        for pair, ws in self._ws_clients.items():
            try:
                logger.info(f"Closing WebSocket for {pair}")
                if hasattr(ws, 'close'):
                    ws.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket for {pair}: {e}")
        
        # Wait for threads to finish
        for thread in self._threads:
            if thread.is_alive():
                thread.join(timeout=10)
        
        # Close database connection
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
            
        logger.info("Collector stopped")
    
    def _signal_handler(self, sig, frame):
        """Handle termination signals"""
        logger.info(f"Received signal {sig}, shutting down...")
        self.stop()
        sys.exit(0)

def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(description='5-Second Candle Data Collector for FreqTrade')
    
    parser.add_argument('--exchange', type=str, default=DEFAULT_EXCHANGE,
                        help=f'Exchange name (ccxt) (default: {DEFAULT_EXCHANGE})')
    
    parser.add_argument('--pairs', type=str, nargs='+', default=DEFAULT_PAIRS,
                        help=f'Trading pairs to collect data for (default: {DEFAULT_PAIRS[0]})')
    
    parser.add_argument('--db-path', type=str, default=DEFAULT_DB_PATH,
                        help=f'Path to the SQLite database (default: {DEFAULT_DB_PATH})')
    
    parser.add_argument('--api-key', type=str, 
                        help='API key (optional)')
    
    parser.add_argument('--api-secret', type=str,
                        help='API secret (optional)')
    
    parser.add_argument('--update-interval', type=int, default=DEFAULT_UPDATE_INTERVAL,
                        help=f'Seconds between updates (default: {DEFAULT_UPDATE_INTERVAL})')
    
    parser.add_argument('--retention-days', type=int, default=DEFAULT_RETENTION_DAYS,
                        help=f'Days to keep data (default: {DEFAULT_RETENTION_DAYS}, 0 = keep forever)')
    
    parser.add_argument('--disable-websocket', action='store_true',
                        help='Disable WebSocket connections')
    
    parser.add_argument('--history-hours', type=int, default=DEFAULT_INITIAL_HISTORY_HOURS,
                        help=f'Hours of historical data to fetch on startup (default: {DEFAULT_INITIAL_HISTORY_HOURS})')
    
    parser.add_argument('--daemon', action='store_true',
                        help='Run as a daemon process')
    
    args = parser.parse_args()
    
    try:
        # Initialize collector
        collector = TradeCollector(
            exchange_name=args.exchange,
            pairs=args.pairs,
            db_path=args.db_path,
            api_key=args.api_key,
            api_secret=args.api_secret,
            update_interval=args.update_interval,
            retention_days=args.retention_days,
            enable_websocket=not args.disable_websocket,
            initial_history_hours=args.history_hours,
        )
        
        # Start the collector
        main_thread = collector.start()
        
        if args.daemon:
            # Detach from terminal
            logger.info("Running in daemon mode")
            sys.stdout.flush()
            sys.stderr.flush()
            
            # Keep alive until stopped
            main_thread.join()
        else:
            # Interactive mode - keep running until Ctrl+C
            logger.info("Running in interactive mode (Ctrl+C to stop)")
            
            try:
                # Keep the main thread running
                while main_thread.is_alive():
                    main_thread.join(1.0)  # Join with timeout to keep main thread responsive
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received, shutting down...")
                collector.stop()
        
    except Exception as e:
        logger.error(f"Collector failed: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main()) 
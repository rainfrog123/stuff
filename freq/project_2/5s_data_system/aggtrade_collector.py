#!/usr/bin/env python3
"""
Data collector that uses Binance's aggTrade WebSocket functionality to fetch aggregated trade data
and generate 5-second candles, storing everything in a local database.
Only keeps 1 hour of 5-second data.
"""

import asyncio
import logging
import os
import sys
import time
import signal
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import websockets
import ccxt

from database import MarketDatabase
from config import (
    EXCHANGE, EXCHANGE_CREDENTIALS, SYMBOLS, MAX_TRADES,
    CANDLE_TIMEFRAME, MAX_RECONNECT_ATTEMPTS, RECONNECT_DELAY,
    LOG_LEVEL, LOG_FILE, LOG_DIR
)

# Set up logging
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Define retention period - 1 hour in milliseconds
RETENTION_PERIOD_MS = 60 * 60 * 1000

# Binance WebSocket URL
BINANCE_WS_URL = "wss://stream.binance.com:9443/ws"

class AggTradeDataCollector:
    """
    Collects real-time aggregated trade data and generates 5-second candles,
    storing everything in a local SQLite database. Only keeps 1 hour of data.
    """
    
    def __init__(self):
        """Initialize the data collector."""
        self.db = MarketDatabase()
        self.running = False
        self.tasks = {}
        self.websockets = {}
        self.latest_trades = {symbol: [] for symbol in SYMBOLS}
        self.latest_trade_ids = {symbol: set() for symbol in SYMBOLS}
        self.last_update_time = {symbol: 0 for symbol in SYMBOLS}
        self.last_candle_time = {symbol: 0 for symbol in SYMBOLS}
        
        # Setting up exchange for symbol normalization
        self.exchange = getattr(ccxt, EXCHANGE)(EXCHANGE_CREDENTIALS)
        
        # Handle shutdown signals
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, sig, frame):
        """Handle shutdown signals gracefully."""
        logger.info("Shutdown signal received. Cleaning up...")
        self.running = False
    
    def normalize_timestamp(self, timestamp_ms, interval_sec=5):
        """Normalize timestamp to the nearest 5-second interval with TradingView offset."""
        # Add 2800ms offset to match TradingView's bucketing - based on our research
        adjusted_ts = timestamp_ms + 2800
        timestamp_sec = adjusted_ts / 1000
        normalized_sec = int(timestamp_sec // interval_sec) * interval_sec
        return int(normalized_sec * 1000)
    
    def generate_candles_from_trades(self, trades, symbol):
        """Generate 5-second candles from a list of trades."""
        if not trades:
            return []
        
        # Convert trades to DataFrame
        df = pd.DataFrame([{
            'timestamp': trade['timestamp'],
            'price': float(trade['price']),
            'amount': float(trade['amount']),
            'side': trade.get('side', 'buy' if trade.get('m', False) else 'sell')  # Adapt to aggTrade format
        } for trade in trades])
        
        # Normalize timestamps to 5-second intervals
        df['candle_time'] = df['timestamp'].apply(self.normalize_timestamp)
        
        # Group by candle time
        candles = []
        for candle_time, group in df.groupby('candle_time'):
            if len(group) > 0:
                candle_open = group.iloc[0]['price']
                candle_high = group['price'].max()
                candle_low = group['price'].min()
                candle_close = group.iloc[-1]['price']
                candle_volume = group['amount'].sum()
                
                candles.append([
                    candle_time,  # timestamp
                    candle_open,  # open
                    candle_high,  # high
                    candle_low,   # low
                    candle_close, # close
                    candle_volume # volume
                ])
        
        return sorted(candles, key=lambda x: x[0])
    
    def format_symbol_for_binance(self, symbol):
        """Convert CCXT symbol format to Binance WebSocket format."""
        # Remove / and convert to lowercase: BTC/USDT -> btcusdt
        return symbol.replace('/', '').lower()
    
    def parse_aggtrade(self, aggtrade_msg, symbol):
        """Parse aggTrade message from Binance WebSocket."""
        try:
            data = json.loads(aggtrade_msg)
            # Check if it's a ping message
            if 'ping' in data:
                return None
            
            # For combined streams, the data is nested
            if 'data' in data:
                data = data['data']
            
            # Format the trade data to match our existing structure
            trade = {
                'id': str(data['a']),               # Aggregate trade ID
                'timestamp': data['T'],             # Trade time
                'datetime': datetime.fromtimestamp(data['T'] / 1000).isoformat(),
                'symbol': symbol,
                'price': float(data['p']),
                'amount': float(data['q']),
                'm': data['m'],                     # Is the buyer the market maker?
                'side': 'sell' if data['m'] else 'buy',  # Derive side from m
                'info': aggtrade_msg                # Store original message
            }
            return trade
        except Exception as e:
            logger.error(f"Error parsing aggTrade message: {e}")
            return None
    
    async def process_aggtrade_updates(self, symbol):
        """Process aggTrade updates for a symbol using direct WebSocket connection."""
        binance_symbol = self.format_symbol_for_binance(symbol)
        ws_url = f"{BINANCE_WS_URL}/{binance_symbol}@aggTrade"
        attempt = 0
        
        while self.running and attempt < MAX_RECONNECT_ATTEMPTS:
            try:
                logger.info(f"Starting aggTrade WebSocket connection for {symbol} at {ws_url}")
                
                async with websockets.connect(ws_url) as websocket:
                    self.websockets[symbol] = websocket
                    
                    # Send ping every 20 seconds to keep connection alive
                    ping_task = asyncio.create_task(self.ping_websocket(websocket, symbol))
                    
                    while self.running:
                        message = await websocket.recv()
                        
                        # Parse the aggTrade message
                        trade = self.parse_aggtrade(message, symbol)
                        
                        if trade and trade['id'] not in self.latest_trade_ids[symbol]:
                            # Add to our collections
                            self.latest_trade_ids[symbol].add(trade['id'])
                            self.latest_trades[symbol].append(trade)
                            
                            # Keep trade buffer size limited
                            if len(self.latest_trades[symbol]) > MAX_TRADES:
                                excess = len(self.latest_trades[symbol]) - MAX_TRADES
                                self.latest_trades[symbol] = self.latest_trades[symbol][excess:]
                                
                                # Also update the ID set
                                self.latest_trade_ids[symbol] = set(
                                    trade['id'] for trade in self.latest_trades[symbol]
                                )
                            
                            # Insert into database
                            self.db.insert_trades([trade], symbol)
                            self.last_update_time[symbol] = time.time()
                            
                            # Check if it's time to generate a new candle
                            current_time_ms = int(time.time() * 1000)
                            normalized_time = self.normalize_timestamp(current_time_ms)
                            
                            if normalized_time > self.last_candle_time[symbol]:
                                # Generate candle for previous interval
                                candles = self.generate_latest_candle(symbol)
                                if candles:
                                    self.db.insert_candles(candles, symbol)
                                self.last_candle_time[symbol] = normalized_time
                    
                    # Cancel ping task when exiting the loop
                    ping_task.cancel()
                    try:
                        await ping_task
                    except asyncio.CancelledError:
                        pass
                
                # Reset attempt counter on successful execution
                attempt = 0
            except (websockets.exceptions.ConnectionClosed, 
                    websockets.exceptions.ConnectionClosedError,
                    websockets.exceptions.ConnectionClosedOK) as e:
                logger.warning(f"WebSocket connection closed for {symbol}: {e}")
                attempt += 1
                await asyncio.sleep(RECONNECT_DELAY)
            except Exception as e:
                logger.error(f"Error in aggTrade WebSocket connection for {symbol}: {e}")
                attempt += 1
                logger.info(f"Reconnect attempt {attempt}/{MAX_RECONNECT_ATTEMPTS} in {RECONNECT_DELAY} seconds")
                await asyncio.sleep(RECONNECT_DELAY)
        
        if attempt >= MAX_RECONNECT_ATTEMPTS:
            logger.error(f"Failed to maintain WebSocket connection for {symbol} after {MAX_RECONNECT_ATTEMPTS} attempts")
    
    async def ping_websocket(self, websocket, symbol):
        """Send periodic pings to keep the WebSocket connection alive."""
        try:
            while True:
                await asyncio.sleep(20)  # Send ping every 20 seconds
                if websocket.open:
                    await websocket.send(json.dumps({"ping": int(time.time() * 1000)}))
                    logger.debug(f"Sent ping to {symbol} WebSocket")
                else:
                    logger.warning(f"WebSocket for {symbol} is closed, stopping ping")
                    break
        except asyncio.CancelledError:
            logger.debug(f"Ping task for {symbol} was cancelled")
        except Exception as e:
            logger.error(f"Error in ping task for {symbol}: {e}")
    
    def generate_latest_candle(self, symbol):
        """Generate a candle from the latest trades for a symbol."""
        current_time_ms = int(time.time() * 1000)
        normalized_time = self.normalize_timestamp(current_time_ms)
        prev_interval = normalized_time - 5000  # Previous 5-second interval
        
        # Filter trades for the previous interval
        interval_trades = [
            trade for trade in self.latest_trades[symbol]
            if self.normalize_timestamp(trade['timestamp']) == prev_interval
        ]
        
        # Generate candle from these trades
        return self.generate_candles_from_trades(interval_trades, symbol)
    
    async def maintenance_task(self):
        """Perform regular maintenance tasks like pruning old data."""
        while self.running:
            try:
                current_time_ms = int(time.time() * 1000)
                cutoff_time = current_time_ms - RETENTION_PERIOD_MS
                
                for symbol in SYMBOLS:
                    # Prune old trades and candles to keep only 1 hour of data
                    trades_removed = self.db.prune_old_data(symbol, "trades", cutoff_time)
                    candles_removed = self.db.prune_old_data(symbol, "candles", cutoff_time)
                    
                    if trades_removed or candles_removed:
                        logger.info(f"Pruned {trades_removed} trades and {candles_removed} candles older than 1 hour for {symbol}")
                
                # Wait before the next maintenance cycle
                await asyncio.sleep(60)  # Check every 1 minute
            except Exception as e:
                logger.error(f"Error in maintenance task: {e}")
                await asyncio.sleep(60)  # Longer wait on error
    
    async def run(self):
        """Run the data collection system."""
        self.running = True
        
        # Start WebSocket connections for each symbol
        for symbol in SYMBOLS:
            self.tasks[symbol] = asyncio.create_task(self.process_aggtrade_updates(symbol))
        
        # Start maintenance task
        maintenance_task = asyncio.create_task(self.maintenance_task())
        
        # Wait for completion or error
        try:
            await asyncio.gather(*self.tasks.values(), maintenance_task)
        except asyncio.CancelledError:
            logger.info("Tasks cancelled")
        except Exception as e:
            logger.error(f"Error in main task: {e}")
        
        return True
    
    async def stop(self):
        """Stop the data collection system."""
        self.running = False
        
        # Close all WebSocket connections
        for symbol, websocket in self.websockets.items():
            if websocket and not websocket.closed:
                await websocket.close()
        
        # Cancel all tasks
        for symbol, task in self.tasks.items():
            if not task.done():
                task.cancel()
        
        # Close database
        self.db.close()
        
        logger.info("AggTrade data collection system stopped")

async def main():
    """Main entry point for the aggTrade data collection system."""
    collector = AggTradeDataCollector()
    
    try:
        await collector.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        await collector.stop()

if __name__ == "__main__":
    asyncio.run(main()) 
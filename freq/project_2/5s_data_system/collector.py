#!/usr/bin/env python3
"""
Data collector that uses ccxtpro to fetch real-time trade data
and generate 5-second candles, storing everything in a local database.
"""

import asyncio
import logging
import os
import sys
import time
import signal
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import ccxtpro

from database import MarketDatabase
from config import (
    EXCHANGE, EXCHANGE_CREDENTIALS, SYMBOLS, MAX_TRADES,
    CANDLE_TIMEFRAME, MAX_RECONNECT_ATTEMPTS, RECONNECT_DELAY,
    INITIAL_HISTORY_MINUTES, LOG_LEVEL, LOG_FILE, LOG_DIR
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

class DataCollector:
    """
    Collects real-time trade data and generates 5-second candles,
    storing everything in a local SQLite database.
    """
    
    def __init__(self):
        """Initialize the data collector."""
        self.db = MarketDatabase()
        self.exchange = None
        self.running = False
        self.tasks = {}
        self.latest_trades = {symbol: [] for symbol in SYMBOLS}
        self.latest_trade_ids = {symbol: set() for symbol in SYMBOLS}
        self.candle_buffers = {symbol: [] for symbol in SYMBOLS}
        self.last_update_time = {symbol: 0 for symbol in SYMBOLS}
        self.last_candle_time = {symbol: 0 for symbol in SYMBOLS}
        
        # Handle shutdown signals
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, sig, frame):
        """Handle shutdown signals gracefully."""
        logger.info("Shutdown signal received. Cleaning up...")
        self.running = False
        
    async def init_exchange(self):
        """Initialize the exchange connection with ccxtpro."""
        try:
            exchange_class = getattr(ccxtpro, EXCHANGE)
            self.exchange = exchange_class(EXCHANGE_CREDENTIALS)
            
            # Load markets for symbol normalization
            await self.exchange.load_markets()
            logger.info(f"Successfully connected to {EXCHANGE} exchange")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize exchange: {e}")
            return False
    
    async def fetch_historical_data(self, symbol, minutes=60):
        """Fetch historical trade data for a symbol."""
        try:
            logger.info(f"Fetching {minutes} minutes of historical trade data for {symbol}")
            since = int((datetime.now() - timedelta(minutes=minutes)).timestamp() * 1000)
            
            trades = await self.exchange.fetch_trades(symbol, since=since)
            logger.info(f"Fetched {len(trades)} historical trades for {symbol}")
            
            if trades:
                self.db.insert_trades(trades, symbol)
                
                # Generate historical candles
                candles = self.generate_candles_from_trades(trades, symbol)
                if candles:
                    self.db.insert_candles(candles, symbol)
                    logger.info(f"Generated {len(candles)} historical 5s candles for {symbol}")
            
            return len(trades)
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            return 0
    
    def normalize_timestamp(self, timestamp_ms, interval_sec=5):
        """Normalize timestamp to the nearest 5-second interval."""
        timestamp_sec = timestamp_ms / 1000
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
            'side': trade['side']
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
    
    async def process_trade_updates(self, symbol):
        """Process trade updates for a symbol using websockets."""
        attempt = 0
        
        while self.running and attempt < MAX_RECONNECT_ATTEMPTS:
            try:
                logger.info(f"Starting trade subscription for {symbol}")
                
                # Subscribe to trades
                while self.running:
                    trades = await self.exchange.watch_trades(symbol)
                    
                    if trades:
                        # Filter out duplicates
                        new_trades = []
                        for trade in trades:
                            if trade['id'] not in self.latest_trade_ids[symbol]:
                                self.latest_trade_ids[symbol].add(trade['id'])
                                new_trades.append(trade)
                                self.latest_trades[symbol].append(trade)
                        
                        # Keep trade buffer size limited
                        if len(self.latest_trades[symbol]) > MAX_TRADES:
                            excess = len(self.latest_trades[symbol]) - MAX_TRADES
                            self.latest_trades[symbol] = self.latest_trades[symbol][excess:]
                            
                            # Also update the ID set
                            self.latest_trade_ids[symbol] = set(
                                trade['id'] for trade in self.latest_trades[symbol]
                            )
                        
                        # Process new trades
                        if new_trades:
                            self.db.insert_trades(new_trades, symbol)
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
                
                # Reset attempt counter on successful connection
                attempt = 0
                
            except Exception as e:
                attempt += 1
                logger.error(f"Error in trade websocket for {symbol} (attempt {attempt}/{MAX_RECONNECT_ATTEMPTS}): {e}")
                
                if attempt < MAX_RECONNECT_ATTEMPTS:
                    wait_time = RECONNECT_DELAY * attempt
                    logger.info(f"Reconnecting to {symbol} in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Max reconnection attempts reached for {symbol}. Giving up.")
    
    def generate_latest_candle(self, symbol):
        """Generate a candle from the latest trades for a symbol."""
        # Filter trades for the last interval
        current_time_ms = int(time.time() * 1000)
        interval_start = self.normalize_timestamp(current_time_ms) - 5000  # 5 seconds ago
        
        # Filter trades in the last interval
        recent_trades = [
            trade for trade in self.latest_trades[symbol]
            if trade['timestamp'] >= interval_start and trade['timestamp'] < current_time_ms
        ]
        
        if recent_trades:
            candles = self.generate_candles_from_trades(recent_trades, symbol)
            return candles
        return []
    
    async def maintenance_task(self):
        """Perform periodic maintenance tasks."""
        while self.running:
            try:
                # Prune old trades from database
                for symbol in SYMBOLS:
                    self.db.prune_old_trades(symbol, MAX_TRADES)
                
                # Check for stale connections
                current_time = time.time()
                for symbol in SYMBOLS:
                    if current_time - self.last_update_time[symbol] > 30:  # 30-second threshold
                        logger.warning(f"No updates for {symbol} in 30 seconds. Connection may be stale.")
            
            except Exception as e:
                logger.error(f"Error in maintenance task: {e}")
            
            await asyncio.sleep(60)  # Run maintenance every minute
    
    async def run(self):
        """Run the data collector."""
        self.running = True
        
        # Initialize exchange
        success = await self.init_exchange()
        if not success:
            logger.error("Failed to initialize exchange. Exiting.")
            return
        
        # Fetch initial historical data
        for symbol in SYMBOLS:
            await self.fetch_historical_data(symbol, minutes=INITIAL_HISTORY_MINUTES)
        
        # Start trade processing tasks for each symbol
        for symbol in SYMBOLS:
            normalized_symbol = self.exchange.market(symbol)['symbol'] if symbol in self.exchange.markets else symbol
            self.tasks[symbol] = asyncio.create_task(self.process_trade_updates(normalized_symbol))
            logger.info(f"Started data collection for {normalized_symbol}")
        
        # Start maintenance task
        maintenance_task = asyncio.create_task(self.maintenance_task())
        
        # Wait for tasks to complete
        try:
            await asyncio.gather(*self.tasks.values(), maintenance_task)
        except asyncio.CancelledError:
            logger.info("Tasks cancelled")
        finally:
            # Clean up
            if self.exchange:
                await self.exchange.close()
            logger.info("Data collector stopped")
    
    async def stop(self):
        """Stop the data collector gracefully."""
        self.running = False
        
        # Cancel all tasks
        for symbol, task in self.tasks.items():
            if not task.done():
                task.cancel()
        
        # Close exchange
        if self.exchange:
            await self.exchange.close()
        
        logger.info("Data collector stopped")

async def main():
    """Main function to run the data collector."""
    collector = DataCollector()
    try:
        await collector.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down...")
    finally:
        await collector.stop()

if __name__ == "__main__":
    logger.info("Starting 5-second data collection system")
    asyncio.run(main()) 
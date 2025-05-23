#!/usr/bin/env python3
"""
5-Second Data Collector
High-precision candle collection with exact time boundaries and raw trade processing.
"""

import asyncio
import logging
import time
import signal
import numpy as np
from datetime import datetime
from collections import deque, defaultdict
from typing import Dict, List, Optional, Set
import ccxt.pro as ccxtpro
from dataclasses import dataclass
from asyncio import Queue, Semaphore

from database import MarketDatabase
from settings import EXCHANGE, EXCHANGE_CREDENTIALS, SYMBOLS, LOG_LEVEL, LOG_FILE

# Setup logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL), format='%(asctime)s - %(levelname)s - %(message)s',
                   handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()])
logger = logging.getLogger(__name__)

# Constants
CANDLE_INTERVAL_MS = 5000
TRADE_BUFFER_SIZE = 2000
QUEUE_SIZE = 10000
BATCH_SIZE = 25
MAX_TRADE_IDS = 5000

@dataclass
class RawTrade:
    """Raw trade data with full precision"""
    id: str
    timestamp_ms: int
    price: float
    amount: float
    symbol: str
    side: str

@dataclass
class Candle:
    """5-second candle with precise boundaries"""
    timestamp_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    trade_count: int
    symbol: str

class DataCollector:
    def __init__(self):
        self.db = MarketDatabase()
        self.exchange = None
        self.running = False
        
        # Data structures
        self.trade_queues = {symbol: Queue(maxsize=QUEUE_SIZE) for symbol in SYMBOLS}
        self.candle_queues = {symbol: Queue(maxsize=QUEUE_SIZE) for symbol in SYMBOLS}
        self.trade_buffers = {symbol: deque(maxlen=TRADE_BUFFER_SIZE) for symbol in SYMBOLS}
        self.trade_id_sets = {symbol: set() for symbol in SYMBOLS}
        
        # Time boundary tracking
        self.last_candle_boundary = {symbol: 0 for symbol in SYMBOLS}
        self.pending_candles = {symbol: {} for symbol in SYMBOLS}
        
        # Stats and semaphore
        self.stats = defaultdict(int)
        self.db_semaphore = Semaphore(3)
        
        # Graceful shutdown
        signal.signal(signal.SIGINT, lambda s, f: setattr(self, 'running', False))
        signal.signal(signal.SIGTERM, lambda s, f: setattr(self, 'running', False))
    
    @staticmethod
    def get_candle_boundary(timestamp_ms: int) -> int:
        """Calculate exact 5-second boundary using floor division"""
        return (timestamp_ms // CANDLE_INTERVAL_MS) * CANDLE_INTERVAL_MS
    
    @staticmethod
    def trade_belongs_to_boundary(trade_timestamp_ms: int, boundary_ms: int) -> bool:
        """Check if trade belongs to specific 5s boundary [start, end)"""
        return boundary_ms <= trade_timestamp_ms < (boundary_ms + CANDLE_INTERVAL_MS)
    
    async def init_exchange(self) -> bool:
        """Initialize exchange for raw trade data"""
        try:
            exchange_class = getattr(ccxtpro, EXCHANGE)
            
            config = {
                **EXCHANGE_CREDENTIALS,
                'enableRateLimit': True,
                'options': {
                    'fetchTradesMethod': 'publicGetTrades',
                    'tradesLimit': 1000,
                }
            }
            
            self.exchange = exchange_class(config)
            await self.exchange.load_markets()
            
            logger.info(f"✅ Connected to {EXCHANGE}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Exchange initialization failed: {e}")
            return False
    
    async def websocket_handler(self, symbol: str):
        """WebSocket handler for raw trade streaming"""
        attempt = 0
        max_attempts = 10
        
        while self.running and attempt < max_attempts:
            try:
                logger.info(f"🔄 Starting WebSocket for {symbol} (attempt {attempt + 1})")
                
                while self.running:
                    trades = await asyncio.wait_for(self.exchange.watch_trades(symbol), timeout=30)
                    
                    if trades:
                        new_trades = []
                        
                        for trade in trades:
                            trade_id = str(trade['id'])
                            
                            # Duplicate detection
                            if trade_id not in self.trade_id_sets[symbol]:
                                self.trade_id_sets[symbol].add(trade_id)
                                
                                raw_trade = RawTrade(
                                    id=trade_id,
                                    timestamp_ms=int(trade['timestamp']),
                                    price=float(trade['price']),
                                    amount=float(trade['amount']),
                                    symbol=symbol,
                                    side=trade.get('side', 'unknown')
                                )
                                
                                new_trades.append(raw_trade)
                        
                        # Cleanup old trade IDs
                        if len(self.trade_id_sets[symbol]) > MAX_TRADE_IDS:
                            sorted_ids = sorted(self.trade_id_sets[symbol])
                            self.trade_id_sets[symbol] = set(sorted_ids[-MAX_TRADE_IDS//2:])
                        
                        if new_trades:
                            try:
                                await asyncio.wait_for(self.trade_queues[symbol].put(new_trades), timeout=1)
                                self.stats[f'{symbol}_trades'] += len(new_trades)
                                
                                if self.stats[f'{symbol}_trades'] % 1000 == 0:
                                    logger.debug(f"📈 {symbol}: {self.stats[f'{symbol}_trades']} trades")
                                    
                            except asyncio.TimeoutError:
                                logger.warning(f"⚠️  Trade queue full for {symbol}")
                    
                    attempt = 0
                    
            except asyncio.TimeoutError:
                logger.warning(f"⏰ WebSocket timeout for {symbol}")
                attempt += 1
                
            except Exception as e:
                logger.error(f"❌ WebSocket error for {symbol}: {e}")
                attempt += 1
                await asyncio.sleep(min(attempt * 2, 30))
        
        if attempt >= max_attempts:
            logger.error(f"💀 WebSocket for {symbol} failed after {max_attempts} attempts")
    
    async def trade_processor(self, symbol: str):
        """Process raw trades and group by time boundaries"""
        while self.running:
            try:
                trades = await asyncio.wait_for(self.trade_queues[symbol].get(), timeout=5)
                
                for trade in trades:
                    self.trade_buffers[symbol].append(trade)
                    
                    # Group by candle boundaries
                    boundary = self.get_candle_boundary(trade.timestamp_ms)
                    
                    if boundary not in self.pending_candles[symbol]:
                        self.pending_candles[symbol][boundary] = []
                    
                    self.pending_candles[symbol][boundary].append(trade)
                
                self.trade_queues[symbol].task_done()
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"❌ Trade processor error for {symbol}: {e}")
                await asyncio.sleep(1)
    
    async def candle_generator(self, symbol: str):
        """Generate 5s candles from grouped trades"""
        while self.running:
            try:
                current_time_ms = int(time.time() * 1000)
                current_boundary = self.get_candle_boundary(current_time_ms)
                
                # Process completed boundaries
                completed_boundaries = [
                    boundary for boundary in self.pending_candles[symbol].keys()
                    if boundary < current_boundary - CANDLE_INTERVAL_MS
                ]
                
                for boundary in completed_boundaries:
                    trades_in_boundary = self.pending_candles[symbol][boundary]
                    
                    if trades_in_boundary:
                        trades_in_boundary.sort(key=lambda t: t.timestamp_ms)
                        candle = self._construct_candle(boundary, trades_in_boundary, symbol)
                        
                        if candle:
                            try:
                                await asyncio.wait_for(self.candle_queues[symbol].put(candle), timeout=1)
                                self.stats[f'{symbol}_candles'] += 1
                                
                                logger.debug(f"📊 {symbol}: Candle {datetime.fromtimestamp(boundary/1000)} "
                                           f"O:{candle.open:.4f} H:{candle.high:.4f} L:{candle.low:.4f} "
                                           f"C:{candle.close:.4f} V:{candle.volume:.4f}")
                                
                            except asyncio.TimeoutError:
                                logger.warning(f"⚠️  Candle queue full for {symbol}")
                    
                    del self.pending_candles[symbol][boundary]
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ Candle generator error for {symbol}: {e}")
                await asyncio.sleep(5)
    
    def _construct_candle(self, boundary_ms: int, trades: List[RawTrade], symbol: str) -> Optional[Candle]:
        """Construct candle from trades within time boundary"""
        if not trades:
            return None
        
        # Extract price and volume data
        prices = np.array([trade.price for trade in trades], dtype=np.float64)
        volumes = np.array([trade.amount for trade in trades], dtype=np.float64)
        
        return Candle(
            timestamp_ms=boundary_ms,
            open=float(prices[0]),
            high=float(np.max(prices)),
            low=float(np.min(prices)),
            close=float(prices[-1]),
            volume=float(np.sum(volumes)),
            trade_count=len(trades),
            symbol=symbol
        )
    
    async def database_writer(self, symbol: str):
        """Write candles to database"""
        pending_candles = []
        
        while self.running:
            try:
                try:
                    candle = await asyncio.wait_for(self.candle_queues[symbol].get(), timeout=2)
                    pending_candles.append(candle)
                    self.candle_queues[symbol].task_done()
                except asyncio.TimeoutError:
                    pass
                
                # Write in batches
                if len(pending_candles) >= BATCH_SIZE or (pending_candles and time.time() % 5 < 1):
                    await self._write_candles(symbol, pending_candles)
                    pending_candles.clear()
                    
            except Exception as e:
                logger.error(f"❌ Database writer error for {symbol}: {e}")
                await asyncio.sleep(1)
        
        # Write remaining candles on shutdown
        if pending_candles:
            await self._write_candles(symbol, pending_candles)
    
    async def _write_candles(self, symbol: str, candles: List[Candle]):
        """Write candles to database"""
        if not candles:
            return
            
        async with self.db_semaphore:
            try:
                candle_data = [
                    [c.timestamp_ms, c.open, c.high, c.low, c.close, c.volume]
                    for c in candles
                ]
                
                await asyncio.get_event_loop().run_in_executor(
                    None, self.db.insert_candles, candle_data, symbol
                )
                
                self.stats[f'{symbol}_written'] += len(candles)
                
                logger.info(f"✅ {symbol}: {len(candles)} candles "
                          f"T:{self.stats[f'{symbol}_trades']} "
                          f"C:{self.stats[f'{symbol}_candles']} "
                          f"W:{self.stats[f'{symbol}_written']}")
                
            except Exception as e:
                logger.error(f"❌ Database write error for {symbol}: {e}")
                # Re-queue candles for retry
                for candle in candles:
                    try:
                        await asyncio.wait_for(self.candle_queues[symbol].put(candle), timeout=0.1)
                    except asyncio.TimeoutError:
                        break
    
    async def stats_monitor(self):
        """Monitor collection statistics"""
        while self.running:
            try:
                await asyncio.sleep(60)
                
                for symbol in SYMBOLS:
                    trades = self.stats[f'{symbol}_trades']
                    candles = self.stats[f'{symbol}_candles']
                    written = self.stats[f'{symbol}_written']
                    
                    ratio = trades / max(candles, 1)
                    
                    logger.info(f"📊 {symbol}: T:{trades} C:{candles} W:{written} "
                              f"R:{ratio:.1f} B:{len(self.trade_buffers[symbol])}")
                    
                    if candles > 10 and ratio < 5:
                        logger.warning(f"⚠️  {symbol}: Low trade/candle ratio ({ratio:.1f})")
                        
            except Exception as e:
                logger.error(f"❌ Stats monitor error: {e}")
    
    async def run(self):
        """Run the data collector"""
        try:
            if not await self.init_exchange():
                return
            
            self.running = True
            logger.info("🚀 Starting 5s Data Collector")
            logger.info(f"📈 Monitoring symbols: {SYMBOLS}")
            
            # Create tasks for all symbols
            tasks = []
            
            for symbol in SYMBOLS:
                tasks.extend([
                    asyncio.create_task(self.websocket_handler(symbol)),
                    asyncio.create_task(self.trade_processor(symbol)),
                    asyncio.create_task(self.candle_generator(symbol)),
                    asyncio.create_task(self.database_writer(symbol)),
                ])
            
            tasks.append(asyncio.create_task(self.stats_monitor()))
            
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"❌ Collector error: {e}")
        finally:
            await self.stop()
    
    async def stop(self):
        """Graceful shutdown"""
        logger.info("🛑 Shutting down collector...")
        self.running = False
        
        if self.exchange:
            await self.exchange.close()
        
        logger.info("✅ Shutdown complete")

async def main():
    """Main entry point"""
    collector = DataCollector()
    await collector.run()

if __name__ == "__main__":
    asyncio.run(main()) 
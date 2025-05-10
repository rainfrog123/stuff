#!/usr/bin/env python3
"""
Test WebSocket connection to get real-time trade data.
This script connects to Binance WebSocket API and prints the received trade data.
"""

import asyncio
import logging
import sys
import time
import pprint
import ccxt.pro as ccxtpro
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("websocket_test")

# Exchange settings (copied from config.py)
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
SYMBOL = "ETH/USDT"  # Change this to any symbol you want to test

class WebSocketTester:
    """Simple tester class to connect to exchange WebSocket and print trade data"""
    
    def __init__(self):
        self.exchange = None
        self.received_trades = 0
        self.start_time = None
        self.trade_ids = set()  # Track trade IDs to detect duplicates
    
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
    
    async def watch_trades(self):
        """Connect to WebSocket and watch trades for the specified symbol"""
        self.start_time = time.time()
        
        try:
            logger.info(f"Starting WebSocket connection for {SYMBOL}")
            
            # Watch trades for 1 minute (can be modified)
            end_time = self.start_time + 60
            
            while time.time() < end_time:
                try:
                    # This is the key method that connects to WebSocket and receives trade data
                    trades = await self.exchange.watch_trades(SYMBOL)
                    
                    # Process received trades
                    new_trades = []
                    for trade in trades:
                        if trade['id'] not in self.trade_ids:
                            self.trade_ids.add(trade['id'])
                            new_trades.append(trade)
                    
                    if new_trades:
                        self.received_trades += len(new_trades)
                        logger.info(f"Received {len(new_trades)} new trades. Total: {self.received_trades}")
                        
                        # Print the first new trade in a readable format
                        logger.info("Sample trade data:")
                        pprint.pprint(new_trades[0])
                        
                        # Print normalized timestamp to show 5s bucket
                        timestamp_ms = new_trades[0]['timestamp']
                        normalized_ts = int(timestamp_ms / 1000 // 5 * 5 * 1000)
                        logger.info(f"Trade time: {datetime.fromtimestamp(timestamp_ms/1000)}")
                        logger.info(f"5s bucket: {datetime.fromtimestamp(normalized_ts/1000)}")
                        
                except Exception as e:
                    logger.error(f"Error in WebSocket: {e}")
                    # Small pause to avoid tight loop on error
                    await asyncio.sleep(1)
            
            logger.info(f"Test completed. Received {self.received_trades} trades in {time.time() - self.start_time:.2f} seconds")
        
        finally:
            # Make sure to close the exchange connection
            if self.exchange:
                await self.exchange.close()
                logger.info("Exchange connection closed")

async def main():
    """Main entry point for the WebSocket tester"""
    tester = WebSocketTester()
    
    # Initialize exchange
    if not await tester.init_exchange():
        logger.error("Failed to initialize exchange. Exiting.")
        return
    
    # Watch trades
    await tester.watch_trades()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Exiting.")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}") 
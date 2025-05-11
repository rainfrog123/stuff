#!/usr/bin/env python3
"""
WebSocket server that monitors the 5-second candle database and broadcasts updates
"""

import asyncio
import json
import logging
import os
import sqlite3
import signal
import sys
import time
import websockets
from contextlib import contextmanager
from datetime import datetime
import pandas as pd

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Database path
CANDLES_DB_PATH = "/allah/data/candles_5s.db"
DB_POLL_INTERVAL = 1.0  # How often to check for DB changes (seconds)

# WebSocket server settings
WS_HOST = "0.0.0.0"
WS_PORT = 8765

# Track connected clients
connected_clients = set()
subscriptions = {}  # Maps symbols to sets of client websockets
last_candle_ts = {}  # Tracks the last timestamp for each symbol

@contextmanager
def get_db_connection():
    """Context manager for database connection."""
    if not os.path.exists(CANDLES_DB_PATH):
        logger.error(f"Database not found at {CANDLES_DB_PATH}")
        raise FileNotFoundError(f"Database not found at {CANDLES_DB_PATH}")
        
    conn = sqlite3.connect(CANDLES_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

async def monitor_database():
    """Monitor the database for new candles and broadcast updates."""
    while True:
        try:
            symbols_with_updates = await check_for_updates()
            for symbol in symbols_with_updates:
                await broadcast_symbol_update(symbol)
                
            # Yield control to other tasks
            await asyncio.sleep(DB_POLL_INTERVAL)
        except Exception as e:
            logger.error(f"Error in database monitor: {e}", exc_info=True)
            await asyncio.sleep(5)  # Longer delay on error

async def check_for_updates():
    """Check for new candles in the database."""
    updated_symbols = []
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get all symbols in the database
            cursor.execute("SELECT DISTINCT symbol FROM candles")
            all_symbols = [row['symbol'] for row in cursor.fetchall()]
            
            # Check each symbol for updates
            for symbol in all_symbols:
                last_ts = last_candle_ts.get(symbol, 0)
                
                # Query for newer candles
                cursor.execute(
                    "SELECT MAX(timestamp) as max_ts FROM candles WHERE symbol = ? AND timestamp > ?",
                    (symbol, last_ts)
                )
                result = cursor.fetchone()
                
                if result and result['max_ts']:
                    updated_symbols.append(symbol)
    
    except Exception as e:
        logger.error(f"Error checking for updates: {e}")
    
    return updated_symbols

async def broadcast_symbol_update(symbol):
    """Fetch and broadcast updates for a specific symbol."""
    if symbol not in subscriptions or not subscriptions[symbol]:
        return
        
    try:
        # Get the last timestamp we broadcasted
        last_ts = last_candle_ts.get(symbol, 0)
        
        # Fetch new candles
        with get_db_connection() as conn:
            query = """
            SELECT timestamp, datetime, open, high, low, close, volume 
            FROM candles 
            WHERE symbol = ? AND timestamp > ?
            ORDER BY timestamp ASC
            """
            df = pd.read_sql_query(query, conn, params=(symbol, last_ts))
            
            if not df.empty:
                # Convert DataFrame to list of dictionaries
                candles = df.to_dict('records')
                
                # Update last timestamp
                last_candle_ts[symbol] = df['timestamp'].max()
                
                # Prepare message
                message = json.dumps({
                    'type': 'candle_update',
                    'symbol': symbol,
                    'candles': candles
                })
                
                # Broadcast to subscribed clients
                await broadcast_to_subscribers(symbol, message)
                
                logger.info(f"Broadcast {len(candles)} new candles for {symbol}")
    
    except Exception as e:
        logger.error(f"Error broadcasting update for {symbol}: {e}")

async def broadcast_to_subscribers(symbol, message):
    """Send a message to all clients subscribed to a symbol."""
    if symbol not in subscriptions:
        return
        
    disconnected = set()
    
    for websocket in subscriptions[symbol]:
        try:
            await websocket.send(message)
        except websockets.exceptions.ConnectionClosed:
            disconnected.add(websocket)
        except Exception as e:
            logger.error(f"Error sending to client: {e}")
            disconnected.add(websocket)
    
    # Remove disconnected clients
    subscriptions[symbol] = subscriptions[symbol] - disconnected
    for ws in disconnected:
        cleanup_client(ws)

def cleanup_client(websocket):
    """Remove a client from all subscriptions."""
    if websocket in connected_clients:
        connected_clients.remove(websocket)
    
    # Remove from all subscriptions
    for symbol in subscriptions:
        if websocket in subscriptions[symbol]:
            subscriptions[symbol].remove(websocket)

async def handle_client(websocket, path):
    """Handle a client connection."""
    # Register the new client
    connected_clients.add(websocket)
    
    logger.info(f"New client connected: {websocket.remote_address}")
    
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                action = data.get('action')
                symbol = data.get('symbol')
                
                if action == 'subscribe' and symbol:
                    # Create a set for this symbol if it doesn't exist
                    if symbol not in subscriptions:
                        subscriptions[symbol] = set()
                    
                    # Add client to subscribers for this symbol
                    subscriptions[symbol].add(websocket)
                    logger.info(f"Client subscribed to {symbol}")
                    
                    # Send immediate update with current data
                    await broadcast_symbol_update(symbol)
                
                elif action == 'unsubscribe' and symbol:
                    # Remove client from subscribers for this symbol
                    if symbol in subscriptions and websocket in subscriptions[symbol]:
                        subscriptions[symbol].remove(websocket)
                        logger.info(f"Client unsubscribed from {symbol}")
            
            except json.JSONDecodeError:
                logger.warning(f"Received invalid JSON: {message}")
            except Exception as e:
                logger.error(f"Error processing message: {e}")
    
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        # Clean up on disconnect
        cleanup_client(websocket)
        logger.info(f"Client disconnected: {websocket.remote_address}")

async def main():
    """Main entry point for the WebSocket server."""
    # Set up signal handlers
    loop = asyncio.get_running_loop()
    stop = loop.create_future()
    
    # Handle termination signals
    for signal_name in ('SIGINT', 'SIGTERM'):
        loop.add_signal_handler(
            getattr(signal, signal_name),
            stop.set_result,
            None
        )
    
    # Start database monitor
    monitor_task = asyncio.create_task(monitor_database())
    
    # Start WebSocket server
    async with websockets.serve(handle_client, WS_HOST, WS_PORT):
        logger.info(f"WebSocket server started on ws://{WS_HOST}:{WS_PORT}")
        
        # Run until stopped
        await stop
        logger.info("Stopping server...")
        
        # Cancel the monitor task
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user") 
#!/usr/bin/env python3
"""
Simple test script to verify the Binance aggTrade WebSocket functionality.
"""

import asyncio
import json
import sys
import websockets
from datetime import datetime
import pandas as pd

# Binance WebSocket URL
BINANCE_WS_URL = "wss://stream.binance.com:9443/ws"

async def test_aggtrade(symbol="ethusdt", duration_sec=30):
    """Connect to Binance aggTrade WebSocket and display received data."""
    ws_url = f"{BINANCE_WS_URL}/{symbol}@aggTrade"
    trades = []
    
    print(f"Connecting to {ws_url}")
    print(f"Will collect data for {duration_sec} seconds...")
    
    try:
        async with websockets.connect(ws_url) as websocket:
            # Set timeout for the entire collection process
            end_time = asyncio.get_event_loop().time() + duration_sec
            
            while asyncio.get_event_loop().time() < end_time:
                try:
                    # Set a timeout for each message reception
                    message = await asyncio.wait_for(
                        websocket.recv(), 
                        timeout=1.0
                    )
                    
                    # Parse the message
                    data = json.loads(message)
                    
                    # Extract key information
                    trade = {
                        'id': str(data['a']),               # Aggregate trade ID
                        'timestamp': data['T'],             # Trade time
                        'datetime': datetime.fromtimestamp(data['T'] / 1000).isoformat(),
                        'price': float(data['p']),
                        'amount': float(data['q']),
                        'is_buyer_maker': data['m']         # Is the buyer the market maker?
                    }
                    
                    trades.append(trade)
                    
                    # Print progress every 5 trades
                    if len(trades) % 5 == 0:
                        print(f"Received {len(trades)} trades so far...")
                    
                except asyncio.TimeoutError:
                    # No message received within timeout
                    continue
    
    except Exception as e:
        print(f"Error: {e}")
        return False
    
    # Analysis of collected data
    if not trades:
        print("No trades received!")
        return False
    
    print(f"\nCollection complete. Received {len(trades)} aggregated trades.")
    
    # Convert to DataFrame for analysis
    df = pd.DataFrame(trades)
    
    # Print data summary
    print("\nData Summary:")
    print(f"Time range: {df['datetime'].min()} to {df['datetime'].max()}")
    print(f"Price range: {df['price'].min()} to {df['price'].max()}")
    print(f"Total volume: {df['amount'].sum()}")
    print(f"Average trade size: {df['amount'].mean()}")
    
    # Print sample trades
    print("\nSample of received trades:")
    if len(df) > 5:
        print(df.head(5)[['datetime', 'price', 'amount', 'is_buyer_maker']])
    else:
        print(df[['datetime', 'price', 'amount', 'is_buyer_maker']])
    
    # Calculate 5-second OHLCV
    print("\nGenerating 5-second candles from the trades:")
    df['timestamp_sec'] = (df['timestamp'] // 5000) * 5000
    ohlcv = []
    
    for ts, group in df.groupby('timestamp_sec'):
        candle = {
            'timestamp': ts,
            'datetime': datetime.fromtimestamp(ts / 1000),
            'open': group.iloc[0]['price'],
            'high': group['price'].max(),
            'low': group['price'].min(),
            'close': group.iloc[-1]['price'],
            'volume': group['amount'].sum()
        }
        ohlcv.append(candle)
    
    if ohlcv:
        ohlcv_df = pd.DataFrame(ohlcv).sort_values('timestamp')
        print(ohlcv_df[['datetime', 'open', 'high', 'low', 'close', 'volume']].head(3))
    else:
        print("Not enough data to generate candles")
    
    return True

if __name__ == "__main__":
    # Get symbol from command line args if provided
    symbol = sys.argv[1].lower() if len(sys.argv) > 1 else "ethusdt"
    
    # Get duration from command line args if provided
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    
    print(f"Testing aggTrade WebSocket for {symbol} for {duration} seconds")
    asyncio.run(test_aggtrade(symbol, duration)) 
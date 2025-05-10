#!/usr/bin/env python3
"""
Simple test script to verify the Binance Futures aggTrade WebSocket functionality.
Specifically for perpetual futures contracts (USDⓈ-M).
"""

import asyncio
import json
import sys
import websockets
from datetime import datetime
import pandas as pd

# Binance Futures WebSocket URL (USDⓈ-M)
BINANCE_FUTURES_WS_URL = "wss://fstream.binance.com/ws"

async def test_futures_aggtrade(symbol="ethusdt", duration_sec=60):
    """Connect to Binance Futures aggTrade WebSocket and display received data."""
    ws_url = f"{BINANCE_FUTURES_WS_URL}/{symbol}@aggTrade"
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
                    
                    # Print progress every 10 trades
                    if len(trades) % 10 == 0:
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
    
    print(f"\nCollection complete. Received {len(trades)} futures aggregated trades.")
    
    # Convert to DataFrame for analysis
    df = pd.DataFrame(trades)
    
    # Print data summary
    print("\nData Summary:")
    print(f"Time range: {df['datetime'].min()} to {df['datetime'].max()}")
    print(f"Price range: {df['price'].min()} to {df['price'].max()}")
    print(f"Total volume: {df['amount'].sum()} contracts")
    print(f"Average trade size: {df['amount'].mean()} contracts")
    
    # Print sample trades
    print("\nSample of received trades:")
    if len(df) > 5:
        print(df.head(5)[['datetime', 'price', 'amount', 'is_buyer_maker']])
    else:
        print(df[['datetime', 'price', 'amount', 'is_buyer_maker']])
    
    # Calculate 5-second OHLCV
    print("\nGenerating 5-second candles from the futures trades:")
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
        print(f"Generated {len(ohlcv_df)} candles. Showing up to 30:")
        pd.set_option('display.max_rows', 30)
        print(ohlcv_df[['datetime', 'open', 'high', 'low', 'close', 'volume']])
    else:
        print("Not enough data to generate candles")
    
    # Calculate TradingView-matched candles with 2800ms offset
    print("\nGenerating TradingView-matched candles (with 2800ms offset):")
    df['tv_timestamp'] = ((df['timestamp'] + 2800) // 5000) * 5000
    tv_ohlcv = []
    
    for ts, group in df.groupby('tv_timestamp'):
        candle = {
            'timestamp': ts,
            'datetime': datetime.fromtimestamp(ts / 1000),
            'open': group.iloc[0]['price'],
            'high': group['price'].max(),
            'low': group['price'].min(),
            'close': group.iloc[-1]['price'],
            'volume': group['amount'].sum()
        }
        tv_ohlcv.append(candle)
    
    if tv_ohlcv:
        tv_ohlcv_df = pd.DataFrame(tv_ohlcv).sort_values('timestamp')
        print(f"Generated {len(tv_ohlcv_df)} TV-matched candles. Showing up to 30:")
        pd.set_option('display.max_rows', 30)
        print(tv_ohlcv_df[['datetime', 'open', 'high', 'low', 'close', 'volume']])
    else:
        print("Not enough data to generate TradingView-matched candles")
    
    return True

if __name__ == "__main__":
    # Get symbol from command line args if provided, default to ETHUSDT
    symbol = sys.argv[1].lower() if len(sys.argv) > 1 else "ethusdt"
    
    # Get duration from command line args if provided
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    
    print(f"Testing Futures aggTrade WebSocket for {symbol} for {duration} seconds")
    asyncio.run(test_futures_aggtrade(symbol, duration)) 
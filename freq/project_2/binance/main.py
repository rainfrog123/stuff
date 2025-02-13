import ccxt
from datetime import datetime, timedelta
import pandas as pd
import time
import os

# API credentials
API_KEY = 'ofQzX3gGAKS777NyYIovAy1XyqLzGC2UJPMh9jqIYEfieFRy3DCkZJl15VYA2zXo'
API_SECRET = 'QVJpTFgHIEv74LmCT5clX8o1zAFEEqJqKpg2ePklObM1Ybv9iKNe8jvM7MRjoz07'

OUTPUT_DIR = "/allah/data/trades"

def get_all_futures_trades(symbol, batch_size=1000):
    """
    Fetch all available futures trading data from Binance using CCXT
    
    Args:
        symbol (str): Trading pair symbol (e.g., 'ETH/USDT')
        batch_size (int): Number of records to fetch per request (max 1000)
    """
    # Validate batch_size
    if batch_size > 1000:
        print("Warning: batch_size cannot exceed 1000. Setting to 1000.")
        batch_size = 1000
        
    # Initialize CCXT Binance Futures client
    exchange = ccxt.binanceusdm({
        'apiKey': API_KEY,
        'secret': API_SECRET,
        'enableRateLimit': True,  # enables built-in rate limiter
    })
    
    all_trades = []
    since = None  # Starting timestamp
    batch_num = 1
    
    while True:
        try:
            # Fetch trades with pagination
            trades = exchange.fetch_trades(
                symbol=symbol,
                limit=batch_size,
                since=since,
                params={'type': 'future'}
            )
            
            if not trades:
                print("No more trades to fetch.")
                break
                
            all_trades.extend(trades)
            print(f"Batch {batch_num}: Fetched {len(trades)} trades. Total trades: {len(all_trades)}")
            
            # Update timestamp for pagination
            since = trades[-1]['timestamp']
            batch_num += 1
            
            # Save intermediate results every 100 batches
            if batch_num % 100 == 0:
                save_trades_to_parquet(all_trades, symbol, batch_num)
                all_trades = []  # Clear memory
            
            # Small delay to be safe, although CCXT handles rate limiting
            time.sleep(0.1)
            
        except Exception as e:
            print(f"Error fetching trades: {e}")
            # Save what we have so far if there's an error
            if all_trades:
                save_trades_to_parquet(all_trades, symbol, batch_num)
            break
    
    # Save any remaining trades
    if all_trades:
        save_trades_to_parquet(all_trades, symbol, batch_num)

def save_trades_to_parquet(trades, symbol, batch_num):
    """
    Save trades to Parquet file with proper formatting and compression
    """
    if not trades:
        return
        
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Convert to DataFrame
    df = pd.DataFrame([{
        'id': trade['id'],
        'timestamp': pd.to_datetime(trade['timestamp'], unit='ms'),
        'price': float(trade['price']),
        'amount': float(trade['amount']),
        'side': trade['side'],
        'cost': float(trade['cost']),
    } for trade in trades])
    
    # Save to Parquet with compression
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = os.path.join(OUTPUT_DIR, f"binance_futures_{symbol.replace('/', '').lower()}_batch_{batch_num}_{timestamp}.parquet")
    df.to_parquet(filename, compression='snappy', index=False)
    print(f"Saved batch {batch_num} to {filename}")

if __name__ == "__main__":
    symbol = "ETH/USDT"  # CCXT uses / format for symbol pairs
    print(f"Downloading all available futures trades for {symbol}...")
    print(f"Data will be saved to: {OUTPUT_DIR}")
    
    get_all_futures_trades(symbol)
    print("Download completed!")

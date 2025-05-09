import ccxt
import time
import datetime
import os

# API credentials from your config
API_KEY = 'ofQzX3gGAKS777NyYIovAy1XyqLzGC2UJPMh9jqIYEfieFRy3DCkZJl15VYA2zXo'
API_SECRET = 'QVJpTFgHIEv74LmCT5clX8o1zAFEEqJqKpg2ePklObM1Ybv9iKNe8jvM7MRjoz07'

# Exchange configuration
exchange_id = 'binance'
exchange_class = getattr(ccxt, exchange_id)
exchange = exchange_class({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'options': {
        'defaultType': 'future',  # For USDT margined futures, use 'future'. For COIN margined, use 'delivery'
    },
})

# Test parameters
# symbol = 'ETH/USDT:USDT' # As in Freqtrade pairlist
symbol_ccxt = 'ETH/USDT' # CCXT typically uses this format for futures fetch_trades
limit = 1000 # Max trades per call for Binance

# Calculate 'since' timestamp (e.g., 60 minutes ago)
# startup_candle_count_equivalent = 170  # From strategy
# five_sec_candles_in_one_hour = (60 * 60) // 5 # 720 candles of 5s in an hour
# hist_duration_seconds = startup_candle_count_equivalent * 5 # 170 * 5 = 850 seconds
# buffer_seconds = max(hist_duration_seconds * 0.5 + 600, 900) # Approx 30 mins of total lookback

minutes_ago = 60 # Let's try to fetch trades from the last 60 minutes
now = exchange.milliseconds()
since_timestamp = now - (minutes_ago * 60 * 1000)

print(f"Attempting to fetch trades for {symbol_ccxt} on {exchange_id} futures.")
print(f"Current time: {datetime.datetime.fromtimestamp(now/1000)}")
print(f"Fetching since: {datetime.datetime.fromtimestamp(since_timestamp/1000)} (approx {minutes_ago} minutes ago)")
print(f"Using limit: {limit}")

try:
    # Load markets to ensure symbol is recognized and to get correct ID if needed
    # markets = exchange.load_markets()
    # market = exchange.market(symbol_ccxt) # Throws if symbol is not found
    # print(f"Market details for {symbol_ccxt}: {market}")

    trades = exchange.fetch_trades(symbol_ccxt, since=since_timestamp, limit=limit)
    
    if trades:
        print(f"Successfully fetched {len(trades)} trades.")
        print("First 5 trades:")
        for i, trade in enumerate(trades[:5]):
            print(f"  {i+1}: {trade}")
        print("Last 5 trades:")
        for i, trade in enumerate(trades[-5:]):
            print(f"  {len(trades)-5+i+1}: {trade}")
            
        # Check timestamp range
        oldest_ts = trades[0]['timestamp']
        newest_ts = trades[-1]['timestamp']
        print(f"Oldest trade timestamp: {datetime.datetime.fromtimestamp(oldest_ts/1000)} ({oldest_ts})")
        print(f"Newest trade timestamp: {datetime.datetime.fromtimestamp(newest_ts/1000)} ({newest_ts})")
    else:
        print("No trades fetched. The list is empty.")

except ccxt.NetworkError as e:
    print(f"CCXT Network Error: {e}")
except ccxt.ExchangeError as e:
    print(f"CCXT Exchange Error: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")

print("Script finished.") 
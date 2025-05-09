#!/usr/bin/env python3
"""
Fetches historical trades within a recent window from Binance futures using pagination,
identifies the most recent trade, and calculates the time difference to now.
"""
import ccxt
import datetime
import pandas as pd
import os
import time

# --- Configuration ---
EXCHANGE_ID = 'binance'
EXCHANGE_PARAMS = {
    'options': {
        'defaultType': 'swap',  # For USDT-M futures like ETH/USDT
    },
    # API keys are generally not needed for public fetch_trades
    # 'apiKey': os.getenv('BINANCE_API_KEY_FUTURES'),
    # 'secret': os.getenv('BINANCE_API_SECRET_FUTURES'),
}
PAIR_SYMBOL_CCXT = 'ETH/USDT'

# Configuration for paginated fetch
LOOKBACK_MINUTES = 5      # How many minutes of recent history to check
MAX_PAGES_TO_FETCH = 5    # Max number of pages to fetch for the lookback window
PAGE_FETCH_LIMIT = 1000   # Number of trades per page (Binance max is 1000 for trades)
INTER_PAGE_DELAY_S = 0.2  # Small delay to be polite to the API

def main():
    print(f"--- CCXT Paginated Historical Trade Fetcher for {EXCHANGE_ID.capitalize()} Futures ---")
    print(f"Fetching trades for {PAIR_SYMBOL_CCXT} from the last {LOOKBACK_MINUTES} minutes.")
    print(f"Max pages: {MAX_PAGES_TO_FETCH}, Trades per page: {PAGE_FETCH_LIMIT}")

    # --- Initialize Exchange ---
    try:
        exchange = getattr(ccxt, EXCHANGE_ID)(EXCHANGE_PARAMS)
        exchange.load_markets()
        print(f"Successfully connected to {EXCHANGE_ID} and loaded markets.")
        if EXCHANGE_PARAMS.get('apiKey'):
            print("Using API key provided in configuration.")
        else:
            print("No API key configured; proceeding with unauthenticated request.")

    except Exception as e:
        print(f"Error initializing exchange: {e}")
        return

    # --- Paginated Fetching Logic ---
    all_fetched_trades = []
    current_unix_time_sec = time.time()
    # Calculate 'since' timestamp for the start of our lookback window
    loop_since_ms = int((current_unix_time_sec - (LOOKBACK_MINUTES * 60)) * 1000)
    
    print(f"Starting fetch from: {pd.to_datetime(loop_since_ms, unit='ms', utc=True).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} UTC")

    for page_num in range(MAX_PAGES_TO_FETCH):
        print(f"Fetching page {page_num + 1}/{MAX_PAGES_TO_FETCH}... Since: {loop_since_ms} ({pd.to_datetime(loop_since_ms, unit='ms', utc=True).strftime('%H:%M:%S.%f')[:-3]} UTC)")
        try:
            current_trades_batch = exchange.fetch_trades(
                PAIR_SYMBOL_CCXT, 
                since=loop_since_ms, 
                limit=PAGE_FETCH_LIMIT
            )

            if not current_trades_batch:
                print(f"Page {page_num + 1}: No more trades found in this batch.")
                break 
            
            all_fetched_trades.extend(current_trades_batch)
            # Update 'since' for the next iteration to be AFTER the last trade fetched in this batch
            newest_ts_in_batch = current_trades_batch[-1]['timestamp']
            loop_since_ms = newest_ts_in_batch + 1

            print(f"Page {page_num + 1}: Fetched {len(current_trades_batch)} trades. Newest in batch: {pd.to_datetime(newest_ts_in_batch, unit='ms', utc=True).strftime('%H:%M:%S.%f')[:-3]} UTC")

            if len(current_trades_batch) < PAGE_FETCH_LIMIT:
                print(f"Page {page_num + 1}: Fetched less than limit ({len(current_trades_batch)} < {PAGE_FETCH_LIMIT}), assuming end of available data for the window.")
                break
            
            if page_num < MAX_PAGES_TO_FETCH - 1: # No need to sleep after the last page
                 time.sleep(INTER_PAGE_DELAY_S)

        except ccxt.RateLimitExceeded as e:
            print(f"Rate limit exceeded: {e}. Try increasing INTER_PAGE_DELAY_S or reducing page count/frequency.")
            break # Stop fetching on rate limit
        except ccxt.NetworkError as e:
            print(f"Network error on page {page_num + 1}: {e}")
            # Optionally, you could implement retries here
            break 
        except ccxt.ExchangeError as e:
            print(f"Exchange error on page {page_num + 1}: {e}")
            break
        except Exception as e:
            print(f"An unexpected error occurred on page {page_num + 1}: {e}")
            break
    
    if not all_fetched_trades:
        print("\nNo trades were fetched in total.")
        return

    print(f"\nTotal of {len(all_fetched_trades)} trades fetched across all pages.")

    # Identify the most recent trade from the entire collection
    most_recent_trade = max(all_fetched_trades, key=lambda x: x['timestamp'])
    
    trade_id = most_recent_trade.get('id', 'N/A')
    trade_price = most_recent_trade.get('price', 'N/A')
    trade_amount = most_recent_trade.get('amount', 'N/A')
    trade_side = most_recent_trade.get('side', 'N/A')
    trade_timestamp_ms = most_recent_trade.get('timestamp')

    if trade_timestamp_ms is None:
        print("Could not retrieve timestamp from the overall most recent trade.")
        return
        
    trade_datetime_utc = pd.to_datetime(trade_timestamp_ms, unit='ms', utc=True)
    current_datetime_utc = datetime.datetime.now(datetime.timezone.utc)
    time_difference = current_datetime_utc - trade_datetime_utc

    print(f"\n--- Overall Most Recent Trade Details from Paginated Fetch ({PAIR_SYMBOL_CCXT}) ---")
    print(f"  Looked back:    {LOOKBACK_MINUTES} minutes")
    print(f"  Trade ID:       {trade_id}")
    print(f"  Timestamp (UTC):{trade_datetime_utc.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
    print(f"  Milliseconds:   {trade_timestamp_ms}")
    print(f"  Price:          {trade_price}")
    print(f"  Amount:         {trade_amount}")
    print(f"  Side:           {trade_side}")
    print(f"---------------------------------------------------------------------")
    
    print(f"\nCurrent UTC time:           {current_datetime_utc.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
    print(f"Time difference from trade: {time_difference}")
    print(f"Time difference (seconds):  {time_difference.total_seconds():.3f} s")

if __name__ == '__main__':
    main() 
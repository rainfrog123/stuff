#!/usr/bin/env python3
import pandas as pd
import numpy as np
import glob
import os
import pytz
from datetime import datetime
from tqdm import tqdm

# Define paths
TRADES_DIR = "/allah/data/trades/eth_usdt_daily_trades"
OUTPUT_FEATHER = "/allah/freqtrade/user_data/data/binance/futures/ETH_USDT_USDT-5s-futures.feather"

def load_existing_feather():
    """Load existing feather file if it exists"""
    if os.path.exists(OUTPUT_FEATHER):
        print(f"Loading existing feather file: {OUTPUT_FEATHER}")
        try:
            df = pd.read_feather(OUTPUT_FEATHER)
            print(f"Loaded feather with shape: {df.shape}")
            # Get the latest timestamp from the feather file
            latest_date = df['date'].max()
            print(f"Latest date in feather: {latest_date}")
            return df, latest_date
        except Exception as e:
            print(f"Error loading feather file: {e}")
            return None, None
    else:
        print(f"Feather file does not exist: {OUTPUT_FEATHER}")
        return None, None

def get_parquet_files():
    """Get all parquet files in the trades directory"""
    files = glob.glob(os.path.join(TRADES_DIR, "ETHUSDT-trades-*.parquet"))
    files.sort()  # Sort files by date
    return files

def process_trades_to_ohlcv(df, timeframe='5s'):
    """Process trade data to OHLCV format with 5-second intervals"""
    print(f"Converting trade data to OHLCV with {timeframe} timeframe")
    
    # Convert timestamp to datetime and set timezone to UTC
    if 'datetime' not in df.columns and 'time' in df.columns:
        df['datetime'] = pd.to_datetime(df['time'], unit='ms')
    
    # Set datetime as index for resampling
    df = df.set_index('datetime')
    
    # Resample to 5-second intervals and create OHLCV data
    ohlcv = df['price'].resample(timeframe).agg(['first', 'max', 'min', 'last'])
    ohlcv.columns = ['open', 'high', 'low', 'close']
    
    # Calculate volume (sum of quantities)
    volume = df['qty'].resample(timeframe).sum()
    ohlcv['volume'] = volume
    
    # Reset index to get datetime as a column
    ohlcv.reset_index(inplace=True)
    ohlcv.rename(columns={'datetime': 'date'}, inplace=True)
    
    # Ensure date is timezone aware (UTC)
    ohlcv['date'] = ohlcv['date'].dt.tz_localize('UTC')
    
    return ohlcv

def main():
    """Main function to convert parquet files to feather"""
    print("Starting conversion from parquet to feather...")
    
    # Load existing feather file
    existing_df, latest_date = load_existing_feather()
    
    # Get parquet files
    parquet_files = get_parquet_files()
    print(f"Found {len(parquet_files)} parquet files")
    
    if not parquet_files:
        print("No parquet files found. Exiting.")
        return
    
    # List of new dataframes to be added
    new_dfs = []
    
    for file_path in tqdm(parquet_files, desc="Processing files"):
        # Extract date from filename (format: ETHUSDT-trades-YYYY-MM-DD.parquet)
        file_name = os.path.basename(file_path)
        try:
            date_str = file_name.split('-trades-')[1].split('.')[0]
            file_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=pytz.UTC)
            
            # Skip files with dates already in the feather file
            if latest_date is not None and file_date.date() < latest_date.date():
                print(f"Skipping {file_name} - data already in feather file")
                continue
                
            # Load parquet file
            trades_df = pd.read_parquet(file_path)
            
            # Add datetime column
            trades_df['datetime'] = pd.to_datetime(trades_df['time'], unit='ms')
            
            # Process to OHLCV
            ohlcv_df = process_trades_to_ohlcv(trades_df)
            
            new_dfs.append(ohlcv_df)
            print(f"Processed {file_name}: {len(ohlcv_df)} rows")
            
        except Exception as e:
            print(f"Error processing {file_name}: {e}")
            continue
    
    if not new_dfs:
        print("No new data to add. Exiting.")
        return
    
    # Concatenate all new data
    combined_df = pd.concat(new_dfs, ignore_index=True)
    print(f"Combined new data: {len(combined_df)} rows")
    
    # If existing data, append new data
    if existing_df is not None:
        # Make sure we don't have duplicate timestamps
        # Use pandas date comparison to avoid timezone issues
        combined_df = combined_df[combined_df['date'].dt.floor('D') >= latest_date.floor('D')]
        
        # Combine with existing data
        final_df = pd.concat([existing_df, combined_df], ignore_index=True)
        
        # Sort by date and drop duplicates
        final_df = final_df.sort_values('date').drop_duplicates(subset=['date'], keep='last')
        
        print(f"Final combined data: {len(final_df)} rows")
    else:
        final_df = combined_df
    
    # Save to feather
    print(f"Saving to feather: {OUTPUT_FEATHER}")
    final_df.reset_index(drop=True).to_feather(OUTPUT_FEATHER)
    print("Conversion complete!")
    
    # Display summary
    print("\nSummary:")
    print(f"Feather file: {OUTPUT_FEATHER}")
    print(f"Total rows: {len(final_df)}")
    print(f"Date range: {final_df['date'].min()} to {final_df['date'].max()}")
    print(f"Columns: {final_df.columns.tolist()}")

if __name__ == "__main__":
    main() 
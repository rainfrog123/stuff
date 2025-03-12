#!/usr/bin/env python
import pandas as pd
import os
import glob
from datetime import datetime
import argparse
from tqdm import tqdm
import sys

# Path to the trades directory
TRADES_DIR = "/allah/data/trades/eth_usdt_monthly_trades"

def parse_date(date_str):
    """
    Parse date string in format YYYY-MM or YYYY-MM-DD
    Returns a tuple of (year, month)
    """
    try:
        if len(date_str) == 7:  # YYYY-MM format
            dt = datetime.strptime(date_str, "%Y-%m")
            return dt.year, dt.month
        elif len(date_str) == 10:  # YYYY-MM-DD format
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.year, dt.month
        else:
            raise ValueError("Invalid date format")
    except ValueError as e:
        print(f"Error parsing date: {e}")
        sys.exit(1)

def get_parquet_files(start_date, end_date=None):
    """
    Get list of Parquet files between start_date and end_date (inclusive)
    If end_date is None, only get files for start_date
    
    Parameters:
    - start_date: string in format 'YYYY-MM' or 'YYYY-MM-DD'
    - end_date: string in format 'YYYY-MM' or 'YYYY-MM-DD' (optional)
    
    Returns:
    - List of file paths
    """
    start_year, start_month = parse_date(start_date)
    
    if end_date:
        end_year, end_month = parse_date(end_date)
    else:
        # If no end date provided, use the same as start date
        end_year, end_month = start_year, start_month
    
    # Validate dates
    if (end_year < start_year) or (end_year == start_year and end_month < start_month):
        print("Error: End date must be after or equal to start date")
        sys.exit(1)
    
    # Get all Parquet files
    all_files = glob.glob(os.path.join(TRADES_DIR, "*.parquet"))
    
    # Filter files based on date range
    filtered_files = []
    for file_path in all_files:
        file_name = os.path.basename(file_path)
        # Extract date from filename (format: ETHUSDT-trades-YYYY-MM.parquet)
        try:
            date_part = file_name.split('-trades-')[1].split('.')[0]
            file_year, file_month = map(int, date_part.split('-'))
            
            # Check if file is within date range
            if (file_year > start_year or (file_year == start_year and file_month >= start_month)) and \
               (file_year < end_year or (file_year == end_year and file_month <= end_month)):
                filtered_files.append(file_path)
        except (IndexError, ValueError):
            # Skip files that don't match the expected format
            continue
    
    # Sort files by date
    filtered_files.sort()
    
    return filtered_files

def load_parquet_files(file_paths, columns=None, sample_rate=None):
    """
    Load and concatenate Parquet files
    
    Parameters:
    - file_paths: List of file paths to load
    - columns: List of columns to load (optional)
    - sample_rate: Float between 0 and 1 for random sampling (optional)
    
    Returns:
    - Concatenated DataFrame
    """
    if not file_paths:
        print("No files found for the specified date range")
        return None
    
    dfs = []
    total_size = 0
    
    print(f"Loading {len(file_paths)} files...")
    for file_path in tqdm(file_paths):
        try:
            # Load with specified columns if provided
            if columns:
                df = pd.read_parquet(file_path, columns=columns, engine='pyarrow')
            else:
                df = pd.read_parquet(file_path, engine='pyarrow')
            
            # Apply sampling if specified
            if sample_rate and 0 < sample_rate < 1:
                df = df.sample(frac=sample_rate, random_state=42)
            
            dfs.append(df)
            total_size += len(df)
            
            # Print progress
            file_name = os.path.basename(file_path)
            print(f"Loaded {file_name}: {len(df):,} rows")
            
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
    
    if not dfs:
        return None
    
    # Concatenate all dataframes
    print(f"Concatenating {len(dfs)} dataframes with total {total_size:,} rows...")
    result = pd.concat(dfs, ignore_index=True)
    
    # Convert timestamp to datetime
    if 'time' in result.columns:
        result['datetime'] = pd.to_datetime(result['time'], unit='ms')
    
    return result

def main():
    parser = argparse.ArgumentParser(description='Aggregate Binance trade data from Parquet files')
    parser.add_argument('start_date', type=str, help='Start date in format YYYY-MM or YYYY-MM-DD')
    parser.add_argument('--end_date', type=str, help='End date in format YYYY-MM or YYYY-MM-DD (optional)')
    parser.add_argument('--columns', type=str, nargs='+', help='Columns to load (optional)')
    parser.add_argument('--sample_rate', type=float, help='Sample rate between 0 and 1 (optional)')
    parser.add_argument('--output', type=str, help='Output file path (optional)')
    
    args = parser.parse_args()
    
    # Get files for the specified date range
    files = get_parquet_files(args.start_date, args.end_date)
    
    if not files:
        print(f"No files found for the specified date range: {args.start_date} to {args.end_date or args.start_date}")
        return
    
    print(f"Found {len(files)} files for the specified date range")
    for file in files:
        print(f"  - {os.path.basename(file)}")
    
    # Load data
    df = load_parquet_files(files, args.columns, args.sample_rate)
    
    if df is not None:
        print(f"\nLoaded DataFrame with {len(df):,} rows and {len(df.columns)} columns")
        print("\nDataFrame info:")
        print(df.info())
        print("\nDataFrame head:")
        print(df.head())
        
        # Save to file if output path is specified
        if args.output:
            file_ext = os.path.splitext(args.output)[1].lower()
            if file_ext == '.csv':
                df.to_csv(args.output, index=False)
                print(f"Saved to CSV: {args.output}")
            elif file_ext == '.parquet':
                df.to_parquet(args.output, index=False, engine='pyarrow')
                print(f"Saved to Parquet: {args.output}")
            else:
                print(f"Unsupported output format: {file_ext}")
        
        return df
    
    return None

if __name__ == "__main__":
    main() 
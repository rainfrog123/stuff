#!/usr/bin/env python
"""
Command-line script to aggregate Binance trade data
"""
import argparse
import sys
from .trade_aggregator import TradeAggregator

def main():
    parser = argparse.ArgumentParser(description='Aggregate Binance trade data from Parquet files')
    parser.add_argument('start_date', type=str, help='Start date in format YYYY-MM or YYYY-MM-DD')
    parser.add_argument('--end_date', type=str, help='End date in format YYYY-MM or YYYY-MM-DD (optional)')
    parser.add_argument('--columns', type=str, nargs='+', help='Columns to load (optional)')
    parser.add_argument('--sample_rate', type=float, help='Sample rate between 0 and 1 (optional)')
    parser.add_argument('--output', type=str, help='Output file path (optional)')
    parser.add_argument('--trades_dir', type=str, help='Path to the trades directory (optional)')
    
    args = parser.parse_args()
    
    # Create an instance of the TradeAggregator
    if args.trades_dir:
        aggregator = TradeAggregator(trades_dir=args.trades_dir)
    else:
        aggregator = TradeAggregator()
    
    # Get files for the specified date range
    try:
        files = aggregator.get_parquet_files(args.start_date, args.end_date)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    if not files:
        print(f"No files found for the specified date range: {args.start_date} to {args.end_date or args.start_date}")
        return
    
    print(f"Found {len(files)} files for the specified date range")
    for file in files:
        print(f"  - {file}")
    
    # Load data
    df = aggregator.load_parquet_files(files, args.columns, args.sample_rate)
    
    if df is not None:
        print(f"\nLoaded DataFrame with {len(df):,} rows and {len(df.columns)} columns")
        print("\nDataFrame info:")
        print(df.info())
        print("\nDataFrame head:")
        print(df.head())
        
        # Save to file if output path is specified
        if args.output:
            import os
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
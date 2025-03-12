#!/usr/bin/env python
"""
main.py - Load Binance trade data for any time period, resample to 5-second intervals, and print the dataframe

This script loads Binance trade data, resamples it to 5-second intervals, and generates OHLCV data.
It saves the resampled data to a CSV file and creates a plot of the first 100 data points.

Configuration:
    - Set the parameters directly in the main() function:
        - start_date: Start date in format YYYY-MM or YYYY-MM-DD
        - end_date: End date in format YYYY-MM or YYYY-MM-DD (optional)
        - sample_rate: Float between 0 and 1 for random sampling
        - columns: List of columns to load (optional)
"""

import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# Add the parent directory to the Python path to import the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the TradeAggregator class
try:
    from binance_trade_aggregator import TradeAggregator
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../binance_trade_aggregator/src')))
    from trade_aggregator import TradeAggregator

def print_dataframe_info(df):
    """
    Print detailed information about the dataframe
    """
    print("\n" + "="*80)
    print(f"DataFrame Information:")
    print(f"Shape: {df.shape} (rows, columns)")
    print(f"Memory usage: {df.memory_usage(deep=True).sum() / (1024 * 1024):.2f} MB")
    
    if 'datetime' in df.columns:
        print(f"Date range: {df['datetime'].min()} to {df['datetime'].max()}")
    
    print("\nColumn names:")
    for col in df.columns:
        print(f"  - {col}")
    
    print("\nData types:")
    for col, dtype in df.dtypes.items():
        print(f"  - {col}: {dtype}")
    
    print("\nBasic statistics:")
    numeric_cols = df.select_dtypes(include=['number']).columns
    print(df[numeric_cols].describe())
    
    print("\nSample data (first 5 rows):")
    print(df.head())
    print("="*80)

def resample_to_5s(df):
    """
    Resample trade data to 5-second intervals
    
    Parameters:
    - df: DataFrame with trade data
    
    Returns:
    - DataFrame with 5-second OHLCV data
    """
    print("\nResampling trade data to 5-second intervals...")
    
    # Make sure datetime is the index for resampling
    if 'datetime' in df.columns:
        df = df.set_index('datetime')
    
    # Define aggregation functions for OHLCV
    agg_dict = {
        'price': ['first', 'max', 'min', 'last'],
        'qty': 'sum'
    }
    
    # Add quote_qty if it exists
    if 'quote_qty' in df.columns:
        agg_dict['quote_qty'] = 'sum'
    
    # Resample to 5-second intervals
    resampled = df.resample('5S').agg(agg_dict)
    
    # Flatten column names
    resampled.columns = ['_'.join(col).strip() for col in resampled.columns.values]
    
    # Rename columns to standard OHLCV names
    column_mapping = {
        'price_first': 'open',
        'price_max': 'high',
        'price_min': 'low',
        'price_last': 'close',
        'qty_sum': 'volume'
    }
    
    if 'quote_qty_sum' in resampled.columns:
        column_mapping['quote_qty_sum'] = 'quote_volume'
    
    resampled = resampled.rename(columns=column_mapping)
    
    # Reset index to make datetime a column again
    resampled = resampled.reset_index()
    
    # Fill NaN values with forward fill for OHLC
    for col in ['open', 'high', 'low', 'close']:
        resampled[col] = resampled[col].fillna(method='ffill')
    
    # Fill NaN values with 0 for volume
    resampled['volume'] = resampled['volume'].fillna(0)
    if 'quote_volume' in resampled.columns:
        resampled['quote_volume'] = resampled['quote_volume'].fillna(0)
    
    print(f"Resampled to {len(resampled):,} 5-second intervals")
    return resampled

def main():
    # Set your parameters directly here
    start_date = "2023-01"    # Start date in format YYYY-MM or YYYY-MM-DD
    end_date = None           # End date in format YYYY-MM or YYYY-MM-DD (None means same as start_date)
    sample_rate = 0.1         # Float between 0 and 1 for random sampling (0.1 = 10%)
    columns = None            # List of columns to load (None means all columns)
    
    # Print configuration
    print(f"Configuration:")
    print(f"  - Start date: {start_date}")
    print(f"  - End date: {end_date or start_date}")
    print(f"  - Sample rate: {sample_rate * 100:.1f}%")
    print(f"  - Columns: {columns or 'All'}")
    
    # Create an instance of the TradeAggregator
    aggregator = TradeAggregator()
    
    # Get available dates
    dates = aggregator.get_available_dates()
    print(f"Available dates: {dates}")
    
    # If no dates are available, exit with a message
    if not dates:
        print("No data available. Please check the data directory.")
        sys.exit(1)
    
    # If specified start date is not available, use the first available date
    if start_date not in dates and dates:
        start_date = dates[0]
        print(f"Specified start date not available. Using first available date: {start_date}")
    
    # Load trades for the specified date range
    print(f"\nLoading trades for period: {start_date} to {end_date or start_date}")
    print(f"Sample rate: {sample_rate * 100:.1f}%")
    print(f"Columns: {columns or 'All'}")
    
    # Make sure we load the datetime and price columns for resampling
    required_columns = ['datetime', 'price', 'qty']
    if columns:
        for col in required_columns:
            if col not in columns:
                columns.append(col)
    
    df = aggregator.load_trades(start_date, end_date, columns, sample_rate)
    
    if df is not None and not df.empty:
        print(f"\nSuccessfully loaded {len(df):,} trades")
        
        # Print original dataframe info
        print("\nOriginal Trade Data:")
        print_dataframe_info(df)
        
        # Resample to 5-second intervals
        df_5s = resample_to_5s(df)
        
        # Print 5-second resampled dataframe info
        print("\n5-Second Resampled Data:")
        print_dataframe_info(df_5s)
        
        # Save to CSV for easy inspection
        csv_filename = f"eth_usdt_5s_{start_date}_{end_date or start_date}.csv"
        df_5s.to_csv(csv_filename, index=False)
        print(f"\nSaved 5-second data to {csv_filename}")
        
        # Plot sample of the data
        try:
            # Plot a sample of the data (first 100 points)
            sample_df = df_5s.head(100)
            
            plt.figure(figsize=(12, 8))
            
            # Price subplot
            plt.subplot(2, 1, 1)
            plt.plot(sample_df['datetime'], sample_df['close'], label='Close Price')
            plt.title('ETH/USDT 5-Second Price')
            plt.ylabel('Price (USDT)')
            plt.grid(True)
            plt.legend()
            
            # Volume subplot
            plt.subplot(2, 1, 2)
            plt.bar(sample_df['datetime'], sample_df['volume'], label='Volume')
            plt.title('ETH/USDT 5-Second Volume')
            plt.xlabel('Time')
            plt.ylabel('Volume (ETH)')
            plt.grid(True)
            plt.legend()
            
            plt.tight_layout()
            
            # Save the plot
            plot_filename = f"eth_usdt_5s_{start_date}_{end_date or start_date}.png"
            plt.savefig(plot_filename)
            print(f"Saved plot to {plot_filename}")
            
        except Exception as e:
            print(f"Error creating plot: {e}")
    else:
        print("No data found for the specified date range")

if __name__ == "__main__":
    main() 
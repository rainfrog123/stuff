#!/usr/bin/env python
"""
Example script demonstrating how to use the TradeAggregator class
"""
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import sys
import os

# Add the parent directory to the Python path to import the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from binance_trade_aggregator import TradeAggregator

def main():
    # Create an instance of the TradeAggregator
    aggregator = TradeAggregator()
    
    # Get available dates
    dates = aggregator.get_available_dates()
    print(f"Available dates: {dates}")
    print(f"First available date: {dates[0]}")
    print(f"Last available date: {dates[-1]}")
    
    # Example 1: Load trades for a specific month
    print("\n=== Example 1: Load trades for a specific month ===")
    df_month = aggregator.load_trades("2023-01")
    
    if df_month is not None:
        print(f"Loaded {len(df_month):,} trades for January 2023")
        print(f"DataFrame shape: {df_month.shape}")
        print(f"Memory usage: {df_month.memory_usage(deep=True).sum() / (1024 * 1024):.2f} MB")
        print("\nSample data:")
        print(df_month.head())
    
    # Example 2: Load trades for a specific date range with sampling
    print("\n=== Example 2: Load trades for a specific date range with sampling ===")
    df_range = aggregator.load_trades("2023-01", "2023-02", sample_rate=0.01)
    
    if df_range is not None:
        print(f"Loaded {len(df_range):,} trades for Jan-Feb 2023 (1% sample)")
        print(f"DataFrame shape: {df_range.shape}")
        
        # Basic analysis
        print("\nBasic statistics:")
        print(df_range[['price', 'qty', 'quote_qty']].describe())
        
        # Calculate daily volume
        df_range['date'] = df_range['datetime'].dt.date
        daily_volume = df_range.groupby('date')['quote_qty'].sum().reset_index()
        print("\nDaily trading volume:")
        print(daily_volume.head())
        
        # Plot daily volume
        plt.figure(figsize=(12, 6))
        plt.bar(daily_volume['date'], daily_volume['quote_qty'])
        plt.title('Daily Trading Volume (Jan-Feb 2023, 1% sample)')
        plt.xlabel('Date')
        plt.ylabel('Volume (USDT)')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig('daily_volume.png')
        print("Saved daily volume chart to 'daily_volume.png'")
    
    # Example 3: Load specific columns only
    print("\n=== Example 3: Load specific columns only ===")
    df_columns = aggregator.load_trades("2023-01", columns=['price', 'time'])
    
    if df_columns is not None:
        print(f"Loaded {len(df_columns):,} trades with selected columns")
        print(f"DataFrame shape: {df_columns.shape}")
        print(f"Columns: {df_columns.columns.tolist()}")
        print("\nSample data:")
        print(df_columns.head())
    
    # Example 4: Calculate hourly OHLC data
    print("\n=== Example 4: Calculate hourly OHLC data ===")
    df_ohlc = aggregator.load_trades("2023-01-01", "2023-01-02", sample_rate=0.1)
    
    if df_ohlc is not None:
        # Add hour column
        df_ohlc['hour'] = df_ohlc['datetime'].dt.floor('H')
        
        # Calculate OHLC
        hourly_ohlc = df_ohlc.groupby('hour').agg({
            'price': ['first', 'max', 'min', 'last'],
            'qty': 'sum',
            'quote_qty': 'sum'
        }).reset_index()
        
        # Flatten column names
        hourly_ohlc.columns = ['hour', 'open', 'high', 'low', 'close', 'volume', 'quote_volume']
        
        print("\nHourly OHLC data:")
        print(hourly_ohlc.head())
        
        # Plot OHLC
        plt.figure(figsize=(14, 7))
        
        # Price subplot
        plt.subplot(2, 1, 1)
        plt.plot(hourly_ohlc['hour'], hourly_ohlc['close'], label='Close Price')
        plt.title('Hourly ETH/USDT Price (Jan 1-2, 2023)')
        plt.ylabel('Price (USDT)')
        plt.legend()
        
        # Volume subplot
        plt.subplot(2, 1, 2)
        plt.bar(hourly_ohlc['hour'], hourly_ohlc['quote_volume'])
        plt.title('Hourly Trading Volume')
        plt.xlabel('Hour')
        plt.ylabel('Volume (USDT)')
        
        plt.tight_layout()
        plt.savefig('hourly_ohlc.png')
        print("Saved hourly OHLC chart to 'hourly_ohlc.png'")

if __name__ == "__main__":
    main() 
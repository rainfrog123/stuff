#!/usr/bin/env python3
"""
Data viewer utility for the 5-second data collection system.
"""

import argparse
import sys
import pandas as pd
from datetime import datetime, timedelta
import json
import os

from data_access import DataAccess

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='View and export collected 5-second market data.')
    
    # Command options
    parser.add_argument('command', choices=['info', 'candles', 'trades', 'export'],
                        help='Command to execute')
    
    # Symbol option
    parser.add_argument('--symbol', '-s', type=str, default='ETH/USDT',
                        help='Trading pair symbol (default: ETH/USDT)')
    
    # Time range options
    parser.add_argument('--start', type=str,
                        help='Start time (format: YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--end', type=str,
                        help='End time (format: YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--last', type=str,
                        help='Last period (e.g., 1h, 30m, 5m)')
    
    # Limit option
    parser.add_argument('--limit', '-l', type=int, default=10,
                        help='Number of records to display (default: 10)')
    
    # Export options
    parser.add_argument('--type', '-t', choices=['candles', 'trades'], default='candles',
                        help='Type of data to export (default: candles)')
    parser.add_argument('--timeframe', '-tf', type=str, default='5s',
                        help='Timeframe for candles export (default: 5s)')
    parser.add_argument('--output', '-o', type=str,
                        help='Output file name for export')
    
    return parser.parse_args()

def parse_time_range(args):
    """Parse time range from arguments."""
    end_time = datetime.now()
    start_time = None
    
    # Parse explicit start and end times
    if args.start:
        try:
            start_time = datetime.strptime(args.start, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            print(f"Error: Invalid start time format. Use YYYY-MM-DD HH:MM:SS")
            sys.exit(1)
    
    if args.end:
        try:
            end_time = datetime.strptime(args.end, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            print(f"Error: Invalid end time format. Use YYYY-MM-DD HH:MM:SS")
            sys.exit(1)
    
    # Parse relative time period
    if args.last:
        if not start_time:
            unit = args.last[-1].lower()
            try:
                value = int(args.last[:-1])
                
                if unit == 'h':
                    start_time = end_time - timedelta(hours=value)
                elif unit == 'm':
                    start_time = end_time - timedelta(minutes=value)
                elif unit == 'd':
                    start_time = end_time - timedelta(days=value)
                else:
                    print(f"Error: Invalid time unit in --last. Use h (hours), m (minutes), or d (days)")
                    sys.exit(1)
            except ValueError:
                print(f"Error: Invalid time period format. Use e.g. 1h, 30m, or 2d")
                sys.exit(1)
    
    # Default to last hour if nothing specified
    if not start_time:
        start_time = end_time - timedelta(hours=1)
    
    return start_time, end_time

def format_df_for_display(df, limit):
    """Format DataFrame for display."""
    if df.empty:
        return "No data found."
    
    pd.set_option('display.max_rows', limit)
    pd.set_option('display.width', 120)
    pd.set_option('display.precision', 8)
    
    return df.tail(limit)

def show_info(data):
    """Show information about available data."""
    info = data.get_latest_data_info()
    
    if not info:
        print("No data available in the database.")
        return
    
    for symbol, symbol_info in info.items():
        print(f"\n=== {symbol} ===")
        print(f"First data:     {symbol_info['first_data']}")
        print(f"Latest candle:  {symbol_info['latest_candle']}")
        print(f"Latest trade:   {symbol_info['latest_trade']}")
        print(f"Time span:      {symbol_info['time_span']}")
        print(f"Candle count:   {symbol_info['candle_count']}")
        print(f"Trade count:    {symbol_info['trade_count']}")

def show_candles(data, symbol, start_time, end_time, limit):
    """Show candles for a symbol."""
    candles = data.get_candles(symbol, start_time, end_time, limit)
    
    if candles.empty:
        print(f"No candle data found for {symbol} in the specified time range.")
        return
    
    print(f"\n=== 5s Candles for {symbol} ===")
    print(f"Time range: {start_time} to {end_time}")
    print(format_df_for_display(candles, limit))

def show_trades(data, symbol, start_time, end_time, limit):
    """Show trades for a symbol."""
    trades = data.get_trades(symbol, start_time, end_time, limit)
    
    if trades.empty:
        print(f"No trade data found for {symbol} in the specified time range.")
        return
    
    print(f"\n=== Trades for {symbol} ===")
    print(f"Time range: {start_time} to {end_time}")
    print(format_df_for_display(trades, limit))

def export_data(data, symbol, data_type, timeframe, start_time, end_time, output):
    """Export data to a file."""
    filename = data.export_to_csv(
        symbol, 
        data_type=data_type, 
        timeframe=timeframe,
        start_time=start_time, 
        end_time=end_time, 
        filename=output
    )
    
    if filename:
        print(f"Data exported to {filename}")
    else:
        print("Export failed. Check logs for details.")

def main():
    """Main function."""
    args = parse_args()
    start_time, end_time = parse_time_range(args)
    
    # Initialize data access
    data = DataAccess()
    
    # Execute command
    if args.command == 'info':
        show_info(data)
    elif args.command == 'candles':
        show_candles(data, args.symbol, start_time, end_time, args.limit)
    elif args.command == 'trades':
        show_trades(data, args.symbol, start_time, end_time, args.limit)
    elif args.command == 'export':
        export_data(data, args.symbol, args.type, args.timeframe, 
                   start_time, end_time, args.output)

if __name__ == "__main__":
    main() 
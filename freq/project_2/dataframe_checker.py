#!/usr/bin/env python
import os
import sys
import argparse
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from tabulate import tabulate
from datetime import datetime

def list_parquet_files(directory, pattern=None):
    """
    List all parquet files in the specified directory
    
    Parameters:
    - directory: Directory to search in
    - pattern: Optional glob pattern to filter files
    
    Returns:
    - List of file paths
    """
    if pattern:
        search_pattern = os.path.join(directory, pattern)
    else:
        search_pattern = os.path.join(directory, "*.parquet")
    
    files = glob.glob(search_pattern)
    files.sort()
    return files

def display_file_info(file_paths):
    """
    Display information about the parquet files
    
    Parameters:
    - file_paths: List of file paths
    """
    if not file_paths:
        print("No parquet files found!")
        return
    
    print(f"\nFound {len(file_paths)} parquet files:")
    print("-" * 80)
    
    file_info = []
    for path in file_paths:
        filename = os.path.basename(path)
        file_size = os.path.getsize(path)
        human_size = f"{file_size / (1024 * 1024):.2f} MB"
        
        # Try to extract date from filename (format: ETHUSDT-trades-YYYY-MM-DD.parquet or ETHUSDT-trades-YYYY-MM.parquet)
        date_part = ""
        try:
            date_part = filename.split('-trades-')[1].split('.')[0]
        except:
            pass
        
        file_info.append([filename, date_part, human_size])
    
    # Display the file info as a table
    print(tabulate(file_info, headers=["Filename", "Date", "Size"], tablefmt="pretty"))
    print("-" * 80)

def load_parquet_file(file_path, sample_rows=None):
    """
    Load a parquet file into a pandas DataFrame
    
    Parameters:
    - file_path: Path to the parquet file
    - sample_rows: Number of rows to load (optional)
    
    Returns:
    - DataFrame
    """
    try:
        if sample_rows:
            # First get total row count
            parquet_file = pd.read_parquet(file_path, engine='pyarrow')
            total_rows = len(parquet_file)
            
            # Determine if we should sample
            if sample_rows < total_rows:
                print(f"Loading sample of {sample_rows} rows out of {total_rows} total rows")
                df = parquet_file.sample(n=sample_rows, random_state=42)
            else:
                df = parquet_file
        else:
            df = pd.read_parquet(file_path, engine='pyarrow')
        
        # Convert timestamp to datetime if it exists
        if 'time' in df.columns and 'datetime' not in df.columns:
            df['datetime'] = pd.to_datetime(df['time'], unit='ms')
        
        return df
    except Exception as e:
        print(f"Error loading parquet file: {e}")
        return None

def analyze_dataframe(df):
    """
    Analyze the contents of a DataFrame and print useful information
    
    Parameters:
    - df: DataFrame to analyze
    """
    if df is None or len(df) == 0:
        print("DataFrame is empty or None!")
        return
    
    # Basic DataFrame info
    print("\n=== DataFrame Info ===")
    print(f"Shape: {df.shape[0]} rows × {df.shape[1]} columns")
    print("\nColumn types:")
    for col, dtype in df.dtypes.items():
        print(f"  {col}: {dtype}")
    
    # Memory usage
    memory_usage = df.memory_usage(deep=True).sum()
    print(f"\nMemory usage: {memory_usage / (1024 * 1024):.2f} MB")
    
    # Time range if datetime exists
    if 'datetime' in df.columns:
        min_time = df['datetime'].min()
        max_time = df['datetime'].max()
        time_span = max_time - min_time
        print(f"\nTime range: {min_time} to {max_time} (span: {time_span})")
    
    # Sample data
    print("\n=== Sample Data ===")
    print(tabulate(df.head(10), headers='keys', tablefmt='pretty', showindex=True))
    
    # Summary statistics
    print("\n=== Summary Statistics ===")
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if numeric_cols:
        print(tabulate(df[numeric_cols].describe().transpose(), 
                       headers='keys', tablefmt='pretty', floatfmt=".6f"))
    else:
        print("No numeric columns found for statistics")
    
    # Count of unique values for categorical columns
    cat_cols = df.select_dtypes(exclude=[np.number, 'datetime64']).columns.tolist()
    if cat_cols:
        print("\n=== Categorical Value Counts ===")
        for col in cat_cols[:5]:  # Limit to first 5 categorical columns
            if df[col].nunique() < 20:  # Only show if fewer than 20 unique values
                print(f"\n{col}:")
                print(df[col].value_counts().head(10))

def plot_dataframe(df, output_file=None):
    """
    Create basic plots of the DataFrame data
    
    Parameters:
    - df: DataFrame to plot
    - output_file: Path to save the plot (optional)
    """
    if df is None or len(df) == 0:
        print("DataFrame is empty or None!")
        return
    
    # Create a figure with multiple subplots
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('Data Visualization', fontsize=16)
    
    # Plot 1: Price over time (if available)
    if 'datetime' in df.columns and 'price' in df.columns:
        ax = axes[0, 0]
        df.set_index('datetime')['price'].plot(ax=ax, alpha=0.7)
        ax.set_title('Price Over Time')
        ax.set_ylabel('Price')
        ax.grid(True, alpha=0.3)
    
    # Plot 2: Price histogram (if available)
    if 'price' in df.columns:
        ax = axes[0, 1]
        df['price'].plot.hist(bins=50, ax=ax, alpha=0.7)
        ax.set_title('Price Distribution')
        ax.set_xlabel('Price')
        ax.grid(True, alpha=0.3)
    
    # Plot 3: Quantity histogram (if available)
    if 'qty' in df.columns:
        ax = axes[1, 0]
        df['qty'].plot.hist(bins=50, ax=ax, alpha=0.7)
        ax.set_title('Quantity Distribution')
        ax.set_xlabel('Quantity')
        ax.grid(True, alpha=0.3)
    
    # Plot 4: Trades per minute/hour (if datetime available)
    if 'datetime' in df.columns:
        ax = axes[1, 1]
        # Resample to count trades per minute or hour
        if (df['datetime'].max() - df['datetime'].min()).total_seconds() < 3600:
            # Less than an hour of data, group by minute
            df.set_index('datetime').resample('1min').size().plot(ax=ax, kind='bar', alpha=0.7)
            ax.set_title('Trades per Minute')
        else:
            # More data, group by hour
            df.set_index('datetime').resample('1h').size().plot(ax=ax, kind='bar', alpha=0.7)
            ax.set_title('Trades per Hour')
        ax.set_ylabel('Number of Trades')
        ax.tick_params(axis='x', rotation=45)
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save or show the figure
    if output_file:
        plt.savefig(output_file)
        print(f"Plot saved to: {output_file}")
    else:
        plt.show()

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Parquet DataFrame Checker - Inspect Binance Trade Data')
    parser.add_argument('--dir', type=str, default='/allah/data/trades', 
                        help='Directory containing parquet files (default: /allah/data/trades)')
    parser.add_argument('--pattern', type=str, 
                        help='Glob pattern to filter files (e.g., "ETHUSDT-trades-2025-03-*.parquet")')
    parser.add_argument('--file', type=str, 
                        help='Specific parquet file to analyze')
    parser.add_argument('--sample', type=int, default=10000, 
                        help='Number of rows to sample (default: 10000, use 0 for all)')
    parser.add_argument('--plot', action='store_true', 
                        help='Create plots of the data')
    parser.add_argument('--save_plot', type=str, 
                        help='Save plot to file instead of displaying')
    
    args = parser.parse_args()
    
    # Configure pandas display options
    pd.set_option('display.max_rows', 20)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.float_format', lambda x: '%.6f' % x)
    
    # Process based on arguments
    if args.file:
        # Analyze a specific file
        if not os.path.exists(args.file):
            print(f"Error: File not found: {args.file}")
            return
        
        print(f"Analyzing file: {args.file}")
        sample_rows = args.sample if args.sample > 0 else None
        df = load_parquet_file(args.file, sample_rows)
        
        if df is not None:
            analyze_dataframe(df)
            
            if args.plot:
                plot_dataframe(df, args.save_plot)
    else:
        # List and choose from available files
        search_dir = args.dir
        if not os.path.exists(search_dir):
            print(f"Error: Directory not found: {search_dir}")
            return
        
        files = list_parquet_files(search_dir, args.pattern)
        display_file_info(files)
        
        if files:
            # Ask user to select a file
            while True:
                try:
                    choice = input("\nEnter file number to analyze (1-{0}) or 'q' to quit: ".format(len(files)))
                    if choice.lower() == 'q':
                        return
                    
                    file_idx = int(choice) - 1
                    if 0 <= file_idx < len(files):
                        selected_file = files[file_idx]
                        print(f"\nSelected: {os.path.basename(selected_file)}")
                        
                        sample_rows = args.sample if args.sample > 0 else None
                        df = load_parquet_file(selected_file, sample_rows)
                        
                        if df is not None:
                            analyze_dataframe(df)
                            
                            if args.plot:
                                plot_dataframe(df, args.save_plot)
                        
                        another = input("\nAnalyze another file? (y/n): ")
                        if another.lower() != 'y':
                            break
                    else:
                        print("Invalid selection. Please try again.")
                except ValueError:
                    print("Please enter a valid number or 'q'.")
                except KeyboardInterrupt:
                    print("\nOperation cancelled by user.")
                    return
        else:
            print("No parquet files found to analyze!")

if __name__ == "__main__":
    main() 
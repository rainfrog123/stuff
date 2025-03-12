#!/usr/bin/env python
import pandas as pd
import os
import glob
from datetime import datetime
from tqdm import tqdm

# Path to the trades directory
TRADES_DIR = "/allah/data/trades/eth_usdt_monthly_trades"

class TradeAggregator:
    """
    Class for aggregating Binance trade data from Parquet files
    """
    
    def __init__(self, trades_dir=TRADES_DIR):
        """
        Initialize the aggregator
        
        Parameters:
        - trades_dir: Path to the directory containing trade Parquet files
        """
        self.trades_dir = trades_dir
    
    def parse_date(self, date_str):
        """
        Parse date string in format YYYY-MM or YYYY-MM-DD
        Returns a tuple of (year, month)
        """
        if len(date_str) == 7:  # YYYY-MM format
            dt = datetime.strptime(date_str, "%Y-%m")
            return dt.year, dt.month
        elif len(date_str) == 10:  # YYYY-MM-DD format
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.year, dt.month
        else:
            raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM or YYYY-MM-DD")
    
    def get_available_dates(self):
        """
        Get list of available dates in the trades directory
        
        Returns:
        - List of dates in format YYYY-MM
        """
        all_files = glob.glob(os.path.join(self.trades_dir, "*.parquet"))
        dates = []
        
        for file_path in all_files:
            file_name = os.path.basename(file_path)
            # Extract date from filename (format: ETHUSDT-trades-YYYY-MM.parquet)
            try:
                date_part = file_name.split('-trades-')[1].split('.')[0]
                dates.append(date_part)
            except (IndexError, ValueError):
                # Skip files that don't match the expected format
                continue
        
        # Sort dates
        dates.sort()
        return dates
    
    def get_parquet_files(self, start_date, end_date=None):
        """
        Get list of Parquet files between start_date and end_date (inclusive)
        If end_date is None, only get files for start_date
        
        Parameters:
        - start_date: string in format 'YYYY-MM' or 'YYYY-MM-DD'
        - end_date: string in format 'YYYY-MM' or 'YYYY-MM-DD' (optional)
        
        Returns:
        - List of file paths
        """
        start_year, start_month = self.parse_date(start_date)
        
        if end_date:
            end_year, end_month = self.parse_date(end_date)
        else:
            # If no end date provided, use the same as start date
            end_year, end_month = start_year, start_month
        
        # Validate dates
        if (end_year < start_year) or (end_year == start_year and end_month < start_month):
            raise ValueError("End date must be after or equal to start date")
        
        # Get all Parquet files
        all_files = glob.glob(os.path.join(self.trades_dir, "*.parquet"))
        
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
    
    def load_parquet_files(self, file_paths, columns=None, sample_rate=None, verbose=True):
        """
        Load and concatenate Parquet files
        
        Parameters:
        - file_paths: List of file paths to load
        - columns: List of columns to load (optional)
        - sample_rate: Float between 0 and 1 for random sampling (optional)
        - verbose: Whether to print progress information
        
        Returns:
        - Concatenated DataFrame
        """
        if not file_paths:
            if verbose:
                print("No files found for the specified date range")
            return None
        
        dfs = []
        total_size = 0
        
        if verbose:
            print(f"Loading {len(file_paths)} files...")
            file_iter = tqdm(file_paths)
        else:
            file_iter = file_paths
            
        for file_path in file_iter:
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
                if verbose:
                    file_name = os.path.basename(file_path)
                    print(f"Loaded {file_name}: {len(df):,} rows")
                
            except Exception as e:
                if verbose:
                    print(f"Error loading {file_path}: {e}")
        
        if not dfs:
            return None
        
        # Concatenate all dataframes
        if verbose:
            print(f"Concatenating {len(dfs)} dataframes with total {total_size:,} rows...")
        result = pd.concat(dfs, ignore_index=True)
        
        # Convert timestamp to datetime
        if 'time' in result.columns:
            result['datetime'] = pd.to_datetime(result['time'], unit='ms')
        
        return result
    
    def load_trades(self, start_date, end_date=None, columns=None, sample_rate=None, verbose=True):
        """
        Load trades for a specific date range
        
        Parameters:
        - start_date: string in format 'YYYY-MM' or 'YYYY-MM-DD'
        - end_date: string in format 'YYYY-MM' or 'YYYY-MM-DD' (optional)
        - columns: List of columns to load (optional)
        - sample_rate: Float between 0 and 1 for random sampling (optional)
        - verbose: Whether to print progress information
        
        Returns:
        - DataFrame with trade data
        """
        files = self.get_parquet_files(start_date, end_date)
        
        if not files:
            if verbose:
                print(f"No files found for the specified date range: {start_date} to {end_date or start_date}")
            return None
        
        if verbose:
            print(f"Found {len(files)} files for the specified date range")
            for file in files:
                print(f"  - {os.path.basename(file)}")
        
        return self.load_parquet_files(files, columns, sample_rate, verbose)

# Example usage
if __name__ == "__main__":
    # Create an instance of the aggregator
    aggregator = TradeAggregator()
    
    # Get available dates
    dates = aggregator.get_available_dates()
    print(f"Available dates: {dates}")
    
    # Load trades for a specific date range
    df = aggregator.load_trades("2023-01", "2023-02")
    
    if df is not None:
        print(f"\nLoaded DataFrame with {len(df):,} rows and {len(df.columns)} columns")
        print("\nDataFrame info:")
        print(df.info())
        print("\nDataFrame head:")
        print(df.head()) 
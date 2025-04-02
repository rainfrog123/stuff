#!/usr/bin/env python
import requests
import os
import time
import sys
import glob
import zipfile
import shutil
import io
from datetime import datetime, timedelta
from tqdm import tqdm
import humanize
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.dates import DateFormatter
import matplotlib.dates as mdates
from tabulate import tabulate

# Base URL for Binance daily data
BASE_URL = "https://data.binance.vision/data/futures/um/daily/trades/ETHUSDT"

# Default directories
DEFAULT_OUTPUT_DIR = "/allah/data/trades"
# Use the existing directory with data files
DEFAULT_DATA_DIR = os.path.join(DEFAULT_OUTPUT_DIR, "eth_usdt_daily_trades")

class BinanceDailyTradesManager:
    """
    Class for downloading and aggregating Binance daily trade data
    """
    
    def __init__(self, trades_dir=None):
        """
        Initialize the manager
        
        Parameters:
        - trades_dir: Path to the directory containing trade Parquet files
        """
        # Create or use existing output directory
        os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
        
        # Use provided directory or default to the fixed directory with data
        if trades_dir is None:
            self.trades_dir = DEFAULT_DATA_DIR
            os.makedirs(self.trades_dir, exist_ok=True)
            print(f"Using directory: {self.trades_dir}")
        else:
            self.trades_dir = trades_dir
            os.makedirs(self.trades_dir, exist_ok=True)
            print(f"Using provided directory: {self.trades_dir}")
    
    # ===== DOWNLOADER METHODS =====
    
    def get_free_space(self, path):
        """
        Get free space in bytes for the given path
        """
        try:
            total, used, free = shutil.disk_usage(path)
            return free
        except:
            # Fallback method using statvfs
            try:
                st = os.statvfs(path)
                return st.f_frsize * st.f_bavail
            except:
                return 0

    def get_file_size(self, url):
        """
        Get file size from URL without downloading
        """
        try:
            response = requests.head(url)
            return int(response.headers.get('content-length', 0))
        except:
            return 0

    def download_file(self, url, output_path):
        """
        Download a file with progress bar
        """
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        
        with open(output_path, 'wb') as file, tqdm(
            desc=os.path.basename(output_path),
            total=total_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
        ) as pbar:
            for data in response.iter_content(chunk_size=1024):
                size = file.write(data)
                pbar.update(size)

    def convert_csv_to_parquet(self, csv_path, parquet_path):
        """
        Convert CSV to Parquet with high compression, processing in chunks to handle large files
        """
        try:
            # Process CSV in chunks to handle large files
            chunk_size = 500000  # Reduced chunk size for better memory management
            
            # Read the first chunk to get the schema
            first_chunk = pd.read_csv(csv_path, nrows=1)
            schema = {}
            for column in first_chunk.columns:
                if column == 'timestamp':
                    schema[column] = 'datetime64[ns]'
                else:
                    schema[column] = first_chunk[column].dtype
            
            # Process chunks and write directly to parquet
            chunks = pd.read_csv(csv_path, chunksize=chunk_size, dtype=schema)
            
            first = True
            for chunk in chunks:
                # Convert timestamp to datetime if it exists
                if 'timestamp' in chunk.columns:
                    chunk['timestamp'] = pd.to_datetime(chunk['timestamp'])
                
                # Write mode: 'write' for first chunk, 'append' for subsequent chunks
                mode = 'write' if first else 'append'
                chunk.to_parquet(
                    parquet_path,
                    compression='snappy',
                    index=False,
                    engine='fastparquet',  # Using fastparquet engine which supports append mode
                    append=not first
                )
                first = False
            
            # Remove the original CSV file
            os.remove(csv_path)
            print(f"Converted and compressed: {os.path.basename(csv_path)} → {os.path.basename(parquet_path)}")
            return True
        except Exception as e:
            print(f"Error converting to parquet: {e}")
            # Clean up any partial files
            if os.path.exists(parquet_path):
                os.remove(parquet_path)
            return False

    def get_existing_files(self):
        """
        Get list of already processed files
        """
        existing_files = set()
        for file in glob.glob(os.path.join(self.trades_dir, "*.parquet")):
            # Extract date from filename
            basename = os.path.basename(file)
            if basename.startswith("ETHUSDT-trades-"):
                date_str = basename.split("ETHUSDT-trades-")[1].split(".")[0]  # e.g., "2025-03-01"
                existing_files.add(date_str)
        return existing_files

    def extract_and_convert(self, zip_path, extract_path):
        """
        Extract ZIP file, convert CSV to Parquet, and clean up
        """
        success = False
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Extract CSV file
                csv_files = [f for f in zip_ref.namelist() if f.endswith('.csv')]
                for csv_file in csv_files:
                    zip_ref.extract(csv_file, extract_path)
                    csv_path = os.path.join(extract_path, csv_file)
                    parquet_path = csv_path.replace('.csv', '.parquet')
                    
                    print(f"Converting {csv_file} to Parquet format...")
                    if self.convert_csv_to_parquet(csv_path, parquet_path):
                        success = True
                    elif os.path.exists(csv_path):
                        os.remove(csv_path)  # Clean up CSV if conversion failed
            return success
        except Exception as e:
            print(f"Error extracting zip: {e}")
            return False

    def download_daily_trades(self, year=2025, month=3):
        """
        Download daily ETH/USDT perpetual futures trade data from Binance
        
        Args:
            year (int): Year to download (default: 2025)
            month (int): Month to download (default: 3)
        """
        # Get list of already processed files
        existing_files = self.get_existing_files()
        print(f"\nFound {len(existing_files)} existing processed files")
        if existing_files:
            print("Date range:", min(existing_files), "to", max(existing_files))
        
        # Generate list of days to download for the specified month
        days_to_download = []
        
        # Create a datetime for the first day of the specified month
        first_day = datetime(year, month, 1)
        
        # Determine the number of days in the specified month
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        
        num_days = (next_month - first_day).days
        
        # Generate date range for the specified month
        for day in range(1, num_days + 1):
            date = first_day + timedelta(days=day-1)
            date_str = date.strftime('%Y-%m-%d')
            
            # Check if parquet file already exists
            parquet_filename = f"ETHUSDT-trades-{date_str}.parquet"
            parquet_path = os.path.join(self.trades_dir, parquet_filename)
            if os.path.exists(parquet_path):
                print(f"Skipping {date_str} - parquet file already exists")
                continue
            
            days_to_download.append(date)
        
        if not days_to_download:
            print("\nAll files are up to date!")
            return
        
        total_files = len(days_to_download)
        print(f"\nFiles to download: {total_files}")
        
        # Download and process files
        processed_count = 0
        for idx, date in enumerate(days_to_download, 1):
            date_str = date.strftime('%Y-%m-%d')
            zip_filename = f"ETHUSDT-trades-{date_str}.zip"
            
            # Create URLs and paths
            zip_url = f"{BASE_URL}/{zip_filename}"
            zip_path = os.path.join(self.trades_dir, zip_filename)
            
            try:
                print(f"\nProcessing file {idx}/{total_files}: {zip_filename}")
                
                # Get and show file size
                file_size = self.get_file_size(zip_url)
                if file_size == 0:
                    print(f"Skipping {zip_filename} - file not available or empty")
                    continue
                
                print(f"File size: {humanize.naturalsize(file_size)}")
                
                # Check available disk space
                free_space = self.get_free_space(self.trades_dir)
                required_space = file_size * 2  # Need roughly 2x zip size for extraction
                
                if required_space > free_space:
                    print(f"Warning: Not enough disk space!")
                    print(f"Required: {humanize.naturalsize(required_space)}")
                    print(f"Available: {humanize.naturalsize(free_space)}")
                    print("Please free up some space and try again.")
                    break
                
                # Download file
                print(f"Downloading {zip_filename}...")
                self.download_file(zip_url, zip_path)
                
                # Extract, convert to parquet, and clean up
                print(f"Processing {zip_filename}...")
                if self.extract_and_convert(zip_path, self.trades_dir):
                    processed_count += 1
                
                # Remove the zip file
                if os.path.exists(zip_path):
                    os.remove(zip_path)
                
                # Small delay between downloads
                time.sleep(1)
                
            except Exception as e:
                print(f"Error processing {zip_filename}: {e}")
                # Clean up any partial downloads
                if os.path.exists(zip_path):
                    os.remove(zip_path)
                continue
        
        print(f"\nDownload completed! Data saved to: {self.trades_dir}")
        
        # Show final statistics
        final_files = self.get_existing_files()
        print(f"Total files processed this run: {processed_count}")
        print(f"Total files in directory: {len(final_files)}")
        if final_files:  # Only show date range if there are files
            print("Date range:", min(final_files), "to", max(final_files))
    
    # ===== AGGREGATOR METHODS =====
    
    def parse_date(self, date_str):
        """
        Parse date string in format YYYY-MM-DD
        Returns a datetime object
        """
        try:
            if len(date_str) == 10:  # YYYY-MM-DD format
                return datetime.strptime(date_str, "%Y-%m-%d")
            else:
                raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD")
        except ValueError as e:
            print(f"Error parsing date: {e}")
            sys.exit(1)
    
    def get_daily_dates(self):
        """
        Get list of available daily dates
        
        Returns:
        - List of dates in format YYYY-MM-DD
        """
        all_files = glob.glob(os.path.join(self.trades_dir, "ETHUSDT-trades-????-??-??.parquet"))
        dates = []
        
        for file_path in all_files:
            file_name = os.path.basename(file_path)
            # Extract date from filename (format: ETHUSDT-trades-YYYY-MM-DD.parquet)
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
        - start_date: string in format 'YYYY-MM-DD'
        - end_date: string in format 'YYYY-MM-DD' (optional)
        
        Returns:
        - List of file paths
        """
        start_dt = self.parse_date(start_date)
        
        if end_date:
            end_dt = self.parse_date(end_date)
        else:
            # If no end date provided, use the same as start date
            end_dt = start_dt
        
        # Validate dates
        if end_dt < start_dt:
            raise ValueError("End date must be after or equal to start date")
        
        # Get all Parquet files
        all_files = glob.glob(os.path.join(self.trades_dir, "ETHUSDT-trades-????-??-??.parquet"))
        
        # Filter files based on date range
        filtered_files = []
        for file_path in all_files:
            file_name = os.path.basename(file_path)
            # Extract date from filename (format: ETHUSDT-trades-YYYY-MM-DD.parquet)
            try:
                date_part = file_name.split('-trades-')[1].split('.')[0]
                file_dt = datetime.strptime(date_part, "%Y-%m-%d")
                
                # Check if file is within date range
                if start_dt <= file_dt <= end_dt:
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
        - start_date: string in format 'YYYY-MM-DD'
        - end_date: string in format 'YYYY-MM-DD' (optional)
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

    def visualize_trades(self, df, timeframe='1min', price_col='price', save_path=None):
        """
        Visualize trade data with the specified timeframe
        
        Parameters:
        - df: DataFrame with trade data
        - timeframe: Timeframe for resampling (default: '1min')
        - price_col: Column name for price data (default: 'price')
        - save_path: Path to save the figure (optional)
        
        Returns:
        - None (displays or saves the figure)
        """
        if df is None or len(df) == 0:
            print("No data to visualize")
            return
        
        # Make sure datetime column exists
        if 'datetime' not in df.columns and 'time' in df.columns:
            df['datetime'] = pd.to_datetime(df['time'], unit='ms')
        
        if 'datetime' not in df.columns:
            print("No datetime column found in data")
            return
        
        # Set datetime as index for resampling
        df = df.set_index('datetime')
        
        # Resample data to the specified timeframe
        resampled = df[price_col].resample(timeframe).agg(['first', 'max', 'min', 'last'])
        
        # Create figure and axis
        fig, ax = plt.figure(figsize=(12, 6)), plt.gca()
        
        # Plot the price data
        ax.plot(resampled.index, resampled['last'], label=f'ETH/USDT ({timeframe} timeframe)')
        
        # Format the x-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
        plt.xticks(rotation=45)
        
        # Add labels and title
        plt.xlabel('Time')
        plt.ylabel('Price (USDT)')
        plt.title(f'ETH/USDT Price ({timeframe} timeframe)')
        
        # Add grid and legend
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # Adjust layout
        plt.tight_layout()
        
        # Save or show the figure
        if save_path:
            plt.savefig(save_path)
            print(f"Figure saved to {save_path}")
        else:
            plt.show()

def main():
    # Configure pandas display options for better terminal output
    pd.set_option('display.max_rows', 20)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.float_format', lambda x: '%.5f' % x)
    
    # Initialize the Binance Trades Manager
    manager = BinanceDailyTradesManager()
    
    # Always download March 2025 data
    print("Checking and downloading ETH/USDT trades data for March 2025...")
    manager.download_daily_trades(year=2025, month=3)
    
    # Display available dates after download
    daily_dates = manager.get_daily_dates()
    if daily_dates:
        print(f"\nAvailable data files ({len(daily_dates)}):")
        for date in daily_dates:
            print(f"  - {date}")
        print(f"\nDate range: {daily_dates[0]} to {daily_dates[-1]}")
    else:
        print("No data files found")

if __name__ == "__main__":
    main() 
#!/usr/bin/env python
import requests
import os
import time
import sys
import glob
import zipfile
import shutil
import argparse
import io
from datetime import datetime
from tqdm import tqdm
import humanize
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.dates import DateFormatter
import matplotlib.dates as mdates
from tabulate import tabulate

# Base URL for Binance data
BASE_URL = "https://data.binance.vision/data/futures/um/monthly/trades/ETHUSDT"

# Default directories
DEFAULT_OUTPUT_DIR = "/allah/data/trades"
# Use the existing directory with data files instead of creating a new timestamped one
DEFAULT_DATA_DIR = os.path.join(DEFAULT_OUTPUT_DIR, "eth_usdt_monthly_trades")

class BinanceTradesManager:
    """
    Class for downloading and aggregating Binance monthly trade data
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
            # Extract year and month from filename
            basename = os.path.basename(file)
            if basename.startswith("ETHUSDT-trades-"):
                year_month = basename.split("ETHUSDT-trades-")[1].split(".")[0]  # e.g., "2019-11"
                existing_files.add(year_month)
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

    def download_monthly_trades(self, start_year=2019, start_month=11):
        """
        Download monthly ETH/USDT perpetual futures trade data from Binance
        
        Args:
            start_year (int): Starting year (default: 2019)
            start_month (int): Starting month (default: 11)
        """
        # Get list of already processed files
        existing_files = self.get_existing_files()
        print(f"\nFound {len(existing_files)} existing processed files")
        if existing_files:
            print("Date range:", min(existing_files), "to", max(existing_files))
        
        # Get current date
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        
        # Generate list of months to download
        months_to_download = []
        for year in range(start_year, current_year + 1):
            for month in range(1, 13):
                # Skip future months
                if year == current_year and month > current_month:
                    continue
                # Skip months before start date
                if year == start_year and month < start_month:
                    continue
                # Format month with leading zero
                month_str = f"{month:02d}"
                year_month = f"{year}-{month_str}"
                
                # Check if parquet file already exists
                parquet_filename = f"ETHUSDT-trades-{year_month}.parquet"
                parquet_path = os.path.join(self.trades_dir, parquet_filename)
                if os.path.exists(parquet_path):
                    print(f"Skipping {year_month} - parquet file already exists")
                    continue
                
                months_to_download.append((year, month))
        
        if not months_to_download:
            print("\nAll files are up to date!")
            return
        
        total_files = len(months_to_download)
        print(f"\nFiles to download: {total_files}")
        
        # Download and process files
        processed_count = 0
        for idx, (year, month) in enumerate(months_to_download, 1):
            month_str = f"{month:02d}"
            zip_filename = f"ETHUSDT-trades-{year}-{month_str}.zip"
            
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
        Parse date string in format YYYY-MM
        Returns a tuple of (year, month)
        """
        try:
            if len(date_str) == 7:  # YYYY-MM format
                dt = datetime.strptime(date_str, "%Y-%m")
                return dt.year, dt.month
            else:
                raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM")
        except ValueError as e:
            print(f"Error parsing date: {e}")
            sys.exit(1)
    
    def get_monthly_dates(self):
        """
        Get list of available monthly dates
        
        Returns:
        - List of dates in format YYYY-MM
        """
        all_files = glob.glob(os.path.join(self.trades_dir, "ETHUSDT-trades-????-??.parquet"))
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
        - start_date: string in format 'YYYY-MM'
        - end_date: string in format 'YYYY-MM' (optional)
        
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
        all_files = glob.glob(os.path.join(self.trades_dir, "ETHUSDT-trades-????-??.parquet"))
        
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
        - start_date: string in format 'YYYY-MM'
        - end_date: string in format 'YYYY-MM' (optional)
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

    def visualize_trades(self, df, timeframe='5m', price_col='price', save_path=None):
        """
        Visualize trade data with the specified timeframe
        
        Parameters:
        - df: DataFrame with trade data
        - timeframe: Timeframe for resampling (default: '5m')
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
    
    parser = argparse.ArgumentParser(description='Binance Trades Manager - Download and Analyze ETH/USDT Monthly Trade Data')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Download command
    download_parser = subparsers.add_parser('download', help='Download monthly trade data')
    download_parser.add_argument('--start_year', type=int, default=2025, help='Starting year (default: 2019)')
    download_parser.add_argument('--start_month', type=int, default=6, help='Starting month (default: 11)')
    download_parser.add_argument('--output_dir', type=str, help='Output directory (optional)')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List available monthly dates')
    list_parser.add_argument('--data_dir', type=str, help='Data directory (optional)')
    
    # Aggregate command
    aggregate_parser = subparsers.add_parser('aggregate', help='Aggregate monthly trade data')
    aggregate_parser.add_argument('start_date', type=str, help='Start date in format YYYY-MM')
    aggregate_parser.add_argument('--end_date', type=str, help='End date in format YYYY-MM (optional)')
    aggregate_parser.add_argument('--columns', type=str, nargs='+', help='Columns to load (optional)')
    aggregate_parser.add_argument('--sample_rate', type=float, help='Sample rate between 0 and 1 (optional)')
    aggregate_parser.add_argument('--output', type=str, help='Output file path (optional)')
    aggregate_parser.add_argument('--data_dir', type=str, help='Data directory (optional)')
    
    # Visualize command
    visualize_parser = subparsers.add_parser('visualize', help='Visualize monthly trade data')
    visualize_parser.add_argument('start_date', type=str, help='Start date in format YYYY-MM')
    visualize_parser.add_argument('--end_date', type=str, help='End date in format YYYY-MM (optional)')
    visualize_parser.add_argument('--timeframe', type=str, default='5m', help='Timeframe for resampling (default: 5m)')
    visualize_parser.add_argument('--sample_rate', type=float, default=0.1, help='Sample rate between 0 and 1 (default: 0.1)')
    visualize_parser.add_argument('--save', type=str, help='Path to save the figure (optional)')
    visualize_parser.add_argument('--data_dir', type=str, help='Data directory (optional)')
    
    args = parser.parse_args()
    
    if args.command == 'download':
        # Initialize manager with output directory if provided
        manager = BinanceTradesManager(args.output_dir if hasattr(args, 'output_dir') and args.output_dir else None)
        # Download trades
        manager.download_monthly_trades(args.start_year, args.start_month)
    
    elif args.command == 'list':
        # Initialize manager with data directory if provided
        manager = BinanceTradesManager(args.data_dir if hasattr(args, 'data_dir') and args.data_dir else None)
        
        # Get monthly dates
        monthly_dates = manager.get_monthly_dates()
        if monthly_dates:
            print(f"\nMonthly data files ({len(monthly_dates)}):")
            for date in monthly_dates:
                print(f"  - {date}")
            print(f"\nDate range: {monthly_dates[0]} to {monthly_dates[-1]}")
        else:
            print("No monthly data files found")
    
    elif args.command == 'aggregate':
        # Initialize manager with data directory if provided
        manager = BinanceTradesManager(args.data_dir if hasattr(args, 'data_dir') and args.data_dir else None)
        # Load data
        df = manager.load_trades(args.start_date, args.end_date, args.columns, args.sample_rate)
        
        if df is not None:
            print(f"\nLoaded DataFrame with {len(df):,} rows and {len(df.columns)} columns")
            
            # Display DataFrame info in a nicer format
            print("\nDataFrame Info:")
            buffer = io.StringIO()
            df.info(buf=buffer)
            print(buffer.getvalue())
            
            # Display DataFrame preview with tabulate
            print("\nDataFrame Preview:")
            print(tabulate(df.head(20), headers='keys', tablefmt='psql', showindex=True))
            
            # Display basic statistics
            print("\nDataFrame Statistics:")
            print(tabulate(df.describe(), headers='keys', tablefmt='psql', showindex=True))
            
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
    
    elif args.command == 'visualize':
        # Initialize manager with data directory if provided
        manager = BinanceTradesManager(args.data_dir if hasattr(args, 'data_dir') and args.data_dir else None)
        # Load data
        print(f"Loading data from {args.start_date} to {args.end_date or args.start_date} (sample rate: {args.sample_rate})")
        df = manager.load_trades(args.start_date, args.end_date, sample_rate=args.sample_rate)
        
        if df is not None:
            print(f"Visualizing {len(df):,} trades")
            manager.visualize_trades(df, timeframe=args.timeframe, save_path=args.save)
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 
import requests
import os
import time
from datetime import datetime
import zipfile
from tqdm import tqdm
import humanize
import pandas as pd
import glob
import shutil

# Base URL for Binance data
BASE_URL = "https://data.binance.vision/data/futures/um/monthly/trades/ETHUSDT"

# Output directory
OUTPUT_DIR = "/allah/data/trades"

def get_free_space(path):
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

def get_file_size(url):
    """
    Get file size from URL without downloading
    """
    try:
        response = requests.head(url)
        return int(response.headers.get('content-length', 0))
    except:
        return 0

def download_file(url, output_path):
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

def convert_csv_to_parquet(csv_path, parquet_path):
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

def get_existing_files(data_dir):
    """
    Get list of already processed files
    """
    existing_files = set()
    for file in glob.glob(os.path.join(data_dir, "*.parquet")):
        # Extract year and month from filename
        basename = os.path.basename(file)
        if basename.startswith("ETHUSDT-trades-"):
            year_month = basename.split("ETHUSDT-trades-")[1].split(".")[0]  # e.g., "2019-11"
            existing_files.add(year_month)
    return existing_files

def extract_and_convert(zip_path, extract_path):
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
                if convert_csv_to_parquet(csv_path, parquet_path):
                    success = True
                elif os.path.exists(csv_path):
                    os.remove(csv_path)  # Clean up CSV if conversion failed
        return success
    except Exception as e:
        print(f"Error extracting zip: {e}")
        return False

def download_monthly_trades(start_year=2019, start_month=11):
    """
    Download monthly ETH/USDT perpetual futures trade data from Binance
    
    Args:
        start_year (int): Starting year (default: 2019)
        start_month (int): Starting month (default: 11)
    """
    # Create or use existing output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Find most recent data directory or create new one
    existing_dirs = glob.glob(os.path.join(OUTPUT_DIR, "eth_usdt_monthly_trades_*"))
    if existing_dirs:
        data_dir = max(existing_dirs)  # Use the most recent directory
        print(f"Using existing directory: {data_dir}")
    else:
        data_dir = os.path.join(OUTPUT_DIR, f"eth_usdt_monthly_trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        os.makedirs(data_dir, exist_ok=True)
        print(f"Created new directory: {data_dir}")
    
    # Get list of already processed files
    existing_files = get_existing_files(data_dir)
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
            parquet_path = os.path.join(data_dir, parquet_filename)
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
        zip_path = os.path.join(data_dir, zip_filename)
        
        try:
            print(f"\nProcessing file {idx}/{total_files}: {zip_filename}")
            
            # Get and show file size
            file_size = get_file_size(zip_url)
            if file_size == 0:
                print(f"Skipping {zip_filename} - file not available or empty")
                continue
            
            print(f"File size: {humanize.naturalsize(file_size)}")
            
            # Check available disk space
            free_space = get_free_space(data_dir)
            required_space = file_size * 2  # Need roughly 2x zip size for extraction
            
            if required_space > free_space:
                print(f"Warning: Not enough disk space!")
                print(f"Required: {humanize.naturalsize(required_space)}")
                print(f"Available: {humanize.naturalsize(free_space)}")
                print("Please free up some space and try again.")
                break
            
            # Download file
            print(f"Downloading {zip_filename}...")
            download_file(zip_url, zip_path)
            
            # Extract, convert to parquet, and clean up
            print(f"Processing {zip_filename}...")
            if extract_and_convert(zip_path, data_dir):
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
    
    print(f"\nDownload completed! Data saved to: {data_dir}")
    
    # Show final statistics
    final_files = get_existing_files(data_dir)
    print(f"Total files processed this run: {processed_count}")
    print(f"Total files in directory: {len(final_files)}")
    if final_files:  # Only show date range if there are files
        print("Date range:", min(final_files), "to", max(final_files))

if __name__ == "__main__":
    # Download all available monthly trade data
    download_monthly_trades(start_year=2019, start_month=11)

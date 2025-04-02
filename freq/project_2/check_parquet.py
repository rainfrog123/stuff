#!/usr/bin/env python3
import pandas as pd
import glob
import os

# Find parquet files
files = glob.glob('/allah/data/trades/eth_usdt_daily_trades/*.parquet')
print(f'Found {len(files)} parquet files')

if files:
    # Read the first file
    file_path = files[0]
    df = pd.read_parquet(file_path)
    
    print(f'Parquet file: {os.path.basename(file_path)}')
    print(f'Shape: {df.shape}')
    print(f'Columns: {df.columns.tolist()}')
    print('Sample data:')
    print(df.head(3))
    print('Data types:')
    print(df.dtypes)
else:
    print("No parquet files found in the directory") 
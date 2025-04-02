#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TEMA-50 Reversal ETH/USDT Data Export
-------------------------------------
Export labeled ETH/USDT data in multiple formats for easy loading into dataframes
"""

import pandas as pd
import numpy as np
import os
import pickle

def export_data_in_multiple_formats():
    """
    Load the labeled ETH/USDT data and export in multiple formats
    """
    # Load the labeled data
    data_file = 'labeled_data/labeled_ETH_USDT_USDT-5s-futures.csv'
    print(f"Loading data from {data_file}...")
    df = pd.read_csv(data_file)
    
    # Create output directory if it doesn't exist
    output_dir = 'labeled_data/ethusdt_export'
    os.makedirs(output_dir, exist_ok=True)
    
    # Filter out rows with label=0 (unlabeled)
    df_clean = df[df['label'] != 0].copy()
    
    # Create binary labels for ML
    df_clean['binary_label'] = df_clean['label'].apply(lambda x: 1 if x == 1 or x == -1 else 0)
    df_clean['is_long'] = df_clean['label'].apply(lambda x: 1 if x > 0 else 0)
    
    # Create a clean version with only essential columns
    essential_cols = [
        'open', 'high', 'low', 'close', 'volume', 
        'tema', 'atr', 'trend', 'tema_distance', 'atr_percent',
        'binary_label', 'label', 'is_long'
    ]
    df_essential = df_clean[essential_cols].copy()
    
    # Export in CSV format
    csv_path = os.path.join(output_dir, 'ethusdt_tema_labeled.csv')
    df_essential.to_csv(csv_path, index=False)
    print(f"Saved CSV to {csv_path}")
    
    # Export in Parquet format
    parquet_path = os.path.join(output_dir, 'ethusdt_tema_labeled.parquet')
    df_essential.to_parquet(parquet_path, index=False)
    print(f"Saved Parquet to {parquet_path}")
    
    # Export in feather format
    feather_path = os.path.join(output_dir, 'ethusdt_tema_labeled.feather')
    df_essential.to_feather(feather_path)
    print(f"Saved Feather to {feather_path}")
    
    # Export in pickle format
    pickle_path = os.path.join(output_dir, 'ethusdt_tema_labeled.pkl')
    with open(pickle_path, 'wb') as f:
        pickle.dump(df_essential, f)
    print(f"Saved Pickle to {pickle_path}")
    
    # Export in HDF5 format
    h5_path = os.path.join(output_dir, 'ethusdt_tema_labeled.h5')
    df_essential.to_hdf(h5_path, key='data', mode='w')
    print(f"Saved HDF5 to {h5_path}")
    
    # Export for TensorFlow/PyTorch use
    # Create X (features) and y (target) numpy arrays
    X = df_essential.drop(['binary_label', 'label', 'is_long'], axis=1).values
    y = df_essential['binary_label'].values
    y_multi = df_essential['label'].values
    
    np_path = os.path.join(output_dir, 'ethusdt_tema_arrays.npz')
    np.savez(np_path, X=X, y_binary=y, y_multi=y_multi)
    print(f"Saved NumPy arrays to {np_path}")
    
    # Print data summary
    print("\nData Summary:")
    print(f"Total samples: {len(df_essential)}")
    print("Label distribution:")
    print(df_essential['label'].value_counts())
    print("\nBinary label distribution:")
    print(df_essential['binary_label'].value_counts())
    
    # Create a small demo file with sample data
    df_sample = df_essential.sample(n=1000, random_state=42)
    sample_path = os.path.join(output_dir, 'ethusdt_tema_sample.csv')
    df_sample.to_csv(sample_path, index=False)
    print(f"\nSaved sample dataset (1000 rows) to {sample_path}")
    
    # Print loading instructions
    print("\nTo load the data in Python:")
    print("```python")
    print("# CSV")
    print("import pandas as pd")
    print("df = pd.read_csv('labeled_data/ethusdt_export/ethusdt_tema_labeled.csv')")
    print("\n# Parquet")
    print("df = pd.read_parquet('labeled_data/ethusdt_export/ethusdt_tema_labeled.parquet')")
    print("\n# Feather")
    print("df = pd.read_feather('labeled_data/ethusdt_export/ethusdt_tema_labeled.feather')")
    print("\n# Pickle")
    print("import pickle")
    print("with open('labeled_data/ethusdt_export/ethusdt_tema_labeled.pkl', 'rb') as f:")
    print("    df = pickle.load(f)")
    print("\n# HDF5")
    print("df = pd.read_hdf('labeled_data/ethusdt_export/ethusdt_tema_labeled.h5', key='data')")
    print("\n# NumPy Arrays")
    print("import numpy as np")
    print("data = np.load('labeled_data/ethusdt_export/ethusdt_tema_arrays.npz')")
    print("X, y_binary, y_multi = data['X'], data['y_binary'], data['y_multi']")
    print("```")

if __name__ == "__main__":
    export_data_in_multiple_formats() 
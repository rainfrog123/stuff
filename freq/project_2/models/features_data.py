    #!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LSTM Data Features Engineering
-----------------------------
This script processes the labeled ETH_USDT 5-second timeframe data to create features for LSTM models,
prepare sequences, normalize data, and save the processed dataset.
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from typing import Tuple, List, Dict, Union, Optional
import os
from pathlib import Path
import json
import time
from tqdm import tqdm


def load_labeled_data(file_path: str) -> pd.DataFrame:
    """
    Load the labeled parquet file
    
    Args:
        file_path: Path to the labeled parquet file
        
    Returns:
        DataFrame with labeled data
    """
    print(f"Loading data from: {file_path}")
    df = pd.read_parquet(file_path)
    print(f"Loaded dataframe with shape: {df.shape}")
    
    # Print basic information
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"Columns: {df.columns.tolist()}")
    
    # Print label distribution
    label_counts = df['label'].value_counts().sort_index()
    print("\nOriginal label distribution:")
    print(label_counts)
    print("\nOriginal label meanings:")
    print("1: Profitable long trades (hit take profit)")
    print("2: Unprofitable long trades (hit stop loss)")
    print("-1: Profitable short trades (hit take profit)")
    print("-2: Unprofitable short trades (hit stop loss)")
    print("0: No trade signal or unlabeled data")
    
    # Create a binary profitability label
    # Initialize with 0 (no signal)
    df['binary_label'] = 0
    
    # Set profitable trades (1, -1) to 1
    df.loc[df['label'].isin([1, -1]), 'binary_label'] = 1
    
    # Set unprofitable trades (2, -2) to -1
    df.loc[df['label'].isin([2, -2]), 'binary_label'] = -1
    
    # Create direction from original labels
    df['direction'] = 0  # Default neutral
    df.loc[df['label'] > 0, 'direction'] = 1  # Long signals
    df.loc[df['label'] < 0, 'direction'] = -1  # Short signals
    
    # Count the binary labels
    binary_counts = df['binary_label'].value_counts().sort_index()
    print("\nBinary label distribution:")
    print("-1 = Unprofitable (hit stop loss)")
    print("0 = No trade signal")
    print("1 = Profitable (hit take profit)")
    print(binary_counts)
    
    # Direction counts
    direction_counts = df[df['binary_label'] != 0]['direction'].value_counts().sort_index()
    print("\nDirection distribution for trades (-1=short, 1=long):")
    print(direction_counts)
    
    return df


def prepare_lstm_sequences(df: pd.DataFrame, 
                          sequence_length: int = 60,
                          feature_columns: Optional[List[str]] = None,
                          target_column: str = 'binary_label',
                          normalize: bool = True) -> Tuple[np.ndarray, np.ndarray, dict]:
    """
    Prepare sequences for LSTM training
    
    Args:
        df: DataFrame with features and labels
        sequence_length: Length of each sequence
        feature_columns: List of feature column names to include
        target_column: Name of the target column (defaults to binary_label)
        normalize: Whether to normalize features
        
    Returns:
        Tuple of (X_sequences, y_values, scaler_dict)
    """
    # Make a copy to avoid modifying the original
    working_df = df.copy()
    
    # Default feature columns if not specified
    if feature_columns is None:
        # Exclude date, target columns, and non-numeric columns
        exclude_cols = ['date', target_column, 'label']
        feature_columns = [col for col in working_df.columns 
                         if col not in exclude_cols 
                         and pd.api.types.is_numeric_dtype(working_df[col])]
    
    print(f"Using {len(feature_columns)} feature columns: {feature_columns}")
    
    # Fill NaN values in features
    for col in feature_columns:
        working_df[col] = working_df[col].fillna(0)
    
    # Apply log transformation to volume before normalization
    if 'volume' in feature_columns:
        print("Applying log transformation to volume data")
        working_df['volume'] = np.log1p(working_df['volume'])  # log(volume + 1)
    
    # Normalize features if requested
    scaler_dict = {}
    if normalize:
        print("Normalizing features...")
        for col in tqdm(feature_columns):
            scaler = MinMaxScaler(feature_range=(-1, 1))
            working_df[col] = scaler.fit_transform(working_df[col].values.reshape(-1, 1))
            scaler_dict[col] = scaler
    
    # Find rows with binary_label of 1 or -1 (profitable or unprofitable trades)
    valid_indices = working_df[working_df[target_column].isin([1, -1])].index
    print(f"Found {len(valid_indices)} valid target rows (binary_label = 1 or -1)")
    
    # Create sequences
    X_sequences = []
    y_values = []
    skipped = 0
    
    print(f"Creating sequences for trades...")
    
    # For each valid target row, create a sequence
    for idx in tqdm(valid_indices):
        # Check if we have enough prior data points to form a sequence
        if idx < sequence_length - 1:
            skipped += 1
            continue
            
        # Get sequence of features including the labeled row itself
        start_idx = idx - (sequence_length - 1)
        
        # Make a copy of the sequence
        X_seq_df = working_df.iloc[start_idx:(idx+1)][feature_columns].copy()
        
        # If 'direction' is in the feature columns, make it static for the entire sequence
        # by setting all values to the direction of the entry point (the target row)
        if 'direction' in feature_columns:
            entry_direction = working_df.loc[idx, 'direction']
            X_seq_df['direction'] = entry_direction
            
        # Convert to numpy array

        X_seq = X_seq_df.values
        
        # Get target value from the labeled row
        y_val = working_df.loc[idx, target_column]
        
        X_sequences.append(X_seq)
        y_values.append(y_val)
    
    print(f"Skipped {skipped} sequences due to insufficient prior data")
    print(f"Created {len(X_sequences)} valid sequences")
    
    return np.array(X_sequences), np.array(y_values), scaler_dict


def add_custom_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add custom features to the DataFrame
    
    Args:
        df: DataFrame with OHLCV data (5-second timeframe)
        
    Returns:
        DataFrame with added features
    """
    # This is where you can customize your features
    result_df = df.copy()
    
    # -- ADD ONLY RSI_14 INDICATOR --
    
    # 1. Calculate RSI (Relative Strength Index)
    # First, calculate price changes
    delta = result_df['close'].diff()
    
    # Separate gains and losses
    gain = delta.copy()
    loss = delta.copy()
    gain[gain < 0] = 0
    loss[loss > 0] = 0
    loss = abs(loss)
    
    # Define the RSI period
    period = 14  # Using only RSI-14
    
    # Calculate the average gain and loss over the period
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    # Calculate the Relative Strength (RS)
    rs = avg_gain / avg_loss
    
    # Calculate the RSI
    result_df['rsi_14'] = 100 - (100 / (1 + rs))
    
    # Note: We're using raw volume directly instead of VWAP
    # Volume is already in the original dataframe, so no calculation needed
    
    # Print the list of added features
    original_columns = set(df.columns)
    new_columns = set(result_df.columns) - original_columns
    print(f"Added {len(new_columns)} custom features: {list(new_columns)}")
    
    return result_df


def save_processed_data(X: np.ndarray, y: np.ndarray, 
                       scaler_dict: dict,
                       feature_columns: List[str],
                       output_dir: str,
                       file_prefix: str = "lstm_data") -> None:
    """
    Save processed data and metadata
    
    Args:
        X: Sequence data
        y: Target values
        scaler_dict: Dictionary of feature scalers
        feature_columns: List of feature column names
        output_dir: Directory to save files
        file_prefix: Prefix for output files
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Save X and y as numpy arrays
    np.save(os.path.join(output_dir, f"{file_prefix}_X.npy"), X)
    np.save(os.path.join(output_dir, f"{file_prefix}_y.npy"), y)
    
    # Save feature columns list
    with open(os.path.join(output_dir, f"{file_prefix}_features.txt"), 'w') as f:
        for col in feature_columns:
            f.write(f"{col}\n")
    
    # Convert numpy values to Python native types for class distribution
    unique_classes, counts = np.unique(y, return_counts=True)
    class_distribution = {str(int(cls)): int(count) for cls, count in zip(unique_classes, counts)}
    
    # Save dataset metadata
    metadata = {
        'X_shape': tuple(int(x) for x in X.shape),
        'y_shape': tuple(int(x) for x in y.shape),
        'sequence_length': int(X.shape[1]),
        'num_features': int(X.shape[2]),
        'feature_columns': feature_columns,
        'class_distribution': class_distribution
    }
    
    # Save metadata as JSON instead of parquet
    with open(os.path.join(output_dir, f"{file_prefix}_metadata.json"), 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Saved processed data to {output_dir}")
    print(f"X shape: {X.shape}, y shape: {y.shape}")


def main():
    # Configuration - MODIFY THESE VALUES AS NEEDED
    input_file = "labeled_ETH_USDT_USDT-5s-futures_r1_05.parquet"
    output_dir = "./lstm_data"
    sequence_length = 120  # 10-minute sequence (120 steps at 5s interval)
    
    # Load data - returns the full dataset including NaN values
    df = load_labeled_data(input_file)
    
    # Add custom features - now only RSI_14
    df_with_features = add_custom_features(df)
    
    # Define feature columns - SIMPLIFIED TO ONLY RSI_14, VOLUME, AND DIRECTION
    feature_columns = [
        # Direction as a static feature (long/short)
        'direction',
        
        # RSI indicator (dynamic feature)
        'rsi_14',
        
        # Volume (dynamic feature)
        'volume'
    ]
    
    # Remove any features that don't exist in the dataframe
    feature_columns = [col for col in feature_columns if col in df_with_features.columns]
    
    # Prepare sequences - use only -1 and 1 binary_label values
    X, y, scaler_dict = prepare_lstm_sequences(
        df_with_features, 
        sequence_length=sequence_length,
        feature_columns=feature_columns,
        target_column='binary_label',  # Using binary label (-1=unprofitable, 1=profitable)
        normalize=True
    )
    
    # Print the class distribution
    unique_classes, counts = np.unique(y, return_counts=True)
    print(f"Class distribution: {dict(zip(unique_classes, counts))}")
    
    # Save processed data
    save_processed_data(
        X, 
        y, 
        scaler_dict,
        feature_columns,
        output_dir,
        file_prefix="trade_outcome_data"  # Better name for binary classification
    )
    
    # Save the full processed DataFrame as parquet (for reference)
    processed_df_path = os.path.join(output_dir, "processed_trade_features.parquet")
    df_with_features.to_parquet(processed_df_path)
    print(f"Saved processed features dataframe to {processed_df_path}")


if __name__ == "__main__":
    main()

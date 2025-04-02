#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TEMA-50 Reversal Strategy with ATR-based Dynamic Labeling
---------------------------------------------------------
This script implements a dynamic ATR-based labeling method for the TEMA-50 reversal strategy.
The labeling approach creates realistic labels for trade entries based on market volatility.
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Tuple, List, Dict, Union, Optional
from pathlib import Path


def calculate_tema(series: pd.Series, period: int = 50) -> pd.Series:
    """
    Calculate Triple Exponential Moving Average (TEMA)
    
    Args:
        series: Price data series
        period: TEMA period
        
    Returns:
        TEMA values as pandas Series
    """
    ema1 = series.ewm(span=period, adjust=False).mean()
    ema2 = ema1.ewm(span=period, adjust=False).mean()
    ema3 = ema2.ewm(span=period, adjust=False).mean()
    tema = 3 * ema1 - 3 * ema2 + ema3
    return tema


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculate Average True Range (ATR)
    
    Args:
        df: DataFrame with 'high', 'low', and 'close' columns
        period: ATR period
        
    Returns:
        ATR values as pandas Series
    """
    high = df['high']
    low = df['low']
    close = df['close'].shift(1)
    
    tr1 = high - low
    tr2 = abs(high - close)
    tr3 = abs(low - close)
    
    tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    return atr


def identify_tema_reversal_entries(df: pd.DataFrame, tema_period: int = 50) -> pd.DataFrame:
    """
    Identify potential entry points based on TEMA-50 reversal strategy
    Based on the TradingView script logic of trend changes
    
    Args:
        df: DataFrame with OHLCV data
        tema_period: Period for TEMA calculation
        
    Returns:
        DataFrame with entry signals
    """
    # Create a copy of the dataframe to avoid modifying the original
    result_df = df.copy()

    # Calculate TEMA
    result_df['tema'] = calculate_tema(result_df['close'], tema_period)
    
    # Initialize trend direction
    result_df['trend'] = pd.Series(np.nan, index=result_df.index).astype('object')
    
    # Determine trend based on TEMA direction (same as TradingView script)
    result_df['tema_diff'] = result_df['tema'] - result_df['tema'].shift(1)
    result_df.loc[result_df['tema_diff'] > 0, 'trend'] = 'UP'
    result_df.loc[result_df['tema_diff'] < 0, 'trend'] = 'DOWN'
    result_df.loc[result_df['tema_diff'] == 0, 'trend'] = 'STABLE'
    
    # Track trend changes
    result_df['prev_trend'] = result_df['trend'].shift(1)
    result_df['trend_change'] = result_df['trend'] != result_df['prev_trend']
    
    # Initialize entry signals
    result_df['long_entry'] = False
    result_df['short_entry'] = False
    
    # Identify trend reversals
    result_df.loc[(result_df['trend_change']) & (result_df['trend'] == 'UP'), 'long_entry'] = True
    result_df.loc[(result_df['trend_change']) & (result_df['trend'] == 'DOWN'), 'short_entry'] = True
    
    return result_df


def generate_atr_based_labels(df: pd.DataFrame, atr_multiplier_sl: float = 0.5, 
                             atr_multiplier_tp: float = 1.0, atr_period: int = 14) -> pd.DataFrame:
    """
    Generate labels for trade entries based on ATR-based stop loss and take profit levels
    Using 1:0.5 risk-reward ratio (0.5 ATR for stop loss, 1 ATR for take profit)
    
    Args:
        df: DataFrame with OHLCV data and entry signals
        atr_multiplier_sl: Multiplier for ATR to set stop loss (default: 0.5)
        atr_multiplier_tp: Multiplier for ATR to set take profit (default: 1.0)
        atr_period: Period for ATR calculation
        
    Returns:
        DataFrame with entry labels
    """
    # Create a copy of the dataframe to avoid modifying the original
    result_df = df.copy()
    
    # Calculate ATR
    result_df['atr'] = calculate_atr(result_df, atr_period)
    
    # Initialize label column
    result_df['label'] = 0  # 0 = no entry, 1 = profitable long, -1 = profitable short, 2 = unprofitable long, -2 = unprofitable short
    
    # Process each potential entry point
    for idx in result_df.index[atr_period:]:
        if result_df.at[idx, 'long_entry']:
            entry_price = result_df.at[idx, 'close']
            atr_value = result_df.at[idx, 'atr']
            
            # Set stop loss and take profit levels based on ATR
            stop_loss = entry_price - (atr_value * atr_multiplier_sl)
            take_profit = entry_price + (atr_value * atr_multiplier_tp)
            
            # Look ahead in the price data to see if TP or SL is hit first
            future_prices = result_df.loc[idx:, ['high', 'low']].iloc[1:]  # Skip the entry candle
            
            hit_tp = False
            hit_sl = False
            
            for future_idx, future_row in future_prices.iterrows():
                if future_row['high'] >= take_profit:
                    hit_tp = True
                    break
                elif future_row['low'] <= stop_loss:
                    hit_sl = True
                    break
            
            # Assign label based on outcome
            if hit_tp:
                result_df.at[idx, 'label'] = 1  # Profitable long
            elif hit_sl:
                result_df.at[idx, 'label'] = 2  # Unprofitable long
            # If neither TP nor SL is hit within the available data, leave as 0
        
        elif result_df.at[idx, 'short_entry']:
            entry_price = result_df.at[idx, 'close']
            atr_value = result_df.at[idx, 'atr']
            
            # Set stop loss and take profit levels based on ATR
            stop_loss = entry_price + (atr_value * atr_multiplier_sl)
            take_profit = entry_price - (atr_value * atr_multiplier_tp)
            
            # Look ahead in the price data to see if TP or SL is hit first
            future_prices = result_df.loc[idx:, ['high', 'low']].iloc[1:]  # Skip the entry candle
            
            hit_tp = False
            hit_sl = False
            
            for future_idx, future_row in future_prices.iterrows():
                if future_row['low'] <= take_profit:
                    hit_tp = True
                    break
                elif future_row['high'] >= stop_loss:
                    hit_sl = True
                    break
            
            # Assign label based on outcome
            if hit_tp:
                result_df.at[idx, 'label'] = -1  # Profitable short
            elif hit_sl:
                result_df.at[idx, 'label'] = -2  # Unprofitable short
            # If neither TP nor SL is hit within the available data, leave as 0
    
    return result_df


def visualize_labeled_entries(df: pd.DataFrame, window_size: int = 200) -> None:
    """
    Visualize a sample of labeled entries
    
    Args:
        df: DataFrame with price data, TEMA, entry signals, and labels
        window_size: Number of candles to display
    """
    # Find indices with entry signals
    long_entries = df[df['long_entry']].index
    short_entries = df[df['short_entry']].index
    
    if len(long_entries) == 0 and len(short_entries) == 0:
        print("No entry signals found")
        return
    
    # Select a random entry to visualize
    if len(long_entries) > 0:
        entry_idx = np.random.choice(long_entries)
        entry_type = 'long'
    else:
        entry_idx = np.random.choice(short_entries)
        entry_type = 'short'
    
    # Extract a window of data around the entry
    start_idx = max(0, entry_idx - window_size // 2)
    end_idx = min(len(df), entry_idx + window_size // 2)
    window_df = df.iloc[start_idx:end_idx].copy()
    
    # Get entry details
    entry_price = window_df.loc[entry_idx, 'close']
    atr_value = window_df.loc[entry_idx, 'atr']
    label = window_df.loc[entry_idx, 'label']
    
    # Calculate stop loss and take profit levels
    if entry_type == 'long':
        stop_loss = entry_price - (atr_value * 0.5)
        take_profit = entry_price + (atr_value * 1.0)
        label_txt = "Profitable" if label == 1 else "Unprofitable"
    else:
        stop_loss = entry_price + (atr_value * 0.5)
        take_profit = entry_price - (atr_value * 1.0)
        label_txt = "Profitable" if label == -1 else "Unprofitable"
    
    # Create the plot
    plt.figure(figsize=(14, 7))
    plt.title(f'{entry_type.capitalize()} Entry at {entry_idx} - {label_txt}')
    
    # Plot price and TEMA
    plt.plot(window_df.index, window_df['close'], label='Price')
    plt.plot(window_df.index, window_df['tema'], label='TEMA-50')
    
    # Highlight entry point
    plt.scatter(entry_idx, entry_price, color='g' if entry_type == 'long' else 'r', 
                s=100, label=f'{entry_type.capitalize()} Entry')
    
    # Draw stop loss and take profit levels
    plt.axhline(y=stop_loss, color='r', linestyle='--', label='Stop Loss')
    plt.axhline(y=take_profit, color='g', linestyle='--', label='Take Profit')
    
    plt.legend()
    plt.grid(True)
    plt.xlabel('Candle Index')
    plt.ylabel('Price')
    plt.show()


def save_labeled_data(df: pd.DataFrame, output_path: str) -> None:
    """
    Save labeled data to Parquet format (more efficient than CSV)
    
    Args:
        df: DataFrame with labels
        output_path: Base path to save the labeled data (without extension)
    """
    # Create a copy of the full dataset to preserve all rows
    output_df = df.copy()
    
    # Create additional features that might be useful for ML models
    output_df.loc[:, 'tema_distance'] = (output_df['close'] - output_df['tema']) / output_df['tema']
    output_df.loc[:, 'atr_percent'] = output_df['atr'] / output_df['close']
    
    # Make sure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Get base path without extension
    base_path = output_path.rsplit('.', 1)[0]
    
    # Save to Parquet (efficient columnar storage format)
    parquet_path = f"{base_path}.parquet"
    output_df.to_parquet(parquet_path, index=True)  # Keep the index to maintain timestamp order
    print(f"Saved full dataset with {len(output_df)} rows to {parquet_path}")
    
    # Filter only rows with entries for statistics
    entry_df = output_df[(output_df['long_entry']) | (output_df['short_entry'])].copy()
    
    # Print label statistics
    label_counts = entry_df['label'].value_counts()
    print("\nLabel distribution:")
    print(f"Profitable longs (1): {label_counts.get(1, 0)}")
    print(f"Unprofitable longs (2): {label_counts.get(2, 0)}")
    print(f"Profitable shorts (-1): {label_counts.get(-1, 0)}")
    print(f"Unprofitable shorts (-2): {label_counts.get(-2, 0)}")
    print(f"Unlabeled (0): {label_counts.get(0, 0)}")
    
    # Calculate profitability percentages
    total_longs = label_counts.get(1, 0) + label_counts.get(2, 0)
    total_shorts = label_counts.get(-1, 0) + label_counts.get(-2, 0)
    
    if total_longs > 0:
        long_win_rate = label_counts.get(1, 0) / total_longs * 100
        print(f"Long trade win rate: {long_win_rate:.2f}%")
    
    if total_shorts > 0:
        short_win_rate = label_counts.get(-1, 0) / total_shorts * 100
        print(f"Short trade win rate: {short_win_rate:.2f}%")
    
    if total_longs + total_shorts > 0:
        overall_win_rate = (label_counts.get(1, 0) + label_counts.get(-1, 0)) / (total_longs + total_shorts) * 100
        print(f"Overall win rate: {overall_win_rate:.2f}%")


def process_data_file(file_path: str, output_dir: str) -> None:
    """
    Process a single data file
    
    Args:
        file_path: Path to the data file
        output_dir: Directory to save the labeled data
    """
    print(f"Processing {file_path}...")
    
    # Load data
    if file_path.endswith('.feather'):
        df = pd.read_feather(file_path)
    elif file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    else:
        print(f"Unsupported file format: {file_path}")
        return
    
    # Make sure we have the required columns
    required_columns = ['open', 'high', 'low', 'close', 'volume']
    if not all(col in df.columns for col in required_columns):
        print(f"Missing required columns in {file_path}")
        return
    
    # Identify entry signals
    df = identify_tema_reversal_entries(df)
    
    # Generate labels
    labeled_df = generate_atr_based_labels(df, atr_multiplier_sl=0.5, atr_multiplier_tp=1.0)
    
    # Create output filename
    file_name = os.path.basename(file_path)
    base_name = file_name.split('.')[0]
    output_base = os.path.join(output_dir, f"labeled_{base_name}_r1_05")
    
    # Save labeled data (will save as both parquet and feather)
    save_labeled_data(labeled_df, output_base)
    
    # Print sample data
    print("\nSample of labeled entries:")
    sample_entries = labeled_df[(labeled_df['long_entry']) | (labeled_df['short_entry'])].head(5)
    if len(sample_entries) > 0:
        for idx, row in sample_entries.iterrows():
            entry_type = "LONG" if row['long_entry'] else "SHORT"
            label_desc = "PROFITABLE" if (row['label'] == 1 or row['label'] == -1) else "UNPROFITABLE"
            print(f"Entry {idx}: {entry_type}, Label: {row['label']} ({label_desc})")
            print(f"  Entry price: {row['close']:.2f}, ATR: {row['atr']:.2f}")
            if entry_type == "LONG":
                print(f"  SL: {row['close'] - 0.5*row['atr']:.2f}, TP: {row['close'] + row['atr']:.2f}")
            else:
                print(f"  SL: {row['close'] + 0.5*row['atr']:.2f}, TP: {row['close'] - row['atr']:.2f}")
            print("")
    else:
        print("No entries found in the sample.")
    
    # Visualize a few examples (optional - uncomment to enable)
    # visualize_labeled_entries(labeled_df)


def main():
    """
    Main function to process data files and generate labels
    """
    # Define data directory and output directory
    data_dir = "/allah/freqtrade/user_data/data/binance/futures"
    output_dir = "/allah/stuff/freq/project_2/labeled_data"
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Process ETH_USDT_USDT-5s-futures.feather file as requested
    target_file = os.path.join(data_dir, "ETH_USDT_USDT-5s-futures.feather")
    
    if os.path.exists(target_file):
        # Process for regular labeling
        process_data_file(target_file, output_dir)
    else:
        print(f"Error: Target file not found at {target_file}")
        
        # List available files in case the target file is missing
        print("\nAvailable files in the directory:")
        for file in os.listdir(data_dir):
            if file.endswith('.feather'):
                print(f"- {file}")


if __name__ == "__main__":
    main() 
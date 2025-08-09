# %% Block 1: Data Loading and Basic Exploration
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
from pathlib import Path
import talib as ta

# Load dataset
dataset_path = "TEMAReversal_MLStrategy_ml_dataset.feather"
summary_path = "TEMAReversal_MLStrategy_ml_dataset_summary.json"
df = pd.read_feather(dataset_path)
json_data = json.load(open(summary_path))

# Basic data exploration
print("Dataset Info:")
df.info()
print("\nDataset Statistics:")
print(df.describe())
print(f"\nDataset shape: {df.shape}")
print(f"Columns: {list(df.columns)}")

# Show sample row with all columns
with pd.option_context('display.max_columns', None):
    print("\nSample row (500):")
    display(df.iloc[[500]])

# %% Block 2: Feature Engineering with Side Column and Flipping
print("=== Feature Engineering for Unified Dataset ===")

# Base technical indicators first
print("Adding base technical indicators...")
df['EMA_20'] = ta.EMA(df['close'], timeperiod=20)
df['EMA_50'] = ta.EMA(df['close'], timeperiod=50)
df['RSI'] = ta.RSI(df['close'], timeperiod=14)
df['ATR'] = ta.ATR(df['high'], df['low'], df['close'], timeperiod=14)
df['MACD'], df['MACD_signal'], df['MACD_hist'] = ta.MACD(df['close'])
df['CCI'] = ta.CCI(df['high'], df['low'], df['close'], timeperiod=14)
df['BBANDS_upper'], df['BBANDS_middle'], df['BBANDS_lower'] = ta.BBANDS(df['close'])
df['OBV'] = ta.OBV(df['close'], df['volume'])

# === TREND FEATURES (趋势) - Will be flipped by side ===
df['ema_20_slope'] = df['EMA_20'].diff(5) / df['EMA_20'].shift(5)  # 5-period slope
df['ema_50_slope'] = df['EMA_50'].diff(10) / df['EMA_50'].shift(10)  # 10-period slope
df['roc_5'] = ta.ROC(df['close'], timeperiod=5)
df['roc_10'] = ta.ROC(df['close'], timeperiod=10)
df['price_vs_ema20'] = (df['close'] - df['EMA_20']) / df['ATR']
df['price_vs_ema50'] = (df['close'] - df['EMA_50']) / df['ATR']

# === MOMENTUM FEATURES (动量) - Will be flipped by side ===
df['rsi_centered'] = (df['RSI'] - 50) / 50  # Center around 0
df['cci_norm'] = df['CCI'] / 100
df['macd_norm'] = df['MACD'] / df['close']
df['price_momentum'] = df['close'].diff(3) / df['close'].shift(3)
df['price_acceleration'] = df['close'].diff().diff()
df['rsi_momentum'] = df['RSI'].diff(3)

# === VOLATILITY FEATURES (波动率) - NOT flipped ===
df['atr_ratio'] = df['ATR'] / df['close']
df['bb_width'] = (df['BBANDS_upper'] - df['BBANDS_lower']) / df['BBANDS_middle']
df['volatility_5'] = df['close'].rolling(5).std() / df['close']
df['high_low_range'] = (df['high'] - df['low']) / df['close']

# === STRUCTURE FEATURES (结构) - Will be flipped by side ===
df['higher_high'] = (df['high'] > df['high'].shift(1)).astype(int)
df['lower_low'] = (df['low'] < df['low'].shift(1)).astype(int)
df['close_vs_high'] = (df['close'] - df['high']) / df['ATR']
df['close_vs_low'] = (df['close'] - df['low']) / df['ATR']
df['body_size'] = (df['close'] - df['open']) / df['ATR']  # Candle body

# === ORDER FLOW FEATURES (订单流) - Will be flipped by side ===
df['volume_spike'] = df['volume'] / df['volume'].rolling(20).mean()
df['volume_trend'] = df['volume'].diff(3) / df['volume'].shift(3)
df['obv_momentum'] = df['OBV'].diff(5) / df['volume']
df['price_volume'] = df['price_momentum'] * df['volume_spike']

# === MULTI-TIMEFRAME FEATURES (多周期) - Will be flipped by side ===
df['ema_alignment'] = np.where(df['EMA_20'] > df['EMA_50'], 1, -1)
df['trend_strength'] = (df['EMA_20'] - df['EMA_50']) / df['ATR']
df['price_position'] = np.where(df['close'] > df['EMA_20'], 1, -1)

# Add side column for each row (for demonstration using profit_ratio)
# Replace with your actual signal logic: reversal_to_up/reversal_to_down
if 'profit_ratio' in df.columns:
    df['side'] = np.where(df['profit_ratio'] > 0, 1, 
                 np.where(df['profit_ratio'] < 0, -1, 0))
else:
    # Placeholder - replace with your actual reversal signals
    df['side'] = 0

# === FEATURE FLIPPING (关键：按方向统一特征) ===
print("Applying feature flipping based on side...")

# Define directional features that need flipping
directional_features = [
    # Trend features
    'ema_20_slope', 'ema_50_slope', 'roc_5', 'roc_10', 
    'price_vs_ema20', 'price_vs_ema50',
    # Momentum features  
    'rsi_centered', 'cci_norm', 'macd_norm', 'price_momentum',
    'price_acceleration', 'rsi_momentum',
    # Structure features
    'close_vs_high', 'close_vs_low', 'body_size',
    # Order flow features
    'volume_trend', 'obv_momentum', 'price_volume',
    # Multi-timeframe features
    'ema_alignment', 'trend_strength', 'price_position'
]

# Create flipped versions (norm_ prefix indicates flipped by side)
for feature in directional_features:
    df[f'norm_{feature}'] = df['side'] * df[feature]

# Non-directional features (keep as-is)
non_directional_features = [
    'atr_ratio', 'bb_width', 'volatility_5', 'high_low_range',
    'volume_spike', 'RSI', 'ATR'
]

print(f"\nFeature Engineering Complete!")
print(f"Dataset shape: {df.shape}")
print(f"Directional features (flipped): {len(directional_features)}")
print(f"Non-directional features: {len(non_directional_features)}")

# Show feature breakdown
flipped_features = [f'norm_{f}' for f in directional_features]
print(f"\nFlipped features: {flipped_features[:10]}...")
print(f"Non-directional: {non_directional_features}")

# Show rows with actual side values
side_rows = df[df['side'] != 0]
print(f"\nRows with side != 0: {len(side_rows)}")
if len(side_rows) > 0:
    print(f"Long (side=1): {sum(df['side'] == 1)}")
    print(f"Short (side=-1): {sum(df['side'] == -1)}")
    
    # Show sample of flipped features
    sample_cols = ['side'] + flipped_features[:5] + non_directional_features[:3]
    print(f"\nSample of flipped features:")
    with pd.option_context('display.max_columns', None):
        display(side_rows[sample_cols].head(3))

# %%

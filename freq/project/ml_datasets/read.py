# %%  
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
from pathlib import Path

# Set plotting style
plt.style.use('default')
sns.set_palette("husl")

# Load the dataset and summary
dataset_path = "TEMAReversal_MLStrategy_ml_dataset.feather"
summary_path = "TEMAReversal_MLStrategy_ml_dataset_summary.json"

# Load the main dataset
df = pd.read_feather(dataset_path)

# Load the summary
with open(summary_path, 'r') as f:
    summary = json.load(f)

print("Dataset loaded successfully!")
print(f"Dataset shape: {df.shape}")
print("\nSummary statistics:")
for key, value in summary.items():
    print(f"  {key}: {value}")

# %%
# Basic dataset exploration
print("Dataset Info:")
print(df.info())
print("\nFirst few rows:")
print(df.head())

print("\nColumn names:")
print(df.columns.tolist())

print("\nDataset statistics:")
print(df.describe())

# %%
# Analyze target variable (profit_ratio)
if 'profit_ratio' in df.columns:
    print("Profit Ratio Analysis:")
    print(f"Mean profit ratio: {df['profit_ratio'].mean():.6f}")
    print(f"Median profit ratio: {df['profit_ratio'].median():.6f}")
    print(f"Standard deviation: {df['profit_ratio'].std():.6f}")
    print(f"Min profit ratio: {df['profit_ratio'].min():.6f}")
    print(f"Max profit ratio: {df['profit_ratio'].max():.6f}")
    
    # Profit/Loss distribution
    profitable_trades = df[df['profit_ratio'] > 0]
    losing_trades = df[df['profit_ratio'] <= 0]
    
    print(f"\nTrade Distribution:")
    print(f"Profitable trades: {len(profitable_trades)} ({len(profitable_trades)/len(df)*100:.1f}%)")
    print(f"Losing trades: {len(losing_trades)} ({len(losing_trades)/len(df)*100:.1f}%)")
    
    plt.figure(figsize=(12, 4))
    
    plt.subplot(1, 2, 1)
    plt.hist(df['profit_ratio'], bins=30, alpha=0.7, edgecolor='black')
    plt.axvline(df['profit_ratio'].mean(), color='red', linestyle='--', label=f'Mean: {df["profit_ratio"].mean():.6f}')
    plt.axvline(0, color='black', linestyle='-', label='Break-even')
    plt.xlabel('Profit Ratio')
    plt.ylabel('Frequency')
    plt.title('Distribution of Profit Ratios')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.subplot(1, 2, 2)
    plt.boxplot(df['profit_ratio'])
    plt.ylabel('Profit Ratio')
    plt.title('Profit Ratio Box Plot')
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()

# %%
# Analyze time-based patterns
if 'date' in df.columns:
    df['date'] = pd.to_datetime(df['date'])
    df['hour'] = df['date'].dt.hour
    df['minute'] = df['date'].dt.minute
    
    print("Time-based Analysis:")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    
    # Plot profit over time
    plt.figure(figsize=(15, 8))
    
    plt.subplot(2, 2, 1)
    plt.plot(df['date'], df['profit_ratio'], marker='o', markersize=3, alpha=0.7)
    plt.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    plt.xlabel('Time')
    plt.ylabel('Profit Ratio')
    plt.title('Profit Ratio Over Time')
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    
    # Cumulative profit
    plt.subplot(2, 2, 2)
    cumulative_profit = df['profit_ratio'].cumsum()
    plt.plot(df['date'], cumulative_profit, marker='o', markersize=3)
    plt.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    plt.xlabel('Time')
    plt.ylabel('Cumulative Profit Ratio')
    plt.title('Cumulative Profit Over Time')
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    
    # Profit by hour
    if len(df['hour'].unique()) > 1:
        plt.subplot(2, 2, 3)
        hourly_profit = df.groupby('hour')['profit_ratio'].mean()
        plt.bar(hourly_profit.index, hourly_profit.values, alpha=0.7)
        plt.axhline(y=0, color='black', linestyle='-', alpha=0.5)
        plt.xlabel('Hour')
        plt.ylabel('Average Profit Ratio')
        plt.title('Average Profit by Hour')
        plt.grid(True, alpha=0.3)
    
    # Trade count by hour
    plt.subplot(2, 2, 4)
    trade_counts = df.groupby('hour').size()
    plt.bar(trade_counts.index, trade_counts.values, alpha=0.7)
    plt.xlabel('Hour')
    plt.ylabel('Number of Trades')
    plt.title('Trade Count by Hour')
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()

# %%
# Feature analysis
feature_columns = [col for col in df.columns if col not in ['date', 'profit_ratio', 'pair']]

if feature_columns:
    print(f"Feature Analysis ({len(feature_columns)} features):")
    print("Feature columns:", feature_columns)
    
    # Correlation with target
    if 'profit_ratio' in df.columns:
        correlations = df[feature_columns + ['profit_ratio']].corr()['profit_ratio'].drop('profit_ratio')
        correlations = correlations.sort_values(key=abs, ascending=False)
        
        print(f"\nTop 10 features correlated with profit_ratio:")
        for feature, corr in correlations.head(10).items():
            print(f"  {feature}: {corr:.4f}")
        
        # Plot correlation heatmap for top features
        top_features = correlations.head(15).index.tolist() + ['profit_ratio']
        plt.figure(figsize=(12, 10))
        correlation_matrix = df[top_features].corr()
        sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', center=0, 
                   square=True, fmt='.3f', cbar_kws={'shrink': 0.8})
        plt.title('Feature Correlation Heatmap (Top 15 Features)')
        plt.tight_layout()
        plt.show()
    
    # Feature distributions
    if len(feature_columns) >= 4:
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        axes = axes.ravel()
        
        for i, feature in enumerate(feature_columns[:4]):
            axes[i].hist(df[feature].dropna(), bins=30, alpha=0.7, edgecolor='black')
            axes[i].set_xlabel(feature)
            axes[i].set_ylabel('Frequency')
            axes[i].set_title(f'Distribution of {feature}')
            axes[i].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()

# %%
# Feature importance analysis using correlation
if 'profit_ratio' in df.columns and feature_columns:
    # Create binary target for classification analysis
    df['profitable'] = (df['profit_ratio'] > 0).astype(int)
    
    print("Profitable vs Non-profitable Trade Analysis:")
    
    # Compare feature means between profitable and non-profitable trades
    profitable_mask = df['profitable'] == 1
    unprofitable_mask = df['profitable'] == 0
    
    feature_comparison = {}
    for feature in feature_columns[:10]:  # Analyze top 10 features
        if df[feature].dtype in ['int64', 'float64']:
            profitable_mean = df[profitable_mask][feature].mean()
            unprofitable_mean = df[unprofitable_mask][feature].mean()
            difference = profitable_mean - unprofitable_mean
            feature_comparison[feature] = {
                'profitable_mean': profitable_mean,
                'unprofitable_mean': unprofitable_mean,
                'difference': difference
            }
    
    # Display comparison
    print(f"\nFeature comparison (Profitable vs Unprofitable trades):")
    for feature, stats in feature_comparison.items():
        print(f"{feature}:")
        print(f"  Profitable trades mean: {stats['profitable_mean']:.6f}")
        print(f"  Unprofitable trades mean: {stats['unprofitable_mean']:.6f}")
        print(f"  Difference: {stats['difference']:.6f}")
        print()

# %%
# Summary statistics and insights
print("="*60)
print("ANALYSIS SUMMARY")
print("="*60)

print(f"Dataset Overview:")
print(f"  • Total trades: {len(df)}")
print(f"  • Features: {len(feature_columns)}")
print(f"  • Date range: {summary.get('date_range', 'N/A')}")

if 'profit_ratio' in df.columns:
    total_profit_pct = df['profit_ratio'].sum() * 100
    win_rate = (df['profit_ratio'] > 0).mean() * 100
    avg_win = df[df['profit_ratio'] > 0]['profit_ratio'].mean() * 100
    avg_loss = df[df['profit_ratio'] <= 0]['profit_ratio'].mean() * 100
    
    print(f"\nPerformance Metrics:")
    print(f"  • Total return: {total_profit_pct:.2f}%")
    print(f"  • Win rate: {win_rate:.1f}%")
    print(f"  • Average win: {avg_win:.2f}%")
    print(f"  • Average loss: {avg_loss:.2f}%")
    print(f"  • Risk-reward ratio: {abs(avg_win/avg_loss):.2f}" if avg_loss != 0 else "  • Risk-reward ratio: N/A")
    
    # Sharpe-like ratio (simplified)
    if df['profit_ratio'].std() != 0:
        sharpe_like = df['profit_ratio'].mean() / df['profit_ratio'].std()
        print(f"  • Return/Volatility ratio: {sharpe_like:.3f}")

print(f"\nData Quality:")
print(f"  • Missing values: {df.isnull().sum().sum()}")
print(f"  • Duplicate rows: {df.duplicated().sum()}")

# %%

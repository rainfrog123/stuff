"""
ML Dataset Analysis Script
==========================

This script performs comprehensive analysis of ML trading strategy datasets,
including data exploration, visualization, and performance metrics calculation.

Author: Trading Strategy Analysis
"""

# %%
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# Configure plotting style
plt.style.use('default')
sns.set_palette("husl")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10


def load_dataset(dataset_path: str, summary_path: str) -> Tuple[pd.DataFrame, Dict]:
    """
    Load the ML dataset and its summary statistics.
    
    Args:
        dataset_path: Path to the feather dataset file
        summary_path: Path to the JSON summary file
        
    Returns:
        Tuple of (dataframe, summary_dict)
    """
    # Load the main dataset
    df = pd.read_feather(dataset_path)
    
    # Load the summary
    with open(summary_path, 'r') as f:
        summary = json.load(f)
    
    return df, summary


def print_basic_info(df: pd.DataFrame, summary: Dict) -> None:
    """Print basic dataset information and summary statistics."""
    print("=" * 60)
    print("DATASET LOADED SUCCESSFULLY")
    print("=" * 60)
    print(f"Dataset shape: {df.shape}")
    print("\nSummary statistics:")
    for key, value in summary.items():
        print(f"  {key}: {value}")


def explore_dataset_structure(df: pd.DataFrame) -> None:
    """Perform basic dataset exploration and display structure information."""
    print("\n" + "=" * 60)
    print("DATASET STRUCTURE ANALYSIS")
    print("=" * 60)
    
    print("Dataset Info:")
    print(df.info())
    
    print("\nFirst few rows:")
    print(df.head())
    
    print("\nColumn names:")
    print(df.columns.tolist())
    
    print("\nDataset statistics:")
    print(df.describe())


# Load dataset
dataset_path = "TEMAReversal_MLStrategy_ml_dataset.feather"
summary_path = "TEMAReversal_MLStrategy_ml_dataset_summary.json"

df, summary = load_dataset(dataset_path, summary_path)
print_basic_info(df, summary)

# %%
explore_dataset_structure(df)

# %%
def analyze_profit_ratio(df: pd.DataFrame) -> None:
    """
    Analyze the profit_ratio column and create visualizations.
    
    Args:
        df: DataFrame containing profit_ratio column
    """
    if 'profit_ratio' not in df.columns:
        print("Warning: profit_ratio column not found in dataset")
        return
    
    print("\n" + "=" * 60)
    print("PROFIT RATIO ANALYSIS")
    print("=" * 60)
    
    # Basic statistics
    profit_stats = {
        'mean': df['profit_ratio'].mean(),
        'median': df['profit_ratio'].median(),
        'std': df['profit_ratio'].std(),
        'min': df['profit_ratio'].min(),
        'max': df['profit_ratio'].max()
    }
    
    print("Profit Ratio Statistics:")
    for stat_name, value in profit_stats.items():
        print(f"  {stat_name.capitalize()}: {value:.6f}")
    
    # Trade distribution analysis
    profitable_trades = df[df['profit_ratio'] > 0]
    losing_trades = df[df['profit_ratio'] <= 0]
    
    total_trades = len(df)
    profitable_count = len(profitable_trades)
    losing_count = len(losing_trades)
    
    print(f"\nTrade Distribution:")
    print(f"  Profitable trades: {profitable_count} ({profitable_count/total_trades*100:.1f}%)")
    print(f"  Losing trades: {losing_count} ({losing_count/total_trades*100:.1f}%)")
    
    # Create visualization
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Histogram
    ax1.hist(df['profit_ratio'], bins=30, alpha=0.7, edgecolor='black', color='skyblue')
    ax1.axvline(profit_stats['mean'], color='red', linestyle='--', 
                label=f'Mean: {profit_stats["mean"]:.6f}')
    ax1.axvline(0, color='black', linestyle='-', label='Break-even', linewidth=2)
    ax1.set_xlabel('Profit Ratio')
    ax1.set_ylabel('Frequency')
    ax1.set_title('Distribution of Profit Ratios')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Box plot
    ax2.boxplot(df['profit_ratio'], patch_artist=True, 
                boxprops=dict(facecolor='lightblue', alpha=0.7))
    ax2.set_ylabel('Profit Ratio')
    ax2.set_title('Profit Ratio Box Plot')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()


analyze_profit_ratio(df)

# %%
def analyze_time_patterns(df: pd.DataFrame) -> None:
    """
    Analyze time-based patterns in trading data.
    
    Args:
        df: DataFrame containing date and profit_ratio columns
    """
    if 'date' not in df.columns:
        print("Warning: date column not found in dataset")
        return
    
    print("\n" + "=" * 60)
    print("TIME-BASED PATTERN ANALYSIS")
    print("=" * 60)
    
    # Convert date column and extract time components
    df_time = df.copy()
    df_time['date'] = pd.to_datetime(df_time['date'])
    df_time['hour'] = df_time['date'].dt.hour
    df_time['minute'] = df_time['date'].dt.minute
    df_time['day_of_week'] = df_time['date'].dt.day_name()
    
    print(f"Date range: {df_time['date'].min()} to {df_time['date'].max()}")
    print(f"Total time span: {(df_time['date'].max() - df_time['date'].min()).days} days")
    
    # Create comprehensive time analysis plots
    fig = plt.figure(figsize=(16, 12))
    
    # 1. Profit ratio over time
    ax1 = plt.subplot(2, 3, 1)
    plt.plot(df_time['date'], df_time['profit_ratio'], 
             marker='o', markersize=2, alpha=0.7, linewidth=1, color='blue')
    plt.axhline(y=0, color='black', linestyle='-', alpha=0.5, linewidth=2)
    plt.xlabel('Date')
    plt.ylabel('Profit Ratio')
    plt.title('Profit Ratio Over Time')
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    
    # 2. Cumulative profit
    ax2 = plt.subplot(2, 3, 2)
    cumulative_profit = df_time['profit_ratio'].cumsum()
    plt.plot(df_time['date'], cumulative_profit, 
             marker='o', markersize=2, linewidth=2, color='green')
    plt.axhline(y=0, color='black', linestyle='-', alpha=0.5, linewidth=2)
    plt.xlabel('Date')
    plt.ylabel('Cumulative Profit Ratio')
    plt.title('Cumulative Profit Over Time')
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    
    # 3. Profit by hour (if multiple hours exist)
    if len(df_time['hour'].unique()) > 1:
        ax3 = plt.subplot(2, 3, 3)
        hourly_profit = df_time.groupby('hour')['profit_ratio'].mean()
        bars = plt.bar(hourly_profit.index, hourly_profit.values, 
                       alpha=0.7, color='orange', edgecolor='black')
        plt.axhline(y=0, color='black', linestyle='-', alpha=0.5, linewidth=2)
        plt.xlabel('Hour of Day')
        plt.ylabel('Average Profit Ratio')
        plt.title('Average Profit by Hour')
        plt.grid(True, alpha=0.3)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.4f}', ha='center', va='bottom', fontsize=8)
    
    # 4. Trade count by hour
    ax4 = plt.subplot(2, 3, 4)
    trade_counts = df_time.groupby('hour').size()
    bars = plt.bar(trade_counts.index, trade_counts.values, 
                   alpha=0.7, color='purple', edgecolor='black')
    plt.xlabel('Hour of Day')
    plt.ylabel('Number of Trades')
    plt.title('Trade Count by Hour')
    plt.grid(True, alpha=0.3)
    
    # 5. Profit by day of week
    ax5 = plt.subplot(2, 3, 5)
    daily_profit = df_time.groupby('day_of_week')['profit_ratio'].mean()
    # Reorder days properly
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    daily_profit = daily_profit.reindex([day for day in day_order if day in daily_profit.index])
    
    bars = plt.bar(range(len(daily_profit)), daily_profit.values, 
                   alpha=0.7, color='red', edgecolor='black')
    plt.axhline(y=0, color='black', linestyle='-', alpha=0.5, linewidth=2)
    plt.xlabel('Day of Week')
    plt.ylabel('Average Profit Ratio')
    plt.title('Average Profit by Day of Week')
    plt.xticks(range(len(daily_profit)), daily_profit.index, rotation=45)
    plt.grid(True, alpha=0.3)
    
    # 6. Trade count by day of week
    ax6 = plt.subplot(2, 3, 6)
    daily_counts = df_time.groupby('day_of_week').size()
    daily_counts = daily_counts.reindex([day for day in day_order if day in daily_counts.index])
    
    plt.bar(range(len(daily_counts)), daily_counts.values, 
            alpha=0.7, color='teal', edgecolor='black')
    plt.xlabel('Day of Week')
    plt.ylabel('Number of Trades')
    plt.title('Trade Count by Day of Week')
    plt.xticks(range(len(daily_counts)), daily_counts.index, rotation=45)
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()
    
    # Print summary statistics
    print(f"\nHourly Trading Summary:")
    print(f"  Most active hour: {trade_counts.idxmax()} ({trade_counts.max()} trades)")
    if len(df_time['hour'].unique()) > 1:
        best_hour = hourly_profit.idxmax()
        print(f"  Best performing hour: {best_hour} (avg profit: {hourly_profit[best_hour]:.6f})")


analyze_time_patterns(df)

# %%
def analyze_features(df: pd.DataFrame, max_features_to_show: int = 20) -> List[str]:
    """
    Analyze feature correlations and distributions.
    
    Args:
        df: DataFrame containing features and profit_ratio
        max_features_to_show: Maximum number of features to display in detail
        
    Returns:
        List of feature column names
    """
    # Identify feature columns (exclude non-feature columns)
    excluded_columns = ['date', 'profit_ratio', 'pair', 'hour', 'minute', 'day_of_week']
    feature_columns = [col for col in df.columns if col not in excluded_columns]
    
    if not feature_columns:
        print("Warning: No feature columns found in dataset")
        return []
    
    print("\n" + "=" * 60)
    print(f"FEATURE ANALYSIS ({len(feature_columns)} features)")
    print("=" * 60)
    
    print("Feature columns:")
    for i, col in enumerate(feature_columns[:max_features_to_show], 1):
        print(f"  {i:2d}. {col}")
    
    if len(feature_columns) > max_features_to_show:
        print(f"  ... and {len(feature_columns) - max_features_to_show} more features")
    
    # Correlation analysis with target
    if 'profit_ratio' in df.columns:
        print(f"\nCorrelation Analysis with Profit Ratio:")
        
        # Calculate correlations
        feature_data = df[feature_columns + ['profit_ratio']].select_dtypes(include=[np.number])
        correlations = feature_data.corr()['profit_ratio'].drop('profit_ratio')
        correlations = correlations.sort_values(key=abs, ascending=False)
        
        print(f"Top 10 features correlated with profit_ratio:")
        for i, (feature, corr) in enumerate(correlations.head(10).items(), 1):
            correlation_strength = "Strong" if abs(corr) > 0.5 else "Moderate" if abs(corr) > 0.3 else "Weak"
            print(f"  {i:2d}. {feature}: {corr:+.4f} ({correlation_strength})")
        
        # Create correlation heatmap for top features
        top_n = min(15, len(correlations))
        top_features = correlations.head(top_n).index.tolist() + ['profit_ratio']
        
        plt.figure(figsize=(14, 12))
        correlation_matrix = df[top_features].corr()
        
        # Create heatmap with better styling
        mask = np.triu(np.ones_like(correlation_matrix, dtype=bool))
        sns.heatmap(correlation_matrix, 
                   annot=True, 
                   cmap='RdBu_r', 
                   center=0,
                   square=True, 
                   fmt='.3f', 
                   cbar_kws={'shrink': 0.8, 'label': 'Correlation Coefficient'},
                   mask=mask,
                   linewidths=0.5)
        plt.title(f'Feature Correlation Heatmap (Top {top_n} Features + Target)', 
                 fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.show()
    
    # Feature distribution analysis
    if len(feature_columns) >= 4:
        print(f"\nFeature Distribution Analysis:")
        
        # Select first 6 features for distribution plots
        features_to_plot = feature_columns[:6]
        n_features = len(features_to_plot)
        
        # Calculate grid dimensions
        n_cols = 3
        n_rows = (n_features + n_cols - 1) // n_cols
        
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 5 * n_rows))
        if n_rows == 1:
            axes = axes.reshape(1, -1)
        
        for i, feature in enumerate(features_to_plot):
            row = i // n_cols
            col = i % n_cols
            ax = axes[row, col]
            
            # Plot histogram
            feature_data = df[feature].dropna()
            ax.hist(feature_data, bins=30, alpha=0.7, edgecolor='black', color='skyblue')
            ax.set_xlabel(feature)
            ax.set_ylabel('Frequency')
            ax.set_title(f'Distribution of {feature}')
            ax.grid(True, alpha=0.3)
            
            # Add statistics text
            stats_text = f'Mean: {feature_data.mean():.3f}\nStd: {feature_data.std():.3f}'
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                   verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        # Hide any unused subplots
        for i in range(n_features, n_rows * n_cols):
            row = i // n_cols
            col = i % n_cols
            axes[row, col].set_visible(False)
        
        plt.tight_layout()
        plt.show()
    
    return feature_columns


feature_columns = analyze_features(df)

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

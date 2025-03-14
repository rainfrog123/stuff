#!/usr/bin/env python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.ensemble import IsolationForest
from scipy import stats
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

class BinanceTradesAnalysis:
    """
    Advanced analysis features for Binance trade data including:
    - Outlier detection and filtering
    - Enhanced visualizations
    - Data preparation for machine learning
    """
    
    def __init__(self, df=None):
        """
        Initialize the analysis class
        
        Parameters:
        - df: pandas DataFrame with trade data (optional)
        """
        self.df = df
        self.outliers_mask = None
        self.scaled_data = None
    
    def set_data(self, df):
        """Set the DataFrame to analyze"""
        self.df = df
        self.outliers_mask = None
        self.scaled_data = None
    
    def detect_outliers(self, method='zscore', threshold=3.0, contamination=0.01):
        """
        Detect outliers in price and quantity data
        
        Parameters:
        - method: 'zscore', 'iqr', or 'isolation_forest'
        - threshold: threshold for z-score method
        - contamination: contamination parameter for isolation forest
        
        Returns:
        - DataFrame with outliers marked
        """
        if self.df is None:
            raise ValueError("No data available. Please set data using set_data() first.")
        
        # Create copy of DataFrame
        df = self.df.copy()
        
        if method == 'zscore':
            # Z-score method
            z_scores = stats.zscore(df[['price', 'qty']])
            self.outliers_mask = (abs(z_scores) > threshold).any(axis=1)
            
        elif method == 'iqr':
            # IQR method
            Q1 = df[['price', 'qty']].quantile(0.25)
            Q3 = df[['price', 'qty']].quantile(0.75)
            IQR = Q3 - Q1
            self.outliers_mask = ((df[['price', 'qty']] < (Q1 - 1.5 * IQR)) | 
                                (df[['price', 'qty']] > (Q3 + 1.5 * IQR))).any(axis=1)
            
        elif method == 'isolation_forest':
            # Isolation Forest method
            iso_forest = IsolationForest(contamination=contamination, random_state=42)
            self.outliers_mask = iso_forest.fit_predict(df[['price', 'qty']]) == -1
            
        else:
            raise ValueError(f"Unknown outlier detection method: {method}")
        
        # Add outlier column to DataFrame
        df['is_outlier'] = self.outliers_mask
        
        # Print summary
        n_outliers = self.outliers_mask.sum()
        print(f"\nOutlier Detection Summary ({method}):")
        print(f"Total samples: {len(df):,}")
        print(f"Outliers detected: {n_outliers:,} ({n_outliers/len(df)*100:.2f}%)")
        
        return df
    
    def remove_outliers(self):
        """Remove detected outliers from the DataFrame"""
        if self.outliers_mask is None:
            raise ValueError("No outliers detected. Run detect_outliers() first.")
        
        self.df = self.df[~self.outliers_mask].copy()
        print(f"\nRemoved {self.outliers_mask.sum():,} outliers.")
        return self.df
    
    def prepare_for_ml(self, features=None, target='price', scale_method='standard'):
        """
        Prepare data for machine learning
        
        Parameters:
        - features: List of feature columns (optional)
        - target: Target column name
        - scale_method: 'standard' or 'robust'
        
        Returns:
        - X: Feature matrix
        - y: Target vector
        """
        if self.df is None:
            raise ValueError("No data available. Please set data using set_data() first.")
        
        # Default features if none provided
        if features is None:
            features = ['qty', 'price']
        
        # Create feature matrix
        X = self.df[features].copy()
        
        # Add time-based features if datetime is available
        if 'datetime' in self.df.columns:
            X['hour'] = self.df['datetime'].dt.hour
            X['day_of_week'] = self.df['datetime'].dt.dayofweek
            X['day_of_month'] = self.df['datetime'].dt.day
            
        # Scale features
        if scale_method == 'standard':
            scaler = StandardScaler()
        elif scale_method == 'robust':
            scaler = RobustScaler()
        else:
            raise ValueError(f"Unknown scaling method: {scale_method}")
        
        self.scaled_data = scaler.fit_transform(X)
        
        # Create target vector
        y = self.df[target].values
        
        print("\nData Preparation Summary:")
        print(f"Features shape: {self.scaled_data.shape}")
        print(f"Target shape: {y.shape}")
        print("\nFeatures:")
        for i, feature in enumerate(X.columns):
            print(f"  - {feature}")
        
        return self.scaled_data, y
    
    def plot_interactive(self, timeframe='5min', plot_type='candlestick'):
        """
        Create interactive plots using Plotly
        
        Parameters:
        - timeframe: Timeframe for resampling
        - plot_type: 'candlestick' or 'ohlc'
        """
        if self.df is None:
            raise ValueError("No data available. Please set data using set_data() first.")
        
        # Ensure we have datetime index
        df = self.df.copy()
        if 'datetime' not in df.columns and 'time' in df.columns:
            df['datetime'] = pd.to_datetime(df['time'], unit='ms')
        
        # Set datetime as index
        df.set_index('datetime', inplace=True)
        
        # Resample data
        ohlc = df['price'].resample(timeframe).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last'
        })
        volume = df['qty'].resample(timeframe).sum()
        
        # Create subplots
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                          vertical_spacing=0.03, 
                          subplot_titles=('Price', 'Volume'),
                          row_heights=[0.7, 0.3])
        
        # Add price data
        if plot_type == 'candlestick':
            fig.add_trace(
                go.Candlestick(
                    x=ohlc.index,
                    open=ohlc['open'],
                    high=ohlc['high'],
                    low=ohlc['low'],
                    close=ohlc['close'],
                    name='OHLC'
                ),
                row=1, col=1
            )
        else:  # OHLC
            fig.add_trace(
                go.Ohlc(
                    x=ohlc.index,
                    open=ohlc['open'],
                    high=ohlc['high'],
                    low=ohlc['low'],
                    close=ohlc['close'],
                    name='OHLC'
                ),
                row=1, col=1
            )
        
        # Add volume bar chart
        fig.add_trace(
            go.Bar(
                x=volume.index,
                y=volume.values,
                name='Volume'
            ),
            row=2, col=1
        )
        
        # Update layout
        fig.update_layout(
            title='ETH/USDT Trading Data',
            yaxis_title='Price (USDT)',
            yaxis2_title='Volume',
            xaxis_rangeslider_visible=False
        )
        
        return fig
    
    def plot_analysis(self):
        """Create comprehensive analysis plots"""
        if self.df is None:
            raise ValueError("No data available. Please set data using set_data() first.")
        
        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Trade Data Analysis', fontsize=16)
        
        # 1. Price and Volume Over Time
        ax1 = axes[0, 0]
        ax1.plot(self.df['datetime'], self.df['price'], 'b-', alpha=0.6)
        ax1.set_title('Price Over Time')
        ax1.set_xlabel('Time')
        ax1.set_ylabel('Price (USDT)')
        ax1.grid(True)
        
        # 2. Volume Distribution
        ax2 = axes[0, 1]
        sns.histplot(data=self.df, x='qty', bins=50, ax=ax2)
        ax2.set_title('Volume Distribution')
        ax2.set_xlabel('Volume')
        ax2.set_ylabel('Count')
        
        # 3. Price Distribution
        ax3 = axes[1, 0]
        sns.histplot(data=self.df, x='price', bins=50, ax=ax3)
        ax3.set_title('Price Distribution')
        ax3.set_xlabel('Price')
        ax3.set_ylabel('Count')
        
        # 4. Price vs Volume Scatter
        ax4 = axes[1, 1]
        ax4.scatter(self.df['qty'], self.df['price'], alpha=0.1)
        ax4.set_title('Price vs Volume')
        ax4.set_xlabel('Volume')
        ax4.set_ylabel('Price')
        ax4.grid(True)
        
        plt.tight_layout()
        return fig
    
    def calculate_statistics(self):
        """Calculate advanced trading statistics"""
        if self.df is None:
            raise ValueError("No data available. Please set data using set_data() first.")
        
        stats_dict = {}
        
        # Basic statistics
        stats_dict['total_trades'] = len(self.df)
        stats_dict['total_volume'] = self.df['qty'].sum()
        stats_dict['total_value'] = (self.df['price'] * self.df['qty']).sum()
        
        # Price statistics
        stats_dict['price_mean'] = self.df['price'].mean()
        stats_dict['price_std'] = self.df['price'].std()
        stats_dict['price_min'] = self.df['price'].min()
        stats_dict['price_max'] = self.df['price'].max()
        
        # Volume statistics
        stats_dict['volume_mean'] = self.df['qty'].mean()
        stats_dict['volume_std'] = self.df['qty'].std()
        
        # Time-based statistics if datetime is available
        if 'datetime' in self.df.columns:
            stats_dict['time_span'] = self.df['datetime'].max() - self.df['datetime'].min()
            stats_dict['trades_per_day'] = len(self.df) / (stats_dict['time_span'].days + 1)
        
        # Format statistics for display
        print("\nTrading Statistics:")
        print("-" * 50)
        for key, value in stats_dict.items():
            if isinstance(value, float):
                print(f"{key.replace('_', ' ').title():25}: {value:,.2f}")
            else:
                print(f"{key.replace('_', ' ').title():25}: {value}")
        
        return stats_dict 
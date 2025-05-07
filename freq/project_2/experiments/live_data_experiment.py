#!/usr/bin/env python3
"""
Live Trading Data Experiment for FreqTrade
-------------------------------------------
This script demonstrates how data looks during live trading,
comparing standard candles vs. trade-based 5s candles.

Usage:
    python live_data_experiment.py --pair ETH/USDT:USDT
"""
import os
import sys
import time
import logging
import argparse
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import ccxt

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('live_data_experiment')

class LiveDataExperiment:
    """Experiment with live trading data to understand its structure and limitations"""
    
    def __init__(self, exchange_name: str, pair: str, api_key=None, api_secret=None):
        self.exchange_name = exchange_name
        self.pair = pair
        
        # Initialize exchange
        logger.info(f"Connecting to {exchange_name}...")
        exchange_class = getattr(ccxt, exchange_name)
        self.exchange = exchange_class({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
        })
        
        logger.info("Connected to exchange")
        self.exchange.load_markets()
        
        # Validate pair
        if pair not in self.exchange.markets:
            logger.error(f"Pair {pair} not found on {exchange_name}")
            raise ValueError(f"Pair {pair} not found on {exchange_name}")
            
        logger.info(f"Using pair: {pair}")
        
    def fetch_standard_candles(self, timeframe: str = '1m', limit: int = 100) -> pd.DataFrame:
        """Fetch standard OHLCV candles from the exchange"""
        logger.info(f"Fetching {limit} {timeframe} candles for {self.pair}...")
        
        try:
            candles = self.exchange.fetch_ohlcv(self.pair, timeframe=timeframe, limit=limit)
            
            if not candles:
                logger.warning(f"No {timeframe} candles returned")
                return pd.DataFrame()
                
            # Convert to DataFrame
            df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            logger.info(f"Got {len(df)} {timeframe} candles, from {df['date'].min()} to {df['date'].max()}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching {timeframe} candles: {str(e)}")
            return pd.DataFrame()
    
    def fetch_trades(self, limit: int = 1000, since: Optional[int] = None) -> pd.DataFrame:
        """Fetch recent trades from the exchange"""
        try:
            logger.info(f"Fetching up to {limit} trades for {self.pair}...")
            
            # Calculate since time if not provided (last hour)
            if since is None:
                since = int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp() * 1000)
                
            # Fetch trades
            trades = self.exchange.fetch_trades(self.pair, since=since, limit=limit)
            
            if not trades:
                logger.warning("No trades returned")
                return pd.DataFrame()
                
            # Convert to DataFrame
            df = pd.DataFrame([{
                'id': t['id'],
                'timestamp': t['timestamp'],
                'price': float(t['price']),
                'amount': float(t['amount']),
                'side': t['side']
            } for t in trades])
            
            df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            logger.info(f"Got {len(df)} trades, from {df['date'].min()} to {df['date'].max()}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching trades: {str(e)}")
            return pd.DataFrame()
    
    def trades_to_ohlcv(self, trades_df: pd.DataFrame, timeframe: str = '5s') -> pd.DataFrame:
        """Convert trades to OHLCV candles with specified timeframe"""
        if trades_df.empty:
            return pd.DataFrame()
            
        logger.info(f"Converting {len(trades_df)} trades to {timeframe} candles...")
        
        # Floor timestamp to specified timeframe
        if timeframe == '5s':
            trades_df['candle_time'] = trades_df['date'].dt.floor('5s')
        elif timeframe == '1m':
            trades_df['candle_time'] = trades_df['date'].dt.floor('1min')
        else:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
            
        # Group by candle time
        grouped = trades_df.groupby('candle_time')
        
        # Create OHLCV candles
        candles = pd.DataFrame({
            'date': grouped.indices.keys(),
            'open': grouped['price'].first(),
            'high': grouped['price'].max(),
            'low': grouped['price'].min(),
            'close': grouped['price'].last(),
            'volume': grouped['amount'].sum()
        })
        
        # Sort by date
        candles = candles.sort_values('date')
        
        # Add timestamp column (milliseconds)
        candles['timestamp'] = candles['date'].astype(np.int64) // 10**6
        
        logger.info(f"Created {len(candles)} {timeframe} candles")
        return candles
    
    def compare_candle_data(self):
        """Compare standard candles vs. trade-constructed candles"""
        # Get standard 1m candles
        candles_1m = self.fetch_standard_candles('1m', 30)
        
        # Get 5s candles if available
        candles_5s_direct = None
        try:
            # Note: Most exchanges don't support 5s candles directly
            candles_5s_direct = self.fetch_standard_candles('5s', 100)
        except Exception as e:
            logger.warning(f"Could not fetch 5s candles directly: {e}")
        
        # Get trades and construct 5s candles
        trades_df = self.fetch_trades(1000)
        candles_5s_from_trades = self.trades_to_ohlcv(trades_df, '5s')
        
        # Also construct 1m candles from trades for comparison
        candles_1m_from_trades = self.trades_to_ohlcv(trades_df, '1m')
        
        # Print summary
        print("\n" + "="*80)
        print(f"DATA COMPARISON FOR {self.pair}")
        print("="*80)
        
        if not candles_1m.empty:
            print(f"\n1. Standard 1m Candles (from exchange.fetch_ohlcv):")
            print(f"   - Count: {len(candles_1m)} candles")
            print(f"   - Time Range: {candles_1m['date'].min()} to {candles_1m['date'].max()}")
            print(f"   - First Candle: {candles_1m.iloc[0].to_dict()}")
            print(f"   - Last Candle: {candles_1m.iloc[-1].to_dict()}")
        else:
            print("\n1. Standard 1m Candles: None available")
        
        if candles_5s_direct is not None and not candles_5s_direct.empty:
            print(f"\n2. Direct 5s Candles (from exchange.fetch_ohlcv):")
            print(f"   - Count: {len(candles_5s_direct)} candles")
            print(f"   - Time Range: {candles_5s_direct['date'].min()} to {candles_5s_direct['date'].max()}")
            print(f"   - First Candle: {candles_5s_direct.iloc[0].to_dict()}")
            print(f"   - Last Candle: {candles_5s_direct.iloc[-1].to_dict()}")
        else:
            print("\n2. Direct 5s Candles: Not supported by exchange")
        
        if not trades_df.empty:
            print(f"\n3. Raw Trades (from exchange.fetch_trades):")
            print(f"   - Count: {len(trades_df)} trades")
            print(f"   - Time Range: {trades_df['date'].min()} to {trades_df['date'].max()}")
            print(f"   - First Trade: {trades_df.iloc[0].to_dict()}")
            print(f"   - Last Trade: {trades_df.iloc[-1].to_dict()}")
        else:
            print("\n3. Raw Trades: None available")
        
        if not candles_5s_from_trades.empty:
            print(f"\n4. Constructed 5s Candles (from trades):")
            print(f"   - Count: {len(candles_5s_from_trades)} candles")
            print(f"   - Time Range: {candles_5s_from_trades['date'].min()} to {candles_5s_from_trades['date'].max()}")
            print(f"   - First Candle: {candles_5s_from_trades.iloc[0].to_dict()}")
            print(f"   - Last Candle: {candles_5s_from_trades.iloc[-1].to_dict()}")
        else:
            print("\n4. Constructed 5s Candles: None available (no trades)")
        
        if not candles_1m_from_trades.empty and not candles_1m.empty:
            print(f"\n5. Comparison of 1m Candles (Standard vs. Constructed from Trades):")
            # Find overlapping time periods
            common_times = set(candles_1m['date']).intersection(set(candles_1m_from_trades['date']))
            if common_times:
                # Get a sample time for comparison
                sample_time = list(common_times)[0]
                std_candle = candles_1m[candles_1m['date'] == sample_time].iloc[0]
                trade_candle = candles_1m_from_trades[candles_1m_from_trades['date'] == sample_time].iloc[0]
                
                print(f"   Sample time: {sample_time}")
                print(f"   Standard:    OHLCV = {std_candle['open']:.2f}, {std_candle['high']:.2f}, {std_candle['low']:.2f}, {std_candle['close']:.2f}, {std_candle['volume']:.4f}")
                print(f"   Constructed: OHLCV = {trade_candle['open']:.2f}, {trade_candle['high']:.2f}, {trade_candle['low']:.2f}, {trade_candle['close']:.2f}, {trade_candle['volume']:.4f}")
                
                # Calculate differences
                open_diff = abs(std_candle['open'] - trade_candle['open']) / std_candle['open'] * 100
                high_diff = abs(std_candle['high'] - trade_candle['high']) / std_candle['high'] * 100
                low_diff = abs(std_candle['low'] - trade_candle['low']) / std_candle['low'] * 100
                close_diff = abs(std_candle['close'] - trade_candle['close']) / std_candle['close'] * 100
                volume_diff = abs(std_candle['volume'] - trade_candle['volume']) / std_candle['volume'] * 100 if std_candle['volume'] > 0 else 0
                
                print(f"   Differences: Open={open_diff:.2f}%, High={high_diff:.2f}%, Low={low_diff:.2f}%, Close={close_diff:.2f}%, Volume={volume_diff:.2f}%")
            else:
                print("   No overlapping candles found for comparison")
        
        print("\n" + "="*80)
        print("CONCLUSIONS")
        print("="*80)
        print("1. Data Availability:")
        print(f"   - 1m Candles: {'Available' if not candles_1m.empty else 'Not available'}")
        print(f"   - 5s Candles: {'Available' if candles_5s_direct is not None and not candles_5s_direct.empty else 'Not directly available'}")
        print(f"   - Trades: {'Available' if not trades_df.empty else 'Not available'}")
        print(f"   - Constructed 5s Candles: {'Available' if not candles_5s_from_trades.empty else 'Not available'}")
        
        print("\n2. Historical Data Depth:")
        if not candles_1m.empty:
            candle_1m_minutes = (candles_1m['date'].max() - candles_1m['date'].min()).total_seconds() / 60
            print(f"   - 1m Candles: {len(candles_1m)} candles = {candle_1m_minutes:.1f} minutes of data")
        
        if candles_5s_direct is not None and not candles_5s_direct.empty:
            candle_5s_minutes = (candles_5s_direct['date'].max() - candles_5s_direct['date'].min()).total_seconds() / 60
            print(f"   - Direct 5s Candles: {len(candles_5s_direct)} candles = {candle_5s_minutes:.1f} minutes of data")
        
        if not trades_df.empty:
            trade_minutes = (trades_df['date'].max() - trades_df['date'].min()).total_seconds() / 60
            print(f"   - Trades: {len(trades_df)} trades spanning {trade_minutes:.1f} minutes")
        
        if not candles_5s_from_trades.empty:
            constructed_minutes = (candles_5s_from_trades['date'].max() - candles_5s_from_trades['date'].min()).total_seconds() / 60
            print(f"   - Constructed 5s Candles: {len(candles_5s_from_trades)} candles = {constructed_minutes:.1f} minutes of data")
        
        print("\n3. Live Trading Implications:")
        if not candles_5s_from_trades.empty and not candles_1m.empty:
            print("   - Trade-constructed 5s candles provide more granular data than standard 1m candles")
            print("   - For strategy using both timeframes, 5s data would need to be constructed from trades")
            print("   - Amount of historical 5s data is limited by the trade history available")
            print("   - Continuous collection and storage of trade data is necessary for maintaining history")
        else:
            print("   - Limited data available to draw conclusions")
        
        # Store results to CSV for further analysis
        if not candles_5s_from_trades.empty:
            output_dir = os.path.dirname(os.path.abspath(__file__))
            filename = os.path.join(output_dir, f"5s_candles_{self.pair.replace('/', '_')}.csv")
            candles_5s_from_trades.to_csv(filename, index=False)
            print(f"\nSaved 5s candles to: {filename}")

def main():
    parser = argparse.ArgumentParser(description='Live trading data experiment for FreqTrade')
    parser.add_argument('--exchange', type=str, default='binance', help='Exchange name (ccxt)')
    parser.add_argument('--pair', type=str, required=True, help='Trading pair (e.g. ETH/USDT:USDT)')
    parser.add_argument('--api-key', type=str, help='API key (optional)')
    parser.add_argument('--api-secret', type=str, help='API secret (optional)')
    
    args = parser.parse_args()
    
    try:
        experiment = LiveDataExperiment(
            exchange_name=args.exchange,
            pair=args.pair,
            api_key=args.api_key,
            api_secret=args.api_secret
        )
        
        experiment.compare_candle_data()
        
    except Exception as e:
        logger.error(f"Experiment failed: {str(e)}")
        return 1
        
    return 0

if __name__ == '__main__':
    sys.exit(main()) 
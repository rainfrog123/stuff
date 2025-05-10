#!/usr/bin/env python3
"""
Utility module for accessing collected market data in various formats.
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta

from database import MarketDatabase
from config import SYMBOLS

logger = logging.getLogger(__name__)

class DataAccess:
    """
    Provides convenient access to market data collected by the system.
    Handles data retrieval, formatting, and export functionality.
    """
    
    def __init__(self):
        """Initialize the data access utility."""
        self.db = MarketDatabase()
    
    def get_available_symbols(self):
        """Get a list of all available symbols in the database."""
        with self.db.get_candles_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT DISTINCT symbol FROM candles')
            symbols = [row['symbol'] for row in cursor.fetchall()]
            return symbols
    
    def get_candles(self, symbol, start_time=None, end_time=None, limit=None):
        """Get 5s candles for a symbol with optional time filtering."""
        # Convert datetime objects to timestamps if provided
        if isinstance(start_time, datetime):
            start_time = int(start_time.timestamp() * 1000)
        if isinstance(end_time, datetime):
            end_time = int(end_time.timestamp() * 1000)
            
        # Get data from database
        df = self.db.get_candles(symbol, start_time, end_time, limit)
        
        if df.empty:
            logger.warning(f"No candle data found for {symbol} in the specified time range")
            return df
        
        # Convert timestamp to datetime for easier handling
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        return df
    
    def get_trades(self, symbol, start_time=None, end_time=None, limit=None):
        """Get trades for a symbol with optional time filtering."""
        # Convert datetime objects to timestamps if provided
        if isinstance(start_time, datetime):
            start_time = int(start_time.timestamp() * 1000)
        if isinstance(end_time, datetime):
            end_time = int(end_time.timestamp() * 1000)
            
        # Get data from database
        df = self.db.get_trades(symbol, start_time, end_time, limit)
        
        if df.empty:
            logger.warning(f"No trade data found for {symbol} in the specified time range")
            return df
        
        # Convert timestamp to datetime for easier handling
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        return df
    
    def get_candles_as_ohlcv(self, symbol, start_time=None, end_time=None, limit=None):
        """Get candles in OHLCV format compatible with technical analysis libraries."""
        df = self.get_candles(symbol, start_time, end_time, limit)
        
        if df.empty:
            return df
        
        # Format as OHLCV
        ohlcv = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()
        ohlcv.set_index('timestamp', inplace=True)
        
        return ohlcv
    
    def resample_candles(self, symbol, timeframe, start_time=None, end_time=None):
        """
        Resample 5s candles to a higher timeframe.
        
        Args:
            symbol: Trading pair symbol
            timeframe: Target timeframe (e.g., '1m', '5m', '15m', '1h')
            start_time: Start time for data
            end_time: End time for data
            
        Returns:
            DataFrame with resampled OHLCV data
        """
        # Get 5s candles
        df = self.get_candles_as_ohlcv(symbol, start_time, end_time)
        
        if df.empty:
            return df
        
        # Map timeframe strings to pandas resample rule
        timeframe_map = {
            '10s': '10S',
            '15s': '15S',
            '30s': '30S',
            '1m': '1Min',
            '5m': '5Min',
            '15m': '15Min',
            '30m': '30Min',
            '1h': '1H',
            '4h': '4H',
            '1d': '1D'
        }
        
        if timeframe not in timeframe_map:
            logger.error(f"Unsupported timeframe: {timeframe}. Supported timeframes: {list(timeframe_map.keys())}")
            return pd.DataFrame()
        
        # Resample data
        rule = timeframe_map[timeframe]
        resampled = df.resample(rule).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })
        
        # Clean up NaN values (periods with no trades)
        resampled.dropna(inplace=True)
        
        return resampled
    
    def export_to_csv(self, symbol, data_type='candles', timeframe='5s', 
                      start_time=None, end_time=None, filename=None):
        """
        Export data to CSV file.
        
        Args:
            symbol: Trading pair symbol
            data_type: Type of data ('candles' or 'trades')
            timeframe: Timeframe for candles (default: '5s')
            start_time: Start time for data
            end_time: End time for data
            filename: Output filename (default: auto-generated)
            
        Returns:
            Path to the saved CSV file
        """
        # Get data
        if data_type == 'candles':
            if timeframe == '5s':
                df = self.get_candles(symbol, start_time, end_time)
            else:
                df = self.resample_candles(symbol, timeframe, start_time, end_time)
                df.reset_index(inplace=True)  # Convert index back to column
        elif data_type == 'trades':
            df = self.get_trades(symbol, start_time, end_time)
        else:
            logger.error(f"Invalid data_type: {data_type}. Must be 'candles' or 'trades'")
            return None
        
        if df.empty:
            logger.warning(f"No data to export for {symbol}")
            return None
        
        # Generate filename if not provided
        if filename is None:
            symbol_clean = symbol.replace('/', '_')
            timeframe_str = f"_{timeframe}" if data_type == 'candles' else ""
            current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{symbol_clean}_{data_type}{timeframe_str}_{current_time}.csv"
        
        # Export to CSV
        try:
            df.to_csv(filename, index=False)
            logger.info(f"Data exported to {filename}")
            return filename
        except Exception as e:
            logger.error(f"Error exporting data to CSV: {e}")
            return None
    
    def get_latest_data_info(self):
        """Get information about the latest available data for all symbols."""
        info = {}
        
        for symbol in self.get_available_symbols():
            # Get latest candle info from candles database
            with self.db.get_candles_connection() as conn:
                cursor = conn.cursor()
                
                # Get latest candle info
                cursor.execute('''
                SELECT MAX(timestamp) as latest_candle_ts, COUNT(*) as candle_count 
                FROM candles WHERE symbol = ?
                ''', (symbol,))
                candle_result = cursor.fetchone()
                
                # Get earliest candle info
                cursor.execute('''
                SELECT MIN(timestamp) as first_data_ts
                FROM candles WHERE symbol = ?
                ''', (symbol,))
                first_data_result = cursor.fetchone()
            
            # Get latest trade info from trades database
            with self.db.get_trades_connection() as conn:
                cursor = conn.cursor()
                
                # Get latest trade info
                cursor.execute('''
                SELECT MAX(timestamp) as latest_trade_ts, COUNT(*) as trade_count 
                FROM trades WHERE symbol = ?
                ''', (symbol,))
                trade_result = cursor.fetchone()
            
            # Process results
            latest_candle_ts = candle_result['latest_candle_ts'] if candle_result and candle_result['latest_candle_ts'] else 0
            latest_trade_ts = trade_result['latest_trade_ts'] if trade_result and trade_result['latest_trade_ts'] else 0
            first_data_ts = first_data_result['first_data_ts'] if first_data_result and first_data_result['first_data_ts'] else 0
            
            # Convert timestamps to datetime
            latest_candle = datetime.fromtimestamp(latest_candle_ts / 1000) if latest_candle_ts else None
            latest_trade = datetime.fromtimestamp(latest_trade_ts / 1000) if latest_trade_ts else None
            first_data = datetime.fromtimestamp(first_data_ts / 1000) if first_data_ts else None
            
            # Calculate time span
            time_span = None
            if latest_trade and first_data:
                time_delta = latest_trade - first_data
                days = time_delta.days
                hours, remainder = divmod(time_delta.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                time_span = f"{days} days {hours:02d}:{minutes:02d}:{seconds:02d}"
            
            # Store info for symbol
            info[symbol] = {
                'first_data': first_data,
                'latest_candle': latest_candle,
                'latest_trade': latest_trade,
                'time_span': time_span,
                'candle_count': candle_result['candle_count'] if candle_result else 0,
                'trade_count': trade_result['trade_count'] if trade_result else 0
            }
        
        return info

# Example usage
if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    # Initialize data access
    data = DataAccess()
    
    # Print information about available data
    info = data.get_latest_data_info()
    for symbol, symbol_info in info.items():
        print(f"Symbol: {symbol}")
        print(f"  Time span: {symbol_info['first_data']} to {symbol_info['latest_candle']}")
        print(f"  Candles: {symbol_info['candle_count']}")
        print(f"  Trades: {symbol_info['trade_count']}")
        print("")
    
    # Export example
    for symbol in data.get_available_symbols():
        # Export last hour of 5-second candles
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)
        data.export_to_csv(symbol, data_type='candles', start_time=start_time, end_time=end_time) 
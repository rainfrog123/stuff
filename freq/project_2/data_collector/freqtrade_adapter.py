#!/usr/bin/env python3
"""
FreqTrade 5s Candle Adapter
---------------------------
This script provides an interface between the 5s candle database
created by trade_collector.py and FreqTrade's strategy system.

It contains:
1. A custom DataProvider class for FreqTrade to use with 5s data
2. Example usage in a strategy
3. Configuration for live trading with 5s data

Usage:
    - Place this file in user_data/
    - Reference the custom data provider in config.json
"""
import os
import logging
import sqlite3
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from freqtrade.data.dataprovider import DataProvider
from freqtrade.exchange import Exchange
from freqtrade.data.converter import ohlcv_to_dataframe
from freqtrade.data.history import load_pair_history

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'user_data', 'data', '5s_candles.sqlite')

class External5sDataProvider:
    """
    Custom data provider that retrieves 5s candles from SQLite database.
    Can be used alongside FreqTrade's standard data provider.
    """
    
    def __init__(self, config: dict, exchange: Exchange, dataprovider: Optional[DataProvider] = None):
        """
        Initialize the data provider
        :param config: Configuration dictionary
        :param exchange: Exchange instance
        :param dataprovider: Optional DataProvider instance (will be injected by FreqTrade)
        """
        self.config = config
        self.exchange = exchange
        self.dp = dataprovider  # Standard FreqTrade DataProvider
        
        # Read config
        provider_config = config.get('data_provider', {}).get('config', {})
        self.db_path = provider_config.get('db_path', DEFAULT_DB_PATH)
        self.lookback_candles = provider_config.get('lookback_candles', 100)
        self.cache_timeout = provider_config.get('cache_timeout', 5)  # seconds
        
        # Cache for 5s OHLCV data
        self._ohlcv_cache: Dict[str, Tuple[pd.DataFrame, datetime]] = {}
        
        # Connect to the database
        try:
            self._init_database()
            logger.info(f"External 5s data provider initialized with database: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize 5s data provider: {e}")
            raise RuntimeError(f"Failed to initialize 5s data provider: {e}")
    
    def _init_database(self):
        """Initialize database connection"""
        if not os.path.exists(self.db_path):
            logger.warning(f"5s candle database not found at {self.db_path}")
            logger.warning("Make sure trade_collector.py is running to collect data")
            self.conn = None
            return
        
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        
        # Test connection
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM candles")
        count = cursor.fetchone()[0]
        logger.info(f"Connected to 5s candle database with {count} candles")
    
    def get_5s_ohlcv(self, pair: str, lookback_candles: Optional[int] = None) -> pd.DataFrame:
        """
        Get 5-second OHLCV data for a trading pair
        
        :param pair: Trading pair (e.g. 'BTC/USDT:USDT')
        :param lookback_candles: Number of candles to retrieve (overrides default)
        :return: DataFrame with 5s OHLCV data
        """
        if not self.conn:
            return pd.DataFrame()
        
        # Check if we have fresh cached data
        if pair in self._ohlcv_cache:
            df, timestamp = self._ohlcv_cache[pair]
            age = (datetime.now(timezone.utc) - timestamp).total_seconds()
            
            if age < self.cache_timeout:
                return df
        
        # Determine number of candles to fetch
        num_candles = lookback_candles if lookback_candles is not None else self.lookback_candles
        
        try:
            # Fetch from database
            query = """
            SELECT timestamp, open, high, low, close, volume 
            FROM candles 
            WHERE pair = ? 
            ORDER BY timestamp DESC
            LIMIT ?
            """
            
            df = pd.read_sql_query(
                query, 
                self.conn, 
                params=(pair, num_candles),
            )
            
            if df.empty:
                logger.warning(f"No 5s candles found for {pair}")
                return pd.DataFrame()
            
            # Convert timestamp to datetime
            df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Reorder columns to match FreqTrade format
            df = df[['date', 'open', 'high', 'low', 'close', 'volume']]
            
            # Sort by date (ascending)
            df = df.sort_values('date')
            
            # Store in cache
            self._ohlcv_cache[pair] = (df.copy(), datetime.now(timezone.utc))
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching 5s candles for {pair}: {e}")
            return pd.DataFrame()
    
    def get_5s_dataframe(self, pair: str, lookback_candles: Optional[int] = None) -> pd.DataFrame:
        """
        Get 5-second OHLCV data formatted as a FreqTrade dataframe
        (with additional columns like 'date_str')
        
        :param pair: Trading pair
        :param lookback_candles: Number of candles to retrieve
        :return: FreqTrade-formatted DataFrame
        """
        df = self.get_5s_ohlcv(pair, lookback_candles)
        
        if df.empty:
            return df
        
        # Convert to FreqTrade format
        return ohlcv_to_dataframe(df, '5s', pair, False, False)
    
    def available_pairs(self) -> List[str]:
        """Get list of available pairs in the database"""
        if not self.conn:
            return []
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT DISTINCT pair FROM candles")
            pairs = [row[0] for row in cursor.fetchall()]
            return pairs
        except Exception as e:
            logger.error(f"Error fetching available pairs: {e}")
            return []
    
    def refresh(self):
        """Clear the cache to force data refresh"""
        self._ohlcv_cache.clear()

# Example strategy using 5s data
"""
from freqtrade.strategy import IStrategy, IntParameter
import talib.abstract as ta

class FiveSecondScalper(IStrategy):
    '''Example strategy using 5s candles from external data provider'''
    
    timeframe = '1m'  # Required standard timeframe
    
    # Strategy parameters
    buy_rsi = IntParameter(10, 40, default=30)
    sell_rsi = IntParameter(60, 90, default=70)
    
    # Minimal ROI
    minimal_roi = {
        "0": 0.005,  # 0.5% is fine for scalping
    }

    # Stoploss
    stoploss = -0.01  # 1% stoploss

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        # FreqTrade will inject the External5sDataProvider as self.dp_5s
        self.dp_5s = None  
    
    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        # Standard 1m indicators
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # Get 5s dataframe if available
        if self.dp_5s:
            try:
                # Get 5s data
                df_5s = self.dp_5s.get_5s_dataframe(metadata['pair'])
                
                if not df_5s.empty:
                    # Calculate 5s-specific indicators
                    df_5s['rsi_5s'] = ta.RSI(df_5s, timeperiod=7)
                    
                    # Get latest 5s values
                    latest_5s = df_5s.iloc[-1].to_dict()
                    
                    # Add 5s indicators to 1m dataframe
                    dataframe['rsi_5s'] = latest_5s['rsi_5s']
                    dataframe['5s_close'] = latest_5s['close']
                    dataframe['5s_volume'] = latest_5s['volume']
                    
                    # Add more sophisticated indicators as needed
                    
            except Exception as e:
                logging.error(f"Error processing 5s data: {e}")
                
        return dataframe
    
    def populate_buy_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        conditions = []
        
        # If 5s data is available, use it
        if 'rsi_5s' in dataframe.columns:
            conditions.append(dataframe['rsi_5s'] < self.buy_rsi.value)
        else:
            # Fallback to 1m data
            conditions.append(dataframe['rsi'] < self.buy_rsi.value)
        
        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'buy'
            ] = 1
        
        return dataframe
    
    def populate_sell_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        conditions = []
        
        # If 5s data is available, use it
        if 'rsi_5s' in dataframe.columns:
            conditions.append(dataframe['rsi_5s'] > self.sell_rsi.value)
        else:
            # Fallback to 1m data
            conditions.append(dataframe['rsi'] > self.sell_rsi.value)
        
        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'sell'
            ] = 1
        
        return dataframe
"""

# Example config.json settings
"""
{
    "max_open_trades": 10,
    "stake_currency": "USDT",
    "stake_amount": "unlimited",
    "fiat_display_currency": "USD",
    "dry_run": false,
    "timeframe": "1m",
    "data_provider": {
        "class": "user_data.freqtrade_adapter:External5sDataProvider",
        "config": {
            "db_path": "/path/to/user_data/data/5s_candles.sqlite",
            "lookback_candles": 100,
            "cache_timeout": 5
        }
    },
    "order_types": {
        "buy": "market",
        "sell": "market",
        "stoploss": "market",
        "stoploss_on_exchange": false
    },
    "exchange": {
        "name": "binance",
        "key": "",
        "secret": "",
        "ccxt_config": {},
        "ccxt_async_config": {},
        "pair_whitelist": [
            "BTC/USDT:USDT",
            "ETH/USDT:USDT"
        ],
        "pair_blacklist": []
    },
    "pairlists": [
        {"method": "StaticPairList"}
    ]
}
"""

if __name__ == "__main__":
    # If run directly, perform a test to check if 5s data is available
    import sys
    
    test_db_path = DEFAULT_DB_PATH
    if len(sys.argv) > 1:
        test_db_path = sys.argv[1]
    
    print(f"Testing 5s candle data availability in {test_db_path}")
    
    try:
        if not os.path.exists(test_db_path):
            print(f"ERROR: Database not found at {test_db_path}")
            sys.exit(1)
            
        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()
        
        # Get total candle count
        cursor.execute("SELECT COUNT(*) FROM candles")
        total_count = cursor.fetchone()[0]
        print(f"Total candles in database: {total_count}")
        
        # Get available pairs
        cursor.execute("SELECT DISTINCT pair FROM candles")
        pairs = [row[0] for row in cursor.fetchall()]
        print(f"Available pairs: {', '.join(pairs)}")
        
        # For each pair, get candle count and time range
        for pair in pairs:
            cursor.execute(
                "SELECT MIN(timestamp), MAX(timestamp), COUNT(*) FROM candles WHERE pair = ?",
                (pair,)
            )
            min_ts, max_ts, count = cursor.fetchone()
            
            min_date = datetime.fromtimestamp(min_ts / 1000, tz=timezone.utc)
            max_date = datetime.fromtimestamp(max_ts / 1000, tz=timezone.utc)
            duration = max_date - min_date
            
            print(f"\nPair: {pair}")
            print(f"  Candles: {count}")
            print(f"  Time Range: {min_date} to {max_date}")
            print(f"  Duration: {duration}")
            print(f"  Candles per Hour: {count / (duration.total_seconds() / 3600):.1f}")
        
        print("\n5s candle data test successful!")
        
    except Exception as e:
        print(f"ERROR: Could not access 5s candle data: {e}")
        sys.exit(1) 
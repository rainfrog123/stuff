#!/usr/bin/env python3
"""
Custom data provider for FreqTrade that fetches and uses 5-second candles from Binance.
This provider integrates with the existing FreqTrade infrastructure but adds
real-time 5s candle support.
"""
import logging
import time
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime, timezone
import threading

import pandas as pd
import numpy as np
from pandas import DataFrame

from freqtrade.data.dataprovider import DataProvider
from freqtrade.enums import CandleType
from freqtrade.exchange.exchange_types import OrderBook
from freqtrade.persistence.models import Trade

# Import the BinanceTradesFetcher to get 5s candle data
from user_data.scripts.fetch_binance_trades import BinanceTradesFetcher

logger = logging.getLogger(__name__)

# Constants
TIMEFRAME = "5s"
EXCHANGE_NAME = "binance"
BASE_DATA_DIR = Path("/allah/stuff/freq/project_2/user_data/data")


class CustomFiveSecondProvider(DataProvider):
    """
    Custom data provider that intercepts FreqTrade's normal data flow and 
    injects 5-second candle data from Binance.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the custom data provider."""
        super().__init__(*args, **kwargs)
        self.fetcher = BinanceTradesFetcher(exchange_name=EXCHANGE_NAME)
        self.data_dir = BASE_DATA_DIR / EXCHANGE_NAME / TIMEFRAME
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache for 5s candle data
        self._candle_cache: Dict[str, DataFrame] = {}
        self._last_update: Dict[str, datetime] = {}
        
        # Pairs we're monitoring
        self._monitored_pairs: List[str] = []
        
        # Update thread
        self._stop_event = threading.Event()
        self._update_thread = None
        
        logger.info("CustomFiveSecondProvider initialized")
        
    def start_update_thread(self):
        """Start the background thread that updates candle data."""
        if self._update_thread is None or not self._update_thread.is_alive():
            self._stop_event.clear()
            self._update_thread = threading.Thread(target=self._update_candles_loop)
            self._update_thread.daemon = True
            self._update_thread.start()
            logger.info("Started 5s candle update thread")
    
    def stop_update_thread(self):
        """Stop the background update thread."""
        if self._update_thread and self._update_thread.is_alive():
            self._stop_event.set()
            self._update_thread.join(timeout=10)
            logger.info("Stopped 5s candle update thread")
    
    def _update_candles_loop(self):
        """Background thread that periodically updates 5s candle data."""
        while not self._stop_event.is_set():
            try:
                # Get pairs from whitelist
                if hasattr(self._exchange, "get_valid_pair_names"):
                    self._monitored_pairs = self._exchange.get_valid_pair_names()
                elif self._config.get("pairs", None):
                    self._monitored_pairs = self._config["pairs"]
                elif self._config.get("exchange", {}).get("pair_whitelist", None):
                    self._monitored_pairs = self._config["exchange"]["pair_whitelist"]
                
                # Update each pair
                for pair in self._monitored_pairs:
                    self._update_candles_for_pair(pair)
                
                # Sleep for a short time (2 seconds for a 5s timeframe makes sense)
                time.sleep(2)
            except Exception as e:
                logger.error(f"Error in update thread: {str(e)}")
                time.sleep(5)  # Sleep longer on error
    
    def _update_candles_for_pair(self, pair: str):
        """Update candle data for a single pair."""
        now = datetime.now(timezone.utc)
        
        # If we haven't updated this pair recently, do it now
        if pair not in self._last_update or (now - self._last_update[pair]).total_seconds() > 4:
            try:
                # Calculate time range for fetching trades
                # Go back 5 minutes to ensure we have enough data
                end_time = int(now.timestamp() * 1000)
                start_time = end_time - (5 * 60 * 1000)  # 5 minutes in milliseconds
                
                # Fetch and aggregate trades to 5s candles
                candles_df = self.fetcher.fetch_and_aggregate(pair, start_time, end_time, TIMEFRAME)
                
                if not candles_df.empty:
                    # Save to cache
                    self._candle_cache[pair] = candles_df
                    self._last_update[pair] = now
                    
                    # Also save to disk for persistence
                    self.fetcher.save_candles(candles_df, pair, TIMEFRAME)
                    
                    # Update FreqTrade's internal cache
                    self._set_cached_df(pair, TIMEFRAME, candles_df, CandleType.SPOT)
                    
                    logger.debug(f"Updated 5s candles for {pair}, got {len(candles_df)} candles")
                
            except Exception as e:
                logger.error(f"Error updating candles for {pair}: {str(e)}")
    
    def _load_cached_candles(self, pair: str) -> Optional[DataFrame]:
        """Load cached candle data from disk if available."""
        # Convert pair to filename format
        filename = pair.replace('/', '-').replace(':', '')
        file_path = self.data_dir / f"{filename}.parquet"
        
        if not file_path.exists():
            logger.warning(f"No cached data file found for {pair} at {file_path}")
            return None
        
        try:
            # Load parquet file
            df = pd.read_parquet(file_path)
            
            # Ensure required columns exist
            required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
            if not all(col in df.columns for col in required_cols):
                logger.error(f"Missing required columns in {file_path}")
                return None
            
            logger.info(f"Loaded {len(df)} cached candles for {pair}")
            return df
        
        except Exception as e:
            logger.error(f"Error loading cached data for {pair}: {str(e)}")
            return None
    
    def ohlcv(
        self, pair: str, timeframe: str = None, copy: bool = True, candle_type: str = ""
    ) -> DataFrame:
        """
        Override the ohlcv method to provide custom 5s candle data.
        """
        # Handle 5s timeframe special case
        if timeframe == TIMEFRAME or (timeframe is None and self._config.get("timeframe") == TIMEFRAME):
            # First check if we have recent data in cache
            if pair in self._candle_cache and not self._candle_cache[pair].empty:
                df = self._candle_cache[pair]
                return df.copy() if copy else df
            
            # If not in memory cache, try to load from disk
            df = self._load_cached_candles(pair)
            if df is not None:
                self._candle_cache[pair] = df
                return df.copy() if copy else df
            
            # If nothing found, update now
            self._update_candles_for_pair(pair)
            
            # Return what we have, even if empty
            if pair in self._candle_cache:
                df = self._candle_cache[pair]
                return df.copy() if copy else df
            
            # If all else fails, return empty DataFrame with correct structure
            return pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume'])
        
        # For other timeframes, use the parent implementation
        return super().ohlcv(pair, timeframe, copy, candle_type) 
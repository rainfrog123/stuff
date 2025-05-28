#!/usr/bin/env python3
"""
Configuration settings for the TradingView 5-second data collection system.
"""

import os
from pathlib import Path

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = "/allah/data"  # Use absolute path for data storage
LOG_DIR = os.path.join(DATA_DIR, "logs")

# Ensure data directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# Database settings
CANDLES_DB_PATH = os.path.join(DATA_DIR, "tv_candles.db")  # Main 5s candles database

# Data collection settings
SYMBOLS = ["BINANCE:ETHUSDT.P"]  # TradingView symbol format
CANDLE_TIMEFRAME = "5s"  # 5-second candles

# Logging configuration
LOG_LEVEL = "INFO"
LOG_FILE = os.path.join(LOG_DIR, "tv_collector.log") 
#!/usr/bin/env python3
"""
Configuration settings for the 5-second data collection system.
"""

import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.absolute()
DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_DIR = os.path.join(BASE_DIR, "logs")

# Database settings
DB_PATH = os.path.join(DATA_DIR, "market_data.db")

# Exchange settings
EXCHANGE = "binance"
EXCHANGE_CREDENTIALS = {
    "apiKey": "ofQzX3gGAKS777NyYIovAy1XyqLzGC2UJPMh9jqIYEfieFRy3DCkZJl15VYA2zXo",
    "secret": "QVJpTFgHIEv74LmCT5clX8o1zAFEEqJqKpg2ePklObM1Ybv9iKNe8jvM7MRjoz07",
    "enableRateLimit": True,
    "options": {
        "defaultType": "future"
    }
}

# Data collection settings
SYMBOLS = ["ETH/USDT"]  # List of trading pairs to collect
MAX_TRADES = 10000  # Maximum number of trades to keep per symbol
CANDLE_TIMEFRAME = "5s"  # 5-second candles

# Logging configuration
LOG_LEVEL = "INFO"
LOG_FILE = os.path.join(LOG_DIR, "data_collector.log")

# Retry settings
MAX_RECONNECT_ATTEMPTS = 5
RECONNECT_DELAY = 5  # seconds

# Initial historical data fetch
INITIAL_HISTORY_MINUTES = 60  # Fetch 1 hour of historical data on startup 
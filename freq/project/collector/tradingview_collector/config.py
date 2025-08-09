#!/usr/bin/env python3
"""Configuration for TradingView 5s candle collector."""

import os

# Directories
DATA_DIR = "/allah/data"
LOG_DIR = os.path.join(DATA_DIR, "logs")

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# Database
DB_PATH = os.path.join(DATA_DIR, "candles.db")

# Collection settings
SYMBOLS = ["BINANCE:ETHUSDT.P"]
RETENTION_HOURS = 3
PRUNE_INTERVAL_MINUTES = 5

# TradingView WebSocket
AUTH_TOKEN = "eyJhbGciOiJSUzUxMiIsImtpZCI6IkdaeFUiLCJ0eXAiOiJKV1QifQ.eyJ1c2VyX2lkIjoxMDcyNjQ5MDMsImV4cCI6MTc0ODQ3NDMxOSwiaWF0IjoxNzQ4NDU5OTE5LCJwbGFuIjoicHJvX3ByZW1pdW1fdHJpYWwiLCJwcm9zdGF0dXMiOiJub25fcHJvIiwiZXh0X2hvdXJzIjoxLCJwZXJtIjoiIiwic3R1ZHlfcGVybSI6InR2LXByb3N0dWRpZXMsdHYtY2hhcnRwYXR0ZXJucyx0di1jaGFydF9wYXR0ZXJucyx0di12b2x1bWVieXByaWNlIiwibWF4X3N0dWRpZXMiOjI1LCJtYXhfZnVuZGFtZW50YWxzIjoxMCwibWF4X2NoYXJ0cyI6OCwibWF4X2FjdGl2ZV9hbGVydHMiOjQwMCwibWF4X3N0dWR5X29uX3N0dWR5IjoyNCwiZmllbGRzX3Blcm1pc3Npb25zIjpbInJlZmJvbmRzIl0sIm1heF9hbGVydF9jb25kaXRpb25zIjo1LCJtYXhfb3ZlcmFsbF9hbGVydHMiOjIwMDAsIm1heF9vdmVyYWxsX3dhdGNobGlzdF9hbGVydHMiOjUsIm1heF9hY3RpdmVfcHJpbWl0aXZlX2FsZXJ0cyI6NDAwLCJtYXhfYWN0aXZlX2NvbXBsZXhfYWxlcnRzIjo0MDAsIm1heF9hY3RpdmVfd2F0Y2hsaXN0X2FsZXJ0cyI6MiwibWF4X2Nvbm5lY3Rpb25zIjo1MH0.jCnGIXp99XUBxyFvdLm2xJkGusKaFsME51W0RNfWuGFGWGJiJG3Le0XIq5SFQ9om0l1yCOyO_mw3J44HyAweIsACDzOXbk8DRQz4C0AM8L2zbGUHe5mL8cwv3Dm3HxTUYVClF9LFt7Azlc_KGSo3d5wXpkgBkzbWyzkURq7yBeA"
WS_URL = "wss://prodata.tradingview.com/socket.io/websocket"
SESSION_ID = "cs_RlEFHlg56lDq"

# Logging
LOG_LEVEL = "INFO"
LOG_FILE = os.path.join(LOG_DIR, "collector.log") 
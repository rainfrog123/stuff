#!/usr/bin/env python3
"""Configuration for TradingView 5s candle collector."""

import os

# Directories
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
LOG_DIR = os.path.join(DATA_DIR, "logs")

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# Database
DB_PATH = os.path.join(DATA_DIR, "candles.db")

# Collection settings
SYMBOLS = ["BINANCE:ETHUSDT.P"]
RETENTION_HOURS = 3
PRUNE_INTERVAL_MINUTES = 10

# TradingView WebSocket
AUTH_TOKEN = "eyJhbGciOiJSUzUxMiIsImtpZCI6IkdaeFUiLCJ0eXAiOiJKV1QifQ.eyJ1c2VyX2lkIjoxMTI1NzU4MTIsImV4cCI6MTc1NDc1OTE5NywiaWF0IjoxNzU0NzQ0Nzk3LCJwbGFuIjoicHJvX3ByZW1pdW1fdHJpYWwiLCJwcm9zdGF0dXMiOiJub25fcHJvIiwiZXh0X2hvdXJzIjoxLCJwZXJtIjoiIiwic3R1ZHlfcGVybSI6InR2LWNoYXJ0cGF0dGVybnMsdHYtcHJvc3R1ZGllcyx0di1jaGFydF9wYXR0ZXJucyx0di12b2x1bWVieXByaWNlIiwibWF4X3N0dWRpZXMiOjI1LCJtYXhfZnVuZGFtZW50YWxzIjoxMCwibWF4X2NoYXJ0cyI6OCwibWF4X2FjdGl2ZV9hbGVydHMiOjQwMCwibWF4X3N0dWR5X29uX3N0dWR5IjoyNCwiZmllbGRzX3Blcm1pc3Npb25zIjpbInJlZmJvbmRzIl0sIm1heF9hbGVydF9jb25kaXRpb25zIjo1LCJtYXhfb3ZlcmFsbF9hbGVydHMiOjIwMDAsIm1heF9vdmVyYWxsX3dhdGNobGlzdF9hbGVydHMiOjUsIm1heF9hY3RpdmVfcHJpbWl0aXZlX2FsZXJ0cyI6NDAwLCJtYXhfYWN0aXZlX2NvbXBsZXhfYWxlcnRzIjo0MDAsIm1heF9hY3RpdmVfd2F0Y2hsaXN0X2FsZXJ0cyI6MiwibWF4X2Nvbm5lY3Rpb25zIjo1MH0.A-gA-YrLgEoIFSqdBj_bzCRlaxH2XPQ7UdAu0kpg5Sl_NJc-X4JWKbDcUiTijP0ex0h_BwAcA1t2YOhy8A0blzolzXJCU1XaO0OxHrLYtCK1U_NASf_pIujk1MdZzaY3BlFbK7DqYxhi_8Xlyds_z9zz8WcAf00zSJCgF801628"
WS_URL = "wss://prodata.tradingview.com/socket.io/websocket"
SESSION_ID = "cs_UnjWX3itlj5J"

# Logging
LOG_LEVEL = "INFO"
LOG_FILE = os.path.join(LOG_DIR, "collector.log") 
# TradingView Data Collector

A stealthy and efficient data collection system for TradingView that supports both username/password login and session ID authentication.

## Features

- Multiple authentication methods:
  - Username/password login
  - Direct session ID usage
  - Saved session reuse
- Handles modern TradingView authentication challenges
- Real-time WebSocket data collection
- Supports multiple symbols simultaneously
- Session persistence between runs

## Components

- `tradingview_auth.py` - Authentication management
- `tradingview_websocket.py` - WebSocket client for data collection
- `test_tv_collector.py` - Example script for testing the collector
- `tv_session.py` - Basic session ID based connection
- `tv_cookie_session.py` - Cookie-based session connection
- `tv_login.py` - Direct login implementation
- `tv_stealth_login.py` - Enhanced stealth login with browser fingerprinting

## Usage

### Basic Usage with Session ID

```bash
python test_tv_collector.py --session-id YOUR_SESSION_ID
```

### Login with Username/Password

```bash
python test_tv_collector.py --username YOUR_USERNAME --password YOUR_PASSWORD
```

### Watching Multiple Symbols

```bash
python test_tv_collector.py --symbols BINANCE:BTCUSDT,BINANCE:ETHUSDT,NYSE:AAPL
```

### Integration with Your Code

```python
from tradingview_auth import TradingViewAuth
from tradingview_websocket import TradingViewWebSocket

# Create and authenticate
auth = TradingViewAuth()
auth.set_session_id('YOUR_SESSION_ID')  # Or auth.login_with_credentials(username, password)

# Create WebSocket client
tv_ws = TradingViewWebSocket(auth)

# Set up data callback
def handle_data(message):
    # Process the data
    print(f"Received data: {message[:100]}...")

tv_ws.set_data_callback(handle_data)

# Connect and add symbols
if tv_ws.connect():
    tv_ws.add_symbol("BINANCE:BTCUSDT")
    
    # Keep running for a while
    import time
    time.sleep(60)
    
    # Disconnect when done
    tv_ws.disconnect()
```

## Obtaining a Session ID

1. Login to TradingView with your browser
2. Open Developer Tools (F12 or right-click > Inspect)
3. Go to the Application tab
4. Under Storage > Cookies > www.tradingview.com
5. Find the cookie named "sessionid"
6. Copy its value

## Troubleshooting

- If login fails with CAPTCHA detection, use a pre-existing session ID instead
- If WebSocket connection fails, ensure your session ID is valid (try logging in manually)
- For persistent usage, ensure your IP address and user agent remain consistent between runs
- If you encounter "protocol_error" messages, check that your session ID is valid and has proper permissions

## Legal Considerations

This code is provided for educational purposes only. Ensure you comply with TradingView's Terms of Service before using this code. Automated data collection may be against TradingView's terms of service.

## Requirements

- Python 3.6+
- websocket-client
- requests
- beautifulsoup4 
#!/usr/bin/env python3
import websocket
import json
import time
import string
import random
import argparse
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('tv_binance_futures_simple')

def generate_session():
    """Generate a random session ID for TradingView chart"""
    string_length = 12
    letters = string.ascii_lowercase
    random_string = ''.join(random.choice(letters) for i in range(string_length))
    return "cs_" + random_string

def prepend_header(st):
    """Add message length header used by TradingView protocol"""
    return "~m~" + str(len(st)) + "~m~" + st

def construct_message(func, param_list):
    """Create a JSON message in TradingView format"""
    return json.dumps({"m": func, "p": param_list}, separators=(',', ':'))

def create_message(func, args):
    """Create a complete message with header"""
    return prepend_header(construct_message(func, args))

def on_message(ws, message):
    """Handle received messages"""
    # Print all messages in raw form when in debug mode
    if logger.level == logging.DEBUG:
        logger.debug(f"RAW: {message[:300]}")
        
    # Handle heartbeat messages
    if "~h~" in message:
        logger.info("Received heartbeat, responding...")
        ws.send(message)
        return
    
    # Print any message containing ETHUSDT
    if "ETHUSDT" in message:
        logger.info(f"ETH Data: {message[:300]}")
        try:
            # Clean up message for better readability
            parts = message.split("~m~")
            for part in parts:
                if part and part.startswith("{"):
                    data = json.loads(part)
                    if data.get("m") == "du" and data.get("p"):
                        symbol = data["p"][0]
                        if "ETHUSDT" in symbol:
                            values = data["p"][1].get("v", {})
                            price = values.get("lp")
                            change = values.get("ch")
                            change_pct = values.get("chp")
                            timestamp = datetime.now().strftime("%H:%M:%S")
                            
                            if price:
                                direction = "🟢" if change and float(change) > 0 else "🔴" if change and float(change) < 0 else "⚪"
                                logger.info(f"{timestamp} | {symbol} | {direction} Price: {price} | Change: {change_pct}%")
        except Exception as e:
            logger.debug(f"Error parsing message: {e}")

def on_error(ws, error):
    """Handle errors"""
    logger.error(f"WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    """Handle connection close"""
    logger.info(f"WebSocket connection closed: {close_status_code} - {close_msg}")

def on_open(ws):
    """Handle connection open - setup subscriptions"""
    logger.info("WebSocket connection opened!")
    
    # Generate chart session
    chart_session = generate_session()
    logger.info(f"Chart session ID: {chart_session}")
    
    # Generate quote session
    quote_session = "qs_" + ''.join(random.choice(string.ascii_lowercase) for i in range(12))
    logger.info(f"Quote session ID: {quote_session}")
    
    # Create sessions
    ws.send(create_message("chart_create_session", [chart_session, ""]))
    ws.send(create_message("quote_create_session", [quote_session]))
    
    # Setup quote fields (full set of fields)
    ws.send(create_message("quote_set_fields", [
        quote_session,
        "ch", "chp", "current_session", "description", "local_description", 
        "language", "exchange", "fractional", "is_tradable", "lp", "lp_time", 
        "minmov", "minmove2", "original_name", "pricescale", "pro_name", 
        "short_name", "type", "update_mode", "volume", "currency_code", "rchp", "rtc", 
        "open_price", "high_price", "low_price", "prev_close_price", "funding_rate", 
        "bid", "ask", "fundamentals", "market_cap_basic"
    ]))
    
    # Try multiple symbols/formats for Binance ETHUSDT
    symbols = [
        "BINANCE:ETHUSDT",          # Spot market
        "BINANCE:ETHUSDT.P",        # Perpetual futures with .P suffix
        "BINANCEFUTURES:ETHUSDT",   # Explicit futures exchange
        "BINANCE:ETHUSDTPERP"       # Another futures notation
    ]
    
    for symbol in symbols:
        logger.info(f"Adding symbol: {symbol}")
        ws.send(create_message("quote_add_symbols", [quote_session, symbol, {"flags": ['force_permission']}]))
        ws.send(create_message("quote_fast_symbols", [quote_session, symbol]))
    
    # Also setup chart for the main spot symbol (this often helps trigger data flow)
    ws.send(create_message("resolve_symbol", [chart_session, "symbol_1", '={"symbol":"BINANCE:ETHUSDT","adjustment":"splits"}']))
    ws.send(create_message("create_series", [chart_session, "s1", "s1", "symbol_1", "1", 300]))
    
    logger.info("Successfully subscribed to symbols")
    
    # Request full symbol details (often helps trigger data)
    time.sleep(1)  # Small delay before requesting more data
    for symbol in symbols:
        ws.send(create_message("quote_fast_symbols", [quote_session, symbol]))

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Simple TradingView Binance ETHUSDT Tracker")
    parser.add_argument("--session-id", required=True, help="TradingView session ID")
    parser.add_argument("--duration", type=int, default=60, help="Duration to run in seconds")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
        websocket.enableTrace(True)
    else:
        websocket.enableTrace(False)
    
    # WebSocket URL - direct connection to TradingView WebSocket
    socket_url = "wss://data.tradingview.com/socket.io/websocket"
    
    # Headers with session ID cookie for authentication
    headers = {
        "Origin": "https://www.tradingview.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Cookie": f"sessionid={args.session_id}",
        "Referer": "https://www.tradingview.com/chart/",
    }
    
    logger.info(f"Connecting to TradingView with session ID: {args.session_id[:5]}***")
    logger.info(f"This connection will run for {args.duration} seconds...")
    
    # Create and run WebSocket
    ws = websocket.WebSocketApp(
        socket_url,
        header=list(f"{k}: {v}" for k, v in headers.items()),
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    # Run WebSocket in foreground (more stable than threading for testing)
    import threading
    ws_thread = threading.Thread(target=ws.run_forever, kwargs={"ping_interval": 20, "ping_timeout": 10})
    ws_thread.daemon = True
    ws_thread.start()
    
    try:
        # Keep the main thread alive for the specified duration
        start_time = time.time()
        while time.time() - start_time < args.duration:
            time.sleep(1)
            # Check if the websocket is still alive
            if not ws_thread.is_alive():
                logger.error("WebSocket thread died. Trying to reconnect...")
                ws_thread = threading.Thread(target=ws.run_forever, kwargs={"ping_interval": 20, "ping_timeout": 10})
                ws_thread.daemon = True
                ws_thread.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        # Properly close the WebSocket
        ws.close()
        logger.info("Connection closed")

if __name__ == "__main__":
    main() 
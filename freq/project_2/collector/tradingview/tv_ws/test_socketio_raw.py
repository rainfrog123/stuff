#!/usr/bin/env python3
import websocket
import json
import time
import string
import random
import argparse
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('tv_raw_socket')

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

def send_message(ws, func, args):
    """Send a message to the TradingView WebSocket"""
    message = create_message(func, args)
    logger.info(f"Sending: {message[:100]}...")
    ws.send(message)

def on_message(ws, message):
    """Handle received messages"""
    logger.info(f"Received: {message[:200]}")
    
    # Respond to heartbeat messages
    if "~h~" in message:
        logger.info("Received heartbeat, responding...")
        ws.send(message)

def on_error(ws, error):
    """Handle errors"""
    logger.error(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    """Handle connection close"""
    logger.info(f"Connection closed: {close_status_code} - {close_msg}")

def on_open(ws):
    """Handle connection open"""
    logger.info("Connection opened!")
    
    # Generate chart session
    chart_session = generate_session()
    logger.info(f"Chart session ID: {chart_session}")
    
    # Generate quote session
    quote_session = "qs_" + ''.join(random.choice(string.ascii_lowercase) for i in range(12))
    logger.info(f"Quote session ID: {quote_session}")
    
    # Create sessions - don't set auth token, we're using cookie instead
    send_message(ws, "chart_create_session", [chart_session, ""])
    send_message(ws, "quote_create_session", [quote_session])
    
    # Setup quote fields
    send_message(ws, "quote_set_fields", [
        quote_session,
        "ch", "chp", "current_session", "description", "local_description", 
        "language", "exchange", "fractional", "is_tradable", "lp", "lp_time", 
        "minmov", "minmove2", "original_name", "pricescale", "pro_name", 
        "short_name", "type", "update_mode", "volume", "currency_code", "rchp", "rtc"
    ])
    
    # Add symbol to watch
    symbol = "BINANCE:BTCUSDT"
    send_message(ws, "quote_add_symbols", [quote_session, symbol, {"flags": ['force_permission']}])
    send_message(ws, "quote_fast_symbols", [quote_session, symbol])
    
    # Setup chart
    send_message(ws, "resolve_symbol", [chart_session, "symbol_1", f"={{\"symbol\":\"{symbol}\",\"adjustment\":\"splits\"}}"])
    send_message(ws, "create_series", [chart_session, "s1", "s1", "symbol_1", "1", 300])

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="TradingView Raw WebSocket Test")
    parser.add_argument("--session-id", required=True, help="TradingView session ID")
    parser.add_argument("--duration", type=int, default=60, help="Duration to run in seconds")
    args = parser.parse_args()
    
    # WebSocket URL
    socket_url = "wss://data.tradingview.com/socket.io/websocket"
    
    # Headers
    headers = {
        "Origin": "https://www.tradingview.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Cookie": f"sessionid={args.session_id}",
    }
    
    # Setup websocket with callback functions
    websocket.enableTrace(True)
    ws = websocket.WebSocketApp(
        socket_url,
        header=list(f"{k}: {v}" for k, v in headers.items()),
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    # Run the websocket connection in a thread
    import threading
    ws_thread = threading.Thread(target=ws.run_forever)
    ws_thread.daemon = True
    ws_thread.start()
    
    # Run for the specified duration
    try:
        logger.info(f"Running for {args.duration} seconds...")
        time.sleep(args.duration)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        # Close the websocket connection
        ws.close()
        logger.info("Test complete")

if __name__ == "__main__":
    main() 
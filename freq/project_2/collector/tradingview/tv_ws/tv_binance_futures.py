#!/usr/bin/env python3
import websocket
import json
import time
import string
import random
import argparse
import logging
import threading
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('binance_futures.log')
    ]
)
logger = logging.getLogger('tv_binance_futures')

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
    logger.debug(f"Sending: {message[:100]}...")
    ws.send(message)

def parse_data_update(message):
    """Parse data updates from TradingView websocket"""
    if "~m~" not in message:
        return None
        
    try:
        # Split by message prefix pattern and find the part with data
        parts = message.split("~m~")
        for part in parts:
            if not part or not part.startswith("{"):
                continue
                
            try:
                data = json.loads(part)
                
                # Check for quote updates (for symbol price data)
                if data.get("m") == "du" and data.get("p"):
                    updates = data.get("p", [])
                    if len(updates) > 1:
                        symbol = updates[0]
                        values = updates[1].get("v", {})
                        
                        # Extract the relevant fields
                        price_data = {
                            "symbol": symbol,
                            "timestamp": time.time(),
                            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "last_price": values.get("lp"),
                            "volume": values.get("volume"),
                            "change": values.get("ch"),
                            "change_percent": values.get("chp"),
                            "bid": values.get("bid"),
                            "ask": values.get("ask"),
                            "funding_rate": values.get("funding_rate"),
                            "open": values.get("open_price"),
                            "high": values.get("high_price"),
                            "low": values.get("low_price")
                        }
                        return price_data
                        
                # Check for series data (chart price data)
                elif data.get("m") == "timescale_update" and data.get("p"):
                    params = data.get("p", [])
                    if len(params) > 1 and "sds" in params[1]:
                        series_data = params[1].get("sds", {})
                        if series_data:
                            # Sometimes multiple series data in one message
                            for series_id, series_values in series_data.items():
                                if "s" in series_values:
                                    bars = series_values.get("s", [])
                                    if bars:
                                        logger.debug(f"Received {len(bars)} bars for series {series_id}")
                                        # Process the last bar (most recent)
                                        return {"type": "candle_data", "data": bars[-1]}
            except json.JSONDecodeError:
                continue
    except Exception as e:
        logger.error(f"Error parsing data update: {e}")
        
    return None

def on_message(ws, message):
    """Handle received messages"""
    # Respond to heartbeat messages
    if "~h~" in message:
        logger.debug("Received heartbeat, responding...")
        ws.send(message)
        return
        
    # Check for specific data we're interested in
    if '"m":"du"' in message and ('"symbol":"BINANCE:ETHUSDT.P"' in message or 
                                '"symbol":"BINANCEFUTURES:ETHUSDT"' in message):
        # Print the raw message for debugging (first time only)
        logger.info(f"Raw ETHUSDT futures data: {message[:400]}...")
        
    # Parse data updates
    price_data = parse_data_update(message)
    if price_data:
        # For quote updates (price data)
        if "type" not in price_data:
            symbol = price_data.get("symbol", "")
            if "ETHUSDT" in symbol:
                price = price_data.get("last_price")
                change_pct = price_data.get("change_percent")
                timestamp = price_data.get("datetime")
                funding = price_data.get("funding_rate", "N/A")
                
                # Use emoji to indicate price direction
                direction = "🟢" if change_pct and float(change_pct) > 0 else "🔴" if change_pct and float(change_pct) < 0 else "⚪"
                
                # Only log if we have a price
                if price:
                    logger.info(f"{timestamp} | {symbol} | {direction} Price: {price} | Change: {change_pct}% | Funding: {funding}")
                    # Save to file if needed
                    # save_to_file(price_data)
        
        # For candle data
        elif price_data["type"] == "candle_data":
            candle = price_data["data"]
            logger.debug(f"Candle data: {candle}")

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
    
    # Create sessions - don't set auth token, we're using cookie instead
    send_message(ws, "chart_create_session", [chart_session, ""])
    send_message(ws, "quote_create_session", [quote_session])
    
    # Setup quote fields - request all available fields
    send_message(ws, "quote_set_fields", [
        quote_session,
        "ch", "chp", "current_session", "description", "local_description", 
        "language", "exchange", "fractional", "is_tradable", "lp", "lp_time", 
        "minmov", "minmove2", "original_name", "pricescale", "pro_name", 
        "short_name", "type", "update_mode", "volume", "currency_code", "rchp", "rtc", 
        "open_price", "high_price", "low_price", "prev_close_price", "funding_rate", 
        "bid", "ask", "fundamentals", "market_cap_basic", "earnings_per_share_basic_ttm"
    ])
    
    # Try different symbol formats for Binance Futures ETHUSDT
    symbols = [
        "BINANCE:ETHUSDT.P",        # .P suffix for perpetual contracts
        "BINANCEFUTURES:ETHUSDT",   # Explicit futures exchange
        "BINANCE:ETHUSDT_PERP",     # Alternative notation
        "BINANCE:ETHUSDT"           # Sometimes spot symbol works too
    ]
    
    for symbol in symbols:
        logger.info(f"Adding symbol: {symbol}")
        # Add to quote session for price updates
        send_message(ws, "quote_add_symbols", [quote_session, symbol, {"flags": ['force_permission']}])
        send_message(ws, "quote_fast_symbols", [quote_session, symbol])
        
        # Setup chart for the symbol
        symbol_id = f"symbol_{symbols.index(symbol)+1}"
        send_message(ws, "resolve_symbol", [chart_session, symbol_id, f"={{\"symbol\":\"{symbol}\",\"adjustment\":\"splits\"}}"])
        send_message(ws, "create_series", [chart_session, f"s{symbols.index(symbol)+1}", f"s{symbols.index(symbol)+1}", symbol_id, "1", 300])
    
    logger.info(f"Successfully subscribed to Binance ETHUSDT futures symbols")

def connect_and_subscribe(session_id, timeout=3600):
    """Connect to TradingView WebSocket and subscribe to Binance Futures ETHUSDT"""
    # WebSocket URL
    socket_url = "wss://data.tradingview.com/socket.io/websocket"
    
    # Headers
    headers = {
        "Origin": "https://www.tradingview.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Cookie": f"sessionid={session_id}",
        "Referer": "https://www.tradingview.com/chart/",
    }
    
    logger.info(f"Connecting to TradingView with session ID: {session_id[:5]}***")
    
    # Setup websocket with callback functions
    websocket.enableTrace(False)  # Set to True for detailed logging
    ws = websocket.WebSocketApp(
        socket_url,
        header=list(f"{k}: {v}" for k, v in headers.items()),
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    # Run the websocket connection with automatic reconnection
    ws_thread = threading.Thread(target=lambda: ws.run_forever(ping_interval=30, ping_timeout=10, reconnect=5))
    ws_thread.daemon = True
    ws_thread.start()
    
    try:
        logger.info(f"Listening for Binance Futures ETHUSDT updates for {timeout} seconds...")
        # Keep the main thread alive
        for _ in range(timeout):
            time.sleep(1)
            if not ws_thread.is_alive():
                logger.error("WebSocket thread died. Attempting to restart...")
                ws_thread = threading.Thread(target=lambda: ws.run_forever(ping_interval=30, ping_timeout=10, reconnect=5))
                ws_thread.daemon = True
                ws_thread.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        # Close the websocket connection
        ws.close()
        logger.info("Connection closed")

def save_to_file(data, filename="ethusdt_data.json"):
    """Save received data to a file"""
    with open(filename, "a") as f:
        f.write(json.dumps(data) + "\n")

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="TradingView Binance Futures ETHUSDT Tracker")
    parser.add_argument("--session-id", required=True, help="TradingView session ID")
    parser.add_argument("--duration", type=int, default=3600, help="Duration to run in seconds")
    parser.add_argument("--save", action="store_true", help="Save data to file")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    logger.info("Starting Binance Futures ETHUSDT tracker")
    connect_and_subscribe(args.session_id, args.duration)
    logger.info("ETHUSDT tracking completed")

if __name__ == "__main__":
    main() 
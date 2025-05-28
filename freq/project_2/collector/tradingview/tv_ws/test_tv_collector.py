#!/usr/bin/env python3
import json
import argparse
import time
import logging
from tradingview_auth import TradingViewAuth
from tradingview_websocket import TradingViewWebSocket

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('tradingview_collector.log')
    ]
)
logger = logging.getLogger('tv_collector')

def parse_data(message):
    """Parse TradingView WebSocket data message"""
    if "~m~" not in message:
        return None
        
    # Split by message prefix pattern
    parts = message.split("~m~")
    for part in parts:
        if part.startswith("{"):
            try:
                data = json.loads(part)
                if data.get("m") == "du" and data.get("p"):
                    # Extract updates
                    updates = data.get("p", [])
                    if len(updates) > 1:
                        symbol = updates[0]
                        values = updates[1].get("v", {})
                        
                        # Extract relevant fields
                        result = {
                            "symbol": symbol,
                            "timestamp": time.time(),
                            "last_price": values.get("lp"),
                            "volume": values.get("volume"),
                            "change": values.get("ch"),
                            "change_percent": values.get("chp")
                        }
                        return result
            except json.JSONDecodeError:
                pass
    
    return None

def process_data(message):
    """Process and display received data updates"""
    parsed = parse_data(message)
    if parsed:
        symbol = parsed.get("symbol")
        price = parsed.get("last_price")
        change = parsed.get("change")
        change_pct = parsed.get("change_percent")
        volume = parsed.get("volume")
        
        if price:
            direction = "▲" if change and float(change) > 0 else "▼" if change and float(change) < 0 else "◆"
            logger.info(f"{symbol} {direction} {price} ({change_pct}%) Vol: {volume}")

def run_collector(args):
    """Run the TradingView data collector"""
    # Create auth manager
    auth = TradingViewAuth()
    authenticated = False
    
    # Try authentication methods in order of preference
    if args.session_id:
        logger.info("Authenticating with provided session ID...")
        authenticated = auth.set_session_id(args.session_id)
    
    if not authenticated and not args.no_saved_session:
        logger.info("Trying to load saved session...")
        authenticated = auth.load_saved_session()
    
    if not authenticated and args.username and args.password:
        logger.info("Authenticating with username and password...")
        authenticated = auth.login_with_credentials(args.username, args.password)
    
    if not authenticated:
        logger.error("All authentication methods failed!")
        return False
    
    # Create WebSocket client
    tv_ws = TradingViewWebSocket(auth)
    tv_ws.set_data_callback(process_data)
    
    # Connect to WebSocket
    if not tv_ws.connect():
        logger.error("Failed to connect to TradingView WebSocket")
        return False
    
    logger.info("Successfully connected to TradingView WebSocket")
    
    # Add symbols to watch
    symbols = args.symbols.split(',') if args.symbols else ["BINANCE:BTCUSDT"]
    
    for symbol in symbols:
        symbol = symbol.strip()
        if symbol:
            if tv_ws.add_symbol(symbol):
                logger.info(f"Added symbol: {symbol}")
            else:
                logger.warning(f"Failed to add symbol: {symbol}")
    
    try:
        logger.info(f"Collecting data for {args.duration} seconds...")
        time.sleep(args.duration)
    except KeyboardInterrupt:
        logger.info("Collection interrupted by user")
    finally:
        # Disconnect
        tv_ws.disconnect()
        logger.info("Data collection completed")
    
    return True

def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(description="TradingView Data Collector")
    
    # Authentication options
    auth_group = parser.add_argument_group("Authentication Options")
    auth_group.add_argument("--session-id", help="TradingView session ID")
    auth_group.add_argument("--username", help="TradingView username")
    auth_group.add_argument("--password", help="TradingView password")
    auth_group.add_argument("--no-saved-session", action="store_true", 
                           help="Don't try to load saved session")
    
    # Collection options
    parser.add_argument("--symbols", default="BINANCE:BTCUSDT",
                       help="Comma-separated list of symbols to watch")
    parser.add_argument("--duration", type=int, default=60,
                       help="Duration to collect data in seconds")
    
    args = parser.parse_args()
    
    # Run collector
    success = run_collector(args)
    
    if not success:
        print("\nUsage examples:")
        print("  With session ID:   python test_tv_collector.py --session-id YOUR_SESSION_ID")
        print("  With credentials:  python test_tv_collector.py --username YOUR_USERNAME --password YOUR_PASSWORD")
        print("  With symbols:      python test_tv_collector.py --symbols BINANCE:BTCUSDT,BINANCE:ETHUSDT,NASDAQ:AAPL")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 
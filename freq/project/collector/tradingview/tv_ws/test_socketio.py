#!/usr/bin/env python3
import socketio
import json
import time
import argparse
import logging
from tradingview_auth import TradingViewAuth

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('tradingview_socketio.log')
    ]
)
logger = logging.getLogger('tv_socketio')

class TradingViewSocketIO:
    """
    Socket.IO client for TradingView data connection
    Alternative approach to WebSocket connection
    """
    
    def __init__(self, auth_manager=None):
        """Initialize with optional auth manager"""
        self.auth_manager = auth_manager or TradingViewAuth()
        self.sio = None
        self.connected = False
        self.messages_received = 0
    
    def setup(self):
        """Set up the Socket.IO client with event handlers"""
        self.sio = socketio.Client(logger=True, engineio_logger=True)
        
        @self.sio.event
        def connect():
            logger.info("✅ Connected to TradingView via Socket.IO!")
            self.connected = True
        
        @self.sio.event
        def connect_error(data):
            logger.error(f"❌ Connection error: {data}")
        
        @self.sio.event
        def disconnect():
            logger.info("❌ Disconnected from TradingView!")
            self.connected = False
        
        @self.sio.on('*')
        def catch_all(event, data):
            self.messages_received += 1
            logger.info(f"Event #{self.messages_received}: {event}")
            logger.debug(f"Data: {data}")
    
    def connect(self, endpoint="https://prodata.tradingview.com", socketio_path="/socket.io"):
        """
        Connect to TradingView via Socket.IO
        Returns True if successful, False otherwise
        """
        if not self.auth_manager.get_session_id():
            logger.error("No valid session ID available. Authentication required.")
            return False
            
        if not self.sio:
            self.setup()
            
        session_id = self.auth_manager.get_session_id()
        logger.info(f"Connecting to TradingView Socket.IO with session ID: {session_id[:5]}***")
        
        # Get headers from auth manager
        auth_headers = self.auth_manager.get_auth_headers()
        if not auth_headers:
            logger.error("Failed to get authentication headers")
            return False
            
        # Prepare connection parameters
        try:
            logger.info(f"Connecting to {endpoint} with path {socketio_path}")
            self.sio.connect(
                endpoint,
                socketio_path=socketio_path,
                headers=auth_headers,
                transports=['websocket'],  # Forces upgrade to websocket only (skip polling)
                wait_timeout=10,
            )
            
            # Wait a bit to ensure connection is established
            time.sleep(3)
            
            return self.connected
        except Exception as e:
            logger.error(f"Socket.IO connection error: {e}")
            return False
    
    def subscribe_to_symbol(self, symbol):
        """
        Subscribe to data for a specific symbol
        This is an example; the actual event names/formats would depend on TradingView's API
        """
        if not self.connected or not self.sio:
            logger.error("Not connected to TradingView")
            return False
            
        try:
            # Example subscription - this would need to be adjusted based on actual TradingView Socket.IO API
            subscription_data = {
                'symbol': symbol,
                'resolution': '1',  # 1 minute
                'type': 'quotes'
            }
            
            logger.info(f"Subscribing to {symbol}")
            self.sio.emit('subscribe', subscription_data)
            return True
        except Exception as e:
            logger.error(f"Error subscribing to {symbol}: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from TradingView"""
        if self.sio and self.connected:
            logger.info("Disconnecting from TradingView...")
            try:
                self.sio.disconnect()
                return True
            except Exception as e:
                logger.error(f"Error disconnecting: {e}")
                return False
        return False

def run_test(args):
    """Run the Socket.IO test with provided arguments"""
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
    
    # Create and connect Socket.IO client
    tv_socketio = TradingViewSocketIO(auth)
    
    if not tv_socketio.connect(endpoint=args.endpoint, socketio_path=args.path):
        logger.error("Failed to connect to TradingView Socket.IO")
        return False
    
    logger.info("Successfully connected to TradingView via Socket.IO")
    
    # Add symbols to watch
    symbols = args.symbols.split(',') if args.symbols else ["BINANCE:BTCUSDT"]
    
    for symbol in symbols:
        symbol = symbol.strip()
        if symbol:
            if tv_socketio.subscribe_to_symbol(symbol):
                logger.info(f"Subscribed to symbol: {symbol}")
            else:
                logger.warning(f"Failed to subscribe to symbol: {symbol}")
    
    try:
        logger.info(f"Listening for events for {args.duration} seconds...")
        time.sleep(args.duration)
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    finally:
        # Disconnect
        tv_socketio.disconnect()
        logger.info("Socket.IO test completed")
    
    return True

def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(description="TradingView Socket.IO Test Client")
    
    # Authentication options
    auth_group = parser.add_argument_group("Authentication Options")
    auth_group.add_argument("--session-id", help="TradingView session ID")
    auth_group.add_argument("--username", help="TradingView username")
    auth_group.add_argument("--password", help="TradingView password")
    auth_group.add_argument("--no-saved-session", action="store_true", 
                           help="Don't try to load saved session")
    
    # Socket.IO options
    socketio_group = parser.add_argument_group("Socket.IO Options")
    socketio_group.add_argument("--endpoint", default="https://prodata.tradingview.com",
                              help="Socket.IO endpoint URL")
    socketio_group.add_argument("--path", default="/socket.io",
                              help="Socket.IO path")
    
    # Collection options
    parser.add_argument("--symbols", default="BINANCE:BTCUSDT",
                       help="Comma-separated list of symbols to watch")
    parser.add_argument("--duration", type=int, default=60,
                       help="Duration to collect data in seconds")
    
    args = parser.parse_args()
    
    # Run test
    success = run_test(args)
    
    if not success:
        print("\nUsage examples:")
        print("  With session ID:  python test_socketio.py --session-id YOUR_SESSION_ID")
        print("  With credentials: python test_socketio.py --username YOUR_USERNAME --password YOUR_PASSWORD")
        print("  Different endpoint: python test_socketio.py --endpoint https://data.tradingview.com --path /socket.io")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 
import websocket
import json
import time
import string
import random
import logging
import threading
from tradingview_auth import TradingViewAuth

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('tradingview_websocket')

class TradingViewWebSocket:
    """
    WebSocket client for TradingView data collection
    Handles authentication, connection, and data reception
    """
    
    def __init__(self, auth_manager=None):
        """Initialize with optional auth manager"""
        self.auth_manager = auth_manager or TradingViewAuth()
        self.ws = None
        self.chart_session = None
        self.quote_session = None
        self.running = False
        self.callback = None
        self.symbols = set()
        self.ws_thread = None
    
    def generate_session(self, prefix="cs_"):
        """Generate a random session ID for TradingView"""
        string_length = 12
        letters = string.ascii_lowercase
        random_string = ''.join(random.choice(letters) for i in range(string_length))
        return prefix + random_string
    
    def prepend_header(self, st):
        """Add message length header used by TradingView protocol"""
        return "~m~" + str(len(st)) + "~m~" + st
    
    def construct_message(self, func, param_list):
        """Create a JSON message in TradingView format"""
        return json.dumps({"m": func, "p": param_list}, separators=(',', ':'))
    
    def create_message(self, func, args):
        """Create a complete message with header"""
        return self.prepend_header(self.construct_message(func, args))
    
    def send_message(self, func, args):
        """Send a message to the TradingView WebSocket"""
        if not self.ws:
            logger.error("WebSocket not connected")
            return False
            
        message = self.create_message(func, args)
        logger.debug(f"Sending: {message[:100]}...")
        try:
            self.ws.send(message)
            return True
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    def connect(self):
        """
        Establish WebSocket connection to TradingView
        Returns True if successful, False otherwise
        """
        if not self.auth_manager.get_session_id():
            logger.error("No valid session ID available. Authentication required.")
            return False
            
        session_id = self.auth_manager.get_session_id()
        logger.info(f"Connecting to TradingView WebSocket with session ID: {session_id[:5]}***")
        
        # Prepare WebSocket connection with cookie in headers
        socket_url = "wss://data.tradingview.com/socket.io/websocket"
        headers = self.auth_manager.get_auth_headers()
        
        if not headers:
            logger.error("Failed to get authentication headers")
            return False
        
        try:
            # Create WebSocket connection with callback handlers
            websocket.enableTrace(False)
            self.ws = websocket.WebSocketApp(
                socket_url,
                header=list(f"{k}: {v}" for k, v in headers.items()),
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            # Generate chart and quote sessions
            self.chart_session = self.generate_session("cs_")
            self.quote_session = self.generate_session("qs_")
            
            logger.info(f"Chart session ID: {self.chart_session}")
            logger.info(f"Quote session ID: {self.quote_session}")
            
            # Start WebSocket in a thread
            self.running = True
            self.ws_thread = threading.Thread(target=self.ws.run_forever)
            self.ws_thread.daemon = True
            self.ws_thread.start()
            
            # Wait for connection to establish
            time.sleep(2)
            
            return self.ws.sock and self.ws.sock.connected
            
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            self.running = False
            return False
    
    def _on_open(self, ws):
        """Callback when WebSocket connection is established"""
        logger.info("WebSocket connection established!")
        
        # Create sessions - no auth token, we're using cookie
        self.send_message("chart_create_session", [self.chart_session, ""])
        self.send_message("quote_create_session", [self.quote_session])
        
        # Setup quote fields
        self.send_message("quote_set_fields", [
            self.quote_session,
            "ch", "chp", "current_session", "description", "local_description", 
            "language", "exchange", "fractional", "is_tradable", "lp", "lp_time", 
            "minmov", "minmove2", "original_name", "pricescale", "pro_name", 
            "short_name", "type", "update_mode", "volume", "currency_code", "rchp", "rtc"
        ])
    
    def _on_message(self, ws, message):
        """Callback when a message is received"""
        # Check for heartbeat message
        if "~h~" in message:
            logger.debug("Received heartbeat, responding...")
            try:
                ws.send(message)
            except Exception as e:
                logger.error(f"Error responding to heartbeat: {e}")
        else:
            # Process data message
            if "protocol_error" in message:
                logger.error(f"Protocol error: {message[:200]}...")
            elif "du" in message and len(message) > 200:
                logger.debug(f"Data update received (length: {len(message)})")
                if self.callback:
                    try:
                        self.callback(message)
                    except Exception as e:
                        logger.error(f"Error in callback: {e}")
            else:
                logger.debug(f"Message received: {message[:100]}...")
    
    def _on_error(self, ws, error):
        """Callback when an error occurs"""
        logger.error(f"WebSocket error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Callback when the connection is closed"""
        logger.info(f"WebSocket connection closed: {close_status_code} - {close_msg}")
        self.running = False
    
    def add_symbol(self, symbol):
        """
        Add a symbol to watch
        Returns True if successful, False otherwise
        """
        if not self.ws or not self.running:
            logger.error("WebSocket not connected")
            return False
            
        symbol = symbol.upper()  # Ensure uppercase
        
        if symbol in self.symbols:
            logger.info(f"Symbol {symbol} already being watched")
            return True
            
        logger.info(f"Adding symbol: {symbol}")
        
        try:
            # Add symbol to quote session
            self.send_message("quote_add_symbols", [self.quote_session, symbol, {"flags": ['force_permission']}])
            self.send_message("quote_fast_symbols", [self.quote_session, symbol])
            
            # Setup chart for this symbol
            symbol_id = f"symbol_{len(self.symbols) + 1}"
            self.send_message("resolve_symbol", [self.chart_session, symbol_id, f"={{\"symbol\":\"{symbol}\",\"adjustment\":\"splits\"}}"])
            self.send_message("create_series", [self.chart_session, f"s{len(self.symbols) + 1}", f"s{len(self.symbols) + 1}", symbol_id, "1", 300])
            
            # Add the symbol to our tracked symbols
            self.symbols.add(symbol)
            return True
            
        except Exception as e:
            logger.error(f"Error adding symbol {symbol}: {e}")
            return False
    
    def set_data_callback(self, callback):
        """Set a callback function to process received data"""
        self.callback = callback
    
    def disconnect(self):
        """Close the WebSocket connection"""
        if self.ws:
            logger.info("Closing WebSocket connection...")
            self.running = False
            try:
                self.ws.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")
            
            # Wait for thread to finish
            if self.ws_thread and self.ws_thread.is_alive():
                self.ws_thread.join(timeout=3)
                
            self.ws = None
            self.symbols.clear()
            return True
        return False


# Example usage
if __name__ == "__main__":
    # Example callback function to process received data
    def process_data(message):
        # Simple printing for this example
        if "~m~" in message:
            parts = message.split("~m~")
            for part in parts:
                if part.startswith("{"):
                    try:
                        data = json.loads(part)
                        if data.get("m") == "du" and data.get("p"):
                            # Extract symbol and last price
                            update = data.get("p", [])
                            if len(update) > 1:
                                symbol_data = update[1].get("v", {})
                                symbol = update[0]
                                lp = symbol_data.get("lp")
                                if lp:
                                    print(f"Symbol: {symbol}, Last Price: {lp}")
                    except json.JSONDecodeError:
                        pass
    
    # Create auth manager
    auth = TradingViewAuth()
    
    # Try to load saved session or create new one
    if not auth.load_saved_session():
        # Try with direct session ID
        session_id = input("Enter TradingView session ID: ")
        if not auth.set_session_id(session_id):
            username = input("Enter TradingView username: ")
            password = input("Enter TradingView password: ")
            if not auth.login_with_credentials(username, password):
                print("All authentication methods failed")
                exit(1)
    
    # Create WebSocket client
    tv_websocket = TradingViewWebSocket(auth)
    
    # Set callback
    tv_websocket.set_data_callback(process_data)
    
    # Connect
    if tv_websocket.connect():
        print("Connected to TradingView WebSocket")
        
        # Add symbols to watch
        tv_websocket.add_symbol("BINANCE:BTCUSDT")
        tv_websocket.add_symbol("COINBASE:ETHUSD")
        
        # Keep running for a while
        try:
            print("Receiving data for 60 seconds...")
            time.sleep(60)
        except KeyboardInterrupt:
            print("Interrupted by user")
        
        # Disconnect
        tv_websocket.disconnect()
    else:
        print("Failed to connect to TradingView WebSocket") 
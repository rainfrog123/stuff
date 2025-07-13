import websocket
import json
import time
import string
import random

# Use the known working session ID
SESSION_ID = "tkfi0exuv4mkvd8izlp1ev798qx1zdv3"

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
    print(f"Sending: {message[:100]}...")
    ws.send(message)

def connect_to_tradingview():
    print(f"Connecting to TradingView WebSocket with session ID: {SESSION_ID}")
    
    # Prepare WebSocket connection
    socket_url = "wss://data.tradingview.com/socket.io/websocket"
    headers = {
        "Origin": "https://www.tradingview.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    }
    
    try:
        # Create WebSocket connection
        ws = websocket.create_connection(socket_url, header=headers)
        print("WebSocket connection established!")
        
        # Generate chart session
        chart_session = generate_session()
        print(f"Chart session ID: {chart_session}")
        
        # Generate quote session
        quote_session = "qs_" + ''.join(random.choice(string.ascii_lowercase) for i in range(12))
        print(f"Quote session ID: {quote_session}")
        
        # Set auth token (using session ID)
        send_message(ws, "set_auth_token", [SESSION_ID])
        
        # Create sessions
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
        
        # Add volume study
        send_message(ws, "create_study", [chart_session, "st1", "st1", "s1", "Volume@tv-basicstudies-118", {"length": 20, "col_prev_close": "false"}])
        
        # Listen for messages
        print("\nListening for messages:")
        for i in range(30):  # Listen for 30 messages or 30 seconds
            try:
                result = ws.recv()
                
                # Check for heartbeat message
                heartbeat_pattern = r"~m~\d+~m~~h~\d+"
                if result.count("~h~") > 0:
                    print("Received heartbeat, responding...")
                    ws.send(result)
                else:
                    # Try to pretty print if it's a data update
                    if "du" in result and len(result) > 200:
                        print(f"Message {i+1}: Data update received (length: {len(result)})")
                    else:
                        print(f"Message {i+1}: {result[:200]}...")
                        
                # Check for errors
                if "\"m\":\"protocol_error\"" in result:
                    print("!!! Protocol error detected !!!")
                    error_start = result.find("\"p\":")
                    error_end = result.find("]}", error_start)
                    error_msg = result[error_start:error_end+2]
                    print(f"Error details: {error_msg}")
                
            except Exception as e:
                print(f"Error receiving message: {e}")
                break
                
            # Add a small delay
            time.sleep(1)
        
        # Close connection
        ws.close()
        print("Connection closed")
        
    except Exception as e:
        print(f"WebSocket connection error: {e}")

if __name__ == "__main__":
    connect_to_tradingview() 
import requests
import json
import time
import websocket
import string
import random
import re
from bs4 import BeautifulSoup

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

def login_to_tradingview(username, password):
    """
    Login to TradingView and retrieve session ID
    Returns session ID if successful, None otherwise
    """
    print(f"Attempting to login with username: {username}")
    
    session = requests.Session()
    
    # Set common headers
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    session.headers.update(headers)
    
    # First, get the login page to obtain any necessary tokens/cookies
    try:
        login_page = session.get("https://www.tradingview.com/signin/")
        
        # Extract CSRF token if present
        soup = BeautifulSoup(login_page.text, 'html.parser')
        csrf_token = None
        csrf_input = soup.find('input', attrs={'name': 'csrf_token'})
        if csrf_input:
            csrf_token = csrf_input.get('value')
            print(f"Found CSRF token: {csrf_token}")
        
        # Prepare login data
        login_data = {
            "username": username,
            "password": password,
            "remember": "on"
        }
        if csrf_token:
            login_data["csrf_token"] = csrf_token
            
        # Login request
        login_url = "https://www.tradingview.com/accounts/signin/"
        login_response = session.post(
            login_url, 
            data=login_data,
            headers={
                "Origin": "https://www.tradingview.com",
                "Referer": "https://www.tradingview.com/signin/",
                "Content-Type": "application/x-www-form-urlencoded"
            }
        )
        
        # Check if login was successful
        if login_response.status_code == 200:
            # Check for CAPTCHA challenge
            if "captcha" in login_response.text.lower():
                print("CAPTCHA detected! Manual intervention required.")
                return None
                
            # Extract session ID from cookies
            session_id = session.cookies.get("sessionid")
            if session_id:
                print(f"Login successful! Session ID: {session_id}")
                return session_id
            else:
                print("Login seemed successful but no session ID found in cookies")
                return None
        else:
            print(f"Login failed with status code: {login_response.status_code}")
            return None
            
    except Exception as e:
        print(f"Login error: {e}")
        return None

def connect_to_tradingview(session_id):
    """Connect to TradingView WebSocket using session ID cookie"""
    print(f"Connecting to TradingView WebSocket with session ID cookie: {session_id}")
    
    # Prepare WebSocket connection with cookie in headers
    socket_url = "wss://data.tradingview.com/socket.io/websocket"
    headers = {
        "Origin": "https://www.tradingview.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Cookie": f"sessionid={session_id}",
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
        
        # Add volume study
        send_message(ws, "create_study", [chart_session, "st1", "st1", "s1", "Volume@tv-basicstudies-118", {"length": 20, "col_prev_close": "false"}])
        
        # Listen for messages
        print("\nListening for messages:")
        for i in range(30):  # Listen for 30 messages or 30 seconds
            try:
                result = ws.recv()
                
                # Check for heartbeat message
                if "~h~" in result:
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

def main():
    username = input("Enter TradingView username: ")
    password = input("Enter TradingView password: ")
    
    session_id = login_to_tradingview(username, password)
    
    if session_id:
        connect_to_tradingview(session_id)
    else:
        print("Failed to obtain session ID. Cannot connect to TradingView.")

if __name__ == "__main__":
    main() 
import requests
import json
import time
import websocket
import string
import random
import re
import os
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('tv_stealth')

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

def stealth_login(username, password):
    """
    Perform a stealthy login to TradingView
    Uses modern browser fingerprints and handles security challenges
    Returns session ID if successful, None otherwise
    """
    logger.info(f"Starting stealth login process for user: {username[:3]}***")
    
    session = requests.Session()
    
    # Browser fingerprint headers
    browser_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Ch-Ua": '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0"
    }
    session.headers.update(browser_headers)
    
    # First visit the main site to get cookies
    try:
        logger.info("Visiting TradingView homepage to collect initial cookies...")
        main_page = session.get("https://www.tradingview.com/")
        
        # Add a small delay to appear more human-like
        time.sleep(random.uniform(1.5, 3.0))
        
        # Now visit the sign-in page
        logger.info("Navigating to sign-in page...")
        signin_page = session.get("https://www.tradingview.com/signin/", 
                                 headers={"Referer": "https://www.tradingview.com/"})
        
        # Extract CSRF token and any other required parameters
        soup = BeautifulSoup(signin_page.text, 'html.parser')
        
        # Look for hidden inputs that might contain tokens
        csrf_token = None
        for input_tag in soup.find_all('input', type='hidden'):
            if input_tag.get('name') == 'csrf_token':
                csrf_token = input_tag.get('value')
                logger.info(f"Found CSRF token: {csrf_token[:10]}***")
        
        # Prepare login data
        login_data = {
            "username": username,
            "password": password,
            "remember": "on"
        }
        
        if csrf_token:
            login_data["csrf_token"] = csrf_token
            
        # Add a small delay again to mimic a human entering credentials
        time.sleep(random.uniform(2.0, 4.0))
            
        # Attempt login - modern TradingView might use XHR/fetch instead of form submit
        # Check for both approaches
        
        # 1. First, try the traditional form submission
        logger.info("Attempting login via form submission...")
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
        
        # 2. If that didn't work, try the API endpoint approach
        if login_response.status_code != 200 or "sessionid" not in session.cookies:
            logger.info("Form submission approach failed, trying API endpoint...")
            login_url = "https://www.tradingview.com/accounts/signin/ajax/"
            login_response = session.post(
                login_url, 
                json={
                    "username": username,
                    "password": password,
                    "remember": True
                },
                headers={
                    "Origin": "https://www.tradingview.com",
                    "Referer": "https://www.tradingview.com/signin/",
                    "Content-Type": "application/json",
                    "X-Requested-With": "XMLHttpRequest"
                }
            )
        
        # Check for CAPTCHA or 2FA challenges
        if "captcha" in login_response.text.lower():
            logger.error("CAPTCHA detected! Manual intervention required.")
            return None
            
        if "two-factor" in login_response.text.lower() or "2fa" in login_response.text.lower():
            logger.error("Two-factor authentication detected! Manual intervention required.")
            return None
            
        # Check if we have a session ID in cookies
        session_id = session.cookies.get("sessionid")
        
        if session_id:
            logger.info(f"Login successful! Session ID: {session_id[:5]}***")
            
            # Save cookies to reuse later
            cookie_file = "tradingview_cookies.json"
            cookies_dict = {cookie.name: cookie.value for cookie in session.cookies}
            with open(cookie_file, "w") as f:
                json.dump(cookies_dict, f)
            logger.info(f"Cookies saved to {cookie_file}")
            
            return session_id
        else:
            # Check if we were redirected to a success page
            if login_response.status_code == 302 or "/chart/" in login_response.url:
                # We're authenticated but cookies might not be properly captured
                logger.warning("Redirected to success page but no session ID found. Checking cookies again...")
                
                # Try to visit a page that requires authentication
                profile_page = session.get("https://www.tradingview.com/u/#/")
                session_id = session.cookies.get("sessionid")
                
                if session_id:
                    logger.info(f"Found session ID after redirect: {session_id[:5]}***")
                    return session_id
            
            logger.error("Login failed: No session ID found in cookies")
            logger.debug(f"Response status: {login_response.status_code}")
            logger.debug(f"Response URL: {login_response.url}")
            return None
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return None

def connect_with_session_id(session_id):
    """Connect to TradingView WebSocket using session ID cookie"""
    logger.info(f"Connecting to TradingView WebSocket with session ID cookie: {session_id[:5]}***")
    
    # Prepare WebSocket connection with cookie in headers
    socket_url = "wss://data.tradingview.com/socket.io/websocket"
    headers = {
        "Origin": "https://www.tradingview.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Cookie": f"sessionid={session_id}",
    }
    
    try:
        # Create WebSocket connection
        ws = websocket.create_connection(socket_url, header=headers)
        logger.info("WebSocket connection established!")
        
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
        
        # Add volume study
        send_message(ws, "create_study", [chart_session, "st1", "st1", "s1", "Volume@tv-basicstudies-118", {"length": 20, "col_prev_close": "false"}])
        
        # Listen for messages
        logger.info("\nListening for messages:")
        received_data = False
        
        for i in range(30):  # Listen for 30 messages or 30 seconds
            try:
                result = ws.recv()
                
                # Check for heartbeat message
                if "~h~" in result:
                    logger.info("Received heartbeat, responding...")
                    ws.send(result)
                else:
                    # Try to pretty print if it's a data update
                    if "du" in result and len(result) > 200:
                        logger.info(f"Message {i+1}: Data update received (length: {len(result)})")
                        received_data = True
                    else:
                        logger.info(f"Message {i+1}: {result[:200]}...")
                        
                # Check for errors
                if "\"m\":\"protocol_error\"" in result:
                    logger.error("!!! Protocol error detected !!!")
                    error_start = result.find("\"p\":")
                    error_end = result.find("]}", error_start)
                    error_msg = result[error_start:error_end+2]
                    logger.error(f"Error details: {error_msg}")
                    break
                
            except Exception as e:
                logger.error(f"Error receiving message: {e}")
                break
                
            # Add a small delay
            time.sleep(1)
        
        # Close connection
        ws.close()
        logger.info("Connection closed")
        
        # Return success based on whether we received data
        return received_data
        
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        return False

def load_saved_session():
    """Try to load previously saved session"""
    cookie_file = "tradingview_cookies.json"
    if os.path.exists(cookie_file):
        try:
            with open(cookie_file, "r") as f:
                cookies = json.load(f)
                if "sessionid" in cookies:
                    logger.info(f"Found saved session ID: {cookies['sessionid'][:5]}***")
                    return cookies["sessionid"]
        except Exception as e:
            logger.error(f"Error loading saved session: {e}")
    
    logger.info("No saved session found or session invalid")
    return None

def main():
    # First try to use saved session
    session_id = load_saved_session()
    
    if session_id:
        logger.info("Testing saved session...")
        if connect_with_session_id(session_id):
            logger.info("Saved session is valid!")
            return
        else:
            logger.info("Saved session is invalid or expired, need to login again")
    
    # If no saved session or saved session invalid, prompt for login
    username = input("Enter TradingView username: ")
    password = input("Enter TradingView password: ")
    
    session_id = stealth_login(username, password)
    
    if session_id:
        connect_with_session_id(session_id)
    else:
        logger.error("Failed to obtain session ID. Cannot connect to TradingView.")

if __name__ == "__main__":
    main() 
import requests
import json
import websocket
import time

def get_auth_token(username, password):
    print(f"Attempting to sign in with username: {username}")
    url = "https://www.tradingview.com/accounts/signin/"
    payload = {"username": username, "password": password, "remember": "on"}
    headers = {
        "Referer": "https://www.tradingview.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    try:
        resp = requests.post(url, data=payload, headers=headers)
        resp.raise_for_status()  # Raise exception for 4XX/5XX responses
        
        # Check if we got a JSON response
        try:
            data = resp.json()
            print("Got JSON response")
            
            if 'user' in data and 'auth_token' in data['user']:
                token = data['user']['auth_token']
                print(f"Authentication successful! Token: {token[:10]}...")
                return token
            else:
                print(f"Authentication response doesn't contain auth_token: {data}")
                return None
                
        except json.JSONDecodeError:
            print("Response is not JSON. Response content:")
            print(resp.text[:500])  # Print first 500 chars of response
            
            # Check if we got cookies
            if 'sessionid' in resp.cookies:
                session_id = resp.cookies['sessionid']
                print(f"Found sessionid cookie: {session_id}")
                return session_id
            else:
                print("No sessionid cookie found")
                return None
    
    except Exception as e:
        print(f"Error during authentication: {e}")
        return None

def connect_tradingview_websocket(auth_token):
    print(f"Connecting to TradingView WebSocket with auth token: {auth_token[:10]}...")
    
    # Prepare WebSocket connection
    socket_url = "wss://data.tradingview.com/socket.io/websocket"
    headers = {
        "Origin": "https://www.tradingview.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        # Create connection
        ws = websocket.create_connection(socket_url, header=headers)
        print("WebSocket connection established!")
        
        # Helper functions for TradingView WebSocket protocol
        def prepend_header(st):
            return "~m~" + str(len(st)) + "~m~" + st
            
        def construct_message(func, param_list):
            return json.dumps({"m": func, "p": param_list}, separators=(',', ':'))
            
        def create_message(func, args):
            return prepend_header(construct_message(func, args))
            
        def send_message(ws, func, args):
            message = create_message(func, args)
            print(f"Sending: {message[:100]}...")
            ws.send(message)
        
        # Send authentication message
        send_message(ws, "set_auth_token", [auth_token])
        
        # Create chart session
        chart_session = "cs_" + "".join([chr(97 + i) for i in range(12)])  # Random 12-char string
        print(f"Chart session ID: {chart_session}")
        send_message(ws, "chart_create_session", [chart_session, ""])
        
        # Watch for symbol (Bitcoin on Binance)
        send_message(ws, "resolve_symbol", [chart_session, "symbol_1", "={\"symbol\":\"BINANCE:BTCUSDT\",\"adjustment\":\"splits\"}"])
        send_message(ws, "create_series", [chart_session, "s1", "s1", "symbol_1", "1", 300])
        
        # Receive messages
        print("\nListening for messages:")
        for i in range(10):  # Listen for 10 messages
            try:
                result = ws.recv()
                print(f"Message {i+1}: {result[:200]}...")  # Print first 200 chars
                
                # Handle pings (~h~)
                if "~h~" in result:
                    ws.send(result)
                    print("Responded to ping")
            except Exception as e:
                print(f"Error receiving message: {e}")
                break
        
        # Close connection
        ws.close()
        print("Connection closed")
        
    except Exception as e:
        print(f"WebSocket connection error: {e}")

if __name__ == "__main__":
    username = "snell7579@gmail.com"
    password = "4dwlq5!H4uA26A8"
    
    # Get auth token
    auth_token = get_auth_token(username, password)
    
    if auth_token:
        # Connect to TradingView WebSocket
        connect_tradingview_websocket(auth_token)
    else:
        print("Failed to get authentication token. Cannot proceed.") 
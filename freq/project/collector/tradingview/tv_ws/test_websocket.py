import socketio
import time
import json

# Your TradingView session ID (from browser cookies or login):
session_id = "tkfi0exuv4mkvd8izlp1ev798qx1zdv3"  # Updated to match the actual cookie value


# Create a Socket.IO client instance
sio = socketio.Client()

# Define Socket.IO event handlers
@sio.event
def connect():
    print("Connected to TradingView!")

@sio.event
def connect_error(data):
    print(f"Connection error: {data}")

@sio.event
def disconnect():
    print("Disconnected from TradingView")

@sio.event
def message(data):
    print(f"Received message: {data}")

# Define custom event handlers (TradingView specific)
@sio.on('protocol_error')
def on_protocol_error(data):
    print(f"Protocol error: {data}")

@sio.on('critical_error')
def on_critical_error(data):
    print(f"Critical error: {data}")

@sio.on('series_completed')
def on_series_completed(data):
    print(f"Series completed: {data}")

@sio.on('du')
def on_du(data):
    print(f"Data update: {data}")

# Connect to TradingView Socket.IO server
try:
    print("Connecting to TradingView using Socket.IO...")
    
    # Prepare connection headers
    headers = {
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en-GB;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Origin": "https://www.tradingview.com",
        "Pragma": "no-cache",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "Cookie": f"sessionid={session_id}"
    }
    
    # First try data.tradingview.com
    try:
        sio.connect('https://data.tradingview.com', headers=headers, transports=['websocket'])
        print("Connected to data.tradingview.com!")
        
        # Wait for events
        time.sleep(10)
        
    except Exception as e:
        print(f"Failed to connect to data.tradingview.com: {e}")
        
        # Try with prodata.tradingview.com as fallback
        print("Trying prodata.tradingview.com...")
        try:
            sio.connect('https://prodata.tradingview.com', headers=headers, transports=['websocket'])
            print("Connected to prodata.tradingview.com!")
            
            # Wait for events
            time.sleep(10)
            
        except Exception as e:
            print(f"Failed to connect to prodata.tradingview.com: {e}")
    
    # Disconnect
    if sio.connected:
        sio.disconnect()
        
except Exception as e:
    print(f"Error: {e}")

print("Test complete") 
#!/usr/bin/env python3
import socketio
import argparse
import json
import time

def main():
    """
    TradingView Socket.IO testing tool using the python-socketio library
    Uses the session ID in the cookie header for authentication
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Simple TradingView Socket.IO Test")
    parser.add_argument("--session-id", required=True, help="TradingView session ID")
    parser.add_argument("--endpoint", default="https://data.tradingview.com", help="Socket.IO endpoint URL")
    parser.add_argument("--path", default="/socket.io", help="Socket.IO path")
    parser.add_argument("--duration", type=int, default=60, help="Duration to run in seconds")
    args = parser.parse_args()
    
    # Set up the Socket.IO client
    sio = socketio.Client(logger=True, engineio_logger=True)

    @sio.event
    def connect():
        print("✅ Connected!")

    @sio.event
    def connect_error(data):
        print(f"❌ Connection error: {data}")

    @sio.event
    def disconnect():
        print("❌ Disconnected!")

    @sio.on('*')
    def catch_all(event, data):
        print(f"Event: {event}, Data: {data}")

    # These headers should match your browser (for auth, anti-bot, etc.)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.3',
        'Origin': 'https://www.tradingview.com',
        'Referer': 'https://www.tradingview.com/',
        'Cookie': f'sessionid={args.session_id}',  # Add session ID cookie
    }

    try:
        # Connect to the endpoint (note: use https:// not wss:// for python-socketio)
        print(f"Connecting to {args.endpoint} with path {args.path}")
        print(f"Using session ID: {args.session_id[:5]}***")
        
        sio.connect(
            args.endpoint,
            socketio_path=args.path,
            headers=headers,
            transports=['websocket'],  # Forces upgrade to websocket only (skip polling)
            wait_timeout=10,
        )

        print(f"Listening for events for {args.duration} seconds...")
        
        # Example subscription for a symbol (adjust as needed)
        try:
            subscription_data = {
                'symbol': 'BINANCE:BTCUSDT',
                'resolution': '1',
                'type': 'quotes'
            }
            sio.emit('subscribe', subscription_data)
            print(f"Sent subscription for BINANCE:BTCUSDT")
        except Exception as e:
            print(f"Error sending subscription: {e}")

        # Wait for specified duration
        time.sleep(args.duration)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Disconnect if connected
        if sio.connected:
            sio.disconnect()
            print("Disconnected from server")

if __name__ == "__main__":
    main() 
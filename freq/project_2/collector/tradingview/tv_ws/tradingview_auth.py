import websocket
import json
import time
import threading

# === Your TradingView JWT token (REPLACE with your latest one!) ===
JWT_TOKEN = "eyJhbGciOiJSUzUxMiIsImtpZCI6IkdaeFUiLCJ0eXAiOiJKV1QifQ.eyJ1c2VyX2lkIjoxMDUxMzU3MDMsImV4cCI6MTc0ODE4NzIxNCwiaWF0IjoxNzQ4MTcyODE0LCJwbGFuIjoicHJvX3ByZW1pdW1fdHJpYWwiLCJkZWNsYXJlZF9zdGF0dXMiOiJub25fcHJvIiwiZXh0X2hvdXJzIjoxLCJwZXJtIjoiIiwic3R1ZHlfcGVybSI6InR2LXByb3N0dWRpZXMsdHYtY2hhcnRwYXR0ZXJucyx0di1jaGFydF9wYXR0ZXJucyx0di12b2x1bWVieXByaWNlIiwibWF4X3N0dWRpZXMiOjI1LCJtYXhfZnVuZGFtZW50YWxzIjoxMCwibWF4X2NoYXJ0cyI6OCwibWF4X2FjdGl2ZV9hbGVydHMiOjQwMCwibWF4X3N0dWR5X29uX3N0dWR5IjoyNCwiZmllbGRzX3Blcm1pc3Npb25zIjpbInJlZmJvbmRzIl0sIm1heF9hbGVydF9jb25kaXRpb25zIjo1LCJtYXhfb3ZlcmFsbF9hbGVydHMiOjIwMDAsIm1heF9vdmVyYWxsX3dhdGNobGlzdF9hbGVydHMiOjUsIm1heF9hY3RpdmVfcHJpbWl0aXZlX2FsZXJ0cyI6NDAwLCJtYXhfYWN0aXZlX2NvbXBsZXhfYWxlcnRzIjo0MDAsIm1heF9hY3RpdmVfd2F0Y2hsaXN0X2FsZXJ0cyI6MiwibWF4X2Nvbm5lY3Rpb25zIjo1MH0.sj_cY5X97Y4lShyxB9oaaLGbMakDLg3P_QwS1Z1CdQRIiM2w1ck-OuVV6zpexJ6yyMmFzED-7OM779tu_8xiETtU9Xu5vD4qJvNRqZh-7w7Au6-VEivgilnb9onIUMZuQiOcQLWzcflS97sGWgrOdHO7rODL8TjQJouXCLJwu9k"

# === TradingView WebSocket endpoint ===
TV_WS_URL = "wss://prodata.tradingview.com/socket.io/websocket"

# === Chart and symbol session names (can be anything unique) ===
chart_session = "cs_eth5s"
symbol_session = "sds_1"
series_id = "s1"

# === TradingView expects all payloads to be wrapped like this ===
def wrap_message(msg):
    return f"~m~{len(msg)}~m~{msg}"

def send_tv_msg(ws, msg_dict):
    msg = json.dumps(msg_dict)
    ws.send(wrap_message(msg))

def on_open(ws):
    print("[*] Connected, sending set_auth_token...")
    # 1. Authenticate
    send_tv_msg(ws, {"m": "set_auth_token", "p": [JWT_TOKEN]})
    time.sleep(1)  # Give a moment for authentication

    print("[*] Creating chart session...")
    # 2. Create chart session
    send_tv_msg(ws, {"m": "chart_create_session", "p": [chart_session, ""]})

    time.sleep(0.2)
    print("[*] Resolving symbol BINANCE:ETHUSDT.P...")
    # 3. Resolve symbol
    send_tv_msg(ws, {"m": "resolve_symbol", "p": [chart_session, symbol_session, "=\"BINANCE:ETHUSDT.P\""]})

    time.sleep(0.2)
    print("[*] Subscribing to 5s candle series...")
    # 4. Subscribe to 5s candles
    send_tv_msg(ws, {"m": "create_series", "p": [chart_session, series_id, symbol_session, "5", "5000", 1]})

    # (Optional) Keep-alive thread to send pings every 15 seconds
    def ping():
        while True:
            try:
                ws.send("~m~8~m~{\"m\":\"ping\"}")
                time.sleep(15)
            except:
                break
    threading.Thread(target=ping, daemon=True).start()

def on_message(ws, message):
    # Print only du (data update) messages
    if "\"m\":\"du\"" in message:
        # Extract the payload JSON (after TradingView's ~m~ framing)
        try:
            idx = message.find("{")
            if idx != -1:
                msg = json.loads(message[idx:])
                # Extract candle info if available
                if msg.get("m") == "du":
                    data = msg["p"][1]
                    for v in data.get("s1", {}).get("s", []):
                        ohlcv = v["v"]
                        print(f"[5s OHLCV] Time: {ohlcv[0]}, Open: {ohlcv[1]}, High: {ohlcv[2]}, Low: {ohlcv[3]}, Close: {ohlcv[4]}, Volume: {ohlcv[5]}")
        except Exception as e:
            print("[!] Error parsing du:", e)

def on_error(ws, error):
    print("[!] Error:", error)

def on_close(ws, close_status_code, close_msg):
    print("[*] Closed connection")

headers = {
    "Origin": "https://www.tradingview.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
}

ws = websocket.WebSocketApp(
    TV_WS_URL,
    header=[f"{k}: {v}" for k, v in headers.items()],
    on_open=on_open,
    on_message=on_message,
    on_error=on_error,
    on_close=on_close
)

print("Connecting to TradingView WebSocket...")
ws.run_forever()

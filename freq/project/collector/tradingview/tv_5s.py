import websocket
import json
import time
import threading
from urllib.parse import urlparse
import re
from datetime import datetime

TV_WS_URL = "wss://prodata.tradingview.com/socket.io/websocket"
HEADERS = {
    "Origin": "https://www.tradingview.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
}

AUTH_PAYLOAD = '{"m":"set_auth_token","p":["eyJhbGciOiJSUzUxMiIsImtpZCI6IkdaeFUiLCJ0eXAiOiJKV1QifQ.eyJ1c2VyX2lkIjoxMDUxMzU3MDMsImV4cCI6MTc0ODE5MDE3OSwiaWF0IjoxNzQ4MTc1Nzc5LCJwbGFuIjoicHJvX3ByZW1pdW1fdHJpYWwiLCJkZWNsYXJlZF9zdGF0dXMiOiJub25fcHJvIiwiZXh0X2hvdXJzIjoxLCJwZXJtIjoiIiwic3R1ZHlfcGVybSI6InR2LXByb3N0dWRpZXMsdHYtY2hhcnRwYXR0ZXJucyx0di1jaGFydF9wYXR0ZXJucyx0di12b2x1bWVieXByaWNlIiwibWF4X3N0dWRpZXMiOjI1LCJtYXhfZnVuZGFtZW50YWxzIjoxMCwibWF4X2NoYXJ0cyI6OCwibWF4X2FjdGl2ZV9hbGVydHMiOjQwMCwibWF4X3N0dWR5X29uX3N0dWR5IjoyNCwiZmllbGRzX3Blcm1pc3Npb25zIjpbInJlZmJvbmRzIl0sIm1heF9hbGVydF9jb25kaXRpb25zIjo1LCJtYXhfb3ZlcmFsbF9hbGVydHMiOjIwMDAsIm1heF9vdmVyYWxsX3dhdGNobGlzdF9hbGVydHMiOjUsIm1heF9hY3RpdmVfcHJpbWl0aXZlX2FsZXJ0cyI6NDAwLCJtYXhfYWN0aXZlX2NvbXBsZXhfYWxlcnRzIjo0MDAsIm1heF9hY3RpdmVfd2F0Y2hsaXN0X2FsZXJ0cyI6MiwibWF4X2Nvbm5lY3Rpb25zIjo1MH0.Fk_Qr-SsuDDFvQXCP-4jJOIZeRB3ytRZ2Sa9ERIUfMLMEucNqlzLW0nBUchMvMgf7chgb_RbhCqSpSzleyjQYl6PoJP3RYa-GUNtew1iPf6vab9AE425d_cNU67L5EDQrC1DkEdfuKArcJBBpVi0zIDoDGz3HRXlVzC8tr0-0Ic"]}'
CHART_SESSION_ID = "cs_RlEFHlg56lDq"
RESOLVE_SYMBOL_PAYLOAD = json.dumps({
    "m": "resolve_symbol",
    "p": [
        CHART_SESSION_ID,
        "sds_sym_1",
        '={"adjustment":"splits","currency-id":"XTVCUSDT","session":"regular","symbol":"BINANCE:ETHUSDT.P"}'
    ]
})
CHART_CREATE_SESSION_PAYLOAD = json.dumps({"m": "chart_create_session", "p": [CHART_SESSION_ID, ""]})
CREATE_SERIES_PAYLOAD = json.dumps({
    "m": "create_series",
    "p": [CHART_SESSION_ID, "sds_1", "s1", "sds_sym_1", "5S", 300, ""]
})

def wrap_message(msg: str) -> str:
    return f"~m~{len(msg)}~m~{msg}"

def send_message(ws, msg):
    ws.send(wrap_message(msg))

def send_pong(ws, heartbeat_msg):
    ws.send(heartbeat_msg)

def split_tradingview_messages(raw):
    messages = []
    while raw:
        match = re.match(r"~m~(\d+)~m~", raw)
        if not match:
            break
        length = int(match.group(1))
        start = match.end()
        end = start + length
        json_part = raw[start:end]
        messages.append(json_part)
        raw = raw[end:]
    return messages

def on_open(ws):
    send_message(ws, AUTH_PAYLOAD)
    def delayed_sequence():
        time.sleep(1)
        send_message(ws, CHART_CREATE_SESSION_PAYLOAD)
        time.sleep(1)
        send_message(ws, RESOLVE_SYMBOL_PAYLOAD)
        time.sleep(1)
        send_message(ws, CREATE_SERIES_PAYLOAD)
    threading.Thread(target=delayed_sequence, daemon=True).start()

# Track current candle data
current_candle_time = None
current_candle_data = None
# Flag to print all raw messages after first error
print_raw_messages = False

def on_message(ws, message):
    global current_candle_time, current_candle_data, print_raw_messages
    if print_raw_messages:
        print(f"[RAW] {repr(message)}")
    for json_part in split_tradingview_messages(message):
        try:
            # Skip empty or whitespace-only parts
            if not json_part or not json_part.strip():
                continue
            # If this is a heartbeat, echo the full frame back
            if re.match(r"^~h~\d+$", json_part):
                # Re-wrap the heartbeat in the TradingView frame and send it back
                frame = f"~m~{len(json_part)}~m~{json_part}"
                ws.send(frame)
                continue
            parsed = json.loads(json_part)
            if parsed.get("m") == "du":
                p = parsed.get("p", [])
                if len(p) > 1 and isinstance(p[1], dict):
                    sds_1 = p[1].get("sds_1", {})
                    if "s" in sds_1:
                        for bar in sds_1["s"]:
                            ohlcv = bar["v"]
                            candle_time = int(ohlcv[0])
                            
                            # If we see a new candle time, print the previous one first
                            if current_candle_time is not None and candle_time != current_candle_time:
                                dt = datetime.utcfromtimestamp(current_candle_time)
                                print(f"{dt.strftime('%H:%M:%S')} {current_candle_data[1]} {current_candle_data[2]} {current_candle_data[3]} {current_candle_data[4]} {current_candle_data[5]}")
                            
                            # Update current candle data
                            current_candle_time = candle_time
                            current_candle_data = ohlcv
        except Exception as e:
            print(f"Error processing message: {e} | json_part: {repr(json_part)} | FULL RAW MESSAGE: {repr(message)}")
            print_raw_messages = True

def on_error(ws, error):
    print(f"WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    print(f"WebSocket closed (code={close_status_code}, msg={close_msg})")

def main():
    ws = websocket.WebSocketApp(
        TV_WS_URL,
        header=[f"{k}: {v}" for k, v in HEADERS.items()],
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    try:
        websocket.enableTrace(False)
        ws.run_forever()
    except KeyboardInterrupt:
        # Print the final candle data before exiting
        if current_candle_time is not None and current_candle_data is not None:
            dt = datetime.utcfromtimestamp(current_candle_time)
            print(f"{dt.strftime('%H:%M:%S')} {current_candle_data[1]} {current_candle_data[2]} {current_candle_data[3]} {current_candle_data[4]} {current_candle_data[5]}")
        print("Keyboard interrupt received, shutting down...")
    except Exception as e:
        print(f"Unhandled exception: {e}")
    finally:
        print("WebSocket client terminated")

if __name__ == "__main__":
    main() 
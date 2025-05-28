import websocket
import json
import logging
import datetime
import traceback
import time
import threading
from urllib.parse import urlparse
import re
from datetime import datetime

# =========================
# CONFIGURATION & CONSTANTS
# =========================

TV_WS_URL = "wss://prodata.tradingview.com/socket.io/websocket"
HEADERS = {
    "Origin": "https://www.tradingview.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
}

# Replace with your actual token
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

# =========================
# LOGGING SETUP
# =========================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('tv_websocket')

# =========================
# UTILITY FUNCTIONS
# =========================

def wrap_message(msg: str) -> str:
    """Wrap message in TradingView's ~m~{length}~m~{message} format."""
    return f"~m~{len(msg)}~m~{msg}"

def parse_message(message: str):
    """Parse TradingView's ~m~ framed messages into JSON if possible."""
    try:
        idx = message.find("{")
        if idx != -1:
            return json.loads(message[idx:])
        return {"raw": message}
    except Exception as e:
        logger.warning(f"Failed to parse message as JSON: {e}")
        return {"raw": message}

def send_message(ws, msg, description=""):
    """Send a message with logging."""
    try:
        wrapped = wrap_message(msg)
        logger.info(f"Sending {description} (len={len(msg)})")
        ws.send(wrapped)
        return True
    except Exception as e:
        logger.error(f"Error sending {description}: {e}")
        logger.error(traceback.format_exc())
        return False

def send_pong(ws, heartbeat_msg):
    logger.info(f"Sending pong: {heartbeat_msg}")
    ws.send(heartbeat_msg)

def split_tradingview_messages(raw):
    """Split a TradingView WebSocket message into individual JSON payloads."""
    messages = []
    while raw:
        match = re.match(r"~m~(\\d+)~m~", raw)
        if not match:
            break
        length = int(match.group(1))
        start = match.end()
        end = start + length
        json_part = raw[start:end]
        messages.append(json_part)
        raw = raw[end:]
    return messages

# =========================
# CALLBACKS
# =========================

def on_open(ws):
    logger.info(f"WebSocket connection opened to {urlparse(ws.url).netloc}")
    send_message(ws, AUTH_PAYLOAD, "authentication token")
    # Wait a moment, then send chart_create_session, resolve_symbol, and create_series
    def delayed_sequence():
        time.sleep(1)
        send_message(ws, CHART_CREATE_SESSION_PAYLOAD, "chart_create_session")
        time.sleep(1)
        send_message(ws, RESOLVE_SYMBOL_PAYLOAD, "resolve_symbol")
        time.sleep(1)
        send_message(ws, CREATE_SERIES_PAYLOAD, "create_series")
    threading.Thread(target=delayed_sequence, daemon=True).start()

last_candle_time = None

def on_message(ws, message):
    global last_candle_time
    if message.startswith("~m~4~m~~h~"):
        send_pong(ws, message)
        return
    for json_part in split_tradingview_messages(message):
        try:
            parsed = json.loads(json_part)
            if parsed.get("m") == "du":
                p = parsed.get("p", [])
                if len(p) > 1 and isinstance(p[1], dict):
                    sds_1 = p[1].get("sds_1", {})
                    if "s" in sds_1:
                        for bar in sds_1["s"]:
                            ohlcv = bar["v"]
                            candle_time = int(ohlcv[0])
                            if candle_time != last_candle_time:
                                last_candle_time = candle_time
                                dt = datetime.utcfromtimestamp(candle_time)
                                # Print as: HH:MM:SS O H L C V
                                print(f"{dt.strftime('%H:%M:%S')} {ohlcv[1]} {ohlcv[2]} {ohlcv[3]} {ohlcv[4]} {ohlcv[5]}")
        except Exception:
            pass

def on_error(ws, error):
    logger.error(f"WebSocket error: {error}")
    logger.error(traceback.format_exc())

def on_close(ws, close_status_code, close_msg):
    logger.info(f"WebSocket closed (code={close_status_code}, msg={close_msg})")

# =========================
# MAIN ENTRY POINT
# =========================

def main():
    logger.info("Starting TradingView WebSocket client...")
    ws = websocket.WebSocketApp(
        TV_WS_URL,
        header=[f"{k}: {v}" for k, v in HEADERS.items()],
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    try:
        websocket.enableTrace(False)  # Set True for very verbose debug
        ws.run_forever()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}")
        logger.critical(traceback.format_exc())
    finally:
        logger.info("WebSocket client terminated")

if __name__ == "__main__":
    main() 
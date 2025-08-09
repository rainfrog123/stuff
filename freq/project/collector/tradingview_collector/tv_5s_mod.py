import websocket
import json
import time
import threading
import asyncio
import re
from datetime import datetime
from typing import AsyncGenerator, Dict, Any, Optional

TV_WS_URL = "wss://prodata.tradingview.com/socket.io/websocket"
HEADERS = {
    "Origin": "https://www.tradingview.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
}

AUTH_PAYLOAD = '{"m":"set_auth_token","p":["eyJhbGciOiJSUzUxMiIsImtpZCI6IkdaeFUiLCJ0eXAiOiJKV1QifQ.eyJ1c2VyX2lkIjoxMDcyNjQ5MDMsImV4cCI6MTc0ODQ3NDMxOSwiaWF0IjoxNzQ4NDU5OTE5LCJwbGFuIjoicHJvX3ByZW1pdW1fdHJpYWwiLCJwcm9zdGF0dXMiOiJub25fcHJvIiwiZXh0X2hvdXJzIjoxLCJwZXJtIjoiIiwic3R1ZHlfcGVybSI6InR2LXByb3N0dWRpZXMsdHYtY2hhcnRwYXR0ZXJucyx0di1jaGFydF9wYXR0ZXJucyx0di12b2x1bWVieXByaWNlIiwibWF4X3N0dWRpZXMiOjI1LCJtYXhfZnVuZGFtZW50YWxzIjoxMCwibWF4X2NoYXJ0cyI6OCwibWF4X2FjdGl2ZV9hbGVydHMiOjQwMCwibWF4X3N0dWR5X29uX3N0dWR5IjoyNCwiZmllbGRzX3Blcm1pc3Npb25zIjpbInJlZmJvbmRzIl0sIm1heF9hbGVydF9jb25kaXRpb25zIjo1LCJtYXhfb3ZlcmFsbF9hbGVydHMiOjIwMDAsIm1heF9vdmVyYWxsX3dhdGNobGlzdF9hbGVydHMiOjUsIm1heF9hY3RpdmVfcHJpbWl0aXZlX2FsZXJ0cyI6NDAwLCJtYXhfYWN0aXZlX2NvbXBsZXhfYWxlcnRzIjo0MDAsIm1heF9hY3RpdmVfd2F0Y2hsaXN0X2FsZXJ0cyI6MiwibWF4X2Nvbm5lY3Rpb25zIjo1MH0.jCnGIXp99XUBxyFvdLm2xJkGusKaFsME51W0RNfWuGFGWGJiJG3Le0XIq5SFQ9om0l1yCOyO_mw3J44HyAweIsACDzOXbk8DRQz4C0AM8L2zbGUHe5mL8cwv3Dm3HxTUYVClF9LFt7Azlc_KGSo3d5wXpkgBkzbWyzkURq7yBeA"]}'
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

class TradingView5sCandleClient:
    def __init__(self):
        self.ws = None
        self._loop = None
        self._thread = None
        self._queue: Optional[asyncio.Queue] = None
        self._current_candle_time = None
        self._current_candle_data = None
        self._stop_event = threading.Event()

    def _on_open(self, ws):
        ws.send(wrap_message(AUTH_PAYLOAD))
        def delayed_sequence():
            time.sleep(1)
            ws.send(wrap_message(CHART_CREATE_SESSION_PAYLOAD))
            time.sleep(1)
            ws.send(wrap_message(RESOLVE_SYMBOL_PAYLOAD))
            time.sleep(1)
            ws.send(wrap_message(CREATE_SERIES_PAYLOAD))
        threading.Thread(target=delayed_sequence, daemon=True).start()

    def _on_message(self, ws, message):
        for json_part in split_tradingview_messages(message):
            try:
                if not json_part or not json_part.strip():
                    continue
                if re.match(r"^~h~\d+$", json_part):
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
                                if self._current_candle_time is not None and candle_time != self._current_candle_time:
                                    # Yield the previous candle
                                    dt = datetime.utcfromtimestamp(self._current_candle_time)
                                    candle = {
                                        "time": dt,
                                        "open": self._current_candle_data[1],
                                        "high": self._current_candle_data[2],
                                        "low": self._current_candle_data[3],
                                        "close": self._current_candle_data[4],
                                        "volume": self._current_candle_data[5],
                                    }
                                    if self._queue:
                                        asyncio.run_coroutine_threadsafe(self._queue.put(candle), self._loop)
                                self._current_candle_time = candle_time
                                self._current_candle_data = ohlcv
            except Exception:
                continue

    def _on_error(self, ws, error):
        pass

    def _on_close(self, ws, close_status_code, close_msg):
        pass

    def _run_ws(self):
        self.ws = websocket.WebSocketApp(
            TV_WS_URL,
            header=[f"{k}: {v}" for k, v in HEADERS.items()],
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )
        self.ws.run_forever()

    async def candle_generator(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Async generator yielding 5s OHLCV candles as dicts."""
        self._queue = asyncio.Queue()
        self._loop = asyncio.get_event_loop()
        self._thread = threading.Thread(target=self._run_ws, daemon=True)
        self._thread.start()
        try:
            while True:
                candle = await self._queue.get()
                yield candle
        finally:
            self._stop_event.set()
            if self.ws:
                self.ws.close() 
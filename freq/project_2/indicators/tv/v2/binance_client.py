#!/allah/freqtrade/.venv/bin/python3.11

from binance.client import Client
from binance.exceptions import BinanceAPIException
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal
import time
import traceback
import asyncio

from logger import logger
from utils import calculate_min_order_amount, parse_position_data, round_to_precision, get_quantity_precision, get_price_precision

class BinanceClient:
    def __init__(self, api_key: str, api_secret: str):
        """
        Initialize the Binance client wrapper with API credentials.
        
        Args:
            api_key: Binance API key
            api_secret: Binance API secret
        """
        self.client = Client(api_key, api_secret)
        self._validate_api_keys()
        
    def _validate_api_keys(self) -> None:
        """Validate that API keys are working properly."""
        try:
            self.client.get_account_status()
            logger.info("API keys validated successfully")
        except BinanceAPIException as e:
            logger.error(f"API key validation failed: {e}")
            raise RuntimeError("Invalid API keys or insufficient permissions")
            
    def set_leverage(self, symbol: str, leverage: int) -> bool:
        """
        Set leverage for a specific symbol.
        
        Args:
            symbol: Trading symbol (in Binance futures format, e.g., 'ETHUSDT')
            leverage: Leverage value (e.g., 1-125 depending on the symbol)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            response = self.client.futures_change_leverage(
                symbol=symbol,
                leverage=leverage
            )
            logger.info(f"Changed leverage to {leverage}x for {symbol}")
            return True
        except BinanceAPIException as e:
            logger.error(f"Error setting leverage to {leverage}x: {e}")
            return False
            
    def get_balance(self) -> Dict[str, Any]:
        """
        Get account balance information.
        
        Returns:
            Dict containing balance information
        """
        try:
            futures_account = self.client.futures_account()
            assets = futures_account.get('assets', [])
            
            # Extract USDT balance
            usdt_balance = None
            for asset in assets:
                if asset.get('asset') == 'USDT':
                    usdt_balance = {
                        'free': float(asset.get('availableBalance', 0)),
                        'total': float(asset.get('walletBalance', 0))
                    }
                    break
                    
            if not usdt_balance:
                return {'USDT': {'free': 0.0, 'total': 0.0}}
                
            return {'USDT': usdt_balance}
        except BinanceAPIException as e:
            logger.error(f"Error getting balance: {e}")
            return {'USDT': {'free': 0.0, 'total': 0.0}}
            
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get current ticker information for a symbol.
        
        Args:
            symbol: Trading symbol (in Binance futures format, e.g., 'ETHUSDT')
            
        Returns:
            Dict with ticker information
        """
        try:
            ticker = self.client.futures_ticker(symbol=symbol)
            return {
                'symbol': ticker.get('symbol', symbol),
                'last': float(ticker.get('lastPrice', 0)),
                'bid': float(ticker.get('bidPrice', 0)), 
                'ask': float(ticker.get('askPrice', 0)),
                'volume': float(ticker.get('volume', 0)),
                'quoteVolume': float(ticker.get('quoteVolume', 0))
            }
        except BinanceAPIException as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            return {'symbol': symbol, 'last': 0, 'bid': 0, 'ask': 0, 'volume': 0, 'quoteVolume': 0}
            
    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get current position for a symbol.
        
        Args:
            symbol: Trading symbol (in Binance futures format, e.g., 'ETHUSDT')
            
        Returns:
            Position information or None if no position exists
        """
        try:
            positions = self.client.futures_position_information(symbol=symbol)
            return parse_position_data(positions, symbol)
        except BinanceAPIException as e:
            logger.error(f"Error fetching position for {symbol}: {e}")
            return None
            
    def get_orderbook(self, symbol: str) -> Dict[str, Any]:
        """
        Get current orderbook for a symbol.
        
        Args:
            symbol: Trading symbol (in Binance futures format, e.g., 'ETHUSDT')
            
        Returns:
            Dict with orderbook information
        """
        try:
            depth = self.client.futures_order_book(symbol=symbol, limit=5)
            return {
                'bids': [[float(price), float(qty)] for price, qty in depth.get('bids', [])],
                'asks': [[float(price), float(qty)] for price, qty in depth.get('asks', [])]
            }
        except BinanceAPIException as e:
            logger.error(f"Error fetching orderbook for {symbol}: {e}")
            return {'bids': [], 'asks': []}
            
    def cancel_all_orders(self, symbol: str) -> bool:
        """
        Cancel all active orders for a symbol.
        
        Args:
            symbol: Trading symbol (in Binance futures format, e.g., 'ETHUSDT')
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.client.futures_cancel_all_open_orders(symbol=symbol)
            logger.info(f"Cancelled all open orders for {symbol}")
            return True
        except BinanceAPIException as e:
            logger.error(f"Error cancelling orders for {symbol}: {e}")
            return False
            
    def place_order(self, symbol: str, side: str, order_type: str, 
                    quantity: float, price: Optional[float] = None, 
                    reduce_only: bool = False) -> Optional[Dict[str, Any]]:
        """
        Place an order on Binance Futures.
        
        Args:
            symbol: Trading symbol (in Binance futures format, e.g., 'ETHUSDT')
            side: Order side ('BUY' or 'SELL')
            order_type: Order type ('MARKET' or 'LIMIT')
            quantity: Order quantity
            price: Order price (required for LIMIT orders)
            reduce_only: Whether the order should be reduce-only
            
        Returns:
            Order information or None if failed
        """
        try:
            # Round quantity to the appropriate precision for the symbol
            quantity_precision = get_quantity_precision(symbol)
            quantity = round_to_precision(quantity, quantity_precision)
            
            # Round price to appropriate precision for LIMIT orders
            if price is not None and order_type.upper() == 'LIMIT':
                # Get the appropriate price precision for the symbol
                price_precision = get_price_precision(symbol)
                price = round_to_precision(price, price_precision)
            
            params = {
                'symbol': symbol,
                'side': side.upper(),
                'quantity': quantity,
                'reduceOnly': 'true' if reduce_only else 'false'
            }
            
            if order_type.upper() == 'LIMIT':
                if price is None:
                    raise ValueError("Price is required for LIMIT orders")
                
                params.update({
                    'type': 'LIMIT',
                    'price': price,
                    'timeInForce': 'GTX'  # POST_ONLY - will only execute as maker order
                })
            else:
                params.update({
                    'type': 'MARKET'
                })
                
            order = self.client.futures_create_order(**params)
            logger.info(f"Placed {side} {order_type} order for {quantity} at {price if price else 'MARKET'}")
            return order
            
        except BinanceAPIException as e:
            error_code = str(e.code) if hasattr(e, 'code') else 'Unknown'
            error_msg = str(e.message) if hasattr(e, 'message') else str(e)
            
            logger.error(f"Error placing order (code {error_code}): {error_msg}")
            logger.error(f"Order details: {side} {order_type} {quantity} {symbol} reduce_only={reduce_only}")
            
            return None
        except Exception as e:
            logger.error(f"Unexpected error placing order: {e}")
            logger.error(traceback.format_exc())
            return None
            
    def get_order(self, symbol: str, order_id: int) -> Optional[Dict[str, Any]]:
        """
        Get order details by order ID.
        
        Args:
            symbol: Trading symbol (in Binance futures format, e.g., 'ETHUSDT')
            order_id: The order ID to retrieve
            
        Returns:
            Order information or None if failed
        """
        try:
            order = self.client.futures_get_order(
                symbol=symbol,
                orderId=order_id
            )
            return order
        except BinanceAPIException as e:
            logger.error(f"Error fetching order {order_id}: {e}")
            return None
            
    def cancel_order(self, symbol: str, order_id: int) -> bool:
        """
        Cancel a specific order by order ID.
        
        Args:
            symbol: Trading symbol (in Binance futures format, e.g., 'ETHUSDT')
            order_id: The order ID to cancel
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.client.futures_cancel_order(
                symbol=symbol,
                orderId=order_id
            )
            logger.info(f"Cancelled order {order_id} for {symbol}")
            return True
        except BinanceAPIException as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False 
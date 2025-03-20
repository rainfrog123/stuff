#!/allah/freqtrade/.venv/bin/python3.11

import ccxt
import time
import datetime
import threading
import readline
import logging
import sys
import queue
import math
from typing import Optional, Dict, Any

# Create a queue for log messages
log_queue = queue.Queue()

# Custom handler that puts messages in queue instead of directly to console
class QueueHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            log_queue.put(msg)
        except Exception:
            self.handleError(record)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trading_assistant.log"),
        QueueHandler()  # Use our custom handler for console output
    ]
)
logger = logging.getLogger("BinanceAssistant")

# Function to print logs in a separate thread
def log_printer():
    while True:
        try:
            # Print logs from the queue
            while not log_queue.empty():
                # Get log message
                log_message = log_queue.get()
                
                # Print the log with a trailing newline to ensure prompt stays clean
                sys.stdout.write(f"{log_message}\n")
                sys.stdout.flush()
                
            time.sleep(0.1)
        except Exception as e:
            print(f"Error in log printer: {e}")
            time.sleep(1)

# Custom print function that won't interfere with input prompt
def safe_print(message):
    """Print a message that won't be overwritten by logs."""
    sys.stdout.write(f"\n{message}")
    sys.stdout.flush()

# Start log printer thread
log_thread = threading.Thread(target=log_printer, daemon=True)
log_thread.start()

class BinanceAssistant:
    def __init__(self, api_key: str, api_secret: str, symbol: str = 'ETH/USDT:USDT'):
        """
        Initialize the Binance trading assistant.
        
        Args:
            api_key: Binance API key
            api_secret: Binance API secret
            symbol: Trading pair symbol (default: ETH/USDT:USDT for perpetual futures)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.symbol = symbol
        self.active_order_id: Optional[str] = None
        self.position_side: Optional[str] = None
        self.entry_price: Optional[float] = None
        self.entry_time: Optional[datetime.datetime] = None
        self.candle_count = 0
        self.limit_order_thread: Optional[threading.Thread] = None
        self.stop_threads = False
        self.current_leverage = 125  # Default leverage at 125x
        self.exchange = self._initialize_exchange()
        
        # Start position monitor thread
        self.position_monitor_thread = threading.Thread(target=self._monitor_positions, daemon=True)
        self.position_monitor_thread.start()
    
    def _initialize_exchange(self) -> ccxt.binance:
        """Initialize the CCXT Binance exchange instance."""
        exchange = ccxt.binance({
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',  # Use futures for leverage trading
            }
        })
        
        # Load markets to ensure symbol data is available
        exchange.load_markets()
        
        # Set leverage for ETH trading
        try:
            exchange.set_leverage(self.current_leverage, self.symbol)
            logger.info(f"Set leverage to {self.current_leverage}x for {self.symbol}")
        except Exception as e:
            logger.error(f"Error setting leverage: {e}")
        
        logger.info(f"Connected to Binance, trading {self.symbol} with {self.current_leverage}x leverage")
        return exchange
    
    def set_leverage(self, leverage: int) -> bool:
        """
        Set the leverage for trading.
        
        Args:
            leverage: The leverage multiplier (e.g., 125, 120, 115)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.exchange.set_leverage(leverage, self.symbol)
            self.current_leverage = leverage
            logger.info(f"Changed leverage to {leverage}x for {self.symbol}")
            return True
        except Exception as e:
            logger.error(f"Error setting leverage to {leverage}x: {e}")
            return False
    
    def get_orderbook(self) -> Dict[str, Any]:
        """Get the current orderbook for the symbol."""
        return self.exchange.fetch_order_book(self.symbol)
    
    def get_best_price(self, side: str) -> float:
        """
        Get the best available price in the orderbook.
        
        Args:
            side: 'buy' or 'sell'
            
        Returns:
            float: Best price for the specified side
        """
        orderbook = self.get_orderbook()
        if side == 'buy':
            return orderbook['asks'][0][0]  # Lowest ask price
        else:
            return orderbook['bids'][0][0]  # Highest bid price
    
    def place_limit_order(self, side: str, is_entry: bool = True) -> None:
        """
        Place a limit order with the best available price.
        Continuously adjust the price if it changes to ensure fast execution.
        
        Args:
            side: 'buy' or 'sell'
            is_entry: Whether this is an entry order (True) or exit order (False)
        """
        # Reset the stop flag for threads
        self.stop_threads = False
        
        # Launch order management in a thread
        self.limit_order_thread = threading.Thread(
            target=self._manage_limit_order,
            args=(side, is_entry)
        )
        self.limit_order_thread.daemon = True
        self.limit_order_thread.start()
    
    def _manage_limit_order(self, side: str, is_entry: bool) -> None:
        """
        Thread function to manage the limit order placement and updates.
        
        Args:
            side: 'buy' or 'sell'
            is_entry: Whether this is an entry order (True) or exit order (False)
        """
        start_time = datetime.datetime.now()
        self.candle_count = 0
        max_candles = 3  # Max 3 candles (15 seconds in 5s timeframe)
        current_leverage = self.current_leverage  # Store but don't modify
        
        # For exit orders, get current position information
        position_amount = None
        if not is_entry:
            try:
                # Fetch positions to get the actual position size
                positions = self.exchange.fetch_positions(symbols=[self.symbol])
                for position in positions:
                    if position['symbol'] == self.symbol and abs(float(position['contracts'])) > 0:
                        # Use the absolute position size
                        position_amount = abs(float(position['contracts']))
                        logger.info(f"Found existing position of {position_amount} {self.symbol}")
                        break
                
                # If position not found through fetch_positions, try another method
                if position_amount is None or position_amount < 0.001:
                    # Fallback method - use minimum size
                    position_amount = 0.001
                    logger.warning(f"Could not determine position size, using minimum: {position_amount}")
            except Exception as e:
                logger.error(f"Error getting position size: {e}")
                # Use minimum order size as fallback
                position_amount = 0.001
        
        # Track how much has been filled so far (for partial fills)
        filled_amount = 0.0
        target_amount = None
        
        # Error tracking to avoid infinite loops
        consecutive_error_count = 0
        max_consecutive_errors = 5
        last_error_message = ""
        
        while not self.stop_threads:
            try:
                # If we've seen the same error multiple times, abort the operation
                if consecutive_error_count >= max_consecutive_errors:
                    logger.error(f"Aborting after {consecutive_error_count} consecutive errors: {last_error_message}")
                    self.stop_threads = True
                    
                    # For exit orders, try force close as fallback
                    if not is_entry:
                        logger.info("Trying force close as fallback after multiple errors...")
                        self.force_close_position()
                    break
                
                # For exit orders, verify if we still have a position before continuing
                if not is_entry:
                    has_position = False
                    try:
                        positions = self.exchange.fetch_positions(symbols=[self.symbol])
                        for position in positions:
                            if position['symbol'] == self.symbol and abs(float(position['contracts'])) > 0.0001:
                                has_position = True
                                break
                        
                        if not has_position:
                            logger.info("Position already closed - stopping order loop")
                            self.position_side = None
                            self.entry_price = None
                            self.entry_time = None
                            self.active_order_id = None
                            self.stop_threads = True
                            break
                    except Exception as check_err:
                        logger.error(f"Error checking position at start of loop: {check_err}")
                
                # Check and cancel any existing orders first
                if not is_entry:
                    try:
                        # Cancel any existing orders that might conflict with our reduceOnly order
                        open_orders = self.exchange.fetch_open_orders(symbol=self.symbol)
                        if open_orders:
                            logger.info(f"Cancelling {len(open_orders)} existing open orders...")
                            for order in open_orders:
                                try:
                                    self.exchange.cancel_order(order['id'], self.symbol)
                                except Exception as cancel_err:
                                    logger.warning(f"Error cancelling order {order['id']}: {cancel_err}")
                    except Exception as list_err:
                        logger.warning(f"Error fetching open orders: {list_err}")
                
                # Cancel any existing active order
                if self.active_order_id:
                    try:
                        # Check if the order ID is valid before fetching
                        if self.active_order_id and len(str(self.active_order_id)) > 5:
                            order_status = self.exchange.fetch_order(self.active_order_id, self.symbol)
                            
                            # Check if order was partially filled before canceling
                            if order_status['status'] == 'open' and order_status.get('filled', 0) > 0:
                                partial_fill = float(order_status.get('filled', 0))
                                filled_amount += partial_fill
                                logger.info(f"Order partially filled: {partial_fill} ({filled_amount} total)")
                            
                            # Cancel the order to place a new one
                            self.exchange.cancel_order(self.active_order_id, self.symbol)
                            logger.info(f"Cancelled previous order: {self.active_order_id}")
                        else:
                            logger.warning(f"Invalid order ID: {self.active_order_id}, skipping fetch/cancel")
                    except Exception as e:
                        logger.warning(f"Error cancelling previous order: {e}")
                    self.active_order_id = None
                
                # Get the current best price
                price = self.get_best_price('sell' if side == 'buy' else 'buy')
                
                # Calculate order amount
                if target_amount is None:  # Only calculate once
                    if is_entry:
                        # For entry orders, calculate based on full balance and leverage
                        balance = self.exchange.fetch_balance()
                        usdt_balance = balance['USDT']['free']  # Use 100% of balance
                        target_amount = (usdt_balance * current_leverage) / price
                    else:
                        # For exit orders, use the position amount we determined earlier
                        target_amount = position_amount
                
                # Calculate remaining amount needed to complete the order
                remaining_amount = max(0, target_amount - filled_amount)
                
                # Ensure order meets minimum notional value (20 USDT)
                min_amount = self.get_min_order_amount(price)
                
                if remaining_amount < min_amount:
                    if filled_amount > 0:
                        # We've already filled part of the order
                        logger.info(f"Remaining amount {remaining_amount} is below minimum notional value. Order considered complete.")
                        
                        if is_entry:
                            self.position_side = side
                            self.entry_price = price
                            self.entry_time = datetime.datetime.now()
                        else:
                            # For exit orders, check if we've closed most of the position
                            if filled_amount >= (target_amount * 0.95):  # 95% filled
                                self.position_side = None
                                self.entry_price = None
                                self.entry_time = None
                            else:
                                logger.warning(f"Position partially closed ({filled_amount}/{target_amount}). Using force close to complete.")
                                # Try to force close the remainder
                                self.force_close_position()
                        
                        self.stop_threads = True
                        break
                    else:
                        # No fills yet, use minimum order size
                        remaining_amount = min_amount
                        logger.info(f"Using minimum order size to meet 20 USDT notional requirement: {min_amount}")
                
                # For entry orders, enforce the 3-candle limit
                if is_entry and filled_amount == 0:  # Only check timeout if nothing filled yet
                    elapsed_time = datetime.datetime.now() - start_time
                    # Check if we've exceeded the 3-candle limit (15 seconds for 5s timeframe)
                    if elapsed_time.total_seconds() > 15:
                        logger.info("3 candles passed without filling the entry order. Cancelling.")
                        self.stop_threads = True
                        continue
                
                # Skip order placement if we've filled everything we need
                if remaining_amount <= 0:
                    logger.info(f"Order completely filled ({filled_amount}/{target_amount})")
                    
                    if is_entry:
                        self.position_side = side
                        self.entry_price = price
                        self.entry_time = datetime.datetime.now()
                    else:
                        self.position_side = None
                        self.entry_price = None
                        self.entry_time = None
                    
                    self.stop_threads = True
                    break
                
                # For exit orders, check one more time if the position still exists
                if not is_entry:
                    has_position = False
                    try:
                        positions = self.exchange.fetch_positions(symbols=[self.symbol])
                        for position in positions:
                            if position['symbol'] == self.symbol and abs(float(position['contracts'])) > 0.0001:
                                has_position = True
                                break
                        
                        if not has_position:
                            logger.info("Position already closed - no need to place another order")
                            self.position_side = None
                            self.entry_price = None
                            self.entry_time = None
                            self.stop_threads = True
                            break
                    except Exception as check_err:
                        logger.error(f"Error checking position before order placement: {check_err}")
                
                # Place a new limit order for the remaining amount
                order_params = {
                    'symbol': self.symbol,
                    'type': 'limit',
                    'side': side,
                    'amount': remaining_amount,
                    'price': price
                }
                
                # Add reduceOnly flag for exit orders
                if not is_entry:
                    if 'params' not in order_params:
                        order_params['params'] = {}
                    order_params['params']['reduceOnly'] = True
                
                try:
                    order = self.exchange.create_order(**order_params)
                    
                    # Reset error counter on success
                    consecutive_error_count = 0
                    
                    self.active_order_id = order['id']
                    logger.info(f"Placed {side} limit order for {remaining_amount} at {price}: {self.active_order_id}")
                except Exception as e:
                    error_msg = str(e).lower()
                    last_error_message = error_msg
                    
                    # Track consecutive errors of the same type
                    consecutive_error_count += 1
                    
                    # Check for reduceOnly rejection specifically
                    if "reduceonly order is rejected" in error_msg or "code:-2022" in error_msg or "code:-4118" in error_msg or "code:-4112" in error_msg:
                        logger.error(f"ReduceOnly order rejected ({consecutive_error_count}/{max_consecutive_errors}): {e}")
                        
                        # On first occurrence, run diagnostics to help identify the problem
                        if consecutive_error_count == 1:
                            self.debug_order_issue(side, remaining_amount, 'limit', str(e))
                        
                        # For persistent reduceOnly rejections, try force close after a few attempts
                        if consecutive_error_count >= 3 and not is_entry:
                            logger.info("Multiple reduceOnly rejections - trying force close...")
                            self.force_close_position()
                            self.stop_threads = True
                            break
                    
                    # Check for margin insufficient error specifically
                    if ("margin is insufficient" in error_msg or 
                        "insufficient margin" in error_msg or 
                        '"code":-2019' in str(e)):
                        
                        # For margin issues, try with smaller position size instead of changing leverage
                        if is_entry:
                            logger.info(f"Margin insufficient! Trying with smaller position size")
                            try:
                                # Use decreasing percentages of balance on successive attempts
                                percent_to_use = 0.75
                                if consecutive_error_count > 1:
                                    percent_to_use = 0.5
                                if consecutive_error_count > 2:
                                    percent_to_use = 0.3
                                
                                # Recalculate with reduced size
                                balance = self.exchange.fetch_balance()
                                usdt_balance = balance['USDT']['free'] * percent_to_use
                                target_amount = (usdt_balance * current_leverage) / price
                                remaining_amount = target_amount  # No fills yet
                                
                                # Check minimum again
                                if remaining_amount < min_amount:
                                    remaining_amount = min_amount
                                    logger.info(f"Using minimum order size: {min_amount}")
                                
                                logger.info(f"Retrying with {percent_to_use*100}% of balance: {remaining_amount}")
                                continue  # Try again with smaller size
                            except Exception as size_err:
                                logger.error(f"Error adjusting position size: {size_err}")
                        
                        # Handle minimum amount errors
                        if "must be greater than minimum amount" in error_msg:
                            attempt_count = getattr(self, '_attempt_count', 0) + 1
                            setattr(self, '_attempt_count', attempt_count)
                            
                            if attempt_count >= 5:
                                logger.error("Failed to place order after multiple attempts due to minimum amount issues")
                                if filled_amount > 0:
                                    logger.info(f"Partial fill achieved ({filled_amount}/{target_amount}). Considering order complete.")
                                    
                                    if is_entry:
                                        self.position_side = side
                                        self.entry_price = price
                                        self.entry_time = datetime.datetime.now()
                                        
                                    self.stop_threads = True
                                    break
                                else:
                                    logger.info("Trying market order as fallback...")
                                    try:
                                        # Fall back to market order for remaining amount
                                        market_params = {
                                            'symbol': self.symbol,
                                            'type': 'market',
                                            'side': side,
                                            'amount': remaining_amount
                                        }
                                        
                                        # For exit orders, use reduceOnly flag
                                        if not is_entry:
                                            if 'params' not in market_params:
                                                market_params['params'] = {}
                                            market_params['params']['reduceOnly'] = True
                                        
                                        self.exchange.create_order(**market_params)
                                        logger.info(f"Placed {side.upper()} MARKET order as fallback")
                                        self.stop_threads = True
                                        break
                                    except Exception as market_err:
                                        logger.error(f"Market order fallback failed: {market_err}")
                                        self.stop_threads = True
                                        break
                        
                        # Special handling for 'notional must be no smaller than 20' error
                        if "notional must be no smaller than 20" in error_msg or "code:-4164" in error_msg:
                            # Calculate minimum amount based on current price
                            min_notional_amount = self.get_min_order_amount(price)
                            logger.info(f"Order below minimum notional value. Increasing size to {min_notional_amount}")
                            
                            if not is_entry:
                                # For exit orders, use reduceOnly with increased size
                                logger.warning("Trying larger order size with reduceOnly to meet notional requirements")
                                try:
                                    exit_params = {
                                        'symbol': self.symbol,
                                        'type': 'market',  # Switch to market order for better chance of execution
                                        'side': side,
                                        'amount': max(min_notional_amount, remaining_amount),
                                        'params': {
                                            'reduceOnly': True
                                        }
                                    }
                                    
                                    self.exchange.create_order(**exit_params)
                                    logger.info(f"Placed {side.upper()} exit MARKET order with increased size and reduceOnly")
                                    
                                    # Consider position closed
                                    self.position_side = None
                                    self.entry_price = None
                                    self.entry_time = None
                                    
                                    self.stop_threads = True
                                    break
                                except Exception as notional_err:
                                    logger.error(f"Failed notional value fix attempt: {notional_err}")
                            else:
                                # For entry orders, try with minimum notional amount
                                try:
                                    entry_params = {
                                        'symbol': self.symbol,
                                        'type': 'market',  # Switch to market order
                                        'side': side,
                                        'amount': min_notional_amount
                                    }
                                    
                                    self.exchange.create_order(**entry_params)
                                    logger.info(f"Placed {side.upper()} entry MARKET order with increased size to meet notional requirements")
                                    
                                    # Update position status
                                    self.position_side = side
                                    self.entry_price = price
                                    self.entry_time = datetime.datetime.now()
                                    
                                    self.stop_threads = True
                                    break
                                except Exception as entry_err:
                                    logger.error(f"Failed entry with minimum notional: {entry_err}")
                        
                        logger.error(f"Order placement error: {e}")
                        # Slow down the retry pace on errors
                        time.sleep(2.0 if consecutive_error_count > 2 else 0.5)
                        continue
                
                # Check order status multiple times to see if it was filled
                order_status = None
                for check in range(5):  # Check a few times with short waits
                    if self.stop_threads:
                        break
                    
                    try:
                        # Only check if we have a valid order ID
                        if self.active_order_id and len(str(self.active_order_id)) >= 5:
                            order_status = self.exchange.fetch_order(self.active_order_id, self.symbol)
                            
                            # Order completely filled
                            if order_status['status'] == 'closed':
                                filled_amount += float(order_status.get('filled', 0))
                                logger.info(f"Order fully filled! {side.upper()} at {price} for {order_status.get('filled', 0)} ({filled_amount}/{target_amount})")
                                
                                # If we've filled all (or most) of what we needed
                                if filled_amount >= (target_amount * 0.99):  # Consider 99% filled as complete
                                    if is_entry:
                                        self.position_side = side
                                        self.entry_price = price
                                        self.entry_time = datetime.datetime.now()
                                    else:
                                        self.position_side = None
                                        self.entry_price = None
                                        self.entry_time = None
                                        
                                    self.active_order_id = None
                                    self.stop_threads = True
                                    break
                                else:
                                    # Still need to fill more
                                    self.active_order_id = None
                                    break  # Break the check loop but continue the main loop
                            
                            # Check for partial fills
                            elif float(order_status.get('filled', 0)) > 0:
                                filled_this_time = float(order_status.get('filled', 0))
                                filled_amount += filled_this_time
                                logger.info(f"Order partially filled: {filled_this_time} ({filled_amount}/{target_amount})")
                                
                                # Check if position is actually closed for exit orders
                                if not is_entry and filled_amount > 0:
                                    # Verify if position actually exists after partial fill
                                    has_position = False
                                    try:
                                        positions = self.exchange.fetch_positions(symbols=[self.symbol])
                                        for position in positions:
                                            if position['symbol'] == self.symbol and abs(float(position.get('contracts', 0))) > 0.0001:
                                                has_position = True
                                                break
                                        
                                        if not has_position:
                                            logger.info("Position fully closed after partial fill")
                                            self.position_side = None
                                            self.entry_price = None
                                            self.entry_time = None
                                            self.active_order_id = None
                                            self.stop_threads = True
                                            break
                                    except Exception as check_err:
                                        logger.error(f"Error checking position after partial fill: {check_err}")
                                # Don't break yet, continue checking
                        else:
                            # Invalid/missing order ID
                            logger.debug(f"Skipping order status check - no valid order ID")
                            break
                    except Exception as status_err:
                        # Handle API errors more gracefully
                        error_msg = str(status_err).lower()
                        
                        # Check for "orderid" parameter error specifically
                        if "orderid was not sent" in error_msg or "malformed" in error_msg:
                            logger.warning(f"Order ID error in status check: {error_msg}")
                            # Set order ID to None to avoid further errors
                            self.active_order_id = None
                            break
                        
                        logger.warning(f"Error checking order status: {status_err}")
                        # Don't immediately break on error, try a few more times
                    
                    time.sleep(0.5)
                
                # Wait briefly before updating the order
                time.sleep(0.5)
                
                # If we reach here, the order wasn't fully filled
                # This will trigger the cancel in the next loop iteration
                
            except Exception as e:
                logger.error(f"Error in limit order thread: {e}")
                time.sleep(1)
    
    def place_market_order(self, side: str, amount: float = None) -> None:
        """
        Place a market order for immediate execution.
        
        Args:
            side: 'buy' or 'sell'
            amount: Optional specific amount to use, otherwise calculated
        """
        try:
            # Cancel any active limit orders
            if self.active_order_id:
                try:
                    self.exchange.cancel_order(self.active_order_id, self.symbol)
                except Exception as e:
                    logger.warning(f"Error cancelling active order: {e}")
                self.active_order_id = None
            
            # Stop any running order threads
            self.stop_threads = True
            if self.limit_order_thread and self.limit_order_thread.is_alive():
                self.limit_order_thread.join(timeout=1.0)
            
            # Determine if this is an exit or entry
            is_exit = False
            if (side == 'sell' and self.position_side == 'buy') or (side == 'buy' and self.position_side == 'sell'):
                is_exit = True
            
            # For exit orders, cancel any existing orders that might conflict
            if is_exit:
                try:
                    open_orders = self.exchange.fetch_open_orders(symbol=self.symbol)
                    if open_orders:
                        logger.info(f"Cancelling {len(open_orders)} existing open orders before market exit...")
                        for order in open_orders:
                            try:
                                self.exchange.cancel_order(order['id'], self.symbol)
                            except Exception as cancel_err:
                                logger.warning(f"Error cancelling order {order['id']}: {cancel_err}")
                except Exception as list_err:
                    logger.warning(f"Error fetching open orders: {list_err}")
            
            # Use provided amount or calculate order amount
            if amount is None:
                if is_exit:
                    # For position exits, get the actual position size
                    try:
                        positions = self.exchange.fetch_positions(symbols=[self.symbol])
                        for position in positions:
                            if position['symbol'] == self.symbol and abs(float(position['contracts'])) > 0:
                                # Use the absolute position size
                                amount = abs(float(position['contracts']))
                                logger.info(f"Closing position of {amount} {self.symbol}")
                                break
                        
                        # If position not found, use minimum size
                        if amount is None or amount < 0.001:
                            amount = 0.001
                            logger.warning(f"Could not determine position size, using minimum: {amount}")
                    except Exception as e:
                        logger.error(f"Error getting position size: {e}")
                        amount = 0.001
                else:
                    # For new entries, calculate based on full balance and leverage
                    balance = self.exchange.fetch_balance()
                    usdt_balance = balance['USDT']['free']  # Use 100% of balance
                    
                    # For market orders, we need the current price to calculate amount
                    ticker = self.exchange.fetch_ticker(self.symbol)
                    price = ticker['last']
                    
                    # Use full balance with leverage
                    amount = (usdt_balance * self.current_leverage) / price
            
            # Ensure minimum order size meets notional value requirements
            ticker = self.exchange.fetch_ticker(self.symbol)
            price = ticker['last']
            min_amount = self.get_min_order_amount(price)
            if amount < min_amount:
                logger.warning(f"Calculated amount {amount} is below minimum notional requirement")
                amount = min_amount
                logger.info(f"Using minimum order size to meet 20 USDT notional requirement: {min_amount}")
            
            current_leverage = self.current_leverage
            
            # Track consecutive errors
            max_attempts = 3
            attempts = 0
            
            # Place market order
            while attempts < max_attempts:
                attempts += 1
                try:
                    # Prepare order parameters
                    market_params = {
                        'symbol': self.symbol,
                        'type': 'market',
                        'side': side,
                        'amount': amount
                    }
                    
                    # Add reduceOnly flag for exit orders
                    if is_exit:
                        if 'params' not in market_params:
                            market_params['params'] = {}
                        market_params['params']['reduceOnly'] = True
                    
                    order = self.exchange.create_order(**market_params)
                    
                    logger.info(f"Placed {side.upper()} MARKET order for {amount}: {order['id']}")
                    
                    # Check if the order was filled
                    try:
                        filled_order = self.exchange.fetch_order(order['id'], self.symbol)
                        filled_amount = float(filled_order.get('filled', 0))
                        
                        if filled_amount > 0:
                            logger.info(f"Market order filled: {filled_amount}/{amount}")
                            
                            # Reset position tracking
                            if is_exit:
                                # Exiting a position
                                if filled_amount >= (amount * 0.95):  # Consider 95% fill as complete
                                    self.position_side = None
                                    self.entry_price = None 
                                    self.entry_time = None
                                else:
                                    logger.warning(f"Position partially closed ({filled_amount}/{amount}). You may need to close the rest manually.")
                            else:
                                # Entering a position
                                self.position_side = side
                                self.entry_price = filled_order.get('price') or filled_order.get('average')
                                self.entry_time = datetime.datetime.now()
                    except Exception as fill_check_err:
                        logger.warning(f"Error checking market order fill: {fill_check_err}")
                    
                    # We succeeded, so break the retry loop
                    break
                    
                except Exception as e:
                    error_msg = str(e).lower()
                    
                    # Check for reduceOnly rejection specifically
                    if "reduceonly order is rejected" in error_msg or "code:-2022" in error_msg or "code:-4118" in error_msg or "code:-4112" in error_msg:
                        logger.error(f"ReduceOnly order rejected (attempt {attempts}/{max_attempts}): {e}")
                        
                        # Only run diagnostics on first attempt to avoid spam
                        if attempts == 1:
                            self.debug_order_issue(side, amount, 'market', str(e))
                        
                        # If this is the last attempt and we're trying to exit, use force close
                        if attempts == max_attempts and is_exit:
                            logger.info("Multiple market order failures - trying force close...")
                            self.force_close_position()
                    
                    # Check for margin insufficient error specifically
                    if ("margin is insufficient" in error_msg or 
                        "insufficient margin" in error_msg or 
                        '"code":-2019' in str(e)):
                        
                        # For margin issues in entry orders, try with smaller position size
                        if not is_exit:
                            logger.info("Margin insufficient! Trying with smaller position size")
                            try:
                                # Use decreasing percentages of balance on successive attempts
                                percent_to_use = 0.75
                                if attempts > 1:
                                    percent_to_use = 0.5
                                if attempts > 2:
                                    percent_to_use = 0.3
                                
                                balance = self.exchange.fetch_balance()
                                usdt_balance = balance['USDT']['free'] * percent_to_use
                                ticker = self.exchange.fetch_ticker(self.symbol)
                                price = ticker['last']
                                amount = (usdt_balance * self.current_leverage) / price
                                
                                # Check minimum again
                                if amount < min_amount:
                                    amount = min_amount
                                    
                                logger.info(f"Retrying with {percent_to_use*100}% of balance: {amount}")
                                continue  # Try again with smaller size
                            except Exception as retry_err:
                                logger.error(f"Error calculating smaller size: {retry_err}")
                        elif is_exit:
                            # For exit orders with margin issues, try closing with the minimum amount
                            logger.warning("Margin issue when closing position. Trying minimum amount.")
                            try:
                                min_order_params = {
                                    'symbol': self.symbol,
                                    'type': 'market',
                                    'side': side,
                                    'amount': min_amount
                                }
                                
                                # Add reduceOnly flag for exit orders
                                if 'params' not in min_order_params:
                                    min_order_params['params'] = {}
                                min_order_params['params']['reduceOnly'] = True
                                
                                order = self.exchange.create_order(**min_order_params)
                                logger.info(f"Placed {side.upper()} MARKET order with minimum amount: {order['id']}")
                                
                                # Try force close as well to close the rest
                                self.force_close_position()
                                break
                            except Exception as min_err:
                                logger.error(f"Error placing minimum market order: {min_err}")
                                
                                # As last resort, try force close
                                logger.info("Trying force close as last resort...")
                                self.force_close_position()
                    else:
                        logger.error(f"Market order error (attempt {attempts}/{max_attempts}): {e}")
                        
                    # If this is the last attempt and we're trying to exit, use force close
                    if attempts == max_attempts and is_exit:
                        logger.info("Multiple market order failures - trying force close...")
                        self.force_close_position()
                    
                # Increase delay between retries
                time.sleep(1.0 * attempts)
                
            # If we hit max attempts, log warning
            if attempts >= max_attempts:
                logger.warning(f"Max retry attempts ({max_attempts}) reached for market order")
                
        except Exception as e:
            logger.error(f"Error placing market order: {e}")
            
            # If this was an exit attempt that failed, try force close as last resort
            if is_exit:
                logger.info("Critical failure during market exit - attempting force close...")
                self.force_close_position()

    def _has_open_position(self) -> bool:
        """Check if there is an open position on Binance."""
        try:
            positions = self.exchange.fetch_positions(symbols=[self.symbol])
            for position in positions:
                # Check if position size is non-zero
                if position['symbol'] == self.symbol and abs(float(position.get('contracts', 0))) > 0.0001:
                    position_side = None
                    
                    # Method 1: Use 'side' property if available
                    if 'side' in position and position['side'] in ['long', 'short']:
                        position_side = 'buy' if position['side'] == 'long' else 'sell'
                    # Method 2: Use 'info.positionSide' if available
                    elif 'info' in position and 'positionSide' in position['info']:
                        raw_side = position['info']['positionSide'].lower()
                        position_side = 'buy' if raw_side == 'long' else 'sell'
                    # Method 3: Use contracts sign as fallback
                    else:
                        position_contracts = float(position.get('contracts', 0))
                        position_side = 'buy' if position_contracts > 0 else 'sell'
                    
                    # Update our internal position tracking
                    self.position_side = position_side
                    self.entry_price = float(position.get('entryPrice', 0)) if 'entryPrice' in position else None
                    # We don't know the original entry time, so we'll set it to now
                    if self.entry_time is None:
                        self.entry_time = datetime.datetime.now()
                    return True
            return False
        except Exception as e:
            logger.error(f"Error checking for open positions: {e}")
            return False

    def long(self) -> None:
        """Enter a long position using a limit order."""
        # First check if we already have a position on Binance
        if self._has_open_position():
            logger.warning(f"Already in a {self.position_side} position. Exit first.")
            return
        
        logger.info(f"Entering LONG position with limit order at {self.current_leverage}x leverage...")
        self.place_limit_order(side='buy', is_entry=True)
    
    def short(self) -> None:
        """Enter a short position using a limit order."""
        # First check if we already have a position on Binance
        if self._has_open_position():
            logger.warning(f"Already in a {self.position_side} position. Exit first.")
            return
        
        logger.info(f"Entering SHORT position with limit order at {self.current_leverage}x leverage...")
        self.place_limit_order(side='sell', is_entry=True)
    
    def terminate(self) -> None:
        """Exit the current position using a limit order."""
        try:
            # Cancel any existing orders to avoid conflicts
            try:
                logger.info("Cancelling any existing orders before exit...")
                self.exchange.cancel_all_orders(self.symbol)
                logger.info("Existing orders cancelled")
            except Exception as e:
                logger.warning(f"Error cancelling existing orders: {e}")
            
            # Get positions directly from Binance
            positions = self.exchange.fetch_positions(symbols=[self.symbol])
            position_found = False
            position_amount = 0
            position_side = None
            
            for position in positions:
                # Check if this is our target symbol and has non-zero size
                if position['symbol'] == self.symbol and abs(float(position.get('contracts', 0))) > 0.0001:
                    # Check position side using info from Binance
                    # Alternative methods to determine position direction
                    position_found = True
                    position_amount = abs(float(position.get('contracts', 0)))
                    
                    # Method 1: Use 'side' property if available
                    if 'side' in position and position['side'] in ['long', 'short']:
                        position_side = position['side']
                        logger.info(f"Position direction detected using 'side' property: {position_side}")
                    # Method 2: Use 'info.positionSide' if available
                    elif 'info' in position and 'positionSide' in position['info']:
                        position_side = position['info']['positionSide'].lower()
                        logger.info(f"Position direction detected using 'info.positionSide': {position_side}")
                    # Method 3: Use contracts sign as fallback
                    else:
                        contracts = float(position.get('contracts', 0))
                        position_side = 'long' if contracts > 0 else 'short'
                        logger.info(f"Position direction determined by contracts sign: {position_side} (contracts: {contracts})")
                    
                    logger.info(f"Found {position_side.upper()} position of size {position_amount}")
                    break
            
            if not position_found:
                logger.warning("No open position found to exit.")
                self.position_side = None
                self.entry_price = None
                self.entry_time = None
                return
            
            # Determine correct exit side based on position direction
            exit_side = 'sell' if position_side == 'long' else 'buy'
            logger.info(f"Terminating {position_side.upper()} position with limit order (exit side: {exit_side.upper()})...")
            
            # Get the best price for the limit order
            best_price = self.get_best_price('buy' if exit_side == 'sell' else 'sell')
            
            # Adjust price to ensure post-only doesn't execute immediately but stay extremely close
            # Make the offset as small as possible while still valid for Binance
            if exit_side == 'sell':
                price = best_price + 0.01  # Fixed 0.01 above best bid for sell orders
            else:
                price = best_price - 0.01  # Fixed 0.01 below best ask for buy orders
                
            logger.info(f"Setting exit {exit_side} price at {price} (best price: {best_price})")
            
            # Create the limit order with reduceOnly flag
            try:
                limit_params = {
                    'symbol': self.symbol,
                    'type': 'limit',
                    'side': exit_side,
                    'amount': position_amount,
                    'price': price,
                    'params': {
                        'reduceOnly': True,
                        'postOnly': True
                    }
                }
                
                order = self.exchange.create_order(**limit_params)
                self.active_order_id = order['id']
                logger.info(f"✅ Placed {exit_side.upper()} LIMIT order at {price} to exit position: {order['id']} (post-only)")
                
                # Start a thread to manage this limit order
                self.stop_threads = False
                self.limit_order_thread = threading.Thread(
                    target=self._manage_limit_order,
                    args=(exit_side, False)  # is_entry=False means exit
                )
                self.limit_order_thread.daemon = True
                self.limit_order_thread.start()
                
            except Exception as limit_err:
                logger.error(f"Limit exit failed: {limit_err}")
            
        except Exception as e:
            logger.error(f"Error in terminate: {e}")

    def force_close_position(self) -> bool:
        """Force close any open position regardless of our internal state tracking.
        Uses limit orders to close position."""
        try:
            # Get all positions directly from Binance
            positions = self.exchange.fetch_positions(symbols=[self.symbol])
            position_found = False
            
            for position in positions:
                # Check if this is our target symbol and has non-zero size
                if position['symbol'] == self.symbol and abs(float(position.get('contracts', 0))) > 0.0001:
                    # Get position details
                    position_amount = abs(float(position.get('contracts', 0)))
                    position_side = None
                    
                    # Method 1: Use 'side' property if available
                    if 'side' in position and position['side'] in ['long', 'short']:
                        position_side = position['side']
                        logger.info(f"Position direction detected using 'side' property: {position_side}")
                    # Method 2: Use 'info.positionSide' if available
                    elif 'info' in position and 'positionSide' in position['info']:
                        position_side = position['info']['positionSide'].lower()
                        logger.info(f"Position direction detected using 'info.positionSide': {position_side}")
                    # Method 3: Use contracts sign as fallback
                    else:
                        contracts = float(position.get('contracts', 0))
                        position_side = 'long' if contracts > 0 else 'short'
                        logger.info(f"Position direction determined by contracts sign: {position_side} (contracts: {contracts})")
                    
                    # Determine correct exit side based on position direction
                    exit_side = 'sell' if position_side == 'long' else 'buy'
                    
                    logger.info(f"Forcing close of {position_side.upper()} position of size {position_amount}")
                    position_found = True
                    
                    # Get current price for logging
                    ticker = self.exchange.fetch_ticker(self.symbol)
                    current_price = ticker['last']
                    entry_price = float(position.get('entryPrice', 0))
                    
                    # Cancel all open orders first to prevent conflicts
                    try:
                        logger.info("Cancelling all open orders first...")
                        self.exchange.cancel_all_orders(self.symbol)
                        logger.info("All open orders cancelled")
                    except Exception as cancel_err:
                        logger.warning(f"Could not cancel all orders: {cancel_err}")
                        
                        # Try cancelling orders one by one as a fallback
                        try:
                            open_orders = self.exchange.fetch_open_orders(symbol=self.symbol)
                            for order in open_orders:
                                try:
                                    self.exchange.cancel_order(order['id'], self.symbol)
                                    logger.info(f"Cancelled order {order['id']}")
                                except Exception as e:
                                    logger.warning(f"Could not cancel order {order['id']}: {e}")
                        except Exception as e:
                            logger.warning(f"Could not fetch open orders: {e}")
                    
                    # Wait a moment after cancelling orders
                    time.sleep(1)
                    
                    # Place a limit order at the current price
                    best_price = self.get_best_price('buy' if exit_side == 'sell' else 'sell')
                    
                    # Adjust price to ensure post-only doesn't execute immediately but stay extremely close
                    # Make the offset as small as possible while still valid for Binance
                    if exit_side == 'sell':
                        price = best_price + 0.01  # Fixed 0.01 above best bid for sell orders
                    else:
                        price = best_price - 0.01  # Fixed 0.01 below best ask for buy orders
                        
                    logger.info(f"Setting force close {exit_side} price at {price} (best price: {best_price})")
                    
                    try:
                        limit_params = {
                            'symbol': self.symbol,
                            'type': 'limit',
                            'side': exit_side,
                            'amount': position_amount,
                            'price': price,
                            'params': {
                                'reduceOnly': True,
                                'postOnly': True
                            }
                        }
                        
                        order = self.exchange.create_order(**limit_params)
                        self.active_order_id = order['id']
                        logger.info(f"✅ Force close limit order placed: {order['id']} at {price}")
                        
                        # Start a thread to manage this limit order
                        self.stop_threads = False
                        self.limit_order_thread = threading.Thread(
                            target=self._manage_limit_order,
                            args=(exit_side, False)  # is_entry=False
                        )
                        self.limit_order_thread.daemon = True
                        self.limit_order_thread.start()
                        
                        # Update our internal state
                        return True
                    except Exception as e:
                        logger.error(f"❌ Force close limit order failed: {e}")
                        return False
            
            if not position_found:
                logger.info("No open position found to close")
                self.position_side = None
                self.entry_price = None
                self.entry_time = None
                return False
                
        except Exception as e:
            logger.error(f"Error in force close: {e}")
            return False

    def market_exit(self) -> None:
        """Immediately exit the current position using a limit order placed at market price."""
        logger.info("EMERGENCY EXIT - Attempting to close position with limit order at market price...")
        
        try:
            # Get positions directly from Binance
            positions = self.exchange.fetch_positions(symbols=[self.symbol])
            position_found = False
            position_amount = 0
            exit_side = None
            
            for position in positions:
                # Check if this is our target symbol and has non-zero size
                if position['symbol'] == self.symbol and abs(float(position.get('contracts', 0))) > 0.0001:
                    # Get position details
                    position_amount = abs(float(position.get('contracts', 0)))
                    position_side = None
                    
                    # Method 1: Use 'side' property if available
                    if 'side' in position and position['side'] in ['long', 'short']:
                        position_side = position['side']
                        logger.info(f"Position direction detected using 'side' property: {position_side}")
                    # Method 2: Use 'info.positionSide' if available
                    elif 'info' in position and 'positionSide' in position['info']:
                        position_side = position['info']['positionSide'].lower()
                        logger.info(f"Position direction detected using 'info.positionSide': {position_side}")
                    # Method 3: Use contracts sign as fallback
                    else:
                        contracts = float(position.get('contracts', 0))
                        position_side = 'long' if contracts > 0 else 'short'
                        logger.info(f"Position direction determined by contracts sign: {position_side} (contracts: {contracts})")
                    
                    # Determine correct exit side based on position direction
                    exit_side = 'sell' if position_side == 'long' else 'buy'
                    
                    position_found = True
                    logger.info(f"Found {position_side.upper()} position of size {position_amount}, will {exit_side.upper()} to exit")
                    break
            
            if not position_found:
                logger.info("No position found to exit")
                self.position_side = None
                self.entry_price = None
                self.entry_time = None
                return
                
            # Cancel all existing orders first
            try:
                logger.info("Cancelling all existing orders before exit...")
                self.exchange.cancel_all_orders(self.symbol)
            except Exception as e:
                logger.warning(f"Error cancelling orders: {e}")
            
            # Place limit order at the best available price
            best_price = self.get_best_price('buy' if exit_side == 'sell' else 'sell')
            
            # Adjust price to ensure post-only doesn't execute immediately but stay extremely close
            # Make the offset as small as possible while still valid for Binance
            if exit_side == 'sell':
                price = best_price + 0.01  # Fixed 0.01 above best bid for sell orders
            else:
                price = best_price - 0.01  # Fixed 0.01 below best ask for buy orders
                
            logger.info(f"Setting emergency exit {exit_side} price at {price} (best price: {best_price})")
            
            try:
                limit_params = {
                    'symbol': self.symbol,
                    'type': 'limit',
                    'side': exit_side,
                    'amount': position_amount,
                    'price': price,
                    'params': {
                        'reduceOnly': True,
                        'postOnly': True
                    }
                }
                
                order = self.exchange.create_order(**limit_params)
                self.active_order_id = order['id']
                logger.info(f"✅ Emergency exit limit order placed: {order['id']} at {price}")
                
                # Start a thread to manage this limit order
                self.stop_threads = False
                self.limit_order_thread = threading.Thread(
                    target=self._manage_limit_order,
                    args=(exit_side, False)  # is_entry=False
                )
                self.limit_order_thread.daemon = True
                self.limit_order_thread.start()
                
            except Exception as e:
                logger.error(f"Emergency exit failed: {e}")
                self.force_close_position()
                
        except Exception as e:
            logger.error(f"Error in emergency exit: {e}")
            logger.info("Trying force close as last resort...")
            self.force_close_position()

    def show_status(self) -> None:
        """Display the current trading status."""
        try:
            # Check for actual position on Binance
            self._has_open_position()  # This updates self.position_side if a position exists
                
            balance = self.exchange.fetch_balance()
            ticker = self.exchange.fetch_ticker(self.symbol)
            
            safe_print("--- Binance Status ---")
            safe_print(f"Symbol: {self.symbol} | Price: {ticker['last']} | Leverage: {self.current_leverage}x")
            safe_print(f"Balance: {balance['USDT']['free']} USDT | Total: {balance['USDT']['total']} USDT")
            
            # Get position details directly from Binance
            positions = self.exchange.fetch_positions(symbols=[self.symbol])
            position_found = False
            
            for position in positions:
                if position['symbol'] == self.symbol and abs(float(position['contracts'])) > 0:
                    position_found = True
                    position_size = abs(float(position['contracts']))
                    entry_price = float(position['entryPrice']) if 'entryPrice' in position else 0
                    unrealized_pnl = float(position['unrealizedPnl']) if 'unrealizedPnl' in position else 0
                    position_side = 'LONG' if float(position['contracts']) > 0 else 'SHORT'
                    
                    # Get actual leverage from position or use current_leverage
                    position_leverage = self.current_leverage
                    if 'leverage' in position and position['leverage'] is not None:
                        try:
                            # Try to get leverage from position data
                            lev_val = float(position['leverage'])
                            if lev_val > 0:  # Only update if positive
                                position_leverage = lev_val
                        except (ValueError, TypeError):
                            pass  # Keep default leverage on error
                    
                    # Display position details
                    safe_print(f"Position: {position_side} | Size: {position_size} ETH | Entry: {entry_price}")
                    safe_print(f"P&L: {unrealized_pnl} USDT | Leverage: {position_leverage}x")
                    if self.entry_time:
                        position_time = datetime.datetime.now() - self.entry_time
                        safe_print(f"Position time: {position_time}")
                    break
            
            if not position_found:
                safe_print("No active position")
                # Reset internal state if no position is found
                self.position_side = None
                self.entry_price = None
                
            safe_print("-------------------")
        except Exception as e:
            logger.error(f"Error showing status: {e}")
    
    def _monitor_positions(self):
        """Periodically check for position changes to keep internal state accurate."""
        while True:
            try:
                # Check every 5 seconds
                self._has_open_position()
                time.sleep(5)
            except Exception as e:
                logger.error(f"Error in position monitor: {e}")
                time.sleep(5)

    def reset_position_tracking(self) -> None:
        """Reset all position tracking state variables. Use when things get out of sync."""
        self.position_side = None
        self.entry_price = None
        self.entry_time = None
        self.active_order_id = None
        self.stop_threads = True
        
        logger.info("Position tracking state has been reset")
        
        # Force check for actual positions
        has_position = self._has_open_position()
        if has_position:
            logger.warning(f"NOTE: You still have an active {self.position_side.upper()} position on Binance")
        else:
            logger.info("No active positions found on Binance")
        
        return has_position

    def get_min_order_amount(self, price: float) -> float:
        """
        Calculate the minimum order amount based on Binance's 20 USDT minimum notional value requirement.
        
        Args:
            price: Current price of the asset
            
        Returns:
            float: Minimum order amount that satisfies the notional value requirement
        """
        # Binance requires minimum notional value of 20 USDT
        min_notional = 20.1  # Slightly higher to be safe
        
        # Calculate minimum amount
        min_amount = min_notional / price
        
        # Ensure it's also above the minimum quantity requirement (0.001 for ETH)
        min_amount = max(min_amount, 0.001)
        
        # Round to appropriate precision (ETH futures uses 3 decimal places)
        min_amount = round(min_amount, 3)
        
        return min_amount

    def debug_order_issue(self, side: str, amount: float, order_type: str, error_message: str) -> None:
        """
        Debug issues with orders, especially ReduceOnly order rejections.
        Captures essential diagnostic information to help resolve order issues.
        
        Args:
            side: The order side ('buy' or 'sell')
            amount: The attempted order amount
            order_type: The type of order ('limit' or 'market')
            error_message: The error message received
        """
        try:
            logger.info("=== ORDER REJECTION DIAGNOSIS ===")
            logger.info(f"Error: {error_message}")
            logger.info(f"Order: {order_type.upper()} {side.upper()} {amount} {self.symbol}")
            
            # Check current positions
            positions = self.exchange.fetch_positions(symbols=[self.symbol])
            position_exists = False
            
            for position in positions:
                if position['symbol'] == self.symbol and abs(float(position['contracts'])) > 0.0001:
                    position_exists = True
                    position_size = abs(float(position['contracts']))
                    position_direction = "LONG" if float(position['contracts']) > 0 else "SHORT"
                    entry_price = float(position['entryPrice']) if 'entryPrice' in position else 0
                    
                    # Get leverage directly from position or from current_leverage
                    position_leverage = None
                    if 'leverage' in position and position['leverage'] is not None:
                        try:
                            position_leverage = float(position['leverage'])
                        except (ValueError, TypeError):
                            pass
                    if position_leverage is None or position_leverage <= 0:
                        position_leverage = self.current_leverage
                    
                    # Get other position details
                    liquidation_price = float(position.get('liquidationPrice', 0)) if 'liquidationPrice' in position else 0
                    margin_mode = position.get('marginMode', 'unknown')
                    
                    ticker = self.exchange.fetch_ticker(self.symbol)
                    current_price = ticker['last']
                    price_diff_percent = abs((current_price - liquidation_price) / current_price * 100) if liquidation_price > 0 else 999
                    
                    logger.info(f"Position: {position_direction} {position_size} @ {entry_price} | Current price: {current_price}")
                    logger.info(f"Leverage: {position_leverage}x | Margin mode: {margin_mode} | Liquidation price: {liquidation_price}")
                    
                    if price_diff_percent < 3:
                        logger.warning(f"⚠️ CRITICAL: Position close to liquidation! Only {price_diff_percent:.2f}% away")
                    
                    if side == 'buy' and position_direction == 'LONG':
                        logger.error("❌ ERROR: Trying to BUY when already LONG")
                    elif side == 'sell' and position_direction == 'SHORT':
                        logger.error("❌ ERROR: Trying to SELL when already SHORT")
                    
                    if amount > position_size * 1.001:
                        logger.error(f"❌ ERROR: Order size ({amount}) exceeds position size ({position_size})")
                    break
            
            if not position_exists:
                logger.error("❌ ERROR: No position exists for reduceOnly order")
                return
            
            # Check open orders
            open_orders = self.exchange.fetch_open_orders(symbol=self.symbol)
            if open_orders:
                logger.info(f"Open orders: {len(open_orders)}")
                for order in open_orders:
                    logger.info(f"Order: {order.get('side', 'unknown').upper()} {order.get('amount', 0)} @ {order.get('price', 0)}")
            
            # Recommendations
            logger.info("Recommendations:")
            if not position_exists:
                logger.info("• Cannot use reduceOnly without a position")
            elif price_diff_percent < 3:
                logger.info("• Position near liquidation - use F command (force close)")
            elif amount > position_size:
                logger.info(f"• Use smaller size (max {position_size})")
            elif open_orders and len(open_orders) > 0:
                logger.info("• Cancel existing orders first, then retry")
            
            logger.info("• Try F command for Force Close")
            logger.info("=== END DIAGNOSIS ===")
        except Exception as e:
            logger.error(f"Error during diagnostic: {e}")

def main():
    """Main function to run the Binance trading assistant."""
    # Hardcoded Binance API credentials
    api_key = "ofQzX3gGAKS777NyYIovAy1XyqLzGC2UJPMh9jqIYEfieFRy3DCkZJl15VYA2zXo"
    api_secret = "QVJpTFgHIEv74LmCT5clX8o1zAFEEqJqKpg2ePklObM1Ybv9iKNe8jvM7MRjoz07"
    
    # Fixed to ETH/USDT perpetual futures contract
    symbol = "ETH/USDT:USDT"
    assistant = BinanceAssistant(api_key, api_secret, symbol)
    
    # Check for existing positions at startup
    has_position = assistant._has_open_position()
    
    safe_print(f"Binance ETH Trading Assistant initialized")
    safe_print(f"Trading {symbol} with {assistant.current_leverage}x leverage")
    
    if has_position:
        safe_print(f"EXISTING POSITION DETECTED: {assistant.position_side.upper()}")
    
    safe_print("Available commands:")
    safe_print("1=LONG, 2=SHORT, 3=Exit(limit), 4=Exit(market), 5=Status, 0=Quit")
    safe_print("F=Force Close (ignores tracking), C=Clear tracking state, D=Debug")
    safe_print("(Use '!' for emergency market exit)")
    
    # Show status at startup
    assistant.show_status()
    
    # Counter for monitoring state changes
    state_counter = 0
    last_position_state = assistant.position_side
    
    # Clear the input buffer
    while True:
        # Check if position state has changed
        if assistant.position_side != last_position_state:
            # Position state changed, print a clear notification
            if assistant.position_side is not None:
                safe_print(f"Position opened: {assistant.position_side.upper()}")
            else:
                safe_print("Position closed")
            
            last_position_state = assistant.position_side
        
        # Every 20 loops, reprint the command menu to ensure it's visible
        if state_counter % 20 == 0 and state_counter > 0:
            safe_print("Commands: 1=LONG, 2=SHORT, 3=Exit, 4=Emergency, 5=Status, F=Force Close, C=Clear tracking state, D=Debug, 0=Quit")
        
        state_counter += 1
        
        try:
            # Use a clear prompt with current position state
            position_indicator = f"[{assistant.position_side.upper()}]" if assistant.position_side else "[NO-POS]"
            
            # Clear line and print the prompt
            sys.stdout.write(f"\r{position_indicator} Command: ")
            sys.stdout.flush()
            
            command = input().strip()
            
            # Emergency exit for ! character
            if command == '!' and assistant.position_side is not None:
                safe_print("!!! EMERGENCY EXIT TRIGGERED !!!")
                assistant.market_exit()
                continue
            
            if command == '1':
                assistant.long()
            elif command == '2':
                assistant.short()
            elif command == '3':
                assistant.terminate()
            elif command == '4':
                assistant.market_exit()
            elif command == '5' or command.lower() == 'status':
                assistant.show_status()
            elif command == '0' or command.lower() in ['q', 'quit', 'exit']:
                break
            elif command == 'F' or command.lower() == 'force close':
                assistant.force_close_position()
            elif command == 'C' or command.lower() == 'clear tracking state':
                assistant.reset_position_tracking()
            elif command == 'D' or command.lower() == 'debug':
                # Run diagnostics on current position
                side = 'sell' if assistant.position_side == 'buy' else 'buy'
                # Get position size for diagnostics
                position_size = 0
                try:
                    positions = assistant.exchange.fetch_positions(symbols=[assistant.symbol])
                    for position in positions:
                        if position['symbol'] == assistant.symbol and abs(float(position['contracts'])) > 0:
                            position_size = abs(float(position['contracts']))
                            break
                except Exception as e:
                    logger.error(f"Error getting position size for diagnostics: {e}")
                    position_size = 0.001  # Fallback
                
                assistant.debug_order_issue(side, position_size, 'manual', 'User-requested diagnostics')
                safe_print("Diagnostics report generated - check logs")
            else:
                safe_print("Unknown command. Try again.")
            
            # Sleep briefly to allow logs to catch up
            time.sleep(0.1)
        
        except KeyboardInterrupt:
            safe_print("Exiting Binance Trading Assistant...")
            break
        except Exception as e:
            logger.error(f"Command error: {e}")
    
    safe_print("Binance Trading Assistant closed.")

if __name__ == "__main__":
    main() 
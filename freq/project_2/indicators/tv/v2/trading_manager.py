#!/allah/freqtrade/.venv/bin/python3.11

import time
import datetime
import threading
from typing import Dict, Any, Optional, List, Tuple

from logger import logger, safe_print
from binance_client import BinanceClient
from utils import calculate_min_order_amount, format_position_info, round_to_precision, get_price_precision

class TradingManager:
    def __init__(self, binance_client: BinanceClient, symbol: str = 'ETHUSDT', default_leverage: int = 125):
        """
        Initialize the trading manager to handle orders and positions.
        
        Args:
            binance_client: Initialized BinanceClient instance
            symbol: Trading symbol (in Binance futures format, e.g., 'ETHUSDT')
            default_leverage: Default leverage to use
        """
        self.client = binance_client
        self.symbol = symbol
        self.current_leverage = default_leverage
        self.position_side: Optional[str] = None
        self.entry_price: Optional[float] = None
        self.entry_time: Optional[datetime.datetime] = None
        self.active_order_id: Optional[int] = None
        self.stop_threads = False
        self.limit_order_thread: Optional[threading.Thread] = None
        
        # Set initial leverage
        self.set_leverage(default_leverage)
        
        # Start position monitor thread
        self.position_monitor_thread = threading.Thread(target=self._monitor_positions, daemon=True)
        self.position_monitor_thread.start()
        
        # Check for existing positions at startup
        self._check_existing_position()
    
    def _check_existing_position(self) -> bool:
        """Check for existing positions and update internal state."""
        position = self.client.get_position(self.symbol)
        if position:
            position_amt = float(position.get('positionAmt', 0))
            if abs(position_amt) > 0:
                self.position_side = 'BUY' if position_amt > 0 else 'SELL'
                self.entry_price = float(position.get('entryPrice', 0))
                # We don't know the actual entry time, so set it to now
                self.entry_time = datetime.datetime.now()
                logger.info(f"Found existing {self.position_side} position of {abs(position_amt)} {self.symbol}")
                return True
        
        self.position_side = None
        self.entry_price = None
        self.entry_time = None
        return False
    
    def set_leverage(self, leverage: int) -> bool:
        """Set leverage for the symbol."""
        result = self.client.set_leverage(self.symbol, leverage)
        if result:
            self.current_leverage = leverage
        return result
    
    def _monitor_positions(self) -> None:
        """Background thread to monitor position changes."""
        while True:
            try:
                # Check every 5 seconds
                self._check_existing_position()
                time.sleep(5)
            except Exception as e:
                logger.error(f"Error in position monitor: {e}")
                time.sleep(5)
    
    def place_limit_order(self, side: str, is_entry: bool = True) -> None:
        """
        Place a limit order with continuous price adjustment for fast execution.
        
        Args:
            side: Order side ('BUY' or 'SELL')
            is_entry: Whether this is an entry (True) or exit (False) order
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
            side: Order side ('BUY' or 'SELL')
            is_entry: Whether this is an entry (True) or exit (False) order
        """
        start_time = datetime.datetime.now()
        max_time_seconds = 15  # Max 3 candles (15 seconds in 5s timeframe)
        current_leverage = self.current_leverage
        
        # For exit orders, get current position information
        position_amount = None
        if not is_entry:
            position = self.client.get_position(self.symbol)
            if position:
                position_amount = abs(float(position.get('positionAmt', 0)))
                logger.info(f"Found existing position of {position_amount} {self.symbol}")
            
            # If position not found through API, use minimum size
            if position_amount is None or position_amount < 0.001:
                position_amount = 0.001
                logger.warning(f"Could not determine position size, using minimum: {position_amount}")
        
        # Track how much has been filled so far (for partial fills)
        filled_amount = 0.0
        target_amount = None
        
        # Error tracking to avoid infinite loops
        consecutive_error_count = 0
        max_consecutive_errors = 5
        last_error_message = ""
        
        while not self.stop_threads:
            try:
                # Check for excessive errors
                if consecutive_error_count >= max_consecutive_errors:
                    logger.error(f"Aborting after {consecutive_error_count} consecutive errors: {last_error_message}")
                    self.stop_threads = True
                    
                    # For exit orders, try force close as fallback
                    if not is_entry:
                        logger.info("Trying force close as fallback after multiple errors...")
                        self.force_close_position()
                    break
                
                # For entry orders, enforce time limit
                if is_entry and filled_amount == 0:  # Only check timeout if nothing filled yet
                    elapsed_time = datetime.datetime.now() - start_time
                    if elapsed_time.total_seconds() > max_time_seconds:
                        logger.info(f"Time limit of {max_time_seconds} seconds passed without filling. Cancelling.")
                        self.stop_threads = True
                        continue
                
                # For exit orders, verify if we still have a position before continuing
                if not is_entry:
                    position = self.client.get_position(self.symbol)
                    if not position or abs(float(position.get('positionAmt', 0))) < 0.0001:
                        logger.info("Position already closed - stopping order loop")
                        self.position_side = None
                        self.entry_price = None
                        self.entry_time = None
                        self.active_order_id = None
                        self.stop_threads = True
                        break
                
                # Check and cancel any existing orders first
                if not is_entry:
                    self.client.cancel_all_orders(self.symbol)
                
                # Cancel any existing active order
                if self.active_order_id:
                    try:
                        # Check if order was partially filled before canceling
                        order_status = self.client.get_order(self.symbol, self.active_order_id)
                        
                        if order_status and order_status.get('status') == 'FILLED':
                            # Order was completely filled
                            filled_this_time = float(order_status.get('executedQty', 0))
                            filled_amount += filled_this_time
                            logger.info(f"Order completely filled: {filled_this_time} ({filled_amount} total)")
                            
                            if is_entry:
                                self.position_side = side
                                avg_price = float(order_status.get('avgPrice', 0)) or float(order_status.get('price', 0))
                                self.entry_price = avg_price
                                self.entry_time = datetime.datetime.now()
                            else:
                                self.position_side = None
                                self.entry_price = None
                                self.entry_time = None
                            
                            self.active_order_id = None
                            self.stop_threads = True
                            break
                            
                        elif order_status and order_status.get('status') == 'PARTIALLY_FILLED':
                            # Order was partially filled
                            filled_this_time = float(order_status.get('executedQty', 0))
                            filled_amount += filled_this_time
                            logger.info(f"Order partially filled: {filled_this_time} ({filled_amount} total)")
                        
                        # Cancel the order if it's still open
                        if order_status and order_status.get('status') == 'NEW':
                            self.client.cancel_order(self.symbol, self.active_order_id)
                            logger.info(f"Cancelled previous order: {self.active_order_id}")
                            
                    except Exception as e:
                        logger.warning(f"Error cancelling previous order: {e}")
                    
                    self.active_order_id = None
                
                # Get the current best price
                orderbook = self.client.get_orderbook(self.symbol)
                if side == 'BUY':
                    # For buy orders, use exactly the lowest ask price
                    price = orderbook['asks'][0][0] if orderbook['asks'] else 0  # Lowest ask price
                else:
                    # For sell orders, use exactly the highest bid price
                    price = orderbook['bids'][0][0] if orderbook['bids'] else 0  # Highest bid price
                
                if price <= 0:
                    # Fallback to ticker price if orderbook failed
                    ticker = self.client.get_ticker(self.symbol)
                    price = ticker['last']
                    if price <= 0:
                        logger.error("Could not get valid price from orderbook or ticker")
                        time.sleep(1)
                        continue
                
                # Round price to appropriate precision
                price_precision = get_price_precision(self.symbol)
                price = round_to_precision(price, price_precision)
                
                # Calculate order amount
                if target_amount is None:  # Only calculate once
                    if is_entry:
                        # For entry orders, calculate based on full balance and leverage
                        balance = self.client.get_balance()
                        usdt_balance = balance['USDT']['free']  # Use 100% of balance
                        target_amount = (usdt_balance * current_leverage) / price
                    else:
                        # For exit orders, use the position amount we determined earlier
                        target_amount = position_amount
                
                # Calculate remaining amount needed to complete the order
                remaining_amount = max(0, target_amount - filled_amount)
                
                # Ensure order meets minimum notional value (20 USDT)
                min_amount = calculate_min_order_amount(price)
                
                if remaining_amount < min_amount:
                    if filled_amount > 0:
                        # We've already filled part of the order
                        logger.info(f"Remaining amount {remaining_amount} is below minimum. Order considered complete.")
                        
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
                
                # Place a new limit order for the remaining amount
                order = self.client.place_order(
                    symbol=self.symbol,
                    side=side,
                    order_type='LIMIT',
                    quantity=remaining_amount,
                    price=price,
                    reduce_only=(not is_entry)
                )
                
                if order:
                    # Reset error counter on success
                    consecutive_error_count = 0
                    order_id = int(order.get('orderId', 0))
                    self.active_order_id = order_id
                    logger.info(f"Placed {side} limit order for {remaining_amount} at {price}: {order_id}")
                else:
                    # Order placement failed
                    consecutive_error_count += 1
                    last_error_message = "Order placement failed"
                    logger.error(f"Failed to place order (attempt {consecutive_error_count}/{max_consecutive_errors})")
                    
                    # Handle leverage issues
                    if "margin" in last_error_message.lower() and is_entry:
                        # Step down leverage to address margin issues
                        if current_leverage > 20:
                            if current_leverage == 125:
                                current_leverage = 100
                            elif current_leverage == 100:
                                current_leverage = 75
                            elif current_leverage == 75:
                                current_leverage = 50
                            elif current_leverage == 50:
                                current_leverage = 20
                            else:
                                current_leverage = int(current_leverage * 0.8)  # Reduce by 20%
                            
                            logger.info(f"Margin issue! Reducing leverage to {current_leverage}x and retrying")
                            if self.set_leverage(current_leverage):
                                # Recalculate amount with new leverage
                                if is_entry and filled_amount == 0:
                                    balance = self.client.get_balance()
                                    usdt_balance = balance['USDT']['free']  # 100% of balance
                                    target_amount = (usdt_balance * current_leverage) / price
                                    remaining_amount = target_amount  # No fills yet
                                    # Check minimum again
                                    if remaining_amount < min_amount:
                                        remaining_amount = min_amount
                                        logger.info(f"Using minimum order size: {min_amount}")
                                continue  # Try again with new leverage
                    
                # Wait before checking order status
                time.sleep(1.0)
                
                # Check order status
                if self.active_order_id:
                    order_status = self.client.get_order(self.symbol, self.active_order_id)
                    
                    # Order completely filled
                    if order_status and order_status.get('status') == 'FILLED':
                        filled_this_time = float(order_status.get('executedQty', 0))
                        filled_amount += filled_this_time
                        logger.info(f"Order fully filled! {side} at {price} for {filled_this_time} ({filled_amount}/{target_amount})")
                        
                        if filled_amount >= (target_amount * 0.99):  # 99% filled as complete
                            if is_entry:
                                self.position_side = side
                                avg_price = float(order_status.get('avgPrice', 0)) or float(order_status.get('price', 0))
                                self.entry_price = avg_price
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
                    
                    # Check for partial fills
                    elif order_status and order_status.get('status') == 'PARTIALLY_FILLED':
                        filled_this_time = float(order_status.get('executedQty', 0))
                        filled_amount += filled_this_time
                        logger.info(f"Order partially filled: {filled_this_time} ({filled_amount}/{target_amount})")
                        
                # Brief wait before next iteration
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error in limit order thread: {e}")
                consecutive_error_count += 1
                time.sleep(1)
    
    def place_market_order(self, side: str, is_entry: bool = True, amount: float = None) -> bool:
        """
        Place a market order for immediate execution.
        
        Args:
            side: Order side ('BUY' or 'SELL')
            is_entry: Whether this is an entry order
            amount: Optional specific amount to use, otherwise calculated
            
        Returns:
            bool: Success status
        """
        try:
            # Cancel any active limit orders
            if self.active_order_id:
                try:
                    self.client.cancel_order(self.symbol, self.active_order_id)
                except Exception as e:
                    logger.warning(f"Error cancelling active order: {e}")
                self.active_order_id = None
            
            # Stop any running order threads
            self.stop_threads = True
            if self.limit_order_thread and self.limit_order_thread.is_alive():
                self.limit_order_thread.join(timeout=1.0)
            
            # Cancel any existing orders
            self.client.cancel_all_orders(self.symbol)
            
            # Use provided amount or calculate order amount
            if amount is None:
                if not is_entry:
                    # For position exits, get the actual position size
                    position = self.client.get_position(self.symbol)
                    if position:
                        amount = abs(float(position.get('positionAmt', 0)))
                        logger.info(f"Closing position of {amount} {self.symbol}")
                    
                    # If position not found, use minimum size
                    if amount is None or amount < 0.001:
                        amount = 0.001
                        logger.warning(f"Could not determine position size, using minimum: {amount}")
                else:
                    # For new entries, calculate based on full balance and leverage
                    balance = self.client.get_balance()
                    usdt_balance = balance['USDT']['free']  # Use 100% of balance
                    
                    # Get current price for calculation
                    ticker = self.client.get_ticker(self.symbol)
                    price = ticker['last']
                    
                    # Use full balance with leverage
                    amount = (usdt_balance * self.current_leverage) / price
            
            # Ensure minimum order size meets notional value requirements
            ticker = self.client.get_ticker(self.symbol)
            price = ticker['last']
            min_amount = calculate_min_order_amount(price)
            if amount < min_amount:
                logger.warning(f"Calculated amount {amount} is below minimum notional requirement")
                amount = min_amount
                logger.info(f"Using minimum order size to meet 20 USDT notional requirement: {min_amount}")
            
            # Place market order
            for attempt in range(3):  # Try up to 3 times
                try:
                    order = self.client.place_order(
                        symbol=self.symbol,
                        side=side,
                        order_type='MARKET',
                        quantity=amount,
                        reduce_only=(not is_entry)
                    )
                    
                    if order:
                        logger.info(f"Placed {side} MARKET order for {amount}: {order.get('orderId')}")
                        
                        # Update position tracking
                        if is_entry:
                            self.position_side = side
                            self.entry_price = float(order.get('avgPrice', 0)) or price
                            self.entry_time = datetime.datetime.now()
                        else:
                            self.position_side = None
                            self.entry_price = None
                            self.entry_time = None
                        
                        return True
                    else:
                        logger.error(f"Market order failed (attempt {attempt+1}/3)")
                        
                        # If we're trying to exit and failed, try force close
                        if not is_entry and attempt == 2:
                            logger.info("Falling back to force close...")
                            return self.force_close_position()
                        
                except Exception as e:
                    logger.error(f"Error placing market order (attempt {attempt+1}/3): {e}")
                    
                    # If margin issue and entry order, try reducing leverage
                    if is_entry and "margin" in str(e).lower() and self.current_leverage > 20:
                        new_leverage = max(20, int(self.current_leverage * 0.8))
                        logger.info(f"Margin issue! Reducing leverage to {new_leverage}x and retrying")
                        self.set_leverage(new_leverage)
                        
                        # Recalculate amount with new leverage
                        balance = self.client.get_balance()
                        usdt_balance = balance['USDT']['free']
                        amount = (usdt_balance * new_leverage) / price
                        if amount < min_amount:
                            amount = min_amount
                    
                    # If this is the last attempt and exiting, try force close
                    if not is_entry and attempt == 2:
                        logger.info("Trying force close as last resort...")
                        return self.force_close_position()
                
                # Increase delay between retries
                time.sleep(1.0 * (attempt + 1))
            
            return False
            
        except Exception as e:
            logger.error(f"Critical error placing market order: {e}")
            
            # If exiting, try force close as last resort
            if not is_entry:
                logger.info("Critical failure during market exit - attempting force close...")
                return self.force_close_position()
            
            return False
    
    def long(self) -> bool:
        """Enter a long position using a limit order."""
        # First check if we already have a position
        if self.position_side:
            logger.warning(f"Already in a {self.position_side} position. Exit first.")
            return False
        
        logger.info(f"Entering LONG position with limit order at {self.current_leverage}x leverage...")
        self.place_limit_order(side='BUY', is_entry=True)
        return True
    
    def short(self) -> bool:
        """Enter a short position using a limit order."""
        # First check if we already have a position
        if self.position_side:
            logger.warning(f"Already in a {self.position_side} position. Exit first.")
            return False
        
        logger.info(f"Entering SHORT position with limit order at {self.current_leverage}x leverage...")
        self.place_limit_order(side='SELL', is_entry=True)
        return True
    
    def terminate(self) -> bool:
        """Exit the current position using a limit order."""
        # Check if we have a position
        if not self.position_side:
            logger.warning("No position to terminate.")
            return False
        
        # Determine exit side (opposite of position)
        exit_side = 'SELL' if self.position_side == 'BUY' else 'BUY'
        
        logger.info(f"Terminating {self.position_side} position with limit order...")
        self.place_limit_order(side=exit_side, is_entry=False)
        return True
    
    def market_exit(self) -> bool:
        """Immediately exit the current position using a market order."""
        logger.info("EMERGENCY EXIT - Attempting to close any open position...")
        
        # First try regular exit if we know our position
        if self.position_side:
            exit_side = 'SELL' if self.position_side == 'BUY' else 'BUY'
            if self.place_market_order(side=exit_side, is_entry=False):
                logger.info("Position closed with market order")
                return True
        
        # If regular exit failed or position tracking is incorrect, force close
        return self.force_close_position()
    
    def force_close_position(self) -> bool:
        """Force close any open position regardless of our internal state tracking."""
        try:
            # Get position directly from API
            position = self.client.get_position(self.symbol)
            
            if not position or abs(float(position.get('positionAmt', 0))) < 0.0001:
                logger.info("No open position found to close")
                self.position_side = None
                self.entry_price = None
                self.entry_time = None
                return False
            
            # Determine position details
            position_amount = abs(float(position.get('positionAmt', 0)))
            is_long = float(position.get('positionAmt', 0)) > 0
            exit_side = 'SELL' if is_long else 'BUY'
            position_name = 'LONG' if is_long else 'SHORT'
            
            logger.info(f"Force closing {position_name} position of size {position_amount}")
            
            # Cancel all open orders first
            self.client.cancel_all_orders(self.symbol)
            
            # Try market order with reduceOnly
            order = self.client.place_order(
                symbol=self.symbol,
                side=exit_side,
                order_type='MARKET',
                quantity=position_amount,
                reduce_only=True
            )
            
            if order:
                logger.info(f"Position force closed with order ID: {order.get('orderId')}")
                self.position_side = None
                self.entry_price = None
                self.entry_time = None
                return True
            
            # If that failed, try other approaches
            # Try with minimum size to at least reduce the position
            ticker = self.client.get_ticker(self.symbol)
            min_amount = calculate_min_order_amount(ticker['last'])
            
            min_order = self.client.place_order(
                symbol=self.symbol,
                side=exit_side,
                order_type='MARKET',
                quantity=min_amount,
                reduce_only=True
            )
            
            if min_order:
                logger.info(f"Reduced position with minimum order: {min_order.get('orderId')}")
                logger.warning("Position partially closed. Manual intervention may be needed.")
            
            # Check position again
            position = self.client.get_position(self.symbol)
            if not position or abs(float(position.get('positionAmt', 0))) < 0.0001:
                logger.info("Position successfully closed after all attempts")
                self.position_side = None
                self.entry_price = None
                self.entry_time = None
                return True
            else:
                logger.error("Failed to completely close position. Manual intervention required.")
                return False
                
        except Exception as e:
            logger.error(f"Error in force close: {e}")
            return False
    
    def show_status(self) -> None:
        """Display the current trading status."""
        try:
            # Get position directly from API
            position = self.client.get_position(self.symbol)
            
            # Get balance
            balance = self.client.get_balance()
            
            # Get current price
            ticker = self.client.get_ticker(self.symbol)
            
            safe_print("--- Binance Status ---")
            safe_print(f"Symbol: {self.symbol} | Price: {ticker['last']} | Leverage: {self.current_leverage}x")
            safe_print(f"Balance: {balance['USDT']['free']} USDT | Total: {balance['USDT']['total']} USDT")
            
            # Format position info
            if position:
                position_info = format_position_info(position)
                for line in position_info.split('\n'):
                    safe_print(line)
                
                if self.entry_time:
                    position_time = datetime.datetime.now() - self.entry_time
                    safe_print(f"Position time: {position_time}")
            else:
                safe_print("No active position")
                # Reset internal state if no position is found
                self.position_side = None
                self.entry_price = None
                self.entry_time = None
            
            safe_print("-------------------")
        except Exception as e:
            logger.error(f"Error showing status: {e}")
            
    def reset_position_tracking(self) -> bool:
        """Reset all position tracking state variables."""
        self.position_side = None
        self.entry_price = None
        self.entry_time = None
        self.active_order_id = None
        self.stop_threads = True
        
        logger.info("Position tracking state has been reset")
        
        # Force check for actual positions
        has_position = self._check_existing_position()
        if has_position:
            logger.warning(f"NOTE: You still have an active {self.position_side} position on Binance")
        else:
            logger.info("No active positions found on Binance")
        
        return has_position 
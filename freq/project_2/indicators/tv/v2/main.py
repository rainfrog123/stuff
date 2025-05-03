#!/allah/freqtrade/.venv/bin/python3.11

import os
import sys
import time
from dotenv import load_dotenv
from typing import Optional

from logger import logger, safe_print
from binance_client import BinanceClient
from trading_manager import TradingManager

def load_credentials() -> tuple[str, str]:
    """Load API credentials from environment variables or .env file."""
    # First try to load from .env file
    load_dotenv()
    
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    
    if not api_key or not api_secret:
        # If not found in environment, use hardcoded values (for backward compatibility)
        api_key = "ofQzX3gGAKS777NyYIovAy1XyqLzGC2UJPMh9jqIYEfieFRy3DCkZJl15VYA2zXo"
        api_secret = "QVJpTFgHIEv74LmCT5clX8o1zAFEEqJqKpg2ePklObM1Ybv9iKNe8jvM7MRjoz07"
        logger.warning("Using hardcoded API keys. Consider using environment variables for security.")
    
    return api_key, api_secret

def main():
    """Main function to run the Binance trading assistant."""
    # Load API credentials
    api_key, api_secret = load_credentials()
    
    # Default to ETH/USDT perpetual futures
    symbol = os.getenv('TRADING_SYMBOL', 'ETHUSDT')
    
    try:
        # Initialize the Binance client
        binance_client = BinanceClient(api_key, api_secret)
        
        # Initialize trading manager
        default_leverage = int(os.getenv('DEFAULT_LEVERAGE', '125'))
        trading_manager = TradingManager(binance_client, symbol, default_leverage)
        
        safe_print(f"Binance Trading Assistant v2 initialized")
        safe_print(f"Trading {symbol} futures with {trading_manager.current_leverage}x leverage")
        
        # Check for existing positions at startup
        has_position = trading_manager._check_existing_position()
        if has_position:
            safe_print(f"EXISTING POSITION DETECTED: {trading_manager.position_side}")
        
        # Show available commands
        safe_print("Available commands:")
        safe_print("1=LONG, 2=SHORT, 3=Exit(limit), 4=Exit(market), 5=Status, 0=Quit")
        safe_print("F=Force Close (ignores tracking), C=Clear tracking state, L=Change Leverage")
        safe_print("(Use '!' for emergency market exit)")
        
        # Show status at startup
        trading_manager.show_status()
        
        # Counter for monitoring state changes
        state_counter = 0
        last_position_side = trading_manager.position_side
        
        while True:
            # Check if position state has changed
            if trading_manager.position_side != last_position_side:
                # Position state changed, print a clear notification
                if trading_manager.position_side is not None:
                    safe_print(f"Position opened: {trading_manager.position_side}")
                else:
                    safe_print("Position closed")
                
                last_position_side = trading_manager.position_side
            
            # Every 20 loops, reprint the command menu to ensure it's visible
            if state_counter % 20 == 0 and state_counter > 0:
                safe_print("Commands: 1=LONG, 2=SHORT, 3=Exit, 4=Emergency, 5=Status, F=Force Close, C=Clear tracking, L=Leverage, 0=Quit")
            
            state_counter += 1
            
            try:
                # Use a clear prompt with current position state
                position_indicator = f"[{trading_manager.position_side}]" if trading_manager.position_side else "[NO-POS]"
                
                # Clear line and print the prompt
                sys.stdout.write(f"\r{position_indicator} Command: ")
                sys.stdout.flush()
                
                command = input().strip()
                
                # Emergency exit for ! character
                if command == '!' and trading_manager.position_side is not None:
                    safe_print("!!! EMERGENCY EXIT TRIGGERED !!!")
                    trading_manager.market_exit()
                    continue
                
                if command == '1':
                    trading_manager.long()
                elif command == '2':
                    trading_manager.short()
                elif command == '3':
                    trading_manager.terminate()
                elif command == '4':
                    trading_manager.market_exit()
                elif command == '5' or command.lower() == 'status':
                    trading_manager.show_status()
                elif command == '0' or command.lower() in ['q', 'quit', 'exit']:
                    break
                elif command.upper() == 'F' or command.lower() == 'force close':
                    trading_manager.force_close_position()
                elif command.upper() == 'C' or command.lower() == 'clear tracking state':
                    trading_manager.reset_position_tracking()
                elif command.upper() == 'L' or command.lower() == 'leverage':
                    try:
                        safe_print(f"Current leverage: {trading_manager.current_leverage}x")
                        sys.stdout.write("Enter new leverage (20-125): ")
                        sys.stdout.flush()
                        new_leverage = int(input().strip())
                        if 1 <= new_leverage <= 125:
                            if trading_manager.set_leverage(new_leverage):
                                safe_print(f"Leverage changed to {new_leverage}x")
                            else:
                                safe_print(f"Failed to set leverage to {new_leverage}x")
                        else:
                            safe_print("Invalid leverage value. Must be between 1 and 125.")
                    except ValueError:
                        safe_print("Invalid input. Please enter a number.")
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
    
    except Exception as e:
        logger.error(f"Initialization error: {e}")
        safe_print(f"Failed to initialize: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
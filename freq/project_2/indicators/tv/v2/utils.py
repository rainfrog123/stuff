#!/allah/freqtrade/.venv/bin/python3.11

import time
import datetime
from typing import Dict, Any, Tuple, Optional, List

def calculate_min_order_amount(price: float) -> float:
    """
    Calculate the minimum order amount based on Binance's minimum notional value requirement.
    
    Args:
        price: Current price of the asset
        
    Returns:
        float: Minimum order amount that satisfies the notional value requirement
    """
    # Binance requires minimum notional value of 20 USDT for futures
    min_notional = 20.1  # Slightly higher to be safe
    
    # Calculate minimum amount
    min_amount = min_notional / price
    
    # Ensure it's also above the minimum quantity requirement (0.001 for ETH)
    min_amount = max(min_amount, 0.001)
    
    # Round to appropriate precision (ETH futures uses 3 decimal places)
    min_amount = round_to_precision(min_amount, 3)
    
    return min_amount

def round_to_precision(value: float, precision: int) -> float:
    """
    Round a value to the specified decimal precision.
    
    Args:
        value: The value to round
        precision: Number of decimal places
        
    Returns:
        float: Rounded value
    """
    factor = 10 ** precision
    return float(int(value * factor) / factor)

def get_quantity_precision(symbol: str) -> int:
    """
    Get the quantity precision for a specific symbol.
    
    Args:
        symbol: Trading symbol
        
    Returns:
        int: Decimal precision for the quantity
    """
    # Common quantity precisions for Binance futures
    precision_map = {
        'BTCUSDT': 3,
        'ETHUSDT': 3,
        'BNBUSDT': 2,
        'ADAUSDT': 0,
        'XRPUSDT': 1,
        'DOGEUSDT': 0,
        'SOLUSDT': 1
    }
    
    # Default to 3 decimals if symbol not found
    return precision_map.get(symbol, 3)

def get_price_precision(symbol: str) -> int:
    """
    Get the price precision for a specific symbol.
    
    Args:
        symbol: Trading symbol
        
    Returns:
        int: Decimal precision for the price
    """
    # Common price precisions for Binance futures
    precision_map = {
        'BTCUSDT': 1,  # $0.1
        'ETHUSDT': 2,  # $0.01
        'BNBUSDT': 2,  # $0.01
        'ADAUSDT': 4,  # $0.0001
        'XRPUSDT': 5,  # $0.00001
        'DOGEUSDT': 6,  # $0.000001
        'SOLUSDT': 3   # $0.001
    }
    
    # Default to 2 decimals if symbol not found
    return precision_map.get(symbol, 2)

def format_position_info(position: Dict[str, Any]) -> str:
    """Format position information into readable string."""
    if not position or float(position.get('positionAmt', 0)) == 0:
        return "No active position"
        
    position_size = abs(float(position.get('positionAmt', 0)))
    entry_price = float(position.get('entryPrice', 0))
    unrealized_pnl = float(position.get('unrealizedProfit', 0))
    leverage = position.get('leverage', 0)
    position_side = 'LONG' if float(position.get('positionAmt', 0)) > 0 else 'SHORT'
    liquidation_price = float(position.get('liquidationPrice', 0))
    margin_type = position.get('marginType', 'unknown')
    isolated_margin = float(position.get('isolatedMargin', 0)) if margin_type == 'isolated' else 0
    
    info = [
        f"Position: {position_side} | Size: {position_size} ETH | Entry: {entry_price}",
        f"P&L: {unrealized_pnl:.5f} USDT | Liq. Price: {liquidation_price}",
        f"Leverage: {leverage}x | Margin Type: {margin_type.upper()}"
    ]
    
    if margin_type == 'isolated' and isolated_margin > 0:
        info.append(f"Isolated Margin: {isolated_margin} USDT")
        
    return "\n".join(info)

def parse_position_data(position_data: List[Dict[str, Any]], symbol: str) -> Optional[Dict[str, Any]]:
    """
    Parse position data from Binance API to extract the relevant position
    
    Args:
        position_data: List of positions from Binance API
        symbol: Trading symbol to filter on
        
    Returns:
        Optional[Dict[str, Any]]: The position data for the specified symbol or None
    """
    for position in position_data:
        if position.get('symbol') == symbol and abs(float(position.get('positionAmt', 0))) > 0.0001:
            return position
    return None 
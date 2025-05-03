"""
Patch to allow 5s timeframe for Binance
"""
import logging
import ccxt
from freqtrade.exchange.exchange import Exchange

logger = logging.getLogger(__name__)

# Store the original validate_timeframes method
original_validate_timeframes = Exchange.validate_timeframes

def patched_validate_timeframes(self, timeframe: str | None) -> None:
    """
    Patched version of validate_timeframes that allows 5s when use_public_trades is enabled
    """
    # If timeframe is 5s and we're using public trades, allow it
    if timeframe == '5s' and self._config.get('exchange', {}).get('use_public_trades', False):
        logger.info("Allowing 5s timeframe because use_public_trades is enabled")
        return
    
    # Otherwise use the original validation
    return original_validate_timeframes(self, timeframe)

# Apply the patch
Exchange.validate_timeframes = patched_validate_timeframes

logger.info("Applied patch to allow 5s timeframe with use_public_trades") 
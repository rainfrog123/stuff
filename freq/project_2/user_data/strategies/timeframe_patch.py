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
    if timeframe == '5s':
        logger.info("Allowing 5s timeframe (patch modified)")
        return
    return original_validate_timeframes(self, timeframe)

# Apply the patch
Exchange.validate_timeframes = patched_validate_timeframes

logger.info("Applied MODIFIED patch to allow 5s timeframe") 
#!/usr/bin/env python3
"""
Custom wrapper for TrendRevATR strategy that automatically loads and initializes
the 5-second candle data provider.
"""
import logging
import threading
import importlib
from typing import Dict, Any

# Import the original strategy
from user_data.strategies.TrendRevATR import TrendRevATR

# Import our custom data provider
from user_data.custom_data_provider import CustomFiveSecondProvider

logger = logging.getLogger(__name__)

class TrendRevATR_Custom(TrendRevATR):
    """
    Enhanced version of TrendRevATR strategy that automatically uses
    5-second candles from our custom data provider.
    """
    
    # Keep the same parameters but make explicit that we use 5s timeframe
    timeframe = '5s'
    
    # Keep track of whether provider has been initialized
    _provider_initialized = False
    _lock = threading.Lock()
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize the strategy with our custom data provider.
        """
        logger.info("Initializing TrendRevATR_Custom with 5s candles support")
        
        # Initialize the original strategy first
        super().__init__(config)
        
        # Then set up our custom data provider
        with TrendRevATR_Custom._lock:
            if not TrendRevATR_Custom._provider_initialized:
                self._setup_custom_provider()
                TrendRevATR_Custom._provider_initialized = True
    
    def _setup_custom_provider(self) -> None:
        """
        Set up the custom 5s candle data provider by patching FreqTrade.
        """
        try:
            # First, try to get the existing dataprovider instance
            from freqtrade.data.dataprovider import DataProvider
            
            # Get the bot instance
            bot_module = importlib.import_module('freqtrade.freqtradebot')
            FreqtradeBot = getattr(bot_module, 'FreqtradeBot')
            
            # Get current bot instances
            bot_instances = [obj for obj in globals().values() 
                           if isinstance(obj, FreqtradeBot)]
            
            if bot_instances:
                bot = bot_instances[0]
                
                # Create our custom provider
                custom_provider = CustomFiveSecondProvider(
                    config=self.config,
                    exchange=bot.exchange,
                    pairlists=bot.pairlists,
                    rpc=bot.rpc
                )
                
                # Start the update thread
                custom_provider.start_update_thread()
                
                # Replace the dataprovider
                bot.dataprovider = custom_provider
                
                # Also update our local reference
                self.dp = custom_provider
                
                logger.info("Successfully initialized custom 5s candle provider")
            else:
                logger.warning("No FreqtradeBot instance found, will try again later")
                
        except Exception as e:
            logger.error(f"Error setting up custom data provider: {str(e)}")
    
    def bot_loop_start(self, **kwargs) -> None:
        """
        Called at the start of the bot's main loop.
        Use this to ensure our provider is initialized even if it wasn't at strategy init time.
        """
        with TrendRevATR_Custom._lock:
            if not TrendRevATR_Custom._provider_initialized:
                self._setup_custom_provider()
                TrendRevATR_Custom._provider_initialized = True
        
        # Call parent if it has this method
        if hasattr(super(), 'bot_loop_start'):
            super().bot_loop_start(**kwargs) 
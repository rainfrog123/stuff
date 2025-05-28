# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file

from freqtrade.strategy import IStrategy
from pandas import DataFrame
import logging
import sys
import numpy as np

# Configure logger to be much more visible
logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

class SimpleTestStrategy(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '5s'
    can_short: bool = True
    minimal_roi = {"0": 100}
    stoploss = -0.99
    trailing_stop = False
    use_custom_stoploss = False
    startup_candle_count: int = 1
    
    # Class variable to track iterations
    iteration_count = 0
    
    # Force an entry every N iterations (set to 0 to disable)
    force_entry_every = 20
    
    def __init__(self, config: dict) -> None:
        """Initialize the strategy with configuration"""
        super().__init__(config)
        logger.info("🚀 SimpleTestStrategy initialized - VOLUME COMPARISON STRATEGY 🚀")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Log this method is called
        pair = metadata.get('pair', 'UNKNOWN')
        logger.info(f"🔍 populate_indicators called for {pair} with {len(dataframe)} candles")
        
        # No indicators needed for this test strategy
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Get pair name for logging
        pair = metadata.get('pair', 'UNKNOWN')
        
        # Increment our iteration counter
        self.iteration_count += 1
        
        # Debug start of function
        logger.info(f"⚡ populate_entry_trend called for {pair} - Iteration #{self.iteration_count}")
        logger.info(f"📊 Received {len(dataframe)} candles for analysis")
        
        # Force entry periodically for testing if enabled
        force_entry = False
        if self.force_entry_every > 0 and self.iteration_count % self.force_entry_every == 0:
            force_entry = True
            logger.info(f"🔥 FORCING ENTRY on iteration #{self.iteration_count} for testing!")
        
        # Start with empty entry signals
        dataframe['enter_long'] = 0
        dataframe['enter_short'] = 0
        
        # Create a shifted column with previous candle's volume
        dataframe['prev_volume'] = dataframe['volume'].shift(1)
        
        # Make sure we have enough data
        if len(dataframe) < 2:
            logger.warning(f"⚠️ Not enough candles for {pair}: {len(dataframe)} candles")
            return dataframe
        
        # Log some sample data
        logger.info(f"Sample data for {pair}:")
        sample_data = dataframe.tail(3)[['date', 'volume', 'prev_volume']].copy()
        for i, row in sample_data.iterrows():
            logger.info(f"Candle {i}: Date={row['date']}, Volume={row['volume']}, Prev={row['prev_volume']}")
        
        # Check if volumes are all zero
        if dataframe['volume'].sum() == 0:
            logger.warning(f"⚠️ All volumes are ZERO for {pair}! No trades possible.")
            return dataframe
        
        # Set entry conditions: current volume > previous candle's volume
        # NaN check is needed for the first candle
        entry_condition = (dataframe['volume'] > dataframe['prev_volume']) & (~dataframe['prev_volume'].isna())
        
        # Count potential entry signals
        signal_count = entry_condition.sum()
        logger.info(f"Found {signal_count} potential entry signals based on volume comparison")
        
        # Apply conditions and convert to integers (0 or 1)
        if not force_entry:
            dataframe['enter_long'] = entry_condition.astype(int)
            dataframe['enter_short'] = entry_condition.astype(int)
        else:
            # Force entry on the last candle for testing
            dataframe.loc[dataframe.index[-1], 'enter_long'] = 1
            dataframe.loc[dataframe.index[-1], 'enter_short'] = 1
            logger.info(f"🔥 FORCED ENTRY applied on last candle: {dataframe.index[-1]}")
        
        # Log entry signals
        entry_indices = dataframe[dataframe['enter_long'] == 1].index.tolist()
        if entry_indices:
            logger.info(f"📈 ENTRY SIGNALS for {pair} at candles: {entry_indices[:5]}" + 
                      (f" and {len(entry_indices)-5} more" if len(entry_indices) > 5 else ""))
            for i in entry_indices[:3]:  # Log details for first 3 signals
                if i > 0:  # Skip first candle as it has no previous
                    logger.info(f"Entry at candle {i}: Volume {dataframe['volume'].iloc[i]} > Previous {dataframe['prev_volume'].iloc[i]}")
        else:
            logger.warning(f"❌ NO ENTRY SIGNALS found for {pair}!")
        
        # Before returning, check if enter signals were actually set
        final_signal_count = dataframe['enter_long'].sum()
        logger.info(f"Final entry signal count: {final_signal_count} for {pair}")
        
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Log this method is called
        pair = metadata.get('pair', 'UNKNOWN')
        logger.info(f"⏹️ populate_exit_trend called for {pair}")
        
        # Never trigger exit signals (let default exit logic handle it)
        return dataframe

# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file

from freqtrade.strategy import IStrategy
from pandas import DataFrame
import logging
from datetime import datetime
import talib.abstract as ta
import pandas as pd

logger = logging.getLogger(__name__)

class SimpleTestStrategy(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '5s'
    can_short: bool = True
    
    # Only process new candles, not all historical data
    process_only_new_candles = True
    
    # More realistic ROI: 1% profit target
    minimal_roi = {"0": 0.01, "10": 0.005, "30": 0}
    # Tighter stop loss for 5s timeframe
    stoploss = -0.01
    trailing_stop = False  # We'll use custom trailing stop
    use_custom_stoploss = True  # Enable ATR-based trailing stop
    startup_candle_count: int = 20  # Need more candles for ATR calculation

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Volume indicators for entry signals
        dataframe['prev_volume_1'] = dataframe['volume'].shift(1)
        dataframe['prev_volume_2'] = dataframe['volume'].shift(2)
        dataframe['prev_2_volume_sum'] = dataframe['prev_volume_1'] + dataframe['prev_volume_2']
        
        # ATR for trailing stop calculation
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Get pair name for logging
        pair = metadata['pair']
        
        # More selective entry condition: volume spike must be significant (2x previous average)
        volume_spike = (
            (dataframe['volume'] > dataframe['prev_2_volume_sum'] * 1.5) &  # 1.5x more selective
            (~dataframe['prev_volume_1'].isna()) & 
            (~dataframe['prev_volume_2'].isna()) &
            (dataframe['volume'] > 0)  # Ensure positive volume
        )
        
        # Enter long when current volume significantly exceeds sum of previous 2 candles  
        dataframe.loc[volume_spike, 'enter_long'] = 1
        dataframe.loc[~volume_spike, 'enter_long'] = 0
        
        # No short entries for now
        dataframe['enter_short'] = 0
        
        # More detailed logging for debugging
        entry_count = volume_spike.sum()
        total_candles = len(dataframe)
        
        # Only log for the latest candle (what actually matters for trading)
        if not dataframe.empty:
            latest_entry = dataframe['enter_long'].iloc[-1] == 1
            latest_volume = dataframe['volume'].iloc[-1]
            latest_prev_sum = dataframe['prev_2_volume_sum'].iloc[-1] if not dataframe['prev_2_volume_sum'].isna().iloc[-1] else 0
            
            if latest_entry:
                ratio = latest_volume / latest_prev_sum if latest_prev_sum > 0 else 0
                logger.info(f"🎯 NEW ENTRY SIGNAL for {pair}")
                logger.info(f"   💹 Current vol={latest_volume:.0f}, prev_sum={latest_prev_sum:.0f}, ratio={ratio:.2f}x")
            elif entry_count > 0:
                logger.debug(f"📈 {entry_count} historical signals (not actionable)")
        
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # No exit signals - using only ATR-based trailing stop
        dataframe['exit_long'] = 0
        dataframe['exit_short'] = 0
        return dataframe

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime,
                       current_rate: float, current_profit: float, **kwargs) -> float:
        """
        Custom ATR-based trailing stoploss.
        Uses ATR * 0.5 as the trailing stop distance.
        """
        # Get the latest analyzed dataframe
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if dataframe is None or dataframe.empty:
            # Fallback to initial stoploss if no data
            return self.stoploss
        
        # Get the latest ATR value
        latest_atr = dataframe['atr'].iloc[-1]
        
        if pd.isna(latest_atr) or latest_atr <= 0:
            # Fallback to initial stoploss if ATR is invalid
            return self.stoploss
        
        # Calculate ATR-based stop distance (ATR * 0.5)
        atr_stop_distance = latest_atr * 0.5
        
        # Convert to percentage of current rate
        stop_percentage = atr_stop_distance / current_rate
        
        # For long positions, return negative percentage (stop below current price)
        # For short positions, return positive percentage (stop above current price)
        if trade.is_short:
            return stop_percentage
        else:
            return -stop_percentage

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: str | None, side: str,
                 **kwargs) -> float:
        """
        Customize leverage for each new trade. This method is only called in futures mode.
        Return maximum leverage available for the pair.
        """
        return max_leverage

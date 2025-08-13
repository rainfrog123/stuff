from datetime import datetime
from pandas import DataFrame
import numpy as np
import pandas as pd
import talib.abstract as ta
import logging

from freqtrade.strategy import IStrategy, informative
from freqtrade.persistence import Trade, Order

logger = logging.getLogger(__name__)

class gamble(IStrategy):
    """
    A trend-following strategy using TEMA (Triple Exponential Moving Average)
    for trend detection with random entry filtering.
    """
    
    # Strategy interface version
    INTERFACE_VERSION = 3
    
    # Strategy parameters
    timeframe = '5s'
    can_short: bool = True
    process_only_new_candles = True
    startup_candle_count: int = 60
    # ROI and stoploss
    # minimal_roi = {"0": 0.004 * 125}
    minimal_roi = {"0": 1}
    stoploss = -0.001 * 125
    
    # Exit configuration
    trailing_stop = False
    use_custom_stoploss = False
    use_custom_exit = True
    
    # Indicator parameters
    tema_length = 50
    atr_length = 14

    def custom_exit(self, pair: str, trade: Trade, current_time: datetime,
                    current_rate: float, current_profit: float, **kwargs):

        # If an exit (or any) order is already open, don't request another
        if trade.has_open_orders:
            return None

        # Only set the TP once per trade
        if trade.nr_of_successful_exits == 0 and trade.get_custom_data("tp_placed") != True:
            trade.set_custom_data(key="tp_placed", value=True)
            return "place_tp_now"

        return None
    def custom_exit_price(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        proposed_rate: float,
        current_profit: float,
        exit_tag: str | None,
        **kwargs,
    ) -> float:
        """
        Set custom exit price for trades.
        Targets 0.2% profit for long trades, 0.2% profit for short trades.
        
        Note: If adjust_order_price() or adjust_exit_price() methods exist,
        they take precedence over this method. Currently not implemented.
        """
        risk_factor = 0.002  # 0.2%
        if trade.is_short:
            target = trade.open_rate * (1 - risk_factor)  # 0.2% profit for short
        else:
            target = trade.open_rate * (1 + risk_factor)  # 0.2% profit for long
        return target



    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Calculate indicators for the strategy.
        Uses TEMA (Triple Exponential Moving Average) for trend detection.
        """
        # Calculate TEMA on 5s data
        dataframe['tema'] = ta.TEMA(dataframe['close'], timeperiod=self.tema_length)
        
        # Trend detection
        dataframe['tema_prev'] = dataframe['tema'].shift(1)
        dataframe['trend_up'] = dataframe['tema'] > dataframe['tema_prev']
        dataframe['trend_down'] = dataframe['tema'] < dataframe['tema_prev']
        
        # Categorize trend direction
        dataframe['trend'] = np.where(
            dataframe['trend_up'], 'UP',
            np.where(dataframe['trend_down'], 'DOWN', 'FLAT')
        )
        
        # Detect trend changes
        dataframe['trend_prev'] = dataframe['trend'].shift(1)
        dataframe['trend_flip'] = (
            (dataframe['trend'] != dataframe['trend_prev']) & 
            (dataframe['trend'] != 'FLAT')
        )
        
        # Specific reversal signals
        dataframe['reversal_to_up'] = (
            dataframe['trend_flip'] & (dataframe['trend'] == 'UP')
        )
        dataframe['reversal_to_down'] = (
            dataframe['trend_flip'] & (dataframe['trend'] == 'DOWN')
        )
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate entry signals based on trend reversals.
        Uses random filtering (currently set to always enter).
        """
        # Seed for reproducible backtests (comment out for live randomness)
        np.random.seed(42)
        
        # Random entry filter (currently allows all entries)
        dataframe['random_entry'] = np.random.random(len(dataframe)) < 1
        
        # Long entry: trend flips to UP
        dataframe.loc[
            (
                dataframe['trend_flip'] & 
                (dataframe['trend'] == 'UP') & 
                dataframe['random_entry']
            ),
            'enter_long'
        ] = 1
        
        # Short entry: trend flips to DOWN
        dataframe.loc[
            (
                dataframe['trend_flip'] & 
                (dataframe['trend'] == 'DOWN') & 
                dataframe['random_entry']
            ),
            'enter_short'
        ] = 1
        
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate exit signals.
        Currently relies on ROI and stoploss for exits.
        """
        return dataframe

    def leverage(
        self, 
        pair: str, 
        current_time: datetime, 
        current_rate: float,
        proposed_leverage: float, 
        max_leverage: float, 
        entry_tag: str | None, 
        side: str,
        **kwargs
    ) -> float:
        """
        Determine the leverage to use for this trade.
        Currently uses maximum available leverage.
        """
        return max_leverage

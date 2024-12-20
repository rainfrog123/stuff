from freqtrade.strategy import IStrategy, informative
from pandas import DataFrame
import talib.abstract as ta
import numpy as np
import logging
from typing import Optional
from datetime import datetime  # Add this line to import datetime
from freqtrade.persistence import Trade


class MultiTimeframeTEMAAgreement(IStrategy):
    """
    Multi-Timeframe TEMA Strategy with Trend Agreement using Informative Pairs.
    """
    # Define the main timeframe
    timeframe = '1m'
    can_short = True  # Enable shorting
    stoploss = -0.02  # Default stoploss
    use_custom_stoploss = True  # Enable custom stoploss logic
    startup_candle_count = 300  # Minimum candles for TEMA calculation

    # TEMA configuration
    tema_period = 50

    @informative('3m')
    def populate_indicators_3m(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate indicators for the 3-minute informative timeframe.
        """
        dataframe['tema'] = ta.TEMA(dataframe['close'], timeperiod=self.tema_period)
        dataframe['trend'] = np.where(dataframe['tema'] > dataframe['tema'].shift(1), 1,
                                      np.where(dataframe['tema'] < dataframe['tema'].shift(1), -1, 0))
        return dataframe

    @informative('5m')
    def populate_indicators_5m(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate indicators for the 5-minute informative timeframe.
        """
        dataframe['tema'] = ta.TEMA(dataframe['close'], timeperiod=self.tema_period)
        dataframe['trend'] = np.where(dataframe['tema'] > dataframe['tema'].shift(1), 1,
                                      np.where(dataframe['tema'] < dataframe['tema'].shift(1), -1, 0))
        return dataframe

    @informative('15m')
    def populate_indicators_15m(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate indicators for the 15-minute informative timeframe.
        """
        dataframe['tema'] = ta.TEMA(dataframe['close'], timeperiod=self.tema_period)
        dataframe['trend'] = np.where(dataframe['tema'] > dataframe['tema'].shift(1), 1,
                                      np.where(dataframe['tema'] < dataframe['tema'].shift(1), -1, 0))
        return dataframe

    @informative('30m')
    def populate_indicators_30m(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate indicators for the 30-minute informative timeframe.
        """
        dataframe['tema'] = ta.TEMA(dataframe['close'], timeperiod=self.tema_period)
        dataframe['trend'] = np.where(dataframe['tema'] > dataframe['tema'].shift(1), 1,
                                      np.where(dataframe['tema'] < dataframe['tema'].shift(1), -1, 0))
        return dataframe

    @informative('1h')
    def populate_indicators_1h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate indicators for the 1-hour informative timeframe.
        """
        dataframe['tema'] = ta.TEMA(dataframe['close'], timeperiod=self.tema_period)
        dataframe['trend'] = np.where(dataframe['tema'] > dataframe['tema'].shift(1), 1,
                                      np.where(dataframe['tema'] < dataframe['tema'].shift(1), -1, 0))
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate indicators for the main timeframe.
        """
        # Base timeframe TEMA calculation
        dataframe['tema'] = ta.TEMA(dataframe['close'], timeperiod=self.tema_period)
        dataframe['trend'] = np.where(dataframe['tema'] > dataframe['tema'].shift(1), 1,
                                      np.where(dataframe['tema'] < dataframe['tema'].shift(1), -1, 0))
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate entry signals based on multi-timeframe trend agreement.
        """
        # Ensure all trend columns exist (from main and informative timeframes)
        dataframe['is_trend_aligned_up'] = (
            (dataframe['trend'] == 1) &
            (dataframe['trend_3m'] == 1) &
            (dataframe['trend_5m'] == 1) &
            (dataframe['trend_15m'] == 1) &
            (dataframe['trend_30m'] == 1) &
            (dataframe['trend_1h'] == 1)
        )
        dataframe['is_trend_aligned_down'] = (
            (dataframe['trend'] == -1) &
            (dataframe['trend_3m'] == -1) &
            (dataframe['trend_5m'] == -1) &
            (dataframe['trend_15m'] == -1) &
            (dataframe['trend_30m'] == -1) &
            (dataframe['trend_1h'] == -1)
        )

        # Generate long entry signal
        dataframe.loc[
            dataframe['is_trend_aligned_up'],
            ['enter_long', 'enter_tag']
        ] = (1, 'aligned_up')

        # Generate short entry signal
        dataframe.loc[
            dataframe['is_trend_aligned_down'],
            ['enter_short', 'enter_tag']
        ] = (1, 'aligned_down')

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Exit signals are handled by the trailing stop or stoploss.
        """
        return dataframe

    def leverage(self, pair: str, current_time: datetime, current_rate: float, proposed_leverage: float, max_leverage: float, entry_tag: Optional[str], side: str, current_profit: Optional[float] = None, **kwargs) -> float:
        # save this max_leverage value to a variable
        set_leverage = max_leverage * 0.9
        return set_leverage
        # return 1

    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime, current_rate: float,
                        current_profit: float, **kwargs) -> float:
        
        # Extract the liquidation price and open rate from the trade
        liquidation_price = trade.liquidation_price
        open_rate = trade.open_rate

        # Check for valid liquidation price and open rate
      

        # Calculate the distance to the liquidation price
        distance_to_liquidation = abs(open_rate - liquidation_price)

        # Determine the stoploss price based on trade direction (long or short)
        if trade.is_short:
            stoploss_price = open_rate + (distance_to_liquidation * 0.8)  # Short: stoploss above open rate
        else:
            stoploss_price = open_rate - (distance_to_liquidation * 0.8)  # Long: stoploss below open rate

        # Calculate the stoploss ratio relative to the current rate
        if trade.is_short:
            stoploss_ratio = (stoploss_price - current_rate) / current_rate  # Short: stoploss above current rate
        else:
            stoploss_ratio = (current_rate - stoploss_price) / current_rate  # Long: stoploss below current rate

        # Adjust the stoploss ratio based on leverage
        stoploss_ratio = -stoploss_ratio * trade.leverage
        stoploss_int = self.stoploss * trade.leverage
        # Ensure the stoploss ratio does not exceed the strategy's default stoploss
        stoploss_ratio = max(stoploss_ratio, stoploss_int)
        return stoploss_ratio
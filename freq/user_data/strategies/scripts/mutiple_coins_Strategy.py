from freqtrade.strategy import IStrategy, informative
from pandas import DataFrame
import talib.abstract as ta
import numpy as np


class MultiTimeframeTEMAAgreement(IStrategy):
    """
    Multi-Timeframe TEMA Strategy with Trend Agreement using Informative Pairs.
    """
    # Define the main timeframe
    timeframe = '1m'
    can_short = True  # Enable shorting
    stoploss = -0.01  # Default stoploss
    use_custom_stoploss = True  # Enable custom stoploss logic
    startup_candle_count = 50  # Minimum candles for TEMA calculation

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

    def custom_stoploss(self, pair: str, trade, current_time, current_rate, current_profit, **kwargs) -> float:
        """
        Custom stoploss logic can be added here if needed.
        """
        # Example: Use a fixed percentage-based trailing stoploss
        return -0.01  # Default fixed stoploss


# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
# --- Do not remove these libs ---
import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional, Union

from freqtrade.strategy import (BooleanParameter, CategoricalParameter, DecimalParameter,
                                IntParameter, IStrategy, merge_informative_pair)

# --------------------------------
# Add your lib to import here
import talib.abstract as ta
import pandas_ta as pta
from technical import qtpylib

class LongReversalStrategy(IStrategy):

    INTERFACE_VERSION = 3

    timeframe = '3m'

    # Enable short trading capability
    can_short: bool = True

    # Minimal ROI configuration for the strategy, adjusted per minute
    minimal_roi = {
        "60": 10000  # Placeholder for significant ROI value
    }

    # Stoploss configuration to minimize loss
    stoploss = -0.002  # 0.1% stoploss

    # Enable trailing stop functionality
    trailing_stop = True

    # Number of startup candles before producing signals
    startup_candle_count: int = 50

    def informative_pairs(self):
        # This method returns pairs for informative data, currently empty
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Add all necessary technical indicators to the DataFrame.

        :param dataframe: DataFrame containing the OHLCV data
        :param metadata: Additional information like the currently traded pair
        :return: DataFrame with indicators populated
        """
        # Calculate the Triple Exponential Moving Average (TEMA)
        tema_period = 50
        dataframe['tema'] = ta.TEMA(dataframe['close'], timeperiod=tema_period)

        # Determine the trend direction (UP, DOWN)
        dataframe['trend'] = np.where(dataframe['tema'] > dataframe['tema'].shift(1), 'UP', 'DOWN')

        # Count duration of current trend
        dataframe['trend_duration'] = (dataframe['trend'] != dataframe['trend'].shift(1)).cumsum()
        dataframe['trend_count'] = dataframe.groupby('trend_duration').cumcount() + 1

        # for debugging
        # dataframe[dataframe['trend_count']]
        # dataframe[dataframe['trend_duration']]
        # only output column trend duration and basic fisrt 4 columns
        # dataframe[['trend_duration', 'open', 'high', 'low', 'close']]
        # dataframe['trend_duration']

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the entry signal for the given dataframe.

        :param dataframe: DataFrame containing the OHLCV data
        :param metadata: Additional information like the currently traded pair
        :return: DataFrame with entry columns populated
        """
        # Long entry signal: trend reversal from DOWN to UP, previous DOWN trend lasted more than 20 periods
        dataframe.loc[
            (
                (dataframe['trend'] == 'UP') &  # Current trend is UP
                (dataframe['trend'].shift(1) == 'DOWN') &  # Previous trend was DOWN
                (dataframe['trend_count'].shift(1) >= 20)  # Previous DOWN trend lasted more than 20 periods
            ),
            'enter_long'] = 1

        # Short entry signal: trend reversal from UP to DOWN, previous UP trend lasted more than 20 periods
        dataframe.loc[
            (
                (dataframe['trend'] == 'DOWN') &  # Current trend is DOWN
                (dataframe['trend'].shift(1) == 'UP') &  # Previous trend was UP
                (dataframe['trend_count'].shift(1) >= 20)  # Previous UP trend lasted more than 20 periods
            ),
            'enter_short'] = 1

        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the exit signal for the given dataframe.

        :param dataframe: DataFrame containing the OHLCV data
        :param metadata: Additional information like the currently traded pair
        :return: DataFrame with exit columns populated
        """

        return dataframe

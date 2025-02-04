# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file

# --- Standard Library Imports ---
from datetime import datetime
from typing import Optional, Union

# --- Third Party Imports ---
import numpy as np
import pandas as pd
from pandas import DataFrame
import random

# --- Freqtrade Imports ---
from freqtrade.strategy import (
    IStrategy,
    IntParameter
)

# --- Technical Analysis Library Imports ---
import talib.abstract as ta

# --- Custom Strategy Class ---
class TrendReversalLabelingStrategy_Prod(IStrategy):
    """
    Strategy for labeling trend reversals in trading data for machine learning tasks.
    """
    INTERFACE_VERSION = 3
    timeframe = '1m'
    can_short: bool = True
    minimal_roi = {"60": 10000}
    stoploss = -0.003*125  # 0.3% stoploss
    # stoploss = max(-0.005, -ATR_value * factor)  # ATR-based stop-loss
    trailing_stop = True
    startup_candle_count: int = 150

    def informative_pairs(self):
        """
        Define pairs for additional, informative data.
        Currently returns an empty list.
        """
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Add all necessary technical indicators to the DataFrame.
        Currently includes Triple Exponential Moving Average (TEMA).
        """
        tema_period = 50
        dataframe['tema'] = ta.TEMA(dataframe['close'], timeperiod=tema_period)
        dataframe['trend'] = np.where(dataframe['tema'] > dataframe['tema'].shift(1), 'UP', 'DOWN')
        dataframe['trend_duration'] = (dataframe['trend'] != dataframe['trend'].shift(1)).cumsum()
        dataframe['trend_count'] = dataframe.groupby('trend_duration').cumcount() + 1
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate the entry signals based on trend reversal logic.
        Signals for long and short entries based on trend direction changes.
        """
        random_series = dataframe.apply(lambda x: random.choice([0, 1]), axis=1)

        # Apply long entry conditions and random choice
        long_conditions = (dataframe['trend'] == 'UP') & (dataframe['trend'].shift(1) == 'DOWN') & (random_series == 1)
        dataframe.loc[long_conditions, 'enter_long'] = 1

        # Short entry signals remain deterministic
        short_conditions = (dataframe['trend'] == 'DOWN') & (dataframe['trend'].shift(1) == 'UP') &(random_series == 1)

        dataframe.loc[short_conditions, 'enter_short'] = 1

        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate the exit signals for the strategy.
        This method is left empty for further customization.
        """
        return dataframe

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str],
                 side: str, **kwargs) -> float:
        return max_leverage
        # return 100.0

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                            proposed_stake: float, min_stake: float | None, max_stake: float,
                            leverage: float, entry_tag: str | None, side: str,
                            **kwargs) -> float:

        # Fetch the total balance in the stake currency
        # total_balance = self.wallets.get_total_balance(self.config['stake_currency'])
        total_balance = self.wallets.get_total_stake_amount()

        # Calculate 3/4 (75%) of the total balance
        stake_amount = total_balance * 0.75

        # Ensure the stake amount is within allowed limits
        return stake_amount

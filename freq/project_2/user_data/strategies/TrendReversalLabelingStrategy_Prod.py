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
import talib.abstract as ta

# --- Freqtrade Imports ---
from freqtrade.persistence import Trade
from freqtrade.strategy import (
    IStrategy,
    IntParameter,
    CategoricalParameter,
    DecimalParameter
)

# --- Custom Strategy Class ---
class TrendReversalLabelingStrategy_Prod(IStrategy):
    """
    Strategy for labeling trend reversals in trading data for machine learning tasks.
    """
    INTERFACE_VERSION = 3
    timeframe = '5s'
    can_short: bool = True
    
    # We use custom stoploss and exit logic - these are just placeholders
    minimal_roi = {"0": 100}  # Very high ROI means we rely on custom_exit
    stoploss = -0.99  # This is a placeholder, real stoploss is calculated dynamically
    trailing_stop = False
    use_custom_stoploss = True
    startup_candle_count: int = 50

    # ATR period parameter
    atr_period = 14

    def informative_pairs(self):
        """
        Define pairs for additional, informative data.
        Currently returns an empty list.
        """
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Add all necessary technical indicators to the DataFrame.
        Currently includes Triple Exponential Moving Average (TEMA) and ATR.
        """
        # TEMA indicator for trend direction
        tema_period = 50  # Increased for 5s timeframe to maintain similar time window
        dataframe['tema'] = ta.TEMA(dataframe['close'], timeperiod=tema_period)
        dataframe['trend'] = np.where(dataframe['tema'] > dataframe['tema'].shift(1), 'UP', 'DOWN')
        dataframe['trend_duration'] = (dataframe['trend'] != dataframe['trend'].shift(1)).cumsum()
        dataframe['trend_count'] = dataframe.groupby('trend_duration').cumcount() + 1
        
        # ATR calculation for stop loss and take profit
        dataframe['atr'] = ta.ATR(dataframe['high'], dataframe['low'], dataframe['close'], 
                                   timeperiod=self.atr_period)
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate the entry signals based on trend reversal logic.
        Signals for long and short entries based on trend direction changes.
        """
        # Apply long entry conditions
        long_conditions = (dataframe['trend'] == 'UP') & (dataframe['trend'].shift(1) == 'DOWN')
        dataframe.loc[long_conditions, 'enter_long'] = 1

        # Short entry signals
        short_conditions = (dataframe['trend'] == 'DOWN') & (dataframe['trend'].shift(1) == 'UP')
        dataframe.loc[short_conditions, 'enter_short'] = 1

        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate the exit signals for the strategy.
        This method is left empty as we use custom_stoploss and custom_exit for exits.
        """
        return dataframe
    
    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float, **kwargs) -> float:
        """
        Custom stoploss logic.
        
        Returns the stoploss percentage as a positive value between 0.0 and 1.0.
        0.01 would be a 1% loss.
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if dataframe is not None and len(dataframe) > 0:
            # Get current ATR value
            current_atr = dataframe['atr'].iloc[-1]
            
            # Calculate stoploss percentage based on entry price and ATR
            # 0.25 * ATR defines our risk (stoploss distance)
            atr_stoploss_distance = 0.25 * current_atr
            
            # Convert from absolute price distance to percentage
            stoploss_percent = atr_stoploss_distance / trade.open_rate
            
            return stoploss_percent
            
        # Default fallback (1% stoploss)
        return 0.01
    
    def custom_exit(self, pair: str, trade: Trade, current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs):
        """
        Custom exit logic for take profit based on 0.5 * ATR (2:1 reward:risk ratio).
        
        Returns exit tag (string) if exit should occur, or None otherwise.
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if dataframe is not None and len(dataframe) > 0:
            # Get current ATR value
            current_atr = dataframe['atr'].iloc[-1]
            
            # Calculate take profit distance (0.5 * ATR)
            atr_take_profit_distance = 0.5 * current_atr
            
            # Convert distance to percentage
            take_profit_percent = atr_take_profit_distance / trade.open_rate
            
            # Check if current profit exceeds our take profit level
            # This gives us 2:1 reward:risk (0.5 ATR vs 0.25 ATR)
            if current_profit >= take_profit_percent:
                return 'take_profit_atr'
                
        return None

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str],
                 side: str, **kwargs) -> float:
        """
        Return the leverage to use for a trade.
        """
        return max_leverage
        # return 100.0

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                            proposed_stake: float, min_stake: float | None, max_stake: float,
                            leverage: float, entry_tag: str | None, side: str,
                            **kwargs) -> float:
        """
        Custom stake amount logic - uses 75% of the total available balance.
        """
        # Fetch the total balance in the stake currency
        # total_balance = self.wallets.get_total_balance(self.config['stake_currency'])
        total_balance = self.wallets.get_total_stake_amount()

        # Calculate 3/4 (75%) of the total balance
        stake_amount = total_balance * 0.75

        # Ensure the stake amount is within allowed limits
        return stake_amount

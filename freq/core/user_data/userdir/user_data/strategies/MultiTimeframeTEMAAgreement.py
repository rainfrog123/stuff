from freqtrade.strategy import IStrategy, informative
from pandas import DataFrame
import talib.abstract as ta
import numpy as np
import logging
from datetime import datetime  # Add this line to import datetime
from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy, informative
from pandas import DataFrame
import talib.abstract as ta
import numpy as np
import logging
from typing import Optional


class MultiTimeframeTEMAAgreement(IStrategy):
    """
    Multi-Timeframe TEMA Strategy with Trend Agreement using Informative Pairs.
    """
    # Define the main timeframe
    timeframe = '1m'
    can_short = True  # Enable shorting
    stoploss = -0.95  # Default stoploss
    use_custom_stoploss = True  # Enable custom stoploss logic
    startup_candle_count = 300  # Minimum candles for TEMA calculation

    # TEMA configuration
    tema_period = 50

    # Methods for informative timeframes
    @informative('3m')
    def populate_indicators_3m(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['tema'] = ta.TEMA(dataframe['close'], timeperiod=self.tema_period)
        dataframe['trend'] = np.where(dataframe['tema'] > dataframe['tema'].shift(1), 1,
                                      np.where(dataframe['tema'] < dataframe['tema'].shift(1), -1, 0))
        return dataframe

    @informative('5m')
    def populate_indicators_5m(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['tema'] = ta.TEMA(dataframe['close'], timeperiod=self.tema_period)
        dataframe['trend'] = np.where(dataframe['tema'] > dataframe['tema'].shift(1), 1,
                                      np.where(dataframe['tema'] < dataframe['tema'].shift(1), -1, 0))
        return dataframe

    @informative('15m')
    def populate_indicators_15m(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['tema'] = ta.TEMA(dataframe['close'], timeperiod=self.tema_period)
        dataframe['trend'] = np.where(dataframe['tema'] > dataframe['tema'].shift(1), 1,
                                      np.where(dataframe['tema'] < dataframe['tema'].shift(1), -1, 0))
        return dataframe

    @informative('30m')
    def populate_indicators_30m(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['tema'] = ta.TEMA(dataframe['close'], timeperiod=self.tema_period)
        dataframe['trend'] = np.where(dataframe['tema'] > dataframe['tema'].shift(1), 1,
                                      np.where(dataframe['tema'] < dataframe['tema'].shift(1), -1, 0))
        return dataframe

    @informative('1h')
    def populate_indicators_1h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['tema'] = ta.TEMA(dataframe['close'], timeperiod=self.tema_period)
        dataframe['trend'] = np.where(dataframe['tema'] > dataframe['tema'].shift(1), 1,
                                      np.where(dataframe['tema'] < dataframe['tema'].shift(1), -1, 0))
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate indicators for the main timeframe.
        """
        dataframe['tema'] = ta.TEMA(dataframe['close'], timeperiod=self.tema_period)
        dataframe['trend'] = np.where(dataframe['tema'] > dataframe['tema'].shift(1), 1,
                                      np.where(dataframe['tema'] < dataframe['tema'].shift(1), -1, 0))

        # ATR Percentage Calculation
        dataframe['atr'] = ta.ATR(dataframe['high'], dataframe['low'], dataframe['close'], timeperiod=14)
        dataframe['atr_percentage'] = (dataframe['atr'] / dataframe['close']) * 100

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate entry signals based on multi-timeframe trend agreement.
        """
        dataframe['is_trend_aligned_up'] = (
            (dataframe['trend'] == 1) &
            (dataframe['trend'].shift(1) != 1) & 
            (dataframe['trend_3m'] == 1) &
            (dataframe['trend_5m'] == 1) &
            (dataframe['trend_15m'] == 1) &
            (dataframe['trend_30m'] == 1) &
            (dataframe['trend_1h'] == 1)
        )
        dataframe['is_trend_aligned_down'] = (
            (dataframe['trend'] == -1) &
            (dataframe['trend'].shift(1) != -1) & 
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

    def order_filled(self, pair: str, trade: Trade, order, current_time: datetime, **kwargs) -> None:
        """
        Calculate and store the ATR percentage as the stoploss percentage for this trade.
        Trigger this only for entry orders.
        """
        if (order.ft_order_side == trade.entry_side):
            # Get the analyzed dataframe for the pair
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            last_candle = dataframe.iloc[-1].squeeze()

            # Calculate ATR percentage and store it in the trade
            atr_percentage = last_candle.get('atr_percentage', None)
            if atr_percentage is not None:
                # Convert percentage to a ratio for stoploss (e.g., 0.17% => 0.0017)
                stoploss_ratio = (atr_percentage / 100.0) * trade.leverage

                # Store this value as a custom field in the trade
                trade.set_custom_data(key="stoploss_ratio", value=stoploss_ratio)
        return None


    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime, current_rate: float,
                        current_profit: float, **kwargs) -> float:
        """
        Custom stoploss logic using the pre-calculated ATR percentage.
        """
        # Retrieve the stored stoploss ratio from the trade's custom data
        stoploss_ratio = trade.get_custom_data("stoploss_ratio", default=None)

        if stoploss_ratio is not None:
            # Apply the stored stoploss ratio (negative value for stoploss)
            return (-stoploss_ratio * 1.5)  # Use a multiplier to adjust the stoploss

        # Fallback: Default stoploss
        return self.stoploss

    def leverage(self, pair: str, current_time: datetime, current_rate: float, proposed_leverage: float,
                 max_leverage: float, entry_tag: Optional[str], side: str, current_profit: Optional[float] = None,
                 **kwargs) -> float:



        return max_leverage


    # def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime, current_rate: float,
    #                     current_profit: float, **kwargs) -> float:
        
        # Extract the liquidation price and open rate from the trade
        # liquidation_price = trade.liquidation_price
        # open_rate = trade.open_rate

        # # Check for valid liquidation price and open rate
      

        # # Calculate the distance to the liquidation price
        # distance_to_liquidation = abs(open_rate - liquidation_price)

        # # Determine the stoploss price based on trade direction (long or short)
        # if trade.is_short:
        #     stoploss_price = open_rate + (distance_to_liquidation * 0.8)  # Short: stoploss above open rate
        # else:
        #     stoploss_price = open_rate - (distance_to_liquidation * 0.8)  # Long: stoploss below open rate

        # # Calculate the stoploss ratio relative to the current rate
        # if trade.is_short:
        #     stoploss_ratio = (stoploss_price - current_rate) / current_rate  # Short: stoploss above current rate
        # else:
        #     stoploss_ratio = (current_rate - stoploss_price) / current_rate  # Long: stoploss below current rate

        # # Adjust the stoploss ratio based on leverage
        # stoploss_ratio = -stoploss_ratio * trade.leverage
        # stoploss_int = self.stoploss * trade.leverage
        # # Ensure the stoploss ratio does not exceed the strategy's default stoploss
        # stoploss_ratio = max(stoploss_ratio, stoploss_int)
        # return stoploss_ratio
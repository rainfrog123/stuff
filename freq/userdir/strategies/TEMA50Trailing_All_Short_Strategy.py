from technical.indicators import atr
import talib.abstract as ta
import numpy as np
from freqtrade.strategy import IStrategy, stoploss_from_absolute
from freqtrade.persistence import Trade
from pandas import DataFrame
from datetime import datetime


class TEMA50Trailing_All_Short_Strategy(IStrategy):
    """
    A strategy that enters trades when TEMA50 changes direction
    and uses ATR-based trailing stops to manage exits.
    """
    timeframe = '3m'  # Use 3-minute candles (can be adjusted as needed)
    can_short: bool = True  # Allow short trades
    stoploss = -0.91  # Placeholder value, the custom trailing stop logic will override this
    use_custom_stoploss = True  # Enable custom stoploss logic
    startup_candle_count: int = 150  # Require at least 50 candles for TEMA50 calculation

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate all necessary indicators for this strategy.
        """
        # Calculate TEMA50
        tema_period = 50
        dataframe['tema50'] = ta.TEMA(dataframe['close'], timeperiod=tema_period)

        # Detect TEMA direction changes
        dataframe['tema_direction'] = np.where(dataframe['tema50'] > dataframe['tema50'].shift(1), 'UP', 'DOWN')
        dataframe['tema_changed'] = dataframe['tema_direction'] != dataframe['tema_direction'].shift(1)

        # Compute ATR for trailing stop
        atr_period = 14
        dataframe['atr'] = atr(dataframe, atr_period)

        # Calculate ATR percentage
        dataframe['atr_percentage'] = (dataframe['atr'] / dataframe['close']) * 100

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate entry signals for both long and short trades.
        """
        # Long entry: TEMA50 changes direction to UP
        dataframe.loc[
            dataframe['tema_changed'] & (dataframe['tema_direction'] == 'UP'),
            ['enter_short', 'enter_tag']
        ] = (1, 'tema50_up')

        # Short entry: TEMA50 changes direction to DOWN
        dataframe.loc[
            dataframe['tema_changed'] & (dataframe['tema_direction'] == 'DOWN'),
            ['enter_short', 'enter_tag']
        ] = (1, 'tema50_down')

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Exit logic is handled entirely by the trailing stop.
        """
        return dataframe

    def order_filled(self, pair: str, trade: Trade, order, current_time: datetime, **kwargs) -> None:
        """
        Calculate and store the ATR percentage as the stoploss percentage for this trade.
        """
        # Get the analyzed dataframe for the pair
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()

        atr_percentage = last_candle.get('atr_percentage', None)
        if atr_percentage is not None:
            # Convert percentage to a ratio for stoploss (e.g., 0.17% => 0.0017)
            stoploss_ratio = atr_percentage / 100.0 

            # Store this value as a custom field in the trade
            trade.set_custom_data(key="stoploss_ratio", value=stoploss_ratio)

    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime, current_rate: float,
                        current_profit: float, **kwargs) -> float:
        """
        Custom stoploss logic using the pre-calculated ATR percentage.
        """
        # Retrieve the stored stoploss ratio from the trade's custom data
        stoploss_ratio = trade.get_custom_data("stoploss_ratio", default=None)

        if stoploss_ratio is not None:
            # Apply the stored stoploss ratio (negative value for stoploss)
            return -stoploss_ratio*3  # Use a multiplier to adjust the stoploss

        # Fallback: Default stoploss
        return self.stoploss

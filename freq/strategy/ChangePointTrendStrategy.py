from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta
import numpy as np

class ChangePointTrendStrategy(IStrategy):
    """
    ChangePointTrendStrategy
    This strategy buys at a change point where the trend turns UP and sells when it turns DOWN.
    """

    # Define the stoploss for the strategy
    stoploss = -0.1

    # Optimal timeframe for the strategy
    timeframe = '15m'

    # Trailing stop
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.05
    trailing_only_offset_is_reached = True

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Calculate the Triple Exponential Moving Average (TEMA)
        dataframe['tema'] = ta.TEMA(dataframe, timeperiod=50)

        # Determine trend based on TEMA
        dataframe['trend'] = np.where(dataframe['tema'] > dataframe['tema'].shift(1), 'UP',
                                      np.where(dataframe['tema'] < dataframe['tema'].shift(1), 'DOWN', 'STABLE'))

        # Identify trend changes
        dataframe['trend_change'] = dataframe['trend'] != dataframe['trend'].shift(1)
        dataframe['trend_change_point'] = dataframe['trend_change'] & (dataframe['trend'] != 'STABLE')

        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Buy when the trend change point is UP
        dataframe.loc[
            (
                (dataframe['trend_change_point']) &
                (dataframe['trend'] == 'UP')
            ),
            'buy'] = 1
        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Sell when the trend change point is DOWN
        dataframe.loc[
            (
                (dataframe['trend_change_point']) &
                (dataframe['trend'] == 'DOWN')
            ),
            'sell'] = 1
        return dataframe

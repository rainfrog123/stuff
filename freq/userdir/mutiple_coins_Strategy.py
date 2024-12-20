from freqtrade.strategy import IStrategy, merge_informative_pair
from pandas import DataFrame
import numpy as np
import talib.abstract as ta


class MultiTimeframeTEMAAgreement(IStrategy):
    """
    Multi-Timeframe TEMA Strategy with Trend Agreement using Informative Pairs.
    """
    # Define timeframes
    timeframe = '1m'  # Base timeframe
    informative_timeframes = ['3m', '5m', '15m', '30m', '1h']  # Additional timeframes
    can_short = True  # Enable shorting
    stoploss = -0.01  # Default stoploss (will be overridden by custom stoploss)
    use_custom_stoploss = True  # Enable custom stoploss logic
    startup_candle_count = 50  # Minimum candles for TEMA calculation

    # TEMA configuration
    tema_period = 50

    def informative_pairs(self):
        """
        Define informative pairs for different timeframes.
        """
        pairs = self.dp.current_whitelist()  # Get the current whitelist
        return [(pair, tf) for pair in pairs for tf in self.informative_timeframes]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate indicators for the main timeframe and merge with informative pairs.
        """
        # Base timeframe TEMA calculation
        dataframe['tema'] = ta.TEMA(dataframe['close'], timeperiod=self.tema_period)
        dataframe['trend'] = np.where(dataframe['tema'] > dataframe['tema'].shift(1), 1,
                                      np.where(dataframe['tema'] < dataframe['tema'].shift(1), -1, 0))

        # Merge informative timeframes
        for tf in self.informative_timeframes:
            inf_df = self.dp.get_pair_dataframe(metadata['pair'], tf)
            inf_df['tema'] = ta.TEMA(inf_df['close'], timeperiod=self.tema_period)
            inf_df['trend'] = np.where(inf_df['tema'] > inf_df['tema'].shift(1), 1,
                                       np.where(inf_df['tema'] < inf_df['tema'].shift(1), -1, 0))

            # Merge the informative dataframe into the base timeframe
            dataframe = merge_informative_pair(dataframe, inf_df, self.timeframe, tf, ffill=True)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate entry signals based on multi-timeframe trend agreement.
        """
        # Check if all trends align for an UP signal
        up_trend_conditions = [
            (dataframe['trend'] == 1),  # Base timeframe trend
            (dataframe['trend_3m'] == 1),  # 3-minute timeframe
            (dataframe['trend_5m'] == 1),  # 5-minute timeframe
            (dataframe['trend_15m'] == 1),  # 15-minute timeframe
            (dataframe['trend_30m'] == 1),  # 30-minute timeframe
            (dataframe['trend_1h'] == 1)  # 1-hour timeframe
        ]
        dataframe['is_trend_aligned_up'] = np.all(up_trend_conditions, axis=0)

        # Check if all trends align for a DOWN signal
        down_trend_conditions = [
            (dataframe['trend'] == -1),
            (dataframe['trend_3m'] == -1),
            (dataframe['trend_5m'] == -1),
            (dataframe['trend_15m'] == -1),
            (dataframe['trend_30m'] == -1),
            (dataframe['trend_1h'] == -1)
        ]
        dataframe['is_trend_aligned_down'] = np.all(down_trend_conditions, axis=0)

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
        return 0.002

    def order_filled(self, pair: str, trade, order, current_time, **kwargs) -> None:
        """
        Handle order filled logic.
        """
        # Example: Print trade details to the console
        self.log(f"Trade filled: {trade}")

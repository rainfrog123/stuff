from technical.indicators import atr
import talib.abstract as ta
import numpy as np
from freqtrade.strategy import IStrategy
from pandas import DataFrame


class TEMA50TrailingStopStrategy(IStrategy):
    """
    A strategy that enters trades when TEMA50 changes direction
    and uses ATR-based trailing stops to manage exits.
    """
    timeframe = '1m'  # Use 5-minute candles (can be adjusted as needed)
    can_short: bool = True  # Allow short trades
    stoploss = -0.10  # Placeholder value, the custom trailing stop logic will override this
    use_custom_stoploss = True  # Enable custom stoploss logic
    startup_candle_count: int = 50  # Require at least 50 candles for TEMA50 calculation

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
        dataframe['atr'] = atr(dataframe, period=atr_period)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate entry signals for both long and short trades.
        """
        # Long entry: TEMA50 changes direction to UP
        dataframe.loc[
            dataframe['tema_changed'] & (dataframe['tema_direction'] == 'UP'),
            'enter_long'
        ] = 1

        # Short entry: TEMA50 changes direction to DOWN
        dataframe.loc[
            dataframe['tema_changed'] & (dataframe['tema_direction'] == 'DOWN'),
            'enter_short'
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Exit logic is handled entirely by the trailing stop.
        """
        return dataframe

    def custom_stoploss(
        self, pair: str, trade, current_time: datetime, current_rate: float, current_profit: float, **kwargs
    ) -> float:
        """
        Custom stoploss logic using ATR.
        """
        # Fetch analyzed dataframe
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)

        # Ensure dataframe is not empty and ATR is available
        if dataframe.empty or 'atr' not in dataframe:
            return self.stoploss

        # Get the last candle
        last_candle = dataframe.iloc[-1]

        # ATR-based trailing stop calculation
        atr_multiplier = 1.5  # Adjust this multiplier as needed
        atr_trailing_stop = atr_multiplier * last_candle['atr'] / current_rate

        # Ensure trailing stop is within bounds (optional tightening logic)
        if current_profit > 0.02:  # If profit exceeds 2%, tighten the stop
            atr_trailing_stop = max(atr_trailing_stop, -0.02)

        return atr_trailing_stop


def leverage():
    return 1.0
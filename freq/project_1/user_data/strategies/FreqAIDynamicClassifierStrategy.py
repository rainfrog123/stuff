import logging
from functools import reduce
import talib.abstract as ta
from pandas import DataFrame
from technical import qtpylib
from freqtrade.strategy import IStrategy
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

class FreqAIDynamicClassifierStrategy(IStrategy):
    """
    A strategy utilizing AI-based classification for dynamic long and short entry/exit decisions.
    """
    
    # Strategy-specific configurations
    minimal_roi = {"0": 1000000.0}
    stoploss = -0.05
    trailing_stop = True
    process_only_new_candles = False
    startup_candle_count: int = 200
    can_short = True
    timeframe = '1m'
    # Plot configuration
    plot_config = {
        "main_plot": {}
    }

    def feature_engineering_expand_all(self, dataframe: DataFrame, period: int, metadata: dict, **kwargs) -> DataFrame:
        """
        *Only functional with FreqAI enabled strategies*
        This function will automatically expand the defined features on the config defined
        `indicator_periods_candles`, `include_timeframes`, `include_shifted_candles`, and
        `include_corr_pairs`.
        """
        dataframe["%-rsi-period"] = ta.RSI(dataframe, timeperiod=period)
        dataframe["%-mfi-period"] = ta.MFI(dataframe, timeperiod=period)
        dataframe["%-adx-period"] = ta.ADX(dataframe, timeperiod=period)
        dataframe["%-sma-period"] = ta.SMA(dataframe, timeperiod=period)
        dataframe["%-ema-period"] = ta.EMA(dataframe, timeperiod=period)

        bollinger = qtpylib.bollinger_bands(
            qtpylib.typical_price(dataframe), window=period, stds=2.2
        )
        dataframe["bb_lowerband-period"] = bollinger["lower"]
        dataframe["bb_middleband-period"] = bollinger["mid"]
        dataframe["bb_upperband-period"] = bollinger["upper"]

        dataframe["%-bb_width-period"] = (
            dataframe["bb_upperband-period"]
            - dataframe["bb_lowerband-period"]
        ) / dataframe["bb_middleband-period"]
        dataframe["%-close-bb_lower-period"] = (
            dataframe["close"] / dataframe["bb_lowerband-period"]
        )

        dataframe["%-roc-period"] = ta.ROC(dataframe, timeperiod=period)
        dataframe["%-relative_volume-period"] = (
            dataframe["volume"] / dataframe["volume"].rolling(period).mean()
        )

        return dataframe

    def feature_engineering_expand_basic(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        """
        *Only functional with FreqAI enabled strategies*
        This function will automatically expand the defined features on the config defined
        `include_timeframes`, `include_shifted_candles`, and `include_corr_pairs`.
        """
        dataframe["%-pct-change"] = dataframe["close"].pct_change()
        dataframe["%-raw_volume"] = dataframe["volume"]
        dataframe["%-raw_price"] = dataframe["close"]
        return dataframe

    def feature_engineering_standard(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        """
        *Only functional with FreqAI enabled strategies*
        Final function to be called for feature engineering.
        """
        dataframe["%-day_of_week"] = (dataframe["date"].dt.dayofweek + 1) / 7
        dataframe["%-hour_of_day"] = (dataframe["date"].dt.hour + 1) / 25
        return dataframe

    def set_freqai_targets(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Map external targets from a parquet file to the main dataframe.
        """
        self.freqai.class_names = ['WIN', 'LOSE']
        
        # Load external parquet file
        external_df = pd.read_parquet('/allah/data/parquet/filtered_df.parquet')

        # Ensure `open_date` is a datetime object
        external_df['open_date'] = pd.to_datetime(external_df['open_date'])
        
        # Create `target_date` as 3 minutes before `open_date`
        external_df['target_date'] = external_df['open_date'] - pd.Timedelta(minutes=1)
        
        # Filter for only LONG_WIN and SHORT_WIN
        # external_df = external_df[external_df['type'].isin(['LONG_WIN', 'SHORT_WIN'])]

        # Map targets to the main dataframe
        target_map = external_df.set_index('target_date')['profitability'].to_dict()
        dataframe['profitability'] = dataframe['date'].map(target_map)
        dataframe['&-target'] = dataframe['profitability']
        
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate indicators for the AI-based prediction.
        """
        dataframe = self.freqai.start(dataframe, metadata, self)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Define entry conditions for long and short positions based on AI predictions.
        """
 
        # Long entry conditions (when prediction is 'LONG_WIN')
        enter_long_conditions = [
            dataframe["do_predict"] == 1,  # Prediction confidence is high
            dataframe["&-target"] == 'LONG_WIN',  # Predicted to win in a long position
        ]
        if enter_long_conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, enter_long_conditions), ["enter_long", "enter_tag"]
            ] = (1, "long")

        # Short entry conditions (when prediction is 'SHORT_WIN')
        enter_short_conditions = [
            dataframe["do_predict"] == 1,  # Prediction confidence is high
            dataframe["&-target"] == 'SHORT_WIN',  # Predicted to win in a short position
        ]
        if enter_short_conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, enter_short_conditions), ["enter_short", "enter_tag"]
            ] = (1, "short")

        return dataframe


    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Define exit conditions for long and short positions based on AI predictions.
        """
        # Exit long if prediction changes to "down"

        return dataframe
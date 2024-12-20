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
    stoploss = -0.005
    trailing_stop = True
    process_only_new_candles = True
    use_exit_signal = True
    startup_candle_count: int = 40
    can_short = True

    # Plot configuration
    plot_config = {
        "main_plot": {}
        # Example: Uncomment and customize subplots as needed
        # "subplots": {
        #     "&-class": {"&-class": {"color": "blue"}},
        #     "do_predict": {"do_predict": {"color": "brown"}},
        # },
    }

    def feature_engineering_expand_all(self, dataframe: DataFrame, period: int, metadata: dict, **kwargs) -> DataFrame:
        """
        Expand dataframe with advanced TA-based features.
        """
        dataframe["%-rsi-period"] = ta.RSI(dataframe, timeperiod=period)
        dataframe["%-mfi-period"] = ta.MFI(dataframe, timeperiod=period)
        dataframe["%-adx-period"] = ta.ADX(dataframe, timeperiod=period)
        dataframe["%-sma-period"] = ta.SMA(dataframe, timeperiod=period)
        dataframe["%-ema-period"] = ta.EMA(dataframe, timeperiod=period)

        # Bollinger Bands
        bollinger = qtpylib.bollinger_bands(
            qtpylib.typical_price(dataframe), window=period, stds=2.2
        )
        dataframe["bb_lowerband-period"] = bollinger["lower"]
        dataframe["bb_middleband-period"] = bollinger["mid"]
        dataframe["bb_upperband-period"] = bollinger["upper"]
        dataframe["%-bb_width-period"] = (
            dataframe["bb_upperband-period"] - dataframe["bb_lowerband-period"]
        ) / dataframe["bb_middleband-period"]
        dataframe["%-close-bb_lower-period"] = dataframe["close"] / dataframe["bb_lowerband-period"]

        # Rate of Change and Relative Volume
        dataframe["%-roc-period"] = ta.ROC(dataframe, timeperiod=period)
        dataframe["%-relative_volume-period"] = (
            dataframe["volume"] / dataframe["volume"].rolling(period).mean()
        )
        return dataframe

    def feature_engineering_expand_basic(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        """
        Add basic features to the dataframe.
        """
        dataframe["%-pct-change"] = dataframe["close"].pct_change()
        dataframe["%-raw_volume"] = dataframe["volume"]
        dataframe["%-raw_price"] = dataframe["close"]
        return dataframe

    def feature_engineering_standard(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        """
        Add standard features such as time-related attributes.
        """
        dataframe["%-day_of_week"] = dataframe["date"].dt.dayofweek
        dataframe["%-hour_of_day"] = dataframe["date"].dt.hour
        return dataframe

    def set_freqai_targets(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Map external targets from a parquet file to the main dataframe.
        """
        self.freqai.class_names = ['LOSE', 'LONG_WIN', 'SHORT_WIN']
        df = pd.read_parquet("/allah/data/parquet/final_df.parquet")
        df['target_date'] = pd.to_datetime(df['target_date'])
        dataframe['date'] = pd.to_datetime(dataframe['date'])

        # Map targets to the dataframe
        target_map = df.set_index('target_date')['type'].to_dict()
        dataframe['type'] = dataframe['date'].map(target_map)
        dataframe['&-target'] = dataframe['type']
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate indicators for the AI-based prediction.
        """
        dataframe = self.freqai.start(dataframe, metadata, self)
        return dataframe

    def populate_entry_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        """
        Define entry conditions for long and short positions based on AI predictions.
        """
 
    # Long entry conditions (when prediction is 'LONG_WIN')
        enter_long_conditions = [
            df["do_predict"] == 1,  # Prediction confidence is high
            df["&-target"] == 'LONG_WIN',  # Predicted to win in a long position
        ]
        if enter_long_conditions:
            df.loc[
                reduce(lambda x, y: x & y, enter_long_conditions), ["enter_long", "enter_tag"]
            ] = (1, "long")

        # Short entry conditions (when prediction is 'SHORT_WIN')
        enter_short_conditions = [
            df["do_predict"] == 1,  # Prediction confidence is high
            df["&-target"] == 'SHORT_WIN',  # Predicted to win in a short position
        ]
        if enter_short_conditions:
            df.loc[
                reduce(lambda x, y: x & y, enter_short_conditions), ["enter_short", "enter_tag"]
            ] = (1, "short")

        return df


    def populate_exit_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        """
        Define exit conditions for long and short positions based on AI predictions.
        """
        # Exit long if prediction changes to "down"

        return df

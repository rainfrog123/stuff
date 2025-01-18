import logging
from functools import reduce

import talib.abstract as ta
from pandas import DataFrame
from technical import qtpylib
from freqtrade.strategy import IStrategy
import numpy as np

logger = logging.getLogger(__name__)

class freqai_opaq_classifier(IStrategy):
    minimal_roi = {"0": 1000000.0}
    plot_config = {
        "main_plot": {}
        # "subplots": {
        #     "&-class": {"&-class": {"color": "blue"}},
        #     "do_predict": {"do_predict": {"color": "brown"}},
        # },
    }
    process_only_new_candles = True
    use_exit_signal = True
    startup_candle_count: int = 40
    can_short = True

    stoploss = -0.005
    trailing_stop = True
    # trailing_stop_positive = 0.005

    def feature_engineering_expand_all(
        self, dataframe: DataFrame, period: int, metadata: dict, **kwargs
    ) -> DataFrame:
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
            dataframe["bb_upperband-period"] - dataframe["bb_lowerband-period"]
        ) / dataframe["bb_middleband-period"]
        dataframe["%-close-bb_lower-period"] = dataframe["close"] / dataframe["bb_lowerband-period"]

        dataframe["%-roc-period"] = ta.ROC(dataframe, timeperiod=period)
        dataframe["%-relative_volume-period"] = (
            dataframe["volume"] / dataframe["volume"].rolling(period).mean()
        )
        return dataframe

    def feature_engineering_expand_basic(
        self, dataframe: DataFrame, metadata: dict, **kwargs
    ) -> DataFrame:
        dataframe["%-pct-change"] = dataframe["close"].pct_change()
        dataframe["%-raw_volume"] = dataframe["volume"]
        dataframe["%-raw_price"] = dataframe["close"]
        return dataframe

    def feature_engineering_standard(
        self, dataframe: DataFrame, metadata: dict, **kwargs
    ) -> DataFrame:
        dataframe["%-day_of_week"] = dataframe["date"].dt.dayofweek
        dataframe["%-hour_of_day"] = dataframe["date"].dt.hour
        return dataframe

    def set_freqai_targets(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        # Set classification target: "up" or "down/same"
        self.freqai.class_names = ["down", "up"]
        future_price = dataframe["close"].shift(-self.freqai_info["feature_parameters"]["label_period_candles"])
        dataframe["&-class"] = np.where(future_price > dataframe["close"], "up", "down")

        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = self.freqai.start(dataframe, metadata, self)
        return dataframe

    def populate_entry_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        enter_long_conditions = [
            df["do_predict"] == 1,
            df["&-class"] == 'up',  # class 1 means up (predicted price increase)
        ]

        if enter_long_conditions:
            df.loc[
                reduce(lambda x, y: x & y, enter_long_conditions), ["enter_long", "enter_tag"]
            ] = (1, "long")

        enter_short_conditions = [
            df["do_predict"] == 1,
            df["&-class"] == 'down',  # class 0 means down (predicted price decrease)
        ]

        if enter_short_conditions:
            df.loc[
                reduce(lambda x, y: x & y, enter_short_conditions), ["enter_short", "enter_tag"]
            ] = (1, "short")

        return df

    def populate_exit_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
    # Exit long position if the prediction changes to "down"
        exit_long_conditions = [
            df["do_predict"] == 1,
            df["&-class"] == 'down'  # Exit long if prediction is "down"
        ]
        if exit_long_conditions:
            df.loc[reduce(lambda x, y: x & y, exit_long_conditions), "exit_long"] = 1

        # Exit short position if the prediction changes to "up"
        exit_short_conditions = [
            df["do_predict"] == 1,
            df["&-class"] == 'up'  # Exit short if prediction is "up"
        ]
        if exit_short_conditions:
            df.loc[reduce(lambda x, y: x & y, exit_short_conditions), "exit_short"] = 1

        return df

        # exit_long_conditions = [df["do_predict"] == 1, df["&-class"] == 0]
        # if exit_long_conditions:
        #     df.loc[reduce(lambda x, y: x & y, exit_long_conditions), "exit_long"] = 1

        # exit_short_conditions = [df["do_predict"] == 1, df["&-class"] == 1]
        # if exit_short_conditions:
        #     df.loc[reduce(lambda x, y: x & y, exit_short_conditions), "exit_short"] = 1

        return df

    # def confirm_trade_entry(
    #     self,
    #     pair: str,
    #     order_type: str,
    #     amount: float,
    #     rate: float,
    #     time_in_force: str,
    #     current_time,
    #     entry_tag,
    #     side: str,
    #     **kwargs,
    # ) -> bool:
    #     df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
    #     last_candle = df.iloc[-1].squeeze()

    #     if side == "long":
    #         if rate > (last_candle["close"] * (1 + 0.0025)):
    #             return False
    #     else:
    #         if rate < (last_candle["close"] * (1 - 0.0025)):
    #             return False

    #     return True

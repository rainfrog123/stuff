from freqtrade.strategy import IStrategy, informative
from pandas import DataFrame
from datetime import datetime
import talib.abstract as ta
import numpy as np
import logging

logger = logging.getLogger(__name__)

class Gamble(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '5s'
    can_short: bool = True
    process_only_new_candles = True
    minimal_roi = {"0": 0.06, "10": 0.03, "30": 0}
    stoploss = -0.03
    trailing_stop = False
    use_custom_stoploss = True
    startup_candle_count: int = 60

    tema_length = 50
    atr_length = 14
    atr_multiplier = 3.0
    tp_risk_ratio = 2.0

    def informative_pairs(self):
        return []

    @informative('1m')
    def populate_indicators_1m(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=self.atr_length)
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        ema1 = ta.EMA(dataframe['close'], timeperiod=self.tema_length)
        ema2 = ta.EMA(ema1, timeperiod=self.tema_length)
        ema3 = ta.EMA(ema2, timeperiod=self.tema_length)
        dataframe['tema'] = 3 * ema1 - 3 * ema2 + ema3
        
        dataframe['tema_prev'] = dataframe['tema'].shift(1)
        dataframe['trend_up'] = dataframe['tema'] > dataframe['tema_prev']
        dataframe['trend_down'] = dataframe['tema'] < dataframe['tema_prev']
        dataframe['trend'] = np.where(
            dataframe['trend_up'], 'UP',
            np.where(dataframe['trend_down'], 'DOWN', 'FLAT')
        )
        
        dataframe['trend_prev'] = dataframe['trend'].shift(1)
        dataframe['trend_flip'] = (dataframe['trend'] != dataframe['trend_prev']) & (dataframe['trend'] != 'FLAT')
        dataframe['atr'] = dataframe['atr_1m']
        dataframe['entry_price'] = dataframe['close']
        dataframe['risk'] = dataframe['atr'] * self.atr_multiplier
        
        dataframe['tp_long'] = np.where(
            dataframe['trend'] == 'UP',
            dataframe['entry_price'] + (self.tp_risk_ratio * dataframe['risk']),
            np.nan
        )
        dataframe['sl_long'] = np.where(
            dataframe['trend'] == 'UP',
            dataframe['entry_price'] - dataframe['risk'],
            np.nan
        )
        dataframe['tp_short'] = np.where(
            dataframe['trend'] == 'DOWN',
            dataframe['entry_price'] - (self.tp_risk_ratio * dataframe['risk']),
            np.nan
        )
        dataframe['sl_short'] = np.where(
            dataframe['trend'] == 'DOWN',
            dataframe['entry_price'] + dataframe['risk'],
            np.nan
        )
        
        dataframe['reversal_to_up'] = (dataframe['trend_flip']) & (dataframe['trend'] == 'UP')
        dataframe['reversal_to_down'] = (dataframe['trend_flip']) & (dataframe['trend'] == 'DOWN')
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['random_entry'] = np.random.random(len(dataframe)) < 0.1
        
        dataframe.loc[
            (dataframe['reversal_to_up'] == True) &
            (~dataframe['atr'].isna()) &
            (dataframe['atr'] > 0) &
            (~dataframe['tema'].isna()) &
            (dataframe['random_entry'] == True),
            'enter_long'
        ] = 1

        dataframe.loc[
            (dataframe['reversal_to_down'] == True) &
            (~dataframe['atr'].isna()) &
            (dataframe['atr'] > 0) &
            (~dataframe['tema'].isna()) &
            (dataframe['random_entry'] == True),
            'enter_short'
        ] = 1
        
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['exit_long'] = 0
        dataframe['exit_short'] = 0
        return dataframe

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime,
                       current_rate: float, current_profit: float, **kwargs) -> float:
        try:
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            if dataframe is None or dataframe.empty:
                return self.stoploss
            
            entry_price = trade.open_rate
            latest_atr = dataframe['atr'].iloc[-1]
            if pd.isna(latest_atr) or latest_atr <= 0:
                return self.stoploss
            
            risk_amount = latest_atr * self.atr_multiplier
            
            if trade.is_short:
                sl_price = entry_price + risk_amount
                tp_price = entry_price - (self.tp_risk_ratio * risk_amount)
                if current_rate <= tp_price:
                    return 1
                sl_percentage = (sl_price - entry_price) / entry_price
            else:
                sl_price = entry_price - risk_amount
                tp_price = entry_price + (self.tp_risk_ratio * risk_amount)
                if current_rate >= tp_price:
                    return 1
                sl_percentage = -(entry_price - sl_price) / entry_price
            
            return sl_percentage
        except Exception:
            return self.stoploss

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: str | None, side: str,
                 **kwargs) -> float:
        return 1

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float,
                           rate: float, time_in_force: str, current_time: datetime,
                           entry_tag: str | None, side: str, **kwargs) -> bool:
        return True

    def confirm_trade_exit(self, pair: str, trade: 'Trade', order_type: str, amount: float,
                          rate: float, time_in_force: str, exit_reason: str, current_time: datetime,
                          **kwargs) -> bool:
        """
        Confirm trade exit with basic logging
        """
        try:
            # Calculate trade metrics
            entry_price = trade.open_rate
            profit_ratio = (rate - entry_price) / entry_price if not trade.is_short else (entry_price - rate) / entry_price
            
            # Determine outcome
            if profit_ratio > 0.015:  # Approximate 2R profit
                outcome = "TP"
            elif profit_ratio < -0.005:  # Approximate 1R loss
                outcome = "SL"
            else:
                outcome = "OTHER"
            
            # Calculate trade duration using actual timestamps
            trade_duration = current_time - trade.open_date
            
            # Log exit information with actual data timestamp
            logger.info(f"🏁 [{current_time}] TRADE EXIT: {pair} {trade.trade_direction.upper()}")
            logger.info(f"📊 [{current_time}] Exit: {rate:.4f} | Profit: {profit_ratio:.4%} | Outcome: {outcome}")
            logger.info(f"⏱️ [{current_time}] Duration: {trade_duration}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error in confirm_trade_exit for {pair}: {e}")
            return True 
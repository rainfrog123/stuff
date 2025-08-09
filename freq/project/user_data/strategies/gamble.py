from freqtrade.strategy import IStrategy, informative
from freqtrade.persistence import Trade
from pandas import DataFrame
import pandas as pd
from datetime import datetime
import talib.abstract as ta
import numpy as np
import logging

logger = logging.getLogger(__name__)

class gamble(IStrategy):
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
    # Note: atr_multiplier and tp_risk_ratio are now adaptive based on volatility regime

    def informative_pairs(self):
        # No additional timeframe data needed - using same-TF volatility metrics
        return []

    def _vol_metrics(self, df: DataFrame) -> DataFrame:
        """
        Same-timeframe volatility metrics for adaptive risk management
        """
        # 5s ATR (same timeframe)
        df['atr'] = ta.ATR(df['high'], df['low'], df['close'], timeperiod=self.atr_length)
        df['atr_ema'] = df['atr'].ewm(span=10, adjust=False).mean()  # smooth
        df['atr_pct'] = (df['atr_ema'] / df['close']).clip(upper=0.05)  # cap outliers

        # Rolling stats on atr_pct for regime detection
        win = 240  # ~20 minutes on 5s bars
        m = df['atr_pct'].rolling(win, min_periods=win//4)
        mean, std = m.mean(), m.std(ddof=0)
        df['atr_z'] = (df['atr_pct'] - mean) / (std.replace(0, np.nan))  # volatility expansion
        
        # Percentile rank (fast approximation)
        df['atr_pctile'] = df['atr_pct'].rolling(win, min_periods=win//4)\
                             .apply(lambda x: (x.rank(pct=True).iloc[-1]) if len(x) > 0 else np.nan, raw=False)
        return df

    def _risk_block(self, df: DataFrame) -> DataFrame:
        """
        Adaptive R multiples based on volatility regime
        """
        # Map atr_pctile → dynamic multipliers
        conds = [
            df['atr_pctile'] < 0.3,          # low vol
            df['atr_pctile'].between(0.3, 0.7, inclusive='both'),  # medium vol
            df['atr_pctile'] > 0.7           # high vol
        ]
        atr_mults = [3.5, 3.0, 2.2]  # bigger R in low vol, smaller in high vol
        tp_rrs = [2.2, 2.0, 1.5]     # adjust TP ratios accordingly

        df['atr_mult_dyn'] = np.select(conds, atr_mults, default=3.0)
        df['tp_rr_dyn'] = np.select(conds, tp_rrs, default=2.0)

        df['risk'] = df['atr_ema'] * df['atr_mult_dyn']
        df['entry_price'] = df['close']

        # Adaptive TP/SL based on current volatility regime
        df['tp_long'] = df['entry_price'] + df['tp_rr_dyn'] * df['risk']
        df['sl_long'] = df['entry_price'] - df['risk']
        df['tp_short'] = df['entry_price'] - df['tp_rr_dyn'] * df['risk']
        df['sl_short'] = df['entry_price'] + df['risk']
        return df

    def _vol_confirm_mask(self, df: DataFrame):
        """
        Volatility confirmation filters for entry signals
        """
        # Sweet spot: avoid ultra-low and ultra-high noise
        base = df['atr_pct'].between(0.002, 0.01) & (df['atr_z'] > 0.25)
        long_ok = base & (df['trend'] == 'UP')
        short_ok = base & (df['trend'] == 'DOWN')
        return long_ok, short_ok

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # TEMA trend detection (unchanged)
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
        
        # New: same-TF adaptive volatility metrics
        dataframe = self._vol_metrics(dataframe)
        dataframe = self._risk_block(dataframe)
        
        # Trend reversal signals (for reference)
        dataframe['reversal_to_up'] = (dataframe['trend_flip']) & (dataframe['trend'] == 'UP')
        dataframe['reversal_to_down'] = (dataframe['trend_flip']) & (dataframe['trend'] == 'DOWN')
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Get volatility-confirmed entry conditions
        long_ok, short_ok = self._vol_confirm_mask(dataframe)
        
        # Enter long on TEMA reversal to up with volatility confirmation
        dataframe.loc[
            long_ok & dataframe['trend_flip'] & (dataframe['trend'] == 'UP'),
            'enter_long'
        ] = 1

        # Enter short on TEMA reversal to down with volatility confirmation
        dataframe.loc[
            short_ok & dataframe['trend_flip'] & (dataframe['trend'] == 'DOWN'),
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
            
            # Use latest adaptive volatility metrics
            latest_atr_ema = dataframe['atr_ema'].iloc[-1]
            latest_risk = dataframe['risk'].iloc[-1]
            latest_tp_rr = dataframe['tp_rr_dyn'].iloc[-1]
            
            if pd.isna(latest_atr_ema) or pd.isna(latest_risk) or latest_atr_ema <= 0:
                return self.stoploss
            
            if trade.is_short:
                sl_price = entry_price + latest_risk
                tp_price = entry_price - (latest_tp_rr * latest_risk)
                if current_rate <= tp_price:
                    return 1  # Take profit hit
                sl_percentage = (sl_price - entry_price) / entry_price
            else:
                sl_price = entry_price - latest_risk
                tp_price = entry_price + (latest_tp_rr * latest_risk)
                if current_rate >= tp_price:
                    return 1  # Take profit hit
                sl_percentage = -(entry_price - sl_price) / entry_price
            
            return sl_percentage
        except Exception:
            return self.stoploss

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: str | None, side: str,
                 **kwargs) -> float:
        return max_leverage

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
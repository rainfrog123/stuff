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

    # ROI / SL are in PRICE terms (do NOT multiply by leverage)
    minimal_roi = {"0": 0.004*125}   # +0.3% (price)
    stoploss = -0.001*125            # -0.1% (price)

    trailing_stop = False
    use_custom_stoploss = False
    use_custom_exit = True
    use_custom_exit_price = True

    startup_candle_count: int = 60
    
    # Order management
    order_timeout_in_minutes = 5  # Cancel unfilled orders after 5 minutes
    cancel_open_orders_on_exit = True  # Cancel all orders when exiting

    tema_length = 50
    atr_length = 14

    def informative_pairs(self):
        return []

    # ---------------------------
    # Indicators
    # ---------------------------
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # TEMA
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

        # Optional same-TF volatility blocks (you can remove if not used)
        dataframe = self._vol_metrics(dataframe)
        dataframe = self._risk_block(dataframe)

        # Convenience flags
        dataframe['reversal_to_up'] = dataframe['trend_flip'] & (dataframe['trend'] == 'UP')
        dataframe['reversal_to_down'] = dataframe['trend_flip'] & (dataframe['trend'] == 'DOWN')

        return dataframe

    def _vol_metrics(self, dataframe: DataFrame) -> DataFrame:
        dataframe['atr'] = ta.ATR(dataframe['high'], dataframe['low'], dataframe['close'], timeperiod=self.atr_length)
        dataframe['atr_percentile'] = dataframe['atr'].rolling(100).rank(pct=True)
        dataframe['vol_regime'] = np.where(
            dataframe['atr_percentile'] > 0.8, 'HIGH',
            np.where(dataframe['atr_percentile'] < 0.2, 'LOW', 'NORMAL')
        )
        dataframe['atr_multiplier'] = np.where(
            dataframe['vol_regime'] == 'HIGH', 1.5,
            np.where(dataframe['vol_regime'] == 'LOW', 3.0, 2.0)
        )
        return dataframe

    def _risk_block(self, dataframe: DataFrame) -> DataFrame:
        dataframe['tp_risk_ratio'] = np.where(
            dataframe['vol_regime'] == 'HIGH', 1.5,
            np.where(dataframe['vol_regime'] == 'LOW', 3.0, 2.0)
        )
        dataframe['dynamic_stop'] = dataframe['atr'] * dataframe['atr_multiplier']
        dataframe['dynamic_tp'] = dataframe['dynamic_stop'] * dataframe['tp_risk_ratio']
        return dataframe

    # ---------------------------
    # Entries
    # ---------------------------
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Random filter (50%) — remove if you don’t need it
        dataframe['random_entry'] = np.random.random(len(dataframe)) < 1

        dataframe.loc[
            dataframe['trend_flip'] & (dataframe['trend'] == 'UP') & dataframe['random_entry'],
            'enter_long'
        ] = 1

        dataframe.loc[
            dataframe['trend_flip'] & (dataframe['trend'] == 'DOWN') & dataframe['random_entry'],
            'enter_short'
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # No indicator-based exits — TP/SL handled by callbacks + config
        return dataframe

    # ---------------------------
    # Exits (TP as resting LIMIT)
    # ---------------------------
    def custom_exit(self, pair: str, trade: Trade, current_time: datetime,
                    current_rate: float, current_profit: float, **kwargs):
        """
        Place the initial TP LIMIT order immediately after entry.
        Return (True, "init-tp") once per trade; otherwise (False, None).
        """
        # Don't place TP if trade is already closed
        if not trade.is_open:
            return False, None
            
        ci = getattr(trade, "custom_info", {}) or {}

        # More robust order detection
        has_open_exit = False
        try:
            # Check multiple possible ways to detect open orders
            if hasattr(trade, 'orders') and trade.orders:
                # Check if there are any unfilled exit orders
                for order in trade.orders:
                    if (not getattr(order, 'ft_is_entry', True) and 
                        getattr(order, 'status', '') in ['open', 'pending']):
                        has_open_exit = True
                        break
            
            # Fallback to open_order_id
            if not has_open_exit and hasattr(trade, 'open_order_id'):
                has_open_exit = bool(trade.open_order_id)
                
        except Exception as e:
            logger.warning(f"Error checking open orders for {pair}: {e}")

        # Only set TP once per trade
        if not ci.get("tp_set", False) and not has_open_exit:
            ci["tp_set"] = True
            trade.custom_info = ci
            logger.info(f"Setting TP for {pair} at trade open_rate: {trade.open_rate}")
            return True, "init-tp"

        return False, None

    def order_filled(self, pair: str, trade: Trade, order: dict, current_time: datetime, **kwargs) -> None:
        """
        Called when an order is filled. Use this to track order status.
        """
        if not order.get('ft_is_entry', True):  # Exit order filled
            ci = getattr(trade, "custom_info", {}) or {}
            ci["tp_filled"] = True
            trade.custom_info = ci
            logger.info(f"Exit order filled for {pair}: {order.get('ft_order_tag', 'unknown')}")

    def order_cancelled(self, pair: str, trade: Trade, order: dict, current_time: datetime, **kwargs) -> None:
        """
        Called when an order is cancelled. Reset flags if needed.
        """
        if not order.get('ft_is_entry', True):  # Exit order cancelled
            ci = getattr(trade, "custom_info", {}) or {}
            ci["tp_set"] = False  # Allow setting TP again
            trade.custom_info = ci
            logger.info(f"Exit order cancelled for {pair}: {order.get('ft_order_tag', 'unknown')}")

    def custom_exit_price(self, pair: str, trade: Trade, current_time: datetime,
                          proposed_rate: float, current_profit: float,
                          exit_tag: str | None, **kwargs) -> float | None:
        """
        Price for the LIMIT TP order.
        Here: fixed ±0.3% from entry price. Replace with dynamic_tp if preferred.
        """
        # Only set custom price for our TP orders
        if exit_tag != "init-tp":
            return None
            
        try:
            # Use fixed TP target (±0.3% as per your ROI settings)
            tp_multiplier = 0.997 if trade.is_short else 1.003
            tp_price = trade.open_rate * tp_multiplier
            
            # Validation: ensure TP price makes sense
            if trade.is_short and tp_price >= trade.open_rate:
                logger.warning(f"Invalid TP price for SHORT {pair}: {tp_price} >= {trade.open_rate}")
                return None
            elif not trade.is_short and tp_price <= trade.open_rate:
                logger.warning(f"Invalid TP price for LONG {pair}: {tp_price} <= {trade.open_rate}")
                return None
                
            logger.info(f"TP price for {pair} ({'SHORT' if trade.is_short else 'LONG'}): {tp_price:.6f}")
            return float(tp_price)
            
        except Exception as e:
            logger.warning(f"custom_exit_price error for {pair}: {e}")
            return None  # fall back to exit_pricing if something's off

    # ---------------------------
    # Leverage
    # ---------------------------
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: str | None, side: str,
                 **kwargs) -> float:
        return max_leverage

"""
Binance Trades Downloader

A package for downloading and processing Binance ETH/USDT trade data.
"""

from .downloader import download_monthly_trades

__version__ = "0.1.0"
__all__ = ["download_monthly_trades"] 
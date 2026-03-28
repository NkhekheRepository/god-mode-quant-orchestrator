"""
VNPy Datafeed Module for Binance
Provides historical market data via Binance REST API.
"""

__version__ = "1.0.0"

from .datafeed import BinanceDatafeed as Datafeed

__all__ = ["Datafeed"]

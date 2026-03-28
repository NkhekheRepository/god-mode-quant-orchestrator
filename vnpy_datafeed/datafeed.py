"""
VNPy Datafeed for Binance
Implements the BaseDatafeed interface for fetching historical market data.
"""

import time
import requests
from datetime import datetime
from typing import List, Optional

from vnpy.trader.datafeed import BaseDatafeed
from vnpy.trader.object import BarData, TickData
from vnpy.trader.constant import Exchange, Interval

import logging

logger = logging.getLogger(__name__)


# Interval mapping from VNPy to Binance
INTERVAL_MAP = {
    Interval.MINUTE: "1m",
    Interval.HOUR: "1h",
    Interval.DAILY: "1d",
    Interval.WEEKLY: "1w",
}


class BinanceDatafeed(BaseDatafeed):
    """
    Binance data feed implementation.
    Uses REST API to fetch historical kline data.
    """
    
    def __init__(self) -> None:
        """Initialize the datafeed."""
        super().__init__()
        self.base_url = "https://fapi.binance.com"
        self._initialized = False
    
    def init(self, output: bool = True) -> bool:
        """
        Initialize the datafeed connection.
        
        Args:
            output: Whether to print initialization messages
            
        Returns:
            True if initialization successful
        """
        if self._initialized:
            return True
            
        try:
            # Test connection with a simple API call
            response = requests.get(
                f"{self.base_url}/fapi/v1/ping",
                timeout=10
            )
            response.raise_for_status()
            
            self._initialized = True
            
            if output:
                logger.info("Binance datafeed initialized successfully")
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Binance datafeed: {e}")
            return False
    
    def query_bar_history(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
        start: datetime,
        end: Optional[datetime] = None,
        output: bool = True
    ) -> List[BarData]:
        """
        Query historical bar data from Binance.
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            exchange: Exchange enum
            interval: Bar interval
            start: Start datetime
            end: End datetime (optional, defaults to now)
            output: Whether to print progress
            
        Returns:
            List of BarData objects
        """
        if not self._initialized:
            self.init(output)
        
        # Convert interval to Binance format
        kline_interval = INTERVAL_MAP.get(interval, "1h")
        
        # Clean symbol (remove exchange suffix if present)
        clean_symbol = symbol.split(".")[0] if "." in symbol else symbol
        
        # Convert to Binance format (no slashes)
        if "/" in clean_symbol:
            clean_symbol = clean_symbol.replace("/", "")
        
        # Convert timestamps to milliseconds
        start_ms = int(start.timestamp() * 1000)
        end_ms = int(end.timestamp() * 1000) if end else int(time.time() * 1000)
        
        # Fetch klines from Binance
        try:
            url = f"{self.base_url}/fapi/v1/klines"
            params = {
                "symbol": clean_symbol,
                "interval": kline_interval,
                "startTime": start_ms,
                "endTime": end_ms,
                "limit": 1500  # Binance max limit
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            klines = response.json()
            
            # Convert to BarData objects
            bars = []
            for kline in klines:
                bar = BarData(
                    symbol=clean_symbol,
                    exchange=Exchange.LOCAL,  # VNPy doesn't have BINANCE exchange
                    datetime=datetime.fromtimestamp(kline[0] / 1000),
                    interval=interval,
                    open_price=float(kline[1]),
                    high_price=float(kline[2]),
                    low_price=float(kline[3]),
                    close_price=float(kline[4]),
                    volume=float(kline[5]),
                    gateway_name="BINANCE"
                )
                bars.append(bar)
            
            if output:
                logger.info(f"Loaded {len(bars)} bars for {clean_symbol} ({interval.value})")
                
            return bars
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {clean_symbol}: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to query bar history: {e}")
            return []
    
    def query_tick_history(
        self,
        symbol: str,
        exchange: Exchange,
        start: datetime,
        end: Optional[datetime] = None,
        output: bool = True
    ) -> List[TickData]:
        """
        Query historical tick data.
        
        Note: Binance REST API does not provide historical tick data.
        Use WebSocket for real-time tick data.
        
        Args:
            symbol: Trading symbol
            exchange: Exchange enum
            start: Start datetime
            end: End datetime
            output: Whether to print messages
            
        Returns:
            Empty list (tick history not available via REST)
        """
        if output:
            logger.warning(
                "Historical tick data not available from Binance REST API. "
                "Use WebSocket connection for real-time ticks."
            )
        return []

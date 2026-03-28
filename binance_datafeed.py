"""
Custom Binance Datafeed for VNPy 4.x
Provides historical market data via Binance REST API.
"""

from datetime import datetime
from typing import List, Optional

from vnpy.trader.datafeed import BaseDatafeed
from vnpy.trader.object import BarData, TickData
from vnpy.trader.constant import Exchange, Interval
from vnpy_rest import RestClient

import logging

logger = logging.getLogger(__name__)


class BinanceDatafeed(BaseDatafeed):
    """
    Binance data feed implementation using REST API.
    Supports fetching historical kline data for backtesting.
    """
    
    def __init__(self) -> None:
        """Initialize datafeed."""
        super().__init__()
        self.rest_client = None
        self._initialized = False
        
    def init(self, output: bool = True) -> bool:
        """
        Initialize the datafeed.
        
        Args:
            output: Whether to print output
            
        Returns:
            True if successful
        """
        if self._initialized:
            return True
            
        try:
            # Initialize REST client for Binance futures API
            from vnpy_binance import BinanceLinearGateway
            
            # Use public endpoints (no auth needed for market data)
            self.rest_client = RestClient(
                url="https://fapi.binance.com",
                proxy_host="",
                proxy_port=0
            )
            
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
        Query historical bar data.
        
        Args:
            symbol: Trading symbol
            exchange: Exchange
            interval: Bar interval
            start: Start datetime
            end: End datetime
            output: Whether to print output
            
        Returns:
            List of BarData
        """
        if not self._initialized:
            self.init(output)
            
        # Convert interval to Binance kline interval
        interval_map = {
            Interval.MINUTE: "1m",
            Interval.HOUR: "1h", 
            Interval.DAILY: "1d",
        }
        kline_interval = interval_map.get(interval, "1h")
        
        # Simple implementation - fetch via requests
        # For full implementation, use vnpy_rest properly
        try:
            import requests
            import time
            
            # Convert symbol (remove exchange suffix if present)
            clean_symbol = symbol.split(".")[0] if "." in symbol else symbol
            
            # Convert to Binance format
            if "/" in clean_symbol:
                clean_symbol = clean_symbol.replace("/", "")
            
            # Convert timestamps
            start_ms = int(start.timestamp() * 1000)
            end_ms = int(end.timestamp() * 1000) if end else int(time.time() * 1000)
            
            # Fetch klines
            url = "https://fapi.binance.com/fapi/v1/klines"
            params = {
                "symbol": clean_symbol,
                "interval": kline_interval,
                "startTime": start_ms,
                "endTime": end_ms,
                "limit": 1500
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Convert to BarData
            bars = []
            for kline in data:
                bar = BarData(
                    symbol=clean_symbol,
                    exchange=Exchange.BINANCE,
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
                logger.info(f"Loaded {len(bars)} bars for {clean_symbol}")
                
            return bars
            
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
        
        Note: Binance doesn't provide historical tick data via REST API.
        This returns empty list - use real-time WebSocket for ticks.
        """
        logger.warning("Historical tick data not available from Binance REST API")
        return []

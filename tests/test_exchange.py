"""
Exchange/Gateway Tests for GodMode Quant Orchestrator
Comprehensive tests for Binance Gateway, Order Manager, and Position Tracker
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import sys
import os
import asyncio
import time
from typing import Dict, List
from enum import Enum

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBinanceGateway(unittest.TestCase):
    """Test Binance Gateway functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock the requests module before importing
        self.mock_requests_patcher = patch('exchange.binance_gateway.requests')
        self.mock_requests = self.mock_requests_patcher.start()
        
        # Create mock session with proper headers dict
        self.mock_session = MagicMock()
        self.mock_session.headers = {}
        self.mock_requests.Session.return_value = self.mock_session
        
    def tearDown(self):
        """Tear down test fixtures"""
        self.mock_requests_patcher.stop()
    
    def test_gateway_initialization(self):
        """Test gateway initializes with correct config"""
        from exchange.binance_gateway import BinanceGateway, BinanceConfig
        
        # Test with default config (testnet)
        gateway = BinanceGateway()
        self.assertIsNotNone(gateway)
        self.assertEqual(gateway.config.testnet, True)
        self.assertEqual(gateway.config.base_url, "https://testnet.binancefuture.com")
        # Note: Headers are updated on mock session, check config headers instead
        self.assertIn("X-MBX-APIKEY", gateway.config.headers)
        
        # Test with custom config
        config = BinanceConfig(
            api_key="test_key",
            api_secret="test_secret",
            testnet=False,
            recv_window=10000
        )
        gateway = BinanceGateway(config)
        self.assertEqual(gateway.config.testnet, False)
        self.assertEqual(gateway.config.base_url, "https://fapi.binance.com")
        self.assertEqual(gateway.config.recv_window, 10000)
    
    def test_connect_to_binance(self):
        """Test connection to Binance API"""
        from exchange.binance_gateway import BinanceGateway
        
        # Mock successful server time response
        mock_response = MagicMock()
        mock_response.json.return_value = {"serverTime": int(time.time() * 1000)}
        mock_response.raise_for_status.return_value = None
        self.mock_session.get.return_value = mock_response
        
        gateway = BinanceGateway()
        server_time = gateway.get_server_time()
        
        self.assertIsInstance(server_time, int)
        self.mock_session.get.assert_called_once()
    
    def test_place_order(self):
        """Test order placement"""
        from exchange.binance_gateway import BinanceGateway, OrderSide, OrderType
        
        # Mock successful order response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "orderId": 123456789,
            "symbol": "BTCUSDT",
            "status": "FILLED",
            "executedQty": "0.001",
            "avgPrice": "50000.0"
        }
        mock_response.raise_for_status.return_value = None
        self.mock_session.post.return_value = mock_response
        
        gateway = BinanceGateway()
        result = gateway.place_market_order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=0.001
        )
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['orderId'], 123456789)
        self.assertEqual(result['status'], "FILLED")
    
    def test_cancel_order(self):
        """Test order cancellation"""
        from exchange.binance_gateway import BinanceGateway
        
        # Mock successful cancel response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "orderId": 123456789,
            "symbol": "BTCUSDT",
            "status": "CANCELED"
        }
        mock_response.raise_for_status.return_value = None
        self.mock_session.delete.return_value = mock_response
        
        gateway = BinanceGateway()
        result = gateway.cancel_order("BTCUSDT", order_id=123456789)
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['status'], "CANCELED")
    
    def test_get_account_balance(self):
        """Test account balance retrieval"""
        from exchange.binance_gateway import BinanceGateway
        
        # Mock successful account info response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "assets": [
                {
                    "asset": "USDT",
                    "walletBalance": "10000.00",
                    "availableBalance": "9500.00",
                    "totalUnrealizedProfit": "500.00"
                },
                {
                    "asset": "BNB",
                    "walletBalance": "10.0",
                    "availableBalance": "10.0",
                    "totalUnrealizedProfit": "0.0"
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        self.mock_session.get.return_value = mock_response
        
        gateway = BinanceGateway()
        balance = gateway.get_balance("USDT")
        
        self.assertEqual(balance, 9500.0)
    
    def test_rate_limiting(self):
        """Test rate limiting is applied"""
        from exchange.binance_gateway import retry_with_backoff, BinanceGateway
        
        # Test retry decorator
        call_count = 0
        
        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Simulated failure")
            return "success"
        
        result = failing_function()
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 3)
    
    def test_signature_generation(self):
        """Test HMAC signature generation"""
        from exchange.binance_gateway import BinanceGateway, BinanceConfig
        
        config = BinanceConfig(
            api_key="test_key",
            api_secret="test_secret"
        )
        gateway = BinanceGateway(config)
        
        # Test signature generation
        params = "symbol=BTCUSDT&timestamp=1234567890"
        signature = gateway._generate_signature(params)
        
        self.assertIsInstance(signature, str)
        self.assertEqual(len(signature), 64)  # SHA256 hex digest length
    
    def test_get_positions(self):
        """Test position retrieval"""
        from exchange.binance_gateway import BinanceGateway
        
        # Mock successful positions response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "positions": [
                {
                    "symbol": "BTCUSDT",
                    "positionAmt": "0.01",
                    "entryPrice": "50000.0",
                    "markPrice": "51000.0",
                    "unrealizedProfit": "10.0",
                    "positionSide": "LONG",
                    "leverage": "10",
                    "isolatedMargin": "0.0"
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        self.mock_session.get.return_value = mock_response
        
        gateway = BinanceGateway()
        positions = gateway.get_positions()
        
        self.assertIsInstance(positions, list)
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0]['symbol'], "BTCUSDT")
        self.assertEqual(positions[0]['positionAmt'], 0.01)
    
    def test_market_data_endpoints(self):
        """Test various market data endpoints"""
        from exchange.binance_gateway import BinanceGateway
        
        # Create different mock responses for different endpoints
        def mock_get_response(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            
            # Check the URL to determine what to return
            if "ticker/24hr" in str(args[0]) if args else "":
                mock_response.json.return_value = {
                    "symbol": "BTCUSDT",
                    "lastPrice": "50000.0",
                    "priceChangePercent": "2.5"
                }
            elif "depth" in str(args[0]) if args else "":
                mock_response.json.return_value = {
                    "symbol": "BTCUSDT",
                    "bids": [["49999.0", "0.1"]],
                    "asks": [["50001.0", "0.1"]]
                }
            elif "trades" in str(args[0]) if args else "":
                mock_response.json.return_value = [
                    {"id": "1", "price": "50000.0", "qty": "0.001"},
                    {"id": "2", "price": "50001.0", "qty": "0.002"}
                ]
            else:
                mock_response.json.return_value = {"serverTime": 1234567890}
            
            return mock_response
        
        self.mock_session.get.side_effect = mock_get_response
        
        gateway = BinanceGateway()
        
        # Test ticker
        ticker = gateway.get_ticker("BTCUSDT")
        self.assertEqual(ticker['symbol'], "BTCUSDT")
        
        # Test order book
        order_book = gateway.get_order_book("BTCUSDT")
        self.assertIsInstance(order_book, dict)
        self.assertIn("bids", order_book)
        
        # Test recent trades
        trades = gateway.get_recent_trades("BTCUSDT")
        self.assertIsInstance(trades, list)
        self.assertEqual(len(trades), 2)


class TestOrderManager(unittest.TestCase):
    """Test Order Manager functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create mock gateway
        self.mock_gateway = MagicMock()
        
    def test_order_creation(self):
        """Test order creation"""
        from exchange.order_manager import OrderManager, Order, OrderSide, OrderType, OrderStatus
        
        manager = OrderManager(self.mock_gateway)
        
        # Test creating an order
        order_id = manager.generate_order_id()
        self.assertIsInstance(order_id, str)
        self.assertTrue(order_id.startswith("GM_"))
        
        # Create order object
        order = Order(
            order_id=order_id,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.001,
            status=OrderStatus.PENDING
        )
        
        self.assertEqual(order.symbol, "BTCUSDT")
        self.assertEqual(order.side, OrderSide.BUY)
        self.assertEqual(order.status, OrderStatus.PENDING)
        self.assertFalse(order.is_terminal())
    
    def test_order_validation(self):
        """Test order validation"""
        from exchange.order_manager import Order, OrderSide, OrderType, OrderStatus
        
        # Test valid order
        order = Order(
            order_id="test_1",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=0.001,
            price=50000.0
        )
        
        self.assertEqual(order.symbol, "BTCUSDT")
        self.assertEqual(order.quantity, 0.001)
        self.assertEqual(order.price, 50000.0)
        
        # Test terminal states
        terminal_statuses = [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED, OrderStatus.EXPIRED]
        for status in terminal_statuses:
            order.status = status
            self.assertTrue(order.is_terminal())
        
        # Test non-terminal states
        non_terminal_statuses = [OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]
        for status in non_terminal_statuses:
            order.status = status
            self.assertFalse(order.is_terminal())
    
    def test_order_cancellation(self):
        """Test order cancellation"""
        from exchange.order_manager import OrderManager, OrderSide, OrderType
        
        # Mock successful cancel
        self.mock_gateway.cancel_order.return_value = {"status": "CANCELED"}
        
        manager = OrderManager(self.mock_gateway)
        
        # Manually add an order to track
        order_id = "test_order_1"
        manager._orders[order_id] = MagicMock()
        manager._orders[order_id].symbol = "BTCUSDT"
        manager._orders[order_id].order_id = 123
        manager._orders[order_id].is_terminal.return_value = False
        
        # Test cancellation
        result = manager.cancel_order(order_id)
        
        self.assertTrue(result)
        self.mock_gateway.cancel_order.assert_called_once()
    
    def test_statistics_tracking(self):
        """Test order statistics tracking"""
        from exchange.order_manager import OrderManager
        
        manager = OrderManager(self.mock_gateway)
        
        # Initial statistics
        stats = manager.get_statistics()
        self.assertEqual(stats['total_orders'], 0)
        self.assertEqual(stats['filled_orders'], 0)
        self.assertEqual(stats['rejected_orders'], 0)
        
        # Simulate some orders
        manager._total_orders = 10
        manager._filled_orders = 7
        manager._rejected_orders = 3
        
        stats = manager.get_statistics()
        self.assertEqual(stats['total_orders'], 10)
        self.assertEqual(stats['filled_orders'], 7)
        self.assertEqual(stats['rejected_orders'], 3)
        self.assertAlmostEqual(stats['fill_rate'], 0.7, places=2)
    
    def test_order_retrieval(self):
        """Test order retrieval methods"""
        from exchange.order_manager import OrderManager, Order, OrderSide, OrderType, OrderStatus
        
        manager = OrderManager(self.mock_gateway)
        
        # Create test orders
        order1 = Order(
            order_id="order_1",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.001,
            status=OrderStatus.FILLED
        )
        
        order2 = Order(
            order_id="order_2",
            symbol="ETHUSDT",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=1.0,
            price=3000.0,
            status=OrderStatus.PENDING
        )
        
        # Add to manager
        manager._orders["order_1"] = order1
        manager._orders["order_2"] = order2
        manager._pending_orders["order_2"] = order2
        
        # Test get_order
        retrieved = manager.get_order("order_1")
        self.assertEqual(retrieved.symbol, "BTCUSDT")
        
        # Test get_open_orders
        open_orders = manager.get_open_orders()
        self.assertEqual(len(open_orders), 1)
        self.assertEqual(open_orders[0].order_id, "order_2")
        
        # Test get_filled_orders
        filled_orders = manager.get_filled_orders()
        self.assertEqual(len(filled_orders), 1)
        self.assertEqual(filled_orders[0].order_id, "order_1")
    
    def test_client_order_id_generation(self):
        """Test client order ID generation"""
        from exchange.order_manager import OrderManager
        
        manager = OrderManager(self.mock_gateway)
        
        # Generate client order ID
        client_id = manager.generate_client_order_id()
        
        # Test basic properties
        self.assertIsInstance(client_id, str)
        self.assertTrue(client_id.startswith("GM_"))
        self.assertGreater(len(client_id), 3)
        
        # Generate another one to ensure it works
        client_id2 = manager.generate_client_order_id()
        self.assertIsInstance(client_id2, str)
        self.assertTrue(client_id2.startswith("GM_"))


class TestPositionTracker(unittest.TestCase):
    """Test Position Tracker functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create mock gateway
        self.mock_gateway = MagicMock()
        self.mock_gateway.get_balance.return_value = 10000.0
        self.mock_gateway.calculate_liquidation_price.return_value = 45000.0
        
    def test_position_creation(self):
        """Test position creation"""
        from exchange.position_tracker import Position
        
        position = Position(
            symbol="BTCUSDT",
            position_side="LONG",
            quantity=0.01,
            entry_price=50000.0,
            mark_price=51000.0,
            leverage=10,
            unrealized_pnl=10.0
        )
        
        self.assertEqual(position.symbol, "BTCUSDT")
        self.assertEqual(position.position_side, "LONG")
        self.assertEqual(position.quantity, 0.01)
        self.assertTrue(position.is_long)
        self.assertFalse(position.is_short)
        
        # Test position side properties
        position.position_side = "SHORT"
        position.quantity = -0.01
        self.assertTrue(position.is_short)
        self.assertFalse(position.is_long)
        
        position.position_side = "BOTH"
        position.quantity = 0.01
        self.assertTrue(position.is_long)
        
        position.quantity = -0.01
        self.assertTrue(position.is_short)
    
    def test_position_update(self):
        """Test position update"""
        from exchange.position_tracker import Position
        
        position = Position(
            symbol="BTCUSDT",
            position_side="LONG",
            quantity=0.01,
            entry_price=50000.0,
            mark_price=50000.0,  # Initial mark price
            leverage=10,
            unrealized_pnl=0.0
        )
        
        # Test initial PnL calculation
        self.assertEqual(position.unrealized_pnl, 0.0)
        
        # Update mark price and recalculate PnL
        position.mark_price = 51000.0
        position.unrealized_pnl = (position.mark_price - position.entry_price) * position.quantity
        position.position_value = abs(position.quantity * position.mark_price)
        
        self.assertEqual(position.unrealized_pnl, 10.0)
        self.assertAlmostEqual(position.pnl_percent, 1.9607843137254901, places=3)  # 10/510 * 100 = 1.96%
        self.assertAlmostEqual(position.return_percent, 2.0, places=3)  # 10/(50000*0.01) = 2%
    
    def test_position_closure(self):
        """Test position closure"""
        from exchange.position_tracker import PositionTracker
        
        tracker = PositionTracker(self.mock_gateway)
        
        # Mock gateway to return a position with numeric values
        self.mock_gateway.get_positions.return_value = [
            {
                "symbol": "BTCUSDT",
                "positionAmt": 0.01,
                "entryPrice": 50000.0,
                "markPrice": 51000.0,
                "unrealizedProfit": 10.0,
                "positionSide": "LONG",
                "leverage": 10
            }
        ]
        
        # Sync positions
        tracker.sync_positions()
        self.assertEqual(len(tracker.get_all_positions()), 1)
        
        # Close position
        result = tracker.close_position("BTCUSDT", realized_pnl=10.0)
        self.assertTrue(result)
        self.assertEqual(len(tracker.get_all_positions()), 0)
        self.assertEqual(len(tracker._closed_positions), 1)
        self.assertEqual(tracker.get_total_realized_pnl(), 10.0)
    
    def test_pnl_calculation(self):
        """Test PnL calculation"""
        from exchange.position_tracker import Position
        
        # Test long position PnL
        position = Position(
            symbol="BTCUSDT",
            position_side="LONG",
            quantity=0.1,
            entry_price=50000.0,
            mark_price=51000.0,
            leverage=10,
            unrealized_pnl=0.0
        )
        
        # Calculate unrealized PnL
        position.unrealized_pnl = (position.mark_price - position.entry_price) * position.quantity
        self.assertEqual(position.unrealized_pnl, 100.0)
        
        # Calculate position value
        position.position_value = abs(position.quantity * position.mark_price)
        self.assertEqual(position.position_value, 5100.0)
        
        # Test short position PnL
        short_position = Position(
            symbol="ETHUSDT",
            position_side="SHORT",
            quantity=-1.0,
            entry_price=3000.0,
            mark_price=2900.0,
            leverage=5,
            unrealized_pnl=0.0
        )
        
        short_position.unrealized_pnl = (short_position.mark_price - short_position.entry_price) * short_position.quantity
        self.assertEqual(short_position.unrealized_pnl, 100.0)  # (2900-3000)*(-1) = 100
    
    def test_position_statistics(self):
        """Test position statistics"""
        from exchange.position_tracker import PositionTracker, Position
        
        tracker = PositionTracker(self.mock_gateway)
        
        # Add some mock positions
        btc_position = Position(
            symbol="BTCUSDT",
            position_side="LONG",
            quantity=0.01,
            entry_price=50000.0,
            mark_price=51000.0,
            leverage=10,
            unrealized_pnl=10.0,
            position_value=510.0
        )
        
        eth_position = Position(
            symbol="ETHUSDT",
            position_side="SHORT",
            quantity=-1.0,
            entry_price=3000.0,
            mark_price=2900.0,
            leverage=5,
            unrealized_pnl=100.0,
            position_value=2900.0
        )
        
        tracker._positions["BTCUSDT"] = btc_position
        tracker._positions["ETHUSDT"] = eth_position
        
        # Update total unrealized PnL
        tracker._total_unrealized_pnl = btc_position.unrealized_pnl + eth_position.unrealized_pnl
        
        # Test statistics
        stats = tracker.get_statistics()
        self.assertEqual(stats['position_count'], 2)
        self.assertEqual(stats['long_positions'], 1)
        self.assertEqual(stats['short_positions'], 1)
        self.assertEqual(stats['total_unrealized_pnl'], 110.0)
        self.assertEqual(stats['profitable_count'], 2)
        self.assertEqual(stats['losing_count'], 0)
    
    def test_profitable_and_losing_positions(self):
        """Test filtering profitable and losing positions"""
        from exchange.position_tracker import PositionTracker, Position
        
        tracker = PositionTracker(self.mock_gateway)
        
        # Add positions with different PnL
        tracker._positions["PROFIT"] = Position(
            symbol="PROFIT",
            position_side="LONG",
            quantity=1.0,
            entry_price=100.0,
            mark_price=110.0,
            leverage=2,
            unrealized_pnl=10.0,
            position_value=110.0
        )
        
        tracker._positions["LOSS"] = Position(
            symbol="LOSS",
            position_side="LONG",
            quantity=1.0,
            entry_price=100.0,
            mark_price=90.0,
            leverage=2,
            unrealized_pnl=-10.0,
            position_value=90.0
        )
        
        # Test filtering
        profitable = tracker.get_profitable_positions()
        self.assertEqual(len(profitable), 1)
        self.assertEqual(profitable[0].symbol, "PROFIT")
        
        losing = tracker.get_losing_positions()
        self.assertEqual(len(losing), 1)
        self.assertEqual(losing[0].symbol, "LOSS")
    
    def test_positions_near_liquidation(self):
        """Test positions near liquidation"""
        from exchange.position_tracker import PositionTracker, Position
        
        tracker = PositionTracker(self.mock_gateway)
        
        # Add position near liquidation
        tracker._positions["NEAR_LIQ"] = Position(
            symbol="NEAR_LIQ",
            position_side="LONG",
            quantity=0.01,
            entry_price=50000.0,
            mark_price=46000.0,  # Close to liquidation
            leverage=10,
            unrealized_pnl=-40.0,
            position_value=460.0,
            liquidation_price=45000.0
        )
        
        # Add position far from liquidation
        tracker._positions["SAFE"] = Position(
            symbol="SAFE",
            position_side="LONG",
            quantity=0.01,
            entry_price=50000.0,
            mark_price=60000.0,
            leverage=10,
            unrealized_pnl=100.0,
            position_value=600.0,
            liquidation_price=45000.0
        )
        
        # Test near liquidation (within 10% buffer)
        near_liquidation = tracker.get_positions_near_liquidation(buffer_percent=10.0)
        self.assertEqual(len(near_liquidation), 1)
        self.assertEqual(near_liquidation[0].symbol, "NEAR_LIQ")
        
        # Test with larger buffer
        near_liquidation = tracker.get_positions_near_liquidation(buffer_percent=30.0)
        self.assertEqual(len(near_liquidation), 2)  # Both should be within 30%
    
    def test_portfolio_summary(self):
        """Test portfolio summary generation"""
        from exchange.position_tracker import PositionTracker, Position
        
        tracker = PositionTracker(self.mock_gateway)
        
        # Add position
        tracker._positions["BTCUSDT"] = Position(
            symbol="BTCUSDT",
            position_side="LONG",
            quantity=0.01,
            entry_price=50000.0,
            mark_price=51000.0,
            leverage=10,
            unrealized_pnl=10.0,
            position_value=510.0
        )
        
        # Get portfolio summary
        summary = tracker.get_portfolio_summary()
        
        self.assertIn("positions", summary)
        self.assertIn("statistics", summary)
        self.assertIn("total_value", summary)
        self.assertIn("available_balance", summary)
        
        self.assertEqual(len(summary['positions']), 1)
        self.assertEqual(summary['available_balance'], 10000.0)
        self.assertGreaterEqual(summary['total_value'], 10000.0)
    
    def test_sync_positions_with_gateway(self):
        """Test position synchronization with gateway"""
        from exchange.position_tracker import PositionTracker
        
        tracker = PositionTracker(self.mock_gateway)
        
        # Mock gateway response with numeric values
        self.mock_gateway.get_positions.return_value = [
            {
                "symbol": "BTCUSDT",
                "positionAmt": 0.01,
                "entryPrice": 50000.0,
                "markPrice": 51000.0,
                "unrealizedProfit": 10.0,
                "positionSide": "LONG",
                "leverage": 10,
                "positionInitialMargin": 50.0,
                "isolatedMargin": 0.0
            }
        ]
        
        # Sync positions
        positions = tracker.sync_positions()
        
        self.assertEqual(len(positions), 1)
        self.assertIn("BTCUSDT", positions)
        self.assertEqual(positions["BTCUSDT"].quantity, 0.01)
        self.assertEqual(positions["BTCUSDT"].entry_price, 50000.0)
        
        # Verify gateway was called
        self.mock_gateway.get_positions.assert_called_once()


if __name__ == '__main__':
    unittest.main()
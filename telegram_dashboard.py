"""
Telegram Dashboard for God Mode Quant Trading Orchestrator
Provides comprehensive real-time monitoring, command handlers, and inline keyboards
"""
import os
import logging
import time
import json
import threading
import requests
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
import hashlib

logger = logging.getLogger(__name__)


class TelegramMessageType(Enum):
    """Types of Telegram messages"""
    TRADE_ENTRY = "trade_entry"
    TRADE_EXIT = "trade_exit"
    RISK_ALERT = "risk_alert"
    TRUST_CHANGE = "trust_change"
    DAILY_SUMMARY = "daily_summary"
    WEEKLY_SUMMARY = "weekly_summary"
    STATUS_UPDATE = "status_update"
    ERROR = "error"
    SYSTEM = "system"


class TelegramEmoji(Enum):
    """Emojis for different message types"""
    # Trading
    LONG = "\U0001F4C8"   # Chart upward
    SHORT = "\U0001F4C9"  # Chart downward
    ENTRY = "\U00002705"  # Check mark
    EXIT = "\U0000274C"   # Cross mark
    PROFIT = "\U0001F4B0" # Money bag
    LOSS = "\U0001F4B3"   # Money with wings
    
    # Risk
    WARNING = "\U000026A0"  # Warning
    DANGER = "\U0001F6AB"   # Prohibited
    SHIELD = "\U0001F6E1"  # Shield
    
    # Trust
    TRUST_HIGH = "\U0001F3AF"  # Target
    TRUST_MED = "\U0001F50D"   # Magnifying glass
    TRUST_LOW = "\U0001F6D1"   # Stop sign
    
    # System
    ROBOT = "\U0001F916"   # Robot
    HEART = "\U00002764"    # Heart
    GEAR = "\U00002699"     # Gear
    CLOCK = "\U000023F0"   # Alarm clock
    STATS = "\U0001F4CA"    # Bar chart
    FIRE = "\U0001F525"     # Fire
    ICE = "\U0001F9CA"      # Ice


@dataclass
class TradeNotification:
    """Trade execution notification data"""
    symbol: str
    side: str  # LONG or SHORT
    quantity: float
    entry_price: float
    current_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None
    timestamp: float = field(default_factory=time.time)
    strategy: str = "unknown"


@dataclass
class RiskAlertNotification:
    """Risk alert notification data"""
    alert_type: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class TrustChangeNotification:
    """Trust score change notification"""
    service_or_user: str
    old_score: float
    new_score: float
    change_reason: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class DailySummary:
    """Daily summary data"""
    date: str
    total_trades: int
    profitable_trades: int
    losing_trades: int
    total_pnl: float
    win_rate: float
    max_drawdown: float
    portfolio_value: float
    open_positions: int
    trust_score: float


class TelegramDashboard:
    """Comprehensive Telegram dashboard for trading orchestrator"""
    
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_base = f"https://api.telegram.org/bot{bot_token}"
        
        # State for tracking
        self._lock = threading.RLock()
        self.trade_history: List[TradeNotification] = []
        self.last_trust_score: Dict[str, float] = {}
        self.daily_stats: Dict[str, Any] = {
            "trades": 0,
            "profitable": 0,
            "losing": 0,
            "pnl": 0.0,
            "start_value": 0.0,
            "start_time": time.time()
        }
        
        # Configuration
        self.alert_thresholds = {
            "max_drawdown": 10.0,        # 10% max drawdown
            "max_position_risk": 2.0,    # 2% per position
            "max_portfolio_risk": 5.0,   # 5% total portfolio
            "trust_score_low": 50.0,      # Alert if below 50
            "trust_score_critical": 30.0 # Critical if below 30
        }
        
        # Rate limiting
        self.last_alert_time: Dict[str, float] = {}
        self.alert_cooldown = 300  # 5 minutes between alerts of same type
        
        # Prometheus metrics integration
        self._setup_prometheus_exporters()
    
    def _setup_prometheus_exporters(self):
        """Setup Prometheus metrics for Telegram dashboard"""
        try:
            from prometheus_client import Counter, Gauge, Histogram, Info
            from prometheus_client import start_http_server
            from prometheus_client import REGISTRY
            
            # Telegram metrics
            self.telegram_messages_sent = Counter(
                'telegram_messages_sent_total',
                'Total Telegram messages sent',
                ['message_type', 'status']
            )
            
            self.telegram_last_message_time = Gauge(
                'telegram_last_message_timestamp',
                'Timestamp of last Telegram message',
                ['message_type']
            )
            
            self.telegram_command_count = Counter(
                'telegram_commands_received_total',
                'Total Telegram commands received',
                ['command']
            )
            
            self.active_positions_gauge = Gauge(
                'trading_active_positions',
                'Current number of active positions'
            )
            
            self.pnl_gauge = Gauge(
                'trading_unrealized_pnl_dollars',
                'Unrealized P&L in dollars'
            )
            
            self.trust_score_gauge = Gauge(
                'security_trust_score',
                'Current trust score'
            )
            
            self.risk_alert_count = Counter(
                'risk_alerts_triggered_total',
                'Total risk alerts triggered',
                ['alert_type', 'severity']
            )
            
            logger.info("Prometheus metrics initialized for Telegram dashboard")
            
        except ImportError:
            logger.warning("prometheus_client not available, skipping metrics setup")
            self.telegram_messages_sent = None
            self.telegram_last_message_time = None
            self.telegram_command_count = None
            self.active_positions_gauge = None
            self.pnl_gauge = None
            self.trust_score_gauge = None
            self.risk_alert_count = None
    
    def _increment_metric(self, metric, labels=None, value=1):
        """Safely increment a Prometheus metric"""
        if metric is not None:
            if labels:
                metric.labels(**labels).inc(value)
            else:
                metric.inc(value)
    
    def _set_metric(self, metric, labels=None, value=0):
        """Safely set a Prometheus gauge metric"""
        if metric is not None:
            if labels:
                metric.labels(**labels).set(value)
            else:
                metric.set(value)
    
    def _should_send_alert(self, alert_type: str) -> bool:
        """Check if enough time has passed since last alert of this type"""
        current_time = time.time()
        last_time = self.last_alert_time.get(alert_type, 0)
        
        if current_time - last_time >= self.alert_cooldown:
            self.last_alert_time[alert_type] = current_time
            return True
        return False
    
    def _format_price(self, price: float) -> str:
        """Format price with appropriate decimal places"""
        if price >= 1000:
            return f"{price:,.2f}"
        elif price >= 1:
            return f"{price:,.4f}"
        else:
            return f"{price:,.8f}"
    
    def _format_pnl(self, pnl: float) -> Tuple[str, str]:
        """Format P&L with emoji and color"""
        if pnl > 0:
            return f"+{self._format_price(pnl)}", TelegramEmoji.PROFIT.value
        elif pnl < 0:
            return f"-{self._format_price(abs(pnl))}", TelegramEmoji.LOSS.value
        else:
            return "0.00", TelegramEmoji.ENTRY.value
    
    def _format_error(self, command: str, error: Exception) -> str:
        """Format error message for user"""
        return f"⚠️ <b>{command.upper()} ERROR</b>\n\nUnable to retrieve data. Please try again later."
    
    def handle_command(self, command: str, args: Optional[List[str]] = None) -> str:
        """Handle incoming bot commands"""
        if args is None:
            args = []
        
        command_map = {
            "start": self._get_start_command,
            "help": self._get_help_command,
            "status": self._get_status_command,
            "balance": self._get_balance_command,
            "positions": self._get_positions_command,
            "portfolio": self._get_portfolio_command,
            "stop": self._get_stop_command,
            "cancel": self._get_cancel_command,
            "engine": self._get_engine_command,
            "leverage": self._get_leverage_command,
            "kelly": self._get_kelly_command,
            "strategies": self._get_strategies_command,
            "signal": self._get_signal_command,
            "orders": self._get_orders_command,
            "var": self._get_var_command,
        }
        
        handler = command_map.get(command.lower())
        if handler:
            try:
                return handler(args)
            except Exception as e:
                logger.error(f"Error handling /{command}: {e}")
                return self._format_error(command, e)
        
        return self._get_unknown_command(command)
    
    def _get_status_command(self, args: List[str]) -> str:
        """Get system status"""
        try:
            from risk_management import risk_manager
            portfolio = risk_manager.portfolio
            return (
                f"⚡ <b>SYSTEM STATUS</b>\n\n"
                f"<b>Balance:</b> ${portfolio.balance:,.2f}\n"
                f"<b>Positions:</b> {portfolio.position_count}\n"
                f"<b>P&L:</b> ${portfolio.total_unrealized_pnl:,.2f}\n"
                f"<b>Equity:</b> ${portfolio.equity:,.2f}"
            )
        except Exception as e:
            return self._format_error("status", e)
    
    def _get_portfolio_command(self, args: List[str]) -> str:
        """Get portfolio info"""
        return self._get_status_command(args)
    
    def _get_help_command(self, args: List[str]) -> str:
        """Get help message"""
        return (
            f"📖 <b>AVAILABLE COMMANDS</b>\n\n"
            f"/start - Initialize bot\n"
            f"/status - System status\n"
            f"/balance - Account balance\n"
            f"/positions - Open positions\n"
            f"/portfolio - Portfolio details\n"
            f"/stop - Stop trading\n"
            f"/cancel - Cancel pending orders\n"
            f"/engine - Engine control\n"
            f"/leverage [x] - Set leverage\n"
            f"/kelly - Kelly criterion info\n"
            f"/strategies - List strategies\n"
            f"/signal - Get signal\n"
            f"/orders - Active orders\n"
            f"/var - Value at Risk\n"
            f"/help - This help message"
        )

    def _get_start_command(self, args: List[str]) -> str:
        """Handle /start command - welcome message"""
        return (
            f"🤖 <b>GOD MODE QUANT ORCHESTRATOR</b>\n\n"
            f"Welcome! The trading bot is active.\n\n"
            f"<b>Quick Start:</b>\n"
            f"  /status - Check system status\n"
            f"  /balance - View account balance\n"
            f"  /positions - View open positions\n"
            f"  /help - Show all commands\n\n"
            f"<i>Monitoring active. Alerts will be sent automatically.</i>"
        )

    def _get_balance_command(self, args: List[str]) -> str:
        """Get account balance"""
        try:
            from trading_engine import get_trading_engine
            engine = get_trading_engine()

            if engine:
                status = engine.get_status()
                return (
                    f"💰 <b>ACCOUNT BALANCE</b>\n\n"
                    f"<b>Balance:</b> ${status.balance:,.2f}\n"
                    f"<b>Equity:</b> ${status.balance + status.total_pnl:,.2f}\n"
                    f"<b>Unrealized P&L:</b> ${status.total_pnl:+,.2f}\n"
                    f"<b>Leverage:</b> {status.leverage}x\n"
                    f"<b>Available Margin:</b> ${status.balance * 0.8:,.2f}"
                )

            # Fallback to risk_manager
            from risk_management import risk_manager
            portfolio = risk_manager.portfolio
            return (
                f"💰 <b>ACCOUNT BALANCE</b>\n\n"
                f"<b>Balance:</b> ${portfolio.balance:,.2f}\n"
                f"<b>Equity:</b> ${portfolio.equity:,.2f}\n"
                f"<b>Unrealized P&L:</b> ${portfolio.total_unrealized_pnl:+,.2f}\n"
                f"<b>Positions:</b> {portfolio.position_count}"
            )
        except Exception as e:
            return f"⚠️ <b>BALANCE UNAVAILABLE</b>\n\n{str(e)}"

    def _get_positions_command(self, args: List[str]) -> str:
        """Get open positions"""
        try:
            from trading_engine import get_trading_engine
            engine = get_trading_engine()

            if engine is None:
                return "⚠️ <b>ENGINE NOT INITIALIZED</b>\n\nUse /start to initialize."

            positions = engine.get_positions()

            if not positions:
                return (
                    f"📊 <b>OPEN POSITIONS</b>\n\n"
                    f"No open positions.\n"
                    f"Waiting for trading signals..."
                )

            message = f"📊 <b>OPEN POSITIONS</b>\n\n"
            for symbol, pos in positions.items():
                side = pos.get('side', 'UNKNOWN')
                emoji = "📈" if side == "LONG" else "📉"
                pnl = pos.get('unrealized_pnl', 0)
                pnl_emoji = "🟢" if pnl >= 0 else "🔴"

                message += (
                    f"{emoji} <b>{symbol}</b>\n"
                    f"  Side: {side}\n"
                    f"  Qty: {pos.get('quantity', 0):.6f}\n"
                    f"  Entry: {self._format_price(pos.get('entry_price', 0))}\n"
                    f"  SL: {self._format_price(pos.get('stop_loss', 0))}\n"
                    f"  TP: {self._format_price(pos.get('take_profit', 0))}\n"
                    f"  {pnl_emoji} P&L: ${pnl:+,.2f}\n\n"
                )

            return message
        except Exception as e:
            return f"⚠️ <b>POSITIONS UNAVAILABLE</b>\n\n{str(e)}"

    def _get_cancel_command(self, args: List[str]) -> str:
        """Cancel pending orders"""
        try:
            from trading_engine import get_trading_engine
            engine = get_trading_engine()

            if engine is None:
                return "⚠️ <b>ENGINE NOT INITIALIZED</b>\n\nUse /start to initialize."

            # Cancel all pending orders
            if hasattr(engine, 'order_manager') and engine.order_manager:
                stats = engine.order_manager.get_statistics()
                pending = stats.get('pending_orders', 0)

                if pending == 0:
                    return (
                        f"✅ <b>NO PENDING ORDERS</b>\n\n"
                        f"There are no pending orders to cancel."
                    )

                # Cancel pending orders
                cancelled = engine.order_manager.cancel_all_orders()
                return (
                    f"🛑 <b>ORDERS CANCELLED</b>\n\n"
                    f"Cancelled {cancelled} pending order(s)."
                )

            return (
                f"⚠️ <b>CANCEL UNAVAILABLE</b>\n\n"
                f"Order manager not available."
            )
        except Exception as e:
            return f"⚠️ <b>CANCEL ERROR</b>\n\n{str(e)}"

    def send_message_to_chat(self, chat_id: int, text: str, parse_mode: str = 'HTML') -> bool:
        """Send message to a specific chat (for bot handler responses)"""
        url = f"{self.api_base}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode
        }
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            if result.get('ok'):
                return True
            else:
                logger.error(f"Telegram API error: {result}")
                return False
        except Exception as e:
            logger.error(f"Error sending message to chat {chat_id}: {e}")
            return False
    
    def _send_message(self, text: str, parse_mode: str = 'HTML',
                     reply_markup: Optional[Dict] = None) -> bool:
        """Send message to Telegram"""
        url = f"{self.api_base}/sendMessage"
        payload = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': parse_mode
        }
        if reply_markup:
            payload['reply_markup'] = json.dumps(reply_markup)
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if result.get('ok'):
                logger.info(f"Telegram message sent successfully: {text[:50]}...")
                return True
            else:
                logger.error(f"Telegram API error: {result}")
                return False
            
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False
    
    def _get_inline_keyboard(self) -> Dict:
        """Generate inline keyboard with action buttons"""
        return {
            "inline_keyboard": [
                [{"text": "📊 Portfolio", "callback_data": "portfolio"}],
                [{"text": "📈 P&L", "callback_data": "pnl"}],
                [{"text": "⚙️ Settings", "callback_data": "settings"}],
                [{"text": "🛑 Stop", "callback_data": "stop"}]
            ]
        }
    
    def _get_stop_command(self, args: List[str]) -> str:
        """Stop the trading engine"""
        try:
            from trading_engine import get_trading_engine
            engine = get_trading_engine()
            
            if engine is None:
                return "\U0001F6AB Engine not initialized"
            
            if engine.state.value == "STOPPED":
                return "\U0001F534 Engine is already stopped"
            
            engine.stop()
            return "\U0001F534 <b>ENGINE STOPPED</b>\n\nTrading has been halted"
                 
        except Exception as e:
            logger.error(f"Error in _get_stop_command: {e}")
            return f"\U0001F6AB <b>Error stopping engine</b>\n\n{str(e)}"
     
    def _get_engine_command(self, args: List[str]) -> str:
        """Get engine status"""
        try:
            from trading_engine import get_trading_engine
            engine = get_trading_engine()
            
            if engine is None:
                return "\U0001F916 <b>ENGINE STATUS</b>\n\nEngine not initialized.\nUse /start to initialize."
            
            status = engine.get_status()
            
            state_emoji = {
                "INITIALIZING": "\u23F3",
                "READY": "\U0001F7E1",
                "TRADING": "\U0001F7E2",
                "PAUSED": "\U000023F8",
                "STOPPED": "\U0001F534",
                "ERROR": "\U0001F6A8",
            }.get(status.state, "\u26AA")
            
            message = (
                f"{state_emoji} <b>ENGINE STATUS</b>\n\n"
                f"<b>State:</b> {status.state}\n"
                f"<b>Balance:</b> {self._format_price(status.balance)}\n"
                f"<b>Leverage:</b> {status.leverage}x\n"
                f"<b>Symbol:</b> {engine.symbol}\n"
                f"<b>Positions:</b> {status.positions_count}\n"
                f"<b>Total P&L:</b> {self._format_price(status.total_pnl)}\n"
                f"<b>Daily P&L:</b> {status.daily_pnl:+.2f} ({status.daily_pnl_percent:+.2f}%)\n"
                f"<b>Win Rate:</b> {status.win_rate:.1f}%\n"
                f"<b>Total Trades:</b> {status.total_trades}\n"
                f"<b>Can Trade:</b> {'YES' if status.can_trade else 'NO'}\n"
                f"<b>Risk Level:</b> {status.risk_level}\n"
                f"<b>Circuit Breaker:</b> {status.circuit_breaker_state}\n"
                f"<b>Market Regime:</b> {status.current_regime}\n"
                f"<b>Best Strategy:</b> {status.best_strategy}\n"
                f"<b>Kelly Fraction:</b> {status.kelly_fraction:.2%}\n"
                f"<b>VaR (95%):</b> ${status.var_95:.2f} ({status.var_95_percent:.2f}%)\n"
            )
            
            return message
            
        except Exception as e:
            logger.error(f"Error in _get_engine_command: {e}")
            return f"\U0001F6AB <b>Engine unavailable</b>\n\n{str(e)}"
     
    def _get_leverage_command(self, args: List[str]) -> str:
        """Get or set leverage"""
        try:
            from trading_engine import get_trading_engine
            engine = get_trading_engine()
            
            if engine is None:
                return "\U0001F6AB Engine not initialized"
            
            # If args provided, try to set leverage
            if args:
                try:
                    new_leverage = int(args[0])
                    if 1 <= new_leverage <= 125:
                        success = engine.set_leverage(new_leverage)
                        if success:
                            return f"\u26A1 <b>LEVERAGE SET</b>\n\nNew leverage: <b>{new_leverage}x</b>"
                        else:
                            return "\U0001F6AB Failed to set leverage"
                    else:
                        return "\U0001F6AB Leverage must be between 1 and 125"
                except ValueError:
                    return "\U0001F6AB Invalid leverage value"
            
            # Show current leverage
            message = (
                f"\u26A1 <b>LEVERAGE</b>\n\n"
                f"<b>Current:</b> {engine.leverage}x\n"
                f"<b>Symbol:</b> {engine.symbol}\n\n"
                f"Usage: /leverage [number]\n"
                f"Example: /leverage 50"
            )
            
            return message
            
        except Exception as e:
            return f"\U0001F6AB <b>ERROR</b>\n\n{str(e)}"
    
    def _get_kelly_command(self, args: List[str]) -> str:
        """Get Kelly Criterion statistics"""
        try:
            from trading_engine import get_trading_engine
            engine = get_trading_engine()
            
            if engine is None:
                return "\U0001F6AB Engine not initialized"
            
            if engine.kelly_sizer is None:
                message = (
                    f"\U0001F3AF <b>KELLY CRITERION</b>\n\n"
                    f"Kelly sizer not available (risk management not initialized).\n\n"
                    f"<i>Initialize risk management to see Kelly statistics</i>"
                )
            else:
                stats = engine.kelly_sizer.get_statistics()
                
                edge = stats.get('edge', 'NO DATA')
                edge_emoji = {
                    'STRONG': '\U0001F7E2',
                    'MODERATE': '\U0001F7E1',
                    'WEAK': '\U0001F7E0',
                    'NO EDGE': '\U0001F534',
                    'NO DATA': '\u26AA',
                    'INSUFFICIENT DATA': '\u26AA',
                }.get(edge, '\u26AA')
                
                recommended_leverage = engine.kelly_sizer.get_recommended_leverage()
                
                message = (
                    f"\U0001F3AF <b>KELLY CRITERION</b>\n\n"
                    f"<b>Edge:</b> {edge_emoji} {edge}\n"
                    f"<b>Kelly Fraction:</b> {stats.get('kelly_fraction', 0):.2%}\n"
                    f"<b>Optimal (Half):</b> {stats.get('optimal_fraction', 0):.2%}\n"
                    f"<b>Expected Growth:</b> {stats.get('expected_growth', 0):.4f}\n\n"
                    f"<b>Trade Stats:</b>\n"
                    f"  Total: {stats.get('trades_count', 0)}\n"
                    f"  Wins: {stats.get('wins_count', 0)}\n"
                    f"  Losses: {stats.get('losses_count', 0)}\n"
                    f"  Win Rate: {stats.get('win_rate', 0):.1%}\n\n"
                    f"<b>Recommended Leverage:</b> {recommended_leverage}x\n"
                    f"<b>Portfolio Value:</b> {self._format_price(engine.current_balance)}\n"
                )
            
            return message
            
        except Exception as e:
            logger.error(f"Error in _get_kelly_command: {e}")
            return f"\U0001F6AB <b>Kelly unavailable</b>\n\n{str(e)}"
    
    def _get_strategies_command(self, args: List[str]) -> str:
        """Get strategy router status"""
        try:
            from trading_engine import get_trading_engine
            engine = get_trading_engine()
            
            if engine is None:
                return "\U0001F6AB Engine not initialized"
            
            signal_report = engine.get_signal_report()
            
            message = (
                f"\U0001F4CA <b>STRATEGY ROUTER</b>\n\n"
                f"<b>Market Regime:</b> {signal_report['regime']}\n"
                f"<b>Best Strategy:</b> {signal_report['best_strategy']}\n\n"
            )
            
            for name, data in signal_report.get('strategies', {}).items():
                if 'error' in data:
                    message += f"\u2022 <b>{name}:</b> Error\n"
                else:
                    signal = data.get('signal', 'N/A')
                    signal_emoji = {
                        'BUY': '\U0001F4C8',
                        'SELL': '\U0001F4C9',
                        'NEUTRAL': '\u2796',
                    }.get(signal, '\u2753')
                    message += f"{signal_emoji} <b>{name}:</b> {signal}\n"
                    if 'reason' in data:
                        message += f"  {data['reason']}\n"
                    message += "\n"
            
            return message
            
        except Exception as e:
            return f"\U0001F6AB <b>ERROR</b>\n\n{str(e)}"
    
    def _get_signal_command(self, args: List[str]) -> str:
        """Get current trading signal"""
        try:
            from trading_engine import get_trading_engine
            engine = get_trading_engine()
            
            if engine is None:
                return "\U0001F6AB Engine not initialized"
            
            signal_report = engine.get_signal_report()
            status = engine.get_status()
            
            # Determine overall signal
            best = signal_report.get('best_strategy', 'none')
            regime = signal_report.get('regime', 'UNKNOWN')
            
            # Get best strategy's signal
            strategies = signal_report.get('strategies', {})
            best_data = strategies.get(best, {})
            best_signal = best_data.get('signal', 'NEUTRAL')
            best_reason = best_data.get('reason', 'No data')
            
            signal_emoji = {
                'BUY': '\U0001F4C8',
                'SELL': '\U0001F4C9',
                'NEUTRAL': '\u2796',
            }.get(best_signal, '\u2753')
            
            message = (
                f"\U0001F3AF <b>CURRENT SIGNAL</b>\n\n"
                f"<b>Signal:</b> {signal_emoji} {best_signal}\n"
                f"<b>Strategy:</b> {best}\n"
                f"<b>Reason:</b> {best_reason}\n\n"
                f"<b>Market Regime:</b> {regime}\n"
                f"<b>Confidence:</b> {best_data.get('confidence', 0):.1%}\n"
                f"<b>Can Trade:</b> {'YES' if status.can_trade else 'NO'}\n"
                f"<b>Positions:</b> {status.positions_count}\n"
            )
            
            return message
            
        except Exception as e:
            logger.error(f"Error in _get_signal_command: {e}")
            return f"\U0001F6AB <b>Signal unavailable</b>\n\n{str(e)}"
    
    def _get_orders_command(self, args: List[str]) -> str:
        """Get open orders and positions"""
        try:
            from trading_engine import get_trading_engine
            engine = get_trading_engine()
            
            if engine is None:
                return "\U0001F6AB Engine not initialized"
            
            positions = engine.get_positions()
            
            if not positions:
                return (
                    f"\U0001F4CB <b>ORDERS & POSITIONS</b>\n\n"
                    f"No open positions or orders.\n"
                    f"Waiting for signals..."
                )
            
            message = f"\U0001F4CB <b>ORDERS & POSITIONS</b>\n\n"
            
            for symbol, pos in positions.items():
                side = pos['side']
                emoji = "\U0001F4C8" if side == "LONG" else "\U0001F4C9"
                
                message += (
                    f"{emoji} <b>{symbol}</b>\n"
                    f"  Side: {side}\n"
                    f"  Qty: {pos['quantity']:.6f}\n"
                    f"  Entry: {self._format_price(pos['entry_price'])}\n"
                    f"  SL: {self._format_price(pos['stop_loss'])}\n"
                    f"  TP: {self._format_price(pos['take_profit'])}\n"
                    f"  Strategy: {pos['strategy']}\n\n"
                )
            
            # Get order manager stats if available
            if engine.order_manager:
                stats = engine.order_manager.get_statistics()
                message += (
                    f"<b>Order Stats:</b>\n"
                    f"  Total: {stats['total_orders']}\n"
                    f"  Filled: {stats['filled_orders']}\n"
                    f"  Pending: {stats['pending_orders']}\n"
                    f"  Fill Rate: {stats['fill_rate']:.1%}\n"
                )
            
            return message
            
        except Exception as e:
            return f"\U0001F6AB <b>ERROR</b>\n\n{str(e)}"
    
    def _get_var_command(self, args: List[str]) -> str:
        """Get Value at Risk report"""
        try:
            from trading_engine import get_trading_engine
            engine = get_trading_engine()
            
            if engine is None:
                return "\U0001F6AB Engine not initialized"
            
            risk_report = engine.get_risk_report()
            var_data = risk_report.get('var', {})
            
            if not var_data or engine.var_calculator is None:
                message = (
                    f"\U0001F4C8 <b>VALUE AT RISK</b>\n\n"
                    f"Value at Risk calculator not available.\n"
                    f"This may be due to insufficient trading data or risk management not initialized.\n\n"
                    f"<i>Collect more trading data to enable VaR calculation</i>"
                )
            else:
                risk_level = var_data.get('risk_level', 'UNKNOWN')
                risk_emoji = {
                    'LOW': '\U0001F7E2',
                    'MODERATE': '\U0001F7E1',
                    'HIGH': '\U0001F7E0',
                    'CRITICAL': '\U0001F534',
                }.get(risk_level, '\u26AA')
                
                message = (
                    f"\U0001F4C8 <b>VALUE AT RISK</b>\n\n"
                    f"<b>Risk Level:</b> {risk_emoji} {risk_level}\n\n"
                    f"<b>VaR (95%):</b> ${var_data.get('var_95_dollars', 0):.2f}\n"
                    f"  ({var_data.get('var_95_percent', 0):.2f}% of portfolio)\n\n"
                    f"<b>VaR (99%):</b> ${var_data.get('var_99_dollars', 0):.2f}\n"
                    f"  ({var_data.get('var_99_percent', 0):.2f}% of portfolio)\n\n"
                    f"<b>CVaR (95%):</b> ${var_data.get('cvar_95', 0):.2f}\n"
                    f"<b>CVaR (99%):</b> ${var_data.get('cvar_99', 0):.2f}\n\n"
                    f"<b>Max Drawdown:</b> {var_data.get('max_drawdown_percent', 0):.2f}%\n"
                    f"<b>Volatility:</b> {var_data.get('volatility_annualized', 0):.2f}%\n"
                    f"<b>Method:</b> {var_data.get('method', 'N/A')}\n"
                )
            
            return message
            
        except Exception as e:
            logger.error(f"Error in _get_var_command: {e}")
            return f"\U0001F6AB <b>VaR unavailable</b>\n\n{str(e)}"

    def _get_unknown_command(self, command: str) -> str:
        """Handle unknown commands"""
        return (
            f"\U0001F6AB <b>UNKNOWN COMMAND</b>\n\n"
            f"Command /{command} not recognized.\n"
            f"Send /help for available commands."
        )
    
    # ==================== SYSTEM NOTIFICATIONS ====================
    
    def send_startup_message(self) -> bool:
        """Send startup notification"""
        message = (
            f"{TelegramEmoji.ROBOT.value} <b>GOD MODE QUANT ORCHESTRATOR</b>\n\n"
            f"Trading system is now ONLINE\n\n"
            f"Monitoring and alerts active\n"
            f"Use /help for available commands\n\n"
            f"\U0001F4E2 Waiting for trades..."
        )
        
        self._increment_metric(
            self.telegram_messages_sent,
            {"message_type": "system", "status": "sent"}
        )
        
        return self._send_message(message, reply_markup=self._get_inline_keyboard())
    
    def send_shutdown_message(self) -> bool:
        """Send shutdown notification"""
        with self._lock:
            stats = self.daily_stats.copy()
        
        message = (
            f"\U0001F6D1 <b>SYSTEM SHUTDOWN</b>\n\n"
            f"Trading orchestrator is stopping\n\n"
            f"<b>Session Stats:</b>\n"
            f"  Trades: {stats.get('trades', 0)}\n"
            f"  P&L: {self._format_price(stats.get('pnl', 0))}\n\n"
            f"Thank you for using God Mode Quant!"
        )
        
        self._increment_metric(
            self.telegram_messages_sent,
            {"message_type": "system", "status": "sent"}
        )
        
        return self._send_message(message)
    
    def send_error_notification(self, error_message: str, context: Optional[Dict] = None) -> bool:
        """Send error notification"""
        message = (
            f"\U0001F6A8 <b>ERROR NOTIFICATION</b>\n\n"
            f"<b>Error:</b> {error_message}\n"
        )
        
        if context:
            message += "\n<b>Context:</b>\n"
            for key, value in context.items():
                message += f"  \u2022 {key}: {value}\n"
        
        message += f"\n\U000023F0 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        self._increment_metric(
            self.telegram_messages_sent,
            {"message_type": "error", "status": "sent"}
        )
        
        return self._send_message(message, reply_markup=self._get_inline_keyboard())
    
    def send_heartbeat(self, status: str = "running") -> bool:
        """Send heartbeat/status update"""
        from risk_management import risk_manager
        from security.trust_scorer import trust_scorer
        
        portfolio = risk_manager.portfolio
        trust_score = trust_scorer.get_trust_score("orchestrator:system")
        
        pnl = portfolio.total_unrealized_pnl
        pnl_str, _ = self._format_pnl(pnl)
        
        message = (
            f"\U0001F525 <b>HEARTBEAT</b>\n\n"
            f"<b>Status:</b> {status}\n"
            f"<b>Positions:</b> {portfolio.position_count}\n"
            f"<b>P&L:</b> {pnl_str}\n"
            f"<b>Trust:</b> {trust_score:.1f}\n"
            f"\U000023F0 {datetime.now().strftime('%H:%M:%S')}"
        )
        
        return self._send_message(message)
    
    def check_trust_score_change(self, service: str, trust_score: float) -> None:
        """Check and alert on trust score changes"""
        last_score = self.last_trust_score.get(service)
        
        if last_score is not None:
            change = last_score - trust_score
            
            if abs(change) >= 10:
                alert_type = "critical" if trust_score < self.alert_thresholds["trust_score_critical"] else "warning"
                emoji = TelegramEmoji.DANGER.value if alert_type == "critical" else TelegramEmoji.WARNING.value
                
                message = (
                    f"{emoji} <b>TRUST SCORE ALERT</b>\n\n"
                    f"<b>Service:</b> {service}\n"
                    f"<b>Previous:</b> {last_score:.1f}\n"
                    f"<b>Current:</b> {trust_score:.1f}\n"
                    f"<b>Change:</b> {change:+.1f}"
                )
                
                if self._should_send_alert(f"trust_{service}"):
                    self._send_message(message)
                    self.last_alert_time[f"trust_{service}"] = time.time()
        
        self.last_trust_score[service] = trust_score

    # ==================== TRADE NOTIFICATION METHODS ====================

    def send_trade_entry(self, trade: 'TradeNotification') -> bool:
        """Send trade entry notification"""
        side_emoji = TelegramEmoji.LONG.value if trade.side == "LONG" else TelegramEmoji.SHORT.value
        message = (
            f"{side_emoji} <b>TRADE ENTRY</b>\n\n"
            f"<b>Symbol:</b> {trade.symbol}\n"
            f"<b>Side:</b> {trade.side}\n"
            f"<b>Quantity:</b> {trade.quantity:.6f}\n"
            f"<b>Entry:</b> {self._format_price(trade.entry_price)}\n"
        )
        if trade.stop_loss:
            message += f"<b>Stop Loss:</b> {self._format_price(trade.stop_loss)}\n"
        if trade.take_profit:
            message += f"<b>Take Profit:</b> {self._format_price(trade.take_profit)}\n"
        message += f"<b>Strategy:</b> {trade.strategy}\n"
        message += f"\n⏰ {datetime.now().strftime('%H:%M:%S')}"

        self._increment_metric(self.telegram_messages_sent, {"message_type": "trade_entry", "status": "sent"})
        return self._send_message(message)

    def send_trade_exit(self, trade: 'TradeNotification') -> bool:
        """Send trade exit notification"""
        pnl_str, pnl_emoji = self._format_pnl(trade.pnl or 0)
        message = (
            f"{TelegramEmoji.EXIT.value} <b>TRADE EXIT</b>\n\n"
            f"<b>Symbol:</b> {trade.symbol}\n"
            f"<b>Side:</b> {trade.side}\n"
            f"<b>Quantity:</b> {trade.quantity:.6f}\n"
            f"<b>Entry:</b> {self._format_price(trade.entry_price)}\n"
        )
        if trade.current_price:
            message += f"<b>Exit:</b> {self._format_price(trade.current_price)}\n"
        message += f"{pnl_emoji} <b>P&L:</b> {pnl_str}\n"
        if trade.pnl_percent is not None:
            message += f"<b>P&L %:</b> {trade.pnl_percent:+.2f}%\n"
        message += f"\n⏰ {datetime.now().strftime('%H:%M:%S')}"

        self._increment_metric(self.telegram_messages_sent, {"message_type": "trade_exit", "status": "sent"})
        return self._send_message(message)

    def send_risk_alert(self, alert: 'RiskAlertNotification') -> bool:
        """Send risk alert notification"""
        severity_emoji = {
            "LOW": TelegramEmoji.WARNING.value,
            "MEDIUM": TelegramEmoji.WARNING.value,
            "HIGH": TelegramEmoji.DANGER.value,
            "CRITICAL": TelegramEmoji.DANGER.value,
        }.get(alert.severity, TelegramEmoji.WARNING.value)

        message = (
            f"{severity_emoji} <b>RISK ALERT [{alert.severity}]</b>\n\n"
            f"<b>Type:</b> {alert.alert_type}\n"
            f"<b>Message:</b> {alert.message}\n"
        )
        if alert.details:
            message += "\n<b>Details:</b>\n"
            for key, value in alert.details.items():
                message += f"  • {key}: {value}\n"
        message += f"\n⏰ {datetime.now().strftime('%H:%M:%S')}"

        self._increment_metric(self.telegram_messages_sent, {"message_type": "risk_alert", "status": "sent"})
        return self._send_message(message)


# Global dashboard instance
_dashboard_instance: Optional[TelegramDashboard] = None

# Import system monitor
from telegram_system_monitor import (
    SystemArchitectureDisplay,
    SystemMetricsCollector
)

def init_telegram_dashboard(bot_token: str = None, chat_id: str = None) -> TelegramDashboard:
    """Initialize the global Telegram dashboard"""
    global _dashboard_instance
    
    if bot_token is None:
        from security.secrets_manager import get_telegram_bot_token
        bot_token = get_telegram_bot_token() or os.getenv('TELEGRAM_BOT_TOKEN')
    
    if chat_id is None:
        from security.secrets_manager import get_telegram_chat_id
        chat_id = get_telegram_chat_id() or os.getenv('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        raise ValueError("Telegram bot token and chat ID are required")
    
    _dashboard_instance = TelegramDashboard(bot_token, chat_id)
    logger.info("Telegram dashboard initialized")
    
    return _dashboard_instance


def get_telegram_dashboard() -> Optional[TelegramDashboard]:
    """Get the global dashboard instance"""
    return _dashboard_instance


# Convenience functions for common notifications
def send_trade_entry_notification(symbol: str, side: str, quantity: float,
                                 entry_price: float, strategy: str = "unknown",
                                 stop_loss: float = None, take_profit: float = None) -> bool:
    """Send trade entry notification"""
    dashboard = get_telegram_dashboard()
    if dashboard:
        trade = TradeNotification(
            symbol=symbol,
            side=side,
            quantity=quantity,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            strategy=strategy
        )
        return dashboard.send_trade_entry(trade)
    return False


def send_trade_exit_notification(symbol: str, side: str, quantity: float,
                                 entry_price: float, exit_price: float,
                                 pnl: float = None, pnl_percent: float = None) -> bool:
    """Send trade exit notification"""
    dashboard = get_telegram_dashboard()
    if dashboard:
        trade = TradeNotification(
            symbol=symbol,
            side=side,
            quantity=quantity,
            entry_price=entry_price,
            current_price=exit_price,
            pnl=pnl,
            pnl_percent=pnl_percent
        )
        return dashboard.send_trade_exit(trade)
    return False


def send_risk_alert_notification(alert_type: str, severity: str, 
                                message: str, details: Dict = None) -> bool:
    """Send risk alert notification"""
    dashboard = get_telegram_dashboard()
    if dashboard:
        alert = RiskAlertNotification(
            alert_type=alert_type,
            severity=severity,
            message=message,
            details=details or {}
        )
        return dashboard.send_risk_alert(alert)
    return False

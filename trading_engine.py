"""
Trading Engine - God Mode Quant Trading Orchestrator
Main orchestrator connecting all components:
- Exchange Gateway (Binance Futures)
- Strategy Router (Multi-strategy ensemble)
- Risk Management (Kelly, trailing stop, circuit breaker, VaR, volatility sizer)
- Order Manager (Async order execution)
- Position Tracker (Real-time position sync)
- Telegram Dashboard (Real-time notifications)
"""
import os
import time
import logging
import threading
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logging_config import setup_logging

logger = setup_logging('trading_engine')

# Import ML Service
try:
    from ml_service import get_ml_service, initialize_ml_service
    ML_SERVICE_AVAILABLE = True
except ImportError:
    ML_SERVICE_AVAILABLE = False
    logger.warning("ML Service not available. ML predictions will be disabled.")


class EngineState(Enum):
    """Trading engine states"""
    INITIALIZING = "INITIALIZING"
    READY = "READY"
    TRADING = "TRADING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


@dataclass
class TradeSignal:
    """Trade signal from strategy"""
    symbol: str
    side: str  # LONG or SHORT
    strategy: str
    confidence: float
    price: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class EngineStatus:
    """Engine status snapshot"""
    state: str
    balance: float
    positions_count: int
    total_pnl: float
    daily_pnl: float
    daily_pnl_percent: float
    win_rate: float
    total_trades: int
    circuit_breaker_state: str
    can_trade: bool
    current_regime: str
    best_strategy: str
    kelly_fraction: float
    var_95: float
    var_95_percent: float
    risk_level: str
    leverage: int
    timestamp: float = field(default_factory=time.time)


class TradingEngine:
    """
    God Mode Trading Engine
    
    Orchestrates all trading components into a unified system.
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize the Trading Engine
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        
        # Engine state
        self.state = EngineState.INITIALIZING
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        
        # Configuration
        self.symbol = self.config.get('symbol', 'BTCUSDT')
        self.leverage = self.config.get('leverage', 75)
        self.starting_capital = self.config.get('starting_capital', 10.0)
        self.testnet = self.config.get('testnet', True)
        self.trading_interval = self.config.get('trading_interval', 5)  # seconds
        
        # ML Service configuration
        self.ml_enabled = self.config.get('ml_enabled', True) and ML_SERVICE_AVAILABLE
        
        # Components (initialized later)
        self.gateway = None
        self.order_manager = None
        self.position_tracker = None
        self.strategy_router = None
        self.kelly_sizer = None
        self.trailing_stop = None
        self.circuit_breaker = None
        self.volatility_sizer = None
        self.var_calculator = None
        self.dashboard = None
        
        # Trading state
        self.current_balance = self.starting_capital
        self.peak_balance = self.starting_capital
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0.0
        self.daily_pnl = 0.0
        self.trade_pnls: List[float] = []
        self.open_positions: Dict[str, Dict] = {}
        
        # ML Service
        self.ml_service = None
        self.ml_price_history: List[float] = []
        self.ml_volume_history: List[float] = []
        self.max_ml_history = 1000  # Keep last 1000 price/volume points for ML
        
        # Strategies
        self.strategies: Dict[str, Any] = {}
        
        logger.info(f"Trading Engine initialized: {self.symbol}, leverage={self.leverage}, "
                   f"capital=${self.starting_capital}, testnet={self.testnet}")
    
    def initialize(self) -> bool:
        """
        Initialize all components with fault tolerance
        
        Returns:
            True if at least critical components initialized
        """
        logger.info("=" * 60)
        logger.info("  GOD MODE QUANT TRADING ENGINE - INITIALIZING")
        logger.info("=" * 60)
        
        initialized_components = []
        critical_failed = False
        
        # 1. Initialize Exchange Gateway (may fail in demo mode)
        try:
            self._init_gateway()
            initialized_components.append("gateway")
        except Exception as e:
            logger.warning(f"Gateway initialization failed (demo mode?): {e}")
            # Continue without gateway - engine can still provide status
        
        # 2. Initialize Order Manager (requires gateway)
        if self.gateway:
            try:
                self._init_order_manager()
                initialized_components.append("order_manager")
            except Exception as e:
                logger.warning(f"Order manager initialization failed: {e}")
        
        # 3. Initialize Position Tracker (requires gateway)
        if self.gateway:
            try:
                self._init_position_tracker()
                initialized_components.append("position_tracker")
            except Exception as e:
                logger.warning(f"Position tracker initialization failed: {e}")
        
        # 4. Initialize Strategies (no external dependencies)
        try:
            self._init_strategies()
            initialized_components.append("strategies")
        except Exception as e:
            logger.error(f"Strategies initialization failed: {e}")
            critical_failed = True
        
        # 5. Initialize Strategy Router (requires strategies)
        if self.strategies:
            try:
                self._init_strategy_router()
                initialized_components.append("strategy_router")
            except Exception as e:
                logger.warning(f"Strategy router initialization failed: {e}")

        # 6. Initialize ML Service (if enabled)
        if self.ml_enabled:
            try:
                self._init_ml_service()
                initialized_components.append("ml_service")
            except Exception as e:
                logger.warning(f"ML Service initialization failed: {e}")
                # Continue without ML service - not critical

        # 7. Initialize Risk Management (no external dependencies)
        try:
            self._init_risk_management()
            initialized_components.append("risk_management")
        except Exception as e:
            logger.error(f"Risk management initialization failed: {e}")
            critical_failed = True
        
        # 7. Set leverage on exchange (requires gateway)
        if self.gateway:
            try:
                self._configure_exchange()
            except Exception as e:
                logger.warning(f"Exchange configuration failed: {e}")
        
        # 8. Get initial balance (requires gateway)
        if self.gateway:
            try:
                self._sync_balance()
            except Exception as e:
                logger.warning(f"Balance sync failed: {e}")
        
        # 9. Start circuit breaker day (requires risk management)
        if self.circuit_breaker:
            try:
                self.circuit_breaker.start_day(self.current_balance)
            except Exception as e:
                logger.warning(f"Circuit breaker start failed: {e}")
        
        # Determine overall state
        if critical_failed:
            self.state = EngineState.ERROR
            logger.error("Critical components failed to initialize")
            return False
        elif "risk_management" in initialized_components and "strategies" in initialized_components:
            self.state = EngineState.READY
            logger.info("=" * 60)
            logger.info("  ENGINE INITIALIZATION PARTIAL (trading disabled)")
            logger.info(f"  Balance: ${self.current_balance:.2f}")
            logger.info(f"  Leverage: {self.leverage}x")
            logger.info(f"  Strategies: {len(self.strategies)}")
            logger.info(f"  Initialized: {', '.join(initialized_components)}")
            logger.info("=" * 60)
            return True
        else:
            self.state = EngineState.ERROR
            logger.error("Insufficient components initialized")
            return False
    
    def _init_gateway(self):
        """Initialize Binance gateway"""
        from exchange.binance_gateway import BinanceGateway, BinanceConfig
        
        api_key = self.config.get('api_key') or os.getenv('BINANCE_API_KEY', '')
        api_secret = self.config.get('api_secret') or os.getenv('BINANCE_API_SECRET', '')
        
        binance_config = BinanceConfig(
            api_key=api_key,
            api_secret=api_secret,
            testnet=self.testnet
        )
        
        self.gateway = BinanceGateway(binance_config)
        logger.info(f"Gateway initialized (testnet: {self.testnet})")
    
    def _init_order_manager(self):
        """Initialize order manager"""
        from exchange.order_manager import OrderManager
        
        self.order_manager = OrderManager(self.gateway)
        logger.info("Order Manager initialized")
    
    def _init_position_tracker(self):
        """Initialize position tracker"""
        from exchange.position_tracker import PositionTracker
        
        self.position_tracker = PositionTracker(self.gateway)
        logger.info("Position Tracker initialized")
    
    def _init_strategies(self):
        """Initialize all trading strategies"""
        from strategies.rsi_divergence import RSIDivergenceStrategy
        from strategies.bollinger_breakout import BollingerBreakoutStrategy
        from strategies.momentum_surge import MomentumSurgeStrategy
        from strategies.mean_reversion import MeanReversionStrategy
        
        self.strategies = {
            'rsi_divergence': RSIDivergenceStrategy(
                rsi_period=14,
                oversold=30.0,
                overbought=70.0
            ),
            'bollinger': BollingerBreakoutStrategy(
                period=20,
                std_dev=2.0,
                volume_confirmation=True
            ),
            'momentum': MomentumSurgeStrategy(
                lookback_period=14,
                momentum_threshold=0.03,
                volume_threshold=1.5
            ),
            'mean_reversion': MeanReversionStrategy(
                ma_period=20,
                std_dev_multiplier=2.0,
                deviation_threshold=2.0
            ),
        }
        
        logger.info(f"Initialized {len(self.strategies)} strategies")
    
    def _init_strategy_router(self):
        """Initialize strategy router"""
        from strategies.strategy_router import StrategyRouter
        
        self.strategy_router = StrategyRouter(strategies=self.strategies)
        logger.info("Strategy Router initialized")
    
    def _init_risk_management(self):
        """Initialize all risk management components"""
        from risk.kelly_sizing import KellySizer
        from risk.trailing_stop import TrailingStop
        from risk.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
        from risk.volatility_sizer import VolatilitySizer
        from risk.var_calculator import VaRCalculator, VaRMethod
        
        # Kelly Criterion position sizing
        self.kelly_sizer = KellySizer(
            portfolio_value=self.current_balance,
            fraction_cap=0.25,
            use_fraction="optimal"  # Half-Kelly
        )
        
        # Trailing stops
        self.trailing_stop = TrailingStop(
            default_callback_rate=0.5,  # 0.5% trailing
            min_activation_percent=1.0  # 1% profit before activation
        )
        
        # Circuit breaker (3% daily loss limit)
        cb_config = CircuitBreakerConfig(
            daily_loss_limit_percent=3.0,
            warning_threshold_percent=2.0,
            max_trades_per_day=50
        )
        self.circuit_breaker = CircuitBreaker(cb_config)
        
        # Volatility-based position sizing
        self.volatility_sizer = VolatilitySizer(
            base_risk_percent=1.0,
            atr_period=14
        )
        
        # VaR Calculator
        self.var_calculator = VaRCalculator(
            method=VaRMethod.HISTORICAL,
            lookback_period=100
        )
        
        logger.info("Risk management components initialized")

    def _init_ml_service(self):
        """Initialize ML Service for enhanced predictions"""
        try:
            # Prepare ML service config from engine config and environment
            ml_config = {
                'ml_enabled': self.ml_enabled,
                'use_ml_predictions': os.getenv('USE_ML_PREDICTIONS', 'true').lower() == 'true',
                'ml_model_path': os.getenv('ML_MODEL_PATH', './ml_models'),
                'retrain_schedule': os.getenv('RETRAIN_SCHEDULE', 'daily'),
                'ml_confidence_threshold': float(os.getenv('ML_CONFIDENCE_THRESHOLD', '0.6')),
                'ml_model_type': os.getenv('ML_MODEL_TYPE', 'ensemble').lower(),
                # Add any engine-specific ML configs
                'symbol': self.symbol,
                'trading_interval': self.trading_interval
            }
            
            # Initialize ML service
            self.ml_service = initialize_ml_service(ml_config)
            
            if self.ml_service and self.ml_service.is_initialized:
                logger.info("ML Service initialized successfully")
            else:
                logger.warning("ML Service initialized but not fully functional")
                
        except Exception as e:
            logger.error(f"Failed to initialize ML Service: {e}")
            self.ml_service = None
            raise
    
    def _configure_exchange(self):
        """Configure exchange settings (leverage, margin type)"""
        try:
            # Set leverage
            result = self.gateway.set_leverage(self.symbol, self.leverage)
            logger.info(f"Leverage set to {self.leverage}x for {self.symbol}: {result}")
            
            # Set margin type to CROSSED (better for small accounts)
            try:
                self.gateway.set_margin_type(self.symbol, "CROSSED")
                logger.info(f"Margin type set to CROSSED for {self.symbol}")
            except Exception as e:
                logger.info(f"Margin type already set or error: {e}")
                
        except Exception as e:
            logger.warning(f"Failed to configure exchange: {e}")
    
    def _sync_balance(self):
        """Sync balance from exchange"""
        try:
            balance = self.gateway.get_balance("USDT")
            if balance > 0:
                self.current_balance = balance
                logger.info(f"Balance synced: ${balance:.2f}")
            else:
                logger.warning(f"Using starting capital: ${self.starting_capital}")
                self.current_balance = self.starting_capital
        except Exception as e:
            logger.warning(f"Could not sync balance: {e}, using starting capital")
            self.current_balance = self.starting_capital
    
    def start(self):
        """Start the trading engine"""
        if self.state not in [EngineState.READY, EngineState.PAUSED]:
            logger.error(f"Cannot start engine in state: {self.state}")
            return False
        
        self._running = True
        self.state = EngineState.TRADING
        self._thread = threading.Thread(target=self._trading_loop, daemon=True)
        self._thread.start()
        
        logger.info("Trading engine STARTED")
        
        # Notify dashboard
        if self.dashboard:
            try:
                self.dashboard.send_startup_message()
            except Exception:
                pass
        
        return True
    
    def stop(self):
        """Stop the trading engine"""
        self._running = False
        self.state = EngineState.STOPPED
        
        logger.info("Trading engine STOPPED")
        
        # Notify dashboard
        if self.dashboard:
            try:
                self.dashboard.send_shutdown_message()
            except Exception:
                pass
    
    def pause(self):
        """Pause trading (keep monitoring)"""
        self.state = EngineState.PAUSED
        logger.info("Trading engine PAUSED")
    
    def resume(self):
        """Resume trading"""
        if self.state == EngineState.PAUSED:
            self.state = EngineState.TRADING
            logger.info("Trading engine RESUMED")
    
    def _trading_loop(self):
        """Main trading loop"""
        logger.info("Trading loop started")
        
        while self._running:
            try:
                if self.state == EngineState.TRADING:
                    self._execute_trading_cycle()
                
                time.sleep(self.trading_interval)
                
            except Exception as e:
                logger.error(f"Trading loop error: {e}")
                time.sleep(self.trading_interval)
    
    def _execute_trading_cycle(self):
        """Execute one trading cycle"""
        
        # 1. Check circuit breaker
        can_trade, reason = self.circuit_breaker.can_trade()
        if not can_trade:
            logger.debug(f"Circuit breaker blocking trade: {reason}")
            return
         
        # 2. Get current price
        try:
            if self.gateway is None:
                logger.debug("Gateway not available, skipping price fetch")
                return
            
            ticker = self.gateway.get_ticker(self.symbol)
            current_price = float(ticker.get('lastPrice', 0))
             
            if current_price <= 0:
                logger.warning("Invalid price received")
                return
                 
        except Exception as e:
            logger.error(f"Failed to get price: {e}")
            return
         
        # 3. Update strategies with current price
        volume = float(ticker.get('volume', 0))
         
        # 3.5. Update ML history buffers
        self.ml_price_history.append(current_price)
        self.ml_volume_history.append(volume)
        # Maintain buffer size
        if len(self.ml_price_history) > self.max_ml_history:
            self.ml_price_history.pop(0)
            self.ml_volume_history.pop(0)
         
        # 4. Update strategy router and get best strategy
        router_result = self.strategy_router.update(current_price, volume)
         
        # 5. Get signals from all strategies
        signals = self._collect_signals(current_price, volume)
         
        # 6. Execute trades based on signals
        if signals:
            self._process_signals(signals, current_price)
         
        # 7. Update existing positions (trailing stops)
        self._update_positions(current_price)
         
        # 8. Update risk metrics
        self._update_risk_metrics(current_price)
         
        # 9. Sync with exchange periodically
        if self.total_trades % 10 == 0:
            self._sync_positions()
    
    def _collect_signals(self, price: float, volume: float) -> List[TradeSignal]:
        """Collect signals from all strategies"""
        signals = []
        
        for name, strategy in self.strategies.items():
            try:
                if hasattr(strategy, 'update'):
                    signal = strategy.update(price, volume)
                elif hasattr(strategy, 'get_signal'):
                    signal, _ = strategy.get_signal()
                else:
                    continue
                
                signal_str = signal.value if hasattr(signal, 'value') else str(signal)
                
                if signal_str in ['BUY', 'SELL']:
                    # Get confidence from router
                    confidence = 0.5
                    if self.strategy_router._last_result:
                        for score in self.strategy_router._last_result.scores:
                            if score.strategy_name == name:
                                confidence = score.confidence
                                break
                    
                    signals.append(TradeSignal(
                        symbol=self.symbol,
                        side="LONG" if signal_str == "BUY" else "SHORT",
                        strategy=name,
                        confidence=confidence,
                        price=price
                    ))
                    
            except Exception as e:
                logger.warning(f"Error getting signal from {name}: {e}")
        
        return signals
    
    def _process_signals(self, signals: List[TradeSignal], current_price: float):
        """Process trade signals and execute trades"""
        
        # Only trade if we don't already have a position
        if self.symbol in self.open_positions:
            return
         
        # Find the strongest signal
        best_signal = max(signals, key=lambda s: s.confidence)
         
        # Enhance signal with ML prediction if available and sufficient data
        ml_confidence = 0.0
        ml_agreement = False
        if (self.ml_service and self.ml_service.is_initialized and 
            len(self.ml_price_history) >= 50 and self.ml_enabled):
            
            try:
                ml_prediction = self.ml_service.get_ml_prediction(
                    np.array(self.ml_price_history),
                    np.array(self.ml_volume_history)
                )
                
                ml_confidence = ml_prediction.get('confidence', 0)
                ml_signal_val = ml_prediction.get('signal', 0)
                
                if ml_confidence > 0.6:  # ML confident enough to consider
                    if ml_signal_val != 0:  # ML has directional signal
                        ml_direction = "LONG" if ml_signal_val > 0 else "SHORT"
                        if ml_direction == best_signal.side:
                            # ML agrees - boost confidence
                            original_confidence = best_signal.confidence
                            best_signal.confidence = min(1.0, best_signal.confidence + 0.2)
                            ml_agreement = True
                            logger.debug(f"ML agreement boosted confidence from {original_confidence:.2f} to {best_signal.confidence:.2f}")
                        else:
                            # ML disagrees - reduce confidence
                            original_confidence = best_signal.confidence
                            best_signal.confidence *= 0.5
                            logger.debug(f"ML disagreement reduced confidence from {original_confidence:.2f} to {best_signal.confidence:.2f}")
                    else:
                        # ML uncertain - slight confidence reduction
                        original_confidence = best_signal.confidence
                        best_signal.confidence *= 0.9
                        logger.debug(f"ML uncertainty reduced confidence from {original_confidence:.2f} to {best_signal.confidence:.2f}")
                        
            except Exception as e:
                logger.warning(f"ML prediction failed: {e}")
                # Continue with original signal
         
        # Require minimum confidence (after potential ML adjustment)
        if best_signal.confidence < 0.5:
            logger.debug(f"Signal confidence too low after ML adjustment: {best_signal.confidence:.2f}")
            return
         
        # Calculate position size using Kelly
        stop_loss_pct = 1.5  # 1.5% stop loss
         
        if best_signal.side == "LONG":
            stop_loss_price = current_price * (1 - stop_loss_pct / 100)
        else:
            stop_loss_price = current_price * (1 + stop_loss_pct / 100)
         
        # Use Kelly for position sizing
        quantity = self.kelly_sizer.calculate_position_size(
            entry_price=current_price,
            stop_loss_price=stop_loss_price,
            win_rate=None,  # Will use historical trades
            avg_win=None,
            avg_loss=None
        )
         
        # Apply leverage
        quantity = quantity * self.leverage
         
        # Apply volatility adjustment
        if self.gateway is None:
            logger.debug("Gateway not available, skipping volatility adjustment")
        else:
            try:
                klines = self.gateway.get_klines(self.symbol, interval="1m", limit=20)
                if klines and len(klines) > 0:
                    last_kline = klines[-1]
                    high = float(last_kline[2])
                    low = float(last_kline[3])
                    close = float(last_kline[4])
                      
                    vol_metrics = self.volatility_sizer.update(high, low, close)
                      
                    # Reduce size in extreme volatility
                    if vol_metrics.volatility_regime == "EXTREME":
                        quantity *= 0.25
                        logger.warning("Extreme volatility - reducing position to 25%")
                    elif vol_metrics.volatility_regime == "HIGH":
                        quantity *= 0.5
                        logger.warning("High volatility - reducing position to 50%")
            except Exception:
                pass
         
        # Check minimum quantity
        if self.gateway is None:
            logger.debug("Gateway not available, skipping quantity checks")
        else:
            min_qty = self.gateway.get_min_quantity(self.symbol)
            if quantity < min_qty:
                logger.debug(f"Position size too small: {quantity:.6f} < {min_qty}")
                return
         
        # Round quantity to exchange precision
        if self.gateway is not None:
            precision = self.gateway.get_quantity_precision(self.symbol)
            quantity = round(quantity, precision)
         
        # Execute trade
        self._execute_trade(best_signal, quantity, current_price, stop_loss_price)
    
    def _execute_trade(self, signal: TradeSignal, quantity: float, 
                       entry_price: float, stop_loss_price: float):
        """Execute a trade"""
        from exchange.binance_gateway import OrderSide, OrderType
        
        try:
            if self.gateway is None:
                logger.warning("Cannot execute trade: gateway not available")
                return
            
            if quantity <= 0:
                logger.warning(f"Invalid quantity: {quantity}")
                return
            
            # Place market order
            side = OrderSide.BUY if signal.side == "LONG" else OrderSide.SELL
            
            result = self.gateway.place_market_order(
                symbol=signal.symbol,
                side=side,
                quantity=quantity
            )
            
            if result.get('orderId'):
                logger.info(f"Trade executed: {signal.side} {quantity} {signal.symbol} "
                           f"@ ${entry_price:.2f} (strategy: {signal.strategy})")
                
                # Track position
                take_profit_price = entry_price * (1 + 4.0 / 100) if signal.side == "LONG" \
                    else entry_price * (1 - 4.0 / 100)
                
                self.open_positions[signal.symbol] = {
                    'side': signal.side,
                    'quantity': quantity,
                    'entry_price': entry_price,
                    'stop_loss': stop_loss_price,
                    'take_profit': take_profit_price,
                    'strategy': signal.strategy,
                    'timestamp': time.time(),
                }
                
                # Create trailing stop
                self.trailing_stop.create_trailing_stop(
                    order_id=f"trade_{self.total_trades}",
                    symbol=signal.symbol,
                    side=signal.side,
                    quantity=quantity,
                    entry_price=entry_price,
                    callback_rate=0.5,
                    activation_percent=1.0
                )
                
                self.total_trades += 1
                
                # Notify dashboard
                if self.dashboard:
                    try:
                        from telegram_dashboard import TradeNotification
                        trade = TradeNotification(
                            symbol=signal.symbol,
                            side=signal.side,
                            quantity=quantity,
                            entry_price=entry_price,
                            stop_loss=stop_loss_price,
                            take_profit=take_profit_price,
                            strategy=signal.strategy
                        )
                        self.dashboard.send_trade_entry(trade)
                    except Exception:
                        pass
                        
        except Exception as e:
            logger.error(f"Trade execution failed: {e}", exc_info=True)
    
    def _update_positions(self, current_price: float):
        """Update existing positions (check stops, take profits)"""
        if self.symbol not in self.open_positions:
            return
        
        pos = self.open_positions[self.symbol]
        
        # Update trailing stop
        triggered = self.trailing_stop.update_trailing_stop(
            f"trade_{self.total_trades - 1}",
            current_price
        )
        
        if triggered:
            self._close_position(current_price, "trailing_stop")
            return
        
        # Check take profit
        if pos['side'] == "LONG" and current_price >= pos['take_profit']:
            self._close_position(current_price, "take_profit")
        elif pos['side'] == "SHORT" and current_price <= pos['take_profit']:
            self._close_position(current_price, "take_profit")
        
        # Check stop loss
        if pos['side'] == "LONG" and current_price <= pos['stop_loss']:
            self._close_position(current_price, "stop_loss")
        elif pos['side'] == "SHORT" and current_price >= pos['stop_loss']:
            self._close_position(current_price, "stop_loss")
    
    def _close_position(self, exit_price: float, reason: str):
        """Close a position"""
        if self.symbol not in self.open_positions:
            return
        
        from exchange.binance_gateway import OrderSide
        
        pos = self.open_positions[self.symbol]
        
        try:
            if self.gateway is None:
                logger.warning("Cannot close position: gateway not available")
                # Still update local tracking even without exchange
                self._close_position_local(exit_price, reason, pos)
                return
            
            # Close position on exchange
            close_side = OrderSide.SELL if pos['side'] == "LONG" else OrderSide.BUY
            result = self.gateway.place_market_order(
                symbol=self.symbol,
                side=close_side,
                quantity=pos['quantity'],
                reduce_only=True
            )
            
            # Close position locally
            self._close_position_local(exit_price, reason, pos)
            
        except Exception as e:
            logger.error(f"Failed to close position: {e}", exc_info=True)
            # Try to close locally anyway
            try:
                self._close_position_local(exit_price, reason, pos)
            except Exception as local_error:
                logger.error(f"Failed to close position locally: {local_error}")
    
    def _close_position_local(self, exit_price: float, reason: str, pos: Dict):
        """Close position locally (update stats without exchange call)"""
        try:
            # Calculate PnL
            if pos['side'] == "LONG":
                pnl = (exit_price - pos['entry_price']) * pos['quantity']
                pnl_percent = (exit_price - pos['entry_price']) / pos['entry_price'] * 100
            else:
                pnl = (pos['entry_price'] - exit_price) * pos['quantity']
                pnl_percent = (pos['entry_price'] - exit_price) / pos['entry_price'] * 100
            
            # Apply leverage to PnL
            pnl *= self.leverage
            
            # Update stats
            self.total_pnl += pnl
            self.daily_pnl += pnl
            self.current_balance += pnl
            self.trade_pnls.append(pnl)
            
            if pnl > 0:
                self.winning_trades += 1
            else:
                self.losing_trades += 1
            
            # Record in circuit breaker
            self.circuit_breaker.record_trade(pnl)
            
            # Record in Kelly sizer
            self.kelly_sizer.add_trade(pnl)
            self.kelly_sizer.update_portfolio_value(self.current_balance)
            
            # Record in VaR calculator
            self.var_calculator.add_return(pnl / self.current_balance if self.current_balance > 0 else 0)
            self.var_calculator.add_portfolio_value(self.current_balance)
            
            # Track peak
            if self.current_balance > self.peak_balance:
                self.peak_balance = self.current_balance
            
            logger.info(f"Position closed: {pos['side']} {self.symbol} "
                       f"PnL: ${pnl:.2f} ({pnl_percent:+.2f}%) [{reason}]")
            
            # Notify dashboard
            if self.dashboard:
                try:
                    from telegram_dashboard import TradeNotification
                    trade = TradeNotification(
                        symbol=self.symbol,
                        side=pos['side'],
                        quantity=pos['quantity'],
                        entry_price=pos['entry_price'],
                        current_price=exit_price,
                        pnl=pnl,
                        pnl_percent=pnl_percent
                    )
                    self.dashboard.send_trade_exit(trade)
                except Exception:
                    pass
            
            # Remove position
            del self.open_positions[self.symbol]
            
        except Exception as e:
            logger.error(f"Failed to close position locally: {e}", exc_info=True)
    
    def _update_risk_metrics(self, current_price: float):
        """Update all risk metrics"""
        # Add price to VaR calculator
        self.var_calculator.add_price(self.symbol, current_price)
        
        # Update circuit breaker balance
        self.circuit_breaker.update_balance(self.current_balance)
    
    def _sync_positions(self):
        """Sync positions with exchange"""
        try:
            positions = self.position_tracker.sync_positions()
            logger.debug(f"Synced {len(positions)} positions with exchange")
        except Exception as e:
            logger.warning(f"Position sync failed: {e}")
    
    # ==================== PUBLIC API ====================
    
    def get_status(self) -> EngineStatus:
        """Get engine status with safe defaults for missing components"""
        win_rate = (self.winning_trades / max(1, self.winning_trades + self.losing_trades)) * 100
        
        daily_pnl_percent = 0
        if self.circuit_breaker and self.circuit_breaker.starting_balance > 0:
            daily_pnl_percent = (self.daily_pnl / self.circuit_breaker.starting_balance) * 100
        
        # Get Kelly stats
        kelly_fraction = 0
        if self.kelly_sizer:
            try:
                kelly_stats = self.kelly_sizer.get_statistics()
                kelly_fraction = kelly_stats.get('kelly_fraction', 0)
            except Exception:
                pass
        
        # Get VaR
        var_95 = 0
        var_95_percent = 0
        risk_level = "UNKNOWN"
        if self.var_calculator:
            try:
                if len(self.var_calculator._returns) >= 10:
                    var_result = self.var_calculator.calculate_full_var(self.current_balance)
                    var_95 = var_result.var_95
                    var_95_percent = (var_95 / self.current_balance * 100) if self.current_balance > 0 else 0
                    risk_level, _ = self.var_calculator.get_risk_level(self.current_balance)
            except Exception:
                pass
        
        # Get strategy info
        regime = "UNKNOWN"
        best_strategy = "none"
        if self.strategy_router:
            try:
                regime = self.strategy_router.get_regime().value
                best_strategy = self.strategy_router.get_best_strategy()
            except Exception:
                pass
        
        can_trade = False
        circuit_breaker_state = "UNKNOWN"
        if self.circuit_breaker:
            try:
                can_trade, _ = self.circuit_breaker.can_trade()
                circuit_breaker_state = self.circuit_breaker.state.value
            except Exception:
                pass
        
        return EngineStatus(
            state=self.state.value,
            balance=self.current_balance,
            positions_count=len(self.open_positions),
            total_pnl=self.total_pnl,
            daily_pnl=self.daily_pnl,
            daily_pnl_percent=daily_pnl_percent,
            win_rate=win_rate,
            total_trades=self.total_trades,
            circuit_breaker_state=circuit_breaker_state,
            can_trade=can_trade,
            current_regime=regime,
            best_strategy=best_strategy,
            kelly_fraction=kelly_fraction,
            var_95=var_95,
            var_95_percent=var_95_percent,
            risk_level=risk_level,
            leverage=self.leverage
        )
    
    def get_positions(self) -> Dict:
        """Get open positions"""
        return self.open_positions.copy()
    
    def get_trade_history(self) -> List[float]:
        """Get trade PnL history"""
        return self.trade_pnls.copy()
    
    def get_risk_report(self) -> Dict:
        """Get comprehensive risk report with safe defaults"""
        status = self.get_status()
        
        # Kelly stats
        kelly_stats = {}
        if self.kelly_sizer:
            try:
                kelly_stats = self.kelly_sizer.get_statistics()
            except Exception:
                pass
        
        # VaR report
        var_report = {}
        if self.var_calculator:
            try:
                if len(self.var_calculator._returns) >= 10:
                    var_report = self.var_calculator.get_risk_report(self.current_balance)
            except Exception:
                pass
        
        # Circuit breaker
        cb_status = {}
        if self.circuit_breaker:
            try:
                cb_status = self.circuit_breaker.get_status()
            except Exception:
                pass
        
        # Trailing stops
        ts_stats = {}
        if self.trailing_stop:
            try:
                ts_stats = self.trailing_stop.get_statistics()
            except Exception:
                pass
        
        # Volatility
        vol_stats = {}
        if self.volatility_sizer:
            try:
                vol_stats = self.volatility_sizer.get_statistics()
            except Exception:
                pass
        
        return {
            'engine_state': status.state,
            'balance': status.balance,
            'total_pnl': status.total_pnl,
            'daily_pnl': status.daily_pnl,
            'daily_pnl_percent': status.daily_pnl_percent,
            'win_rate': status.win_rate,
            'total_trades': status.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'open_positions': len(self.open_positions),
            'leverage': self.leverage,
            'kelly': kelly_stats,
            'var': var_report,
            'circuit_breaker': cb_status,
            'trailing_stops': ts_stats,
            'volatility': vol_stats,
            'regime': status.current_regime,
            'best_strategy': status.best_strategy,
        }
    
    def get_signal_report(self) -> Dict:
        """Get current signal report from all strategies"""
        report = {
            'regime': self.strategy_router.get_regime().value if self.strategy_router else 'UNKNOWN',
            'best_strategy': self.strategy_router.get_best_strategy() if self.strategy_router else 'none',
            'strategies': {}
        }
        
        for name, strategy in self.strategies.items():
            try:
                if hasattr(strategy, 'get_statistics'):
                    report['strategies'][name] = strategy.get_statistics()
                elif hasattr(strategy, 'get_signal'):
                    signal, reason = strategy.get_signal()
                    report['strategies'][name] = {
                        'signal': signal.value if hasattr(signal, 'value') else str(signal),
                        'reason': reason
                    }
            except Exception as e:
                report['strategies'][name] = {'error': str(e)}
        
        return report
    
    def force_close_all(self):
        """Force close all positions (emergency)"""
        logger.warning("FORCE CLOSING ALL POSITIONS")
        
        for symbol in list(self.open_positions.keys()):
            try:
                pos = self.open_positions[symbol]
                from exchange.binance_gateway import OrderSide
                close_side = OrderSide.SELL if pos['side'] == "LONG" else OrderSide.BUY
                self.gateway.place_market_order(
                    symbol=symbol,
                    side=close_side,
                    quantity=pos['quantity'],
                    reduce_only=True
                )
                del self.open_positions[symbol]
                logger.info(f"Force closed: {symbol}")
            except Exception as e:
                logger.error(f"Failed to force close {symbol}: {e}")
    
    def set_leverage(self, leverage: int) -> bool:
        """Set trading leverage"""
        if self.gateway:
            try:
                self.gateway.set_leverage(self.symbol, leverage)
                self.leverage = leverage
                logger.info(f"Leverage changed to {leverage}x")
                return True
            except Exception as e:
                logger.error(f"Failed to set leverage on exchange: {e}")
                # Still update internal leverage for demo mode
                self.leverage = leverage
                logger.info(f"Internal leverage updated to {leverage}x (exchange update failed)")
                return True
        else:
            # No gateway, just update internal value
            self.leverage = leverage
            logger.info(f"Leverage changed to {leverage}x (demo mode)")
            return True


# Global engine instance
_engine: Optional[TradingEngine] = None


def get_trading_engine() -> Optional[TradingEngine]:
    """Get the global trading engine instance"""
    return _engine


def create_trading_engine(config: Dict = None) -> TradingEngine:
    """Create and initialize the trading engine"""
    global _engine
    _engine = TradingEngine(config)
    return _engine

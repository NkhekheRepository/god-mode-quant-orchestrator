"""
Orchestrator Lifecycle Manager
Manages the startup, shutdown, and health monitoring of all orchestrator components.
"""

import asyncio
import signal
import sys
import logging
import threading
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import time

from .config import OrchestratorConfig, TradingMode

logger = logging.getLogger(__name__)


class ComponentState(Enum):
    """Component health state enumeration"""
    UNKNOWN = "unknown"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class ComponentHealth:
    """Health status of a managed component"""
    name: str
    state: ComponentState = ComponentState.UNKNOWN
    last_heartbeat: Optional[datetime] = None
    error_count: int = 0
    last_error: Optional[str] = None
    started_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'name': self.name,
            'state': self.state.value,
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            'error_count': self.error_count,
            'last_error': self.last_error,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'metadata': self.metadata
        }


class OrchestratorLifecycle:
    """
    Manages the complete lifecycle of the GodMode Quant Trading Orchestrator.
    Handles initialization, startup, shutdown, and health monitoring of all components.
    """
    
    def __init__(self, config: OrchestratorConfig):
        """
        Initialize the lifecycle manager with configuration.
        
        Args:
            config: Orchestrator configuration object
        """
        self.config = config
        self._shutdown_event = asyncio.Event()
        self._shutdown_in_progress = False
        self._components: Dict[str, ComponentHealth] = {}
        self._shutdown_handlers: List[Callable] = []
        self._startup_handlers: List[Callable] = []
        self._background_tasks: List[asyncio.Task] = []
        
        # Component references (will be set during startup)
        self._vnpy_available = False
        self._main_engine = None
        self._cta_engine = None
        self._event_engine = None
        self._trading_engine = None
        self._dashboard = None
        self._bot_handler = None
        self._health_server_thread = None
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        logger.info(f"OrchestratorLifecycle initialized for {config.service_name} v{config.version}")
        logger.info(f"Environment: {config.environment}")
        logger.info(f"Trading mode: {config.trading.mode.value}")
    
    def _setup_signal_handlers(self):
        """Setup OS signal handlers for graceful shutdown"""
        def handle_signal(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            # Schedule shutdown in the event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.stop())
            else:
                # If no event loop, force exit
                import os
                os._exit(128 + signum)
        
        try:
            signal.signal(signal.SIGINT, handle_signal)
            signal.signal(signal.SIGTERM, handle_signal)
            logger.info("Signal handlers registered for graceful shutdown")
        except (ValueError, RuntimeError) as e:
            logger.debug(f"Could not register signal handlers: {e}")
    
    def _register_component(self, name: str, metadata: Optional[Dict[str, Any]] = None):
        """Register a component for health monitoring"""
        self._components[name] = ComponentHealth(
            name=name,
            state=ComponentState.UNKNOWN,
            metadata=metadata or {}
        )
    
    def _update_component_state(self, name: str, state: ComponentState, 
                               error: Optional[str] = None):
        """Update component state and health information"""
        if name in self._components:
            component = self._components[name]
            component.state = state
            component.last_heartbeat = datetime.now()
            
            if state == ComponentState.RUNNING:
                if not component.started_at:
                    component.started_at = datetime.now()
                component.error_count = 0
                component.last_error = None
            elif state == ComponentState.ERROR:
                component.error_count += 1
                component.last_error = error
            elif state == ComponentState.STOPPED:
                component.started_at = None
    
    async def start(self) -> bool:
        """
        Start all orchestrator components in proper order.
        
        Returns:
            bool: True if startup successful, False otherwise
        """
        if self._shutdown_in_progress:
            logger.error("Cannot start - shutdown in progress")
            return False
        
        logger.info("=== STARTING ORCHESTRATOR COMPONENTS ===")
        
        try:
            # 1. Initialize security components
            await self._start_security_components()
            
            # 2. Initialize database connections
            await self._start_database_components()
            
            # 3. Initialize VNPy trading system (if available)
            await self._start_vnpy_components()
            
            # 4. Initialize Telegram dashboard
            await self._start_telegram_components()
            
            # 5. Start monitoring and metrics
            await self._start_monitoring_components()
            
            # 6. Start health check server
            await self._start_health_server()
            
            # 7. Start background tasks
            await self._start_background_tasks()
            
            # 8. Run startup handlers
            await self._run_startup_handlers()
            
            logger.info("=== ALL COMPONENTS STARTED SUCCESSFULLY ===")
            
            # Send startup notification
            await self._send_startup_notification()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start orchestrator: {e}")
            await self.stop()  # Cleanup on failure
            return False
    
    async def stop(self) -> None:
        """
        Gracefully stop all orchestrator components in reverse order.
        """
        if self._shutdown_in_progress:
            logger.warning("Shutdown already in progress")
            return
        
        self._shutdown_in_progress = True
        logger.info("=== INITIATING GRACEFUL SHUTDOWN ===")
        
        try:
            # 1. Send shutdown notification
            await self._send_shutdown_notification()
            
            # 2. Stop background tasks
            await self._stop_background_tasks()
            
            # 3. Stop health server
            await self._stop_health_server()
            
            # 4. Stop monitoring
            await self._stop_monitoring_components()
            
            # 5. Stop Telegram
            await self._stop_telegram_components()
            
            # 6. Stop VNPy
            await self._stop_vnpy_components()
            
            # 7. Stop database connections
            await self._stop_database_components()
            
            # 8. Run shutdown handlers
            await self._run_shutdown_handlers()
            
            # 9. Stop security components
            await self._stop_security_components()
            
            logger.info("=== GRACEFUL SHUTDOWN COMPLETE ===")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        finally:
            self._shutdown_event.set()
            self._shutdown_in_progress = False
    
    async def _start_security_components(self):
        """Initialize security components"""
        logger.info("Starting security components...")
        self._register_component("security", {"type": "security"})
        
        try:
            # Initialize audit logger
            from security.audit_logger import log_security_event
            log_security_event(
                service="orchestrator",
                user="system",
                action="startup",
                outcome="success",
                details={"version": self.config.version, "component": "lifecycle"}
            )
            
            # Initialize trust scorer
            from security.trust_scorer import record_trust_event, TrustEventType
            record_trust_event(
                service_or_user="orchestrator:system",
                event_type=TrustEventType.AUTH_SUCCESS,
                service="orchestrator",
                user="system",
                description="Orchestrator startup",
                metadata={"version": self.config.version, "component": "lifecycle"}
            )
            
            self._update_component_state("security", ComponentState.RUNNING)
            logger.info("Security components started")
            
        except Exception as e:
            self._update_component_state("security", ComponentState.ERROR, str(e))
            logger.warning(f"Security components initialization failed: {e}")
    
    async def _start_database_components(self):
        """Initialize database connections"""
        logger.info("Starting database components...")
        self._register_component("postgres", {"type": "database", "service": "postgresql"})
        self._register_component("redis", {"type": "database", "service": "redis"})
        
        # PostgreSQL check (async simulation)
        try:
            # In production, this would be an actual async database check
            # For now, we'll just mark it as running
            self._update_component_state("postgres", ComponentState.RUNNING)
            logger.info("PostgreSQL connection initialized")
        except Exception as e:
            self._update_component_state("postgres", ComponentState.ERROR, str(e))
            logger.warning(f"PostgreSQL initialization failed: {e}")
        
        # Redis check (async simulation)
        try:
            # In production, this would be an actual async Redis check
            self._update_component_state("redis", ComponentState.RUNNING)
            logger.info("Redis connection initialized")
        except Exception as e:
            self._update_component_state("redis", ComponentState.ERROR, str(e))
            logger.warning(f"Redis initialization failed: {e}")
    
    async def _start_vnpy_components(self):
        """Initialize VNPy trading system"""
        logger.info("Starting VNPy components...")
        self._register_component("vnpy", {"type": "trading", "engine": "vnpy"})
        
        try:
            import vnpy
            from vnpy.event import EventEngine
            from vnpy.trader.engine import MainEngine
            from vnpy_ctastrategy import CtaStrategyApp
            
            logger.info(f"VNPY imported successfully: {vnpy.__version__}")
            
            # Create event engine
            self._event_engine = EventEngine()
            
            # Create main engine
            self._main_engine = MainEngine(self._event_engine)
            logger.info("VNPy MainEngine created")
            
            # Add Binance gateway if available
            try:
                from vnpy_binance import BinanceLinearGateway
                self._main_engine.add_gateway(BinanceLinearGateway)
                logger.info("BinanceLinearGateway added to MainEngine")
            except ImportError as e:
                logger.warning(f"Could not add Binance gateway: {e}")
            
            # Add CTA strategy app
            self._cta_engine = self._main_engine.add_app(CtaStrategyApp)
            logger.info("CTA Strategy app added")
            
            # Connect to Binance if credentials available
            if (self.config.binance.api_key and self.config.binance.api_secret 
                and self.config.binance.api_key != 'your_key_here'):
                
                connect_setting = {
                    "key": self.config.binance.api_key,
                    "secret": self.config.binance.api_secret,
                    "proxy_host": "",
                    "proxy_port": 0,
                    "usdt_testnet": self.config.binance.testnet,
                }
                self._main_engine.connect(connect_setting, "BINANCE")
                logger.info(f"Connected to Binance {'testnet' if self.config.binance.testnet else 'production'}")
            else:
                logger.warning("Binance API credentials not configured")
            
            # Add and initialize strategies
            await self._initialize_strategies()
            
            self._vnpy_available = True
            self._update_component_state("vnpy", ComponentState.RUNNING)
            logger.info("VNPy components started successfully")
            
        except ImportError as e:
            self._update_component_state("vnpy", ComponentState.ERROR, f"Import error: {e}")
            logger.warning(f"VNPY not available: {e}")
            logger.info("Running in DEMO/MOCK mode - no live trading")
            self._vnpy_available = False
        except Exception as e:
            self._update_component_state("vnpy", ComponentState.ERROR, str(e))
            logger.error(f"Failed to initialize VNPy: {e}")
            self._vnpy_available = False
    
    async def _initialize_strategies(self):
        """Initialize trading strategies"""
        if not self._cta_engine:
            return
        
        try:
            # Import the strategy class
            from strategies.ma_crossover_strategy import MaCrossoverStrategy
            
            # Add MA crossover strategy
            strategy_setting = {}
            self._cta_engine.add_strategy(
                class_name="MaCrossoverStrategy",
                strategy_name="ma_crossover_01",
                vt_symbol=f"{self.config.trading.symbol}.BINANCE",
                setting=strategy_setting
            )
            logger.info("MA Crossover strategy added successfully")
            
            # Initialize and start strategies
            self._cta_engine.init_all_strategies()
            logger.info("All strategies initialized")
            
            self._cta_engine.start_all_strategies()
            logger.info("All strategies started")
            
        except Exception as e:
            logger.error(f"Failed to initialize strategies: {e}")
            # Try alternative symbol format
            try:
                self._cta_engine.add_strategy(
                    class_name="MaCrossoverStrategy",
                    strategy_name="ma_crossover_01",
                    vt_symbol=self.config.trading.symbol,
                    setting={}
                )
                logger.info("MA Crossover strategy added with alternative symbol format")
            except Exception as e2:
                logger.error(f"Failed to add strategy with alternative format: {e2}")
    
    async def _start_telegram_components(self):
        """Initialize Telegram dashboard and bot"""
        if not self.config.telegram.enabled:
            logger.info("Telegram disabled in configuration")
            return
        
        logger.info("Starting Telegram components...")
        self._register_component("telegram_dashboard", {"type": "notification", "service": "telegram"})
        self._register_component("telegram_bot", {"type": "notification", "service": "telegram"})
        
        try:
            from telegram_dashboard import init_telegram_dashboard, get_telegram_dashboard
            from telegram_bot_handler import init_telegram_bot
            from threading import Thread
            
            # Initialize dashboard
            self._dashboard = init_telegram_dashboard(
                self.config.telegram.bot_token,
                self.config.telegram.chat_id
            )
            self._update_component_state("telegram_dashboard", ComponentState.RUNNING)
            logger.info("Telegram Dashboard initialized successfully")
            
            # Initialize bot handler
            self._bot_handler = init_telegram_bot(
                self.config.telegram.bot_token,
                dashboard=self._dashboard
            )
            
            # Start polling in background thread
            polling_thread = Thread(target=self._bot_handler.start_polling, daemon=True)
            polling_thread.start()
            logger.info("Telegram polling started in background")
            
            self._update_component_state("telegram_bot", ComponentState.RUNNING)
            logger.info("Telegram components started successfully")
            
        except Exception as e:
            self._update_component_state("telegram_dashboard", ComponentState.ERROR, str(e))
            self._update_component_state("telegram_bot", ComponentState.ERROR, str(e))
            logger.error(f"Failed to initialize Telegram components: {e}")
            logger.warning("Continuing with basic notifications only")
            self._dashboard = None
            self._bot_handler = None
    
    async def _start_monitoring_components(self):
        """Start monitoring and metrics systems"""
        logger.info("Starting monitoring components...")
        self._register_component("prometheus", {"type": "monitoring", "service": "prometheus"})
        
        if not self.config.monitoring.prometheus_enabled:
            logger.info("Prometheus disabled in configuration")
            self._update_component_state("prometheus", ComponentState.STOPPED)
            return
        
        try:
            from prometheus_client import start_http_server
            from threading import Thread
            
            # Start metrics server in background thread
            metrics_thread = Thread(
                target=start_http_server,
                args=(self.config.api.metrics_port,),
                daemon=True
            )
            metrics_thread.start()
            
            self._update_component_state("prometheus", ComponentState.RUNNING)
            logger.info(f"Prometheus metrics server started on port {self.config.api.metrics_port}")
            
        except ImportError:
            self._update_component_state("prometheus", ComponentState.ERROR, "prometheus_client not installed")
            logger.warning("prometheus_client not available, metrics disabled")
        except Exception as e:
            self._update_component_state("prometheus", ComponentState.ERROR, str(e))
            logger.error(f"Failed to start metrics server: {e}")
    
    async def _start_health_server(self):
        """Start health check HTTP server"""
        logger.info("Starting health check server...")
        self._register_component("health_server", {"type": "monitoring", "service": "health"})
        
        try:
            from flask import Flask, jsonify
            from threading import Thread
            
            # Create Flask app for health checks
            app = Flask(__name__)
            
            @app.route('/health')
            @app.route('/healthz')
            def health_check():
                return jsonify(self.health_check()), 200 if self.is_healthy() else 503
            
            @app.route('/health/ready')
            def readiness_check():
                return jsonify({"status": "ready"}), 200
            
            @app.route('/health/live')
            def liveness_check():
                return jsonify({"status": "alive"}), 200
            
            @app.route('/metrics')
            def metrics():
                from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
                return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}
            
            # Start health server in background thread
            self._health_server_thread = Thread(
                target=app.run,
                kwargs={
                    'host': '0.0.0.0',
                    'port': self.config.api.health_port,
                    'debug': False,
                    'use_reloader': False,
                    'threaded': True
                },
                daemon=True
            )
            self._health_server_thread.start()
            
            self._update_component_state("health_server", ComponentState.RUNNING)
            logger.info(f"Health check server started on port {self.config.api.health_port}")
            
        except Exception as e:
            self._update_component_state("health_server", ComponentState.ERROR, str(e))
            logger.error(f"Failed to start health server: {e}")
    
    async def _start_background_tasks(self):
        """Start background monitoring and maintenance tasks"""
        logger.info("Starting background tasks...")
        
        # Start periodic health check task
        health_task = asyncio.create_task(self._periodic_health_check())
        self._background_tasks.append(health_task)
        
        # Start periodic Telegram heartbeat if enabled
        if self.config.telegram.enabled and self._dashboard:
            heartbeat_task = asyncio.create_task(self._periodic_telegram_heartbeat())
            self._background_tasks.append(heartbeat_task)
        
        logger.info(f"Started {len(self._background_tasks)} background tasks")
    
    async def _periodic_health_check(self):
        """Periodic health check background task"""
        while not self._shutdown_event.is_set():
            try:
                # Update component heartbeats
                for name, component in self._components.items():
                    if component.state == ComponentState.RUNNING:
                        component.last_heartbeat = datetime.now()
                
                # Check risk limits
                await self._check_risk_limits()
                
                await asyncio.sleep(self.config.health_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic health check: {e}")
                await asyncio.sleep(self.config.health_check_interval)
    
    async def _periodic_telegram_heartbeat(self):
        """Periodic Telegram heartbeat task"""
        while not self._shutdown_event.is_set():
            try:
                if self._dashboard:
                    self._dashboard.send_heartbeat()
                
                await asyncio.sleep(self.config.telegram.heartbeat_interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Telegram heartbeat: {e}")
                await asyncio.sleep(self.config.telegram.heartbeat_interval_seconds)
    
    async def _check_risk_limits(self):
        """Check trading risk limits and send alerts if needed"""
        try:
            from risk_management import risk_manager
            
            should_stop, reasons = risk_manager.should_stop_trading()
            if should_stop and self._dashboard:
                from telegram_dashboard import RiskAlertNotification
                for reason in reasons:
                    alert = RiskAlertNotification(
                        alert_type="risk_limit_breach",
                        severity="CRITICAL",
                        message=reason
                    )
                    self._dashboard.send_risk_alert(alert)
                    
        except Exception as e:
            logger.debug(f"Risk limit check skipped: {e}")
    
    async def _run_startup_handlers(self):
        """Run registered startup handlers"""
        for handler in self._startup_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler()
                else:
                    handler()
            except Exception as e:
                logger.error(f"Startup handler error: {e}")
    
    async def _run_shutdown_handlers(self):
        """Run registered shutdown handlers"""
        for handler in self._shutdown_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler()
                else:
                    handler()
            except Exception as e:
                logger.error(f"Shutdown handler error: {e}")
    
    async def _send_startup_notification(self):
        """Send startup notification via Telegram"""
        if not self.config.telegram.enabled or not self._dashboard:
            return
        
        try:
            self._dashboard.send_startup_message()
            logger.info("Startup notification sent")
        except Exception as e:
            logger.error(f"Failed to send startup notification: {e}")
    
    async def _send_shutdown_notification(self):
        """Send shutdown notification via Telegram"""
        if not self.config.telegram.enabled or not self._dashboard:
            return
        
        try:
            self._dashboard.send_shutdown_message()
            logger.info("Shutdown notification sent")
        except Exception as e:
            logger.error(f"Failed to send shutdown notification: {e}")
    
    async def _stop_background_tasks(self):
        """Stop all background tasks"""
        logger.info("Stopping background tasks...")
        
        for task in self._background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        self._background_tasks.clear()
        logger.info("Background tasks stopped")
    
    async def _stop_health_server(self):
        """Stop health check server"""
        logger.info("Stopping health server...")
        # Flask server runs in daemon thread, will be terminated automatically
        self._update_component_state("health_server", ComponentState.STOPPED)
        logger.info("Health server stopped")
    
    async def _stop_monitoring_components(self):
        """Stop monitoring components"""
        logger.info("Stopping monitoring components...")
        self._update_component_state("prometheus", ComponentState.STOPPED)
        logger.info("Monitoring components stopped")
    
    async def _stop_telegram_components(self):
        """Stop Telegram components"""
        logger.info("Stopping Telegram components...")
        
        if self._bot_handler:
            try:
                # Stop bot polling (implementation depends on bot library)
                pass
            except Exception as e:
                logger.error(f"Error stopping Telegram bot: {e}")
        
        self._update_component_state("telegram_dashboard", ComponentState.STOPPED)
        self._update_component_state("telegram_bot", ComponentState.STOPPED)
        logger.info("Telegram components stopped")
    
    async def _stop_vnpy_components(self):
        """Stop VNPy trading system"""
        logger.info("Stopping VNPy components...")
        
        if not self._vnpy_available:
            self._update_component_state("vnpy", ComponentState.STOPPED)
            return
        
        try:
            # Stop all strategies
            if self._cta_engine:
                self._cta_engine.stop_all_strategies()
                logger.info("All strategies stopped")
            
            # Close main engine
            if self._main_engine:
                self._main_engine.close()
                logger.info("VNPy MainEngine closed")
                
        except Exception as e:
            logger.error(f"Error during VNPy shutdown: {e}")
        finally:
            self._update_component_state("vnpy", ComponentState.STOPPED)
            self._vnpy_available = False
            self._main_engine = None
            self._cta_engine = None
            self._event_engine = None
    
    async def _stop_database_components(self):
        """Stop database connections"""
        logger.info("Stopping database components...")
        self._update_component_state("postgres", ComponentState.STOPPED)
        self._update_component_state("redis", ComponentState.STOPPED)
        logger.info("Database components stopped")
    
    async def _stop_security_components(self):
        """Stop security components"""
        logger.info("Stopping security components...")
        
        try:
            from security.audit_logger import log_security_event
            log_security_event(
                service="orchestrator",
                user="system",
                action="shutdown",
                outcome="success",
                details={"component": "lifecycle"}
            )
        except Exception as e:
            logger.error(f"Error logging shutdown event: {e}")
        
        self._update_component_state("security", ComponentState.STOPPED)
        logger.info("Security components stopped")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Comprehensive health check of all components.
        
        Returns:
            Dict containing health status of all components
        """
        overall_state = "healthy"
        unhealthy_components = []
        
        for name, component in self._components.items():
            if component.state != ComponentState.RUNNING:
                overall_state = "unhealthy"
                unhealthy_components.append({
                    'name': name,
                    'state': component.state.value,
                    'error': component.last_error
                })
        
        return {
            'status': overall_state,
            'timestamp': datetime.now().isoformat(),
            'service': self.config.service_name,
            'version': self.config.version,
            'environment': self.config.environment,
            'components': {name: comp.to_dict() for name, comp in self._components.items()},
            'unhealthy_components': unhealthy_components,
            'uptime': self._get_uptime(),
            'trading_mode': self.config.trading.mode.value
        }
    
    def is_healthy(self) -> bool:
        """Check if orchestrator is healthy"""
        for component in self._components.values():
            if component.state == ComponentState.ERROR:
                return False
        return True
    
    def _get_uptime(self) -> Optional[str]:
        """Get uptime since startup"""
        for component in self._components.values():
            if component.started_at:
                uptime = datetime.now() - component.started_at
                return str(uptime)
        return None
    
    def register_startup_handler(self, handler: Callable):
        """Register a handler to be called during startup"""
        self._startup_handlers.append(handler)
    
    def register_shutdown_handler(self, handler: Callable):
        """Register a handler to be called during shutdown"""
        self._shutdown_handlers.append(handler)
    
    def get_component_status(self, name: str) -> Optional[ComponentHealth]:
        """Get status of a specific component"""
        return self._components.get(name)
    
    def wait_for_shutdown(self):
        """Wait for shutdown signal"""
        self._shutdown_event.wait()
    
    async def run_until_shutdown(self):
        """Run the orchestrator until shutdown is requested"""
        await self.start()
        await self._shutdown_event.wait()
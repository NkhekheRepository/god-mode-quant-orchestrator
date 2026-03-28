import os
import sys
import time
import signal
import atexit
import requests
import ssl
import logging
try:
    import psycopg2
except ImportError:
    psycopg2 = None
try:
    import redis
except ImportError:
    redis = None
from threading import Thread
from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

# Configure structured logging
from utils.logging_config import setup_logging
logger = setup_logging('main')

# Flask app for health checks
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(32).hex())

# Rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)
limiter.init_app(app)

# HTTP Basic Authentication
auth = HTTPBasicAuth()

# Load credentials from environment
_users = {
    os.getenv('API_USERNAME', 'admin'): generate_password_hash(
        os.getenv('API_PASSWORD', 'admin')
    )
}

@auth.verify_password
def verify_password(username, password):
    if username in _users and check_password_hash(_users[username], password):
        return username
    return None

# Add security headers to all responses
@app.after_request
def add_security_headers(response):
    from security.config import get_security_headers
    headers = get_security_headers()
    for key, value in headers.items():
        response.headers[key] = value
    return response

@app.route('/health')
@app.route('/healthz')
def health_check():
    """Enhanced health check with dependency verification"""
    status = {"status": "healthy", "service": "god-mode-quant-orchestrator"}
    healthy = True
    
    # Check PostgreSQL
    if psycopg2 is None:
        status["postgres"] = "not checked (psycopg2 not installed)"
    else:
        try:
            pg_host = os.getenv('POSTGRES_HOST', 'postgres')
            conn = psycopg2.connect(
                host=pg_host,
                port=int(os.getenv('POSTGRES_PORT', 5432)),
                user=os.getenv('POSTGRES_USER', 'postgres'),
                password=os.getenv('POSTGRES_PASSWORD', 'postgres'),
                dbname=os.getenv('POSTGRES_DB', 'vnpy'),
                connect_timeout=5
            )
            conn.close()
            status["postgres"] = "healthy"
        except Exception as e:
            status["postgres"] = f"unhealthy: {str(e)}"
            healthy = False
    
    # Check Redis
    if redis is None:
        status["redis"] = "not checked (redis not installed)"
    else:
        try:
            r = redis.Redis(
                host=os.getenv('REDIS_HOST', 'redis'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                password=os.getenv('REDIS_PASSWORD', '') or None,
                socket_connect_timeout=5
            )
            r.ping()
            status["redis"] = "healthy"
        except Exception as e:
            status["redis"] = f"unhealthy: {str(e)}"
            healthy = False
    
    if healthy:
        return jsonify(status), 200
    else:
        return jsonify(status), 503


@app.route('/health/ready')
def readiness_check():
    """Kubernetes readiness probe"""
    return jsonify({"status": "ready"}), 200


@app.route('/health/live')
def liveness_check():
    """Kubernetes liveness probe"""
    return jsonify({"status": "alive"}), 200

@app.route('/metrics')
@auth.login_required
@limiter.limit("50 per minute")
def metrics():
    """Prometheus metrics endpoint"""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    
    # Import metrics from the metrics module
    try:
        from metrics import (
            update_trading_metrics, update_trust_metrics
        )
        
        # Update metrics from current state
        try:
            from risk_management import risk_manager
            update_trading_metrics(risk_manager.portfolio)
        except Exception:
            pass
        
        try:
            from security.trust_scorer import trust_scorer
            score = trust_scorer.get_trust_score("orchestrator:system")
            update_trust_metrics({"orchestrator:system": score})
        except Exception:
            pass
            
    except ImportError:
        pass
    
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

def run_health_server():
    """Run health server on port 8003"""
    app.run(host='0.0.0.0', port=8003, debug=False, use_reloader=False, threaded=True)

# Legacy function for backward compatibility
def send_telegram_message(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'HTML'
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        logger.info("Telegram notification sent successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {e}")
        return False


# Global shutdown flag to prevent double shutdown
_shutdown_in_progress = False


def graceful_shutdown():
    """Handle graceful shutdown on SIGTERM/SIGINT"""
    global _shutdown_in_progress
    
    # Prevent multiple shutdowns
    if _shutdown_in_progress:
        return
    
    _shutdown_in_progress = True
    logger.info("GRACEFUL SHUTDOWN INITIATED")
    
    # Import trading engine here to avoid circular imports
    try:
        from trading_engine import get_trading_engine
        trading_engine = get_trading_engine()
        
        if trading_engine:
            try:
                trading_engine.stop()
                logger.info("Trading engine stopped")
                
                # Close positions if gateway available
                if trading_engine.gateway and trading_engine.open_positions:
                    logger.warning("Closing open positions before shutdown...")
                    trading_engine.force_close_all()
                    logger.info("All positions closed")
            except Exception as e:
                logger.error(f"Error during trading engine shutdown: {e}")
    except Exception as e:
        logger.error(f"Error during graceful shutdown: {e}")
    
    logger.info("Graceful shutdown complete")


# Register signal handlers for graceful shutdown
def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown"""
    def handle_signal(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        graceful_shutdown()
        # Exit with the signal's original exit code
        import os
        os._exit(128 + signum)
    
    try:
        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)
        logger.info("Signal handlers registered for graceful shutdown")
    except (ValueError, RuntimeError) as e:
        # Handle case where signals can't be registered during shutdown
        logger.debug(f"Could not register signal handlers: {e}")


# Setup signal handlers at module load
setup_signal_handlers()
_module_initialized = True


def main():
    logger.info("=== GOD MODE QUANT TRADING ORCHESTRATOR STARTING ===")
    
    # Initialize security components
    from security.mtls_manager import mtls_manager
    from security.secrets_manager import get_binance_api_key, get_binance_api_secret, get_telegram_bot_token, get_telegram_chat_id
    
    # Get environment variables (with fallback to secrets manager)
    telegram_token = get_telegram_bot_token() or os.getenv('TELEGRAM_BOT_TOKEN', '')
    telegram_chat_id = get_telegram_chat_id() or os.getenv('TELEGRAM_CHAT_ID', '')
    
    logger.info(f"Environment check:")
    logger.info(f"  TELEGRAM_BOT_TOKEN: {'SET' if telegram_token else 'NOT SET'}")
    logger.info(f"  TELEGRAM_CHAT_ID: {'SET' if telegram_chat_id else 'NOT SET'}")
    
    if not telegram_token or not telegram_chat_id:
        logger.warning("Telegram credentials not configured")
        # Try loading from .env file
        try:
            from dotenv import load_dotenv
            load_dotenv()
            telegram_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
            telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
            logger.info(f"Loaded from .env - TOKEN: {'SET' if telegram_token else 'NOT SET'}, CHAT_ID: {'SET' if telegram_chat_id else 'NOT SET'}")
        except ImportError:
            pass
        
        if not telegram_token or not telegram_chat_id:
            logger.error("Telegram credentials not configured - exiting")
            sys.exit(1)
    
    # Try to import vnpy to ensure it's installed
    vnpy_available = False
    vnpy_config = {}
    try:
        import vnpy
        from vnpy.event import EventEngine
        from vnpy.trader.engine import MainEngine
        from vnpy_ctastrategy import CtaStrategyApp
        logger.info(f"VNPY imported successfully: {vnpy.__version__}")
        
        # Import VNPy configuration module
        from vnpy_config import setup_vnpy_environment, get_vnpy_config_from_env
        
        # Get API credentials
        binance_api_key = get_binance_api_key() or os.getenv('BINANCE_API_KEY', '')
        binance_api_secret = get_binance_api_secret() or os.getenv('BINANCE_API_SECRET', '')
        testnet = os.getenv('BINANCE_TESTNET', 'true').lower() in ('true', '1', 'yes')
        
        logger.info(f"Binance API Key: {'SET' if binance_api_key and binance_api_key != 'your_key_here' else 'NOT SET'}")
        logger.info(f"Binance Testnet: {testnet}")
        
        # Setup VNPy environment with configuration files
        vnpy_config = setup_vnpy_environment(
            binance_api_key=binance_api_key,
            binance_api_secret=binance_api_secret,
            testnet=testnet
        )
        logger.info("VNPy environment configured successfully")
        vnpy_available = True
    except ImportError as e:
        logger.warning(f"VNPY not available: {e}")
        logger.info("Running in DEMO/MOCK mode - no live trading")
        vnpy_available = False
    except Exception as e:
        logger.warning(f"VNPY configuration error: {e}")
        logger.info("Running in DEMO/MOCK mode - no live trading")
        vnpy_available = False
    
    # ============================================================
    # ENHANCED TELEGRAM DASHBOARD INITIALIZATION
    # ============================================================
    logger.info("=== Initializing Telegram Dashboard ===")
    try:
        from telegram_dashboard import init_telegram_dashboard, get_telegram_dashboard
        from telegram_bot_handler import init_telegram_bot
        
        # Initialize the enhanced Telegram dashboard
        dashboard = init_telegram_dashboard(telegram_token, telegram_chat_id)
        logger.info("Enhanced Telegram Dashboard initialized successfully")
        
        # Initialize Telegram bot handler for commands (pass dashboard directly)
        bot_handler = init_telegram_bot(telegram_token, dashboard=dashboard)
        logger.info("Telegram Bot Handler initialized successfully")
        
        # Start polling in a background thread
        polling_thread = Thread(target=bot_handler.start_polling, daemon=True)
        polling_thread.start()
        logger.info("Telegram polling started in background")
        
        # Send startup message via enhanced dashboard
        dashboard.send_startup_message()
        
    except Exception as e:
        logger.error(f"Failed to initialize Telegram Dashboard: {e}")
        logger.warning("Continuing with basic notifications only")
        dashboard = None
        bot_handler = None
    
    # ============================================================
    # PROMETHEUS METRICS SERVER STARTUP
    # ============================================================
    try:
        from prometheus_client import start_http_server
        # Start metrics server on port 9091 (9090 reserved for Prometheus)
        metrics_thread = Thread(target=start_http_server, args=(9091,), daemon=True)
        metrics_thread.start()
        logger.info("Prometheus metrics server started on port 9091")
    except ImportError:
        logger.warning("prometheus_client not available, metrics disabled")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")
    
    # Send startup notification
    message = "<b>God Mode Quant Trading Orchestrator</b> is now running with vnpy backbone."
    logger.info("Attempting to send Telegram notification...")
    result = send_telegram_message(telegram_token, telegram_chat_id, message)
    logger.info(f"Telegram notification result: {result}")
    
    # Initialize audit logger
    logger.info("Initializing Audit Logger...")
    try:
        from security.audit_logger import log_security_event
        # Log startup event
        log_security_event(
            service="orchestrator",
            user="system",
            action="startup",
            outcome="success",
            details={"version": "1.0.0", "component": "main_orchestrator"}
        )
        logger.info("Audit Logger initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Audit Logger: {e}")
        logger.warning("Continuing without audit logging")
    
    # Initialize trust scorer
    logger.info("Initializing Trust Scorer...")
    try:
        from security.trust_scorer import record_trust_event, get_trust_score, TrustEventType
        # Record startup event for trust scoring
        record_trust_event(
            service_or_user="orchestrator:system",
            event_type=TrustEventType.AUTH_SUCCESS,
            service="orchestrator",
            user="system",
            description="Orchestrator startup",
            metadata={"version": "1.0.0", "component": "main_orchestrator"}
        )
        initial_score = get_trust_score("orchestrator:system")
        logger.info(f"Trust Scorer initialized successfully (initial score: {initial_score:.1f})")
    except Exception as e:
        logger.error(f"Failed to initialize Trust Scorer: {e}")
        logger.warning("Continuing without trust scoring")
    
    # Initialize risk manager
    logger.info("Initializing Risk Manager...")
    try:
        from risk_management import risk_manager, update_portfolio_value
        # Initialize with starting portfolio value
        update_portfolio_value(100000.0)  # Starting with $100,000 portfolio
        logger.info("Risk Manager initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Risk Manager: {e}")
        logger.warning("Continuing without risk management")
    
    # Initialize vnpy trading system (only if available)
    cta_engine = None
    main_engine = None
    if vnpy_available:
        logger.info("Initializing vnpy trading system...")
        try:
            # Create event engine
            event_engine = EventEngine()
            
            # Create main engine
            main_engine = MainEngine(event_engine)
            logger.info("VNPy MainEngine created")
            
            # Add Binance gateway (Linear = USDT-margined futures)
            try:
                from vnpy_binance import BinanceLinearGateway
                main_engine.add_gateway(BinanceLinearGateway)
                logger.info("BinanceLinearGateway added to MainEngine")
            except ImportError as e:
                logger.warning(f"Could not add Binance gateway: {e}")
            except Exception as e:
                logger.warning(f"Error adding Binance gateway: {e}")
            
            # Add CTA strategy app
            cta_engine = main_engine.add_app(CtaStrategyApp)
            logger.info("CTA Strategy app added")
            
            # Connect to Binance with API credentials
            binance_key = vnpy_config.get('binance.key') or get_binance_api_key() or os.getenv('BINANCE_API_KEY', '')
            binance_secret = vnpy_config.get('binance.secret') or get_binance_api_secret() or os.getenv('BINANCE_API_SECRET', '')
            is_testnet = vnpy_config.get('binance.usdt_testnet', os.getenv('BINANCE_TESTNET', 'true').lower() in ('true', '1', 'yes'))
            
            if binance_key and binance_secret and binance_key != 'your_key_here':
                try:
                    connect_setting = {
                        "key": binance_key,
                        "secret": binance_secret,
                        "proxy_host": "",
                        "proxy_port": 0,
                        "usdt_testnet": is_testnet,
                    }
                    main_engine.connect(connect_setting, "BINANCE")
                    logger.info(f"Connected to Binance {'testnet' if is_testnet else 'production'}")
                except Exception as e:
                    logger.error(f"Failed to connect to Binance: {e}")
                    logger.info("Check your API credentials in .env file")
            else:
                logger.warning("Binance API credentials not configured properly")
                logger.info("Set BINANCE_API_KEY and BINANCE_API_SECRET in .env file")
            
            # Load strategy setting (empty for now)
            strategy_setting = {}
            
            # Add our MA crossover strategy
            try:
                # Import the strategy class
                from strategies.ma_crossover_strategy import MaCrossoverStrategy
                
                cta_engine.add_strategy(
                    class_name="MaCrossoverStrategy",
                    strategy_name="ma_crossover_01",
                    vt_symbol="BTCUSDT.BINANCE",  # VNPy symbol format
                    setting=strategy_setting
                )
                logger.info("MA Crossover strategy added successfully")
            except Exception as e:
                logger.error(f"Failed to add strategy: {e}")
                # Try alternative symbol format
                try:
                    cta_engine.add_strategy(
                        class_name="MaCrossoverStrategy",
                        strategy_name="ma_crossover_01",
                        vt_symbol="BTCUSDT",  # Alternative format
                        setting=strategy_setting
                    )
                    logger.info("MA Crossover strategy added with alternative symbol format")
                except Exception as e2:
                    logger.error(f"Failed to add strategy with alternative format: {e2}")
            
            # Initialize all strategies
            try:
                cta_engine.init_all_strategies()
                logger.info("All strategies initialized")
            except Exception as e:
                logger.warning(f"Strategy initialization: {e}")
            
            # Start all strategies
            try:
                cta_engine.start_all_strategies()
                logger.info("All strategies started")
            except Exception as e:
                logger.warning(f"Strategy start: {e}")
                
        except Exception as e:
            logger.error(f"Failed to initialize vnpy trading system: {e}")
            logger.info("Continuing in DEMO mode")
            vnpy_available = False
    else:
        logger.info("Running in DEMO mode - no live trading engine")
    
    # Initialize the TradingEngine for Telegram bot commands
    logger.info("Initializing TradingEngine for Telegram bot...")
    try:
        from trading_engine import create_trading_engine
        trading_config = {
            'starting_capital': 100000.0,
            'leverage': 10,
            'max_positions': 5,
            'demo_mode': True
        }
        trading_engine = create_trading_engine(trading_config)
        # Initialize components (gateway, order manager, risk management, etc.)
        init_success = trading_engine.initialize()
        if init_success:
            logger.info("TradingEngine initialized successfully (DEMO mode)")
        else:
            logger.warning("TradingEngine created but initialization failed - some features may be limited")
    except Exception as e:
        logger.error(f"Failed to initialize TradingEngine: {e}")
        trading_engine = None
    
    # Start health check server in background thread
    health_thread = Thread(target=run_health_server, daemon=True)
    health_thread.start()
    logger.info("Health check server started on port 8000")
    
    # Send strategy start notification
    strategy_message = "<b>MA Crossover Strategy</b> has been started on BINANCE:BTCUSDT"
    send_telegram_message(telegram_token, telegram_chat_id, strategy_message)
    
    # Keep the orchestrator running for a limited time for testing
    logger.info("Trading orchestrator started. Entering main loop...")
    
    # Track last summary sent times
    last_daily_summary = datetime.now()
    last_weekly_summary = datetime.now()
    
    try:
        counter = 0
        max_iterations = -1  # Run indefinitely
        while max_iterations < 0 or counter < max_iterations:
            time.sleep(5)  # Sleep for 5 seconds for testing
            counter += 1
            logger.info(f"Heartbeat: Orchestrator running... ({counter * 5}s)")
            
            # Periodic status update every 2 iterations (10 seconds) for testing
            if counter % 2 == 0:
                # Use enhanced dashboard if available
                if dashboard:
                    dashboard.send_heartbeat()
                elif cta_engine:
                    status_message = f"<b>God Mode Quant Trading Orchestrator</b> is running normally. Strategies active: {len(cta_engine.strategies)}"
                    send_telegram_message(telegram_token, telegram_chat_id, status_message)
                
                # Check risk limits and send alerts
                if dashboard:
                    from risk_management import risk_manager
                    from security.trust_scorer import trust_scorer
                    
                    # Check drawdown
                    should_stop, reasons = risk_manager.should_stop_trading()
                    if should_stop:
                        from telegram_dashboard import RiskAlertNotification
                        for reason in reasons:
                            alert = RiskAlertNotification(
                                alert_type="risk_limit_breach",
                                severity="CRITICAL",
                                message=reason
                            )
                            dashboard.send_risk_alert(alert)
                    
                    # Check trust score changes
                    trust_score = trust_scorer.get_trust_score("orchestrator:system")
                    dashboard.check_trust_score_change("orchestrator:system", trust_score)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        # Stop all strategies
        if cta_engine:
            try:
                cta_engine.stop_all_strategies()
                logger.info("All strategies stopped")
            except Exception as e:
                logger.error(f"Error stopping strategies: {e}")
        
        # Close main engine connection
        if main_engine:
            try:
                main_engine.close()
                logger.info("VNPy MainEngine closed")
            except Exception as e:
                logger.error(f"Error closing MainEngine: {e}")
        
        # Send shutdown notification via enhanced dashboard
        if dashboard:
            dashboard.send_shutdown_message()
        else:
            shutdown_message = "<b>God Mode Quant Trading Orchestrator</b> is shutting down."
            send_telegram_message(telegram_token, telegram_chat_id, shutdown_message)

if __name__ == "__main__":
    main()

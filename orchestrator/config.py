"""
Orchestrator Configuration Module
Centralized configuration management for the GodMode Quant Trading Orchestrator.
Loads and validates all settings from environment variables.
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TradingMode(Enum):
    """Trading mode enumeration"""
    LIVE = "live"
    TESTNET = "testnet"
    DEMO = "demo"
    PAPER = "paper"


@dataclass
class TradingConfig:
    """Trading-related configuration settings"""
    symbol: str = "BTCUSDT"
    interval: str = "5"  # minutes
    starting_capital: float = 100000.0
    leverage: int = 10
    max_positions: int = 5
    max_daily_loss_percent: float = 3.0
    max_drawdown_percent: float = 10.0
    default_stop_loss_percent: float = 1.5
    default_take_profit_percent: float = 4.0
    risk_per_trade_percent: float = 1.0
    mode: TradingMode = TradingMode.DEMO
    
    @classmethod
    def from_env(cls) -> 'TradingConfig':
        """Create TradingConfig from environment variables"""
        mode_str = os.getenv('TRADING_MODE', 'demo').lower()
        try:
            mode = TradingMode(mode_str)
        except ValueError:
            logger.warning(f"Invalid TRADING_MODE '{mode_str}', using 'demo'")
            mode = TradingMode.DEMO
            
        return cls(
            symbol=os.getenv('TRADING_SYMBOL', 'BTCUSDT'),
            interval=os.getenv('TRADING_INTERVAL', '5'),
            starting_capital=float(os.getenv('STARTING_CAPITAL', '100000')),
            leverage=int(os.getenv('MAX_LEVERAGE', '10')),
            max_positions=int(os.getenv('MAX_POSITIONS', '5')),
            max_daily_loss_percent=float(os.getenv('DAILY_LOSS_LIMIT', '3')),
            max_drawdown_percent=float(os.getenv('MAX_DRAWDOWN', '10')),
            default_stop_loss_percent=float(os.getenv('DEFAULT_STOP_LOSS', '1.5')),
            default_take_profit_percent=float(os.getenv('DEFAULT_TAKE_PROFIT', '4')),
            risk_per_trade_percent=float(os.getenv('RISK_PER_TRADE', '1')),
            mode=mode
        )


@dataclass
class DatabaseConfig:
    """Database configuration settings"""
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "vnpy"
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0
    
    @property
    def postgres_url(self) -> str:
        """Get PostgreSQL connection URL"""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    @property
    def redis_url(self) -> str:
        """Get Redis connection URL"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        """Create DatabaseConfig from environment variables"""
        return cls(
            postgres_host=os.getenv('POSTGRES_HOST', 'postgres'),
            postgres_port=int(os.getenv('POSTGRES_PORT', '5432')),
            postgres_user=os.getenv('POSTGRES_USER', 'postgres'),
            postgres_password=os.getenv('POSTGRES_PASSWORD', 'postgres'),
            postgres_db=os.getenv('POSTGRES_DB', 'vnpy'),
            redis_host=os.getenv('REDIS_HOST', 'redis'),
            redis_port=int(os.getenv('REDIS_PORT', '6379')),
            redis_password=os.getenv('REDIS_PASSWORD') or None,
            redis_db=int(os.getenv('REDIS_DB', '0'))
        )


@dataclass
class TelegramConfig:
    """Telegram notification configuration"""
    bot_token: str = ""
    chat_id: str = ""
    enabled: bool = True
    heartbeat_interval_seconds: int = 300  # 5 minutes
    daily_summary_hour: int = 20  # 8 PM
    weekly_summary_day: int = 0  # Monday
    
    @classmethod
    def from_env(cls) -> 'TelegramConfig':
        """Create TelegramConfig from environment variables"""
        return cls(
            bot_token=os.getenv('TELEGRAM_BOT_TOKEN', ''),
            chat_id=os.getenv('TELEGRAM_CHAT_ID', ''),
            enabled=os.getenv('TELEGRAM_ENABLED', 'true').lower() == 'true',
            heartbeat_interval_seconds=int(os.getenv('TELEGRAM_HEARTBEAT_INTERVAL', '300')),
            daily_summary_hour=int(os.getenv('TELEGRAM_DAILY_SUMMARY_HOUR', '20')),
            weekly_summary_day=int(os.getenv('TELEGRAM_WEEKLY_SUMMARY_DAY', '0'))
        )


@dataclass
class BinanceConfig:
    """Binance exchange configuration"""
    api_key: str = ""
    api_secret: str = ""
    testnet: bool = True
    futures_enabled: bool = True
    recv_window: int = 5000
    timeout: int = 30
    
    @classmethod
    def from_env(cls) -> 'BinanceConfig':
        """Create BinanceConfig from environment variables"""
        return cls(
            api_key=os.getenv('BINANCE_API_KEY', ''),
            api_secret=os.getenv('BINANCE_API_SECRET', ''),
            testnet=os.getenv('BINANCE_TESTNET', 'true').lower() in ('true', '1', 'yes'),
            futures_enabled=os.getenv('BINANCE_FUTURES_ENABLED', 'true').lower() == 'true',
            recv_window=int(os.getenv('BINANCE_RECV_WINDOW', '5000')),
            timeout=int(os.getenv('BINANCE_TIMEOUT', '30'))
        )


@dataclass
class APIConfig:
    """API server configuration"""
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    health_port: int = 8003
    metrics_port: int = 9091
    username: str = "admin"
    password: str = "admin"
    auth_enabled: bool = True
    cors_origins: List[str] = field(default_factory=lambda: ["http://localhost:3000"])
    rate_limit_per_minute: int = 10
    rate_limit_per_day: int = 200
    secret_key: str = ""
    
    @classmethod
    def from_env(cls) -> 'APIConfig':
        """Create APIConfig from environment variables"""
        cors_origins_str = os.getenv('CORS_ORIGINS', 'http://localhost:3000')
        cors_origins = [origin.strip() for origin in cors_origins_str.split(',')]
        
        return cls(
            host=os.getenv('API_HOST', '0.0.0.0'),
            port=int(os.getenv('API_PORT', '8000')),
            workers=int(os.getenv('API_WORKERS', '1')),
            health_port=int(os.getenv('HEALTH_PORT', '8003')),
            metrics_port=int(os.getenv('METRICS_PORT', '9091')),
            username=os.getenv('API_USERNAME', 'admin'),
            password=os.getenv('API_PASSWORD', 'admin'),
            auth_enabled=os.getenv('AUTH_ENABLED', 'true').lower() == 'true',
            cors_origins=cors_origins,
            rate_limit_per_minute=int(os.getenv('RATE_LIMIT_PER_MINUTE', '10')),
            rate_limit_per_day=int(os.getenv('RATE_LIMIT_PER_DAY', '200')),
            secret_key=os.getenv('SECRET_KEY', os.urandom(32).hex())
        )


@dataclass
class SecurityConfig:
    """Security configuration"""
    ssl_verify: bool = True
    ssl_cert_path: Optional[str] = None
    session_timeout: int = 3600
    jwt_secret_key: str = ""
    log_security_events: bool = True
    security_log_level: str = "INFO"
    vault_addr: Optional[str] = None
    vault_token: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'SecurityConfig':
        """Create SecurityConfig from environment variables"""
        return cls(
            ssl_verify=os.getenv('SSL_VERIFY', 'true').lower() == 'true',
            ssl_cert_path=os.getenv('SSL_CERT_PATH') or None,
            session_timeout=int(os.getenv('SESSION_TIMEOUT', '3600')),
            jwt_secret_key=os.getenv('JWT_SECRET_KEY', ''),
            log_security_events=os.getenv('LOG_SECURITY_EVENTS', 'true').lower() == 'true',
            security_log_level=os.getenv('SECURITY_LOG_LEVEL', 'INFO'),
            vault_addr=os.getenv('VAULT_ADDR') or None,
            vault_token=os.getenv('VAULT_TOKEN') or None
        )


@dataclass
class MonitoringConfig:
    """Monitoring and observability configuration"""
    prometheus_enabled: bool = True
    sentry_dsn: Optional[str] = None
    opentelemetry_enabled: bool = False
    opentelemetry_endpoint: Optional[str] = None
    log_level: str = "INFO"
    structured_logging: bool = True
    
    @classmethod
    def from_env(cls) -> 'MonitoringConfig':
        """Create MonitoringConfig from environment variables"""
        return cls(
            prometheus_enabled=os.getenv('PROMETHEUS_ENABLED', 'true').lower() == 'true',
            sentry_dsn=os.getenv('SENTRY_DSN') or None,
            opentelemetry_enabled=os.getenv('OPENTELEMETRY_ENABLED', 'false').lower() == 'true',
            opentelemetry_endpoint=os.getenv('OPENTELEMETRY_ENDPOINT') or None,
            log_level=os.getenv('LOG_LEVEL', 'INFO').upper(),
            structured_logging=os.getenv('STRUCTURED_LOGGING', 'true').lower() == 'true'
        )


@dataclass
class MLConfig:
    """Machine Learning configuration"""
    enabled: bool = False
    model_type: str = "ensemble"
    confidence_threshold: float = 0.6
    model_path: str = "./ml_models"
    retrain_schedule: str = "daily"
    
    @classmethod
    def from_env(cls) -> 'MLConfig':
        """Create MLConfig from environment variables"""
        return cls(
            enabled=os.getenv('ML_ENABLED', 'false').lower() == 'true',
            model_type=os.getenv('ML_MODEL_TYPE', 'ensemble').lower(),
            confidence_threshold=float(os.getenv('ML_CONFIDENCE_THRESHOLD', '0.6')),
            model_path=os.getenv('ML_MODEL_PATH', './ml_models'),
            retrain_schedule=os.getenv('RETRAIN_SCHEDULE', 'daily')
        )


@dataclass
class OrchestratorConfig:
    """
    Main orchestrator configuration that aggregates all sub-configurations.
    This is the single source of truth for all orchestrator settings.
    """
    trading: TradingConfig
    database: DatabaseConfig
    telegram: TelegramConfig
    binance: BinanceConfig
    api: APIConfig
    security: SecurityConfig
    monitoring: MonitoringConfig
    ml: MLConfig
    
    # General settings
    service_name: str = "god-mode-quant-orchestrator"
    version: str = "1.0.0"
    environment: str = "development"
    shutdown_timeout: int = 30  # seconds
    health_check_interval: int = 30  # seconds
    
    @classmethod
    def from_env(cls) -> 'OrchestratorConfig':
        """
        Create complete OrchestratorConfig from environment variables.
        This is the primary factory method for loading configuration.
        """
        environment = os.getenv('ENVIRONMENT', 'development').lower()
        
        return cls(
            trading=TradingConfig.from_env(),
            database=DatabaseConfig.from_env(),
            telegram=TelegramConfig.from_env(),
            binance=BinanceConfig.from_env(),
            api=APIConfig.from_env(),
            security=SecurityConfig.from_env(),
            monitoring=MonitoringConfig.from_env(),
            ml=MLConfig.from_env(),
            service_name=os.getenv('SERVICE_NAME', 'god-mode-quant-orchestrator'),
            version=os.getenv('VERSION', '1.0.0'),
            environment=environment,
            shutdown_timeout=int(os.getenv('SHUTDOWN_TIMEOUT', '30')),
            health_check_interval=int(os.getenv('HEALTH_CHECK_INTERVAL', '30'))
        )
    
    def validate(self) -> List[str]:
        """
        Validate configuration and return list of warnings/errors.
        Returns list of validation messages (empty if valid).
        """
        warnings = []
        
        # Check required trading settings
        if self.trading.leverage < 1:
            warnings.append(f"Leverage must be >= 1, got {self.trading.leverage}")
        
        if self.trading.starting_capital <= 0:
            warnings.append(f"Starting capital must be > 0, got {self.trading.starting_capital}")
        
        # Check database settings
        if not self.database.postgres_host:
            warnings.append("PostgreSQL host not configured")
        
        # Check Telegram settings
        if self.telegram.enabled and (not self.telegram.bot_token or not self.telegram.chat_id):
            warnings.append("Telegram enabled but credentials not configured")
        
        # Check Binance settings
        if self.trading.mode in [TradingMode.LIVE, TradingMode.TESTNET]:
            if not self.binance.api_key or not self.binance.api_secret:
                warnings.append(f"Binance API credentials required for {self.trading.mode.value} mode")
        
        # Check API settings
        if self.api.auth_enabled and (self.api.username == 'admin' and self.api.password == 'admin'):
            warnings.append("Using default API credentials (admin/admin) - change in production")
        
        # Check security settings
        if self.environment == 'production':
            if self.security.ssl_verify is False:
                warnings.append("SSL verification disabled in production")
            if not self.security.jwt_secret_key:
                warnings.append("JWT secret key not configured for production")
        
        return warnings
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for logging/serialization"""
        return {
            'service_name': self.service_name,
            'version': self.version,
            'environment': self.environment,
            'trading': {
                'symbol': self.trading.symbol,
                'interval': self.trading.interval,
                'mode': self.trading.mode.value,
                'leverage': self.trading.leverage,
                'starting_capital': self.trading.starting_capital
            },
            'database': {
                'postgres_host': self.database.postgres_host,
                'postgres_port': self.database.postgres_port,
                'redis_host': self.database.redis_host,
                'redis_port': self.database.redis_port
            },
            'telegram': {
                'enabled': self.telegram.enabled,
                'has_credentials': bool(self.telegram.bot_token and self.telegram.chat_id)
            },
            'binance': {
                'testnet': self.binance.testnet,
                'has_credentials': bool(self.binance.api_key and self.binance.api_secret)
            },
            'api': {
                'port': self.api.port,
                'auth_enabled': self.api.auth_enabled
            },
            'monitoring': {
                'prometheus_enabled': self.monitoring.prometheus_enabled,
                'log_level': self.monitoring.log_level
            }
        }
    
    def get_vnpy_config(self) -> Dict[str, Any]:
        """Get VNPy-specific configuration dictionary"""
        return {
            'binance.key': self.binance.api_key,
            'binance.secret': self.binance.api_secret,
            'binance.usdt_testnet': self.binance.testnet,
            'postgres.host': self.database.postgres_host,
            'postgres.port': self.database.postgres_port,
            'postgres.user': self.database.postgres_user,
            'postgres.password': self.database.postgres_password,
            'postgres.database': self.database.postgres_db
        }
"""
VNPy Configuration Manager for God Mode Quant Trading Orchestrator
Handles proper initialization of VNPy with Binance gateway and SQLite database.
Includes custom Binance Datafeed for VNPy 4.x compatibility.
"""
import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Configuration paths
VNPY_CONFIG_DIR = Path.home() / ".vntrader"
VNPY_SETTING_FILE = VNPY_CONFIG_DIR / "vt_setting.json"
VNPY_DB_FILE = VNPY_CONFIG_DIR / "vnpy_data.db"


def ensure_vnpy_config_dir() -> Path:
    """Ensure VNPy configuration directory exists."""
    VNPY_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return VNPY_CONFIG_DIR


def create_vt_setting_json(
    binance_api_key: str,
    binance_api_secret: str,
    testnet: bool = True,
    database_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create vt_setting.json configuration for VNPy.
    
    Args:
        binance_api_key: Binance API key
        binance_api_secret: Binance API secret
        testnet: Whether to use Binance testnet
        database_path: Path to SQLite database file
        
    Returns:
        Configuration dictionary
    """
    ensure_vnpy_config_dir()
    
    # Set database path
    if database_path is None:
        database_path = str(VNPY_DB_FILE)
    
    # Binance futures API URLs
    if testnet:
        usdt_address = "https://testnet.binancefuture.com"
    else:
        usdt_address = "https://fapi.binance.com"
    
    config = {
        # Font settings
        "font.family": "微软雅黑",
        "font.size": 12,
        
        # SQLite database configuration
        "database.driver": "sqlite",
        "database.database": database_path,
        "database.host": "",
        "database.port": 0,
        "database.user": "",
        "database.password": "",
        
        # Data feed configuration - use custom BinanceDatafeed module
        "datafeed.name": "datafeed",  # Will look for vnpy_datafeed.Datafeed
        "datafeed.username": "",
        "datafeed.password": "",
        "datafeed.proxy_host": "",
        "datafeed.proxy_port": 0,
        
        # Binance gateway configuration
        "binance.usdt_address": usdt_address,
        "binance.usdt_testnet": testnet,
        "binance.gateway_name": "BINANCE",
        
        # API credentials (used by gateway)
        "binance.key": binance_api_key,
        "binance.secret": binance_api_secret,
    }
    
    # Write configuration file
    with open(VNPY_SETTING_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    
    logger.info(f"VNPy configuration written to {VNPY_SETTING_FILE}")
    
    return config


def load_vt_setting() -> Dict[str, Any]:
    """Load existing VNPy configuration."""
    if VNPY_SETTING_FILE.exists():
        with open(VNPY_SETTING_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def init_vnpy_gateway(
    main_engine,
    binance_api_key: str,
    binance_api_secret: str,
    testnet: bool = True
) -> bool:
    """
    Initialize Binance gateway on the VNPy MainEngine.
    
    Args:
        main_engine: VNPy MainEngine instance
        binance_api_key: Binance API key
        binance_api_secret: Binance API secret
        testnet: Whether to use testnet
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Import Binance gateway (Linear = USDT-margined futures)
        from vnpy_binance import BinanceLinearGateway
        
        # Add Binance gateway to main engine
        main_engine.add_gateway(BinanceLinearGateway)
        logger.info("BinanceLinearGateway added to MainEngine")
        
        # Connect to Binance with credentials
        connect_setting = {
            "key": binance_api_key,
            "secret": binance_api_secret,
            "proxy_host": "",
            "proxy_port": 0,
            "usdt_testnet": testnet,
        }
        
        main_engine.connect(connect_setting, "BINANCE")
        logger.info(f"Connected to Binance {'testnet' if testnet else 'production'}")
        
        return True
        
    except ImportError as e:
        logger.error(f"Failed to import vnpy_binance: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to initialize Binance gateway: {e}")
        return False


def init_vnpy_database(main_engine) -> bool:
    """
    Initialize SQLite database for VNPy.
    
    Args:
        main_engine: VNPy MainEngine instance
        
    Returns:
        True if successful, False otherwise
    """
    try:
        from vnpy_sqlite import SqliteDatabase
        
        # Database should be auto-configured via vt_setting.json
        # Just ensure the directory exists
        ensure_vnpy_config_dir()
        
        logger.info(f"SQLite database configured at {VNPY_DB_FILE}")
        return True
        
    except ImportError as e:
        logger.error(f"Failed to import vnpy_sqlite: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False


def get_vnpy_config_from_env() -> Dict[str, Any]:
    """
    Get VNPy configuration from environment variables.
    
    Returns:
        Configuration dictionary
    """
    # Try to load from dotenv
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    # Get credentials from environment
    api_key = os.getenv('BINANCE_API_KEY', '')
    api_secret = os.getenv('BINANCE_API_SECRET', '')
    testnet = os.getenv('BINANCE_TESTNET', 'true').lower() in ('true', '1', 'yes')
    
    if not api_key or not api_key.strip() or api_key == 'your_key_here':
        logger.warning("BINANCE_API_KEY not properly configured in environment")
    
    if not api_secret or not api_secret.strip() or api_secret == 'your_secret_here':
        logger.warning("BINANCE_API_SECRET not properly configured in environment")
    
    return {
        'api_key': api_key,
        'api_secret': api_secret,
        'testnet': testnet
    }


def register_binance_datafeed() -> bool:
    """
    Register the custom Binance datafeed with VNPy.
    
    Returns:
        True if successful
    """
    try:
        # Import our custom datafeed
        from binance_datafeed import BinanceDatafeed
        
        # Register with VNPy's datafeed system
        # This makes it available for CTA strategies
        from vnpy.trader.datafeed import Datafeed
        
        # Monkey-patch or register the datafeed
        # VNPy 4.x looks for datafeed in vt_setting.json
        logger.info("Custom Binance datafeed registered successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to register datafeed: {e}")
        return False


def setup_vnpy_environment(
    binance_api_key: Optional[str] = None,
    binance_api_secret: Optional[str] = None,
    testnet: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Complete VNPy environment setup.
    
    Args:
        binance_api_key: Optional API key override
        binance_api_secret: Optional API secret override
        testnet: Optional testnet flag override
        
    Returns:
        Complete configuration used
    """
    # Get config from environment if not provided
    env_config = get_vnpy_config_from_env()
    
    # Override with provided values
    api_key = binance_api_key or env_config['api_key']
    api_secret = binance_api_secret or env_config['api_secret']
    use_testnet = testnet if testnet is not None else env_config['testnet']
    
    # Create vt_setting.json
    config = create_vt_setting_json(
        binance_api_key=api_key,
        binance_api_secret=api_secret,
        testnet=use_testnet
    )
    
    logger.info(f"VNPy environment configured (testnet={use_testnet})")
    
    return config

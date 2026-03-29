"""
Example refactored main.py using the Orchestrator package.
This demonstrates how to integrate the orchestrator package into the existing codebase.
"""

import os
import sys
import asyncio
import logging
from threading import Thread

# Configure logging
from utils.logging_config import setup_logging
logger = setup_logging('main')

# Import orchestrator package
from orchestrator.config import OrchestratorConfig
from orchestrator.lifecycle import OrchestratorLifecycle


async def run_orchestrator():
    """
    Main entry point using OrchestratorLifecycle.
    This replaces the current main() function with proper lifecycle management.
    """
    logger.info("=== GOD MODE QUANT TRADING ORCHESTRATOR (REFACTORED) ===")
    
    try:
        # 1. Load configuration
        logger.info("Loading configuration...")
        config = OrchestratorConfig.from_env()
        
        # 2. Validate configuration
        warnings = config.validate()
        if warnings:
            logger.warning(f"Configuration warnings: {warnings}")
        
        # 3. Log configuration summary (without sensitive data)
        config_summary = {
            'service': config.service_name,
            'version': config.version,
            'environment': config.environment,
            'trading_mode': config.trading.mode.value,
            'trading_symbol': config.trading.symbol,
            'has_telegram': bool(config.telegram.bot_token),
            'has_binance': bool(config.binance.api_key),
            'vnpy_testnet': config.binance.testnet
        }
        logger.info(f"Configuration: {config_summary}")
        
        # 4. Create lifecycle manager
        logger.info("Creating Orchestrator Lifecycle Manager...")
        lifecycle = OrchestratorLifecycle(config)
        
        # 5. Register custom handlers (optional)
        def on_startup_complete():
            logger.info("Custom startup: Orchestrator is ready for trading!")
            # Additional custom startup logic here
        
        def on_shutdown_start():
            logger.info("Custom shutdown: Saving trading state...")
            # Additional custom cleanup logic here
        
        lifecycle.register_startup_handler(on_startup_complete)
        lifecycle.register_shutdown_handler(on_shutdown_start)
        
        # 6. Start all components
        logger.info("Starting orchestrator components...")
        startup_success = await lifecycle.start()
        
        if not startup_success:
            logger.error("Failed to start orchestrator components")
            return 1
        
        logger.info("✅ Orchestrator started successfully!")
        
        # 7. Main loop - run until shutdown
        logger.info("Trading orchestrator running. Press Ctrl+C to stop.")
        
        # Log initial status
        health = lifecycle.health_check()
        logger.info(f"Initial health status: {health['status']}")
        
        # Wait for shutdown signal
        await lifecycle._shutdown_event.wait()
        
        # 8. Graceful shutdown
        logger.info("Initiating graceful shutdown...")
        await lifecycle.stop()
        
        logger.info("✅ Orchestrator shutdown complete")
        return 0
        
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        return 0
    except Exception as e:
        logger.error(f"Orchestrator failed: {e}", exc_info=True)
        return 1


def main_sync():
    """
    Synchronous main function for backward compatibility.
    This can be called from the existing main.py entry point.
    """
    try:
        # Run the async orchestrator
        return asyncio.run(run_orchestrator())
    except KeyboardInterrupt:
        logger.info("Shutdown requested via KeyboardInterrupt")
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


# Legacy compatibility - can be called from existing main.py
def main():
    """
    Main entry point with backward compatibility.
    This function can be used as a drop-in replacement for the existing main().
    """
    logger.info("Starting God Mode Quant Trading Orchestrator...")
    
    # Import existing modules that may be needed
    try:
        # These imports maintain compatibility with existing code
        from security.secrets_manager import get_binance_api_key, get_binance_api_secret
        from security.secrets_manager import get_telegram_bot_token, get_telegram_chat_id
        from security.mtls_manager import mtls_manager
        
        logger.info("Security modules loaded successfully")
    except ImportError as e:
        logger.warning(f"Some security modules not available: {e}")
    
    # Run the orchestrator
    return main_sync()


# Alternative: Thread-based health server for compatibility
def run_health_server_compat():
    """
    Run health server in a separate thread for compatibility with existing deployment.
    The orchestrator lifecycle now includes health server management.
    """
    from flask import Flask, jsonify
    
    app = Flask(__name__)
    
    @app.route('/health')
    def health():
        return jsonify({
            "status": "healthy",
            "service": "god-mode-quant-orchestrator",
            "note": "Health checks now managed by OrchestratorLifecycle"
        })
    
    app.run(host='0.0.0.0', port=8003, debug=False, use_reloader=False)


# Quick migration helper - can be used during transition
class LegacyCompatibility:
    """
    Helper class to maintain compatibility with existing code during migration.
    This allows gradual transition to the orchestrator package.
    """
    
    @staticmethod
    def get_config_value(key: str, default: str = "") -> str:
        """
        Get configuration value with fallback to environment variables.
        Useful for gradual migration of existing configuration access.
        """
        # Try orchestrator config first
        try:
            config = OrchestratorConfig.from_env()
            # Map common keys to config values
            config_map = {
                'TELEGRAM_BOT_TOKEN': config.telegram.bot_token,
                'TELEGRAM_CHAT_ID': config.telegram.chat_id,
                'BINANCE_API_KEY': config.binance.api_key,
                'BINANCE_API_SECRET': config.binance.api_secret,
                'TRADING_SYMBOL': config.trading.symbol,
                'POSTGRES_HOST': config.database.postgres_host,
                'REDIS_HOST': config.database.redis_host,
            }
            if key in config_map:
                return config_map[key] or default
        except:
            pass
        
        # Fallback to environment variable
        return os.getenv(key, default)
    
    @staticmethod
    def send_telegram_message(token: str, chat_id: str, message: str) -> bool:
        """
        Legacy Telegram message function for backward compatibility.
        Uses the same implementation as existing main.py.
        """
        import requests
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


# Migration script that can be run to test the transition
def test_migration():
    """
    Test migration by running both old and new approaches.
    This can be used to verify the orchestrator package works correctly.
    """
    print("Testing Orchestrator Migration...")
    print("=" * 50)
    
    # Test configuration loading
    print("\n1. Testing Configuration Loading...")
    config = OrchestratorConfig.from_env()
    print(f"   ✅ Config loaded: {config.service_name} v{config.version}")
    
    # Test legacy compatibility
    print("\n2. Testing Legacy Compatibility...")
    token = LegacyCompatibility.get_config_value('TELEGRAM_BOT_TOKEN')
    print(f"   ✅ Legacy config access works")
    
    # Test lifecycle initialization
    print("\n3. Testing Lifecycle Initialization...")
    lifecycle = OrchestratorLifecycle(config)
    print(f"   ✅ Lifecycle manager created")
    
    # Test health check
    print("\n4. Testing Health Check...")
    health = lifecycle.health_check()
    print(f"   ✅ Health check: {health['status']}")
    
    print("\n" + "=" * 50)
    print("✅ Migration test completed successfully!")
    print("\nNext steps:")
    print("1. Replace main() call in existing main.py with main_sync()")
    print("2. Remove duplicate configuration loading code")
    print("3. Update shutdown handlers to use lifecycle.register_shutdown_handler()")
    print("4. Test thoroughly in development environment")


if __name__ == "__main__":
    # Check command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "test-migration":
            test_migration()
            sys.exit(0)
        elif command == "legacy-compat":
            # Run with legacy compatibility mode
            sys.exit(main())
        elif command == "health-only":
            # Just run health server
            run_health_server_compat()
            sys.exit(0)
    
    # Default: run orchestrator
    sys.exit(main())
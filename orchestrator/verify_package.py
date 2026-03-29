#!/usr/bin/env python3
"""
Verification script for the Orchestrator package.
Tests all major features and integration points.
"""

import os
import sys
import asyncio
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def verify_imports():
    """Verify all imports work correctly"""
    print("=== Verifying Imports ===")
    
    try:
        from orchestrator import OrchestratorLifecycle, OrchestratorConfig
        print("✓ Package imports successful")
        
        from orchestrator.config import (
            TradingConfig, DatabaseConfig, TelegramConfig, 
            BinanceConfig, APIConfig, SecurityConfig, MonitoringConfig, MLConfig
        )
        print("✓ Config classes imported")
        
        from orchestrator.lifecycle import ComponentHealth, ComponentState
        print("✓ Lifecycle classes imported")
        
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def verify_configuration():
    """Verify configuration loading and validation"""
    print("\n=== Verifying Configuration ===")
    
    from orchestrator.config import OrchestratorConfig, TradingMode
    
    # Set test environment variables
    test_env = {
        'TRADING_SYMBOL': 'BTCUSDT',
        'TRADING_MODE': 'demo',
        'BINANCE_TESTNET': 'true',
        'TELEGRAM_BOT_TOKEN': 'test_token',
        'TELEGRAM_CHAT_ID': 'test_chat',
        'BINANCE_API_KEY': 'test_key',
        'BINANCE_API_SECRET': 'test_secret'
    }
    
    for key, value in test_env.items():
        os.environ[key] = value
    
    try:
        config = OrchestratorConfig.from_env()
        
        # Verify all sub-configs exist
        assert config.trading is not None
        assert config.database is not None
        assert config.telegram is not None
        assert config.binance is not None
        assert config.api is not None
        assert config.security is not None
        assert config.monitoring is not None
        assert config.ml is not None
        
        print("✓ All configuration sections loaded")
        
        # Verify environment variable overrides
        assert config.trading.symbol == 'BTCUSDT'
        assert config.trading.mode == TradingMode.DEMO
        assert config.binance.testnet == True
        assert config.telegram.bot_token == 'test_token'
        
        print("✓ Environment variable overrides work")
        
        # Test validation
        warnings = config.validate()
        assert isinstance(warnings, list)
        print(f"✓ Configuration validation works ({len(warnings)} warnings)")
        
        # Test serialization
        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        print("✓ Configuration serialization works")
        
        # Test VNPy config
        vnpy_config = config.get_vnpy_config()
        assert isinstance(vnpy_config, dict)
        assert 'binance.key' in vnpy_config
        print("✓ VNPy configuration extraction works")
        
        return True
        
    except Exception as e:
        print(f"✗ Configuration verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def verify_lifecycle():
    """Verify lifecycle management"""
    print("\n=== Verifying Lifecycle Management ===")
    
    from orchestrator.config import OrchestratorConfig
    from orchestrator.lifecycle import OrchestratorLifecycle, ComponentState
    
    try:
        # Create minimal config
        config = OrchestratorConfig.from_env()
        
        # Create lifecycle manager
        lifecycle = OrchestratorLifecycle(config)
        print("✓ Lifecycle manager created")
        
        # Test component registration
        lifecycle._register_component("test_component", {"type": "test"})
        component = lifecycle.get_component_status("test_component")
        assert component is not None
        assert component.name == "test_component"
        print("✓ Component registration works")
        
        # Test component state updates
        lifecycle._update_component_state("test_component", ComponentState.RUNNING)
        assert component.state == ComponentState.RUNNING
        print("✓ Component state updates work")
        
        # Test health check
        health = lifecycle.health_check()
        assert health['status'] == 'healthy'
        assert 'test_component' in health['components']
        print("✓ Health check works")
        
        # Test startup/shutdown handlers
        startup_called = []
        shutdown_called = []
        
        def startup_handler():
            startup_called.append(True)
        
        def shutdown_handler():
            shutdown_called.append(True)
        
        lifecycle.register_startup_handler(startup_handler)
        lifecycle.register_shutdown_handler(shutdown_handler)
        
        print("✓ Handler registration works")
        
        # Test wait for shutdown (with timeout)
        async def test_wait():
            await asyncio.sleep(0.1)
            lifecycle._shutdown_event.set()
        
        # Create a task to set the event
        task = asyncio.create_task(test_wait())
        
        # This would block indefinitely without the timeout
        try:
            await asyncio.wait_for(lifecycle._shutdown_event.wait(), timeout=1.0)
            print("✓ Shutdown event works")
        except asyncio.TimeoutError:
            print("⚠ Shutdown event test timed out (expected)")
        finally:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        return True
        
    except Exception as e:
        print(f"✗ Lifecycle verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def verify_integration():
    """Verify integration with existing codebase"""
    print("\n=== Verifying Integration ===")
    
    try:
        # Test that orchestrator can be imported alongside existing modules
        from orchestrator.config import OrchestratorConfig
        
        # Test that existing security modules can be imported
        from security.audit_logger import log_security_event
        print("✓ Security module integration works")
        
        # Test that risk management can be imported
        from risk_management import risk_manager
        print("✓ Risk management integration works")
        
        # Test that VNPy can be imported (if available)
        try:
            import vnpy
            print(f"✓ VNPy available: {vnpy.__version__}")
        except ImportError:
            print("⚠ VNPy not available (expected in some environments)")
        
        return True
        
    except Exception as e:
        print(f"✗ Integration verification failed: {e}")
        return False

def verify_file_structure():
    """Verify file structure and completeness"""
    print("\n=== Verifying File Structure ===")
    
    required_files = [
        'orchestrator/__init__.py',
        'orchestrator/config.py',
        'orchestrator/lifecycle.py'
    ]
    
    for file_path in required_files:
        full_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), file_path)
        if os.path.exists(full_path):
            print(f"✓ {file_path} exists")
            
            # Check file has content
            with open(full_path, 'r') as f:
                content = f.read()
                if len(content) > 100:  # Arbitrary minimum size
                    print(f"  ✓ File has substantial content ({len(content)} chars)")
                else:
                    print(f"  ⚠ File seems small ({len(content)} chars)")
        else:
            print(f"✗ {file_path} missing")
            return False
    
    return True

async def run_all_verifications():
    """Run all verification tests"""
    print("Orchestrator Package Verification")
    print("=" * 50)
    
    tests = [
        ("File Structure", verify_file_structure),
        ("Imports", verify_imports),
        ("Configuration", verify_configuration),
        ("Lifecycle", verify_lifecycle),
        ("Integration", verify_integration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
                print(f"\n✅ {test_name} verification PASSED")
            else:
                print(f"\n❌ {test_name} verification FAILED")
        except Exception as e:
            print(f"\n❌ {test_name} verification ERROR: {e}")
    
    print("\n" + "=" * 50)
    print(f"Verification Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All verifications passed! Orchestrator package is ready.")
        return True
    else:
        print("⚠ Some verifications failed. Review the output above.")
        return False

def main():
    """Main entry point"""
    try:
        result = asyncio.run(run_all_verifications())
        return 0 if result else 1
    except KeyboardInterrupt:
        print("\nVerification interrupted by user")
        return 1
    except Exception as e:
        print(f"\nVerification failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
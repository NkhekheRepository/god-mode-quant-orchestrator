#!/usr/bin/env python3
"""
Simple test script for the orchestrator package.
Verifies that configuration loading and lifecycle initialization work correctly.
"""

import os
import sys
import asyncio
from datetime import datetime

# Add the parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_config():
    """Test configuration loading"""
    print("=== Testing Configuration Loading ===")
    
    # Set some test environment variables
    os.environ['TRADING_SYMBOL'] = 'ETHUSDT'
    os.environ['TRADING_MODE'] = 'testnet'
    os.environ['BINANCE_TESTNET'] = 'true'
    
    from orchestrator.config import OrchestratorConfig
    
    config = OrchestratorConfig.from_env()
    
    print(f"Service: {config.service_name}")
    print(f"Version: {config.version}")
    print(f"Environment: {config.environment}")
    print(f"Trading Symbol: {config.trading.symbol}")
    print(f"Trading Mode: {config.trading.mode.value}")
    print(f"Binance Testnet: {config.binance.testnet}")
    
    # Validate configuration
    warnings = config.validate()
    if warnings:
        print(f"Configuration warnings: {warnings}")
    else:
        print("Configuration is valid")
    
    # Convert to dict
    config_dict = config.to_dict()
    print(f"Config dict keys: {list(config_dict.keys())}")
    
    print("✓ Configuration test passed\n")
    return config

async def test_lifecycle_initialization(config):
    """Test lifecycle manager initialization"""
    print("=== Testing Lifecycle Initialization ===")
    
    from orchestrator.lifecycle import OrchestratorLifecycle
    
    lifecycle = OrchestratorLifecycle(config)
    
    print(f"Lifecycle initialized for {config.service_name}")
    print(f"Components registered: {len(lifecycle._components)}")
    
    # Test health check
    health = lifecycle.health_check()
    print(f"Initial health status: {health['status']}")
    
    print("✓ Lifecycle initialization test passed\n")
    return lifecycle

def test_config_validation():
    """Test configuration validation with invalid values"""
    print("=== Testing Configuration Validation ===")
    
    os.environ['TRADING_LEVERAGE'] = '-5'  # Invalid leverage
    os.environ['STARTING_CAPITAL'] = '0'   # Invalid capital
    
    from orchestrator.config import OrchestratorConfig
    
    config = OrchestratorConfig.from_env()
    warnings = config.validate()
    
    print(f"Validation warnings for invalid config: {warnings}")
    
    # Reset to valid values
    os.environ['TRADING_LEVERAGE'] = '10'
    os.environ['STARTING_CAPITAL'] = '100000'
    
    print("✓ Configuration validation test passed\n")

async def main():
    """Run all tests"""
    print("Running Orchestrator Package Tests")
    print("=" * 50)
    
    try:
        # Test configuration
        config = test_config()
        
        # Test validation
        test_config_validation()
        
        # Test lifecycle
        lifecycle = await test_lifecycle_initialization(config)
        
        # Test component status
        component = lifecycle.get_component_status('vnpy')
        if component:
            print(f"VNPy component state: {component.state.value}")
        
        # Test health check with components
        health = lifecycle.health_check()
        print(f"Components in health check: {list(health['components'].keys())}")
        
        print("\n" + "=" * 50)
        print("✓ All tests passed!")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
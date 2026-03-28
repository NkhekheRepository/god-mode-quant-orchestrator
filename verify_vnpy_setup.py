#!/usr/bin/env python3
"""
VNPy Setup Verification Script for God Mode Quant Trading Orchestrator
Verifies that all components are properly configured.
"""
import os
import sys
import json
from pathlib import Path

# Add project directory to path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

def print_status(name: str, status: bool, message: str = ""):
    """Print formatted status message."""
    icon = "✓" if status else "✗"
    status_str = "OK" if status else "FAILED"
    print(f"  [{icon}] {name}: {status_str}" + (f" - {message}" if message else ""))

def check_vnpy_imports():
    """Check VNPy package imports."""
    print("\n1. Checking VNPy Package Imports:")
    
    try:
        import vnpy
        print_status("vnpy", True, f"version {vnpy.__version__}")
    except ImportError as e:
        print_status("vnpy", False, str(e))
        return False
    
    try:
        from vnpy.event import EventEngine
        print_status("vnpy.event.EventEngine", True)
    except ImportError as e:
        print_status("vnpy.event.EventEngine", False, str(e))
        return False
    
    try:
        from vnpy.trader.engine import MainEngine
        print_status("vnpy.trader.engine.MainEngine", True)
    except ImportError as e:
        print_status("vnpy.trader.engine.MainEngine", False, str(e))
        return False
    
    try:
        from vnpy_ctastrategy import CtaStrategyApp
        print_status("vnpy_ctastrategy.CtaStrategyApp", True)
    except ImportError as e:
        print_status("vnpy_ctastrategy.CtaStrategyApp", False, str(e))
        return False
    
    try:
        from vnpy_binance import BinanceLinearGateway
        print_status("vnpy_binance.BinanceLinearGateway", True)
    except ImportError as e:
        print_status("vnpy_binance.BinanceLinearGateway", False, str(e))
        return False
    
    try:
        import vnpy_sqlite
        print_status("vnpy_sqlite", True)
    except ImportError as e:
        print_status("vnpy_sqlite", False, str(e))
        return False
    
    return True

def check_env_variables():
    """Check environment variables."""
    print("\n2. Checking Environment Variables:")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print_status("python-dotenv", False, "Not installed")
    
    api_key = os.getenv('BINANCE_API_KEY', '')
    api_secret = os.getenv('BINANCE_API_SECRET', '')
    testnet = os.getenv('BINANCE_TESTNET', 'true').lower() in ('true', '1', 'yes')
    
    api_key_set = bool(api_key) and api_key not in ('', 'your_key_here')
    api_secret_set = bool(api_secret) and api_secret not in ('', 'your_secret_here')
    
    print_status("BINANCE_API_KEY", api_key_set, 
                  "Configured" if api_key_set else "NOT SET - Update .env file")
    print_status("BINANCE_API_SECRET", api_secret_set,
                  "Configured" if api_secret_set else "NOT SET - Update .env file")
    print_status("BINANCE_TESTNET", True, f"{'Testnet' if testnet else 'Production'} mode")
    
    return api_key_set and api_secret_set

def check_vt_setting():
    """Check VNPy configuration file."""
    print("\n3. Checking VNPy Configuration:")
    
    config_path = Path.home() / ".vntrader" / "vt_setting.json"
    
    if not config_path.exists():
        print_status("vt_setting.json", False, f"File not found at {config_path}")
        return False
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        print_status("vt_setting.json", True, f"Found at {config_path}")
        
        # Check required settings
        required_settings = [
            "database.driver",
            "datafeed.name",
            "binance.usdt_address",
        ]
        
        for setting in required_settings:
            if setting in config:
                print_status(f"  {setting}", True, str(config[setting]))
            else:
                print_status(f"  {setting}", False, "Missing")
                return False
        
        return True
        
    except Exception as e:
        print_status("vt_setting.json", False, str(e))
        return False

def check_strategy_import():
    """Check strategy import."""
    print("\n4. Checking Strategy Import:")
    
    try:
        from strategies.ma_crossover_strategy import MaCrossoverStrategy
        print_status("MaCrossoverStrategy", True)
        return True
    except ImportError as e:
        print_status("MaCrossoverStrategy", False, str(e))
        return False

def test_mainengine_creation():
    """Test MainEngine creation."""
    print("\n5. Testing MainEngine Creation:")
    
    try:
        from vnpy.event import EventEngine
        from vnpy.trader.engine import MainEngine
        from vnpy_binance import BinanceLinearGateway
        
        event_engine = EventEngine()
        main_engine = MainEngine(event_engine)
        main_engine.add_gateway(BinanceLinearGateway)
        
        print_status("EventEngine creation", True)
        print_status("MainEngine creation", True)
        print_status("BinanceLinearGateway added", True)
        
        # Clean up
        main_engine.close()
        
        return True
        
    except Exception as e:
        print_status("MainEngine test", False, str(e))
        return False

def main():
    """Run all verification checks."""
    print("=" * 60)
    print("VNPy Setup Verification for God Mode Quant Orchestrator")
    print("=" * 60)
    
    results = []
    
    # Run all checks
    results.append(("VNPy Imports", check_vnpy_imports()))
    results.append(("Environment Variables", check_env_variables()))
    results.append(("VNPy Configuration", check_vt_setting()))
    results.append(("Strategy Import", check_strategy_import()))
    results.append(("MainEngine Test", test_mainengine_creation()))
    
    # Print summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        icon = "✓" if passed else "✗"
        print(f"  [{icon}] {name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL CHECKS PASSED - System ready for trading!")
    else:
        print("✗ SOME CHECKS FAILED - Please fix the issues above")
        print("\nNext steps:")
        if not results[1][1]:  # Environment variables
            print("  1. Edit .env file and set BINANCE_API_KEY and BINANCE_API_SECRET")
        if not results[4][1]:  # MainEngine test
            print("  2. Check VNPy package installation")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())

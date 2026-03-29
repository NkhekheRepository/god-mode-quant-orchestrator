# Testing Guide

> Comprehensive guide to the test suite for the GodMode Quant Trading Orchestrator

## Test Organization

All tests are located in the `tests/` directory and follow a consistent structure:

```
tests/
├── __init__.py
├── test_integration.py      # End-to-end integration tests
├── test_risk_management.py  # Risk management unit tests
└── test_paper_trading.py    # Paper trading and strategy tests
```

### Test Categories

| File | Purpose | What's Tested |
|------|---------|----------------|
| `test_integration.py` | Integration tests | Full system startup/shutdown, risk management integration, security component integration |
| `test_risk_management.py` | Unit tests | Position sizing, portfolio management, risk limits, alerts |
| `test_paper_trading.py` | Unit tests | Strategy logic, component initialization, ML imports, Docker configuration |

## Running Tests

### Basic Commands

Run the entire test suite with verbose output:

```bash
pytest tests/ -v
```

Run tests for a specific file:

```bash
pytest tests/test_risk_management.py -v
```

Run a specific test class:

```bash
pytest tests/test_integration.py::TestIntegration -v
```

Run a specific test method:

```bash
pytest tests/test_integration.py::TestIntegration::test_risk_management_integration -v
```

### Common Options

- `-v` or `--verbose`: Verbose output with test names
- `-x` or `--exitfirst`: Stop on first failure
- `--tb=short`: Shorter traceback output
- `-k "keyword"`: Run tests matching keyword (e.g., `-k "risk"` runs all risk tests)

### Environment Setup

Before running tests, ensure:

1. **Virtual environment activated** (if using one)
2. **Dependencies installed**: `pip install -r requirements.txt`
3. **Environment variables set**: Copy `.env.example` to `.env` (mock tests will override sensitive values)

## Mocking Patterns

The test suite uses extensive mocking to isolate components and avoid external dependencies.

### Common Mocking Patterns

#### 1. VNPy Module Mocking

VNPy modules are mocked before import to avoid requiring the full VNPy installation:

```python
import sys
from unittest.mock import Mock

# Pre-mock VNPy modules
mock_vnpy = Mock()
mock_vnpy.__version__ = "3.0.0"
sys.modules['vnpy'] = mock_vnpy
sys.modules['vnpy.event'] = Mock()
sys.modules['vnpy.trader'] = Mock()
sys.modules['vnpy.trader.engine'] = Mock()
sys.modules['vnpy.trader.object'] = Mock()
sys.modules['vnpy.trader.constant'] = Mock()
sys.modules['vnpy_ctastrategy'] = Mock()
```

#### 2. External Service Mocking

Network calls (Telegram, exchanges) are mocked:

```python
@patch('requests.post')
def test_telegram_notification(self, mock_post):
    mock_post.return_value = Mock(status_code=200)
    # Test code that sends Telegram notification
```

#### 3. Environment Variable Mocking

Environment variables are mocked for isolated testing:

```python
@patch.dict('os.environ', {
    'TELEGRAM_BOT_TOKEN': 'test_token',
    'TELEGRAM_CHAT_ID': 'test_chat_id',
    'VAULT_ADDR': '',
    'VAULT_TOKEN': ''
})
def test_with_env_vars(self):
    # Test that uses environment variables
```

#### 4. Time Delay Mocking

`time.sleep` is mocked to speed up tests:

```python
@patch('time.sleep')
def test_with_delays(self, mock_sleep):
    # Test that includes time.sleep calls
```

#### 5. File System Mocking

File operations are mocked when needed:

```python
@patch('builtins.open', mock_open(read_data='{"key": "value"}'))
def test_file_reading(self):
    # Test code that reads files
```

### Test Structure Patterns

#### Standard Test Class

```python
import unittest
from unittest.mock import Mock, patch

class TestFeature(unittest.TestCase):
    """Test feature functionality"""
    
    def setUp(self):
        """Set up test fixtures before each test"""
        # Initialize mocks, test data, etc.
        pass
    
    def tearDown(self):
        """Clean up after each test"""
        # Stop patches, reset state
        pass
    
    def test_expected_behavior(self):
        """Test that feature behaves as expected"""
        # Arrange
        # Act
        # Assert
        self.assertEqual(expected, actual)

if __name__ == '__main__':
    unittest.main()
```

#### Integration Test Pattern

Integration tests often use threading to test full system behavior:

```python
def test_system_startup(self):
    """Test that the system starts up correctly"""
    
    def run_system():
        # Start the system in a separate thread
        import main
        main.main()
    
    system_thread = threading.Thread(target=run_system)
    system_thread.daemon = True
    system_thread.start()
    
    # Wait for initialization
    system_thread.join(timeout=2.0)
    
    # Verify initialization occurred
    self.assertTrue(system_initialized)
```

## Writing New Tests

### Guidelines

1. **Isolate tests**: Each test should be independent and not rely on other tests.
2. **Mock external dependencies**: Never make real network calls or file system operations.
3. **Use descriptive names**: Test names should clearly indicate what's being tested.
4. **Include docstrings**: Explain the purpose of each test method.
5. **Clean up resources**: Use `setUp` and `tearDown` properly.

### Adding a New Test File

1. Create a new file in `tests/` with `test_` prefix (e.g., `test_new_feature.py`).
2. Import `unittest` and necessary mocking utilities.
3. Create a test class inheriting from `unittest.TestCase`.
4. Add test methods with `test_` prefix.
5. Update `__init__.py` if needed (optional, pytest will auto-discover).

### Test Coverage

While not currently enforced, aim for:
- **Critical paths**: 100% coverage for risk management, security, core trading logic
- **New features**: Include tests for any new functionality
- **Bug fixes**: Add regression tests to prevent future breakage

## Continuous Integration

Tests are automatically run on:
- Pull request creation/update
- Direct pushes to `main` branch
- Scheduled nightly runs (if configured)

## Debugging Failed Tests

1. **Run with verbose output**: `pytest tests/ -v`
2. **Check mock setup**: Ensure all dependencies are properly mocked.
3. **Review test isolation**: Tests may be interfering with each other.
4. **Verify environment**: Ensure `.env` is properly configured (or mocked).

For integration test failures, check:
- Thread timing issues (adjust timeouts)
- Mock call sequences
- Environment variable overrides

## Further Reading

- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines including testing requirements
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture overview
- [pytest documentation](https://docs.pytest.org/) - Official pytest documentation
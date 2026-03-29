# Orchestrator Package

Modular monolith phase 1: Extracts orchestrator lifecycle management from main.py into a reusable package.

## Overview

The Orchestrator package provides centralized configuration management and lifecycle orchestration for the GodMode Quant Trading Orchestrator. It implements the modular monolith pattern, preparing the codebase for eventual decomposition into microservices while maintaining simplicity for the current team size.

## Package Structure

```
orchestrator/
├── __init__.py              # Package exports
├── config.py                # Configuration management
├── lifecycle.py             # Lifecycle orchestration
├── example_usage.py         # Usage examples
├── test_orchestrator.py     # Unit tests
└── verify_package.py        # Package verification
```

## Key Components

### 1. Configuration Management (`config.py`)

Centralized configuration that loads and validates all orchestrator settings from environment variables:

- **TradingConfig**: Symbol, interval, capital, leverage, risk limits
- **DatabaseConfig**: PostgreSQL and Redis connections
- **TelegramConfig**: Notification settings
- **BinanceConfig**: Exchange API settings
- **APIConfig**: Health server, metrics, authentication
- **SecurityConfig**: SSL, JWT, secrets management
- **MonitoringConfig**: Prometheus, Sentry, OpenTelemetry
- **MLConfig**: Machine learning settings

### 2. Lifecycle Management (`lifecycle.py`)

Orchestrates startup and shutdown of all components:

- **Component Registration**: Track health of all managed components
- **Startup Sequence**: Initialize components in proper dependency order
- **Shutdown Sequence**: Graceful shutdown with cleanup
- **Health Monitoring**: Continuous health checks and alerts
- **Signal Handling**: OS signal handling for graceful shutdown
- **Background Tasks**: Periodic maintenance and monitoring tasks

## Usage

### Basic Usage

```python
from orchestrator.config import OrchestratorConfig
from orchestrator.lifecycle import OrchestratorLifecycle

# Load configuration from environment
config = OrchestratorConfig.from_env()

# Validate configuration
warnings = config.validate()
if warnings:
    print(f"Configuration warnings: {warnings}")

# Create lifecycle manager
lifecycle = OrchestratorLifecycle(config)

# Start all components
await lifecycle.start()

# Wait for shutdown signal
await lifecycle._shutdown_event.wait()

# Graceful shutdown
await lifecycle.stop()
```

### Advanced Usage

```python
# Register custom handlers
lifecycle.register_startup_handler(my_startup_function)
lifecycle.register_shutdown_handler(my_cleanup_function)

# Check component health
health = lifecycle.health_check()
if health['status'] == 'healthy':
    print("All systems operational")

# Get specific component status
component = lifecycle.get_component_status('vnpy')
if component.state == ComponentState.RUNNING:
    print("VNPy is running")
```

## Configuration

All configuration is loaded from environment variables. See `.env.example` for available options.

### Environment Variables

```bash
# Trading
TRADING_SYMBOL=BTCUSDT
TRADING_MODE=demo  # live, testnet, demo, paper
STARTING_CAPITAL=100000
MAX_LEVERAGE=10

# Database
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
REDIS_HOST=redis
REDIS_PORT=6379

# Telegram
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id

# Binance
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
BINANCE_TESTNET=true
```

## Integration with Existing Code

### Step 1: Replace Configuration Loading

**Before (main.py):**
```python
telegram_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
binance_key = os.getenv('BINANCE_API_KEY', '')
# ... many more environment variables
```

**After (main.py):**
```python
from orchestrator.config import OrchestratorConfig

config = OrchestratorConfig.from_env()
telegram_token = config.telegram.bot_token
binance_key = config.binance.api_key
```

### Step 2: Replace Startup Logic

**Before (main.py):**
```python
def main():
    # Initialize security
    from security.mtls_manager import mtls_manager
    # Initialize VNPy
    # Initialize Telegram
    # ... 100+ lines of initialization
```

**After (main.py):**
```python
from orchestrator.lifecycle import OrchestratorLifecycle

async def main():
    config = OrchestratorConfig.from_env()
    lifecycle = OrchestratorLifecycle(config)
    await lifecycle.start()
    await lifecycle._shutdown_event.wait()
    await lifecycle.stop()
```

### Step 3: Replace Shutdown Logic

**Before (main.py):**
```python
def graceful_shutdown():
    global _shutdown_in_progress
    if _shutdown_in_progress:
        return
    _shutdown_in_progress = True
    # ... shutdown logic
```

**After (main.py):**
```python
# Handled automatically by OrchestratorLifecycle
# with proper signal handling and cleanup
```

## Benefits

1. **Separation of Concerns**: Configuration, lifecycle, and business logic separated
2. **Testability**: Each component can be tested independently
3. **Maintainability**: Single responsibility principle
4. **Scalability**: Ready for microservice extraction when needed
5. **Consistency**: Standardized component lifecycle management
6. **Observability**: Built-in health checks and metrics

## Development

### Running Tests

```bash
# Run unit tests
python orchestrator/test_orchestrator.py

# Run verification
python orchestrator/verify_package.py

# Run examples
python orchestrator/example_usage.py
```

### Adding New Components

1. Register component in lifecycle:
   ```python
   self._register_component("new_component", {"type": "service"})
   ```

2. Add startup logic:
   ```python
   async def _start_new_component(self):
       # Initialization code
       self._update_component_state("new_component", ComponentState.RUNNING)
   ```

3. Add shutdown logic:
   ```python
   async def _stop_new_component(self):
       # Cleanup code
       self._update_component_state("new_component", ComponentState.STOPPED)
   ```

## Roadmap

### Phase 1: Modular Monolith (Current)
- Extract lifecycle management
- Centralize configuration
- Maintain single deployment unit

### Phase 2: Service Extraction
- Extract trading engine as separate service
- Extract Telegram bot as separate service
- Extract ML service as separate service

### Phase 3: Microservices
- Event-driven communication
- Independent scaling
- Service mesh integration

## Architecture Decision Records

See `ADR-001-orchestrator-lifecycle.md` for detailed design decisions.

## License

Part of the GodMode Quant Trading Orchestrator project.
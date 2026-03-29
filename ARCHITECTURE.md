# Architecture Guide

> Detailed system architecture for the God Mode Quant Trading Orchestrator

## Table of Contents

- [High-Level Overview](#high-level-overview)
- [Component Architecture](#component-architecture)
- [Data Flow](#data-flow)
- [Security Architecture](#security-architecture)
- [Monitoring Architecture](#monitoring-architecture)
- [Infrastructure](#infrastructure)

## High-Level Overview

The God Mode Quant Trading Orchestrator is a microservices-based trading system designed for production deployment. It combines:

1. **Trading Engine**: VNPy-based algorithmic trading
2. **Telegram Dashboard**: Real-time monitoring and control via Telegram
3. **Security Framework**: mTLS, secrets, audit, trust scoring
4. **Monitoring Stack**: Prometheus + Grafana
5. **ML Services**: Time series forecasting and sentiment analysis

## Component Architecture

### 1. Trading Orchestrator Service

```
┌─────────────────────────────────────────────────────────────┐
│                    TRADING ORCHESTRATOR                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Flask API  │    │  VNPy Engine │    │   Security  │  │
│  │  (Port 8000) │    │   (CTA)       │    │   Framework │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                   │                   │            │
│         └───────────────────┴───────────────────┘            │
│                             │                                │
│                    ┌────────▼────────┐                      │
│                    │  Event Engine   │                      │
│                    │  (Message Bus)   │                      │
│                    └────────┬────────┘                      │
│                             │                                │
│         ┌───────────────────┼───────────────────┐          │
│         │                   │                   │          │
│  ┌──────▼──────┐    ┌───────▼──────┐    ┌──────▼──────┐  │
│  │   Strategy  │    │   Gateway    │    │  Risk      │  │
│  │   Engine    │    │   Interface  │    │  Manager    │  │
│  └─────────────┘    └──────────────┘    └─────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Key Components:**

- **Flask API Layer**: Health checks, metrics, webhook endpoints
- **VNPy Engine**: CTA strategy engine for algorithmic trading
- **Event Engine**: Message bus for component communication
- **Strategy Engine**: Manages trading strategies
- **Gateway Interface**: Exchange connectivity
- **Risk Manager**: Position limits, drawdown protection

### 2. Telegram Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│                    TELEGRAM DASHBOARD                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐        ┌──────────────────┐         │
│  │  Telegram Bot    │◄──────►│  Bot Handler     │         │
│  │  (API Calls)     │        │  (Flask Server)  │         │
│  └──────────────────┘        └────────┬─────────┘         │
│                                      │                     │
│                             ┌────────▼─────────┐           │
│                             │  Command Router  │           │
│                             │  + Callback      │           │
│                             └────────┬─────────┘           │
│                                      │                     │
│         ┌────────────────────────────┼────────────────────┐│
│         │                            │                    ││
│  ┌──────▼──────┐           ┌─────────▼─────────┐   ┌───────▼──────┐
│  │  Notifier   │           │  Dashboard       │   │  Metrics    │
│  │  Service   │           │  State Manager   │   │  Exporter   │
│  └────────────┘           └───────────────────┘   └─────────────┘
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Features:**
- Real-time trade notifications
- Risk alerts with severity levels
- Trust score change notifications
- Daily/weekly summary reports
- Interactive inline keyboards

### 3. Security Framework

```
┌─────────────────────────────────────────────────────────────┐
│                    SECURITY FRAMEWORK                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                   TRUST SCORER                        │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │  │
│  │  │  Event      │ │   Score    │ │   Alert    │    │  │
│  │  │  Recorder   │ │  Calculator│ │  Generator │    │  │
│  │  └─────────────┘ └─────────────┘ └─────────────┘    │  │
│  └─────────────────────────────────────────────────────┘  │
│                             │                               │
│  ┌──────────────────────────┼──────────────────────────┐  │
│  │                          │                          │  │
│  ▼                          ▼                          ▼  │
│ ┌───────────┐      ┌──────────────┐      ┌──────────────┐ │
│ │   mTLS    │      │   Secrets    │      │    Audit     │ │
│ │  Manager  │      │   Manager    │      │    Logger   │ │
│ │           │      │              │      │              │ │
│ │ - Certs   │      │ - Vault      │      │ - Hash chain│ │
│ │ - SSL ctx│      │ - Env vars   │      │ - Integrity │ │
│ │ - Rotate │      │ - Cache      │      │ - Verify    │ │
│ └───────────┘      └──────────────┘      └──────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

#### Trust Scoring System

The trust scorer assigns a dynamic score (0-100) to services/users based on:

| Event Type | Weight | Description |
|------------|--------|-------------|
| `AUTH_SUCCESS` | +2.0 | Successful authentication |
| `AUTH_FAILURE` | -10.0 | Failed authentication |
| `TRADE_EXECUTED` | +0.5 | Trade executed |
| `TRADE_FAILED` | -5.0 | Trade failure |
| `CONFIG_CHANGE` | -2.0 | Configuration change |
| `ACCESS_VIOLATION` | -20.0 | Access violation |
| `CERTIFICATE_ROTATED` | +5.0 | Certificate rotation |
| `ANOMALY_DETECTED` | -15.0 | Anomaly detected |
| `COMPLIANCE_VIOLATION` | -25.0 | Compliance violation |

#### Audit Logger

Immutable audit log with hash chaining:

```json
{
  "timestamp": "2026-03-26T12:00:00Z",
  "event_type": "TRADE",
  "service": "orchestrator",
  "user": "system",
  "action": "order_submitted",
  "outcome": "success",
  "severity": "INFO",
  "details": {"symbol": "BTCUSDT", "side": "BUY"},
  "previous_hash": "abc123...",
  "hash": "def456..."
}
```

### 4. Risk Management

```
┌─────────────────────────────────────────────────────────────┐
│                    RISK MANAGEMENT                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                    PORTFOLIO                         │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │  │
│  │  │   Total     │ │    Cash     │ │  Positions  │   │  │
│  │  │   Value     │ │             │ │             │   │  │
│  │  └─────────────┘ └─────────────┘ └─────────────┘   │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │  │
│  │  │  Unrealized │ │   Max       │ │    Risk     │   │  │
│  │  │    P&L      │ │  Drawdown   │ │  Percent    │   │  │
│  │  └─────────────┘ └─────────────┘ └─────────────┘   │  │
│  └─────────────────────────────────────────────────────┘  │
│                             │                               │
│  ┌──────────────────────────▼──────────────────────────┐  │
│  │                   RISK LIMITS                        │  │
│  │                                                      │  │
│  │  max_drawdown_percent: 10%                         │  │
│  │  max_position_risk_percent: 2%                     │  │
│  │  max_portfolio_risk_percent: 5%                    │  │
│  │                                                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                             │                               │
│  ┌──────────────────────────▼──────────────────────────┐  │
│  │                   ALERTS                             │  │
│  │                                                      │  │
│  │  - Telegram Risk Alerts                             │  │
│  │  - Prometheus Metrics                               │  │
│  │  - Trading Auto-Stop                                │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### Trade Execution Flow

```
1. Strategy Signal
       │
       ▼
2. Risk Check (Position Limits, Drawdown)
       │
       ├──▶ REJECTED ──► Log to Audit ──► Alert via Telegram
       │
       ▼
3. Order Submission to VNPy Gateway
       │
       ▼
4. Exchange Order Execution
       │
       ▼
5. Trade Confirmation
       │
       ├──▶ Log to Audit
       ├──▶ Update Portfolio
       ├──▶ Update Trust Score
       └──▶ Send Telegram Notification
```

### Monitoring Data Flow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   System    │    │  Prometheus │    │  Grafana    │
│  Components │───►│  Scrapes    │───►│  Visualize  │
│             │    │  Metrics    │    │  Dashboards │
└─────────────┘    └─────────────┘    └─────────────┘
      │                                        │
      │           ┌─────────────┐              │
      └──────────►│  Telegram  │◄─────────────┘
                  │  Dashboard │
                  │  Alerts    │
                  └─────────────┘
```

## Monitoring Architecture

### Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `telegram_messages_sent_total` | Counter | Telegram messages sent |
| `trading_active_positions` | Gauge | Active positions |
| `trading_unrealized_pnl_dollars` | Gauge | Unrealized P&L |
| `security_trust_score` | Gauge | Trust score |
| `risk_alerts_triggered_total` | Counter | Risk alerts |

### Grafana Dashboards

1. **Trading Overview**: Portfolio value, P&L, positions
2. **Risk Dashboard**: Drawdown, position risks
3. **Security Dashboard**: Trust scores, auth events
4. **System Health**: Service status, latency

## Infrastructure

### Service Ports

| Service | Internal Port | External Port | Purpose |
|---------|--------------|---------------|---------|
| Trading Orchestrator | 8000 | 8000 | Main API |
| PostgreSQL | 5432 | 5433 | Database |
| Redis | 6379 | 6380 | Cache/Queue |
| Prometheus | 9090 | 9090 | Metrics |
| Grafana | 3000 | 3000 | Dashboards |
| ML Time Series | 8000 | 8001 | Forecasting |
| ML Sentiment | 8000 | 8002 | Sentiment |

### Docker Compose Services

```yaml
services:
  trading-orchestrator:  # Main application
  postgres:              # Database
  redis:                 # Cache
  prometheus:            # Metrics collection
  grafana:               # Visualization
  ml-time-series-forecast:  # ML service
  ml-sentiment-analysis:     # ML service
```

## Security Architecture

### mTLS Configuration

```python
# SSL context creation
context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
context.load_cert_chain(certfile="service.crt", keyfile="service.key")
context.load_verify_locations(cafile="ca.crt")
context.verify_mode = ssl.CERT_REQUIRED
```

### Secrets Management

- **Primary**: HashiCorp Vault (if configured)
- **Fallback**: Environment variables
- **Caching**: 5-minute TTL

## Orchestrator Package Structure

The core orchestration logic is organized into a modular `orchestrator` package, enabling clean separation of concerns and easier extension.

### Package Layout

```
orchestrator/
├── __init__.py          # Public API exports
├── lifecycle.py         # Lifecycle management (startup, shutdown, health)
├── config.py            # Configuration loading and validation
└── (future modules)     # Additional components as the system grows
```

### Module Responsibilities

| Module | Purpose | Key Classes/Functions |
|--------|---------|------------------------|
| `orchestrator.lifecycle` | Manages the lifecycle of the trading orchestrator, including startup sequence, graceful shutdown, and health monitoring. | `OrchestratorLifecycle` class with methods like `start()`, `stop()`, `is_healthy()` |
| `orchestrator.config` | Handles configuration loading from environment variables, `.env` files, and defaults. Validates configuration and provides typed access. | `OrchestratorConfig` class with properties for each configuration group (trading, risk, security, etc.) |

### How to Extend the System

#### Adding a New Orchestrator Component

1. **Create a new module** in the `orchestrator/` directory (e.g., `orchestrator/monitoring.py`).
2. **Define a class** that encapsulates the component's functionality.
3. **Export the class** in `orchestrator/__init__.py` by adding it to `__all__` and importing it.
4. **Integrate the component** into the lifecycle by importing it in `lifecycle.py` and adding appropriate initialization and cleanup steps.

Example extension:

```python
# orchestrator/monitoring.py
class HealthMonitor:
    """Continuously monitors system health and triggers alerts"""
    
    def __init__(self, lifecycle):
        self.lifecycle = lifecycle
    
    def start(self):
        # Start background health checks
        pass
    
    def stop(self):
        # Clean up monitoring resources
        pass
```

```python
# orchestrator/__init__.py
from .lifecycle import OrchestratorLifecycle
from .config import OrchestratorConfig
from .monitoring import HealthMonitor

__all__ = ['OrchestratorLifecycle', 'OrchestratorConfig', 'HealthMonitor']
```

#### Modifying Lifecycle Behavior

The `OrchestratorLifecycle` class provides hooks for extending startup and shutdown sequences:

- **Before startup**: Add pre‑initialization steps (e.g., loading external data).
- **After startup**: Add post‑initialization steps (e.g., warming up caches).
- **Before shutdown**: Add cleanup steps (e.g., flushing buffers, saving state).

Refer to `lifecycle.py` for the exact hook points.

## Extension Points

### Adding New Strategies

1. Create strategy class extending `CtaTemplate`
2. Implement required callbacks: `on_init`, `on_start`, `on_stop`, `on_bar`
3. Register with CTA engine

### Adding Custom Metrics

```python
from prometheus_client import Counter, Gauge

custom_metric = Counter('custom_events_total', 'Custom events')
custom_metric.inc()
```

### Webhook Integration

Configure Telegram webhook:

```python
bot_handler.set_webhook("https://your-domain.com/webhook")
```

---

**Related Documentation:**
- [README.md](README.md) - Main project documentation
- [API.md](API.md) - API endpoints
- [TELEGRAM_DASHBOARD.md](TELEGRAM_DASHBOARD.md) - Telegram bot guide
- [SECURITY.md](SECURITY.md) - Security framework details

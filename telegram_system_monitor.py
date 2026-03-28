"""
Telegram System Monitor - Architecture Display and Metrics Collector
Provides system architecture visualization and comprehensive metrics collection
for the GodMode Quant Orchestrator Telegram bot.
"""

import os
import time
import threading
import logging
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from datetime import datetime

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    psutil = None
    logging.getLogger(__name__).warning("psutil not available, system metrics will be limited")

logger = logging.getLogger(__name__)


# ==================== SYSTEM ARCHITECTURE DISPLAY ====================

class SystemArchitectureDisplay:
    """Display system architecture in various formats"""
    
    # ASCII art constants
    BOX_TOP = "┌─────────────────────────────────────────────────────────────────────┐"
    BOX_BOTTOM = "└─────────────────────────────────────────────────────────────────────┘"
    SEPARATOR = "│"
    
    @staticmethod
    def get_summary() -> str:
        """Get high-level architecture summary"""
        return (
            f"{SystemArchitectureDisplay.BOX_TOP}\n"
            f"{SystemArchitectureDisplay.SEPARATOR}  🏗️ <b>GOD MODE QUANT ORCHESTRATOR - SYSTEM ARCHITECTURE</b>{SystemArchitectureDisplay.SEPARATOR}\n"
            f"{SystemArchitectureDisplay.SEPARATOR}\n"
            f"{SystemArchitectureDisplay.SEPARATOR}  ┌──────────────────┐    ┌──────────────────┐\n"
            f"{SystemArchitectureDisplay.SEPARATOR}  │  Trading Engine  │    │  AI/ML Services  │\n"
            f"{SystemArchitectureDisplay.SEPARATOR}  │  (VNPy-based)    │    │  (LSTM/Transf.)  │\n"
            f"{SystemArchitectureDisplay.SEPARATOR}  └──────────────────┘    └──────────────────┘\n"
            f"{SystemArchitectureDisplay.SEPARATOR}         │                       │\n"
            f"{SystemArchitectureDisplay.SEPARATOR}  ┌────────▼───────────────────────▼────────┐\n"
            f"{SystemArchitectureDisplay.SEPARATOR}  │      Security Framework               │\n"
            f"{SystemArchitectureDisplay.SEPARATOR}  │   (JWT/Auth/Trust Scoring/Audit)       │\n"
            f"{SystemArchitectureDisplay.SEPARATOR}  └───────────────────────────────────────┘\n"
            f"{SystemArchitectureDisplay.SEPARATOR}         │\n"
            f"{SystemArchitectureDisplay.SEPARATOR}  ┌────────▼───────────────────────────────┐\n"
            f"{SystemArchitectureDisplay.SEPARATOR}  │      Infrastructure Layer              │\n"
            f"{SystemArchitectureDisplay.SEPARATOR}  │  (PostgreSQL/Redis/Prometheus/Grafana) │\n"
            f"{SystemArchitectureDisplay.SEPARATOR}  └───────────────────────────────────────┘\n"
            f"{SystemArchitectureDisplay.SEPARATOR}  \n"
            f"{SystemArchitectureDisplay.SEPARATOR}  <i>Use buttons below for detailed views</i>\n"
            f"{SystemArchitectureDisplay.BOX_BOTTOM}"
        )
    
    @staticmethod
    def get_full_diagram() -> str:
        """Get complete system architecture diagram"""
        diagram = (
            f"\U0001F4C8 <b>COMPLETE SYSTEM ARCHITECTURE</b>\n\n"
            f"<b>LAYER 1: APPLICATION LAYER</b>\n"
            f"┌─────────────────────────────────────────────────────────────────────┐\n"
            f"│                    TRADING ORCHESTRATOR SERVICE                     │\n"
            f"├─────────────────────────────────────────────────────────────────────┤\n"
            f"│                                                                      │\n"
            f"│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │\n"
            f"│  │  FastAPI     │    │  VNPy Engine │    │  Security    │          │\n"
            f"│  │  (Port 8000) │    │  (CTA)       │    │  Framework   │          │\n"
            f"│  └──────────────┘    └──────────────┘    └──────────────┘          │\n"
            f"│         │                   │                   │                    │\n"
            f"│         └───────────────────┴───────────────────┘                    │\n"
            f"│                             │                                        │\n"
            f"│                    ┌────────▼────────┐                              │\n"
            f"│                    │  Event Engine   │                              │\n"
            f"│                    │  (Message Bus)   │                              │\n"
            f"│                    └────────┬────────┘                              │\n"
            f"│                             │                                        │\n"
            f"│  ┌──────────────┐  ┌────────▼────────┐  ┌──────────────┐           │\n"
            f"│  │  Strategy    │  │  Gateway        │  │  Risk        │           │\n"
            f"│  │  Engine      │  │  Interface      │  │  Manager     │           │\n"
            f"│  └──────────────┘  └─────────────────┘  └──────────────┘           │\n"
            f"└─────────────────────────────────────────────────────────────────────┘\n\n"
            f"<b>LAYER 2: AI/ML SERVICES LAYER</b>\n"
            f"┌─────────────────────────────────────────────────────────────────────┐\n"
            f"│                      AI/ML SERVICES                                  │\n"
            f"├─────────────────────────────────────────────────────────────────────┤\n"
            f"│  ┌─────────────────────┐    ┌─────────────────────┐                 │\n"
            f"│  │  LSTM Forecasting   │    │  Transformer Model  │                 │\n"
            f"│  │  (Deep Learning)    │    │  (Self-Attention)   │                 │\n"
            f"│  └─────────────────────┘    └─────────────────────┘                 │\n"
            f"│           │                           │                              │\n"
            f"│           └─────────────┬─────────────┘                              │\n"
            f"│                         ▼                                            │\n"
            f"│              ┌─────────────────────┐                                │\n"
            f"│              │  MLflow MLOps       │                                │\n"
            f"│              │  (Registry/Track)   │                                │\n"
            f"│              └─────────────────────┘                                │\n"
            f"└─────────────────────────────────────────────────────────────────────┘\n\n"
            f"<b>LAYER 3: INFRASTRUCTURE LAYER</b>\n"
            f"┌─────────────────────────────────────────────────────────────────────┐\n"
            f"│                      INFRASTRUCTURE                                  │\n"
            f"├─────────────────────────────────────────────────────────────────────┤\n"
            f"│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐│\n"
            f"│  │ PostgreSQL  │  │    Redis    │  │ Prometheus │  │  Grafana    ││\n"
            f"│  │  (Port 5433)│  │  (Port 6379)│  │ (Port 9090)│  │  (Port 3000)││\n"
            f"│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘│\n"
            f"└─────────────────────────────────────────────────────────────────────┘\n\n"
            f"<i>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
        )
        return diagram
    
    @staticmethod
    def get_component_details(component: str) -> str:
        """Get detailed information about a component"""
        details = {
            'trading_engine': (
                f"\U0001F916 <b>TRADING ENGINE DETAILS</b>\n\n"
                f"<b>Technology:</b> VNPy 3.9.4\n"
                f"<b>Architecture:</b> CTA Strategy Framework\n\n"
                f"<b>Sub-modules:</b>\n"
                f"  \U0001F4C8 Strategy Engine - Manages trading strategies\n"
                f"  \U0001F4CB Gateway Interface - Exchange connectivity\n"
                f"  \U0001F4B0 Order Manager - Order lifecycle\n"
                f"  \u2694\uFE0F Risk Manager - Position limits, drawdown\n\n"
                f"<b>Features:</b>\n"
                f"  • Multi-strategy support\n"
                f"  • Real-time risk monitoring\n"
                f"  • Kelly Criterion sizing\n"
                f"  • VaR calculation\n"
            ),
            'ai_ml_services': (
                f"\U0001F3AF <b>AI/ML SERVICES DETAILS</b>\n\n"
                f"<b>LSTM Model:</b>\n"
                f"  • Bidirectional architecture\n"
                f"  • Attention mechanisms\n"
                f"  • 128 LSTM units\n"
                f"  • Dropout regularization\n\n"
                f"<b>Transformer Model:</b>\n"
                f"  • Multi-head attention (4 heads)\n"
                f"  • Positional encoding\n"
                f"  • 128-dim embeddings\n"
                f"  • GELU activation\n\n"
                f"<b>MLOps (MLflow):</b>\n"
                f"  • Experiment tracking\n"
                f"  • Model registry\n"
                f"  • Performance metrics\n"
                f"  • Hyperparameter logging\n"
            ),
            'security': (
                f"\U0001F6E1 <b>SECURITY FRAMEWORK DETAILS</b>\n\n"
                f"<b>Authentication:</b>\n"
                f"  • JWT-based auth (OAuth2)\n"
                f"  • Role-based access control\n"
                f"  • Access/refresh tokens\n"
                f"  • Session management\n\n"
                f"<b>Trust Scoring:</b>\n"
                f"  • Dynamic 0-100 score per service\n"
                f"  • Event-weighted updates\n"
                f"  • 24h decay factor\n"
                f"  • Alert thresholds\n\n"
                f"<b>Audit Logging:</b>\n"
                f"  • Immutable hash-chained logs\n"
                f"  • Complete event history\n"
                f"  • Integrity verification\n"
                f"  • Compliance tracking\n\n"
                f"<b>Rate Limiting:</b>\n"
                f"  • Per-endpoint limits\n"
                f"  • Configurable windows\n"
                f"  • Automatic blocking\n"
            ),
            'infrastructure': (
                f"\U0001F4CA <b>INFRASTRUCTURE DETAILS</b>\n\n"
                f"<b>PostgreSQL (Port 5433):</b>\n"
                f"  • Persistent data storage\n"
                f"  • Trade history\n"
                f"  • Audit logs\n"
                f"  • User management\n\n"
                f"<b>Redis (Port 6379):</b>\n"
                f"  • In-memory cache\n"
                f"  • Session storage\n"
                f"  • Real-time data\n"
                f"  • Pub/Sub messaging\n\n"
                f"<b>Prometheus (Port 9090):</b>\n"
                f"  • Metrics collection\n"
                f"  • Custom exporters\n"
                f"  • Alert rules\n"
                f"  • Time-series DB\n\n"
                f"<b>Grafana (Port 3000):</b>\n"
                f"  • Visualization dashboards\n"
                f"  • Real-time monitoring\n"
                f"  • Alert notifications\n"
                f"  • Custom panels\n"
            )
        }
        
        return details.get(component, f"\u2753 <b>Unknown Component</b>\n\nComponent '{component}' not found.")
    
    @staticmethod
    def get_data_flow() -> str:
        """Get data flow diagram"""
        return (
            f"\U0001F504 <b>SYSTEM DATA FLOW</b>\n\n"
            f"<b>Trading Flow:</b>\n"
            f"Market Data → Gateway → Strategy Engine → Order Manager → Exchange\n"
            f"                              ↓\n"
            f"                        Risk Manager\n"
            f"                              ↓\n"
            f"                        Portfolio Update\n\n"
            f"<b>Notification Flow:</b>\n"
            f"Trade Execution → Risk Check → Trust Score Update → Telegram Alert\n"
            f"                                                     ↓\n"
            f"                                             Prometheus Metric\n\n"
            f"<b>ML Prediction Flow:</b>\n"
            f"Historical Data → LSTM/Transformer → Price Prediction → Trading Signal\n"
            f"                                      ↓\n"
            f"                               MLflow Logging\n\n"
            f"<b>Security Flow:</b>\n"
            f"API Request → JWT Validation → Role Check → Rate Limit → Authorization\n"
            f"                                     ↓\n"
            f"                               Audit Log\n"
        )


# ==================== SYSTEM METRICS COLLECTOR ====================

@dataclass
class SystemMetricsCache:
    """Thread-safe metrics cache with TTL"""
    ttl: int = 30  # Time to live in seconds
    
    def __post_init__(self):
        self._cache: Dict[str, Tuple[Dict, float]] = {}
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Dict]:
        """Get cached value if not expired"""
        with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if time.time() - timestamp < self.ttl:
                    return value
                # Expired, remove from cache
                del self._cache[key]
        return None
    
    def set(self, key: str, value: Dict):
        """Set value in cache with current timestamp"""
        with self._lock:
            self._cache[key] = (value, time.time())
    
    def invalidate(self, key: str):
        """Invalidate a specific cache key"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    def clear(self):
        """Clear all cache"""
        with self._lock:
            self._cache.clear()


class SystemMetricsCollector:
    """Collect system metrics with caching support"""
    
    def __init__(self, cache_ttl: int = 30):
        """Initialize metrics collector
        
        Args:
            cache_ttl: Cache time-to-live in seconds for quick summary
        """
        self.cache = SystemMetricsCache(ttl=cache_ttl)
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check if required dependencies are available"""
        if not self._has_psutil():
            logger.warning("psutil not available, system metrics will be limited")
    
    def _has_psutil(self) -> bool:
        """Check if psutil is available"""
        return HAS_PSUTIL
    
    def get_quick_summary(self) -> Dict:
        """Get quick summary of system metrics (cached)
        
        Returns:
            Dict with CPU, memory, disk, and API status
        """
        cached = self.cache.get('quick_summary')
        if cached:
            return cached
        
        summary = self._collect_system_resources()
        summary.update(self._collect_api_health())
        
        self.cache.set('quick_summary', summary)
        return summary
    
    def get_detailed_cpu(self) -> Dict:
        """Get detailed CPU metrics (real-time)"""
        if not self._has_psutil():
            return {"error": "psutil not available"}
        
        try:
            cpu_info = {
                "usage_percent": psutil.cpu_percent(interval=0.1),
                "usage_per_core": psutil.cpu_percent(interval=0.1, percpu=True),
                "core_count": psutil.cpu_count(),
                "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else None,
                "process_count": len(psutil.pids())
            }
            return cpu_info
        except Exception as e:
            logger.error(f"Error collecting CPU metrics: {e}")
            return {"error": str(e)}
    
    def get_detailed_memory(self) -> Dict:
        """Get detailed memory metrics (real-time)"""
        if not self._has_psutil():
            return {"error": "psutil not available"}
        
        try:
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            memory_info = {
                "total_gb": mem.total / (1024**3),
                "available_gb": mem.available / (1024**3),
                "used_gb": mem.used / (1024**3),
                "used_percent": mem.percent,
                "free_gb": mem.free / (1024**3),
                "cached_gb": getattr(mem, 'cached', 0) / (1024**3),
                "buffers_gb": getattr(mem, 'buffers', 0) / (1024**3),
                "swap_total_gb": swap.total / (1024**3),
                "swap_used_gb": swap.used / (1024**3),
                "swap_percent": swap.percent
            }
            return memory_info
        except Exception as e:
            logger.error(f"Error collecting memory metrics: {e}")
            return {"error": str(e)}
    
    def get_detailed_disk(self) -> Dict:
        """Get detailed disk metrics (real-time)"""
        if not self._has_psutil():
            return {"error": "psutil not available"}
        
        try:
            disk_info = {}
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_info[partition.mountpoint] = {
                        "total_gb": usage.total / (1024**3),
                        "used_gb": usage.used / (1024**3),
                        "free_gb": usage.free / (1024**3),
                        "used_percent": usage.percent,
                        "filesystem": partition.fstype
                    }
                except PermissionError:
                    continue
            return disk_info
        except Exception as e:
            logger.error(f"Error collecting disk metrics: {e}")
            return {"error": str(e)}
    
    def get_network_metrics(self) -> Dict:
        """Get network metrics (real-time)"""
        if not self._has_psutil():
            return {"error": "psutil not available"}
        
        try:
            net_io = psutil.net_io_counters()
            net_connections = len(psutil.net_connections())
            
            network_info = {
                "bytes_sent_gb": net_io.bytes_sent / (1024**3),
                "bytes_recv_gb": net_io.bytes_recv / (1024**3),
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "errin": net_io.errin,
                "errout": net_io.errout,
                "dropin": net_io.dropin,
                "dropout": net_io.dropout,
                "active_connections": net_connections
            }
            return network_info
        except Exception as e:
            logger.error(f"Error collecting network metrics: {e}")
            return {"error": str(e)}
    
    def get_database_metrics(self) -> Dict:
        """Get database metrics (PostgreSQL and Redis)"""
        db_info = {}
        
        # PostgreSQL metrics
        try:
            from database.database_manager import db_manager
            with db_manager.get_db_connection() as conn:
                result = conn.execute("""
                    SELECT 
                        COUNT(*) FILTER (WHERE state = 'active') as active_connections,
                        COUNT(*) FILTER (WHERE state = 'idle') as idle_connections,
                        COUNT(*) as total_connections
                    FROM pg_stat_activity
                """)
                row = result.fetchone()
                db_info["postgresql"] = {
                    "active_connections": row[0] if row else 0,
                    "idle_connections": row[1] if row else 0,
                    "total_connections": row[2] if row else 0,
                    "status": "connected"
                }
        except Exception as e:
            logger.warning(f"Could not collect PostgreSQL metrics: {e}")
            db_info["postgresql"] = {"status": "unavailable", "error": str(e)}
        
        # Redis metrics (basic check)
        try:
            import redis
            redis_client = redis.Redis(host='localhost', port=6380, decode_responses=True)
            redis_info = redis_client.info()
            db_info["redis"] = {
                "used_memory_gb": redis_info.get('used_memory', 0) / (1024**3),
                "used_memory_peak_gb": redis_info.get('used_memory_peak', 0) / (1024**3),
                "connected_clients": redis_info.get('connected_clients', 0),
                "status": "connected"
            }
        except Exception as e:
            logger.warning(f"Could not collect Redis metrics: {e}")
            db_info["redis"] = {"status": "unavailable", "error": str(e)}
        
        return db_info
    
    def get_api_health(self) -> Dict:
        """Get API health metrics"""
        api_info = {
            "status": "healthy",
            "uptime_seconds": time.time(),
            "request_count": 0
        }
        return api_info
    
    def get_ml_metrics(self) -> Dict:
        """Get ML model metrics"""
        ml_info = {
            "lstm_status": "not_loaded",
            "transformer_status": "not_loaded",
            "last_training": None,
            "prediction_count": 0
        }
        
        # Try to get ML model status
        try:
            from ai_ml.lstm_forecast import LSTMPricePredictor
            from ai_ml.transformer_forecast import TransformerPricePredictor
            ml_info["lstm_status"] = "available"
            ml_info["transformer_status"] = "available"
        except Exception:
            logger.debug("ML models not loaded")
        
        return ml_info
    
    def get_security_metrics(self) -> Dict:
        """Get security metrics"""
        security_info = {
            "active_sessions": 0,
            "auth_success_24h": 0,
            "auth_failure_24h": 0,
            "trust_score_system": 0.0
        }
        
        # Try to get trust score
        try:
            from security.trust_scorer import trust_scorer
            security_info["trust_score_system"] = trust_scorer.get_trust_score("orchestrator:system")
        except Exception:
            logger.debug("Could not get trust score")
        
        return security_info
    
    def get_trading_metrics(self) -> Dict:
        """Get trading metrics"""
        trading_info = {
            "active_positions": 0,
            "unrealized_pnl": 0.0,
            "total_trades_today": 0,
            "total_trades_all": 0,
            "engine_status": "unknown"
        }
        
        try:
            from risk_management import risk_manager
            portfolio = risk_manager.portfolio
            trading_info["active_positions"] = portfolio.position_count
            trading_info["unrealized_pnl"] = portfolio.total_unrealized_pnl
            trading_info["portfolio_value"] = portfolio.total_value
        except Exception:
            logger.debug("Could not get trading metrics")
        
        try:
            from trading_engine import get_trading_engine
            engine = get_trading_engine()
            if engine:
                status = engine.get_status()
                trading_info["engine_status"] = status.state.value
                trading_info["total_trades_all"] = status.total_trades
        except Exception:
            logger.debug("Could not get engine status")
        
        return trading_info
    
    def get_all_metrics(self) -> Dict:
        """Get all system metrics"""
        return {
            "cpu": self.get_detailed_cpu(),
            "memory": self.get_detailed_memory(),
            "disk": self.get_detailed_disk(),
            "network": self.get_network_metrics(),
            "database": self.get_database_metrics(),
            "api": self.get_api_health(),
            "ml": self.get_ml_metrics(),
            "security": self.get_security_metrics(),
            "trading": self.get_trading_metrics(),
            "quick_summary": self.get_quick_summary()
        }
    
    # ==================== PRIVATE COLLECTION METHODS ====================
    
    def _collect_system_resources(self) -> Dict:
        """Collect basic system resources"""
        resources = {}
        
        if self._has_psutil():
            try:
                resources["cpu"] = {
                    "usage_percent": psutil.cpu_percent(interval=0.1)
                }
                
                mem = psutil.virtual_memory()
                resources["memory"] = {
                    "used_percent": mem.percent,
                    "used_gb": mem.used / (1024**3),
                    "total_gb": mem.total / (1024**3)
                }
                
                disk = psutil.disk_usage('/')
                resources["disk"] = {
                    "used_percent": disk.percent,
                    "used_gb": disk.used / (1024**3),
                    "total_gb": disk.total / (1024**3)
                }
            except Exception as e:
                logger.error(f"Error collecting system resources: {e}")
        
        return resources
    
    def _collect_api_health(self) -> Dict:
        """Collect API health metrics"""
        return {"api_status": "healthy", "timestamp": time.time()}

# Export main classes for import
__all__ = [
    'SystemArchitectureDisplay',
    'SystemMetricsCollector',
    'SystemMetricsCache'
]
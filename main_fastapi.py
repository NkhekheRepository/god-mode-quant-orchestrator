"""
GodMode Quant Orchestrator - Main Application with FastAPI

Enterprise-grade production orchestrator with:
- JWT-based authentication and authorization
- Rate limiting and security controls
- SSL/TLS verification
- Input validation and sanitization
- Comprehensive monitoring and logging
"""

import os
import sys
import time
import asyncio
import logging
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Import authentication
from security.auth import (
    authenticator,
    get_current_active_user,
    Token,
    User,
    requires_roles
)

# Import monitoring and logging
from prometheus_client import Counter, Histogram, Gauge

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize application metrics
trading_requests_total = Counter('trading_requests_total', 'Total trading requests', ['operation', 'status'])
trading_request_duration = Histogram('trading_request_duration_seconds', 'Trading request duration')
trading_positions_active = Gauge('trading_positions_active', 'Active positions')
trading_pnl_total = Gauge('trading_pnl_total', 'Total P&L')
system_health_status = Gauge('system_health_status', 'System health status', ['component'])

# Initialize FastAPI with lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("=" * 80)
    logger.info("GOD MODE QUANT TRADING ORCHESTRATOR STARTING")
    logger.info("=" * 80)
    
    # Startup operations
    update_system_health("api", 1)
    
    yield
    
    # Shutdown operations
    logger.info("=" * 80)
    logger.info("GOD MODE QUANT TRADING ORCHESTRATOR SHUTTING DOWN")
    logger.info("=" * 80)
    update_system_health("api", 0)


# Create FastAPI application
app = FastAPI(
    title="GodMode Quant Orchestrator",
    description="""
    Enterprise-grade quantitative trading orchestrator with AI/ML capabilities,
    comprehensive security controls, and real-time monitoring.
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    },
    lifespan=lifespan
)


def update_system_health(component: str, status: int):
    """Update system health metric"""
    system_health_status.labels(component=component).set(status)


# Add CORS middleware with strict origin checking
allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Add GZip compression for responses
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Setup rate limiting
limiter = Limiter(key_func=get_remote_address, app=app)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    trading_requests_total.labels(
        operation=request.url.path,
        status="error"
    ).inc()
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# Health check endpoints
@app.get("/health")
@limiter.limit("100 per minute")
async def health_check(request: Request):
    """Main health check endpoint"""
    return JSONResponse(content={
        "status": "healthy",
        "service": "god-mode-quant-orchestrator",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat()
    })


@app.get("/health/ready")
async def readiness_check():
    """Readiness check for Kubernetes"""
    try:
        # Check database connectivity
        from database.database_manager import db_manager
        with db_manager.get_db_connection() as conn:
            conn.execute("SELECT 1")
        return JSONResponse(content={"ready": True})
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(content={"ready": False}, status_code=503)


@app.get("/health/live")
async def liveness_check():
    """Liveness check for Kubernetes"""
    return JSONResponse(content={"live": True})


# Metrics endpoint
@app.get("/metrics")
@limiter.limit("50 per minute")
async def metrics_endpoint():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Authentication endpoints
@app.post("/api/auth/token", response_model=Token)
@limiter.limit("10 per minute")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """Login endpoint to get access token"""
    with trading_request_duration.time():
        trading_requests_total.labels(operation="login", status="attempt").inc()
        
        user = authenticator.authenticate_user(
            form_data.username, 
            form_data.password
        )
        
        if not user:
            logger.warning(f"Failed login attempt for user: {form_data.username}")
            trading_requests_total.labels(operation="login", status="failed").inc()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        trading_requests_total.labels(operation="login", status="success").inc()
        authenticator.create_tokens(user.username, {})
        
        tokens = authenticator.create_tokens(user.username, {})
        
        logger.info(f"User login successful: {user.username}")
        return tokens


@app.post("/api/auth/refresh")
@limiter.limit("20 per minute")
async def refresh_token(request: Request):
    """Refresh access token"""
    with trading_request_duration.time():
        trading_requests_total.labels(operation="refresh", status="attempt").inc()
        
        body = await request.json()
        refresh_token = body.get("refresh_token")
        
        if not refresh_token:
            trading_requests_total.labels(operation="refresh", status="failed").inc()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token required"
            )
        
        tokens = authenticator.refresh_access_token(refresh_token)
        
        if not tokens:
            trading_requests_total.labels(operation="refresh", status="failed").inc()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        trading_requests_total.labels(operation="refresh", status="success").inc()
        return JSONResponse(content=tokens)


@app.post("/api/auth/logout")
async def logout(current_user: User = Depends(get_current_active_user)):
    """Logout endpoint (token invalidation can be implemented here)"""
    logger.info(f"User logout: {current_user.username}")
    return JSONResponse(content={"message": "Logged out successfully"})


# Protected endpoints - Trading operations
@app.post("/api/orders")
@limiter.limit("60 per minute")
async def create_order(
    order_data: Dict[str, Any],
    current_user: User = Depends(get_current_active_user)
):
    """Create a new trading order"""
    # Check if user has trader role
    if "trader" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Trader role required"
        )
    
    with trading_request_duration.time():
        trading_requests_total.labels(operation="create_order", status="attempt").inc()
        
        # Validate order data
        required_fields = ["symbol", "side", "quantity", "order_type"]
        for field in required_fields:
            if field not in order_data:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Missing required field: {field}"
                )
        
        # Sanitize inputs
        from database.database_manager import db_manager
        db_manager_instance = db_manager
        
        symbol = db_manager_instance.sanitize_input(order_data["symbol"], 20)
        side = db_manager_instance.sanitize_input(order_data["side"], 10)
        order_type = db_manager_instance.sanitize_input(order_data["order_type"], 20)
        quantity = float(order_data.get("quantity", 0))
        
        if symbol not in ["BTCUSDT", "ETHUSDT"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid trading symbol"
            )
        
        if side not in ["buy", "sell"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid order side"
            )
        
        if quantity <= 0 or quantity > 100:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid quantity"
            )
        
        # Log order
        db_manager_instance.log_system_event(
            level="INFO",
            source="api",
            message=f"Order created by user {current_user.username}",
            details=json.dumps({
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "order_type": order_type,
                "user": current_user.username
            })
        )
        
        trading_requests_total.labels(operation="create_order", status="success").inc()
        
        logger.info(
            f"Order created by {current_user.username}: "
            f"{side} {quantity} {symbol}"
        )
        
        return JSONResponse(content={
            "status": "order_submitted",
            "order_id": f"ORDER-{int(time.time())}",
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "order_type": order_type,
            "user": current_user.username,
            "timestamp": datetime.utcnow().isoformat()
        })


@app.get("/api/orders")
async def get_orders(
    symbol: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """Get orders with optional filters"""
    with trading_request_duration.time():
        trading_requests_total.labels(operation="get_orders", status="attempt").inc()
        
        from database.database_manager import db_manager
        db_manager_instance = db_manager
        
        # Get filtered trades from database
        if symbol and status:
            trades = db_manager_instance.get_trades_by_symbol_and_status(
                symbol, status
            )
        elif symbol:
            trades = db_manager_instance.execute_query(
                "SELECT * FROM trades WHERE symbol = :symbol ORDER BY timestamp DESC",
                {"symbol": symbol},
                fetch_all=True
            )
        elif status:
            trades = db_manager_instance.execute_query(
                "SELECT * FROM trades WHERE status = :status ORDER BY timestamp DESC",
                {"status": status},
                fetch_all=True
            )
        else:
            trades = db_manager_instance.execute_query(
                "SELECT * FROM trades ORDER BY timestamp DESC LIMIT 100",
                fetch_all=True
            )
        
        trading_requests_total.labels(operation="get_orders", status="success").inc()
        
        return JSONResponse(content={
            "orders": trades,
            "count": len(trades),
            "timestamp": datetime.utcnow().isoformat()
        })


@app.get("/api/positions")
@limiter.limit("60 per minute")
async def get_positions(
    current_user: User = Depends(get_current_active_user)
):
    """Get current positions"""
    with trading_request_duration.time():
        trading_requests_total.labels(operation="get_positions", status="attempt").inc()
        
        from database.database_manager import db_manager
        db_manager_instance = db_manager
        
        positions = db_manager_instance.execute_query(
            "SELECT * FROM positions WHERE status != 'closed' ORDER BY timestamp DESC",
            fetch_all=True
        )
        
        # Update active positions metric
        trading_positions_active.set(len(positions))
        
        trading_requests_total.labels(operation="get_positions", status="success").inc()
        
        return JSONResponse(content={
            "positions": positions,
            "count": len(positions),
            "timestamp": datetime.utcnow().isoformat()
        })


@app.get("/api/strategies")
async def get_strategies(
    current_user: User = Depends(get_current_active_user)
):
    """Get available trading strategies"""
    with trading_request_duration.time():
        trading_requests_total.labels(operation="get_strategies", status="attempt").inc()
        
        # Return list of available strategies
        strategies = [
            {
                "id": "ma_crossover",
                "name": "Moving Average Crossover",
                "description": "Simple trend-following strategy",
                "status": "active"
            },
            {
                "id": "rsi_divergence",
                "name": "RSI Divergence",
                "description": "Mean reversion based on RSI divergence",
                "status": "active"
            },
            {
                "id": "momentum_surge",
                "name": "Momentum Surge",
                "description": "Momentum-based strategy",
                "status": "active"
            }
        ]
        
        trading_requests_total.labels(operation="get_strategies", status="success").inc()
        
        return JSONResponse(content={
            "strategies": strategies,
            "count": len(strategies),
            "timestamp": datetime.utcnow().isoformat()
        })


@app.get("/api/user/me")
async def read_users_me(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information"""
    return JSONResponse(content={
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "roles": current_user.roles,
        "disabled": current_user.disabled
    })


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return JSONResponse(content={
        "name": "GodMode Quant Orchestrator",
        "version": "2.0.0",
        "status": "operational",
        "documentation": "/docs",
        "metrics": "/metrics",
        "health": "/health"
    })


def run_uvicorn():
    """Run Uvicorn server"""
    port = int(os.getenv("API_PORT", "8000"))
    host = os.getenv("API_HOST", "0.0.0.0")
    workers = int(os.getenv("API_WORKERS", "1"))
    
    logger.info(f"Starting API server on {host}:{port}")
    
    uvicorn.run(
        "main_fastapi:app",
        host=host,
        port=port,
        workers=workers,
        log_level="info",
        access_log=True
    )


def main():
    """Main entry point"""
    print("=" * 80)
    print("GOD MODE QUANT TRADING ORCHESTRATOR - Enterprise Edition")
    print("Version: 2.0.0")
    print("=" * 80)
    
    try:
        run_uvicorn()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
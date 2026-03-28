"""
Database manager for GodMode Quant Orchestrator.
Provides connection pooling and database operations using SQLAlchemy.
"""

import os
import re
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any, List, Tuple, Union

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load .env from project root (one level up from this file)
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(env_path)
except ImportError:
    logger.warning("python-dotenv not installed; skipping .env file loading")

from sqlalchemy import create_engine, text, Column, Integer, String, Float, DateTime, Boolean, JSON, insert
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

Base = declarative_base()


class _ConnectionWrapper:
    """Wrapper around SQLAlchemy Connection that auto-wraps strings with text()."""
    def __init__(self, connection):
        self._connection = connection
    
    def execute(self, statement, *args, **kwargs):
        """Execute a SQL statement, automatically wrapping strings with text()."""
        from sqlalchemy import text as sql_text
        if isinstance(statement, str):
            statement = sql_text(statement)
        return self._connection.execute(statement, *args, **kwargs)
    
    def __getattr__(self, name):
        """Delegate all other attributes to the underlying connection."""
        return getattr(self._connection, name)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Connection handles its own cleanup; we don't close here
        pass


class SystemEvent(Base):
    """System event logging table."""
    __tablename__ = 'system_events'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    level = Column(String(20), nullable=False, index=True)
    source = Column(String(50), nullable=False, index=True)
    message = Column(String(1000), nullable=False)
    details = Column(JSON)
    timestamp = Column(DateTime, nullable=False, server_default=text('NOW()'))


class Trade(Base):
    """Trade table for storing order history."""
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(String(10), nullable=False)
    order_type = Column(String(20), nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float)
    status = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, server_default=text('NOW()'), index=True)
    details = Column(JSON)


class Position(Base):
    """Position table for tracking open positions."""
    __tablename__ = 'positions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(String(10), nullable=False)
    quantity = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float)
    status = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, server_default=text('NOW()'), index=True)
    details = Column(JSON)


class DatabaseManager:
    """Singleton database manager."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        
        # Load configuration from environment
        self.user = os.getenv('POSTGRES_USER', 'postgres')
        self.password = os.getenv('POSTGRES_PASSWORD', 'postgres')
        self.db = os.getenv('POSTGRES_DB', 'vnpy')
        self.host = os.getenv('POSTGRES_HOST', 'localhost')
        self.port = os.getenv('POSTGRES_PORT', '5432')
        
        # Create database URL
        self.database_url = f'postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}'
        
        # Create engine with connection pooling
        self.engine = create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
            echo=False
        )
        
        # Create tables if they don't exist
        self._create_tables()
        
        logger.info(f"Database manager initialized for {self.host}:{self.port}/{self.db}")
    
    def _create_tables(self):
        """Create tables if they don't exist."""
        try:
            Base.metadata.create_all(self.engine)
            logger.debug("Database tables verified/created")
        except SQLAlchemyError as e:
            logger.error(f"Failed to create tables: {e}")
    
    @contextmanager
    def get_db_connection(self):
        """Context manager for database connections."""
        connection = None
        try:
            connection = self.engine.connect()
            yield _ConnectionWrapper(connection)
        except SQLAlchemyError as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if connection:
                connection.close()
    
    def sanitize_input(self, input_str: str, max_length: int = 255) -> str:
        """
        Basic input sanitization for SQL safety.
        This is a simple defense; always use parameterized queries.
        """
        if not isinstance(input_str, str):
            input_str = str(input_str)
        
        # Truncate to max length
        sanitized = input_str[:max_length]
        
        # Remove or escape potentially dangerous characters
        # Note: For SQL injection prevention, use parameterized queries.
        # This is just an extra layer.
        sanitized = re.sub(r'[\'\";]', '', sanitized)
        sanitized = re.sub(r'--', '', sanitized)
        sanitized = re.sub(r'/\*.*?\*/', '', sanitized, flags=re.DOTALL)
        
        return sanitized
    
    def log_system_event(self, level: str, source: str, message: str, details: Optional[Dict] = None):
        """Log a system event to the database."""
        try:
            with self.get_db_connection() as conn:
                stmt = insert(SystemEvent).values(
                    level=level,
                    source=source,
                    message=message,
                    details=details
                )
                conn.execute(stmt)
                conn.commit()
        except SQLAlchemyError as e:
            logger.error(f"Failed to log system event: {e}")
            # Don't raise; logging failure shouldn't break the app
    
    def execute_query(self, query: str, params: Optional[Dict] = None, fetch_all: bool = False) -> Union[List[Dict], Dict, None]:
        """
        Execute a SQL query and return results.
        
        Args:
            query: SQL query string with named parameters (:param)
            params: Dictionary of parameters
            fetch_all: If True, return all rows; otherwise return first row
        
        Returns:
            List of dicts (fetch_all=True) or single dict (fetch_all=False) or None
        """
        try:
            with self.get_db_connection() as conn:
                result = conn.execute(text(query), params or {})
                
                if result.returns_rows:
                    rows = result.fetchall()
                    if fetch_all:
                        return [dict(row._mapping) for row in rows]
                    else:
                        return dict(rows[0]._mapping) if rows else None
                else:
                    # For INSERT/UPDATE/DELETE
                    conn.commit()
                    return None
        except SQLAlchemyError as e:
            logger.error(f"Query execution failed: {e}\nQuery: {query}\nParams: {params}")
            raise
    
    def get_trades_by_symbol_and_status(self, symbol: str, status: str) -> List[Dict]:
        """Get trades filtered by symbol and status."""
        query = """
            SELECT * FROM trades 
            WHERE symbol = :symbol AND status = :status 
            ORDER BY timestamp DESC
        """
        return self.execute_query(query, {'symbol': symbol, 'status': status}, fetch_all=True) or []


# Singleton instance
db_manager = DatabaseManager()
"""
Authentication and Authorization Module

Implements JWT-based authentication, user management, and role-based access control
"""

import os
import time
from datetime import datetime, timedelta
from typing import Dict, Optional
import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, validator
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status

# Get logger
import logging
logger = logging.getLogger(__name__)

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-" + "-".join([str(x) for x in os.urandom(32)]))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = 30

# Token URLs for OAuth2 scheme
TOKEN_URL = "/api/auth/token"
REFRESH_URL = "/api/auth/refresh"

# Models
class User(BaseModel):
    """User model for authentication and authorization"""
    username: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    disabled: bool = False
    roles: list[str] = []

    class Config:
        schema_extra = {
            "example": {
                "username": "trader1",
                "email": "trader@example.com",
                "full_name": "John Doe",
                "roles": ["trader"],
            }
        }

class UserInDB(User):
    """User model stored in database with hashed password"""
    hashed_password: str

class Token(BaseModel):
    """Token response model"""
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str

class RefreshToken(BaseModel):
    """Refresh token model"""
    refresh_token: str

class TokenData(BaseModel):
    """Token payload"""
    username: Optional[str] = None
    scopes: list[str] = []

# OAuth2 Scheme
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=TOKEN_URL,
    auto_error=True
)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against stored hash"""
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'), 
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        logger.error(f"Password verification error: {str(e)}")
        return False

def get_password_hash(password: str) -> str:
    """Generate password hash"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=30))
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_tokens(username: str, user_data: dict) -> Dict[str, str]:
    """Create both access and refresh tokens"""
    access_token = create_access_token(
        {"sub": username, "scopes": ["*"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    refresh_token = create_refresh_token(
        {"sub": username, "scopes": ["refresh"]},
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

def decode_token(token: str) -> dict:
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.error(f"Token validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def verify_token(token: str) -> bool:
    """Verify token validity"""
    try:
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return True
    except JWTError:
        return False

class Authenticator:
    """Authentication and Authorization manager"""
    
    def __init__(self):
        self.users_db = self._load_users_db()
    
    def _load_users_db(self) -> Dict[str, UserInDB]:
        # In production, replace this with database calls
        return {
            "admin": UserInDB(
                username="admin",
                email="admin@example.com",
                full_name="Administrator",
                disabled=False,
                roles=["admin", "trader"],
                hashed_password=get_password_hash(
                    os.getenv("ADMIN_PASSWORD", "changeme")
                )
            ),
            "trader1": UserInDB(
                username="trader1",
                email="trader@example.com",
                full_name="Trader One",
                disabled=False,
                roles=["trader"],
                hashed_password=get_password_hash(
                    os.getenv("TRADER_PASSWORD", "trading123")
                )
            ),
            "auditor": UserInDB(
                username="auditor",
                email="audit@example.com",
                full_name="Auditor",
                disabled=False,
                roles=["audit"],
                hashed_password=get_password_hash(
                    os.getenv("AUDITOR_PASSWORD", "AuditPass123!")
                )
            )
        }
    
    def get_user(self, username: str) -> Optional[UserInDB]:
        """Get user by username"""
        return self.users_db.get(username)
    
    def authenticate_user(self, username: str, password: str) -> Optional[UserInDB]:
        """Authenticate user with username and password"""
        user = self.get_user(username)
        if not user:
            logger.warning(f"User not found: {username}")
            return None
        if not verify_password(password, user.hashed_password):
            logger.warning(f"Invalid password for user: {username}")
            return None
        return user
    
    def get_current_user(self, token: str = Depends(oauth2_scheme)) -> User:
        """Get current user from access token"""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = decode_token(token)
            username: str = payload.get("sub")
            if username is None:
                logger.error("Token missing 'sub' field")
                raise credentials_exception
        except JWTError:
            logger.error("JWT validation error")
            raise credentials_exception
            
        user = self.get_user(username)
        if user is None:
            logger.error(f"User not found from token: {username}")
            raise credentials_exception
            
        return user
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Token]:
        """Generate new access token from refresh token"""
        try:
            payload = decode_token(refresh_token)
            if payload.get("type") != "refresh":
                logger.error("Invalid token type")
                return None
            
            username = payload.get("sub")
            if not username:
                logger.error("Refresh token missing subject")
                return None
                
            if not self.get_user(username):
                logger.error(f"User from refresh token not found: {username}")
                return None
                
            return create_tokens(username, {})
            
        except JWTError as e:
            logger.error(f"Invalid or expired refresh token: {str(e)}")
            return None

# Initialize global authenticator instance
authenticator = Authenticator()

# Role-based access control helpers
def requires_roles(*roles):
    """Decorator to require specific roles"""
    def decorator(func):
        async def wrapper(current_user: User = Depends(authenticator.get_current_user), *args, **kwargs):
            # Check if any of user's roles match required roles
            if not any(role in current_user.roles for role in roles):
                logger.warning(
                    f"User {current_user.username} lacks required roles: "
                    f"Has {current_user.roles}, needs {roles}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not enough permissions"
                )
            return await func(current_user=current_user, *args, **kwargs)
        return wrapper
    return decorator

# FastAPI dependencies
async def get_current_active_user(current_user: User = Depends(authenticator.get_current_user)):
    """Dependency to get current active user"""
    if current_user.disabled:
        logger.error(f"Account disabled: {current_user.username}")
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Test utility
def create_test_user() -> Dict[str, str]:
    """Create test user and tokens for testing"""
    from . import authenticator
    user = authenticator.get_user("trader1")
    if not user:
        raise ValueError("Test user not found")
    return authenticator.create_tokens(user.username, {})
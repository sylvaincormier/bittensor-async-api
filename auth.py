"""
Authentication module for Bittensor Async API.

This module provides a JWT-based authentication system with scope-based permissions.
"""

import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

# Configure logging
import logging
logger = logging.getLogger(__name__)

# Security configuration
# In production, set this via environment variable!
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "INSECURE_SECRET_KEY_CHANGE_ME_IN_PRODUCTION")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# OAuth2 setup for token endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Models
class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """Data stored in JWT token."""
    username: Optional[str] = None
    scopes: List[str] = []

class User(BaseModel):
    """User model."""
    username: str
    scopes: List[str] = ["read"]  # Default to read-only access

# Simple in-memory user database - replace with proper DB in production
# Format: {"username": {"password": "hashed_password", "scopes": ["read", "stake"]}}
user_db = {}

# Authentication functions
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a new JWT access token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Optional expiration time delta
        
    Returns:
        JWT token string
    """
    to_encode = data.copy()
    
    # Set expiration
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    
    # Create JWT token
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Get the current user from a JWT token.
    
    Args:
        token: JWT token from Authorization header
        
    Returns:
        User object
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        
        if username is None:
            raise credentials_exception
            
        # Get scopes from token
        token_scopes = payload.get("scopes", [])
        token_data = TokenData(username=username, scopes=token_scopes)
        
    except JWTError:
        logger.warning("Invalid token", exc_info=True)
        raise credentials_exception
    
    # For API tokens, we don't need to fetch the user from the database
    # Just create a user object with the scopes from the token
    user = User(username=token_data.username, scopes=token_data.scopes)
    
    return user

# Basic token verification function
def verify_token_has_scope(required_scopes: List[str], token: str = Depends(oauth2_scheme)) -> bool:
    """
    Verify if a token has the required scopes.
    
    Args:
        required_scopes: List of required scopes
        token: JWT token
        
    Returns:
        True if token has required scopes
        
    Raises:
        HTTPException: If token is invalid or missing required scopes
    """
    try:
        # Decode the token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_scopes = payload.get("scopes", [])
        
        # Check if token has all required scopes
        for scope in required_scopes:
            if scope not in token_scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Not enough permissions. Required: {scope}",
                )
                
        return True
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# API Token management
def create_api_token(username: str, scopes: List[str]) -> str:
    """
    Create a new API token for a user with specific scopes.
    
    Args:
        username: Username for the token
        scopes: List of permission scopes
        
    Returns:
        JWT token string
    """
    token_data = {"sub": username, "scopes": scopes}
    
    # API tokens can have longer expiration
    expires = timedelta(days=30)  # 30 days by default
    
    return create_access_token(token_data, expires)

# Basic compatibility with existing API_TOKEN environment variable
def initialize_from_env() -> None:
    """Initialize authentication from environment variables."""
    # Get API token from environment
    api_token = os.getenv("API_TOKEN")
    
    if api_token:
        # Split multiple tokens
        tokens = [token.strip() for token in api_token.split(",")]
        
        # Convert each legacy token to a JWT token
        for i, token in enumerate(tokens):
            # Create a user for each token
            username = f"legacy_user_{i+1}"
            
            # Store the token in our user database with all permissions
            # In a real system, this would be a more complex registration process
            user_db[username] = {
                "token": token,
                "scopes": ["read", "stake", "admin"]
            }
            
            logger.info(f"Registered legacy API token for {username}")
    else:
        logger.warning("No API_TOKEN environment variable found")
        
    logger.info("Authentication module initialized")

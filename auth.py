"""
Minimal authentication module for Bittensor Async API.
"""
import os
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
# Configure logging
import logging
logger = logging.getLogger(__name__)
# Security configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "INSECURE_SECRET_KEY_CHANGE_ME_IN_PRODUCTION")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
# OAuth2 setup
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)
# Models
class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str
    
class User(BaseModel):
    """User model."""
    username: str
    scopes: List[str] = ["read"]
    
# Create an access token
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT token."""
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
    
# Simple function to initialize auth from environment (placeholder for now)
def initialize_from_env():
    """Initialize auth from environment variables."""
    logger.info("Minimal auth module initialized")
    return True
    
# Get current user from token
async def get_current_user(token: str = Depends(oauth2_scheme)) -> Optional[User]:
    """Get current user from token."""
    if token is None:
        return None
    try:
        # Decode JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            return None
        # Get scopes from token
        scopes = payload.get("scopes", ["read"])
        return User(username=username, scopes=scopes)
    except JWTError:
        return None
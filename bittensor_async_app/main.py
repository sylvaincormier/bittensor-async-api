from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import time, os
import logging
import traceback
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our services
from bittensor_async_app.services.bittensor_client import get_tao_dividends as async_get_tao_dividends
import bittensor_async_app.services.bittensor_client as bittensor_client

# Import Celery tasks
from celery_worker import process_stake_operation

# Import minimal auth module (comment out if it doesn't exist yet)
try:
    from bittensor_async_app.auth import initialize_from_env, create_access_token, Token
    auth_available = True
    logger.info("JWT authentication module available")
except ImportError:
    auth_available = False
    logger.warning("JWT authentication module not available, using legacy auth only")

app = FastAPI(
    title="Bittensor Async API",
    description="API to query Tao dividends and optionally stake TAO via a background task.",
    version="1.0.0"
)

security = HTTPBearer()

# Load token from environment or use default for development
VALID_TOKENS = set([token.strip() for token in os.getenv("API_TOKEN", "datura").split(",")])

class TaoDividendResponse(BaseModel):
    """Response model for /api/v1/tao_dividends endpoint."""
    netuid: str
    hotkey: str
    dividend_value: float
    timestamp: float
    trade_triggered: bool
    message: str
    task_id: Optional[str] = None
    status: Optional[str] = None

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Simple Bearer token verification."""
    token = credentials.credentials
    if token not in VALID_TOKENS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,  # Change from 401 to 403
            detail="Invalid or missing token"
        )
    return token
# Optional JWT token endpoint - only available if auth module is present
if auth_available:
    @app.post("/token", response_model=Token)
    async def get_token(request: Request):
        """Get a JWT token from a legacy API token."""
        # Get Authorization header
        auth_header = request.headers.get("Authorization")
        
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Extract token
        token = auth_header.replace("Bearer ", "")
        
        # Check if it's a valid legacy token
        if token in VALID_TOKENS:
            # Create a JWT token with all permissions
            access_token = create_access_token(
                data={"sub": "api_user", "scopes": ["read", "stake", "admin"]}
            )
            return {"access_token": access_token, "token_type": "bearer"}
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

@app.get("/api/v1/tao_dividends", response_model=TaoDividendResponse)
async def get_tao_dividends_endpoint(
    request: Request,
    netuid: str = "18",
    hotkey: str = "5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v",
    trade: bool = False,
    token: str = Depends(verify_token)
):
    """
    Get TAO dividends for a subnet and hotkey.
    
    - **netuid**: Subnet ID (default: 18)
    - **hotkey**: Hotkey address (default: 5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v)
    - **trade**: Whether to trigger stake/unstake based on sentiment (default: false)
    """
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    
    logger.info(f"Dividend request from {client_ip}: netuid={netuid}, hotkey={hotkey}, trade={trade}")
    
    try:
        # Get dividend data
        dividend_value = await async_get_tao_dividends(netuid, hotkey)
        logger.info(f"Dividend value retrieved: {dividend_value}")
        
        response_data = {
            "netuid": netuid,
            "hotkey": hotkey,
            "dividend_value": dividend_value,
            "timestamp": time.time(),
            "trade_triggered": trade,
            "message": "No stake triggered.",
            "status": "success"
        }
        
        # If trade flag is set, trigger background task using Celery
        if trade:
            try:
                logger.info(f"Triggering background task for trade=true")
                # Use apply_async with a timeout to prevent hanging
                task = process_stake_operation.apply_async(
                    args=[netuid, hotkey],
                    expires=60  # 60 second expiration
                )
                logger.info(f"Background task triggered successfully: {task.id}")
                
                response_data["trade_triggered"] = True
                response_data["task_id"] = task.id
                response_data["message"] = "Stake operation triggered in background."
            except Exception as e:
                logger.error(f"Failed to trigger background task: {e}")
                logger.error(traceback.format_exc())
                response_data["message"] = f"Failed to trigger stake operation: {str(e)}"
                response_data["status"] = "partial_success"
        
        # Add processing time to logs
        processing_time = time.time() - start_time
        logger.info(f"Processed dividend request in {processing_time:.4f}s")
        
        return response_data
        
    except Exception as e:
        # Log the error with traceback
        logger.error(f"Error processing dividend request: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Instead of returning a 500 error, return a graceful response with simulated data
        processing_time = time.time() - start_time
        logger.info(f"Failed request processed in {processing_time:.4f}s")
        
        return {
            "netuid": netuid,
            "hotkey": hotkey,
            "dividend_value": 0.0,  # Default value when there's an error
            "timestamp": time.time(),
            "trade_triggered": False,
            "message": f"Service is experiencing temporary issues: {str(e)}",
            "status": "simulated"
        }

# Health check endpoint
@app.get("/health")
async def health_check():
    # Check if Bittensor client is initialized
    client = bittensor_client.get_client()
    is_initialized = getattr(client, "is_initialized", False)
    
    # Attempt to initialize if not already initialized
    if not is_initialized:
        # Try to initialize but don't wait for completion
        asyncio.create_task(client.initialize())
    
    status_info = {
        "status": "healthy" if is_initialized else "degraded",
        "bittensor_client": "initialized" if is_initialized else "not_initialized",
        "timestamp": time.time(),
        "auth": "jwt" if auth_available else "legacy"
    }
    
    # If client has an initialization error, include it
    if hasattr(client, "initialization_error") and client.initialization_error:
        status_info["error"] = client.initialization_error
    
    return status_info

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting up application...")
    
    # Initialize auth if available
    if auth_available:
        try:
            initialize_from_env()
            logger.info("JWT authentication initialized")
        except Exception as e:
            logger.error(f"Failed to initialize JWT authentication: {e}")
    
    # Initialize Bittensor client
    try:
        # Don't await here - let it run in the background so startup isn't blocked
        asyncio.create_task(bittensor_client.initialize())
        logger.info("Bittensor client initialization task started")
    except Exception as e:
        logger.error(f"Failed to start Bittensor client initialization: {e}")
        logger.error(traceback.format_exc())
        # Application will still start, but in degraded mode

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
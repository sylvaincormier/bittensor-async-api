import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
import sys
import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Add project directory to path
sys.path.insert(0, os.path.abspath('.'))

# MARK: Bittensor Client Tests

@pytest.mark.asyncio
async def test_get_tao_dividends_cache_hit():
    """Test get_tao_dividends with cache hit"""
    from bittensor_async_app.services.bittensor_client import get_tao_dividends
    
    # Create redis mock
    redis_mock = MagicMock()
    redis_mock.get = AsyncMock(return_value="0.05")
    redis_mock.set = AsyncMock(return_value=True)
    
    with patch("bittensor_async_app.services.bittensor_client.redis_client", redis_mock):
        result = await get_tao_dividends("18", "test_hotkey")
        
        assert result == 0.05
        redis_mock.get.assert_called_once()

@pytest.mark.asyncio
async def test_get_tao_dividends_no_cache():
    """Test get_tao_dividends with cache miss and simulator fallback"""
    from bittensor_async_app.services.bittensor_client import get_tao_dividends
    
    # Create redis mock
    redis_mock = MagicMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)
    
    with patch("bittensor_async_app.services.bittensor_client.redis_client", redis_mock), \
         patch("bittensor_async_app.services.bittensor_client.simulate_dividend_query", AsyncMock(return_value=0.05)):
        
        result = await get_tao_dividends("18", "test_hotkey")
        
        assert result == 0.05
        redis_mock.get.assert_called_once()
        redis_mock.set.assert_called_once()

@pytest.mark.asyncio
async def test_stake_tao():
    """Test stake_tao function"""
    from bittensor_async_app.services.bittensor_client import stake_tao
    
    # Mock AsyncSubtensor
    subtensor_mock = MagicMock()
    subtensor_mock.add_stake = AsyncMock()
    
    with patch("bittensor_async_app.services.bittensor_client.subtensor", subtensor_mock):
        result = await stake_tao(18, "test_hotkey", 0.75)
        
        assert result["status"] == "success"
        assert result["operation"] == "stake"
        assert result["amount"] == 0.75

@pytest.mark.asyncio
async def test_unstake_tao():
    """Test unstake_tao function"""
    from bittensor_async_app.services.bittensor_client import unstake_tao
    
    # Mock AsyncSubtensor
    subtensor_mock = MagicMock()
    subtensor_mock.unstake = AsyncMock()
    
    with patch("bittensor_async_app.services.bittensor_client.subtensor", subtensor_mock):
        result = await unstake_tao(18, "test_hotkey", 0.5)
        
        assert result["status"] == "success"
        assert result["operation"] == "unstake"
        assert result["amount"] == 0.5

@pytest.mark.asyncio
async def test_stake_tao_zero_amount():
    """Test stake_tao with zero amount"""
    from bittensor_async_app.services.bittensor_client import stake_tao
    
    result = await stake_tao(18, "test_hotkey", 0)
    
    assert result["status"] == "skipped"
    assert "Amount is zero or negative" in result["reason"]

# MARK: API Tests

def test_tao_dividends_endpoint():
    """Test the tao_dividends endpoint with auth bypass"""
    
    from bittensor_async_app.main import app, verify_token
    client = TestClient(app)
    
    # Define a replacement function for verify_token
    async def mock_verify_token(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
        return "test_token"
    
    # Save original overrides
    original_overrides = app.dependency_overrides.copy()
    
    try:
        # Override the verify_token dependency
        app.dependency_overrides[verify_token] = mock_verify_token
        
        # Mock the get_tao_dividends function
        with patch("bittensor_async_app.services.bittensor_client.get_tao_dividends", AsyncMock(return_value=0.05)):
            response = client.get(
                "/api/v1/tao_dividends?netuid=18&hotkey=test_key",
                headers={"Authorization": "Bearer test_token"}
            )
            
            # Check if the response is successful
            assert response.status_code == 200
            
            # Validate the response content
            data = response.json()
            assert "dividend_value" in data
            assert data["netuid"] == "18"
            assert data["hotkey"] == "test_key"
            assert isinstance(data["dividend_value"], float)
    finally:
        # Restore original overrides
        app.dependency_overrides = original_overrides

# Test for the unauthorized case, updated to expect 403 instead of 401
def test_unauthorized_access():
    """Test that unauthorized access is rejected"""
    
    from bittensor_async_app.main import app
    client = TestClient(app)
    
    response = client.get("/api/v1/tao_dividends?netuid=18")
    assert response.status_code == 403  # Updated from 401 to 403

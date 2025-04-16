import pytest
import pytest_asyncio
import asyncio
import sys
import os
from fastapi.testclient import TestClient
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Now import should work
from bittensor_async_app.main import app

# App fixture
@pytest.fixture
def test_app():
    return app

# Sync test client
@pytest.fixture
def client(test_app):
    return TestClient(test_app)

# Async test client - use pytest_asyncio.fixture
@pytest_asyncio.fixture
async def async_client(test_app):
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        yield client

# Mock Redis
@pytest.fixture
def mock_redis():
    redis_mock = MagicMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)
    
    with patch("bittensor_async_app.services.bittensor_client.redis_client", redis_mock):
        yield redis_mock

# Mock for AsyncSubtensor
@pytest.fixture
def mock_subtensor():
    subtensor_mock = MagicMock()
    subtensor_mock.get_tao_dividends_per_subnet = AsyncMock(return_value=1000)
    subtensor_mock.add_stake = AsyncMock()
    subtensor_mock.unstake = AsyncMock()
    
    with patch("bittensor_async_app.services.bittensor_client.subtensor", subtensor_mock):
        yield subtensor_mock

# Mock for simulate_dividend_query
@pytest.fixture
def mock_simulator():
    with patch("bittensor_async_app.services.bittensor_client.simulate_dividend_query", 
               AsyncMock(return_value=0.05)):
        yield

# Auth bypass - inspect main.py to find the correct path for the auth logic
@pytest.fixture
def auth_bypass():
    # Try different paths that might work
    with patch("bittensor_async_app.main.verify_token", return_value=True), \
         patch("bittensor_async_app.main.oauth2_scheme", return_value="test_token"):
        yield

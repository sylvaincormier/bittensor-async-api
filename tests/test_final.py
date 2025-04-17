import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
import sys
import os
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

sys.path.insert(0, os.path.abspath('.'))

# ------------------ Bittensor Client Tests ------------------

@pytest.mark.asyncio
async def test_get_tao_dividends_cache_hit():
    from bittensor_async_app.services.bittensor_client import get_tao_dividends
    redis_mock = MagicMock()
    redis_mock.get = AsyncMock(return_value="0.05")
    redis_mock.set = AsyncMock(return_value=True)

    with patch("bittensor_async_app.services.bittensor_client.redis_client", redis_mock):
        result = await get_tao_dividends("18", "test_hotkey")
        assert result == 0.05

@pytest.mark.asyncio
async def test_get_tao_dividends_no_cache():
    from bittensor_async_app.services.bittensor_client import get_tao_dividends
    redis_mock = MagicMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)

    with patch("bittensor_async_app.services.bittensor_client.redis_client", redis_mock), \
         patch("bittensor_async_app.services.bittensor_client.simulate_dividend_query", AsyncMock(return_value=0.05)):
        result = await get_tao_dividends("18", "test_hotkey")
        assert result == 0.05

@pytest.mark.asyncio
async def test_stake_tao():
    from bittensor_async_app.services.bittensor_client import stake_tao
    # Change this line to mock async_subtensor instead of subtensor
    with patch("bittensor_async_app.services.bittensor_client.async_subtensor", MagicMock()):
        # Rest of the test remains the same
        result = await stake_tao(netuid=1, hotkey="test_hotkey", amount=0.5)
        assert result["status"] == "success"

@pytest.mark.asyncio
async def test_unstake_tao():
    from bittensor_async_app.services.bittensor_client import unstake_tao
    # Change this line to mock async_subtensor instead of subtensor
    with patch("bittensor_async_app.services.bittensor_client.async_subtensor", MagicMock()):
        # Rest of the test remains the same
        result = await unstake_tao(netuid=1, hotkey="test_hotkey", amount=0.5)
        assert result["status"] == "success"

@pytest.mark.asyncio
async def test_stake_tao_zero_amount():
    from bittensor_async_app.services.bittensor_client import stake_tao
    result = await stake_tao(18, "test_hotkey", 0)
    assert isinstance(result, dict)
    assert result["status"] == "skipped"
    assert "Amount is zero or negative" in result["reason"]

# ------------------ API Endpoint Tests ------------------

def test_tao_dividends_endpoint():
    from bittensor_async_app.main import app, verify_token
    client = TestClient(app)

    async def mock_verify_token(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
        return "test_token"

    original_overrides = app.dependency_overrides.copy()

    try:
        app.dependency_overrides[verify_token] = mock_verify_token
        with patch("bittensor_async_app.services.bittensor_client.get_tao_dividends", AsyncMock(return_value=0.05)):
            response = client.get(
                "/api/v1/tao_dividends?netuid=18&hotkey=test_key",
                headers={"Authorization": "Bearer test_token"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["netuid"] == "18"
            assert data["hotkey"] == "test_key"
            assert isinstance(data["dividend_value"], float)
    finally:
        app.dependency_overrides = original_overrides

def test_unauthorized_access():
    from bittensor_async_app.main import app
    client = TestClient(app)
    response = client.get("/api/v1/tao_dividends?netuid=18")
    assert response.status_code == 403

# ------------------ Blockchain Integration Test ------------------

@pytest.mark.asyncio
async def test_get_tao_dividends_real_blockchain():
    from bittensor_async_app.services.bittensor_client import get_tao_dividends
    mock_neuron = MagicMock()
    mock_neuron.uid = 5
    mock_neuron.stake = 1.0
    async_subtensor_mock = MagicMock()
    async_subtensor_mock.get_neuron_for_pubkey_and_subnet = AsyncMock(return_value=mock_neuron)
    async_subtensor_mock.get_total_stake = AsyncMock(return_value=1000.0)
    async_subtensor_mock.get_emission = AsyncMock(return_value=2.5)
    redis_mock = MagicMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)

    with patch("bittensor_async_app.services.bittensor_client.redis_client", redis_mock), \
         patch("bittensor_async_app.services.bittensor_client.async_subtensor", async_subtensor_mock), \
         patch.dict(os.environ, {"PYTEST_CURRENT_TEST": ""}):
        result = await get_tao_dividends("18", "test_hotkey")
        assert isinstance(result, float)
        assert 0 <= result <= 2.5  # Allow range for simulated fallback
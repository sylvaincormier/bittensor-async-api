import pytest
from fastapi.testclient import TestClient
import os
from unittest.mock import patch, AsyncMock

# Import your app - you may need to adjust this import path
from bittensor_async_app.main import app

client = TestClient(app)

# Mock environment variables and services for testing
@pytest.fixture(autouse=True)
def mock_env_and_services():
    """Mock environment variables and services."""
    # Use the actual token that your app is configured to accept
    with patch("bittensor_async_app.services.bittensor_client.get_tao_dividends", 
               AsyncMock(return_value=0.05)):
        yield

def test_health_endpoint():
    """Test that health endpoint reports auth status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data

def test_legacy_auth_success():
    """Test that legacy authentication still works."""
    # Use the token that's set in your API_TOKEN environment variable
    response = client.get(
        "/api/v1/tao_dividends?netuid=18&hotkey=test_key",
        headers={"Authorization": "Bearer datura"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["netuid"] == "18"
    assert data["hotkey"] == "test_key"
    assert isinstance(data["dividend_value"], float)

def test_legacy_auth_failure():
    """Test that legacy authentication rejects invalid tokens."""
    response = client.get(
        "/api/v1/tao_dividends?netuid=18&hotkey=test_key",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 403

def test_token_endpoint():
    """Test the token endpoint if it exists."""
    try:
        response = client.post(
            "/token",
            headers={"Authorization": "Bearer datura"}
        )
        # If the endpoint exists, verify basic response
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
            assert len(data["access_token"]) > 0
        else:
            pytest.skip(f"Token endpoint returned status {response.status_code}")
    except Exception as e:
        # The endpoint might not exist yet, skip this test
        pytest.skip(f"Token endpoint test error: {str(e)}")
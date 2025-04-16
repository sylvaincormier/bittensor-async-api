import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import sys
import os

# Add project directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.mark.asyncio
async def test_fetch_tweets():
    """Test the tweet fetching function with mocked response"""
    from bittensor_async_app.services.sentiment import fetch_tweets
    
    # Mock sample tweets
    mock_tweets = [
        {"text": "This Bittensor subnet 18 is amazing!", "id": "1"},
        {"text": "Not a fan of netuid 18 performance", "id": "2"}
    ]
    
    # Mock the HTTP response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": mock_tweets}
    
    # Mock the client and post method
    mock_client = MagicMock()
    mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
    
    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await fetch_tweets("18")
        
        assert result == mock_tweets
        assert len(result) == 2

@pytest.mark.asyncio
async def test_analyze_sentiment():
    """Test the sentiment analysis function with mocked response"""
    from bittensor_async_app.services.sentiment import analyze_sentiment
    
    # Mock sample tweets
    mock_tweets = [
        {"text": "This Bittensor subnet 18 is amazing!", "id": "1"},
        {"text": "Great work on the network performance", "id": "2"}
    ]
    
    # Mock the HTTP response with a positive sentiment
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"output": "75"}
    
    # Mock the client and post method
    mock_client = MagicMock()
    mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
    
    with patch("httpx.AsyncClient", return_value=mock_client):
        sentiment_score = await analyze_sentiment(mock_tweets)
        
        assert sentiment_score == 75

@pytest.mark.asyncio
async def test_get_sentiment_for_subnet():
    """Test the end-to-end sentiment analysis workflow"""
    from bittensor_async_app.services.sentiment import get_sentiment_for_subnet
    
    # Mock sample tweets
    mock_tweets = [
        {"text": "This Bittensor subnet 18 is amazing!", "id": "1"},
        {"text": "Great work on the network performance", "id": "2"}
    ]
    
    # Mock the fetch_tweets function
    with patch("bittensor_async_app.services.sentiment.fetch_tweets", 
               AsyncMock(return_value=mock_tweets)), \
         patch("bittensor_async_app.services.sentiment.analyze_sentiment", 
               AsyncMock(return_value=75)):
        
        score, tweets = await get_sentiment_for_subnet("18")
        
        assert score == 75
        assert tweets == mock_tweets

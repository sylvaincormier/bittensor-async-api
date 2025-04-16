import logging
import aiohttp
import json
import os

# Configure logging
logger = logging.getLogger(__name__)

async def analyze_sentiment(text, api_key):
    """
    Analyze sentiment of text using Chutes.ai API.
    
    Args:
        text: The text to analyze
        api_key: Chutes.ai API key
        
    Returns:
        Sentiment score from -100 (negative) to 100 (positive)
    """
    try:
        logger.info(f"Analyzing sentiment of text ({len(text)} chars)")
        
        # Chutes.ai API endpoint (using the LLM chute specified in the task)
        url = "https://api.chutes.ai/api/v1/chute/20acffc0-0c5f-58e3-97af-21fc0b261ec4/predict"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # Create prompt for sentiment analysis
        prompt = f"""
        Analyze the sentiment of the following tweets about Bittensor cryptocurrency project.
        Rate the overall sentiment on a scale from -100 (extremely negative) to 0 (neutral) to +100 (extremely positive).
        Only respond with a single integer number between -100 and 100.
        
        Tweets:
        {text}
        """
        
        payload = {
            "inputs": {
                "prompt": prompt
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    # Extract the sentiment score from the API response
                    # The API should return a single number as requested in the prompt
                    try:
                        raw_response = result.get("outputs", {}).get("generation", "0")
                        
                        # Clean up the response to extract just the number
                        clean_response = raw_response.strip()
                        
                        # Try to parse as integer
                        sentiment_score = int(clean_response)
                        
                        # Ensure the score is within the expected range
                        sentiment_score = max(-100, min(100, sentiment_score))
                        
                        logger.info(f"Sentiment analysis result: {sentiment_score}")
                        return sentiment_score
                    except (ValueError, KeyError) as e:
                        logger.error(f"Error parsing sentiment response: {e}, raw response: {raw_response}")
                        # Return neutral sentiment as fallback
                        return 0
                else:
                    error_text = await response.text()
                    logger.error(f"Error from Chutes.ai API: {error_text}")
                    # Return neutral sentiment as fallback
                    return 0
    except Exception as e:
        logger.error(f"Exception in sentiment analysis: {e}")
        # Return neutral sentiment as fallback
        return 0

async def search_twitter(query, api_key):
    """
    Search Twitter using Datura.ai API.
    
    Args:
        query: The search query
        api_key: Datura.ai API key
        
    Returns:
        List of tweets
    """
    url = "https://api.datura.ai/api/twitter/search"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url,
            headers=headers,
            json={"query": query, "limit": 20}
        ) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("tweets", [])
            else:
                error_text = await response.text()
                logger.error(f"Error searching Twitter: {error_text}")
                return []

async def analyze_twitter_sentiment(search_query, datura_api_key, chutes_api_key):
    """
    Search Twitter for a query and analyze sentiment of the results.
    
    Args:
        search_query: The Twitter search query
        datura_api_key: API key for Datura.ai
        chutes_api_key: API key for Chutes.ai
        
    Returns:
        Sentiment score from -100 (negative) to 100 (positive)
    """
    logger.info(f"Analyzing Twitter sentiment for query: {search_query}")
    
    # Search Twitter
    tweets = await search_twitter(search_query, datura_api_key)
    
    if not tweets or len(tweets) == 0:
        logger.warning(f"No tweets found for search query: {search_query}")
        return 0  # Neutral sentiment if no tweets found
    
    # Extract text from tweets
    tweet_text = "\n".join([t.get("text", "") for t in tweets])
    logger.info(f"Found {len(tweets)} tweets for analysis")
    
    # Analyze sentiment
    sentiment_score = await analyze_sentiment(tweet_text, chutes_api_key)
    
    logger.info(f"Sentiment analysis result: {sentiment_score}")
    return sentiment_score
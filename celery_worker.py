import os
import logging
import asyncio
from celery import Celery
from celery.signals import worker_process_init
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up Celery
redis_host = os.getenv("REDIS_HOST", "localhost")
app = Celery(
    "bittensor_worker",
    broker=f"redis://{redis_host}:6379/0",
    backend=f"redis://{redis_host}:6379/0"
)

app.conf.task_routes = {
    "celery_worker.process_stake_operation": {"queue": "stake_operations"},
}

# Import here to avoid circular imports
from bittensor_async_app.services.bittensor_client import add_stake, unstake, initialize
from bittensor_async_app.services.sentiment import analyze_twitter_sentiment

# List of initialized processes to prevent duplicate initialization
initialized_processes = set()

@worker_process_init.connect
def init_worker(**kwargs):
    """Initialize worker process once."""
    process_id = os.getpid()
    if process_id not in initialized_processes:
        logger.info(f"Initializing worker process {process_id}")
        # Create a new event loop for the worker
        loop = asyncio.get_event_loop()
        # Initialize the bittensor client in this process
        loop.run_until_complete(initialize())
        initialized_processes.add(process_id)
        logger.info(f"Worker process {process_id} initialized")

@app.task(name="celery_worker.process_stake_operation", bind=True, max_retries=3)
def process_stake_operation(self, netuid, hotkey):
    """
    Background task to perform stake operation based on sentiment analysis.
    
    Args:
        netuid: The subnet ID
        hotkey: The hotkey to stake to/unstake from
    """
    logger.info(f"Starting stake operation task for netuid={netuid}, hotkey={hotkey}")
    
    try:
        # Run the async operations in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the sentiment analysis and stake operation
        # Using the properly named function without underscore prefix
        result = loop.run_until_complete(process_stake_operation_async(netuid, hotkey))
        loop.close()
        
        return result
    except Exception as e:
        logger.error(f"Error in stake operation task: {e}")
        # Retry with exponential backoff
        self.retry(exc=e, countdown=2 ** self.request.retries)
        return {"status": "error", "message": str(e)}

async def process_stake_operation_async(netuid, hotkey):
    """
    Async implementation of the stake operation process.
    
    1. Query Twitter for sentiment about the subnet
    2. Analyze sentiment with Chutes.ai
    3. Stake or unstake based on sentiment score
    """
    try:
        # 1. Query Twitter and analyze sentiment
        logger.info(f"Analyzing Twitter sentiment for Bittensor netuid {netuid}")
        search_query = f"Bittensor netuid {netuid}"
        
        # Get API keys from environment - no hardcoded defaults
        datura_api_key = os.getenv("DATURA_APIKEY")
        chutes_api_key = os.getenv("CHUTES_API_KEY")
        
        if not datura_api_key or not chutes_api_key:
            logger.error("Missing API keys in environment variables")
            return {
                "status": "error",
                "message": "API keys not configured. Please set DATURA_APIKEY and CHUTES_API_KEY in environment variables."
            }
        
        # Use the sentiment analysis function
        sentiment_score = await analyze_twitter_sentiment(search_query, datura_api_key, chutes_api_key)
        
        logger.info(f"Sentiment analysis result: {sentiment_score}")
        
        if sentiment_score == 0:
            logger.info("Neutral sentiment. No stake operation needed.")
            return {
                "status": "neutral",
                "sentiment_score": sentiment_score,
                "message": "Neutral sentiment. No stake operation performed."
            }
        
        # 3. Perform stake or unstake based on sentiment
        amount = abs(sentiment_score) * 0.01  # 0.01 tao * sentiment score
        
        # Ensure netuid is properly typed
        if isinstance(netuid, str):
            try:
                netuid = int(netuid)
            except ValueError:
                logger.warning(f"Could not convert netuid {netuid} to integer, using as is")
        
        if sentiment_score > 0:
            # Positive sentiment: add stake
            # Using named parameters with correct order - amount, netuid, hotkey
            result = await add_stake(amount=amount, netuid=netuid, hotkey=hotkey)
            success = result.get("status") == "success"
            message = result.get("reason", "Stake operation completed")
        else:
            # Negative sentiment: unstake
            # Using named parameters with correct order - amount, netuid, hotkey
            result = await unstake(amount=amount, netuid=netuid, hotkey=hotkey)
            success = result.get("status") == "success" 
            message = result.get("reason", "Unstake operation completed")
        
        # Return result
        return {
            "status": "success" if success else "error",
            "sentiment_score": sentiment_score,
            "operation": "stake" if sentiment_score > 0 else "unstake",
            "amount": amount,
            "message": message,
            "netuid": netuid,
            "hotkey": hotkey
        }
        
    except Exception as e:
        logger.error(f"Error in stake operation: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "message": f"Error processing stake operation: {str(e)}"
        }

if __name__ == "__main__":
    # Start Celery worker
    app.start()
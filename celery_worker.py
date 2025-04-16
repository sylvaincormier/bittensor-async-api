import os
import logging
import asyncio
from celery import Celery
from celery.signals import worker_process_init
import time

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
        result = loop.run_until_complete(_process_stake_operation_async(netuid, hotkey))
        loop.close()
        
        return result
    except Exception as e:
        logger.error(f"Error in stake operation task: {e}")
        # Retry with exponential backoff
        self.retry(exc=e, countdown=2 ** self.request.retries)
        return {"status": "error", "message": str(e)}

async def _process_stake_operation_async(netuid, hotkey):
    """
    Async implementation of the stake operation process.
    
    1. Query Twitter for sentiment about the subnet
    2. Analyze sentiment with Chutes.ai
    3. Stake or unstake based on sentiment score
    """
    try:
        # 1. Query Twitter and analyze sentiment (using your existing sentiment module)
        logger.info(f"Analyzing Twitter sentiment for Bittensor netuid {netuid}")
        search_query = f"Bittensor netuid {netuid}"
        
        # Get API keys from environment
        datura_api_key = os.getenv("DATURA_APIKEY", "dt_$q4qWC2K5mwT5BnNh0ZNF9MfeMDJenJ-pddsi_rE1FZ8")
        chutes_api_key = os.getenv("CHUTES_API_KEY", "cpk_9402c24cc755440b94f4b0931ebaa272.7a748b60e4a557f6957af9ce25778f49.8huXjHVlrSttzKuuY0yU2Fy4qEskr5J0")
        
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
        
        # Default parameters if not specified
        netuid = netuid or "18"
        hotkey = hotkey or "5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v"
        
        if sentiment_score > 0:
            # Positive sentiment: add stake
            success, message = await add_stake(netuid, hotkey, amount)
        else:
            # Negative sentiment: unstake
            success, message = await unstake(netuid, hotkey, amount)
        
        # Return result
        return {
            "status": "success" if success else "error",
            "sentiment_score": sentiment_score,
            "operation": "stake" if sentiment_score > 0 else "unstake",
            "amount": amount,
            "message": message
        }
        
    except Exception as e:
        logger.error(f"Error in stake operation: {e}")
        return {
            "status": "error",
            "message": f"Error processing stake operation: {str(e)}"
        }

if __name__ == "__main__":
    # Start Celery worker
    app.start()
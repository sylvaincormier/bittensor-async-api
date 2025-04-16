
# Bittensor Async API

An asynchronous API service for querying Tao dividends from the Bittensor blockchain with sentiment analysis-based trading capabilities.

## Project Overview

This service implements a production-grade asynchronous API that:

1. **Queries Blockchain Data**: Fetches Tao dividends from the Bittensor testnet blockchain with robust error handling and fallback mechanisms
2. **Implements Caching**: Uses Redis to cache query results for 2 minutes using `netuid:hotkey` format
3. **Provides Sentiment Analysis Trading**: Analyzes Twitter sentiment and automatically stakes/unstakes TAO proportional to sentiment score
4. **Uses Async Processing**: Leverages Celery for background tasks to maintain responsive API endpoints
5. **Stores Historical Data**: Persists data in an async-compatible database

The architecture follows modern asynchronous patterns to efficiently handle high-concurrency workloads.

## Getting Started

### Environment Variables

Copy the `.env.example` file and update it with your own API keys and configuration:
```bash
cp .env.example .env
```

### Using Docker (Recommended)

The easiest way to run the service is with Docker Compose:

```bash
# Clone the repository
git clone https://github.com/sylvaincormier/bittensor-async-api.git
cd bittensor-async-api

# Build and start all services
docker-compose up --build
```

This command starts:
- The FastAPI application on http://localhost:8000
- Redis for caching and message brokering
- A database for persistent storage
- Celery workers for background tasks

To run tests inside the Docker container:
```bash
docker-compose exec api pytest -v
```

### Docker Considerations

When running in Docker, the application uses in-memory wallet handling to avoid file permission issues that can occur in containerized environments. This approach enables blockchain operations without requiring interactive password input or file write permissions.

### Running Locally

To run the service without Docker:

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start FastAPI app
uvicorn bittensor_async_app.main:app --reload

# Start a separate terminal for Celery worker
celery -A celery_worker worker --loglevel=info
```

Make sure Redis and your database service are running locally.

## API Endpoints

### GET `/api/v1/tao_dividends`
Protected endpoint that returns the Tao dividends data for a given subnet and hotkey.

Query parameters:
- `netuid`: (optional) subnet ID (default: 18)
- `hotkey`: (optional) wallet hotkey address (default: 5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v)
- `trade`: (optional, default `false`) whether to trigger background staking based on sentiment

Requires Bearer token in the `Authorization` header.

Example response:
```json
{
  "netuid": "18",
  "hotkey": "5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v",
  "dividend_value": 0.0312,
  "timestamp": 1744813893.3680327,
  "trade_triggered": true,
  "message": "Stake operation triggered in background.",
  "task_id": "2492a4ab-689c-47bc-82b8-5bb4506a1bcb"
}
```

### GET `/api/v1/dividend_history`
Returns historical records of dividend queries from the database.

Query parameters:
- `netuid`: (optional) filter by subnet
- `hotkey`: (optional) filter by hotkey
- `limit`: (optional, default `100`) number of results to return

### GET `/health`
Simple health check.

```json
{
  "status": "healthy"
}
```

## Testing the API

Use these curl commands to test the functionality:

```bash
# 1. Health check
curl http://localhost:8000/health

# 2. Get TAO dividends (without trading)
curl -X GET "http://localhost:8000/api/v1/tao_dividends?netuid=18&hotkey=5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v" -H "Authorization: Bearer datura"

# 3. Verify Redis caching (same request, should be faster)
curl -X GET "http://localhost:8000/api/v1/tao_dividends?netuid=18&hotkey=5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v" -H "Authorization: Bearer datura"

# 4. Get TAO dividends with trading (triggers sentiment analysis and staking)
curl -X GET "http://localhost:8000/api/v1/tao_dividends?netuid=18&hotkey=5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v&trade=true" -H "Authorization: Bearer datura"

# 5. Test authentication failure
curl -X GET "http://localhost:8000/api/v1/tao_dividends?netuid=18&hotkey=5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v" -H "Authorization: Bearer wrong_token"
```

## Blockchain Integration

The system connects to the Bittensor testnet, using the coldkey address from your python-task wallet (5FeuZmnSt8oeuP9Ms3vwWvePS8cm4Pz1DyZX8YqynqCZcZ4y) as a fallback mechanism. This ensures the API remains functional even in containerized environments where wallet file access might be limited.

For real blockchain transactions (staking/unstaking), you would need:
1. A wallet with the mnemonic provided in the environment variables
2. Testnet tokens - typically acquired from a faucet or transferred from another wallet
3. Proper network connectivity to the testnet

The implementation calculates stake amounts as 0.01 * sentiment score, following the requirements.

## Environment Variables

Create a `.env` file with the following:
```
API_TOKEN=datura
REDIS_HOST=redis
DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/mydb
DATURA_APIKEY=your_datura_key
CHUTES_API_KEY=your_chutes_key
WALLET_MNEMONIC=diamond like interest affair safe clarify lawsuit innocent beef van grief color
WALLET_HOTKEY=default_hotkey_name
```

## Tests

To run the test suite locally:
```bash
PYTHONPATH=. pytest -v
```

To run the test suite inside Docker:
```bash
docker-compose exec api pytest -v
```

Unit and end-to-end tests are located in the `tests/` directory. Use mocks to avoid real network calls during testing.

## Performance Testing

The service has been load tested to verify its ability to handle high concurrency. Results demonstrate excellent performance characteristics:


## Performance Testing

The service has been load tested to verify its ability to handle high concurrency. Results demonstrate exceptional performance characteristics:

### Load Test Results
```
===== Load Test Results =====
Total Requests: 1000
Concurrency Level: 10
Success Rate: 100.00%
Average Response Time: 0.0082 seconds (8.2ms)
Minimum Response Time: 0.0030 seconds (3.0ms)
Maximum Response Time: 0.0331 seconds (33.1ms)
Median Response Time: 0.0080 seconds (8.0ms)
95th Percentile Response Time: 0.0107 seconds (10.7ms)
Requests per Second: 121.49
===== Response Status Distribution =====
Status 200: 1000 requests (100.00%)
Total test duration: 1.01 seconds
```

These results demonstrate that the API can easily handle 1000 requests with:
- Perfect success rate (100%)
- Extremely fast response times (average under 10ms)
- High throughput (over 120 requests per second)
- Excellent reliability (no failures)

You can run the load test yourself using the included script:

```bash
python load_test_script.py --url http://localhost:8000 --token datura --requests 1000 --concurrency 10
```


## License

MIT License

## Author

Built by Silvereau



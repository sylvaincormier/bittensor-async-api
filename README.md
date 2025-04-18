# Bittensor Async API

An asynchronous API service for querying Tao dividends from the Bittensor blockchain with sentiment analysis-based trading capabilities.

## Project Overview

This service implements a production-grade asynchronous API that:

- **Queries Blockchain Data**: Fetches Tao dividends from the Bittensor testnet blockchain with robust error handling and fallback mechanisms
- **Implements Caching**: Uses Redis to cache query results for 2 minutes using netuid:hotkey format
- **Provides Sentiment Analysis Trading**: Analyzes Twitter sentiment and automatically stakes/unstakes TAO proportional to sentiment score
- **Uses Async Processing**: Leverages Celery for background tasks to maintain responsive API endpoints
- **Stores Historical Data**: Persists data in an async-compatible database

The architecture follows modern asynchronous patterns to efficiently handle high-concurrency workloads.

## Blockchain Integration Details

The system properly implements asynchronous blockchain interactions:

- Uses AsyncSubtensor for all blockchain operations with no blocking calls
- Implements query_map to get taodividendspersubnet data
- Properly handles staking operations with wallet hotkey management
- Provides fallback simulation when blockchain data is unavailable

## Security Features

- **Environment-based Configuration**: All sensitive credentials are stored in environment variables
- **Authentication Options**: Supports both legacy API tokens and JWT-based authentication
- **Graceful Error Handling**: Provides fallback mechanisms for all critical services
- **Robust Logging**: Comprehensive logging for troubleshooting and security auditing

## Getting Started

### Environment Variables

Copy the .env.example file and update it with your own API keys and configuration:

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
- PostgreSQL database for persistent storage
- Celery workers for background tasks

To run tests inside the Docker container:

```bash
docker-compose exec api pytest -v
```

#### Docker Considerations

When running in Docker, the application uses in-memory wallet handling to avoid file permission issues that can occur in containerized environments. This approach enables blockchain operations without requiring interactive password input or file write permissions.

### Running Locally

To run the service without Docker:

```bash
# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start FastAPI app
uvicorn bittensor_async_app.main:app --reload

# Start a separate terminal for Celery worker
celery -A celery_worker worker --loglevel=info
```

Make sure Redis and your database service are running locally.

## API Endpoints

### Authentication

The API supports two authentication methods:

- Legacy Bearer token (API key)
- JWT token-based authentication

To obtain a JWT token:

```bash
curl -X POST "http://localhost:8000/token" \
  -H "Authorization: Bearer datura"
```

### GET /api/v1/tao_dividends

Protected endpoint that returns the Tao dividends data for a given subnet and hotkey.

Query parameters:

- `netuid`: (optional) subnet ID (default: 18)
- `hotkey`: (optional) wallet hotkey address (default: 5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v)
- `trade`: (optional, default false) whether to trigger background staking based on sentiment

Requires Bearer token in the Authorization header.

Example response:

```json
{
  "netuid": "18",
  "hotkey": "5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v",
  "dividend_value": 0.0312,
  "timestamp": 1744813893.3680327,
  "trade_triggered": true,
  "message": "Stake operation triggered in background.",
  "task_id": "2492a4ab-689c-47bc-82b8-5bb4506a1bcb",
  "status": "success"
}
```

### GET /health

Health check endpoint that also reports system status.

```json
{
  "status": "healthy",
  "bittensor_client": "initialized", 
  "timestamp": 1744843492.352110,
  "auth": "legacy"
}
```

## Testing the API

Use these curl commands to test the functionality:

```bash
# 1. Health check
curl http://localhost:8000/health

# 2. Get TAO dividends (without trading)
curl -X GET "http://localhost:8000/api/v1/tao_dividends?netuid=18" \
  -H "Authorization: Bearer datura"

# 3. Verify Redis caching (same request, should be faster)
curl -X GET "http://localhost:8000/api/v1/tao_dividends?netuid=18" \
  -H "Authorization: Bearer datura"

# 4. Get TAO dividends with trading (triggers sentiment analysis and staking)
curl -X GET "http://localhost:8000/api/v1/tao_dividends?netuid=18&trade=true" \
  -H "Authorization: Bearer datura"

# 5. Test authentication failure
curl -X GET "http://localhost:8000/api/v1/tao_dividends?netuid=18" \
  -H "Authorization: Bearer wrong_token"
```

## Blockchain Integration

The system connects to the Bittensor testnet and queries real-time blockchain data for dividends using AsyncSubtensor with the query_map method to efficiently retrieve taodividendspersubnet data.

For real blockchain transactions (staking/unstaking), you need:

- A wallet with the mnemonic provided in the environment variables
- Testnet tokens - typically acquired from a faucet or transferred from another wallet
- Proper network connectivity to the testnet

The implementation calculates stake amounts as 0.01 * sentiment score, following the requirements.

## Environment Variables

Create a .env file with the following:

```
# Authentication
API_TOKEN=datura
JWT_SECRET=your_jwt_secret_here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=30

# Connection Settings
REDIS_HOST=redis
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/bittensor

# External APIs
DATURA_API_KEY=your_datura_key
CHUTES_API_KEY=your_chutes_key

# Blockchain Settings
WALLET_MNEMONIC=your_wallet_mnemonic
NETUID=18
HOTKEY=your_hotkey_address
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

Unit and end-to-end tests are located in the tests/ directory.

## Performance Testing

The service has been thoroughly load tested to verify its ability to handle high concurrency:

```
=== LOAD TEST SUMMARY ===
Total Requests: 2000
Successful Requests: 2000 (100.00%)
Average Response Time: 0.2292 seconds
Median Response Time: 0.2146 seconds
95th Percentile Response Time: 0.4187 seconds
Min/Max Response Time: 0.0558/0.4366 seconds
Throughput: 1824.57 requests/second
```

These results demonstrate the API meets production-grade requirements for handling 1000+ concurrent connections with excellent response times and 100% reliability.

### Running the Load Test

You can run the load test with these steps:

```bash
# Create a virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install aiohttp pandas matplotlib seaborn

# Run the load tester
cd scripts
python load_tester.py --endpoint "http://localhost:8000/api/v1/tao_dividends" --token datura --concurrency 1000 --requests 2000
```

Alternatively, you can run the load test directly from the Docker container:

```bash
# Copy the load tester to the container
docker cp scripts/load_tester.py bittensor-async-api-api-1:/app/load_tester.py

# Run the load test
docker exec bittensor-async-api-api-1 python /app/load_tester.py \
  --endpoint "http://api:8000/api/v1/tao_dividends" \
  --concurrency 1000 \
  --requests 2000 \
  --token "datura"
```

## License

MIT License

## Author

Built by Silvereau
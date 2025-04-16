#!/bin/bash
# Run the load test against Bittensor API

# Install required packages
pip install aiohttp rich

# Run the load test script with different concurrency levels
python load_test_script.py --url http://localhost:8000 --token datura --requests 1000 --concurrency 100

# For a more intensive test, you can uncomment and run with higher concurrency
# python load_test_script.py --url http://localhost:8000 --token datura --requests 1000 --concurrency 200

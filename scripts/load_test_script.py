#!/usr/bin/env python3
"""
Load Testing Script for Bittensor Async API

This script performs load testing on the Bittensor Async API to verify
its performance under high concurrency conditions.
"""

import argparse
import asyncio
import logging
import time
import statistics
import os
from typing import Dict, List, Tuple, Optional
from collections import Counter, defaultdict

import aiohttp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("load_test")

class LoadTester:
    """Load testing class for the Bittensor Async API."""
    
    def __init__(self, 
                 base_url: str, 
                 auth_token: str, 
                 num_requests: int, 
                 concurrency: int,
                 endpoint: str = "/api/v1/tao_dividends",
                 params: Optional[Dict] = None):
        """
        Initialize the load tester.
        
        Args:
            base_url: Base URL of the API
            auth_token: Authentication token
            num_requests: Total number of requests to make
            concurrency: Number of concurrent requests
            endpoint: API endpoint to test
            params: Query parameters for the request
        """
        self.base_url = base_url
        self.auth_token = auth_token
        self.num_requests = num_requests
        self.concurrency = concurrency
        self.endpoint = endpoint
        self.params = params or {}
        
        # Results storage
        self.response_times = []
        self.status_codes = Counter()
        self.errors = []
    
    async def make_request(self, request_id: int) -> None:
        """
        Make a single request to the API and record the results.
        
        Args:
            request_id: Unique identifier for this request
        """
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        url = f"{self.base_url}{self.endpoint}"
        
        try:
            start_time = time.time()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=self.params) as response:
                    await response.text()  # Ensure the response is fully read
                    
                    # Record results
                    elapsed = time.time() - start_time
                    self.response_times.append(elapsed)
                    self.status_codes[response.status] += 1
            
            logger.debug(f"Completed request {request_id}/{self.num_requests}")
            
        except Exception as e:
            self.errors.append(str(e))
            logger.error(f"Error in request {request_id}: {str(e)}")
    
    async def run(self) -> None:
        """Run the load test with the specified parameters."""
        logger.info(f"Starting load test with {self.num_requests} requests...")
        logger.info(f"Concurrency level: {self.concurrency}")
        
        # Calculate how many batches we need to run
        batch_count = (self.num_requests + self.concurrency - 1) // self.concurrency
        
        # Run in batches of concurrent requests
        for batch in range(batch_count):
            remaining = min(self.concurrency, self.num_requests - batch * self.concurrency)
            logger.info(f"Running batch {batch+1}/{batch_count} ({remaining} requests)")
            
            tasks = [self.make_request(batch * self.concurrency + i) for i in range(remaining)]
            await asyncio.gather(*tasks)
    
    def report_results(self) -> None:
        """Generate and print a report of the load test results."""
        if not self.response_times:
            logger.warning("No successful requests to analyze")
            return
        
        # Calculate statistics
        avg_time = statistics.mean(self.response_times)
        min_time = min(self.response_times)
        max_time = max(self.response_times)
        median_time = statistics.median(self.response_times)
        
        # Calculate 95th percentile
        sorted_times = sorted(self.response_times)
        p95_index = int(len(sorted_times) * 0.95)
        p95_time = sorted_times[p95_index]
        
        # Calculate success rate
        success_count = sum(count for status, count in self.status_codes.items() if 200 <= status < 300)
        success_rate = (success_count / self.num_requests) * 100
        
        # Log the results
        logger.info("\n===== Load Test Results =====")
        logger.info(f"Total Requests: {self.num_requests}")
        logger.info(f"Concurrency Level: {self.concurrency}")
        logger.info(f"Success Rate: {success_rate:.2f}%")
        logger.info(f"Average Response Time: {avg_time:.4f} seconds")
        logger.info(f"Minimum Response Time: {min_time:.4f} seconds")
        logger.info(f"Maximum Response Time: {max_time:.4f} seconds")
        logger.info(f"Median Response Time: {median_time:.4f} seconds")
        logger.info(f"95th Percentile Response Time: {p95_time:.4f} seconds")
        logger.info(f"Requests per Second: {self.num_requests / sum(self.response_times):.2f}")
        
        # Log status code distribution
        logger.info("\n===== Response Status Distribution =====")
        
        for status, count in sorted(self.status_codes.items()):
            percentage = (count / self.num_requests) * 100
            logger.info(f"Status {status}: {count} requests ({percentage:.2f}%)")
        
        # Log any errors
        if self.errors:
            logger.info("\n===== Errors =====")
            for error in self.errors[:10]:  # Show only first 10 errors to avoid overwhelming output
                logger.info(error)
            
            if len(self.errors) > 10:
                logger.info(f"... and {len(self.errors) - 10} more errors")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Load testing tool for Bittensor Async API")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the API")
    parser.add_argument("--token", default="", help="Authentication token")
    parser.add_argument("--requests", type=int, default=100, help="Number of requests to make")
    parser.add_argument("--concurrency", type=int, default=10, help="Number of concurrent requests")
    parser.add_argument("--endpoint", default="/api/v1/tao_dividends", help="API endpoint to test")
    parser.add_argument("--netuid", type=int, default=18, help="Network ID parameter")
    parser.add_argument("--hotkey", default="5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v", help="Hotkey parameter")
    return parser.parse_args()

async def main():
    """Main entry point for the load test script."""
    args = parse_args()
    
    # Get token from environment if not provided, with no default value
    # This forces users to either provide token via CLI argument or environment variable
    auth_token = args.token or os.getenv("API_TOKEN")
    
    if not auth_token:
        logger.error("No authentication token provided. Use --token argument or set API_TOKEN environment variable")
        return
    
    # Set up request parameters
    params = {
        "netuid": args.netuid,
        "hotkey": args.hotkey
    }
    
    # Create and run load tester
    tester = LoadTester(
        base_url=args.url,
        auth_token=auth_token,
        num_requests=args.requests,
        concurrency=args.concurrency,
        endpoint=args.endpoint,
        params=params
    )
    
    start_time = time.time()
    await tester.run()
    total_time = time.time() - start_time
    
    # Report results
    tester.report_results()
    logger.info(f"\nTotal test duration: {total_time:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main())
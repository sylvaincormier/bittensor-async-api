#!/usr/bin/env python3
"""
Load Testing Script for Bittensor Async API

This script performs load testing on the Bittensor Async API to verify
its performance under high concurrency conditions with varied parameters.
"""

import argparse
import asyncio
import logging
import time
import statistics
import os
import random
from typing import Dict, List, Tuple, Optional, Any
from collections import Counter, defaultdict

import aiohttp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("load_test")

class LoadTester:
    """Load testing class for the Bittensor Async API with varied parameters."""
    
    def __init__(self, 
                 base_url: str, 
                 auth_token: str, 
                 num_requests: int, 
                 concurrency: int,
                 endpoint: str = "/api/v1/tao_dividends",
                 param_variations: Optional[List[Dict[str, Any]]] = None,
                 fixed_params: Optional[Dict[str, Any]] = None):
        """
        Initialize the load tester.
        
        Args:
            base_url: Base URL of the API
            auth_token: Authentication token
            num_requests: Total number of requests to make
            concurrency: Number of concurrent requests
            endpoint: API endpoint to test
            param_variations: List of different parameter combinations to use for testing
            fixed_params: Parameters that should remain fixed for all requests
        """
        self.base_url = base_url
        self.auth_token = auth_token
        self.num_requests = num_requests
        self.concurrency = concurrency
        self.endpoint = endpoint
        self.param_variations = param_variations or []
        self.fixed_params = fixed_params or {}
        
        # If no param variations provided, warn user
        if not self.param_variations:
            logger.warning("No parameter variations provided. Using fixed parameters for all requests.")
        
        # Results storage
        self.response_times = []
        self.status_codes = Counter()
        self.errors = []
        self.param_stats = defaultdict(list)  # Track performance by parameter combination
    
    async def make_request(self, request_id: int) -> None:
        """
        Make a single request to the API and record the results.
        
        Args:
            request_id: Unique identifier for this request
        """
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        url = f"{self.base_url}{self.endpoint}"
        
        # Select parameters to use for this request
        if self.param_variations:
            # Use modulo to cycle through parameter variations
            variation_index = request_id % len(self.param_variations)
            params = {**self.fixed_params, **self.param_variations[variation_index]}
            param_key = str(params)  # For tracking stats by parameter
        else:
            # Just use fixed parameters
            params = self.fixed_params
            param_key = str(params)
        
        try:
            start_time = time.time()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    response_data = await response.json()
                    
                    # Record results
                    elapsed = time.time() - start_time
                    self.response_times.append(elapsed)
                    self.status_codes[response.status] += 1
                    
                    # Record stats by parameter
                    self.param_stats[param_key].append({
                        'time': elapsed,
                        'status': response.status,
                        'params': params.copy(),
                        'dividend_value': response_data.get('dividend_value', 0)
                    })
            
            logger.debug(f"Completed request {request_id}/{self.num_requests} with params: {params}")
            
        except Exception as e:
            self.errors.append(f"Request {request_id} with params {params}: {str(e)}")
            logger.error(f"Error in request {request_id}: {str(e)}")
    
    async def run(self) -> None:
        """Run the load test with the specified parameters."""
        logger.info(f"Starting load test with {self.num_requests} requests...")
        logger.info(f"Concurrency level: {self.concurrency}")
        logger.info(f"Testing {len(self.param_variations) or 1} different parameter combinations")
        
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
        
        # Calculate overall statistics
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
        
        # Log the overall results
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
        
        # Log performance by parameter combination
        if len(self.param_stats) > 1:
            logger.info("\n===== Performance by Parameter Combination =====")
            for param_key, stats in self.param_stats.items():
                if not stats:
                    continue
                    
                # Extract the actual params for display
                params = stats[0]['params']
                success_count = sum(1 for s in stats if 200 <= s['status'] < 300)
                success_rate = (success_count / len(stats)) * 100 if stats else 0
                times = [s['time'] for s in stats]
                
                logger.info(f"\nParameters: {params}")
                logger.info(f"  Requests: {len(stats)}")
                logger.info(f"  Success Rate: {success_rate:.2f}%")
                if times:
                    logger.info(f"  Avg Response Time: {statistics.mean(times):.4f} seconds")
                    if len(times) > 1:
                        logger.info(f"  Min/Max Time: {min(times):.4f}/{max(times):.4f} seconds")
                    
                # Check for variance in dividend values
                if stats:
                    dividend_values = [s['dividend_value'] for s in stats]
                    unique_values = set(dividend_values)
                    logger.info(f"  Unique dividend values: {len(unique_values)}")
                    if len(unique_values) <= 5:  # Only show all values if there aren't too many
                        logger.info(f"  Values: {unique_values}")
        
        # Log any errors
        if self.errors:
            logger.info("\n===== Errors =====")
            for error in self.errors[:10]:  # Show only first 10 errors
                logger.info(error)
            
            if len(self.errors) > 10:
                logger.info(f"... and {len(self.errors) - 10} more errors")

def generate_test_variations(netuid_range=None, hotkeys=None, additional_params=None):
    """
    Generate test parameter variations.
    
    Args:
        netuid_range: Range of netuid values to test
        hotkeys: List of hotkeys to test
        additional_params: Additional parameters to vary
        
    Returns:
        List of parameter dictionaries
    """
    if netuid_range is None:
        netuid_range = range(1, 21)  # Default: test netuids 1-20
        
    if hotkeys is None:
        # Default: 5 different hotkeys to test with
        hotkeys = [
            "5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v",  # Original test hotkey
            "5CK2ZFwG5iUaFQjC3sL2o5t4fGEPiYg8GiuYcNRzGN91gx8t",  # Random hotkey 1
            "5CXNq93RHoD8UJYsL2n4yZKLHBT6Zyf5j5W1Py8qHGcCFKqZ",  # Random hotkey 2
            "5Gv6jZ3aiRNvJ8PqKH4FHqbahGi4eYcxJzDDzLRKKcePkst3",  # Random hotkey 3
            "5CaLyzSH5xEvKV8opDJxjvUJKU6gUhy3yRbkjkgKKH5sLKVZ"   # Random hotkey 4
        ]
    
    variations = []
    
    # Create combinations of netuids and hotkeys
    for netuid in netuid_range:
        for hotkey in hotkeys:
            # Start with basic parameters
            params = {
                "netuid": str(netuid),
                "hotkey": hotkey
            }
            
            # Add any additional parameters
            if additional_params:
                for key, values in additional_params.items():
                    for value in values:
                        params_copy = params.copy()
                        params_copy[key] = value
                        variations.append(params_copy)
            else:
                variations.append(params)
    
    return variations

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Load testing tool for Bittensor Async API")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the API")
    parser.add_argument("--token", default="", help="Authentication token")
    parser.add_argument("--requests", type=int, default=100, help="Number of requests to make")
    parser.add_argument("--concurrency", type=int, default=10, help="Number of concurrent requests")
    parser.add_argument("--endpoint", default="/api/v1/tao_dividends", help="API endpoint to test")
    parser.add_argument("--min-netuid", type=int, default=1, help="Minimum netuid to test")
    parser.add_argument("--max-netuid", type=int, default=20, help="Maximum netuid to test")
    parser.add_argument("--test-trade", action="store_true", help="Also test with trade=true parameter")
    parser.add_argument("--random-order", action="store_true", help="Randomize parameter order")
    return parser.parse_args()

async def main():
    """Main entry point for the load test script."""
    args = parse_args()
    
    # Get token from environment if not provided
    auth_token = args.token or os.getenv("API_TOKEN")
    
    if not auth_token:
        logger.error("No authentication token provided. Use --token argument or set API_TOKEN environment variable")
        return
    
    # Generate test variations
    netuid_range = range(args.min_netuid, args.max_netuid + 1)
    
    # Define the set of hotkeys to test
    hotkeys = [
        "5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v",  # Original test hotkey
        "5CK2ZFwG5iUaFQjC3sL2o5t4fGEPiYg8GiuYcNRzGN91gx8t",  # Random hotkey 1
        "5CXNq93RHoD8UJYsL2n4yZKLHBT6Zyf5j5W1Py8qHGcCFKqZ",  # Random hotkey 2
        "5Gv6jZ3aiRNvJ8PqKH4FHqbahGi4eYcxJzDDzLRKKcePkst3",  # Random hotkey 3
        "5CaLyzSH5xEvKV8opDJxjvUJKU6gUhy3yRbkjkgKKH5sLKVZ"   # Random hotkey 4
    ]
    
    # Additional parameters to test
    additional_params = {}
    if args.test_trade:
        additional_params["trade"] = ["true", "false"]
    
    # Generate all parameter variations
    param_variations = generate_test_variations(netuid_range, hotkeys, additional_params)
    
    # Randomize the order of variations if requested
    if args.random_order:
        random.shuffle(param_variations)
    
    logger.info(f"Generated {len(param_variations)} different parameter combinations for testing")
    
    # Create and run load tester
    tester = LoadTester(
        base_url=args.url,
        auth_token=auth_token,
        num_requests=args.requests,
        concurrency=args.concurrency,
        endpoint=args.endpoint,
        param_variations=param_variations
    )
    
    start_time = time.time()
    await tester.run()
    total_time = time.time() - start_time
    
    # Report results
    tester.report_results()
    logger.info(f"\nTotal test duration: {total_time:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main())
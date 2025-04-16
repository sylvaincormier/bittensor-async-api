#!/usr/bin/env python3
"""
Simple load test script for Bittensor async API.
This script sends concurrent requests to the API and measures performance.
"""

import asyncio
import aiohttp
import time
import statistics
import argparse
from collections import Counter


class BittensorAPILoadTest:
    def __init__(self, base_url, auth_token, num_requests=1000, concurrency=100):
        self.base_url = base_url
        self.auth_token = auth_token
        self.num_requests = num_requests
        self.concurrency = concurrency
        self.response_times = []
        self.status_counts = Counter()
        
    async def make_request(self, session, request_id):
        """Make a single request to the API and measure response time"""
        url = f"{self.base_url}/api/v1/tao_dividends?netuid=18&hotkey=5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v"
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        start_time = time.time()
        try:
            async with session.get(url, headers=headers) as response:
                await response.text()
                status = response.status
                response_time = time.time() - start_time
                self.response_times.append(response_time)
                self.status_counts[status] += 1
                
                if request_id % 10 == 0:
                    print(f"Completed request {request_id}/{self.num_requests}")
                return status, response_time
                
        except Exception as e:
            print(f"Error in request {request_id}: {str(e)}")
            self.status_counts["error"] += 1
            return "error", 0
            
    async def run_batch(self, start_id, batch_size):
        """Run a batch of requests concurrently"""
        async with aiohttp.ClientSession() as session:
            tasks = []
            for i in range(batch_size):
                request_id = start_id + i
                if request_id < self.num_requests:
                    tasks.append(self.make_request(session, request_id))
            
            # Execute requests concurrently
            await asyncio.gather(*tasks)
    
    async def run_test(self):
        """Run the full load test with the specified concurrency"""
        print(f"Starting load test with {self.num_requests} requests...")
        print(f"Concurrency level: {self.concurrency}")
        
        # Calculate number of batches
        batch_count = (self.num_requests + self.concurrency - 1) // self.concurrency
        
        for batch in range(batch_count):
            start_id = batch * self.concurrency
            remaining = min(self.concurrency, self.num_requests - start_id)
            print(f"Running batch {batch+1}/{batch_count} ({remaining} requests)")
            await self.run_batch(start_id, remaining)
    
    def print_results(self):
        """Print the test results"""
        if not self.response_times:
            print("No successful requests to analyze")
            return
            
        # Calculate statistics
        avg_time = statistics.mean(self.response_times)
        min_time = min(self.response_times)
        max_time = max(self.response_times)
        median_time = statistics.median(self.response_times)
        p95_time = sorted(self.response_times)[int(len(self.response_times) * 0.95)]
        
        # Success rate
        success_count = self.status_counts.get(200, 0)
        success_rate = (success_count / self.num_requests) * 100 if self.num_requests > 0 else 0
        
        # Print results
        print("\n===== Load Test Results =====")
        print(f"Total Requests: {self.num_requests}")
        print(f"Concurrency Level: {self.concurrency}")
        print(f"Success Rate: {success_rate:.2f}%")
        print(f"Average Response Time: {avg_time:.4f} seconds")
        print(f"Minimum Response Time: {min_time:.4f} seconds")
        print(f"Maximum Response Time: {max_time:.4f} seconds")
        print(f"Median Response Time: {median_time:.4f} seconds")
        print(f"95th Percentile Response Time: {p95_time:.4f} seconds")
        print(f"Requests per Second: {self.num_requests / sum(self.response_times):.2f}")
        
        # Print status code distribution
        print("\n===== Response Status Distribution =====")
        for status, count in sorted(self.status_counts.items()):
            percentage = (count / self.num_requests) * 100
            print(f"Status {status}: {count} requests ({percentage:.2f}%)")


async def main():
    parser = argparse.ArgumentParser(description="Load test the Bittensor Async API")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the API")
    parser.add_argument("--token", default="datura", help="Authentication token")
    parser.add_argument("--requests", type=int, default=1000, help="Number of requests to make")
    parser.add_argument("--concurrency", type=int, default=100, help="Concurrency level")
    
    args = parser.parse_args()
    
    # Run the load test
    load_tester = BittensorAPILoadTest(
        base_url=args.url,
        auth_token=args.token,
        num_requests=args.requests,
        concurrency=args.concurrency
    )
    
    # Track total time
    start_time = time.time()
    
    # Run the test
    await load_tester.run_test()
    
    # Calculate total time
    total_time = time.time() - start_time
    
    # Print results
    load_tester.print_results()
    print(f"\nTotal test duration: {total_time:.2f} seconds")


if __name__ == "__main__":
    asyncio.run(main())
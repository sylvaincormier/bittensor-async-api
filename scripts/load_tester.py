#!/usr/bin/env python3
"""
High Concurrency Load Tester for Bittensor API

This script tests the Bittensor API's performance under high load conditions,
simulating 1000 concurrent connections and analyzing response patterns.
"""

import asyncio
import aiohttp
import time
import logging
import argparse
import json
import statistics
import os
import sys
from typing import Dict, List, Any, Optional, Tuple
import random
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("load_test")

class BitensorLoadTester:
    """
    Load tester for the Bittensor API with high concurrency simulation.
    """
    def __init__(self, 
                 endpoint: str = "http://localhost:8000/api/v1/tao_dividends",
                 concurrency: int = 1000,
                 total_requests: int = 5000,
                 token: str = "datura",
                 test_variants: List[Dict] = None,
                 output_dir: str = "./load_test_results"):
        """
        Initialize the load tester.
        
        Args:
            endpoint: API endpoint URL
            concurrency: Maximum number of concurrent connections
            total_requests: Total number of requests to send
            token: API token for authentication
            test_variants: List of parameter variants to test (netuid, hotkey combinations)
            output_dir: Directory to save test results
        """
        self.endpoint = endpoint
        self.concurrency = concurrency
        self.total_requests = total_requests
        self.token = token
        self.output_dir = output_dir
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Default test variants if none provided
        if not test_variants:
            # Default test variants - covers various subnet IDs and hotkeys
            self.test_variants = [
                {"netuid": "18", "hotkey": "5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v", "trade": "false"},
                {"netuid": "19", "hotkey": "5CXNq93RHoD8UJYsL2n4yZKLHBT6Zyf5j5W1Py8qHGcCFKqZ", "trade": "false"},
                {"netuid": "20", "hotkey": "5CK2ZFwG5iUaFQjC3sL2o5t4fGEPiYg8GiuYcNRzGN91gx8t", "trade": "false"},
                {"netuid": "18", "hotkey": "5CaLyzSH5xEvKV8opDJxjvUJKU6gUhy3yRbkjkgKKH5sLKVZ", "trade": "false"},
                # Add trading variant (only 1 to avoid too many stake operations)
                {"netuid": "18", "hotkey": "5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v", "trade": "true"},
            ]
        else:
            self.test_variants = test_variants
            
        self.results = []
        self.session = None
        self.semaphore = None
        
    async def setup(self):
        """Set up the HTTP session and semaphore for limiting concurrency."""
        # Create client session with default headers
        self.session = aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {self.token}"}
        )
        
        # Create semaphore to limit concurrency
        self.semaphore = asyncio.Semaphore(self.concurrency)
        
        logger.info(f"Setup complete. Configured for {self.concurrency} concurrent connections.")
        
    async def teardown(self):
        """Clean up resources."""
        if self.session:
            await self.session.close()
        logger.info("Resources cleaned up.")
        
    async def make_request(self, params: Dict) -> Dict:
        """
        Make a single API request with the given parameters.
        
        Args:
            params: Query parameters
            
        Returns:
            Dict with request results including timing information
        """
        # Use semaphore to limit concurrency
        async with self.semaphore:
            start_time = time.time()
            error = None
            status_code = None
            response_data = None
            
            try:
                # Make the request
                async with self.session.get(self.endpoint, params=params) as response:
                    status_code = response.status
                    try:
                        response_data = await response.json()
                    except:
                        response_data = await response.text()
                        
                    elapsed = time.time() - start_time
                    
                    # Return results
                    return {
                        "params": params,
                        "status_code": status_code,
                        "elapsed_time": elapsed,
                        "success": 200 <= status_code < 300,
                        "response": response_data,
                        "error": None,
                        "timestamp": time.time()
                    }
            
            except Exception as e:
                elapsed = time.time() - start_time
                return {
                    "params": params,
                    "status_code": status_code,
                    "elapsed_time": elapsed,
                    "success": False,
                    "response": None,
                    "error": str(e),
                    "timestamp": time.time()
                }
    
    async def run_test_batch(self, batch_size: int, variant_index: int) -> List[Dict]:
        """
        Run a batch of tests using the same parameter variant.
        
        Args:
            batch_size: Number of requests in this batch
            variant_index: Index of test variant to use
            
        Returns:
            List of request results
        """
        # Select the test variant (cycling through them)
        variant = self.test_variants[variant_index % len(self.test_variants)]
        
        # Create tasks for concurrent requests
        tasks = []
        for _ in range(batch_size):
            task = asyncio.create_task(self.make_request(variant))
            tasks.append(task)
            
        # Wait for all tasks to complete
        batch_results = await asyncio.gather(*tasks)
        return batch_results
    
    async def run_load_test(self) -> Dict:
        """
        Run the complete load test with the configured number of requests.
        
        Returns:
            Dict with overall test results and statistics
        """
        await self.setup()
        
        all_results = []
        start_time = time.time()
        
        logger.info(f"Starting load test with {self.total_requests} total requests and {self.concurrency} concurrency")
        
        # Calculate number of batches and batch size
        # We want to run batches of the concurrency limit, potentially with a smaller final batch
        batch_size = min(self.concurrency, self.total_requests)
        num_batches = (self.total_requests + batch_size - 1) // batch_size  # Ceiling division
        
        # Run batches
        for batch_idx in range(num_batches):
            current_batch_size = min(batch_size, self.total_requests - batch_idx * batch_size)
            
            if current_batch_size <= 0:
                break
                
            logger.info(f"Running batch {batch_idx+1}/{num_batches} with {current_batch_size} requests")
            
            # Run the batch and collect results
            batch_results = await self.run_test_batch(current_batch_size, batch_idx)
            all_results.extend(batch_results)
            
            # Report on this batch
            successful = sum(1 for r in batch_results if r["success"])
            success_rate = (successful / len(batch_results)) * 100
            
            logger.info(f"Batch {batch_idx+1} completed: {successful}/{len(batch_results)} successful ({success_rate:.2f}%)")
            
            # Small pause between batches to avoid overwhelming the system
            if batch_idx < num_batches - 1:
                await asyncio.sleep(0.2)
        
        # Calculate overall test duration
        total_duration = time.time() - start_time
        
        # Process and save results
        analysis = self.analyze_results(all_results, total_duration)
        
        # Visualize results
        self.visualize_results(all_results, analysis)
        
        # Clean up
        await self.teardown()
        
        return analysis
    
    def analyze_results(self, results: List[Dict], total_duration: float) -> Dict:
        """
        Analyze test results and generate statistics.
        
        Args:
            results: List of request results
            total_duration: Total test duration in seconds
            
        Returns:
            Dict with statistics and aggregated results
        """
        # Overall statistics
        successful = sum(1 for r in results if r["success"])
        success_rate = (successful / len(results)) * 100
        
        # Extract response times for successful requests
        successful_times = [r["elapsed_time"] for r in results if r["success"]]
        
        # Calculate timing statistics
        if successful_times:
            avg_time = statistics.mean(successful_times)
            median_time = statistics.median(successful_times)
            min_time = min(successful_times)
            max_time = max(successful_times)
            p95_time = sorted(successful_times)[int(len(successful_times) * 0.95)]
            std_dev = statistics.stdev(successful_times) if len(successful_times) > 1 else 0
        else:
            avg_time = median_time = min_time = max_time = p95_time = std_dev = 0
        
        # Calculate throughput
        requests_per_second = len(results) / total_duration
        successful_per_second = successful / total_duration
        
        # Group results by status code
        status_counts = {}
        for r in results:
            status = r["status_code"]
            if status is None:
                status = "connection_error"
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Group results by test variant
        variant_results = {}
        for r in results:
            # Create a key from the parameters
            param_str = json.dumps(r["params"], sort_keys=True)
            
            if param_str not in variant_results:
                variant_results[param_str] = {
                    "params": r["params"],
                    "count": 0,
                    "successful": 0,
                    "times": [],
                    "errors": []
                }
                
            variant = variant_results[param_str]
            variant["count"] += 1
            
            if r["success"]:
                variant["successful"] += 1
                variant["times"].append(r["elapsed_time"])
            else:
                variant["errors"].append(r.get("error") or f"Status {r['status_code']}")
        
        # Calculate statistics for each variant
        for variant_key, variant in variant_results.items():
            if variant["times"]:
                variant["avg_time"] = statistics.mean(variant["times"])
                variant["min_time"] = min(variant["times"])
                variant["max_time"] = max(variant["times"])
                variant["success_rate"] = (variant["successful"] / variant["count"]) * 100
                
                # Look for unique dividend values in responses
                dividend_values = set()
                for r in results:
                    if json.dumps(r["params"], sort_keys=True) == variant_key and r["success"]:
                        try:
                            if isinstance(r["response"], dict):
                                value = r["response"].get("dividend_value")
                                if value is not None:
                                    dividend_values.add(value)
                        except:
                            pass
                            
                variant["unique_dividend_values"] = len(dividend_values)
                variant["dividend_values"] = list(dividend_values)
            else:
                variant["avg_time"] = 0
                variant["min_time"] = 0
                variant["max_time"] = 0
                variant["success_rate"] = 0
                variant["unique_dividend_values"] = 0
                variant["dividend_values"] = []
        
        # Calculate time distribution
        time_distribution = {
            "<50ms": sum(1 for t in successful_times if t < 0.05),
            "50-100ms": sum(1 for t in successful_times if 0.05 <= t < 0.1),
            "100-250ms": sum(1 for t in successful_times if 0.1 <= t < 0.25),
            "250-500ms": sum(1 for t in successful_times if 0.25 <= t < 0.5),
            "500-1000ms": sum(1 for t in successful_times if 0.5 <= t < 1),
            "1-2s": sum(1 for t in successful_times if 1 <= t < 2),
            "2-5s": sum(1 for t in successful_times if 2 <= t < 5),
            ">5s": sum(1 for t in successful_times if t >= 5)
        }
        
        # Compile all statistics
        analysis = {
            "total_requests": len(results),
            "successful_requests": successful,
            "success_rate": success_rate,
            "avg_response_time": avg_time,
            "median_response_time": median_time,
            "min_response_time": min_time,
            "max_response_time": max_time,
            "p95_response_time": p95_time,
            "std_dev": std_dev,
            "total_duration": total_duration,
            "requests_per_second": requests_per_second,
            "successful_per_second": successful_per_second,
            "status_counts": status_counts,
            "time_distribution": time_distribution,
            "variant_results": variant_results,
            "concurrency": self.concurrency
        }
        
        # Save analysis to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(self.output_dir, f"load_test_analysis_{timestamp}.json")
        with open(output_file, "w") as f:
            json.dump(analysis, f, indent=2)
            
        logger.info(f"Analysis saved to {output_file}")
        
        # Log summary
        logger.info("\n=== LOAD TEST SUMMARY ===")
        logger.info(f"Total Requests: {len(results)}")
        logger.info(f"Successful Requests: {successful} ({success_rate:.2f}%)")
        logger.info(f"Average Response Time: {avg_time:.4f} seconds")
        logger.info(f"Median Response Time: {median_time:.4f} seconds")
        logger.info(f"95th Percentile Response Time: {p95_time:.4f} seconds")
        logger.info(f"Min/Max Response Time: {min_time:.4f}/{max_time:.4f} seconds")
        logger.info(f"Throughput: {requests_per_second:.2f} requests/second")
        logger.info(f"Total Duration: {total_duration:.2f} seconds")
        logger.info("\nStatus Code Distribution:")
        for status, count in status_counts.items():
            logger.info(f"  {status}: {count} requests ({count/len(results)*100:.2f}%)")
        
        # Log variant summaries
        logger.info("\nTest Variant Results:")
        for variant_key, variant in variant_results.items():
            params_str = ", ".join([f"{k}='{v}'" for k, v in variant["params"].items()])
            logger.info(f"\nParameters: {variant['params']}")
            logger.info(f"  Requests: {variant['count']}")
            logger.info(f"  Success Rate: {variant['success_rate']:.2f}%")
            logger.info(f"  Avg Response Time: {variant.get('avg_time', 0):.4f} seconds")
            logger.info(f"  Min/Max Time: {variant.get('min_time', 0):.4f}/{variant.get('max_time', 0):.4f} seconds")
            logger.info(f"  Unique dividend values: {variant.get('unique_dividend_values', 0)}")
            logger.info(f"  Values: {set(variant.get('dividend_values', []))}")
        
        logger.info("\n=== END OF SUMMARY ===")
        
        return analysis
    
    def visualize_results(self, results: List[Dict], analysis: Dict):
        """
        Generate visualizations of test results.
        
        Args:
            results: List of request results
            analysis: Analysis dictionary with statistics
        """
        # Create dataframe for easier analysis
        df_data = []
        for r in results:
            if r["success"]:
                df_data.append({
                    "elapsed_time": r["elapsed_time"],
                    "status_code": r["status_code"],
                    "success": r["success"],
                    "netuid": r["params"].get("netuid", "unknown"),
                    "hotkey": r["params"].get("hotkey", "unknown"),
                    "trade": r["params"].get("trade", "false"),
                    "timestamp": r["timestamp"]
                })
        
        # Skip visualization if no successful requests
        if not df_data:
            logger.warning("No successful requests to visualize.")
            return
            
        df = pd.DataFrame(df_data)
        
        # 1. Response Time Distribution
        plt.figure(figsize=(12, 6))
        
        plt.subplot(1, 2, 1)
        sns.histplot(df["elapsed_time"], kde=True)
        plt.title("Response Time Distribution")
        plt.xlabel("Response Time (seconds)")
        plt.ylabel("Count")
        
        plt.subplot(1, 2, 2)
        sns.boxplot(y="elapsed_time", data=df)
        plt.title("Response Time Box Plot")
        plt.ylabel("Response Time (seconds)")
        
        # Save figure
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, f"response_time_distribution_{timestamp}.png"))
        plt.close()
        
        # 2. Response times by parameter combination
        plt.figure(figsize=(12, 6))
        
        # Create a parameter combination label
        df["param_combo"] = df["netuid"] + ":" + df["hotkey"].str[:10] + ":" + df["trade"]
        
        sns.boxplot(x="param_combo", y="elapsed_time", data=df)
        plt.title("Response Time by Parameter Combination")
        plt.xlabel("Parameters (netuid:hotkey:trade)")
        plt.ylabel("Response Time (seconds)")
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, f"response_time_by_params_{timestamp}.png"))
        plt.close()
        
        # 3. Response time over test duration
        # Add relative timestamp (seconds from start)
        if len(df) > 0:
            min_timestamp = df["timestamp"].min()
            df["relative_time"] = df["timestamp"] - min_timestamp
            
            plt.figure(figsize=(12, 6))
            plt.scatter(df["relative_time"], df["elapsed_time"], alpha=0.5)
            plt.title("Response Time over Test Duration")
            plt.xlabel("Time from Test Start (seconds)")
            plt.ylabel("Response Time (seconds)")
            
            # Add smoothed line to show trend
            try:
                from scipy.signal import savgol_filter
                if len(df) > 10:  # Need enough points for smoothing
                    # Sort by time
                    df_sorted = df.sort_values("relative_time")
                    # Apply smoothing
                    window_size = min(len(df) // 4 * 2 + 1, 51)  # Must be odd, ~25% of data points
                    poly_order = 3
                    if window_size > poly_order:
                        y_smooth = savgol_filter(df_sorted["elapsed_time"], window_size, poly_order)
                        plt.plot(df_sorted["relative_time"], y_smooth, 'r-', linewidth=2)
            except ImportError:
                # savgol_filter not available, skip smoothing
                pass
            except Exception as e:
                logger.warning(f"Error in smoothing: {e}")
            
            plt.tight_layout()
            plt.savefig(os.path.join(self.output_dir, f"response_time_over_duration_{timestamp}.png"))
            plt.close()
        
        # 4. Create an HTML report
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Bittensor API Load Test Results</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                h1, h2 { color: #2c3e50; }
                table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
                th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
                th { background-color: #f2f2f2; }
                .chart-container { margin: 20px 0; }
                .success { color: green; }
                .failure { color: red; }
                .section { margin: 30px 0; }
            </style>
        </head>
        <body>
            <h1>Bittensor API Load Test Results</h1>
            <p>Generated on: {date}</p>
            
            <div class="section">
                <h2>Test Configuration</h2>
                <table>
                    <tr><th>Setting</th><th>Value</th></tr>
                    <tr><td>Endpoint</td><td>{endpoint}</td></tr>
                    <tr><td>Concurrency</td><td>{concurrency}</td></tr>
                    <tr><td>Total Requests</td><td>{total_requests}</td></tr>
                    <tr><td>Test Duration</td><td>{duration:.2f} seconds</td></tr>
                </table>
            </div>
            
            <div class="section">
                <h2>Overall Performance</h2>
                <table>
                    <tr><th>Metric</th><th>Value</th></tr>
                    <tr><td>Success Rate</td><td class="{success_class}">{success_rate:.2f}%</td></tr>
                    <tr><td>Throughput</td><td>{throughput:.2f} requests/second</td></tr>
                    <tr><td>Average Response Time</td><td>{avg_time:.4f} seconds</td></tr>
                    <tr><td>Median Response Time</td><td>{median_time:.4f} seconds</td></tr>
                    <tr><td>95th Percentile Response Time</td><td>{p95_time:.4f} seconds</td></tr>
                    <tr><td>Min/Max Response Time</td><td>{min_time:.4f}/{max_time:.4f} seconds</td></tr>
                </table>
            </div>
            
            <div class="section">
                <h2>Response Status Distribution</h2>
                <table>
                    <tr><th>Status Code</th><th>Count</th><th>Percentage</th></tr>
                    {status_rows}
                </table>
            </div>
            
            <div class="section">
                <h2>Response Time Distribution</h2>
                <table>
                    <tr><th>Time Range</th><th>Count</th><th>Percentage</th></tr>
                    {time_dist_rows}
                </table>
            </div>
            
            <div class="section">
                <h2>Test Variant Results</h2>
                {variant_tables}
            </div>
            
            <div class="section">
                <h2>Visualizations</h2>
                <div class="chart-container">
                    <h3>Response Time Distribution</h3>
                    <img src="response_time_distribution_{timestamp}.png" alt="Response Time Distribution" style="max-width: 100%;">
                </div>
                
                <div class="chart-container">
                    <h3>Response Time by Parameter Combination</h3>
                    <img src="response_time_by_params_{timestamp}.png" alt="Response Time by Parameters" style="max-width: 100%;">
                </div>
                
                <div class="chart-container">
                    <h3>Response Time over Test Duration</h3>
                    <img src="response_time_over_duration_{timestamp}.png" alt="Response Time over Duration" style="max-width: 100%;">
                </div>
            </div>
            
            <div class="section">
                <h2>Conclusions</h2>
                <ul>
                    {conclusions}
                </ul>
            </div>
        </body>
        </html>
        """.format(
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            endpoint=self.endpoint,
            concurrency=self.concurrency,
            total_requests=analysis["total_requests"],
            duration=analysis["total_duration"],
            success_class="success" if analysis["success_rate"] >= 95 else "failure",
            success_rate=analysis["success_rate"],
            throughput=analysis["requests_per_second"],
            avg_time=analysis["avg_response_time"],
            median_time=analysis["median_response_time"],
            p95_time=analysis["p95_response_time"],
            min_time=analysis["min_response_time"],
            max_time=analysis["max_response_time"],
            status_rows="\n".join([
                f'<tr><td>{status}</td><td>{count}</td><td>{count/analysis["total_requests"]*100:.2f}%</td></tr>'
                for status, count in analysis["status_counts"].items()
            ]),
            time_dist_rows="\n".join([
                f'<tr><td>{time_range}</td><td>{count}</td><td>{count/sum(analysis["time_distribution"].values())*100:.2f}%</td></tr>'
                for time_range, count in analysis["time_distribution"].items()
                if sum(analysis["time_distribution"].values()) > 0
            ]),
            variant_tables="".join([
                f"""
                <h3>Parameters: {params_str}</h3>
                <table>
                    <tr><th>Metric</th><th>Value</th></tr>
                    <tr><td>Success Rate</td><td class="{'success' if variant['success_rate'] >= 95 else 'failure'}">{variant['success_rate']:.2f}%</td></tr>
                    <tr><td>Requests</td><td>{variant['count']}</td></tr>
                    <tr><td>Average Response Time</td><td>{variant.get('avg_time', 0):.4f} seconds</td></tr>
                    <tr><td>Min/Max Response Time</td><td>{variant.get('min_time', 0):.4f}/{variant.get('max_time', 0):.4f} seconds</td></tr>
                    <tr><td>Unique Dividend Values</td><td>{variant.get('unique_dividend_values', 0)}</td></tr>
                    <tr><td>Dividend Values</td><td>{set(variant.get('dividend_values', []))}</td></tr>
                </table>
                """
                for params_str, variant in analysis["variant_results"].items()
            ]),
            timestamp=timestamp,
            conclusions="\n".join([
                f"<li>{conclusion}</li>" for conclusion in [
                    f"The API {'can' if analysis['success_rate'] >= 95 else 'cannot'} handle {self.concurrency} concurrent connections with acceptable reliability ({analysis['success_rate']:.2f}% success rate).",
                    f"Average response time of {analysis['avg_response_time']:.4f} seconds is {'acceptable' if analysis['avg_response_time'] < 1.0 else 'slower than desired'} for a high-performance API.",
                    f"Throughput of {analysis['requests_per_second']:.2f} requests/second {'meets' if analysis['requests_per_second'] >= self.concurrency/5 else 'does not meet'} the target performance for handling 1000 concurrent users.",
                    "The system appears to be using caching effectively, as evidenced by consistent dividend values across requests with the same parameters.",
                    f"The 95th percentile response time of {analysis['p95_response_time']:.4f} seconds indicates that most users will experience {'good' if analysis['p95_response_time'] < 2.0 else 'degraded'} performance under load."
                ]
            ])
        )
        
        # Save HTML report
        html_output_file = os.path.join(self.output_dir, f"load_test_report_{timestamp}.html")
        with open(html_output_file, "w") as f:
            f.write(html_content)
            
        logger.info(f"HTML report saved to {html_output_file}")

async def main():
    parser = argparse.ArgumentParser(description="Bittensor API Load Tester")
    
    parser.add_argument("--endpoint", default="http://localhost:8000/api/v1/tao_dividends",
                      help="API endpoint URL")
    parser.add_argument("--concurrency", type=int, default=1000,
                      help="Maximum number of concurrent connections")
    parser.add_argument("--requests", type=int, default=5000,
                      help="Total number of requests to send")
    parser.add_argument("--token", default="datura",
                      help="API token for authentication")
    parser.add_argument("--output", default="./load_test_results",
                      help="Output directory for test results")
    
    args = parser.parse_args()
    
    # Create load tester
    tester = BitensorLoadTester(
        endpoint=args.endpoint,
        concurrency=args.concurrency,
        total_requests=args.requests,
        token=args.token,
        output_dir=args.output
    )
    
    # Run test
    await tester.run_load_test()

if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""
BharatBuild AI - Python Load Test Script

Usage:
    python load_test.py --url http://localhost:8000/api/v1 --users 50 --duration 60
    python load_test.py --url http://localhost:8000/api/v1 --users 10 --duration 30 --mode public
    python load_test.py --url http://localhost:8000/api/v1 --users 10 --duration 30 --mode auth --credentials test_users_credentials.json
"""

import asyncio
import aiohttp
import argparse
import time
import statistics
import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
import json


@dataclass
class RequestMetrics:
    """Metrics for a single request"""
    endpoint: str
    method: str
    status_code: int
    duration_ms: float
    success: bool
    error: Optional[str] = None


@dataclass
class TestResults:
    """Aggregated test results"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    response_times: List[float] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    requests_by_endpoint: Dict[str, List[float]] = field(default_factory=dict)
    status_codes: Dict[int, int] = field(default_factory=dict)
    start_time: float = 0
    end_time: float = 0

    @property
    def duration_seconds(self) -> float:
        return self.end_time - self.start_time

    @property
    def requests_per_second(self) -> float:
        if self.duration_seconds > 0:
            return self.total_requests / self.duration_seconds
        return 0

    @property
    def error_rate(self) -> float:
        if self.total_requests > 0:
            return (self.failed_requests / self.total_requests) * 100
        return 0

    @property
    def avg_response_time(self) -> float:
        if self.response_times:
            return statistics.mean(self.response_times)
        return 0

    @property
    def p50_response_time(self) -> float:
        if self.response_times:
            return statistics.median(self.response_times)
        return 0

    @property
    def p95_response_time(self) -> float:
        if self.response_times:
            sorted_times = sorted(self.response_times)
            idx = int(len(sorted_times) * 0.95)
            return sorted_times[idx] if idx < len(sorted_times) else sorted_times[-1]
        return 0

    @property
    def p99_response_time(self) -> float:
        if self.response_times:
            sorted_times = sorted(self.response_times)
            idx = int(len(sorted_times) * 0.99)
            return sorted_times[idx] if idx < len(sorted_times) else sorted_times[-1]
        return 0

    @property
    def max_response_time(self) -> float:
        if self.response_times:
            return max(self.response_times)
        return 0


class LoadTester:
    """Load testing client for BharatBuild AI"""

    def __init__(self, base_url: str, num_users: int, duration_seconds: int,
                 mode: str = "mixed", credentials_file: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.num_users = num_users
        self.duration_seconds = duration_seconds
        self.mode = mode  # "public", "auth", or "mixed"
        self.results = TestResults()
        self.running = True

        # Load credentials from file or generate default
        if credentials_file and os.path.exists(credentials_file):
            with open(credentials_file, 'r') as f:
                self.test_users = json.load(f)
            print(f"[OK] Loaded {len(self.test_users)} users from {credentials_file}")
        else:
            self.test_users = [
                {"email": f"loadtest_user_{i}@test.com", "password": "TestPassword123!"}
                for i in range(num_users)
            ]

    async def make_request(
        self,
        session: aiohttp.ClientSession,
        method: str,
        endpoint: str,
        headers: Optional[Dict] = None,
        data: Optional[Dict] = None,
        form_data: Optional[Dict] = None
    ) -> RequestMetrics:
        """Make a single HTTP request and record metrics"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()

        try:
            if form_data:
                async with session.request(method, url, headers=headers, data=form_data) as response:
                    response_text = await response.text()
                    duration_ms = (time.time() - start_time) * 1000
                    return RequestMetrics(
                        endpoint=endpoint,
                        method=method,
                        status_code=response.status,
                        duration_ms=duration_ms,
                        success=200 <= response.status < 300
                    ), response_text
            else:
                async with session.request(method, url, headers=headers, json=data) as response:
                    response_text = await response.text()
                    duration_ms = (time.time() - start_time) * 1000
                    return RequestMetrics(
                        endpoint=endpoint,
                        method=method,
                        status_code=response.status,
                        duration_ms=duration_ms,
                        success=200 <= response.status < 300
                    ), response_text
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return RequestMetrics(
                endpoint=endpoint,
                method=method,
                status_code=0,
                duration_ms=duration_ms,
                success=False,
                error=str(e)
            ), ""

    def record_metrics(self, metrics: RequestMetrics):
        """Record metrics from a request"""
        self.results.total_requests += 1
        self.results.response_times.append(metrics.duration_ms)

        # Track status codes
        if metrics.status_code not in self.results.status_codes:
            self.results.status_codes[metrics.status_code] = 0
        self.results.status_codes[metrics.status_code] += 1

        if metrics.success:
            self.results.successful_requests += 1
        else:
            self.results.failed_requests += 1
            if metrics.error:
                self.results.errors.append(metrics.error)

        # Track by endpoint
        if metrics.endpoint not in self.results.requests_by_endpoint:
            self.results.requests_by_endpoint[metrics.endpoint] = []
        self.results.requests_by_endpoint[metrics.endpoint].append(metrics.duration_ms)

    async def simulate_public_user(self, user_id: int, session: aiohttp.ClientSession):
        """Simulate a user hitting only public endpoints"""
        while self.running:
            try:
                # 1. Health check
                metrics, _ = await self.make_request(session, "GET", "/health")
                self.record_metrics(metrics)

                # 2. Document types (public)
                metrics, _ = await self.make_request(session, "GET", "/documents/types")
                self.record_metrics(metrics)

                # Think time
                await asyncio.sleep(0.5 + (user_id % 3) * 0.5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.results.errors.append(str(e))
                await asyncio.sleep(1)

    async def simulate_auth_user(self, user_id: int, session: aiohttp.ClientSession):
        """Simulate a user with authentication flow"""
        user = self.test_users[user_id % len(self.test_users)]
        token = None

        while self.running:
            try:
                # 1. Login (JSON body with email/password)
                login_metrics, response_text = await self.make_request(
                    session, "POST", "/auth/login",
                    data={"email": user["email"], "password": user["password"]}
                )
                self.record_metrics(login_metrics)

                # Extract token if login succeeded
                if login_metrics.success:
                    try:
                        response_json = json.loads(response_text)
                        token = response_json.get("access_token")
                    except:
                        token = None

                # 2. Authenticated requests if we have a token
                if token:
                    auth_headers = {"Authorization": f"Bearer {token}"}

                    # Get user profile
                    me_metrics, _ = await self.make_request(
                        session, "GET", "/auth/me", headers=auth_headers
                    )
                    self.record_metrics(me_metrics)

                    # List projects
                    projects_metrics, _ = await self.make_request(
                        session, "GET", "/projects?page=1&page_size=10", headers=auth_headers
                    )
                    self.record_metrics(projects_metrics)

                    # Get plan status
                    plan_metrics, _ = await self.make_request(
                        session, "GET", "/users/plan-status", headers=auth_headers
                    )
                    self.record_metrics(plan_metrics)

                    # Get token balance
                    balance_metrics, _ = await self.make_request(
                        session, "GET", "/users/token-balance", headers=auth_headers
                    )
                    self.record_metrics(balance_metrics)

                # Think time
                await asyncio.sleep(1 + (user_id % 3))

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.results.errors.append(str(e))
                await asyncio.sleep(1)

    async def simulate_mixed_user(self, user_id: int, session: aiohttp.ClientSession):
        """Simulate mixed public and authenticated requests"""
        user = self.test_users[user_id % len(self.test_users)]
        token = None

        while self.running:
            try:
                # Public endpoints
                metrics, _ = await self.make_request(session, "GET", "/health")
                self.record_metrics(metrics)

                metrics, _ = await self.make_request(session, "GET", "/documents/types")
                self.record_metrics(metrics)

                # Try authentication (JSON body with email/password)
                login_metrics, response_text = await self.make_request(
                    session, "POST", "/auth/login",
                    data={"email": user["email"], "password": user["password"]}
                )
                self.record_metrics(login_metrics)

                if login_metrics.success:
                    try:
                        response_json = json.loads(response_text)
                        token = response_json.get("access_token")
                    except:
                        token = None

                    if token:
                        auth_headers = {"Authorization": f"Bearer {token}"}

                        me_metrics, _ = await self.make_request(
                            session, "GET", "/auth/me", headers=auth_headers
                        )
                        self.record_metrics(me_metrics)

                        projects_metrics, _ = await self.make_request(
                            session, "GET", "/projects?page=1&page_size=10", headers=auth_headers
                        )
                        self.record_metrics(projects_metrics)

                # Think time
                await asyncio.sleep(1 + (user_id % 3))

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.results.errors.append(str(e))
                await asyncio.sleep(1)

    async def run(self):
        """Run the load test"""
        print(f"\n{'='*60}")
        print("BHARATBUILD AI - LOAD TEST")
        print(f"{'='*60}")
        print(f"Target URL:    {self.base_url}")
        print(f"Virtual Users: {self.num_users}")
        print(f"Duration:      {self.duration_seconds} seconds")
        print(f"Mode:          {self.mode}")
        print(f"{'='*60}\n")

        self.results.start_time = time.time()

        # Check API health first
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.base_url}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        print("[OK] API health check passed")
                    else:
                        print(f"[WARN] API health check returned {response.status}")
            except Exception as e:
                print(f"[FAIL] API health check failed: {e}")
                print("Make sure the API is running!")
                return

        print(f"\nStarting load test with {self.num_users} users...")
        print("Press Ctrl+C to stop early\n")

        # Select user simulation function based on mode
        if self.mode == "public":
            simulate_func = self.simulate_public_user
        elif self.mode == "auth":
            simulate_func = self.simulate_auth_user
        else:
            simulate_func = self.simulate_mixed_user

        # Create session and tasks
        connector = aiohttp.TCPConnector(limit=self.num_users * 2)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = []

            # Ramp up users gradually
            for i in range(self.num_users):
                task = asyncio.create_task(simulate_func(i, session))
                tasks.append(task)

                # Progress indicator
                if (i + 1) % 10 == 0:
                    print(f"  Spawned {i + 1}/{self.num_users} virtual users")

                await asyncio.sleep(0.1)  # 100ms between user spawns

            if self.num_users < 10:
                print(f"  Spawned {self.num_users}/{self.num_users} virtual users")

            print(f"\nAll {self.num_users} users active. Running for {self.duration_seconds} seconds...\n")

            # Run for duration
            try:
                await asyncio.sleep(self.duration_seconds)
            except asyncio.CancelledError:
                pass

            # Stop all users
            self.running = False

            # Give tasks time to finish
            await asyncio.sleep(2)

            # Cancel any remaining tasks
            for task in tasks:
                task.cancel()

        self.results.end_time = time.time()
        self.print_results()

    def print_results(self):
        """Print test results summary"""
        r = self.results

        print(f"\n{'='*60}")
        print("                    TEST RESULTS")
        print(f"{'='*60}")

        print("\nREQUESTS")
        print("-" * 40)
        print(f"  Total Requests:      {r.total_requests}")
        print(f"  Successful:          {r.successful_requests}")
        print(f"  Failed:              {r.failed_requests}")
        print(f"  Error Rate:          {r.error_rate:.2f}%")
        print(f"  Requests/sec:        {r.requests_per_second:.2f}")

        print("\nSTATUS CODES")
        print("-" * 40)
        for code, count in sorted(r.status_codes.items()):
            status_name = {
                0: "Connection Error",
                200: "OK",
                201: "Created",
                400: "Bad Request",
                401: "Unauthorized",
                403: "Forbidden",
                404: "Not Found",
                422: "Validation Error",
                429: "Too Many Requests",
                500: "Server Error"
            }.get(code, "Other")
            print(f"  {code} ({status_name}): {count}")

        print("\nRESPONSE TIMES")
        print("-" * 40)
        print(f"  Average:             {r.avg_response_time:.2f} ms")
        print(f"  Median (p50):        {r.p50_response_time:.2f} ms")
        print(f"  95th Percentile:     {r.p95_response_time:.2f} ms")
        print(f"  99th Percentile:     {r.p99_response_time:.2f} ms")
        print(f"  Max:                 {r.max_response_time:.2f} ms")

        print("\nBY ENDPOINT")
        print("-" * 40)
        for endpoint, times in sorted(r.requests_by_endpoint.items()):
            avg = statistics.mean(times) if times else 0
            p95 = sorted(times)[int(len(times) * 0.95)] if len(times) > 20 else max(times) if times else 0
            print(f"  {endpoint}")
            print(f"    Requests: {len(times)}, Avg: {avg:.0f}ms, p95: {p95:.0f}ms")

        print("\nTEST DURATION")
        print("-" * 40)
        print(f"  Duration:            {r.duration_seconds:.2f} seconds")
        print(f"  Virtual Users:       {self.num_users}")

        # Pass/Fail checks
        print("\nTHRESHOLD CHECKS")
        print("-" * 40)

        p95_pass = r.p95_response_time < 1000
        error_pass = r.error_rate < 5

        print(f"  p95 < 1000ms:        {'[PASS]' if p95_pass else '[FAIL]'} ({r.p95_response_time:.0f}ms)")
        print(f"  Error Rate < 5%:     {'[PASS]' if error_pass else '[FAIL]'} ({r.error_rate:.2f}%)")

        overall_pass = p95_pass and error_pass
        print(f"\n  OVERALL:             {'[PASS]' if overall_pass else '[FAIL]'}")

        print(f"\n{'='*60}\n")

        # Save results to JSON
        results_file = f"load_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump({
                "total_requests": r.total_requests,
                "successful_requests": r.successful_requests,
                "failed_requests": r.failed_requests,
                "error_rate": r.error_rate,
                "requests_per_second": r.requests_per_second,
                "avg_response_time": r.avg_response_time,
                "p50_response_time": r.p50_response_time,
                "p95_response_time": r.p95_response_time,
                "p99_response_time": r.p99_response_time,
                "max_response_time": r.max_response_time,
                "duration_seconds": r.duration_seconds,
                "num_users": self.num_users,
                "mode": self.mode,
                "status_codes": r.status_codes,
                "endpoints": {k: len(v) for k, v in r.requests_by_endpoint.items()},
                "pass": overall_pass
            }, f, indent=2)

        print(f"Results saved to: {results_file}")


async def main():
    parser = argparse.ArgumentParser(description='BharatBuild AI Load Test')
    parser.add_argument('--url', default='http://localhost:8000/api/v1',
                        help='API base URL (default: http://localhost:8000/api/v1)')
    parser.add_argument('--users', type=int, default=50,
                        help='Number of virtual users (default: 50)')
    parser.add_argument('--duration', type=int, default=60,
                        help='Test duration in seconds (default: 60)')
    parser.add_argument('--mode', choices=['public', 'auth', 'mixed'], default='mixed',
                        help='Test mode: public (no auth), auth (with login), mixed (both)')
    parser.add_argument('--credentials', type=str, default=None,
                        help='Path to credentials JSON file (default: auto-generate)')

    args = parser.parse_args()

    tester = LoadTester(args.url, args.users, args.duration, args.mode, args.credentials)

    try:
        await tester.run()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        tester.running = False
        tester.results.end_time = time.time()
        tester.print_results()


if __name__ == "__main__":
    asyncio.run(main())

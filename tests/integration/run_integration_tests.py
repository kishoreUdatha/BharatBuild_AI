#!/usr/bin/env python3
"""
BharatBuild AI - Integration Test Runner
Runs all integration tests and generates a report.

Usage:
    python run_integration_tests.py
    python run_integration_tests.py --url http://localhost:8000/api/v1
    python run_integration_tests.py --quick  # Run quick tests only
"""
import asyncio
import argparse
import sys
import time
from datetime import datetime
from typing import List, Dict, Tuple
import json

# Add current directory to path
sys.path.insert(0, '.')

from api_client import BharatBuildAPIClient
from config import config


class IntegrationTestRunner:
    """Run integration tests and collect results"""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or config.api_base_url
        self.results: List[Dict] = []
        self.start_time = None
        self.end_time = None

    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    async def run_test(self, name: str, test_func) -> Dict:
        """Run a single test and return result"""
        start = time.time()
        result = {
            "name": name,
            "status": "UNKNOWN",
            "duration_ms": 0,
            "error": None
        }

        try:
            await test_func()
            result["status"] = "PASS"
        except AssertionError as e:
            result["status"] = "FAIL"
            result["error"] = str(e)
        except Exception as e:
            result["status"] = "ERROR"
            result["error"] = str(e)

        result["duration_ms"] = (time.time() - start) * 1000
        return result

    async def test_health_check(self):
        """Test API health"""
        async with BharatBuildAPIClient(self.base_url) as client:
            response = await client.health_check()
            assert response.success, f"Health check failed: {response.data}"
            assert response.data.get("status") == "healthy"

    async def test_document_types(self):
        """Test document types endpoint"""
        async with BharatBuildAPIClient(self.base_url) as client:
            response = await client.get_document_types()
            assert response.success, f"Get doc types failed: {response.data}"
            # Response can be list or {"document_types": [...]}
            data = response.data
            if isinstance(data, dict):
                data = data.get("document_types", [])
            assert isinstance(data, list)
            assert len(data) > 0

    async def test_registration(self):
        """Test user registration"""
        import uuid
        email = f"test_{uuid.uuid4().hex[:8]}@test.com"

        async with BharatBuildAPIClient(self.base_url) as client:
            response = await client.register(
                email=email,
                password="TestPassword123!",
                full_name="Test User"
            )
            # May fail due to rate limiting - check for valid responses
            assert response.status in [200, 201, 429], f"Unexpected status: {response.status}"

    async def test_login_invalid(self):
        """Test login with invalid credentials"""
        async with BharatBuildAPIClient(self.base_url) as client:
            response = await client.login("invalid@test.com", "WrongPassword123!")
            assert response.status == 401, f"Expected 401, got {response.status}"

    async def test_authenticated_endpoints(self):
        """Test authenticated endpoints"""
        import uuid
        email = f"auth_test_{uuid.uuid4().hex[:8]}@test.com"
        password = "TestPassword123!"

        async with BharatBuildAPIClient(self.base_url) as client:
            # Register
            reg = await client.register(email=email, password=password, full_name="Auth Test")
            if reg.status == 429:
                return  # Skip if rate limited

            # Login
            login = await client.login(email, password)
            assert login.success, f"Login failed: {login.data}"

            # Get profile
            profile = await client.get_current_user()
            assert profile.success, f"Get profile failed: {profile.data}"

            # Get plan status (may return error for new users - just check it responds)
            plan = await client.get_plan_status()
            # Accept 200 or 4xx as valid responses
            assert plan.status in [200, 400, 404, 422], f"Unexpected plan status: {plan.status}"

            # List projects
            projects = await client.list_projects()
            assert projects.success, f"List projects failed: {projects.data}"

    async def test_unauthenticated_rejection(self):
        """Test that protected endpoints reject unauthenticated requests"""
        async with BharatBuildAPIClient(self.base_url) as client:
            # Don't login, try protected endpoint
            response = await client.get_current_user()
            assert response.status in [401, 403], f"Expected 401/403, got {response.status}"

    async def test_concurrent_requests(self):
        """Test concurrent request handling"""
        async def make_request():
            async with BharatBuildAPIClient(self.base_url) as client:
                return await client.health_check()

        tasks = [make_request() for _ in range(20)]
        results = await asyncio.gather(*tasks)
        success_count = sum(1 for r in results if r.success)
        assert success_count >= 15, f"Only {success_count}/20 succeeded"

    async def run_all_tests(self, quick: bool = False) -> Tuple[int, int, int]:
        """Run all tests and return (passed, failed, errors)"""
        self.start_time = time.time()

        tests = [
            ("API Health Check", self.test_health_check),
            ("Document Types Endpoint", self.test_document_types),
            ("User Registration", self.test_registration),
            ("Invalid Login Rejection", self.test_login_invalid),
            ("Unauthenticated Rejection", self.test_unauthenticated_rejection),
        ]

        if not quick:
            tests.extend([
                ("Authenticated Endpoints", self.test_authenticated_endpoints),
                ("Concurrent Requests", self.test_concurrent_requests),
            ])

        print(f"\n{'='*70}")
        print(f"BHARATBUILD AI - INTEGRATION TEST SUITE")
        print(f"{'='*70}")
        print(f"Target: {self.base_url}")
        print(f"Tests:  {len(tests)}")
        print(f"Mode:   {'Quick' if quick else 'Full'}")
        print(f"{'='*70}\n")

        for name, test_func in tests:
            self.log(f"Running: {name}...")
            result = await self.run_test(name, test_func)
            self.results.append(result)

            status_icon = {"PASS": "[OK]", "FAIL": "[FAIL]", "ERROR": "[ERR]"}.get(result["status"], "[?]")
            duration = f"{result['duration_ms']:.0f}ms"

            if result["status"] == "PASS":
                print(f"  {status_icon} {name} ({duration})")
            else:
                print(f"  {status_icon} {name} ({duration})")
                if result["error"]:
                    print(f"       Error: {result['error'][:100]}")

        self.end_time = time.time()

        # Calculate results
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        errors = sum(1 for r in self.results if r["status"] == "ERROR")

        return passed, failed, errors

    def print_summary(self, passed: int, failed: int, errors: int):
        """Print test summary"""
        total = passed + failed + errors
        duration = self.end_time - self.start_time

        print(f"\n{'='*70}")
        print(f"TEST SUMMARY")
        print(f"{'='*70}")
        print(f"  Total:    {total}")
        print(f"  Passed:   {passed}")
        print(f"  Failed:   {failed}")
        print(f"  Errors:   {errors}")
        print(f"  Duration: {duration:.2f}s")
        print(f"{'='*70}")

        if failed == 0 and errors == 0:
            print(f"\n[PASS] All tests passed!")
        else:
            print(f"\n[FAIL] Some tests failed")

        print(f"{'='*70}\n")

    def save_results(self, filename: str = None):
        """Save results to JSON file"""
        if not filename:
            filename = f"integration_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        report = {
            "timestamp": datetime.now().isoformat(),
            "base_url": self.base_url,
            "duration_seconds": self.end_time - self.start_time if self.end_time else 0,
            "summary": {
                "total": len(self.results),
                "passed": sum(1 for r in self.results if r["status"] == "PASS"),
                "failed": sum(1 for r in self.results if r["status"] == "FAIL"),
                "errors": sum(1 for r in self.results if r["status"] == "ERROR")
            },
            "tests": self.results
        }

        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"Results saved to: {filename}")
        return filename


async def main():
    parser = argparse.ArgumentParser(description='BharatBuild AI Integration Tests')
    parser.add_argument('--url', default='http://localhost:8000/api/v1',
                        help='API base URL')
    parser.add_argument('--quick', action='store_true',
                        help='Run quick tests only')
    parser.add_argument('--save', action='store_true',
                        help='Save results to JSON file')

    args = parser.parse_args()

    runner = IntegrationTestRunner(args.url)

    try:
        passed, failed, errors = await runner.run_all_tests(quick=args.quick)
        runner.print_summary(passed, failed, errors)

        if args.save:
            runner.save_results()

        # Exit with error code if tests failed
        sys.exit(0 if (failed == 0 and errors == 0) else 1)

    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTest runner error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

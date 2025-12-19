#!/usr/bin/env python3
"""
BharatBuild AI - Test Users Setup Script

Creates test users for load testing via API registration endpoint.

Usage:
    python setup_test_users.py --url http://localhost:8000/api/v1 --count 10
"""

import asyncio
import aiohttp
import argparse
import json
from typing import List, Dict


async def create_user(
    session: aiohttp.ClientSession,
    base_url: str,
    user_data: Dict
) -> Dict:
    """Create a single test user via registration API"""
    url = f"{base_url}/auth/register"

    try:
        async with session.post(url, json=user_data) as response:
            result = await response.json()
            return {
                "email": user_data["email"],
                "status": response.status,
                "success": response.status in [200, 201],
                "message": result.get("detail", result.get("message", "OK"))
            }
    except Exception as e:
        return {
            "email": user_data["email"],
            "status": 0,
            "success": False,
            "message": str(e)
        }


async def setup_test_users(base_url: str, count: int, password: str) -> List[Dict]:
    """Create multiple test users"""
    print(f"\n{'='*60}")
    print("BHARATBUILD AI - TEST USER SETUP")
    print(f"{'='*60}")
    print(f"API URL:     {base_url}")
    print(f"User Count:  {count}")
    print(f"Password:    {password}")
    print(f"{'='*60}\n")

    # Health check first
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{base_url}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    print("[OK] API health check passed\n")
                else:
                    print(f"[WARN] API health check returned {response.status}\n")
        except Exception as e:
            print(f"[FAIL] API health check failed: {e}")
            print("Make sure the API is running!")
            return []

    # Create users
    results = []
    created = 0
    existing = 0
    failed = 0

    async with aiohttp.ClientSession() as session:
        for i in range(count):
            user_data = {
                "email": f"loadtest_user_{i}@test.com",
                "password": password,
                "full_name": f"Load Test User {i}",
                "role": "student",
                # Required student fields
                "roll_number": f"LT{i:04d}",
                "college_name": "Load Test College",
                "university_name": "Load Test University",
                "department": "Computer Science",
                "course": "B.Tech",
                "year_semester": "4th Year",
                "batch": "2021-2025",
                "guide_name": "Dr. Load Test",
                "guide_designation": "Professor",
                "hod_name": "Dr. HOD Test"
            }

            result = await create_user(session, base_url, user_data)
            results.append(result)

            if result["success"]:
                created += 1
                print(f"  [+] Created: {result['email']}")
            elif "already" in result["message"].lower() or result["status"] == 400:
                existing += 1
                print(f"  [=] Exists:  {result['email']}")
            else:
                failed += 1
                print(f"  [-] Failed:  {result['email']} - {result['message']}")

            # Small delay to not overwhelm the API
            await asyncio.sleep(0.1)

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"  Total:    {count}")
    print(f"  Created:  {created}")
    print(f"  Existing: {existing}")
    print(f"  Failed:   {failed}")
    print(f"{'='*60}\n")

    # Save credentials to file
    credentials_file = "test_users_credentials.json"
    credentials = [
        {"email": f"loadtest_user_{i}@test.com", "password": password}
        for i in range(count)
    ]
    with open(credentials_file, 'w') as f:
        json.dump(credentials, f, indent=2)

    print(f"Credentials saved to: {credentials_file}")
    print(f"\nYou can now run the load test with these users!")
    print(f"  py load_test.py --url {base_url} --users {min(count, 50)} --duration 30\n")

    return results


async def main():
    parser = argparse.ArgumentParser(description='BharatBuild AI - Test User Setup')
    parser.add_argument('--url', default='http://localhost:8000/api/v1',
                        help='API base URL (default: http://localhost:8000/api/v1)')
    parser.add_argument('--count', type=int, default=10,
                        help='Number of test users to create (default: 10)')
    parser.add_argument('--password', default='TestPassword123!',
                        help='Password for test users (default: TestPassword123!)')

    args = parser.parse_args()

    await setup_test_users(args.url, args.count, args.password)


if __name__ == "__main__":
    asyncio.run(main())

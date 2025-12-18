#!/usr/bin/env python3
"""
BharatBuild AI - Stress Test Script
Find the breaking point of the system.

Usage:
    python stress_test.py --url http://localhost:8000/api/v1
"""

import asyncio
import aiohttp
import argparse
import time
from datetime import datetime


async def make_request(session: aiohttp.ClientSession, url: str) -> tuple:
    """Make a single request and return (success, duration_ms, status)"""
    start = time.time()
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            await response.text()
            duration = (time.time() - start) * 1000
            return (response.status == 200, duration, response.status)
    except Exception as e:
        duration = (time.time() - start) * 1000
        return (False, duration, 0)


async def run_stress_level(base_url: str, num_users: int, duration_secs: int = 10) -> dict:
    """Run stress test at a specific user level"""
    url = f"{base_url}/health"
    results = {"success": 0, "failed": 0, "times": [], "errors": {}}
    running = True

    async def user_loop(session):
        nonlocal results
        while running:
            success, duration, status = await make_request(session, url)
            results["times"].append(duration)
            if success:
                results["success"] += 1
            else:
                results["failed"] += 1
                if status not in results["errors"]:
                    results["errors"][status] = 0
                results["errors"][status] += 1
            await asyncio.sleep(0.1)  # 100ms between requests per user

    connector = aiohttp.TCPConnector(limit=num_users * 2, limit_per_host=num_users * 2)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [asyncio.create_task(user_loop(session)) for _ in range(num_users)]
        await asyncio.sleep(duration_secs)
        running = False
        await asyncio.sleep(1)
        for task in tasks:
            task.cancel()

    # Calculate stats
    total = results["success"] + results["failed"]
    if results["times"]:
        sorted_times = sorted(results["times"])
        p95_idx = int(len(sorted_times) * 0.95)
        results["p95"] = sorted_times[p95_idx] if p95_idx < len(sorted_times) else sorted_times[-1]
        results["avg"] = sum(results["times"]) / len(results["times"])
        results["max"] = max(results["times"])
    else:
        results["p95"] = 0
        results["avg"] = 0
        results["max"] = 0

    results["total"] = total
    results["rps"] = total / duration_secs if duration_secs > 0 else 0
    results["error_rate"] = (results["failed"] / total * 100) if total > 0 else 0

    return results


async def find_breaking_point(base_url: str):
    """Progressively increase load to find breaking point"""
    print(f"\n{'='*70}")
    print("BHARATBUILD AI - STRESS TEST (Finding Breaking Point)")
    print(f"{'='*70}")
    print(f"Target: {base_url}")
    print(f"{'='*70}\n")

    # Health check
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{base_url}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    print("[OK] API is healthy\n")
                else:
                    print(f"[WARN] API returned {response.status}\n")
        except Exception as e:
            print(f"[FAIL] Cannot connect: {e}")
            return

    # Test levels
    levels = [10, 25, 50, 100, 200, 500, 1000]
    results_table = []
    breaking_point = None

    print(f"{'Users':<10} {'Total Req':<12} {'RPS':<10} {'Avg(ms)':<10} {'P95(ms)':<10} {'Max(ms)':<10} {'Err%':<8} {'Status'}")
    print("-" * 85)

    for num_users in levels:
        print(f"Testing {num_users} users...", end=" ", flush=True)

        try:
            results = await run_stress_level(base_url, num_users, duration_secs=10)

            # Determine status
            if results["error_rate"] > 50:
                status = "[BROKEN]"
                if breaking_point is None:
                    breaking_point = num_users
            elif results["error_rate"] > 10:
                status = "[DEGRADED]"
            elif results["p95"] > 1000:
                status = "[SLOW]"
            else:
                status = "[OK]"

            print(f"\r{num_users:<10} {results['total']:<12} {results['rps']:<10.1f} {results['avg']:<10.1f} {results['p95']:<10.1f} {results['max']:<10.1f} {results['error_rate']:<8.1f} {status}")

            results_table.append({
                "users": num_users,
                "total": results["total"],
                "rps": results["rps"],
                "avg": results["avg"],
                "p95": results["p95"],
                "error_rate": results["error_rate"],
                "status": status
            })

            # Stop if system is broken
            if results["error_rate"] > 80:
                print("\n[!] System overwhelmed, stopping test")
                break

        except Exception as e:
            print(f"\r{num_users:<10} ERROR: {str(e)[:50]}")
            break

    # Summary
    print(f"\n{'='*70}")
    print("STRESS TEST SUMMARY")
    print(f"{'='*70}")

    if breaking_point:
        print(f"\n[!] Breaking Point: ~{breaking_point} concurrent users")
        print(f"    System starts failing above this level")
    else:
        max_tested = levels[-1] if results_table else 0
        print(f"\n[OK] System handled up to {max_tested} users without breaking")

    # Capacity estimation
    if results_table:
        best_result = max(results_table, key=lambda x: x["rps"] if x["error_rate"] < 10 else 0)
        print(f"\nBest Performance:")
        print(f"  - Max stable RPS: {best_result['rps']:.1f} requests/second")
        print(f"  - At user level: {best_result['users']} concurrent users")

        # Extrapolate to 100k
        if best_result["rps"] > 0:
            servers_needed = int(100000 / best_result["rps"]) + 1
            print(f"\nTo support 100,000 users:")
            print(f"  - Current capacity: ~{int(best_result['rps'] * 10)} users (with 10 req/user/sec)")
            print(f"  - Estimated servers needed: {servers_needed}+ instances")
            print(f"  - Plus: Load balancer, DB scaling, caching, CDN")

    print(f"\n{'='*70}\n")

    # Save results
    import json
    results_file = f"stress_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump({
            "breaking_point": breaking_point,
            "results": results_table,
            "timestamp": datetime.now().isoformat()
        }, f, indent=2)
    print(f"Results saved to: {results_file}")


async def main():
    parser = argparse.ArgumentParser(description='BharatBuild AI Stress Test')
    parser.add_argument('--url', default='http://localhost:8000/api/v1',
                        help='API base URL')
    args = parser.parse_args()

    await find_breaking_point(args.url)


if __name__ == "__main__":
    asyncio.run(main())

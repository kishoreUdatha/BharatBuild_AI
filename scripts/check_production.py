#!/usr/bin/env python3
"""
Post-Deployment Health Check for BharatBuild AI Production

Run this AFTER deploying to verify everything is working.

Usage:
    # Check production
    python scripts/check_production.py

    # Check specific URL
    python scripts/check_production.py --url https://your-domain.com

Exit codes:
    0 = All critical checks passed
    1 = Critical failure (registration broken)
    2 = Warnings (some issues)
"""

import argparse
import sys
import time
import json

try:
    import requests
except ImportError:
    print("Please install requests: pip install requests")
    sys.exit(1)


# Default production URL (update this for your deployment)
DEFAULT_URL = "http://bharatbuild-alb-223139118.ap-south-1.elb.amazonaws.com"


class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def log(message, color=Colors.RESET):
    print(f"{color}{message}{Colors.RESET}")


def check_endpoint(url, name, timeout=10):
    """Check if an endpoint is accessible and return response"""
    try:
        start = time.time()
        response = requests.get(url, timeout=timeout)
        elapsed = (time.time() - start) * 1000

        if response.status_code == 200:
            log(f"  [PASS] {name} ({elapsed:.0f}ms)", Colors.GREEN)
            return True, response
        elif response.status_code == 503:
            log(f"  [FAIL] {name} - Service Unavailable", Colors.RED)
            return False, response
        else:
            log(f"  [WARN] {name} - Status {response.status_code}", Colors.YELLOW)
            return False, response
    except requests.exceptions.Timeout:
        log(f"  [FAIL] {name} - Timeout after {timeout}s", Colors.RED)
        return False, None
    except requests.exceptions.ConnectionError as e:
        log(f"  [FAIL] {name} - Connection error: {e}", Colors.RED)
        return False, None
    except Exception as e:
        log(f"  [FAIL] {name} - Error: {e}", Colors.RED)
        return False, None


def main():
    parser = argparse.ArgumentParser(description="Check BharatBuild production health")
    parser.add_argument("--url", default=DEFAULT_URL, help="Base URL to check")
    parser.add_argument("--timeout", type=int, default=10, help="Request timeout")
    args = parser.parse_args()

    base_url = args.url.rstrip('/')

    log(f"\n{'='*60}", Colors.BOLD)
    log(f"BharatBuild AI Production Health Check", Colors.BOLD)
    log(f"{'='*60}", Colors.BOLD)
    log(f"URL: {base_url}")
    log(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    all_passed = True
    critical_passed = True

    # 1. Basic Health Check
    log(f"\n{Colors.BOLD}1. Basic Health{Colors.RESET}")
    ok, _ = check_endpoint(f"{base_url}/health", "Root health")
    ok2, _ = check_endpoint(f"{base_url}/api/v1/health", "API health")
    all_passed = all_passed and ok and ok2

    # 2. Deep Health Check (Database, Redis)
    log(f"\n{Colors.BOLD}2. Deep Health Check{Colors.RESET}")
    ok, resp = check_endpoint(f"{base_url}/api/v1/health/deep", "Deep health")

    if resp and resp.status_code == 200:
        try:
            data = resp.json()
            checks = data.get("checks", {})

            # Database check (CRITICAL)
            db = checks.get("database", {})
            db_ok = db.get("status") == "healthy" and db.get("tables_ready", False)
            if db_ok:
                log(f"    Database: OK", Colors.GREEN)
            else:
                log(f"    Database: FAILED - {db.get('message', 'Unknown error')}", Colors.RED)
                critical_passed = False

            # Redis check
            redis = checks.get("redis", {})
            if redis.get("status") == "healthy":
                log(f"    Redis: OK", Colors.GREEN)
            else:
                log(f"    Redis: {redis.get('status', 'unknown')} - {redis.get('message', '')}", Colors.YELLOW)

            # Registration ready
            if data.get("registration_ready"):
                log(f"    Registration: READY", Colors.GREEN)
            else:
                log(f"    Registration: NOT READY", Colors.RED)
                critical_passed = False

        except Exception as e:
            log(f"    Could not parse response: {e}", Colors.YELLOW)
    elif resp and resp.status_code == 503:
        try:
            data = resp.json()
            log(f"    Service unavailable - checking details...", Colors.RED)
            checks = data.get("detail", {}).get("checks", {}) if isinstance(data.get("detail"), dict) else {}
            for name, check in checks.items():
                status = check.get("status", "unknown")
                message = check.get("message", "")
                if status == "healthy":
                    log(f"    {name}: OK", Colors.GREEN)
                else:
                    log(f"    {name}: {status} - {message}", Colors.RED)
            critical_passed = False
        except:
            critical_passed = False
    else:
        critical_passed = False

    # 3. Registration Health
    log(f"\n{Colors.BOLD}3. Registration Check{Colors.RESET}")
    ok, resp = check_endpoint(f"{base_url}/api/v1/health/registration", "Registration health")

    if resp and resp.status_code == 200:
        try:
            data = resp.json()
            if data.get("can_register"):
                log(f"    Users can register: YES", Colors.GREEN)
            else:
                log(f"    Users can register: NO", Colors.RED)
                critical_passed = False

            # Show troubleshooting tips
            tips = data.get("troubleshooting", [])
            for tip in tips:
                log(f"    TIP: {tip}", Colors.YELLOW)
        except:
            pass
    elif resp and resp.status_code == 503:
        log(f"    Registration NOT working!", Colors.RED)
        try:
            data = resp.json()
            tips = data.get("detail", {}).get("troubleshooting", []) if isinstance(data.get("detail"), dict) else []
            for tip in tips:
                log(f"    TIP: {tip}", Colors.YELLOW)
        except:
            pass
        critical_passed = False
    else:
        critical_passed = False

    # 4. Test Auth Endpoints
    log(f"\n{Colors.BOLD}4. Auth Endpoints{Colors.RESET}")
    try:
        # Test register endpoint (should return 422 for empty body)
        resp = requests.post(f"{base_url}/api/v1/auth/register", json={}, timeout=args.timeout)
        if resp.status_code == 422:
            log(f"  [PASS] Register endpoint accessible (validation working)", Colors.GREEN)
        elif resp.status_code == 429:
            log(f"  [PASS] Register endpoint accessible (rate limited)", Colors.GREEN)
        else:
            log(f"  [WARN] Register endpoint returned {resp.status_code}", Colors.YELLOW)

        # Test login endpoint
        resp = requests.post(f"{base_url}/api/v1/auth/login", json={}, timeout=args.timeout)
        if resp.status_code == 422:
            log(f"  [PASS] Login endpoint accessible (validation working)", Colors.GREEN)
        elif resp.status_code == 429:
            log(f"  [PASS] Login endpoint accessible (rate limited)", Colors.GREEN)
        else:
            log(f"  [WARN] Login endpoint returned {resp.status_code}", Colors.YELLOW)
    except Exception as e:
        log(f"  [FAIL] Auth endpoints error: {e}", Colors.RED)

    # Summary
    log(f"\n{'='*60}", Colors.BOLD)
    log(f"RESULT", Colors.BOLD)
    log(f"{'='*60}", Colors.BOLD)

    if critical_passed:
        log(f"\nCRITICAL CHECKS PASSED - Registration should work", Colors.GREEN)
        exit_code = 0
    else:
        log(f"\nCRITICAL CHECKS FAILED - Registration is broken!", Colors.RED)
        log(f"\nTo fix:", Colors.YELLOW)
        log(f"  1. Check database connection", Colors.YELLOW)
        log(f"  2. Run: curl {base_url}/api/v1/create-tables", Colors.YELLOW)
        log(f"  3. Check RDS security groups allow ECS access", Colors.YELLOW)
        exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Production Integration Test Runner

This script runs the comprehensive production integration test suite
with proper configuration and reporting.

Usage:
    python run_production_tests.py [options]

Options:
    --quick     Run only essential tests (skip slow/comprehensive tests)
    --security  Run only security-focused tests
    --crud      Run only CRUD operation tests
    --auth      Run only authentication tests
    --performance Run only performance tests
    --report    Generate detailed HTML report
    --parallel  Run tests in parallel (requires pytest-xdist)
"""
import os
import sys
import argparse
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Run production integration tests")
    
    # Test selection options
    parser.add_argument("--quick", action="store_true", 
                       help="Run only essential tests (skip slow tests)")
    parser.add_argument("--security", action="store_true",
                       help="Run only security-focused tests")
    parser.add_argument("--crud", action="store_true",
                       help="Run only CRUD operation tests")
    parser.add_argument("--auth", action="store_true", 
                       help="Run only authentication tests")
    parser.add_argument("--performance", action="store_true",
                       help="Run only performance tests")
    
    # Output options
    parser.add_argument("--report", action="store_true",
                       help="Generate detailed HTML report")
    parser.add_argument("--parallel", action="store_true",
                       help="Run tests in parallel")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Increase verbosity")
    
    # Backend options
    parser.add_argument("--backend-url", default="http://backend-grc_api-1:80",
                       help="Backend URL for testing (default: http://backend-grc_api-1:80)")
    parser.add_argument("--timeout", type=int, default=300,
                       help="Test timeout in seconds (default: 300)")
    
    args = parser.parse_args()
    
    # Build pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add test directory
    test_dir = Path(__file__).parent
    cmd.append(str(test_dir))
    
    # Test selection markers
    markers = []
    if args.quick:
        markers.append("not slow")
    if args.security:
        markers.append("security")
    if args.crud:
        markers.append("crud")
    if args.auth:
        markers.append("auth")
    if args.performance:
        markers.append("performance")
    
    if markers:
        cmd.extend(["-m", " and ".join(markers)])
    
    # Output options
    if args.verbose:
        cmd.append("-vv")
    else:
        cmd.append("-v")
    
    if args.report:
        cmd.extend(["--html", "production_test_report.html", "--self-contained-html"])
    
    if args.parallel:
        cmd.extend(["-n", "auto"])
    
    # Timeout (skip if pytest-timeout not installed)
    # cmd.extend(["--timeout", str(args.timeout)])
    
    # Environment variables
    env = os.environ.copy()
    env["BACKEND_URL"] = args.backend_url
    
    # Additional pytest options
    cmd.extend([
        "--tb=short",
        "--strict-markers", 
        "--disable-warnings",
        "--color=yes",
        "--durations=10"
    ])
    
    print("Running production integration tests...")
    print(f"Command: {' '.join(cmd)}")
    print(f"Backend URL: {args.backend_url}")
    print(f"Test directory: {test_dir}")
    print()
    
    # Check if backend is accessible
    try:
        import requests
        response = requests.get(f"{args.backend_url}/docs", timeout=10)
        if response.status_code == 200:
            print("✓ Backend is accessible")
        else:
            print(f"⚠ Backend returned status {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"⚠ Cannot reach backend: {e}")
        print("Tests may fail if backend is not running")
    
    print()
    
    # Run tests
    try:
        result = subprocess.run(cmd, env=env, cwd=test_dir)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error running tests: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
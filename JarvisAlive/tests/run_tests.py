#!/usr/bin/env python3
"""
Test runner script with coverage reporting
"""
import subprocess
import sys
import os

def run_tests_with_coverage():
    """Run tests with coverage reporting"""
    print("🧪 Running Lead Scanner Tests with Coverage...")
    print("=" * 60)
    
    # Add parent directory to Python path
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.environ['PYTHONPATH'] = parent_dir
    
    # Check if pytest and coverage are installed
    try:
        import pytest
        import coverage
    except ImportError:
        print("❌ Installing required packages...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pytest", "pytest-asyncio", "pytest-cov", "coverage"])
    
    # Run tests with coverage
    test_file = "test_lead_scanner.py"
    coverage_cmd = [
        sys.executable, "-m", "pytest",
        test_file,
        "-v",  # Verbose
        "--cov=departments.sales.agents.lead_scanner_implementation",  # Coverage for our module
        "--cov-report=term-missing",  # Show missing lines
        "--cov-report=html",  # Generate HTML report
        "--cov-fail-under=90",  # Fail if coverage < 90%
    ]
    
    try:
        result = subprocess.run(coverage_cmd, cwd=os.path.dirname(os.path.abspath(__file__)))
        
        if result.returncode == 0:
            print("\n✅ All tests passed!")
            print("📊 Coverage report generated in htmlcov/index.html")
        else:
            print("\n❌ Some tests failed or coverage threshold not met")
            
        return result.returncode
        
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(run_tests_with_coverage())
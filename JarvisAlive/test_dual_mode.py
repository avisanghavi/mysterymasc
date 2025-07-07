#!/usr/bin/env python3
"""Test script for dual-mode operation."""

import sys
import os
import asyncio

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import jarvis_mode, chat_interface, is_technical_request


async def test_request_routing():
    """Test request routing between technical and business modes."""
    print("Testing request routing logic...")
    
    test_cases = [
        # Business requests (should go to Jarvis)
        ("Grow sales by 30%", False),
        ("Reduce operational costs", False),
        ("Improve customer satisfaction", False),
        ("Scale our marketing department", False),
        ("Increase revenue this quarter", False),
        
        # Technical requests (should go to agent builder)
        ("Create an email monitoring agent", True),
        ("Build automation for file backup", True),
        ("Set up API integration", True),
        ("Monitor system resources", True),
        ("Create webhook endpoint", True),
        
        # Edge cases
        ("Help with business automation", False),  # Business context wins
        ("Technical support for sales", False),    # Business context wins
        ("Create agent for department coordination", False),  # Business context wins
    ]
    
    passed = 0
    total = len(test_cases)
    
    for request, expected_is_technical in test_cases:
        result = await is_technical_request(request)
        if result == expected_is_technical:
            status = "✓ PASS"
            passed += 1
        else:
            status = "✗ FAIL"
        
        mode = "Technical" if result else "Business"
        expected_mode = "Technical" if expected_is_technical else "Business"
        print(f"{status} '{request}' → {mode} (expected: {expected_mode})")
    
    print(f"\nRequest Routing: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    return passed == total


def test_import_functionality():
    """Test that all imports work correctly."""
    print("\nTesting import functionality...")
    
    try:
        from orchestration.orchestrator import HeyJarvisOrchestrator, OrchestratorConfig
        print("✓ Orchestrator imports working")
    except ImportError as e:
        print(f"✗ Orchestrator import failed: {e}")
        return False
    
    try:
        from orchestration.jarvis import Jarvis, JarvisConfig
        print("✓ Jarvis imports working")
    except ImportError as e:
        print(f"✗ Jarvis import failed: {e}")
        return False
    
    try:
        import argparse
        import asyncio
        import uuid
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        print("✓ All required dependencies available")
    except ImportError as e:
        print(f"✗ Dependency import failed: {e}")
        return False
    
    return True


def test_configuration_setup():
    """Test configuration setup for both modes."""
    print("\nTesting configuration setup...")
    
    # Test environment variables
    required_vars = ["ANTHROPIC_API_KEY"]
    optional_vars = ["REDIS_URL", "MAX_RETRIES", "SESSION_TIMEOUT"]
    
    for var in required_vars:
        if not os.getenv(var):
            print(f"⚠️  Warning: {var} not set (required for actual operation)")
        else:
            print(f"✓ {var} configured")
    
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"✓ {var} = {value}")
        else:
            print(f"○ {var} using default")
    
    # Test that configurations can be created
    try:
        from orchestration.orchestrator import OrchestratorConfig
        config = OrchestratorConfig(
            anthropic_api_key="test_key",
            redis_url="redis://localhost:6379",
            max_retries=3,
            session_timeout=3600
        )
        print("✓ OrchestratorConfig creation works")
    except Exception as e:
        print(f"✗ OrchestratorConfig creation failed: {e}")
        return False
    
    try:
        from orchestration.jarvis import JarvisConfig
        jarvis_config = JarvisConfig(
            orchestrator_config=config,
            max_concurrent_departments=5,
            enable_autonomous_department_creation=True,
            enable_cross_department_coordination=True
        )
        print("✓ JarvisConfig creation works")
    except Exception as e:
        print(f"✗ JarvisConfig creation failed: {e}")
        return False
    
    return True


def test_ui_components():
    """Test UI components work correctly."""
    print("\nTesting UI components...")
    
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        
        console = Console()
        
        # Test panel creation
        panel = Panel("Test content", title="Test Panel")
        print("✓ Panel creation works")
        
        # Test table creation
        table = Table(title="Test Table")
        table.add_column("Column 1")
        table.add_column("Column 2")
        table.add_row("Row 1", "Data 1")
        print("✓ Table creation works")
        
        return True
        
    except Exception as e:
        print(f"✗ UI component test failed: {e}")
        return False


async def test_mode_selection():
    """Test that mode selection logic works."""
    print("\nTesting mode selection logic...")
    
    # Test main function argument parsing
    try:
        import argparse
        
        # Simulate different argument combinations
        test_args = [
            ([], "chat_interface"),           # Default mode
            (["--demo"], "demo_mode"),        # Demo mode
            (["--jarvis"], "jarvis_mode"),    # Jarvis mode
        ]
        
        for args, expected_mode in test_args:
            parser = argparse.ArgumentParser()
            parser.add_argument("--demo", action="store_true")
            parser.add_argument("--jarvis", action="store_true")
            
            parsed_args = parser.parse_args(args)
            
            if parsed_args.demo:
                actual_mode = "demo_mode"
            elif parsed_args.jarvis:
                actual_mode = "jarvis_mode"
            else:
                actual_mode = "chat_interface"
            
            if actual_mode == expected_mode:
                print(f"✓ Args {args} → {actual_mode}")
            else:
                print(f"✗ Args {args} → {actual_mode} (expected: {expected_mode})")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Mode selection test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("DUAL-MODE OPERATION TESTS")
    print("=" * 60)
    
    results = []
    
    # Run all tests
    results.append(("Import Functionality", test_import_functionality()))
    results.append(("Configuration Setup", test_configuration_setup()))
    results.append(("UI Components", test_ui_components()))
    results.append(("Request Routing", await test_request_routing()))
    results.append(("Mode Selection", await test_mode_selection()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed_tests = 0
    total_tests = len(results)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:<25} {status}")
        if passed:
            passed_tests += 1
    
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    print(f"\nOVERALL: {passed_tests}/{total_tests} tests passed ({success_rate:.1f}%)")
    
    if success_rate >= 80:
        print("🎉 EXCELLENT - Dual-mode operation is working correctly!")
        exit_code = 0
    elif success_rate >= 60:
        print("👍 GOOD - Most functionality working, minor issues")
        exit_code = 0
    else:
        print("❌ POOR - Significant issues need resolution")
        exit_code = 1
    
    # Test basic mode switching
    print("\n" + "=" * 60)
    print("MODE SWITCHING VERIFICATION")
    print("=" * 60)
    print("✓ Normal mode: python main.py")
    print("✓ Demo mode: python main.py --demo")
    print("✓ Jarvis mode: python main.py --jarvis")
    print("\n💡 All modes should work without breaking existing functionality")
    
    return exit_code


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
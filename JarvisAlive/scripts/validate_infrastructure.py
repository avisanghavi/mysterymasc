#!/usr/bin/env python3
"""
HeyJarvis Infrastructure Validation Script

This script validates all prerequisites for the HeyJarvis system including:
- Redis connection and functionality
- Docker daemon status
- Environment variables
- Python version and required packages

Exit codes:
0: All checks passed
1: One or more checks failed
2: Critical error in validation script itself
"""

import sys
import os
import subprocess
import socket
from typing import Dict, Tuple, List
import importlib.metadata
from pathlib import Path

try:
    import redis
except ImportError:
    redis = None

try:
    from rich.console import Console
    from rich.table import Table
    from rich.text import Text
    from rich import print as rprint
except ImportError:
    # Fallback to regular print if rich is not available
    Console = None
    rprint = print


class InfrastructureValidator:
    def __init__(self):
        self.checks_passed = []
        self.checks_failed = []
        self.console = Console() if Console else None
        
        # Required packages with minimum versions
        self.required_packages = {
            'redis': '4.5.0',
            'anthropic': '0.5.0',
            'fastapi': '0.100.0',
            'pydantic': '2.0.0',
            'rich': '13.0.0',
            'httpx': '0.24.0'
        }
        
    def _print_header(self):
        """Print the header with formatting"""
        if self.console:
            self.console.print("\n🔍 HeyJarvis Infrastructure Validation", style="bold blue")
            self.console.print("=" * 50, style="blue")
        else:
            print("\n🔍 HeyJarvis Infrastructure Validation")
            print("=" * 50)
    
    def _print_check_result(self, check_name: str, passed: bool, details: str = "", version: str = ""):
        """Print a check result with formatting"""
        status_char = "✓" if passed else "✗"
        status_color = "green" if passed else "red"
        
        if self.console:
            line = f"{status_char} {check_name.ljust(25)} "
            if passed:
                result = "OK"
                if version:
                    result += f" ({version})"
                self.console.print(line + result, style=status_color)
            else:
                self.console.print(line + "FAILED", style=status_color)
                if details:
                    self.console.print(f"  Error: {details}", style="red")
        else:
            line = f"{status_char} {check_name.ljust(25)} "
            if passed:
                result = "OK"
                if version:
                    result += f" ({version})"
                print(line + result)
            else:
                print(line + "FAILED")
                if details:
                    print(f"  Error: {details}")
    
    def _print_fix_instructions(self, instructions: List[str]):
        """Print fix instructions"""
        if self.console:
            self.console.print("  Fix:", style="yellow")
            for i, instruction in enumerate(instructions, 1):
                self.console.print(f"    {i}. {instruction}", style="yellow")
        else:
            print("  Fix:")
            for i, instruction in enumerate(instructions, 1):
                print(f"    {i}. {instruction}")
    
    def check_redis(self) -> Tuple[bool, str, str]:
        """Check Redis connection and functionality"""
        if redis is None:
            return False, "Redis package not installed", ""
        
        try:
            # Default Redis URL
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            
            # Create Redis connection
            r = redis.from_url(redis_url)
            
            # Test connection
            r.ping()
            
            # Test basic operations
            test_key = "heyjarvis:test"
            test_value = "validation_test"
            
            # SET operation
            r.set(test_key, test_value)
            
            # GET operation
            retrieved_value = r.get(test_key)
            if retrieved_value.decode('utf-8') != test_value:
                return False, "Redis SET/GET operations failed", ""
            
            # DELETE operation
            r.delete(test_key)
            
            # Test pub/sub functionality
            pubsub = r.pubsub()
            pubsub.subscribe("test_channel")
            r.publish("test_channel", "test_message")
            pubsub.unsubscribe("test_channel")
            pubsub.close()
            
            # Get Redis version
            info = r.info()
            version = info.get('redis_version', 'unknown')
            
            return True, "Redis connection successful", version
            
        except redis.ConnectionError:
            return False, f"Could not connect to Redis at {redis_url}", ""
        except Exception as e:
            return False, f"Redis error: {str(e)}", ""
    
    def check_docker(self) -> Tuple[bool, str, str]:
        """Check Docker daemon status"""
        try:
            # Check if Docker is installed
            result = subprocess.run(['docker', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                return False, "Docker not installed or not in PATH", ""
            
            version_line = result.stdout.strip()
            # Extract version number (e.g., "Docker version 24.0.5, build ced0996")
            version = version_line.split()[2].rstrip(',')
            
            # Check minimum version (20.10+)
            major, minor = map(int, version.split('.')[:2])
            if major < 20 or (major == 20 and minor < 10):
                return False, f"Docker version {version} is below minimum 20.10", version
            
            # Check if Docker daemon is running
            result = subprocess.run(['docker', 'info'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                return False, "Docker daemon not running", version
            
            # Test ability to run containers
            result = subprocess.run(['docker', 'run', '--rm', 'hello-world'], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return False, "Cannot run Docker containers", version
            
            return True, "Docker daemon running", version
            
        except subprocess.TimeoutExpired:
            return False, "Docker command timed out", ""
        except FileNotFoundError:
            return False, "Docker not installed", ""
        except Exception as e:
            return False, f"Docker error: {str(e)}", ""
    
    def check_environment(self) -> Tuple[bool, str, str]:
        """Check required environment variables"""
        issues = []
        
        # Check ANTHROPIC_API_KEY
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            issues.append("ANTHROPIC_API_KEY not set")
        elif not api_key.startswith('sk-ant-'):
            issues.append("ANTHROPIC_API_KEY format invalid (should start with 'sk-ant-')")
        
        # Check REDIS_URL (optional, has default)
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        
        # Check PYTHONPATH includes project root
        pythonpath = os.getenv('PYTHONPATH', '')
        project_root = str(Path(__file__).parent.parent)
        if project_root not in pythonpath.split(os.pathsep):
            issues.append(f"PYTHONPATH should include {project_root}")
        
        if issues:
            return False, "; ".join(issues), ""
        
        # Format for display
        details = []
        if api_key:
            masked_key = api_key[:7] + "***" + api_key[-4:] if len(api_key) > 11 else "sk-ant-***"
            details.append(f"ANTHROPIC_API_KEY: {masked_key}")
        details.append(f"REDIS_URL: {redis_url}")
        
        return True, "Environment variables valid", "\n  ".join(details)
    
    def check_python(self) -> Tuple[bool, str, str]:
        """Check Python version and packages"""
        # Check Python version
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        if sys.version_info < (3, 9):
            return False, f"Python {python_version} is below minimum 3.9", python_version
        
        # Check required packages
        missing_packages = []
        version_issues = []
        
        for package, min_version in self.required_packages.items():
            try:
                installed_version = importlib.metadata.version(package)
                # Simple version comparison (works for basic semver)
                if self._version_compare(installed_version, min_version) < 0:
                    version_issues.append(f"{package} {installed_version} < {min_version}")
            except importlib.metadata.PackageNotFoundError:
                missing_packages.append(package)
        
        # Test imports
        import_issues = []
        test_imports = ['redis', 'anthropic', 'fastapi', 'pydantic', 'rich', 'httpx']
        for module in test_imports:
            try:
                __import__(module)
            except ImportError:
                import_issues.append(f"Cannot import {module}")
        
        issues = missing_packages + version_issues + import_issues
        if issues:
            return False, "; ".join(issues), python_version
        
        return True, "Python environment valid", python_version
    
    def _version_compare(self, version1: str, version2: str) -> int:
        """Compare two version strings. Returns -1 if version1 < version2, 0 if equal, 1 if version1 > version2"""
        def normalize(v):
            return [int(x) for x in v.split('.')]
        
        v1_parts = normalize(version1)
        v2_parts = normalize(version2)
        
        # Pad with zeros if needed
        max_len = max(len(v1_parts), len(v2_parts))
        v1_parts.extend([0] * (max_len - len(v1_parts)))
        v2_parts.extend([0] * (max_len - len(v2_parts)))
        
        for i in range(max_len):
            if v1_parts[i] < v2_parts[i]:
                return -1
            elif v1_parts[i] > v2_parts[i]:
                return 1
        return 0
    
    def run_all_checks(self) -> int:
        """Run all validation checks and return exit code"""
        self._print_header()
        
        # Define all checks
        checks = [
            ("Redis Connection", self.check_redis, [
                "Install Redis: brew install redis (macOS) or apt-get install redis (Ubuntu)",
                "Start Redis: redis-server",
                "Verify it's running: redis-cli ping"
            ]),
            ("Docker Daemon", self.check_docker, [
                "Install Docker: https://docs.docker.com/get-docker/",
                "Start Docker daemon",
                "Verify it's running: docker info"
            ]),
            ("Environment Variables", self.check_environment, [
                "Set ANTHROPIC_API_KEY: export ANTHROPIC_API_KEY=sk-ant-your-key",
                "Set REDIS_URL if needed: export REDIS_URL=redis://localhost:6379",
                "Add project to PYTHONPATH: export PYTHONPATH=$PYTHONPATH:$(pwd)"
            ]),
            ("Python Version", self.check_python, [
                "Install Python 3.9+: https://www.python.org/downloads/",
                "Install required packages: pip install -r requirements.txt",
                "Verify imports work: python -c 'import redis, anthropic, fastapi'"
            ])
        ]
        
        # Run each check
        for check_name, check_func, fix_instructions in checks:
            try:
                passed, error_msg, version = check_func()
                
                if passed:
                    self.checks_passed.append(check_name)
                    self._print_check_result(check_name, True, version=version)
                    if error_msg and check_name == "Environment Variables":
                        # Special case: show environment details
                        for line in error_msg.split('\n'):
                            if line.strip():
                                if self.console:
                                    self.console.print(f"  - {line.strip()}", style="dim")
                                else:
                                    print(f"  - {line.strip()}")
                else:
                    self.checks_failed.append(check_name)
                    self._print_check_result(check_name, False, error_msg, version)
                    self._print_fix_instructions(fix_instructions)
                    
            except Exception as e:
                self.checks_failed.append(check_name)
                self._print_check_result(check_name, False, f"Validation error: {str(e)}")
                self._print_fix_instructions(fix_instructions)
        
        # Print summary
        self._print_summary()
        
        # Return appropriate exit code
        if self.checks_failed:
            return 1
        return 0
    
    def _print_summary(self):
        """Print final summary"""
        print()
        
        if not self.checks_failed:
            if self.console:
                self.console.print("System Status: READY", style="bold green")
                self.console.print("All checks passed! You can proceed with HeyJarvis MVP1.", style="green")
            else:
                print("System Status: READY")
                print("All checks passed! You can proceed with HeyJarvis MVP1.")
        else:
            if self.console:
                self.console.print("System Status: NOT READY", style="bold red")
                self.console.print(f"Failed checks: {len(self.checks_failed)}", style="red")
                self.console.print(f"Passed checks: {len(self.checks_passed)}", style="green")
            else:
                print("System Status: NOT READY")
                print(f"Failed checks: {len(self.checks_failed)}")
                print(f"Passed checks: {len(self.checks_passed)}")


def main():
    """Main entry point"""
    try:
        validator = InfrastructureValidator()
        exit_code = validator.run_all_checks()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nValidation interrupted by user")
        sys.exit(2)
    except Exception as e:
        print(f"Critical error in validation script: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
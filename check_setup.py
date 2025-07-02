#!/usr/bin/env python3
"""Check if all prerequisites are installed and configured for HeyJarvis."""

import sys
import os
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is 3.11+"""
    version = sys.version_info
    if version.major == 3 and version.minor >= 11:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} (OK)")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} (Need 3.11+)")
        return False

def check_docker():
    """Check if Docker is installed and running"""
    try:
        result = subprocess.run(['docker', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✅ {version}")
            
            # Check if Docker daemon is running
            result = subprocess.run(['docker', 'ps'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print("✅ Docker daemon is running")
                return True
            else:
                print("❌ Docker daemon not running - start Docker Desktop")
                return False
        else:
            print("❌ Docker command failed")
            return False
    except subprocess.TimeoutExpired:
        print("❌ Docker command timeout")
        return False
    except FileNotFoundError:
        print("❌ Docker not installed")
        return False

def check_redis():
    """Check if Redis is accessible"""
    try:
        import redis
        client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        client.ping()
        print("✅ Redis connection successful")
        return True
    except ImportError:
        print("❌ Redis Python package not installed")
        return False
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print("   Start Redis with: docker run -d --name redis -p 6379:6379 redis:latest")
        return False

def check_env_file():
    """Check if .env file exists and has required variables"""
    env_file = Path('.env')
    if not env_file.exists():
        print("❌ .env file not found")
        return False
    
    with open(env_file) as f:
        content = f.read()
    
    if 'OPENAI_API_KEY=' in content and len(content.split('OPENAI_API_KEY=')[1].split('\n')[0].strip()) > 10:
        print("✅ OpenAI API key configured in .env")
        return True
    else:
        print("❌ OpenAI API key not configured in .env")
        return False

def check_dependencies():
    """Check if required Python packages are installed"""
    required_packages = [
        'langgraph', 'langchain', 'pydantic', 'redis', 'rich', 
        'docker', 'aiohttp', 'tenacity'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing packages: {', '.join(missing)}")
        print("   Install with: pip install -r requirements.txt")
        return False
    else:
        print("✅ All required packages installed")
        return True

def main():
    """Run all checks"""
    print("🔍 HeyJarvis Setup Checker")
    print("=" * 40)
    
    checks = [
        ("Python Version", check_python_version),
        ("Docker", check_docker),
        ("Redis", check_redis),
        ("Environment File", check_env_file),
        ("Python Dependencies", check_dependencies)
    ]
    
    all_passed = True
    for name, check_func in checks:
        print(f"\n{name}:")
        if not check_func():
            all_passed = False
    
    print("\n" + "=" * 40)
    if all_passed:
        print("🎉 All checks passed! You can run HeyJarvis with:")
        print("   python main.py")
        print("\nOr try demo mode:")
        print("   python main.py --demo")
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        print("\nQuick fixes:")
        print("• Install missing packages: pip install -r requirements.txt")
        print("• Start Redis: docker run -d --name redis -p 6379:6379 redis:latest")
        print("• Check .env file has your OpenAI API key")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
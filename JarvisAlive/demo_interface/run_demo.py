#!/usr/bin/env python3
"""
Demo Interface Runner
Simple script to run the HeyJarvis demo interface
"""

import subprocess
import sys
import os

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = ["fastapi", "uvicorn", "websockets"]
    missing = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"Missing packages: {', '.join(missing)}")
        print("Install with: pip install fastapi uvicorn websockets")
        return False
    
    return True

def run_demo():
    """Run the demo interface"""
    if not check_dependencies():
        sys.exit(1)
    
    print("🚀 Starting HeyJarvis Demo Interface...")
    print("📱 Open your browser to: http://localhost:8000")
    print("🛑 Press Ctrl+C to stop the server")
    print()
    
    try:
        # Change to demo directory
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        
        # Run the FastAPI app
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "app:app", 
            "--host", "0.0.0.0", 
            "--port", "8000",
            "--reload"
        ])
    except KeyboardInterrupt:
        print("\n🛑 Demo interface stopped")
    except Exception as e:
        print(f"❌ Error running demo: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_demo()
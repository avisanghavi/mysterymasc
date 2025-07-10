#!/usr/bin/env python3
"""
Test script for the HeyJarvis Demo Interface
"""

import asyncio
import json
import sys
import os
from fastapi.testclient import TestClient

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app

def test_demo_interface():
    """Test the demo interface functionality"""
    
    print("🧪 Testing HeyJarvis Demo Interface")
    print("=" * 50)
    
    # Create test client
    client = TestClient(app)
    
    # Test 1: Health check
    print("\n1. Testing Health Check...")
    response = client.get("/api/health")
    assert response.status_code == 200
    health_data = response.json()
    print(f"   ✅ Health check passed: {health_data['status']}")
    
    # Test 2: Get scenarios
    print("\n2. Testing Demo Scenarios...")
    response = client.get("/api/scenarios")
    assert response.status_code == 200
    scenarios = response.json()
    print(f"   ✅ Retrieved {len(scenarios)} demo scenarios")
    
    # Test 3: Main page
    print("\n3. Testing Main Page...")
    response = client.get("/")
    assert response.status_code == 200
    assert "HeyJarvis" in response.text
    print("   ✅ Main page loads successfully")
    
    # Test 4: Process request
    print("\n4. Testing Request Processing...")
    response = client.post("/api/process", json={
        "request": "Find me 10 SaaS leads"
    })
    assert response.status_code == 200
    process_data = response.json()
    print(f"   ✅ Request processing started: {process_data['session_id']}")
    
    # Test 5: Export functionality (should fail without results)
    print("\n5. Testing Export Functionality...")
    response = client.get("/api/export/test_session")
    assert response.status_code == 404  # Expected - no results yet
    print("   ✅ Export endpoint responds correctly")
    
    print("\n" + "=" * 50)
    print("🎉 All tests passed! Demo interface is working correctly.")
    print("\n📋 Features tested:")
    print("   • Health check endpoint")
    print("   • Demo scenarios API")
    print("   • Main HTML interface")
    print("   • Request processing endpoint")
    print("   • Export functionality")
    
    print("\n🚀 To run the demo:")
    print("   1. Run: python3 app.py")
    print("   2. Open: http://localhost:8000")
    print("   3. Try the demo scenarios!")

if __name__ == "__main__":
    test_demo_interface()
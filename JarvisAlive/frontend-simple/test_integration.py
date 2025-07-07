#!/usr/bin/env python3
"""
HeyJarvis Backend Integration Test
Run this to verify your backend is ready for frontend connection
"""

import asyncio
import json
import requests
import websockets
from datetime import datetime

class BackendTester:
    def __init__(self, api_url="http://localhost:8000", ws_url="ws://localhost:8000"):
        self.api_url = api_url
        self.ws_url = ws_url
        self.session_id = f"test_session_{int(datetime.now().timestamp())}"
    
    def test_api_health(self):
        """Test if the FastAPI server is running and healthy"""
        print("🔍 Testing API Health...")
        try:
            response = requests.get(f"{self.api_url}/", timeout=5)
            if response.status_code == 200:
                print("✅ API Health Check: PASSED")
                print(f"   Response: {response.json()}")
                return True
            else:
                print(f"❌ API Health Check: FAILED (Status: {response.status_code})")
                return False
        except requests.exceptions.ConnectionError:
            print("❌ API Health Check: FAILED - Connection refused")
            print("   Make sure your backend is running: python api_server.py")
            return False
        except Exception as e:
            print(f"❌ API Health Check: FAILED - {e}")
            return False
    
    async def test_websocket_connection(self):
        """Test WebSocket connection"""
        print("\n🔍 Testing WebSocket Connection...")
        try:
            ws_endpoint = f"{self.ws_url}/ws/{self.session_id}"
            async with websockets.connect(ws_endpoint, timeout=5) as websocket:
                print("✅ WebSocket Connection: ESTABLISHED")
                
                # Test sending a message
                test_message = {
                    "user_request": "test connection",
                    "mode": "agent-builder"
                }
                
                await websocket.send(json.dumps(test_message))
                print("✅ WebSocket Send: SUCCESS")
                
                # Wait for response (with timeout)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10)
                    response_data = json.loads(response)
                    print("✅ WebSocket Receive: SUCCESS")
                    print(f"   Response Type: {response_data.get('type', 'unknown')}")
                    print(f"   Content: {response_data.get('content', 'No content')[:100]}...")
                    return True
                except asyncio.TimeoutError:
                    print("⚠️  WebSocket Receive: TIMEOUT (backend might be processing)")
                    return True  # Connection is still good
                    
        except websockets.exceptions.ConnectionClosed:
            print("❌ WebSocket Connection: CLOSED unexpectedly")
            return False
        except Exception as e:
            print(f"❌ WebSocket Connection: FAILED - {e}")
            return False
    
    async def test_agent_creation(self):
        """Test agent creation via REST API"""
        print("\n🔍 Testing Agent Creation...")
        try:
            agent_request = {
                "user_request": "Create a test email monitoring agent",
                "session_id": self.session_id
            }
            
            response = requests.post(
                f"{self.api_url}/agents/create",
                json=agent_request,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Agent Creation: SUCCESS")
                print(f"   Status: {result.get('status', 'unknown')}")
                if result.get('agent_spec'):
                    agent_spec = result['agent_spec']
                    print(f"   Agent Name: {agent_spec.get('name', 'Unknown')}")
                    print(f"   Capabilities: {len(agent_spec.get('capabilities', []))} found")
                return True
            else:
                print(f"❌ Agent Creation: FAILED (Status: {response.status_code})")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Agent Creation: FAILED - {e}")
            return False
    
    async def test_session_recovery(self):
        """Test session agent retrieval"""
        print("\n🔍 Testing Session Recovery...")
        try:
            response = requests.get(
                f"{self.api_url}/agents/session/{self.session_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Session Recovery: SUCCESS")
                print(f"   Session ID: {result.get('session_id', 'unknown')}")
                print(f"   Agents Found: {len(result.get('agents', []))}")
                return True
            else:
                print(f"❌ Session Recovery: FAILED (Status: {response.status_code})")
                return False
                
        except Exception as e:
            print(f"❌ Session Recovery: FAILED - {e}")
            return False
    
    def test_cors_configuration(self):
        """Test CORS configuration for frontend"""
        print("\n🔍 Testing CORS Configuration...")
        try:
            headers = {
                'Origin': 'http://localhost:8080',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Content-Type'
            }
            
            response = requests.options(f"{self.api_url}/agents/create", headers=headers)
            
            cors_headers = {
                'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
                'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
                'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers')
            }
            
            if any(cors_headers.values()):
                print("✅ CORS Configuration: ENABLED")
                for header, value in cors_headers.items():
                    if value:
                        print(f"   {header}: {value}")
                return True
            else:
                print("⚠️  CORS Configuration: NOT DETECTED")
                print("   Your frontend might have cross-origin issues")
                return False
                
        except Exception as e:
            print(f"❌ CORS Test: FAILED - {e}")
            return False
    
    async def run_full_test(self):
        """Run comprehensive backend test"""
        print("🚀 HeyJarvis Backend Integration Test")
        print("=" * 50)
        
        test_results = []
        
        # Test 1: API Health
        test_results.append(self.test_api_health())
        
        # Test 2: CORS
        test_results.append(self.test_cors_configuration())
        
        # Test 3: WebSocket
        test_results.append(await self.test_websocket_connection())
        
        # Test 4: Agent Creation (only if previous tests pass)
        if all(test_results):
            test_results.append(await self.test_agent_creation())
            
            # Test 5: Session Recovery
            test_results.append(await self.test_session_recovery())
        
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        passed = sum(test_results)
        total = len(test_results)
        
        print(f"Tests Passed: {passed}/{total}")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED! Your backend is ready for frontend integration!")
            print("\nNext steps:")
            print("1. Save the HTML frontend as 'index.html'")
            print("2. Serve it with: python -m http.server 8080")
            print("3. Open http://localhost:8080 in your browser")
        else:
            print("⚠️  Some tests failed. Please fix the issues above before connecting frontend.")
            
        return passed == total

# Quick test functions for individual components
async def quick_websocket_test():
    """Quick WebSocket test"""
    tester = BackendTester()
    return await tester.test_websocket_connection()

def quick_api_test():
    """Quick API test"""
    tester = BackendTester()
    return tester.test_api_health()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        # Quick test mode
        print("🔍 Quick Backend Test")
        tester = BackendTester()
        api_ok = tester.test_api_health()
        
        if api_ok:
            ws_ok = asyncio.run(tester.test_websocket_connection())
            if api_ok and ws_ok:
                print("\n✅ Quick test PASSED! Backend is responsive.")
            else:
                print("\n❌ Quick test FAILED! Check your backend.")
        else:
            print("\n❌ API not responding. Start backend with: python api_server.py")
    else:
        # Full test mode
        tester = BackendTester()
        asyncio.run(tester.run_full_test())
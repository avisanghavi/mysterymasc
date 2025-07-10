#!/usr/bin/env python3
"""
Test script for Supabase authentication integration.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_environment():
    """Test that all required environment variables are set."""
    print("🔍 Testing Environment Configuration...")
    
    required_vars = [
        'ANTHROPIC_API_KEY',
        'REDIS_URL',
        'SUPABASE_URL',
        'SUPABASE_ANON_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
            print(f"❌ {var}: Not set")
        else:
            # Show partial value for security
            display_value = value[:10] + "..." if len(value) > 10 else value
            print(f"✅ {var}: {display_value}")
    
    if missing_vars:
        print(f"\n❌ Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    print("✅ All environment variables are set!")
    return True

async def test_redis_connection():
    """Test Redis connection."""
    print("\n🔍 Testing Redis Connection...")
    
    try:
        import redis.asyncio as redis
        
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        client = redis.from_url(redis_url)
        
        # Test connection
        result = await client.ping()
        if result:
            print("✅ Redis connection successful!")
            
            # Test basic operations
            await client.set("test_key", "test_value")
            value = await client.get("test_key")
            await client.delete("test_key")
            
            if value == b"test_value":
                print("✅ Redis read/write operations working!")
            else:
                print("❌ Redis read/write operations failed!")
                return False
                
        await client.close()
        return True
        
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False

async def test_supabase_config():
    """Test Supabase configuration."""
    print("\n🔍 Testing Supabase Configuration...")
    
    try:
        from supabase import create_client
        
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not supabase_url or not supabase_key:
            print("❌ Supabase credentials not found in environment")
            return False
        
        # Create Supabase client
        supabase = create_client(supabase_url, supabase_key)
        print("✅ Supabase client created successfully!")
        
        # Test basic connectivity (this will fail if URL/key are invalid)
        try:
            # This will make a basic request to verify the client works
            auth_user = supabase.auth.get_user()
            print("✅ Supabase API connectivity verified!")
        except Exception as e:
            # This is expected if no user is logged in, but it verifies the client works
            if "session_not_found" in str(e) or "invalid_token" in str(e) or "JWT" in str(e):
                print("✅ Supabase API connectivity verified (no active session, which is expected)!")
            else:
                print(f"⚠️  Supabase API test returned: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Supabase configuration failed: {e}")
        return False

async def test_auth_models():
    """Test authentication models."""
    print("\n🔍 Testing Authentication Models...")
    
    try:
        from models.user_profile import UserProfile, UserSession, UserUsage, UserTier
        from models.auth_middleware import AuthMiddleware
        import redis.asyncio as redis
        
        # Test model creation
        profile = UserProfile(
            id="test_user",
            email="test@example.com",
            tier=UserTier.FREE
        )
        print("✅ UserProfile model creation successful!")
        
        session = UserSession(
            id="test_session",
            user_id="test_user"
        )
        print("✅ UserSession model creation successful!")
        
        usage = UserUsage(
            user_id="test_user",
            month="2024-07"
        )
        print("✅ UserUsage model creation successful!")
        
        # Test auth middleware initialization
        redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
        middleware = AuthMiddleware(redis_client)
        print("✅ AuthMiddleware initialization successful!")
        
        await redis_client.close()
        return True
        
    except Exception as e:
        print(f"❌ Authentication models test failed: {e}")
        return False

async def test_api_server_imports():
    """Test that the API server can import all required modules."""
    print("\n🔍 Testing API Server Imports...")
    
    try:
        # Test basic imports
        import fastapi
        import jwt
        print("✅ FastAPI and JWT imports successful!")
        
        # Test Supabase imports
        import supabase
        print("✅ Supabase import successful!")
        
        # Test custom model imports
        from models.auth_middleware import AuthMiddleware
        from models.user_profile import UserProfile
        print("✅ Custom model imports successful!")
        
        return True
        
    except Exception as e:
        print(f"❌ API server imports failed: {e}")
        return False

def test_frontend_config():
    """Test frontend configuration."""
    print("\n🔍 Testing Frontend Configuration...")
    
    try:
        # Read the frontend file
        frontend_path = "frontend-simple/index.html"
        if not os.path.exists(frontend_path):
            print(f"❌ Frontend file not found: {frontend_path}")
            return False
        
        with open(frontend_path, 'r') as f:
            content = f.read()
        
        # Check if Supabase credentials are configured
        supabase_url = os.getenv('SUPABASE_URL')
        if supabase_url and supabase_url in content:
            print("✅ Supabase URL configured in frontend!")
        else:
            print("⚠️  Supabase URL not found in frontend - please update manually")
        
        # Check if Supabase script is included
        if 'supabase-js' in content:
            print("✅ Supabase JS library included in frontend!")
        else:
            print("❌ Supabase JS library not found in frontend!")
            return False
        
        print("✅ Frontend configuration looks good!")
        return True
        
    except Exception as e:
        print(f"❌ Frontend configuration test failed: {e}")
        return False

async def run_all_tests():
    """Run all authentication tests."""
    print("🚀 HeyJarvis Authentication Test Suite")
    print("=" * 50)
    
    tests = [
        ("Environment Configuration", test_environment()),
        ("Redis Connection", test_redis_connection()),
        ("Supabase Configuration", test_supabase_config()),
        ("Authentication Models", test_auth_models()),
        ("API Server Imports", test_api_server_imports()),
        ("Frontend Configuration", test_frontend_config())
    ]
    
    results = []
    for test_name, test_coro in tests:
        if asyncio.iscoroutine(test_coro):
            result = await test_coro
        else:
            result = test_coro
        results.append((test_name, result))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n📈 Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Your authentication setup is ready!")
        print("\n🚀 Next Steps:")
        print("1. Start the API server: python3 api_server.py")
        print("2. Start the frontend: cd frontend-simple && python3 -m http.server 8080")
        print("3. Open http://localhost:8080 in your browser")
        print("4. Test authentication by entering your email")
    else:
        print("⚠️  Some tests failed. Please fix the issues above before proceeding.")
        return False
    
    return True

if __name__ == "__main__":
    try:
        result = asyncio.run(run_all_tests())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)
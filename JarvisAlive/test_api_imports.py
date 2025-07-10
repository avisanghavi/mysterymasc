#!/usr/bin/env python3
"""Test script to check what imports are missing for the API server."""

import sys

def test_import(module_name, package_name=None):
    try:
        if package_name:
            exec(f"from {module_name} import {package_name}")
        else:
            exec(f"import {module_name}")
        print(f"✅ {module_name}.{package_name if package_name else ''}")
        return True
    except ImportError as e:
        print(f"❌ {module_name}.{package_name if package_name else ''}: {e}")
        return False

print("🔍 Testing API Server Imports...")
print("=" * 40)

# Test basic imports
imports_to_test = [
    ("fastapi", "FastAPI"),
    ("fastapi", "HTTPException"),
    ("fastapi", "WebSocket"),
    ("fastapi", "Depends"),
    ("fastapi", "status"),
    ("fastapi.security", "HTTPBearer"),
    ("fastapi.security", "HTTPAuthorizationCredentials"),
    ("fastapi.middleware.cors", "CORSMiddleware"),
    ("pydantic", "BaseModel"),
    ("dotenv", "load_dotenv"),
    ("supabase", "create_client"),
    ("supabase", "Client"),
    ("jwt", None),
    ("jwt.exceptions", "InvalidTokenError"),
]

missing_imports = []

for module, package in imports_to_test:
    if not test_import(module, package):
        missing_imports.append((module, package))

# Test custom imports
print("\n🔍 Testing Custom Imports...")
print("=" * 40)

custom_imports = [
    ("models.auth_middleware", "AuthMiddleware"),
    ("models.user_profile", "UserProfile"),
    ("models.user_profile", "UserSession"),
    ("models.user_profile", "UserUsage"),
    ("models.user_profile", "UserTier"),
]

for module, package in custom_imports:
    if not test_import(module, package):
        missing_imports.append((module, package))

print("\n📊 Summary")
print("=" * 40)

if missing_imports:
    print(f"❌ {len(missing_imports)} missing imports:")
    for module, package in missing_imports:
        full_name = f"{module}.{package}" if package else module
        print(f"  - {full_name}")
    
    print("\n💡 Install missing packages with:")
    print("pip3 install fastapi uvicorn supabase pyjwt python-dotenv")
else:
    print("✅ All imports available!")
    print("🚀 Ready to run the API server!")
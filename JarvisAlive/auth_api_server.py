#!/usr/bin/env python3
"""Simplified FastAPI server for testing HeyJarvis authentication."""

import asyncio
import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, WebSocket, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from supabase import create_client, Client
import jwt
from jwt.exceptions import InvalidTokenError
import redis.asyncio as redis

from models.auth_middleware import AuthMiddleware
from models.user_profile import UserProfile

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
supabase: Optional[Client] = None
auth_middleware: Optional[AuthMiddleware] = None
redis_client = None

# Security
security = HTTPBearer()


class AuthRequest(BaseModel):
    """Request model for authentication."""
    email: str


class AuthCallbackRequest(BaseModel):
    """Request model for auth callback."""
    access_token: str
    refresh_token: str


class MockAgentRequest(BaseModel):
    """Mock request model for testing."""
    user_request: str
    session_id: str


class MockAgentResponse(BaseModel):
    """Mock response model for testing."""
    status: str
    message: str
    user_id: str
    session_id: str


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Verify JWT token and return current user."""
    if not supabase:
        # Allow anonymous access if Supabase is not configured
        return {"id": "anonymous", "email": "anonymous@local"}
    
    try:
        # Verify the JWT token
        token = credentials.credentials
        
        # Get the JWT secret from environment
        jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
        if not jwt_secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="JWT secret not configured"
            )
        
        # Decode and verify the token
        payload = jwt.decode(token, jwt_secret, algorithms=["HS256"], audience="authenticated")
        
        # Get user details from Supabase
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        return {
            "id": user_id,
            "email": payload.get("email", ""),
            "role": payload.get("role", "authenticated"),
            "metadata": payload.get("user_metadata", {})
        }
        
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


# Create FastAPI app
app = FastAPI(
    title="HeyJarvis Authentication Test API",
    description="Simplified API for testing Supabase authentication",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global supabase, auth_middleware, redis_client
    
    # Initialize Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    if supabase_url and supabase_key:
        supabase = create_client(supabase_url, supabase_key)
        logger.info("Supabase client initialized")
    else:
        logger.warning("Supabase credentials not found - running without authentication")
    
    # Initialize Redis and auth middleware
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        redis_client = redis.from_url(redis_url)
        auth_middleware = AuthMiddleware(redis_client)
        
        # Test Redis connection
        await redis_client.ping()
        logger.info("Redis connection established")
        
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        redis_client = None
        auth_middleware = None


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    if redis_client:
        await redis_client.close()


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "message": "HeyJarvis Authentication Test API is running",
        "supabase_configured": supabase is not None,
        "redis_configured": redis_client is not None,
        "auth_middleware_ready": auth_middleware is not None
    }


@app.post("/auth/login")
async def login(request: AuthRequest):
    """Send magic link to user's email."""
    if not supabase:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not available"
        )
    
    try:
        # Send magic link
        response = supabase.auth.sign_in_with_otp({
            "email": request.email,
            "options": {
                "email_redirect_to": os.getenv("FRONTEND_URL", "http://localhost:8080")
            }
        })
        
        return {
            "message": "Magic link sent to your email",
            "email": request.email
        }
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.post("/auth/callback")
async def auth_callback(request: AuthCallbackRequest):
    """Handle OAuth callback and validate tokens."""
    if not supabase:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not available"
        )
    
    try:
        # Set the session with the provided tokens
        supabase.auth.set_session(request.access_token, request.refresh_token)
        
        # Get user details
        user = supabase.auth.get_user()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session"
            )
        
        return {
            "user": {
                "id": user.user.id,
                "email": user.user.email,
                "created_at": user.user.created_at
            },
            "access_token": request.access_token,
            "refresh_token": request.refresh_token
        }
        
    except Exception as e:
        logger.error(f"Auth callback error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.post("/auth/logout")
async def logout(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Logout current user."""
    if not supabase:
        return {"message": "Logged out locally"}
    
    try:
        # Sign out from Supabase
        supabase.auth.sign_out()
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        # Even if Supabase logout fails, consider it successful
        return {"message": "Logged out"}


@app.get("/auth/profile")
async def get_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get current user profile."""
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "authenticated": current_user["id"] != "anonymous",
        "metadata": current_user.get("metadata", {})
    }


@app.get("/auth/usage")
async def get_usage(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get current user usage statistics."""
    if not auth_middleware:
        return {"error": "Auth middleware not available"}
    
    try:
        usage = await auth_middleware.get_user_usage(current_user['id'])
        quotas = await auth_middleware.get_user_quotas(current_user['id'])
        
        return {
            "usage": usage.model_dump() if usage else None,
            "quotas": [quota.model_dump() for quota in quotas]
        }
        
    except Exception as e:
        logger.error(f"Error getting usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Mock agent endpoint for testing authentication
@app.post("/agents/create", response_model=MockAgentResponse)
async def create_mock_agent(request: MockAgentRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Mock agent creation endpoint for testing authentication."""
    start_time = datetime.now()
    
    try:
        # Check user quota if auth middleware is available
        if auth_middleware:
            if not await auth_middleware.check_quota(current_user['id'], "agents"):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Agent creation quota exceeded"
                )
            
            if not await auth_middleware.check_quota(current_user['id'], "requests"):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Request quota exceeded"
                )
        
        # Prefix session_id with user_id for user isolation
        user_session_id = f"{current_user['id']}:{request.session_id}"
        
        # Migrate anonymous session if needed
        if auth_middleware and request.session_id.startswith("session_"):
            user_session_id = await auth_middleware.migrate_anonymous_session(
                current_user['id'], 
                request.session_id
            )
        
        # Mock agent creation logic
        mock_response = MockAgentResponse(
            status="completed",
            message=f"Mock agent created for request: '{request.user_request}'",
            user_id=current_user['id'],
            session_id=user_session_id
        )
        
        # Track usage if middleware is available
        if auth_middleware:
            processing_time = (datetime.now() - start_time).total_seconds()
            await auth_middleware.track_api_request(
                current_user['id'], 
                "/agents/create", 
                processing_time
            )
            
            # Track mock agent creation
            await auth_middleware.track_agent_creation(
                current_user['id'],
                "mock_agent_123",
                "mock_agent"
            )
        
        return mock_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating mock agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for testing authentication."""
    await websocket.accept()
    
    # First message should contain auth token
    try:
        auth_message = await websocket.receive_json()
        auth_token = auth_message.get("auth_token")
        
        if not auth_token:
            await websocket.send_json({"error": "Authentication required"})
            await websocket.close()
            return
        
        # Verify token
        try:
            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=auth_token)
            current_user = await get_current_user(credentials)
        except HTTPException as e:
            await websocket.send_json({"error": f"Authentication failed: {e.detail}"})
            await websocket.close()
            return
        
        # Track WebSocket connection
        if auth_middleware:
            await auth_middleware.track_websocket_connection(current_user['id'])
        
        # Prefix session_id with user_id
        user_session_id = f"{current_user['id']}:{session_id}"
        
        # Send welcome message
        await websocket.send_json({
            "type": "welcome",
            "message": f"WebSocket authenticated for user {current_user['email']}",
            "user_session_id": user_session_id
        })
        
        # Handle messages
        while True:
            data = await websocket.receive_json()
            user_request = data.get("user_request", "")
            
            # Echo back with user context
            await websocket.send_json({
                "type": "response",
                "message": f"Received from {current_user['email']}: {user_request}",
                "user_id": current_user['id'],
                "session_id": user_session_id
            })
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_json({"error": str(e)})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
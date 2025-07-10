"""Authentication middleware for session management and user mapping."""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
import redis.asyncio as redis
from .user_profile import UserProfile, UserSession, UserUsage, UserQuota, UserTier

logger = logging.getLogger(__name__)


class AuthMiddleware:
    """Middleware for handling authentication, session management, and user mapping."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.session_prefix = "session:"
        self.user_prefix = "user:"
        self.usage_prefix = "usage:"
        self.quota_prefix = "quota:"
    
    async def migrate_anonymous_session(self, user_id: str, anonymous_session_id: str) -> str:
        """Migrate an anonymous session to a user account."""
        try:
            # Get anonymous session data
            anonymous_key = f"{self.session_prefix}{anonymous_session_id}"
            session_data = await self.redis.get(anonymous_key)
            
            if not session_data:
                logger.info(f"No anonymous session found for {anonymous_session_id}")
                return f"{user_id}:{anonymous_session_id}"
            
            # Parse session data
            session_dict = json.loads(session_data)
            
            # Create new user session
            user_session_id = f"{user_id}:{anonymous_session_id}"
            user_session = UserSession(
                id=user_session_id,
                user_id=user_id,
                original_session_id=anonymous_session_id,
                context=session_dict,
                created_at=datetime.now(timezone.utc)
            )
            
            # Store user session
            await self.store_user_session(user_session)
            
            # Copy all session-related data
            await self._copy_session_data(anonymous_session_id, user_session_id)
            
            # Remove anonymous session
            await self.redis.delete(anonymous_key)
            
            logger.info(f"Migrated anonymous session {anonymous_session_id} to user {user_id}")
            return user_session_id
            
        except Exception as e:
            logger.error(f"Error migrating anonymous session: {e}")
            return f"{user_id}:{anonymous_session_id}"
    
    async def _copy_session_data(self, old_session_id: str, new_session_id: str):
        """Copy all session-related data from old to new session."""
        try:
            # Get all keys related to the old session
            pattern = f"*{old_session_id}*"
            keys = await self.redis.keys(pattern)
            
            for key in keys:
                key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                
                # Skip the main session key (already handled)
                if key_str == f"{self.session_prefix}{old_session_id}":
                    continue
                
                # Create new key with new session ID
                new_key = key_str.replace(old_session_id, new_session_id)
                
                # Copy the data
                data = await self.redis.get(key)
                if data:
                    await self.redis.set(new_key, data)
                
                # Copy TTL if exists
                ttl = await self.redis.ttl(key)
                if ttl > 0:
                    await self.redis.expire(new_key, ttl)
                
                # Delete old key
                await self.redis.delete(key)
                
        except Exception as e:
            logger.error(f"Error copying session data: {e}")
    
    async def get_or_create_user_profile(self, user_id: str, email: str) -> UserProfile:
        """Get existing user profile or create new one."""
        try:
            # Try to get existing profile
            profile_key = f"{self.user_prefix}{user_id}"
            profile_data = await self.redis.get(profile_key)
            
            if profile_data:
                profile_dict = json.loads(profile_data)
                return UserProfile(**profile_dict)
            
            # Create new profile
            profile = UserProfile(
                id=user_id,
                email=email,
                tier=UserTier.FREE,
                created_at=datetime.now(timezone.utc)
            )
            
            # Update limits based on tier
            profile.update_limits()
            
            # Store profile
            await self.store_user_profile(profile)
            
            # Initialize usage tracking
            await self.initialize_user_usage(user_id)
            
            logger.info(f"Created new user profile for {user_id}")
            return profile
            
        except Exception as e:
            logger.error(f"Error getting/creating user profile: {e}")
            # Return default profile on error
            return UserProfile(id=user_id, email=email)
    
    async def store_user_profile(self, profile: UserProfile):
        """Store user profile in Redis."""
        try:
            profile_key = f"{self.user_prefix}{profile.id}"
            profile_data = profile.model_dump_json()
            
            # Store with 7-day expiration
            await self.redis.setex(profile_key, 7 * 24 * 3600, profile_data)
            
        except Exception as e:
            logger.error(f"Error storing user profile: {e}")
    
    async def store_user_session(self, session: UserSession):
        """Store user session in Redis."""
        try:
            session_key = f"{self.session_prefix}{session.id}"
            session_data = session.model_dump_json()
            
            # Store with 24-hour expiration
            await self.redis.setex(session_key, 24 * 3600, session_data)
            
        except Exception as e:
            logger.error(f"Error storing user session: {e}")
    
    async def get_user_session(self, session_id: str) -> Optional[UserSession]:
        """Get user session from Redis."""
        try:
            session_key = f"{self.session_prefix}{session_id}"
            session_data = await self.redis.get(session_key)
            
            if session_data:
                session_dict = json.loads(session_data)
                return UserSession(**session_dict)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user session: {e}")
            return None
    
    async def update_user_activity(self, session_id: str):
        """Update user activity timestamp."""
        try:
            session = await self.get_user_session(session_id)
            if session:
                session.update_activity()
                await self.store_user_session(session)
                
        except Exception as e:
            logger.error(f"Error updating user activity: {e}")
    
    async def initialize_user_usage(self, user_id: str):
        """Initialize usage tracking for a user."""
        try:
            current_month = datetime.now(timezone.utc).strftime("%Y-%m")
            
            # Check if usage already exists
            usage_key = f"{self.usage_prefix}{user_id}:{current_month}"
            existing_usage = await self.redis.get(usage_key)
            
            if not existing_usage:
                # Create new usage record
                usage = UserUsage(
                    user_id=user_id,
                    month=current_month
                )
                
                usage_data = usage.model_dump_json()
                await self.redis.setex(usage_key, 32 * 24 * 3600, usage_data)  # 32 days
                
                # Initialize quotas
                await self.initialize_user_quotas(user_id)
                
        except Exception as e:
            logger.error(f"Error initializing user usage: {e}")
    
    async def initialize_user_quotas(self, user_id: str):
        """Initialize user quotas based on their tier."""
        try:
            # Get user profile to determine tier
            profile = await self.get_or_create_user_profile(user_id, "")
            limits = profile.get_tier_limits()
            
            # Current month
            current_month = datetime.now(timezone.utc).strftime("%Y-%m")
            next_month = (datetime.now(timezone.utc) + timedelta(days=32)).replace(day=1)
            
            # Create quotas
            quotas = [
                UserQuota(
                    user_id=user_id,
                    quota_type="requests",
                    limit=limits["monthly_requests"],
                    reset_date=next_month
                ),
                UserQuota(
                    user_id=user_id,
                    quota_type="agents",
                    limit=limits["agent_limit"],
                    reset_date=next_month
                ),
                UserQuota(
                    user_id=user_id,
                    quota_type="storage",
                    limit=limits["storage_limit_mb"],
                    reset_date=next_month
                )
            ]
            
            # Store quotas
            for quota in quotas:
                quota_key = f"{self.quota_prefix}{user_id}:{quota.quota_type}:{current_month}"
                quota_data = quota.model_dump_json()
                await self.redis.setex(quota_key, 32 * 24 * 3600, quota_data)
                
        except Exception as e:
            logger.error(f"Error initializing user quotas: {e}")
    
    async def track_api_request(self, user_id: str, endpoint: str, processing_time: float):
        """Track API request for usage monitoring."""
        try:
            current_month = datetime.now(timezone.utc).strftime("%Y-%m")
            
            # Update usage
            usage_key = f"{self.usage_prefix}{user_id}:{current_month}"
            usage_data = await self.redis.get(usage_key)
            
            if usage_data:
                usage_dict = json.loads(usage_data)
                usage = UserUsage(**usage_dict)
                usage.add_request(endpoint, processing_time)
                
                # Store updated usage
                await self.redis.setex(usage_key, 32 * 24 * 3600, usage.model_dump_json())
                
                # Update quota
                await self.consume_quota(user_id, "requests", 1)
                
        except Exception as e:
            logger.error(f"Error tracking API request: {e}")
    
    async def track_agent_creation(self, user_id: str, agent_id: str, agent_type: str):
        """Track agent creation for usage monitoring."""
        try:
            current_month = datetime.now(timezone.utc).strftime("%Y-%m")
            
            # Update usage
            usage_key = f"{self.usage_prefix}{user_id}:{current_month}"
            usage_data = await self.redis.get(usage_key)
            
            if usage_data:
                usage_dict = json.loads(usage_data)
                usage = UserUsage(**usage_dict)
                usage.add_agent(agent_id, agent_type)
                
                # Store updated usage
                await self.redis.setex(usage_key, 32 * 24 * 3600, usage.model_dump_json())
                
                # Update quota
                await self.consume_quota(user_id, "agents", 1)
                
        except Exception as e:
            logger.error(f"Error tracking agent creation: {e}")
    
    async def track_websocket_connection(self, user_id: str):
        """Track WebSocket connection for usage monitoring."""
        try:
            current_month = datetime.now(timezone.utc).strftime("%Y-%m")
            
            # Update usage
            usage_key = f"{self.usage_prefix}{user_id}:{current_month}"
            usage_data = await self.redis.get(usage_key)
            
            if usage_data:
                usage_dict = json.loads(usage_data)
                usage = UserUsage(**usage_dict)
                usage.add_websocket_connection()
                
                # Store updated usage
                await self.redis.setex(usage_key, 32 * 24 * 3600, usage.model_dump_json())
                
        except Exception as e:
            logger.error(f"Error tracking WebSocket connection: {e}")
    
    async def check_quota(self, user_id: str, quota_type: str) -> bool:
        """Check if user has remaining quota."""
        try:
            current_month = datetime.now(timezone.utc).strftime("%Y-%m")
            quota_key = f"{self.quota_prefix}{user_id}:{quota_type}:{current_month}"
            
            quota_data = await self.redis.get(quota_key)
            if quota_data:
                quota_dict = json.loads(quota_data)
                quota = UserQuota(**quota_dict)
                return not quota.is_exceeded()
            
            # If no quota found, initialize and allow
            await self.initialize_user_quotas(user_id)
            return True
            
        except Exception as e:
            logger.error(f"Error checking quota: {e}")
            return True  # Allow on error
    
    async def consume_quota(self, user_id: str, quota_type: str, amount: int = 1) -> bool:
        """Consume quota amount."""
        try:
            current_month = datetime.now(timezone.utc).strftime("%Y-%m")
            quota_key = f"{self.quota_prefix}{user_id}:{quota_type}:{current_month}"
            
            quota_data = await self.redis.get(quota_key)
            if quota_data:
                quota_dict = json.loads(quota_data)
                quota = UserQuota(**quota_dict)
                
                if quota.consume(amount):
                    # Store updated quota
                    await self.redis.setex(quota_key, 32 * 24 * 3600, quota.model_dump_json())
                    return True
                return False
            
            return True  # Allow if no quota found
            
        except Exception as e:
            logger.error(f"Error consuming quota: {e}")
            return True  # Allow on error
    
    async def get_user_usage(self, user_id: str) -> Optional[UserUsage]:
        """Get current month's usage for a user."""
        try:
            current_month = datetime.now(timezone.utc).strftime("%Y-%m")
            usage_key = f"{self.usage_prefix}{user_id}:{current_month}"
            
            usage_data = await self.redis.get(usage_key)
            if usage_data:
                usage_dict = json.loads(usage_data)
                return UserUsage(**usage_dict)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user usage: {e}")
            return None
    
    async def get_user_quotas(self, user_id: str) -> List[UserQuota]:
        """Get all quotas for a user."""
        try:
            current_month = datetime.now(timezone.utc).strftime("%Y-%m")
            quota_types = ["requests", "agents", "storage"]
            quotas = []
            
            for quota_type in quota_types:
                quota_key = f"{self.quota_prefix}{user_id}:{quota_type}:{current_month}"
                quota_data = await self.redis.get(quota_key)
                
                if quota_data:
                    quota_dict = json.loads(quota_data)
                    quotas.append(UserQuota(**quota_dict))
            
            return quotas
            
        except Exception as e:
            logger.error(f"Error getting user quotas: {e}")
            return []
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions and related data."""
        try:
            # Get all session keys
            session_pattern = f"{self.session_prefix}*"
            session_keys = await self.redis.keys(session_pattern)
            
            for key in session_keys:
                key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                session_data = await self.redis.get(key)
                
                if session_data:
                    session_dict = json.loads(session_data)
                    session = UserSession(**session_dict)
                    
                    if session.is_expired():
                        # Delete expired session
                        await self.redis.delete(key)
                        logger.info(f"Cleaned up expired session: {session.id}")
                        
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")
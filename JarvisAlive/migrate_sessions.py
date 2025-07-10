#!/usr/bin/env python3
"""
Migration script to convert existing Redis sessions to user-owned data.
This script should be run after implementing Supabase authentication.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

import redis.asyncio as redis
from dotenv import load_dotenv

from models.auth_middleware import AuthMiddleware
from models.user_profile import UserProfile, UserSession, UserUsage, UserTier

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SessionMigrator:
    """Migrates existing Redis sessions to user-owned data structure."""
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis_client = None
        self.auth_middleware = None
        
        # Migration statistics
        self.stats = {
            'total_sessions': 0,
            'migrated_sessions': 0,
            'failed_migrations': 0,
            'anonymous_sessions': 0,
            'user_profiles_created': 0,
            'errors': []
        }
    
    async def initialize(self):
        """Initialize Redis connection and auth middleware."""
        try:
            self.redis_client = redis.from_url(self.redis_url)
            self.auth_middleware = AuthMiddleware(self.redis_client)
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Redis connection established")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection: {e}")
            raise
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
    
    async def discover_sessions(self) -> List[str]:
        """Discover all existing sessions in Redis."""
        try:
            # Look for session keys with various patterns
            patterns = [
                "session:*",
                "session_*",
                "*:session:*",
                "orchestrator:*",
                "conversation:*"
            ]
            
            all_sessions = set()
            
            for pattern in patterns:
                keys = await self.redis_client.keys(pattern)
                for key in keys:
                    key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                    all_sessions.add(key_str)
            
            logger.info(f"Discovered {len(all_sessions)} potential session keys")
            return list(all_sessions)
            
        except Exception as e:
            logger.error(f"Error discovering sessions: {e}")
            return []
    
    async def analyze_session(self, session_key: str) -> Optional[Dict[str, Any]]:
        """Analyze a session key to extract useful information."""
        try:
            # Get session data
            session_data = await self.redis_client.get(session_key)
            if not session_data:
                return None
            
            # Try to parse as JSON
            try:
                data = json.loads(session_data)
            except json.JSONDecodeError:
                # If not JSON, treat as string data
                data = {"raw_data": session_data.decode('utf-8')}
            
            # Extract session info
            session_info = {
                'key': session_key,
                'data': data,
                'size': len(session_data),
                'created_at': datetime.now(timezone.utc),
                'type': self._classify_session(session_key, data)
            }
            
            # Try to extract user information
            user_info = self._extract_user_info(data)
            if user_info:
                session_info['user_info'] = user_info
            
            return session_info
            
        except Exception as e:
            logger.error(f"Error analyzing session {session_key}: {e}")
            self.stats['errors'].append(f"Analysis error for {session_key}: {e}")
            return None
    
    def _classify_session(self, session_key: str, data: Dict[str, Any]) -> str:
        """Classify the type of session based on key pattern and data."""
        key_lower = session_key.lower()
        
        if 'orchestrator' in key_lower:
            return 'orchestrator'
        elif 'conversation' in key_lower:
            return 'conversation'
        elif 'session' in key_lower:
            return 'generic_session'
        elif 'agent' in key_lower:
            return 'agent'
        else:
            return 'unknown'
    
    def _extract_user_info(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Try to extract user information from session data."""
        user_info = {}
        
        # Look for common user fields
        user_fields = ['user_id', 'email', 'username', 'user_email', 'session_id']
        
        for field in user_fields:
            if field in data:
                user_info[field] = data[field]
        
        # Look for nested user info
        if 'user' in data and isinstance(data['user'], dict):
            user_info.update(data['user'])
        
        return user_info if user_info else None
    
    async def create_demo_user_profile(self, session_key: str) -> UserProfile:
        """Create a demo user profile for sessions without user information."""
        # Generate a demo user ID based on session key
        demo_user_id = f"demo_user_{abs(hash(session_key)) % 10000}"
        demo_email = f"{demo_user_id}@demo.heyjarvis.local"
        
        profile = UserProfile(
            id=demo_user_id,
            email=demo_email,
            tier=UserTier.FREE,
            preferences={
                'migrated_from': session_key,
                'migration_date': datetime.now(timezone.utc).isoformat(),
                'is_demo_user': True
            },
            metadata={
                'original_session_key': session_key,
                'migration_source': 'anonymous_session'
            }
        )
        
        await self.auth_middleware.store_user_profile(profile)
        self.stats['user_profiles_created'] += 1
        
        return profile
    
    async def migrate_session_data(self, session_info: Dict[str, Any]) -> bool:
        """Migrate a single session to user-owned data structure."""
        try:
            session_key = session_info['key']
            data = session_info['data']
            
            # Determine user ID
            user_id = None
            if 'user_info' in session_info:
                user_info = session_info['user_info']
                user_id = user_info.get('user_id') or user_info.get('email')
            
            # Create demo user if no user ID found
            if not user_id:
                profile = await self.create_demo_user_profile(session_key)
                user_id = profile.id
                self.stats['anonymous_sessions'] += 1
            else:
                # Try to get existing profile or create new one
                profile = await self.auth_middleware.get_or_create_user_profile(
                    user_id, 
                    user_id if '@' in user_id else f"{user_id}@heyjarvis.local"
                )
            
            # Create new session ID with user prefix
            original_session_id = self._extract_session_id(session_key)
            new_session_id = f"{user_id}:{original_session_id}"
            
            # Create user session
            user_session = UserSession(
                id=new_session_id,
                user_id=user_id,
                original_session_id=original_session_id,
                context=data,
                created_at=datetime.now(timezone.utc)
            )
            
            # Store user session
            await self.auth_middleware.store_user_session(user_session)
            
            # Copy related data with new session ID
            await self._migrate_related_data(session_key, new_session_id)
            
            # Initialize user usage tracking
            await self.auth_middleware.initialize_user_usage(user_id)
            
            logger.info(f"Migrated session {session_key} to user {user_id}")
            self.stats['migrated_sessions'] += 1
            
            return True
            
        except Exception as e:
            logger.error(f"Error migrating session {session_info['key']}: {e}")
            self.stats['failed_migrations'] += 1
            self.stats['errors'].append(f"Migration error for {session_info['key']}: {e}")
            return False
    
    def _extract_session_id(self, session_key: str) -> str:\n        \"\"\"Extract session ID from session key.\"\"\"\n        # Remove common prefixes\n        session_id = session_key\n        for prefix in ['session:', 'session_', 'orchestrator:', 'conversation:']:\n            if session_id.startswith(prefix):\n                session_id = session_id[len(prefix):]\n                break\n        \n        return session_id\n    \n    async def _migrate_related_data(self, old_session_key: str, new_session_id: str):\n        \"\"\"Migrate related data (agents, conversations, etc.) to new session ID.\"\"\"\n        try:\n            # Get the base session ID for pattern matching\n            base_session_id = self._extract_session_id(old_session_key)\n            \n            # Find all keys that might be related to this session\n            patterns = [\n                f\"*{base_session_id}*\",\n                f\"*:{base_session_id}*\",\n                f\"*{base_session_id}:*\"\n            ]\n            \n            related_keys = set()\n            for pattern in patterns:\n                keys = await self.redis_client.keys(pattern)\n                for key in keys:\n                    key_str = key.decode('utf-8') if isinstance(key, bytes) else key\n                    if key_str != old_session_key:  # Skip the main session key\n                        related_keys.add(key_str)\n            \n            # Migrate related data\n            for key in related_keys:\n                await self._copy_key_data(key, key.replace(base_session_id, new_session_id))\n                \n        except Exception as e:\n            logger.error(f\"Error migrating related data for {old_session_key}: {e}\")\n    \n    async def _copy_key_data(self, old_key: str, new_key: str):\n        \"\"\"Copy data from old key to new key.\"\"\"\n        try:\n            # Get data\n            data = await self.redis_client.get(old_key)\n            if data:\n                # Copy data\n                await self.redis_client.set(new_key, data)\n                \n                # Copy TTL if exists\n                ttl = await self.redis_client.ttl(old_key)\n                if ttl > 0:\n                    await self.redis_client.expire(new_key, ttl)\n                \n                logger.debug(f\"Copied data from {old_key} to {new_key}\")\n                \n        except Exception as e:\n            logger.error(f\"Error copying data from {old_key} to {new_key}: {e}\")\n    \n    async def cleanup_old_sessions(self, session_keys: List[str]):\n        \"\"\"Clean up old session keys after migration.\"\"\"\n        logger.info(\"Starting cleanup of old session keys...\")\n        \n        cleaned_count = 0\n        for session_key in session_keys:\n            try:\n                # Delete old session key\n                await self.redis_client.delete(session_key)\n                cleaned_count += 1\n                \n                if cleaned_count % 10 == 0:\n                    logger.info(f\"Cleaned up {cleaned_count} old session keys\")\n                    \n            except Exception as e:\n                logger.error(f\"Error cleaning up {session_key}: {e}\")\n        \n        logger.info(f\"Cleaned up {cleaned_count} old session keys\")\n    \n    async def run_migration(self, dry_run: bool = False, cleanup: bool = False):\n        \"\"\"Run the complete migration process.\"\"\"\n        logger.info(f\"Starting session migration (dry_run={dry_run}, cleanup={cleanup})\")\n        \n        try:\n            # Discover sessions\n            session_keys = await self.discover_sessions()\n            self.stats['total_sessions'] = len(session_keys)\n            \n            if not session_keys:\n                logger.info(\"No sessions found to migrate\")\n                return\n            \n            logger.info(f\"Found {len(session_keys)} sessions to analyze\")\n            \n            # Analyze and migrate sessions\n            for i, session_key in enumerate(session_keys):\n                logger.info(f\"Processing session {i+1}/{len(session_keys)}: {session_key}\")\n                \n                # Analyze session\n                session_info = await self.analyze_session(session_key)\n                if not session_info:\n                    continue\n                \n                # Migrate session (if not dry run)\n                if not dry_run:\n                    await self.migrate_session_data(session_info)\n                else:\n                    logger.info(f\"[DRY RUN] Would migrate: {session_key}\")\n                \n                # Progress update\n                if (i + 1) % 10 == 0:\n                    logger.info(f\"Progress: {i+1}/{len(session_keys)} sessions processed\")\n            \n            # Cleanup old sessions if requested\n            if cleanup and not dry_run:\n                await self.cleanup_old_sessions(session_keys)\n            \n            self.print_migration_summary()\n            \n        except Exception as e:\n            logger.error(f\"Migration failed: {e}\")\n            raise\n    \n    def print_migration_summary(self):\n        \"\"\"Print migration statistics.\"\"\"\n        logger.info(\"\\n\" + \"=\"*50)\n        logger.info(\"MIGRATION SUMMARY\")\n        logger.info(\"=\"*50)\n        logger.info(f\"Total sessions found: {self.stats['total_sessions']}\")\n        logger.info(f\"Successfully migrated: {self.stats['migrated_sessions']}\")\n        logger.info(f\"Failed migrations: {self.stats['failed_migrations']}\")\n        logger.info(f\"Anonymous sessions: {self.stats['anonymous_sessions']}\")\n        logger.info(f\"User profiles created: {self.stats['user_profiles_created']}\")\n        \n        if self.stats['errors']:\n            logger.info(f\"\\nErrors encountered: {len(self.stats['errors'])}\")\n            for error in self.stats['errors'][:10]:  # Show first 10 errors\n                logger.info(f\"  - {error}\")\n            if len(self.stats['errors']) > 10:\n                logger.info(f\"  ... and {len(self.stats['errors']) - 10} more errors\")\n        \n        logger.info(\"=\"*50)\n\n\nasync def main():\n    \"\"\"Main migration function.\"\"\"\n    import argparse\n    \n    parser = argparse.ArgumentParser(description='Migrate HeyJarvis sessions to user-owned data')\n    parser.add_argument('--dry-run', action='store_true', help='Run in dry-run mode (no actual migration)')\n    parser.add_argument('--cleanup', action='store_true', help='Clean up old session keys after migration')\n    parser.add_argument('--redis-url', default=os.getenv('REDIS_URL', 'redis://localhost:6379'), help='Redis URL')\n    \n    args = parser.parse_args()\n    \n    migrator = SessionMigrator(args.redis_url)\n    \n    try:\n        await migrator.initialize()\n        await migrator.run_migration(dry_run=args.dry_run, cleanup=args.cleanup)\n    finally:\n        await migrator.close()\n\n\nif __name__ == \"__main__\":\n    asyncio.run(main())
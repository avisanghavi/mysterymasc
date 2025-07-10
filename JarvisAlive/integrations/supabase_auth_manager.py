#!/usr/bin/env python3
"""
Supabase Authentication Infrastructure for HeyJarvis
Secure storage and management of OAuth credentials and API keys
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum
import base64
from urllib.parse import urlencode, quote

from cryptography.fernet import Fernet
from supabase import create_client, Client
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ServiceType(Enum):
    """Supported OAuth service types"""
    GOOGLE = "google"
    HUBSPOT = "hubspot"
    LINKEDIN = "linkedin"
    API_KEY = "api_key"


@dataclass
class OAuthConfig:
    """OAuth configuration for a service"""
    client_id: str
    client_secret: str
    auth_url: str
    token_url: str
    scope: str
    redirect_uri: str


@dataclass
class StoredCredential:
    """Decrypted credential data"""
    service: str
    credential_type: str
    access_token: Optional[str]
    refresh_token: Optional[str]
    api_key: Optional[str]
    expires_at: Optional[datetime]
    metadata: Dict[str, Any]


class SupabaseAuthManager:
    """
    Manages authentication credentials with Supabase
    Features:
    - Secure encryption using Fernet
    - OAuth flow handling for multiple providers
    - Automatic token refresh
    - Comprehensive audit logging
    - Row Level Security support
    """
    
    def __init__(self, supabase_url: str, supabase_key: str, encryption_key: Optional[str] = None):
        """
        Initialize Supabase Auth Manager
        
        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase anon/service key
            encryption_key: Fernet encryption key (will generate if not provided)
        """
        self.supabase: Client = create_client(supabase_url, supabase_key)
        
        # Initialize or load encryption key
        if encryption_key:
            self.cipher_suite = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        else:
            # Generate new key (should be stored securely in production)
            key = Fernet.generate_key()
            self.cipher_suite = Fernet(key)
            logger.warning(f"Generated new encryption key: {key.decode()}. Store this securely!")
        
        # OAuth configurations
        self.oauth_configs = {
            ServiceType.GOOGLE: OAuthConfig(
                client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
                client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
                auth_url="https://accounts.google.com/o/oauth2/v2/auth",
                token_url="https://oauth2.googleapis.com/token",
                scope="https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/calendar",
                redirect_uri=os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8000/auth/callback")
            ),
            ServiceType.HUBSPOT: OAuthConfig(
                client_id=os.getenv("HUBSPOT_CLIENT_ID", ""),
                client_secret=os.getenv("HUBSPOT_CLIENT_SECRET", ""),
                auth_url="https://app.hubspot.com/oauth/authorize",
                token_url="https://api.hubapi.com/oauth/v1/token",
                scope="crm.objects.contacts.read crm.objects.contacts.write",
                redirect_uri=os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8000/auth/callback")
            ),
            ServiceType.LINKEDIN: OAuthConfig(
                client_id=os.getenv("LINKEDIN_CLIENT_ID", ""),
                client_secret=os.getenv("LINKEDIN_CLIENT_SECRET", ""),
                auth_url="https://www.linkedin.com/oauth/v2/authorization",
                token_url="https://www.linkedin.com/oauth/v2/accessToken",
                scope="r_liteprofile r_emailaddress w_member_social",
                redirect_uri=os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8000/auth/callback")
            )
        }
        
        # Request queue for retry logic
        self.retry_queue: List[Dict[str, Any]] = []
        self._retry_task = None
    
    async def initialize(self):
        """Initialize the auth manager and start background tasks"""
        # Start retry queue processor
        self._retry_task = asyncio.create_task(self._process_retry_queue())
        logger.info("SupabaseAuthManager initialized")
    
    async def close(self):
        """Clean up resources"""
        if self._retry_task:
            self._retry_task.cancel()
            try:
                await self._retry_task
            except asyncio.CancelledError:
                pass
    
    def _encrypt_data(self, data: Dict[str, Any]) -> str:
        """Encrypt sensitive data"""
        json_str = json.dumps(data)
        encrypted = self.cipher_suite.encrypt(json_str.encode())
        return base64.b64encode(encrypted).decode()
    
    def _decrypt_data(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt sensitive data"""
        try:
            decoded = base64.b64decode(encrypted_data.encode())
            decrypted = self.cipher_suite.decrypt(decoded)
            return json.loads(decrypted.decode())
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    async def store_oauth_credentials(
        self,
        user_id: str,
        service: ServiceType,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_in: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Store OAuth credentials securely
        
        Args:
            user_id: User identifier
            service: Service type (Google, HubSpot, LinkedIn)
            access_token: OAuth access token
            refresh_token: OAuth refresh token
            expires_in: Token expiration in seconds
            metadata: Additional metadata
            
        Returns:
            Success status
        """
        try:
            # Prepare credential data
            credential_data = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat() if expires_in else None,
                "metadata": metadata or {}
            }
            
            # Encrypt the data
            encrypted_data = self._encrypt_data(credential_data)
            
            # Store in Supabase
            data = {
                "user_id": user_id,
                "service": service.value,
                "credential_type": "oauth",
                "encrypted_data": encrypted_data,
                "expires_at": credential_data["expires_at"],
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Upsert credential
            result = self.supabase.table("user_credentials").upsert(
                data,
                on_conflict="user_id,service"
            ).execute()
            
            # Log audit event
            await self._log_audit_event(
                user_id=user_id,
                action="store_oauth_credentials",
                service=service.value,
                success=True
            )
            
            logger.info(f"Stored OAuth credentials for user {user_id}, service {service.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store OAuth credentials: {e}")
            await self._log_audit_event(
                user_id=user_id,
                action="store_oauth_credentials",
                service=service.value,
                success=False,
                error=str(e)
            )
            return False
    
    async def store_api_key(
        self,
        user_id: str,
        service: str,
        api_key: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Store API key securely
        
        Args:
            user_id: User identifier
            service: Service name
            api_key: API key to store
            metadata: Additional metadata
            
        Returns:
            Success status
        """
        try:
            # Prepare credential data
            credential_data = {
                "api_key": api_key,
                "metadata": metadata or {}
            }
            
            # Encrypt the data
            encrypted_data = self._encrypt_data(credential_data)
            
            # Store in Supabase
            data = {
                "user_id": user_id,
                "service": service,
                "credential_type": "api_key",
                "encrypted_data": encrypted_data,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Upsert credential
            result = self.supabase.table("user_credentials").upsert(
                data,
                on_conflict="user_id,service"
            ).execute()
            
            # Log audit event
            await self._log_audit_event(
                user_id=user_id,
                action="store_api_key",
                service=service,
                success=True
            )
            
            logger.info(f"Stored API key for user {user_id}, service {service}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store API key: {e}")
            await self._log_audit_event(
                user_id=user_id,
                action="store_api_key",
                service=service,
                success=False,
                error=str(e)
            )
            return False
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_credentials(
        self,
        user_id: str,
        service: str,
        auto_refresh: bool = True
    ) -> Optional[StoredCredential]:
        """
        Retrieve and decrypt credentials with auto-refresh
        
        Args:
            user_id: User identifier
            service: Service name
            auto_refresh: Automatically refresh expired OAuth tokens
            
        Returns:
            Decrypted credential or None
        """
        try:
            # Fetch from Supabase
            result = self.supabase.table("user_credentials").select("*").eq(
                "user_id", user_id
            ).eq(
                "service", service
            ).single().execute()
            
            if not result.data:
                logger.warning(f"No credentials found for user {user_id}, service {service}")
                return None
            
            # Decrypt data
            decrypted_data = self._decrypt_data(result.data["encrypted_data"])
            
            # Create credential object
            credential = StoredCredential(
                service=service,
                credential_type=result.data["credential_type"],
                access_token=decrypted_data.get("access_token"),
                refresh_token=decrypted_data.get("refresh_token"),
                api_key=decrypted_data.get("api_key"),
                expires_at=datetime.fromisoformat(result.data["expires_at"]) if result.data.get("expires_at") else None,
                metadata=decrypted_data.get("metadata", {})
            )
            
            # Check if OAuth token needs refresh
            if (
                auto_refresh and
                credential.credential_type == "oauth" and
                credential.expires_at and
                credential.expires_at <= datetime.utcnow() + timedelta(minutes=5)
            ):
                logger.info(f"Token expired or expiring soon, refreshing for user {user_id}, service {service}")
                
                # Try to refresh the token
                if credential.refresh_token and service in [s.value for s in ServiceType]:
                    new_credential = await self.refresh_oauth_token(
                        user_id=user_id,
                        service=ServiceType(service),
                        refresh_token=credential.refresh_token
                    )
                    if new_credential:
                        return new_credential
                    else:
                        # Add to retry queue
                        await self._add_to_retry_queue(
                            action="refresh_token",
                            user_id=user_id,
                            service=service,
                            data={"refresh_token": credential.refresh_token}
                        )
            
            # Track usage
            await self._track_usage(user_id=user_id, service=service, action="get_credentials")
            
            return credential
            
        except Exception as e:
            logger.error(f"Failed to get credentials: {e}")
            return None
    
    def initiate_oauth_flow(
        self,
        service: ServiceType,
        user_id: str,
        state: Optional[str] = None
    ) -> str:
        """
        Generate OAuth authorization URL
        
        Args:
            service: OAuth service type
            user_id: User identifier
            state: Optional state parameter for security
            
        Returns:
            Authorization URL
        """
        config = self.oauth_configs.get(service)
        if not config:
            raise ValueError(f"No OAuth configuration for service: {service}")
        
        # Generate state if not provided
        if not state:
            state = base64.b64encode(
                json.dumps({
                    "user_id": user_id,
                    "service": service.value,
                    "timestamp": datetime.utcnow().isoformat()
                }).encode()
            ).decode()
        
        # Build authorization URL
        params = {
            "client_id": config.client_id,
            "redirect_uri": config.redirect_uri,
            "response_type": "code",
            "scope": config.scope,
            "state": state,
            "access_type": "offline" if service == ServiceType.GOOGLE else None,
            "prompt": "consent" if service == ServiceType.GOOGLE else None
        }
        
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        
        auth_url = f"{config.auth_url}?{urlencode(params)}"
        
        logger.info(f"Generated OAuth URL for service {service.value}")
        return auth_url
    
    async def handle_oauth_callback(
        self,
        service: ServiceType,
        code: str,
        state: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Exchange authorization code for tokens
        
        Args:
            service: OAuth service type
            code: Authorization code
            state: State parameter for validation
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Decode and validate state
            state_data = json.loads(base64.b64decode(state.encode()).decode())
            user_id = state_data["user_id"]
            
            # Validate service matches
            if state_data["service"] != service.value:
                return False, "Service mismatch in state parameter"
            
            config = self.oauth_configs.get(service)
            if not config:
                return False, f"No OAuth configuration for service: {service}"
            
            # Exchange code for tokens
            async with aiohttp.ClientSession() as session:
                data = {
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": config.redirect_uri,
                    "client_id": config.client_id,
                    "client_secret": config.client_secret
                }
                
                async with session.post(config.token_url, data=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Token exchange failed: {error_text}")
                        return False, f"Token exchange failed: {response.status}"
                    
                    token_data = await response.json()
                    
                    # Store credentials
                    success = await self.store_oauth_credentials(
                        user_id=user_id,
                        service=service,
                        access_token=token_data["access_token"],
                        refresh_token=token_data.get("refresh_token"),
                        expires_in=token_data.get("expires_in"),
                        metadata={
                            "token_type": token_data.get("token_type", "Bearer"),
                            "scope": token_data.get("scope", config.scope)
                        }
                    )
                    
                    if success:
                        logger.info(f"Successfully exchanged code for tokens: {service.value}")
                        return True, None
                    else:
                        return False, "Failed to store credentials"
                        
        except Exception as e:
            logger.error(f"OAuth callback error: {e}")
            return False, str(e)
    
    async def refresh_oauth_token(
        self,
        user_id: str,
        service: ServiceType,
        refresh_token: str
    ) -> Optional[StoredCredential]:
        """
        Refresh expired OAuth token
        
        Args:
            user_id: User identifier
            service: OAuth service type
            refresh_token: Refresh token
            
        Returns:
            Updated credential or None
        """
        try:
            config = self.oauth_configs.get(service)
            if not config:
                logger.error(f"No OAuth configuration for service: {service}")
                return None
            
            # Refresh token
            async with aiohttp.ClientSession() as session:
                data = {
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": config.client_id,
                    "client_secret": config.client_secret
                }
                
                async with session.post(config.token_url, data=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Token refresh failed: {error_text}")
                        
                        # Add to retry queue
                        await self._add_to_retry_queue(
                            action="refresh_token",
                            user_id=user_id,
                            service=service.value,
                            data={"refresh_token": refresh_token}
                        )
                        return None
                    
                    token_data = await response.json()
                    
                    # Update stored credentials
                    success = await self.store_oauth_credentials(
                        user_id=user_id,
                        service=service,
                        access_token=token_data["access_token"],
                        refresh_token=token_data.get("refresh_token", refresh_token),
                        expires_in=token_data.get("expires_in"),
                        metadata={
                            "token_type": token_data.get("token_type", "Bearer"),
                            "scope": token_data.get("scope", config.scope),
                            "refreshed_at": datetime.utcnow().isoformat()
                        }
                    )
                    
                    if success:
                        # Return updated credential
                        return await self.get_credentials(user_id, service.value, auto_refresh=False)
                    
                    return None
                    
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            await self._add_to_retry_queue(
                action="refresh_token",
                user_id=user_id,
                service=service.value,
                data={"refresh_token": refresh_token},
                error=str(e)
            )
            return None
    
    async def _log_audit_event(
        self,
        user_id: str,
        action: str,
        service: str,
        success: bool,
        error: Optional[str] = None
    ):
        """Log security audit event"""
        try:
            audit_data = {
                "user_id": user_id,
                "action": action,
                "service": service,
                "success": success,
                "error": error,
                "ip_address": None,  # Would be set from request context
                "user_agent": None,  # Would be set from request context
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self.supabase.table("auth_audit_log").insert(audit_data).execute()
            
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
    
    async def _track_usage(self, user_id: str, service: str, action: str):
        """Track API usage"""
        try:
            # Increment usage counter
            self.supabase.rpc("increment_usage_counter", {
                "p_user_id": user_id,
                "p_service": service,
                "p_action": action
            }).execute()
            
        except Exception as e:
            logger.error(f"Failed to track usage: {e}")
    
    async def _add_to_retry_queue(
        self,
        action: str,
        user_id: str,
        service: str,
        data: Dict[str, Any],
        error: Optional[str] = None
    ):
        """Add failed request to retry queue"""
        retry_item = {
            "action": action,
            "user_id": user_id,
            "service": service,
            "data": data,
            "error": error,
            "attempts": 0,
            "created_at": datetime.utcnow(),
            "next_retry": datetime.utcnow() + timedelta(minutes=5)
        }
        
        self.retry_queue.append(retry_item)
        logger.info(f"Added {action} to retry queue for user {user_id}, service {service}")
    
    async def _process_retry_queue(self):
        """Background task to process retry queue"""
        while True:
            try:
                current_time = datetime.utcnow()
                
                # Process items ready for retry
                for item in self.retry_queue[:]:  # Copy list to avoid modification during iteration
                    if item["next_retry"] <= current_time and item["attempts"] < 3:
                        logger.info(f"Retrying {item['action']} for user {item['user_id']}")
                        
                        # Increment attempts
                        item["attempts"] += 1
                        
                        # Perform retry based on action
                        if item["action"] == "refresh_token":
                            result = await self.refresh_oauth_token(
                                user_id=item["user_id"],
                                service=ServiceType(item["service"]),
                                refresh_token=item["data"]["refresh_token"]
                            )
                            
                            if result:
                                # Success - remove from queue
                                self.retry_queue.remove(item)
                                logger.info(f"Retry successful for {item['action']}")
                            else:
                                # Failed - update next retry time
                                item["next_retry"] = current_time + timedelta(
                                    minutes=5 * (2 ** item["attempts"])  # Exponential backoff
                                )
                    
                    elif item["attempts"] >= 3:
                        # Max attempts reached - remove from queue
                        logger.error(f"Max retry attempts reached for {item['action']}, user {item['user_id']}")
                        self.retry_queue.remove(item)
                        
                        # Log permanent failure
                        await self._log_audit_event(
                            user_id=item["user_id"],
                            action=f"{item['action']}_max_retries",
                            service=item["service"],
                            success=False,
                            error="Maximum retry attempts reached"
                        )
                
                # Sleep before next iteration
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                logger.info("Retry queue processor cancelled")
                break
            except Exception as e:
                logger.error(f"Error in retry queue processor: {e}")
                await asyncio.sleep(60)
    
    async def revoke_credentials(self, user_id: str, service: str) -> bool:
        """
        Revoke stored credentials
        
        Args:
            user_id: User identifier
            service: Service name
            
        Returns:
            Success status
        """
        try:
            # Delete from database
            result = self.supabase.table("user_credentials").delete().eq(
                "user_id", user_id
            ).eq(
                "service", service
            ).execute()
            
            # Log audit event
            await self._log_audit_event(
                user_id=user_id,
                action="revoke_credentials",
                service=service,
                success=True
            )
            
            logger.info(f"Revoked credentials for user {user_id}, service {service}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke credentials: {e}")
            await self._log_audit_event(
                user_id=user_id,
                action="revoke_credentials",
                service=service,
                success=False,
                error=str(e)
            )
            return False
    
    async def list_user_services(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List all services with stored credentials for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            List of service information
        """
        try:
            result = self.supabase.table("user_credentials").select(
                "service", "credential_type", "expires_at", "updated_at"
            ).eq(
                "user_id", user_id
            ).execute()
            
            services = []
            for row in result.data:
                services.append({
                    "service": row["service"],
                    "type": row["credential_type"],
                    "expires_at": row.get("expires_at"),
                    "updated_at": row["updated_at"],
                    "is_expired": (
                        datetime.fromisoformat(row["expires_at"]) < datetime.utcnow()
                        if row.get("expires_at") else False
                    )
                })
            
            return services
            
        except Exception as e:
            logger.error(f"Failed to list user services: {e}")
            return []


# Example usage
async def main():
    """Example usage of SupabaseAuthManager"""
    
    # Initialize manager
    auth_manager = SupabaseAuthManager(
        supabase_url="https://your-project.supabase.co",
        supabase_key="your-anon-key",
        encryption_key="your-base64-encoded-fernet-key"
    )
    
    await auth_manager.initialize()
    
    try:
        # Example: Store API key
        await auth_manager.store_api_key(
            user_id="user123",
            service="openai",
            api_key="sk-xxxxxxxxxxxx",
            metadata={"tier": "pro"}
        )
        
        # Example: Initiate OAuth flow
        auth_url = auth_manager.initiate_oauth_flow(
            service=ServiceType.GOOGLE,
            user_id="user123"
        )
        print(f"OAuth URL: {auth_url}")
        
        # Example: Get credentials
        credential = await auth_manager.get_credentials(
            user_id="user123",
            service="openai"
        )
        if credential:
            print(f"Retrieved API key: {credential.api_key[:10]}...")
        
        # Example: List services
        services = await auth_manager.list_user_services("user123")
        print(f"User services: {services}")
        
    finally:
        await auth_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
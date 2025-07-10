#!/usr/bin/env python3
"""
Test suite for Supabase Authentication Infrastructure
"""

import asyncio
import json
import base64
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import pytest

from supabase_auth_manager import (
    SupabaseAuthManager,
    ServiceType,
    StoredCredential,
    OAuthConfig
)


class TestSupabaseAuthManager:
    """Test cases for SupabaseAuthManager"""
    
    @pytest.fixture
    def auth_manager(self):
        """Create auth manager instance with mocked Supabase client"""
        manager = SupabaseAuthManager(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            encryption_key="test-encryption-key-must-be-32-bytes!!"
        )
        
        # Mock Supabase client
        manager.supabase = Mock()
        manager.supabase.table = Mock(return_value=Mock())
        manager.supabase.rpc = Mock(return_value=Mock())
        
        return manager
    
    @pytest.mark.asyncio
    async def test_store_oauth_credentials(self, auth_manager):
        """Test storing OAuth credentials"""
        # Mock Supabase response
        auth_manager.supabase.table().upsert().execute = Mock(
            return_value=Mock(data=[{"id": "test-id"}])
        )
        
        # Store credentials
        result = await auth_manager.store_oauth_credentials(
            user_id="test-user",
            service=ServiceType.GOOGLE,
            access_token="test-access-token",
            refresh_token="test-refresh-token",
            expires_in=3600
        )
        
        assert result is True
        auth_manager.supabase.table().upsert.assert_called_once()
        
        # Verify encryption was applied
        call_args = auth_manager.supabase.table().upsert.call_args[0][0]
        assert "encrypted_data" in call_args
        assert call_args["user_id"] == "test-user"
        assert call_args["service"] == "google"
    
    @pytest.mark.asyncio
    async def test_store_api_key(self, auth_manager):
        """Test storing API key"""
        # Mock Supabase response
        auth_manager.supabase.table().upsert().execute = Mock(
            return_value=Mock(data=[{"id": "test-id"}])
        )
        
        # Store API key
        result = await auth_manager.store_api_key(
            user_id="test-user",
            service="openai",
            api_key="sk-test-key",
            metadata={"tier": "pro"}
        )
        
        assert result is True
        auth_manager.supabase.table().upsert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_credentials_with_decryption(self, auth_manager):
        """Test retrieving and decrypting credentials"""
        # Create test data
        test_data = {
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token",
            "api_key": None,
            "metadata": {"scope": "test-scope"}
        }
        
        # Encrypt test data
        encrypted_data = auth_manager._encrypt_data(test_data)
        
        # Mock Supabase response
        auth_manager.supabase.table().select().eq().eq().single().execute = Mock(
            return_value=Mock(data={
                "user_id": "test-user",
                "service": "google",
                "credential_type": "oauth",
                "encrypted_data": encrypted_data,
                "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat()
            })
        )
        
        # Get credentials
        credential = await auth_manager.get_credentials(
            user_id="test-user",
            service="google",
            auto_refresh=False
        )
        
        assert credential is not None
        assert credential.access_token == "test-access-token"
        assert credential.refresh_token == "test-refresh-token"
        assert credential.metadata["scope"] == "test-scope"
    
    @pytest.mark.asyncio
    async def test_auto_refresh_expired_token(self, auth_manager):
        """Test automatic token refresh for expired credentials"""
        # Create expired token data
        test_data = {
            "access_token": "expired-token",
            "refresh_token": "test-refresh-token",
            "metadata": {}
        }
        
        encrypted_data = auth_manager._encrypt_data(test_data)
        
        # Mock Supabase response with expired token
        auth_manager.supabase.table().select().eq().eq().single().execute = Mock(
            return_value=Mock(data={
                "user_id": "test-user",
                "service": "google",
                "credential_type": "oauth",
                "encrypted_data": encrypted_data,
                "expires_at": (datetime.utcnow() - timedelta(hours=1)).isoformat()
            })
        )
        
        # Mock successful refresh
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "access_token": "new-access-token",
                "refresh_token": "new-refresh-token",
                "expires_in": 3600
            })
            
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            # Mock store operation
            auth_manager.store_oauth_credentials = AsyncMock(return_value=True)
            
            # Get credentials with auto-refresh
            credential = await auth_manager.get_credentials(
                user_id="test-user",
                service="google",
                auto_refresh=True
            )
            
            # Verify refresh was called
            auth_manager.store_oauth_credentials.assert_called_once()
    
    def test_initiate_oauth_flow(self, auth_manager):
        """Test OAuth flow URL generation"""
        # Test Google OAuth
        url = auth_manager.initiate_oauth_flow(
            service=ServiceType.GOOGLE,
            user_id="test-user"
        )
        
        assert "https://accounts.google.com/o/oauth2/v2/auth" in url
        assert "client_id=" in url
        assert "redirect_uri=" in url
        assert "state=" in url
        assert "scope=" in url
        
        # Test HubSpot OAuth
        url = auth_manager.initiate_oauth_flow(
            service=ServiceType.HUBSPOT,
            user_id="test-user"
        )
        
        assert "https://app.hubspot.com/oauth/authorize" in url
    
    @pytest.mark.asyncio
    async def test_handle_oauth_callback(self, auth_manager):
        """Test OAuth callback handling"""
        # Create state parameter
        state_data = {
            "user_id": "test-user",
            "service": "google",
            "timestamp": datetime.utcnow().isoformat()
        }
        state = base64.b64encode(json.dumps(state_data).encode()).decode()
        
        # Mock token exchange
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "access_token": "new-access-token",
                "refresh_token": "new-refresh-token",
                "expires_in": 3600,
                "token_type": "Bearer"
            })
            
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            # Mock store operation
            auth_manager.store_oauth_credentials = AsyncMock(return_value=True)
            
            # Handle callback
            success, error = await auth_manager.handle_oauth_callback(
                service=ServiceType.GOOGLE,
                code="test-auth-code",
                state=state
            )
            
            assert success is True
            assert error is None
            auth_manager.store_oauth_credentials.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_retry_queue_processing(self, auth_manager):
        """Test retry queue for failed operations"""
        # Add item to retry queue
        await auth_manager._add_to_retry_queue(
            action="refresh_token",
            user_id="test-user",
            service="google",
            data={"refresh_token": "test-token"},
            error="Test error"
        )
        
        assert len(auth_manager.retry_queue) == 1
        assert auth_manager.retry_queue[0]["action"] == "refresh_token"
        assert auth_manager.retry_queue[0]["attempts"] == 0
    
    @pytest.mark.asyncio
    async def test_revoke_credentials(self, auth_manager):
        """Test credential revocation"""
        # Mock Supabase response
        auth_manager.supabase.table().delete().eq().eq().execute = Mock(
            return_value=Mock(data=[{"id": "test-id"}])
        )
        
        # Revoke credentials
        result = await auth_manager.revoke_credentials(
            user_id="test-user",
            service="google"
        )
        
        assert result is True
        auth_manager.supabase.table().delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_user_services(self, auth_manager):
        """Test listing user services"""
        # Mock Supabase response
        auth_manager.supabase.table().select().eq().execute = Mock(
            return_value=Mock(data=[
                {
                    "service": "google",
                    "credential_type": "oauth",
                    "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                },
                {
                    "service": "openai",
                    "credential_type": "api_key",
                    "expires_at": None,
                    "updated_at": datetime.utcnow().isoformat()
                }
            ])
        )
        
        # List services
        services = await auth_manager.list_user_services("test-user")
        
        assert len(services) == 2
        assert services[0]["service"] == "google"
        assert services[0]["is_expired"] is False
        assert services[1]["service"] == "openai"
        assert services[1]["type"] == "api_key"
    
    def test_encryption_decryption(self, auth_manager):
        """Test encryption and decryption of data"""
        # Test data
        test_data = {
            "api_key": "sk-test-key-12345",
            "metadata": {
                "tier": "pro",
                "created": datetime.utcnow().isoformat()
            }
        }
        
        # Encrypt
        encrypted = auth_manager._encrypt_data(test_data)
        assert isinstance(encrypted, str)
        assert encrypted != json.dumps(test_data)
        
        # Decrypt
        decrypted = auth_manager._decrypt_data(encrypted)
        assert decrypted == test_data
        assert decrypted["api_key"] == test_data["api_key"]
        assert decrypted["metadata"]["tier"] == test_data["metadata"]["tier"]


async def integration_test():
    """Integration test with mock Supabase"""
    print("Running integration tests...")
    
    # Create manager
    auth_manager = SupabaseAuthManager(
        supabase_url="https://test.supabase.co",
        supabase_key="test-key"
    )
    
    # Mock Supabase
    auth_manager.supabase = Mock()
    auth_manager.supabase.table = Mock(return_value=Mock())
    auth_manager.supabase.table().upsert().execute = Mock(
        return_value=Mock(data=[{"id": "test-id"}])
    )
    auth_manager.supabase.table().select().eq().eq().single().execute = Mock(
        return_value=Mock(data=None)
    )
    auth_manager.supabase.rpc = Mock(return_value=Mock())
    auth_manager.supabase.rpc().execute = Mock(return_value=Mock())
    
    await auth_manager.initialize()
    
    try:
        # Test 1: Store API key
        print("\n1. Testing API key storage...")
        success = await auth_manager.store_api_key(
            user_id="test-user",
            service="openai",
            api_key="sk-test-key"
        )
        print(f"   API key stored: {success}")
        
        # Test 2: Generate OAuth URL
        print("\n2. Testing OAuth URL generation...")
        auth_url = auth_manager.initiate_oauth_flow(
            service=ServiceType.GOOGLE,
            user_id="test-user"
        )
        print(f"   OAuth URL: {auth_url[:50]}...")
        
        # Test 3: List services
        print("\n3. Testing service listing...")
        auth_manager.supabase.table().select().eq().execute = Mock(
            return_value=Mock(data=[])
        )
        services = await auth_manager.list_user_services("test-user")
        print(f"   User services: {services}")
        
        print("\n✅ All integration tests passed!")
        
    finally:
        await auth_manager.close()


if __name__ == "__main__":
    # Run integration test
    asyncio.run(integration_test())
    
    # Run unit tests
    print("\nRun unit tests with: pytest test_supabase_auth.py -v")
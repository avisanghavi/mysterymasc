# Supabase Authentication Infrastructure

Complete authentication infrastructure for HeyJarvis with secure credential storage, OAuth flow handling, and comprehensive audit logging.

## Features

### 🔐 **Secure Credential Storage**
- **Fernet Encryption**: All sensitive data encrypted before storage
- **OAuth Token Management**: Store and auto-refresh OAuth tokens
- **API Key Storage**: Secure storage for service API keys
- **Row Level Security**: Users can only access their own credentials

### 🔄 **OAuth Flow Support**
- **Multiple Providers**: Google, HubSpot, LinkedIn
- **Complete Flow**: URL generation, callback handling, token exchange
- **Auto-Refresh**: Automatic token refresh with retry logic
- **State Validation**: Secure state parameter handling

### 📊 **Comprehensive Tracking**
- **Audit Logging**: All authentication events logged
- **Usage Tracking**: Monitor API usage per user/service
- **Error Handling**: Detailed error logging and retry queues
- **Rate Limiting**: Built-in usage tracking for rate limits

## Quick Start

### 1. Set up Supabase Tables

Run the SQL schema in your Supabase project:

```bash
# Execute supabase_schema.sql in your Supabase SQL editor
```

### 2. Configure Environment Variables

```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key

# OAuth Clients
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
HUBSPOT_CLIENT_ID=your-hubspot-client-id
HUBSPOT_CLIENT_SECRET=your-hubspot-client-secret
LINKEDIN_CLIENT_ID=your-linkedin-client-id
LINKEDIN_CLIENT_SECRET=your-linkedin-client-secret

# OAuth Redirect
OAUTH_REDIRECT_URI=http://localhost:8000/auth/callback
```

### 3. Initialize Auth Manager

```python
from supabase_auth_manager import SupabaseAuthManager, ServiceType

# Initialize
auth_manager = SupabaseAuthManager(
    supabase_url=os.getenv("SUPABASE_URL"),
    supabase_key=os.getenv("SUPABASE_KEY"),
    encryption_key=os.getenv("ENCRYPTION_KEY")  # Generate with Fernet.generate_key()
)

await auth_manager.initialize()
```

## Usage Examples

### Store API Key

```python
# Store an API key
success = await auth_manager.store_api_key(
    user_id="user123",
    service="openai",
    api_key="sk-xxxxxxxxxxxx",
    metadata={"tier": "pro", "org": "acme-corp"}
)
```

### OAuth Flow

```python
# 1. Generate authorization URL
auth_url = auth_manager.initiate_oauth_flow(
    service=ServiceType.GOOGLE,
    user_id="user123"
)
# Redirect user to auth_url

# 2. Handle callback
success, error = await auth_manager.handle_oauth_callback(
    service=ServiceType.GOOGLE,
    code=request.query_params["code"],
    state=request.query_params["state"]
)
```

### Retrieve Credentials

```python
# Get credentials with auto-refresh
credential = await auth_manager.get_credentials(
    user_id="user123",
    service="google",
    auto_refresh=True  # Automatically refresh expired tokens
)

if credential:
    if credential.credential_type == "oauth":
        headers = {"Authorization": f"Bearer {credential.access_token}"}
    else:
        headers = {"X-API-Key": credential.api_key}
```

### List User Services

```python
# Get all services for a user
services = await auth_manager.list_user_services("user123")
# Returns: [
#   {"service": "google", "type": "oauth", "is_expired": False},
#   {"service": "openai", "type": "api_key", "is_expired": False}
# ]
```

### Revoke Credentials

```python
# Revoke specific credentials
success = await auth_manager.revoke_credentials(
    user_id="user123",
    service="google"
)
```

## Security Features

### Encryption
- All credentials encrypted using Fernet symmetric encryption
- Encryption key should be stored securely (e.g., environment variable)
- Supports key rotation

### Row Level Security
- Users can only access their own credentials
- Service role required for administrative operations
- Audit logs accessible only to user and service role

### Audit Trail
- All authentication events logged
- Includes: timestamp, action, success/failure, error details
- IP address and user agent tracking (when available)

## Database Schema

### Tables
1. **user_credentials**: Encrypted credential storage
2. **service_configs**: OAuth configurations and metadata
3. **auth_audit_log**: Security audit trail
4. **usage_tracking**: API usage tracking

### Views
- **active_credentials**: Shows valid credentials with service info
- **usage_summary**: Aggregated usage statistics

## Retry Logic

Failed operations are automatically queued for retry:
- Token refresh failures
- API errors
- Network timeouts

Retry configuration:
- Max attempts: 3
- Exponential backoff
- Automatic cleanup after max attempts

## Testing

Run the test suite:

```bash
# Run integration tests
python test_supabase_auth.py

# Run unit tests with pytest
pytest test_supabase_auth.py -v
```

## Production Considerations

1. **Encryption Key Management**
   - Store encryption key securely
   - Implement key rotation strategy
   - Never commit keys to version control

2. **Rate Limiting**
   - Monitor usage_tracking table
   - Implement rate limiting based on service limits
   - Set up alerts for unusual activity

3. **Token Refresh**
   - Configure appropriate refresh windows
   - Monitor retry queue for persistent failures
   - Set up alerts for refresh failures

4. **Monitoring**
   - Set up alerts for authentication failures
   - Monitor audit logs for suspicious activity
   - Track usage patterns

## Error Handling

The system handles various error scenarios:
- Invalid credentials
- Expired tokens
- Network failures
- Rate limit exceeded
- OAuth flow errors

All errors are logged with context for debugging.

## Integration with HeyJarvis

```python
# In your HeyJarvis integration
async def make_api_call(user_id: str, service: str):
    # Get credentials
    credential = await auth_manager.get_credentials(user_id, service)
    
    if not credential:
        raise AuthenticationError("No credentials found")
    
    # Use credentials
    if service == "google":
        return await call_google_api(credential.access_token)
    elif service == "openai":
        return await call_openai_api(credential.api_key)
```

## License

Part of the HeyJarvis project.
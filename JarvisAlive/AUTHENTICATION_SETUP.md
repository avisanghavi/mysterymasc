# HeyJarvis Supabase Authentication Setup

This guide will help you set up Supabase authentication for the HeyJarvis system.

## Prerequisites

- Python 3.11+
- Redis server running
- Supabase account and project

## Supabase Setup

### 1. Create Supabase Project

1. Go to [supabase.com](https://supabase.com) and create a new project
2. Note down your project URL and anon key from the project settings

### 2. Configure Authentication

1. In your Supabase dashboard, go to **Authentication** → **Settings**
2. Enable **Email** provider
3. Configure email templates as needed
4. Set up your redirect URLs:
   - Add `http://localhost:8080` for local development
   - Add your production domain when deploying

### 3. Get JWT Secret

1. Go to **Settings** → **API**
2. Copy the **JWT Secret** (this is needed for token verification)

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your values:
   ```bash
   # Anthropic API Key
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   
   # Redis Configuration
   REDIS_URL=redis://localhost:6379
   
   # Supabase Configuration
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_ANON_KEY=your_supabase_anon_key_here
   SUPABASE_JWT_SECRET=your_supabase_jwt_secret_here
   
   # Frontend Configuration
   FRONTEND_URL=http://localhost:8080
   ```

### 3. Update Frontend Configuration

Edit `frontend-simple/index.html` and update the Supabase configuration:

```javascript
initializeSupabase() {
    const supabaseUrl = 'https://your-project.supabase.co';
    const supabaseKey = 'your_supabase_anon_key_here';
    
    if (supabaseUrl && supabaseKey) {
        this.supabase = supabase.createClient(supabaseUrl, supabaseKey);
        console.log('Supabase initialized');
    } else {
        console.warn('Supabase not configured - using demo mode');
    }
}
```

## Migration

### Migrate Existing Sessions

If you have existing Redis sessions, run the migration script:

```bash
# Dry run to see what would be migrated
python migrate_sessions.py --dry-run

# Run actual migration
python migrate_sessions.py

# Run migration with cleanup of old sessions
python migrate_sessions.py --cleanup
```

### Migration Options

- `--dry-run`: Shows what would be migrated without making changes
- `--cleanup`: Removes old session keys after migration
- `--redis-url`: Specify Redis URL (defaults to REDIS_URL env var)

## Running the Application

### 1. Start Redis Server

```bash
redis-server
```

### 2. Start the API Server

```bash
python api_server.py
```

The API will be available at `http://localhost:8000`

### 3. Serve the Frontend

For development, you can use a simple HTTP server:

```bash
cd frontend-simple
python -m http.server 8080
```

The frontend will be available at `http://localhost:8080`

## API Endpoints

### Authentication Endpoints

- `POST /auth/login` - Send magic link to email
- `POST /auth/callback` - Handle OAuth callback
- `POST /auth/logout` - Logout user
- `GET /auth/profile` - Get user profile
- `GET /auth/usage` - Get user usage statistics

### Agent Endpoints (Authenticated)

- `POST /agents/create` - Create new agent (requires auth)
- `GET /agents/session/{session_id}` - Get session agents (requires auth)
- `WebSocket /ws/{session_id}` - WebSocket connection (requires auth token)

## User Tiers and Limits

### Free Tier
- 5 agents maximum
- 1,000 requests per month
- 100 MB storage

### Premium Tier
- 25 agents maximum
- 10,000 requests per month
- 1 GB storage

### Enterprise Tier
- 100 agents maximum
- 50,000 requests per month
- 10 GB storage

## Security Features

### JWT Token Verification
- All authenticated endpoints verify JWT tokens
- Tokens are validated against Supabase JWT secret
- Automatic token refresh on frontend

### User Isolation
- Session IDs are prefixed with user ID
- Users can only access their own sessions and agents
- Redis data is isolated per user

### Rate Limiting
- API request quotas per user tier
- Agent creation limits
- Usage tracking and enforcement

## WebSocket Authentication

WebSocket connections require authentication:

1. Client connects to `/ws/{session_id}`
2. First message must contain `auth_token` field
3. Server validates token and associates connection with user
4. All subsequent messages are user-scoped

## Troubleshooting

### Common Issues

1. **"Authentication service not available"**
   - Check that SUPABASE_URL and SUPABASE_ANON_KEY are set
   - Verify Supabase project is accessible

2. **"Invalid token"**
   - Check that SUPABASE_JWT_SECRET is correct
   - Verify token hasn't expired

3. **"Quota exceeded"**
   - User has reached their usage limits
   - Check user tier and current usage

### Debug Mode

Enable debug mode in the frontend by pressing `Ctrl+D` to see detailed WebSocket messages.

### Logs

Check the server logs for detailed error information:

```bash
tail -f /var/log/heyjarvis/api.log
```

## Development

### Testing Authentication

1. Start the server in development mode
2. Open the frontend in your browser
3. Enter your email address
4. Check your email for the magic link
5. Click the link to authenticate

### Database Inspection

You can inspect the Redis database to see user sessions and data:

```bash
redis-cli
> KEYS user:*
> KEYS session:*
> KEYS usage:*
```

## Production Deployment

### Environment Variables

Ensure all environment variables are set in production:

```bash
export SUPABASE_URL=https://your-project.supabase.co
export SUPABASE_ANON_KEY=your_production_anon_key
export SUPABASE_JWT_SECRET=your_production_jwt_secret
export REDIS_URL=redis://your-redis-server:6379
export FRONTEND_URL=https://your-domain.com
```

### Security Considerations

1. Use HTTPS in production
2. Set up proper CORS policies
3. Configure rate limiting
4. Monitor usage and costs
5. Set up proper logging and monitoring

### Scaling

- Use Redis Cluster for high availability
- Consider database for persistent user data
- Implement caching for frequently accessed data
- Monitor memory usage and optimize as needed

## Support

For issues and questions:

1. Check the logs for error messages
2. Verify environment configuration
3. Test with a simple magic link authentication
4. Check Redis connectivity and data

## License

This authentication system is part of the HeyJarvis project.
# HeyJarvis Authentication - Quick Start Guide

🎉 **Authentication setup is complete!** Your HeyJarvis system now has full Supabase user authentication.

## ✅ What's Been Implemented

### 🔐 Authentication Features
- **Magic Link Login**: Users authenticate via email magic links
- **JWT Token Management**: Secure token validation and automatic refresh
- **User Isolation**: All sessions and agents are scoped to individual users
- **Usage Tracking**: Comprehensive monitoring of API requests, agents, and storage
- **Tiered Quotas**: Free, Premium, and Enterprise usage limits

### 🏗️ System Components
- **API Server**: Enhanced with auth endpoints and middleware
- **Frontend**: Supabase Auth UI with token management
- **User Profiles**: Complete user management with preferences and limits
- **Session Migration**: Tool to convert existing anonymous sessions
- **WebSocket Auth**: Authenticated real-time connections

## 🚀 How to Test Authentication

### 1. Start the Servers

Open two terminal windows:

**Terminal 1 - API Server:**
```bash
cd /Users/avisanghavi/Desktop/ProjectSpace_Jarvis/Jarvolution/Hey..J/JarvisAlive
python3 api_server.py
```

**Terminal 2 - Frontend:**
```bash
cd /Users/avisanghavi/Desktop/ProjectSpace_Jarvis/Jarvolution/Hey..J/JarvisAlive/frontend-simple
python3 -m http.server 8080
```

### 2. Open the Application

Open your browser and go to: `http://localhost:8080`

### 3. Test Authentication Flow

1. **Initial State**: You'll see the login form
2. **Enter Email**: Type your email address
3. **Click "Send Magic Link"**: Check your email for the magic link
4. **Click Magic Link**: You'll be redirected and automatically logged in
5. **Start Using**: Create agents and interact with the system

### 4. What You'll See

- **Before Auth**: Login form with email input
- **After Auth**: User profile in header + full HeyJarvis interface
- **User Isolation**: All your agents and sessions are private to your account
- **Usage Tracking**: Monitor your quota consumption

## 🔧 Configuration Details

### Environment Variables
Your `.env` file contains:
```
SUPABASE_URL=https://wgeoaufvulfpuknpgnnv.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOi...
FRONTEND_URL=http://localhost:8080
```

⚠️ **Important**: Add your `SUPABASE_JWT_SECRET` to the `.env` file:
```
SUPABASE_JWT_SECRET=your_jwt_secret_from_supabase_settings
```

### User Tiers and Limits

| Tier | Agents | Monthly Requests | Storage |
|------|--------|------------------|---------|
| Free | 5 | 1,000 | 100 MB |
| Premium | 25 | 10,000 | 1 GB |
| Enterprise | 100 | 50,000 | 10 GB |

## 🛠️ Development Tools

### Test Authentication Setup
```bash
python3 test_auth.py
```

### Migrate Existing Sessions
```bash
# Dry run to see what would be migrated
python3 migrate_sessions_fixed.py --dry-run

# Run actual migration
python3 migrate_sessions_fixed.py

# Run with cleanup
python3 migrate_sessions_fixed.py --cleanup
```

### Monitor Redis Data
```bash
redis-cli
> KEYS user:*
> KEYS session:*
> KEYS usage:*
> KEYS quota:*
```

## 🔍 API Endpoints

### Authentication
- `POST /auth/login` - Send magic link
- `POST /auth/callback` - Handle OAuth callback  
- `POST /auth/logout` - Logout user
- `GET /auth/profile` - Get user profile
- `GET /auth/usage` - Get usage statistics

### Agents (Authenticated)
- `POST /agents/create` - Create agent
- `GET /agents/session/{session_id}` - Get session agents
- `WebSocket /ws/{session_id}` - Real-time connection

## 🎯 Next Steps

### For Development
1. **Test the full flow** with your email
2. **Create some agents** to test user isolation
3. **Check usage tracking** via `/auth/usage` endpoint
4. **Test WebSocket connections** with authentication

### For Production
1. **Get JWT Secret** from Supabase settings
2. **Configure email templates** in Supabase dashboard
3. **Set up proper domains** in Supabase auth settings
4. **Deploy with HTTPS** for security
5. **Monitor usage** and costs

## 🐛 Troubleshooting

### Common Issues

**"Authentication service not available"**
- Check `SUPABASE_URL` and `SUPABASE_ANON_KEY` in `.env`
- Verify Supabase project is accessible

**"Invalid token"**
- Add `SUPABASE_JWT_SECRET` to `.env` file
- Get the JWT secret from Supabase Settings → API

**Magic link not working**
- Check email spam folder
- Verify `FRONTEND_URL` matches your browser URL
- Ensure Supabase redirect URLs are configured

**WebSocket connection fails**
- Check that auth token is being sent
- Verify token is valid and not expired

### Debug Mode
Press `Ctrl+D` in the frontend to enable debug mode and see detailed WebSocket messages.

## 📞 Support

If you encounter issues:

1. Run the test suite: `python3 test_auth.py`
2. Check server logs for error messages
3. Verify all environment variables are set
4. Test with a simple email authentication

---

🎉 **Congratulations!** Your HeyJarvis system now has enterprise-grade user authentication with Supabase integration!
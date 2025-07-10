-- Supabase Schema for HeyJarvis Authentication Infrastructure
-- This schema provides secure storage for credentials with Row Level Security

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create enum types
CREATE TYPE credential_type AS ENUM ('oauth', 'api_key');
CREATE TYPE service_type AS ENUM ('google', 'hubspot', 'linkedin', 'api_key');

-- User Credentials Table
-- Stores encrypted OAuth tokens and API keys
CREATE TABLE user_credentials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    service TEXT NOT NULL,
    credential_type credential_type NOT NULL,
    encrypted_data TEXT NOT NULL, -- Fernet encrypted JSON data
    expires_at TIMESTAMPTZ, -- For OAuth tokens
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure one credential per user per service
    CONSTRAINT unique_user_service UNIQUE(user_id, service)
);

-- Index for fast lookups
CREATE INDEX idx_user_credentials_user_id ON user_credentials(user_id);
CREATE INDEX idx_user_credentials_service ON user_credentials(service);
CREATE INDEX idx_user_credentials_expires ON user_credentials(expires_at) WHERE expires_at IS NOT NULL;

-- Service Configurations Table
-- Stores OAuth configurations and service metadata
CREATE TABLE service_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    oauth_enabled BOOLEAN DEFAULT FALSE,
    oauth_auth_url TEXT,
    oauth_token_url TEXT,
    oauth_scopes TEXT[], -- Array of required scopes
    required_fields JSONB, -- Required configuration fields
    rate_limits JSONB, -- Rate limiting configuration
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default service configurations
INSERT INTO service_configs (service, display_name, oauth_enabled, oauth_auth_url, oauth_token_url, oauth_scopes, required_fields, rate_limits) VALUES
    ('google', 'Google', TRUE, 
     'https://accounts.google.com/o/oauth2/v2/auth', 
     'https://oauth2.googleapis.com/token',
     ARRAY['https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/calendar'],
     '{"client_id": "required", "client_secret": "required"}'::JSONB,
     '{"requests_per_minute": 60, "requests_per_day": 10000}'::JSONB),
    
    ('hubspot', 'HubSpot', TRUE,
     'https://app.hubspot.com/oauth/authorize',
     'https://api.hubapi.com/oauth/v1/token',
     ARRAY['crm.objects.contacts.read', 'crm.objects.contacts.write'],
     '{"client_id": "required", "client_secret": "required"}'::JSONB,
     '{"requests_per_second": 10, "requests_per_day": 250000}'::JSONB),
    
    ('linkedin', 'LinkedIn', TRUE,
     'https://www.linkedin.com/oauth/v2/authorization',
     'https://www.linkedin.com/oauth/v2/accessToken',
     ARRAY['r_liteprofile', 'r_emailaddress', 'w_member_social'],
     '{"client_id": "required", "client_secret": "required"}'::JSONB,
     '{"requests_per_minute": 100, "requests_per_day": 100000}'::JSONB),
    
    ('openai', 'OpenAI', FALSE, NULL, NULL, NULL,
     '{"api_key": "required"}'::JSONB,
     '{"requests_per_minute": 3000, "tokens_per_minute": 90000}'::JSONB),
    
    ('anthropic', 'Anthropic', FALSE, NULL, NULL, NULL,
     '{"api_key": "required"}'::JSONB,
     '{"requests_per_minute": 50, "tokens_per_minute": 100000}'::JSONB);

-- Authentication Audit Log Table
-- Tracks all authentication-related events for security
CREATE TABLE auth_audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    action TEXT NOT NULL, -- e.g., 'store_oauth_credentials', 'refresh_token', 'revoke_credentials'
    service TEXT NOT NULL,
    success BOOLEAN NOT NULL,
    error TEXT,
    ip_address INET,
    user_agent TEXT,
    metadata JSONB, -- Additional context
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast queries
CREATE INDEX idx_auth_audit_user_id ON auth_audit_log(user_id);
CREATE INDEX idx_auth_audit_timestamp ON auth_audit_log(timestamp);
CREATE INDEX idx_auth_audit_action ON auth_audit_log(action);

-- Usage Tracking Table
-- Tracks API usage per user per service
CREATE TABLE usage_tracking (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    service TEXT NOT NULL,
    action TEXT NOT NULL, -- e.g., 'get_credentials', 'api_call'
    count INTEGER DEFAULT 1,
    metadata JSONB, -- Additional usage data
    date DATE DEFAULT CURRENT_DATE,
    hour INTEGER DEFAULT EXTRACT(HOUR FROM NOW()),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Composite key for efficient upserts
    CONSTRAINT unique_usage_tracking UNIQUE(user_id, service, action, date, hour)
);

-- Index for analytics queries
CREATE INDEX idx_usage_tracking_user_date ON usage_tracking(user_id, date);
CREATE INDEX idx_usage_tracking_service_date ON usage_tracking(service, date);

-- Create function to increment usage counter
CREATE OR REPLACE FUNCTION increment_usage_counter(
    p_user_id TEXT,
    p_service TEXT,
    p_action TEXT,
    p_metadata JSONB DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    INSERT INTO usage_tracking (user_id, service, action, metadata)
    VALUES (p_user_id, p_service, p_action, p_metadata)
    ON CONFLICT (user_id, service, action, date, hour)
    DO UPDATE SET 
        count = usage_tracking.count + 1,
        metadata = COALESCE(usage_tracking.metadata, '{}'::JSONB) || COALESCE(p_metadata, '{}'::JSONB);
END;
$$ LANGUAGE plpgsql;

-- Create function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for updated_at
CREATE TRIGGER update_user_credentials_updated_at BEFORE UPDATE ON user_credentials
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_service_configs_updated_at BEFORE UPDATE ON service_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS) Policies
-- Enable RLS on all tables
ALTER TABLE user_credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth_audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_tracking ENABLE ROW LEVEL SECURITY;
ALTER TABLE service_configs ENABLE ROW LEVEL SECURITY;

-- User Credentials Policies
-- Users can only access their own credentials
CREATE POLICY "Users can view own credentials" ON user_credentials
    FOR SELECT USING (auth.uid()::TEXT = user_id);

CREATE POLICY "Users can insert own credentials" ON user_credentials
    FOR INSERT WITH CHECK (auth.uid()::TEXT = user_id);

CREATE POLICY "Users can update own credentials" ON user_credentials
    FOR UPDATE USING (auth.uid()::TEXT = user_id);

CREATE POLICY "Users can delete own credentials" ON user_credentials
    FOR DELETE USING (auth.uid()::TEXT = user_id);

-- Service accounts can access all credentials (for backend operations)
CREATE POLICY "Service role can access all credentials" ON user_credentials
    FOR ALL USING (auth.role() = 'service_role');

-- Auth Audit Log Policies
-- Users can only view their own audit logs
CREATE POLICY "Users can view own audit logs" ON auth_audit_log
    FOR SELECT USING (auth.uid()::TEXT = user_id);

-- Only service role can insert audit logs
CREATE POLICY "Service role can insert audit logs" ON auth_audit_log
    FOR INSERT WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "Service role can view all audit logs" ON auth_audit_log
    FOR SELECT USING (auth.role() = 'service_role');

-- Usage Tracking Policies
-- Users can view their own usage
CREATE POLICY "Users can view own usage" ON usage_tracking
    FOR SELECT USING (auth.uid()::TEXT = user_id);

-- Service role can manage all usage data
CREATE POLICY "Service role can manage usage" ON usage_tracking
    FOR ALL USING (auth.role() = 'service_role');

-- Service Configs Policies
-- Everyone can read service configurations
CREATE POLICY "Public can read service configs" ON service_configs
    FOR SELECT USING (is_active = TRUE);

-- Only service role can modify service configs
CREATE POLICY "Service role can manage configs" ON service_configs
    FOR ALL USING (auth.role() = 'service_role');

-- Create views for common queries
-- View for active credentials with service info
CREATE VIEW active_credentials AS
SELECT 
    uc.user_id,
    uc.service,
    uc.credential_type,
    uc.expires_at,
    uc.updated_at,
    sc.display_name AS service_display_name,
    sc.oauth_enabled,
    CASE 
        WHEN uc.expires_at IS NULL THEN TRUE
        WHEN uc.expires_at > NOW() THEN TRUE
        ELSE FALSE
    END AS is_valid
FROM user_credentials uc
JOIN service_configs sc ON uc.service = sc.service
WHERE sc.is_active = TRUE;

-- View for usage summary
CREATE VIEW usage_summary AS
SELECT 
    user_id,
    service,
    date,
    SUM(count) AS total_requests,
    COUNT(DISTINCT action) AS unique_actions,
    MAX(created_at) AS last_activity
FROM usage_tracking
GROUP BY user_id, service, date;

-- Function to clean up expired tokens
CREATE OR REPLACE FUNCTION cleanup_expired_tokens()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM user_credentials
    WHERE credential_type = 'oauth'
    AND expires_at IS NOT NULL
    AND expires_at < NOW() - INTERVAL '30 days'
    AND refresh_token IS NULL;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create indexes for performance
CREATE INDEX idx_active_credentials_user_id ON user_credentials(user_id) WHERE expires_at IS NULL OR expires_at > NOW();
CREATE INDEX idx_usage_tracking_summary ON usage_tracking(user_id, service, date);

-- Grant necessary permissions
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT SELECT ON service_configs TO authenticated;
GRANT SELECT ON active_credentials TO authenticated;
GRANT SELECT ON usage_summary TO authenticated;

-- Comments for documentation
COMMENT ON TABLE user_credentials IS 'Stores encrypted OAuth tokens and API keys for users';
COMMENT ON TABLE service_configs IS 'Configuration for supported services and their OAuth settings';
COMMENT ON TABLE auth_audit_log IS 'Security audit trail for all authentication events';
COMMENT ON TABLE usage_tracking IS 'Tracks API usage per user per service for rate limiting and analytics';
COMMENT ON FUNCTION increment_usage_counter IS 'Atomically increments usage counter for a user/service/action combination';
COMMENT ON FUNCTION cleanup_expired_tokens IS 'Removes expired OAuth tokens that cannot be refreshed';
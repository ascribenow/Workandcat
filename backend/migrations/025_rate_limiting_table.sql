# Database migration for rate limiting system
CREATE TABLE rate_limiting_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ip_address INET NOT NULL,
    email VARCHAR(255),
    event_type VARCHAR(50) NOT NULL DEFAULT 'send_verification_code',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

# Indexes for efficient rate limiting queries
CREATE INDEX idx_rate_limiting_ip_email ON rate_limiting_events(ip_address, email, event_type);
CREATE INDEX idx_rate_limiting_expires_at ON rate_limiting_events(expires_at);
CREATE INDEX idx_rate_limiting_ip_created ON rate_limiting_events(ip_address, created_at DESC);

# Note: Cleanup will be handled in application code
# Database migration for verification codes
CREATE TABLE verification_codes (
    email VARCHAR(255) PRIMARY KEY,
    code VARCHAR(6) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    verified BOOLEAN DEFAULT FALSE,
    attempts INTEGER DEFAULT 0
);

# Index for cleanup efficiency
CREATE INDEX idx_verification_codes_expires_at ON verification_codes(expires_at);
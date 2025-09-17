-- Migration: Convert all timestamps from UTC to IST
-- This updates existing data to reflect IST timezone

-- Update users table
UPDATE users 
SET created_at = created_at + INTERVAL '5 hours 30 minutes'
WHERE created_at IS NOT NULL;

-- Update sessions table  
UPDATE sessions
SET created_at = created_at + INTERVAL '5 hours 30 minutes'
WHERE created_at IS NOT NULL;

-- Update attempt_events table
UPDATE attempt_events 
SET created_at = created_at + INTERVAL '5 hours 30 minutes'
WHERE created_at IS NOT NULL;

-- Update session_pack_plan table
UPDATE session_pack_plan
SET created_at = created_at + INTERVAL '5 hours 30 minutes',
    served_at = served_at + INTERVAL '5 hours 30 minutes'
WHERE created_at IS NOT NULL;

UPDATE session_pack_plan  
SET served_at = served_at + INTERVAL '5 hours 30 minutes'
WHERE served_at IS NOT NULL;

-- Update session_progress_tracking table
UPDATE session_progress_tracking
SET updated_at = updated_at + INTERVAL '5 hours 30 minutes'
WHERE updated_at IS NOT NULL;

-- Update subscriptions table
UPDATE subscriptions
SET created_at = created_at + INTERVAL '5 hours 30 minutes',
    updated_at = updated_at + INTERVAL '5 hours 30 minutes',
    current_period_start = current_period_start + INTERVAL '5 hours 30 minutes',
    current_period_end = current_period_end + INTERVAL '5 hours 30 minutes'
WHERE created_at IS NOT NULL;

UPDATE subscriptions  
SET paused_at = paused_at + INTERVAL '5 hours 30 minutes'
WHERE paused_at IS NOT NULL;

-- Update payment_orders table
UPDATE payment_orders
SET created_at = created_at + INTERVAL '5 hours 30 minutes',
    updated_at = updated_at + INTERVAL '5 hours 30 minutes'
WHERE created_at IS NOT NULL;

-- Update payment_transactions table
UPDATE payment_transactions
SET created_at = created_at + INTERVAL '5 hours 30 minutes'
WHERE created_at IS NOT NULL;

-- Update referral_usage table
UPDATE referral_usage
SET created_at = created_at + INTERVAL '5 hours 30 minutes'
WHERE created_at IS NOT NULL;

-- Update privileged_emails table
UPDATE privileged_emails
SET created_at = created_at + INTERVAL '5 hours 30 minutes'
WHERE created_at IS NOT NULL;

-- Add comment to track migration
COMMENT ON SCHEMA public IS 'Timestamps converted to IST (UTC+5:30) on migration 012';
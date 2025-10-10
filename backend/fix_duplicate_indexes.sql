-- Fix Duplicate Indexes identified by Supabase
-- These duplicates waste storage and slow down writes (INSERT, UPDATE, DELETE)
-- Safe to drop - keeping only one index from each duplicate set

-- CLEANUP COMPLETED ON: 2025-09-30
-- See: /app/backend/scripts/duplicate_index_cleanup_report.md for full details

-- ✅ SUCCESSFULLY REMOVED (2025-09-30):
-- These were actually duplicate UNIQUE CONSTRAINTS, not just indexes
-- 1. payment_orders: Drop unique_razorpay_order_id constraint
ALTER TABLE payment_orders DROP CONSTRAINT IF EXISTS unique_razorpay_order_id;

-- 2. payment_transactions: Drop unique_razorpay_payment_id constraint
ALTER TABLE payment_transactions DROP CONSTRAINT IF EXISTS unique_razorpay_payment_id;

-- 3. referral_usage: Drop unique_email_referral constraint
ALTER TABLE referral_usage DROP CONSTRAINT IF EXISTS unique_email_referral;

-- ✅ ALREADY REMOVED (Prior cleanup):
-- These indexes were not found in the database - already cleaned up
-- 4. attempt_events: idx_attempt_events_user_sess_seq - NOT FOUND
-- DROP INDEX IF EXISTS idx_attempt_events_user_sess_seq;

-- 5. questions: ix_questions_subcat_type - NOT FOUND
-- DROP INDEX IF EXISTS ix_questions_subcat_type;

-- 6. session_pack_plan: Both indexes - NOT FOUND
-- DROP INDEX IF EXISTS idx_session_pack_plan_user_session;
-- DROP INDEX IF EXISTS session_pack_plan_user_session_idx;

-- 7. session_progress_tracking: session_progress_user_session_idx - NOT FOUND
-- DROP INDEX IF EXISTS session_progress_user_session_idx;

-- 8. sessions: idx_sessions_user_sess_seq - NOT FOUND
-- DROP INDEX IF EXISTS idx_sessions_user_sess_seq;

-- 9. verification_codes: ix_verification_codes_email - NOT FOUND
-- DROP INDEX IF EXISTS ix_verification_codes_email;

-- Verification query: Check for remaining duplicate indexes
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

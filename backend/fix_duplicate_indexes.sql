-- Fix Duplicate Indexes identified by Supabase
-- These duplicates waste storage and slow down writes (INSERT, UPDATE, DELETE)
-- Safe to drop - keeping only one index from each duplicate set

-- 1. attempt_events: Keep idx_attempt_events_user_sess, drop idx_attempt_events_user_sess_seq
DROP INDEX IF EXISTS idx_attempt_events_user_sess_seq;

-- 2. payment_orders: Keep payment_orders_razorpay_order_id_key, drop unique_razorpay_order_id
DROP INDEX IF EXISTS unique_razorpay_order_id;

-- 3. payment_transactions: Keep payment_transactions_razorpay_payment_id_key, drop unique_razorpay_payment_id
DROP INDEX IF EXISTS unique_razorpay_payment_id;

-- 4. questions: Keep idx_questions_pair, drop ix_questions_subcat_type
DROP INDEX IF EXISTS ix_questions_subcat_type;

-- 5. referral_usage: Keep referral_usage_used_by_email_referral_code_key, drop unique_email_referral
DROP INDEX IF EXISTS unique_email_referral;

-- 6. session_pack_plan: Keep idx_pack_plan_user_sess, drop the other two
DROP INDEX IF EXISTS idx_session_pack_plan_user_session;
DROP INDEX IF EXISTS session_pack_plan_user_session_idx;

-- 7. session_progress_tracking: Keep idx_session_progress_user_session, drop session_progress_user_session_idx
DROP INDEX IF EXISTS session_progress_user_session_idx;

-- 8. sessions: Keep idx_sessions_user_seq, drop idx_sessions_user_sess_seq
DROP INDEX IF EXISTS idx_sessions_user_sess_seq;

-- 9. verification_codes: Keep idx_verification_codes_email, drop ix_verification_codes_email
DROP INDEX IF EXISTS ix_verification_codes_email;

-- Verification query: Check for remaining duplicate indexes
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

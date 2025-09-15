-- Daily Health Monitoring Queries for Twelvr V2 Production
-- Run these in cron for production monitoring

-- 1. Packs not served after 24 hours (should be minimal)
SELECT 'unserved_packs_24h' as metric, COUNT(*) as count,
       STRING_AGG(user_id::text, ', ') as affected_users
FROM session_pack_plan
WHERE served_at IS NULL 
  AND now() - created_at > interval '24 hours';

-- 2. Constraint drift detection (should be zero)  
SELECT 'constraint_violations' as metric, COUNT(*) as count,
       STRING_AGG(user_id::text || ':' || sess_seq::text, ', ') as affected_sessions
FROM session_pack_plan
WHERE (pack_json->'items' IS NULL OR jsonb_array_length(pack_json->'items') <> 12)
  AND created_at > now() - interval '7 days';

-- 3. Recent sessions with attempt tracking
SELECT 'session_health' as metric,
       spp.sess_seq,
       spp.status,
       spp.planner_fallback,
       spp.processing_time_ms,
       (SELECT count(*) FROM attempt_events a
        WHERE a.user_id = spp.user_id AND a.sess_seq_at_serve = spp.sess_seq) AS attempts,
       CASE 
         WHEN spp.completed_at IS NULL AND now() - spp.created_at > interval '2 hours' THEN 'stale'
         WHEN spp.completed_at IS NOT NULL THEN 'completed'
         ELSE 'active'
       END as session_health
FROM session_pack_plan spp
WHERE spp.created_at > now() - interval '2 days'
ORDER BY spp.created_at DESC
LIMIT 20;

-- 4. Performance metrics (p95 tracking)
SELECT 'performance_metrics' as metric,
       PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY processing_time_ms) as p95_planning_ms,
       AVG(processing_time_ms) as avg_planning_ms,
       COUNT(*) FILTER (WHERE planner_fallback = true) * 100.0 / COUNT(*) as fallback_rate_pct,
       COUNT(*) as total_sessions
FROM session_pack_plan
WHERE created_at > now() - interval '24 hours';

-- 5. Error rate monitoring
SELECT 'error_rates' as metric,
       COUNT(*) FILTER (WHERE status = 'planned' AND served_at IS NULL AND created_at < now() - interval '1 hour') as pack_miss_count,
       COUNT(*) FILTER (WHERE planner_fallback = true) as fallback_count,
       COUNT(*) as total_packs,
       (COUNT(*) FILTER (WHERE status = 'planned' AND served_at IS NULL AND created_at < now() - interval '1 hour') * 100.0 / NULLIF(COUNT(*), 0)) as pack_miss_rate_pct
FROM session_pack_plan
WHERE created_at > now() - interval '24 hours';

-- ALERT CONDITIONS (run with thresholds):
-- Alert if: p95 > 10000ms, fallback_rate > 5%, pack_miss_rate > 3%
-- Daily Health Monitoring Queries for Twelvr V2 Production
-- Run these in cron for production monitoring

-- 1. Packs not served after 24 hours (should be minimal)
SELECT 'unserved_packs_24h' as metric, COUNT(*) as count,
       STRING_AGG(user_id::text, ', ') as affected_users
FROM session_pack_plan
WHERE served_at IS NULL 
  AND now() - created_at > interval '24 hours';

-- 2. V2-CORRECTED: Constraint drift detection (should be zero)
SELECT 'constraint_violations' AS metric,
       COUNT(*) AS count,
       STRING_AGG(user_id::text || ':' || sess_seq::text, ', ') AS affected_sessions
FROM session_pack_plan
WHERE (pack_json IS NULL
       OR jsonb_typeof(pack_json) <> 'object'
       OR NOT (pack_json ? 'items')
       OR jsonb_array_length(pack_json->'items') <> 12)
  AND created_at > now() - interval '7 days';

-- 2b. 3/6/3 band shape (should be all OK)
SELECT 'band_shape_363' AS metric,
       COUNT(*) FILTER (WHERE
         (SELECT COUNT(*) FROM jsonb_array_elements(pack_json->'items') e WHERE e->>'bucket'='easy')   = 3 AND
         (SELECT COUNT(*) FROM jsonb_array_elements(pack_json->'items') e WHERE e->>'bucket'='medium') = 6 AND
         (SELECT COUNT(*) FROM jsonb_array_elements(pack_json->'items') e WHERE e->>'bucket'='hard')   = 3
       ) AS ok_count,
       COUNT(*) FILTER (WHERE
         (SELECT COUNT(*) FROM jsonb_array_elements(pack_json->'items') e WHERE e->>'bucket'='easy')   <> 3 OR
         (SELECT COUNT(*) FROM jsonb_array_elements(pack_json->'items') e WHERE e->>'bucket'='medium') <> 6 OR
         (SELECT COUNT(*) FROM jsonb_array_elements(pack_json->'items') e WHERE e->>'bucket'='hard')   <> 3
       ) AS violation_count
FROM session_pack_plan
WHERE created_at > now() - interval '7 days';

-- 2c. PYQ minima (≥2 with 1.5 and ≥2 with 1.0)
SELECT 'pyq_minima' AS metric,
       COUNT(*) FILTER (WHERE
         (SELECT COUNT(*) FROM jsonb_array_elements(pack_json->'items') e WHERE (e->>'pyq_frequency_score')::float >= 1.5) >= 2 AND
         (SELECT COUNT(*) FROM jsonb_array_elements(pack_json->'items') e WHERE (e->>'pyq_frequency_score')::float >= 1.0) >= 2
       ) AS ok_count,
       COUNT(*) FILTER (WHERE
         (SELECT COUNT(*) FROM jsonb_array_elements(pack_json->'items') e WHERE (e->>'pyq_frequency_score')::float >= 1.5) < 2 OR
         (SELECT COUNT(*) FROM jsonb_array_elements(pack_json->'items') e WHERE (e->>'pyq_frequency_score')::float >= 1.0) < 2
       ) AS violation_count
FROM session_pack_plan
WHERE created_at > now() - interval '7 days';

-- 2d. Idempotency integrity (should be zero)
SELECT 'duplicate_pack_rows' AS metric, user_id, sess_seq, COUNT(*) AS dup_count
FROM session_pack_plan
GROUP BY 1,2
HAVING COUNT(*) > 1;

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

-- 3b. Completed sessions have 12 attempts (exactly-once submit)
SELECT 'completion_attempts_mismatch' AS metric,
       COUNT(*) AS bad_count
FROM session_pack_plan spp
WHERE spp.completed_at IS NOT NULL
AND 12 <> (
  SELECT COUNT(*)
  FROM attempt_events a
  WHERE a.user_id = spp.user_id
    AND a.sess_seq_at_serve = spp.sess_seq
);

-- 4. Performance metrics (p95 tracking)
SELECT 'performance_metrics' as metric,
       PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY processing_time_ms) as p95_planning_ms,
       AVG(processing_time_ms) as avg_planning_ms,
       COUNT(*) FILTER (WHERE planner_fallback = true) * 100.0 / COUNT(*) as fallback_rate_pct,
       COUNT(*) as total_sessions
FROM session_pack_plan
WHERE created_at > now() - interval '24 hours';

-- 4b. Summarizer coverage for recently completed sessions
SELECT 'summarizer_coverage' AS metric,
       COUNT(*) FILTER (WHERE sslm.session_id IS NOT NULL)  AS with_summary,
       COUNT(*) FILTER (WHERE sslm.session_id IS NULL)      AS missing_summary
FROM session_pack_plan spp
LEFT JOIN session_summary_llm sslm
  ON sslm.user_id = spp.user_id AND sslm.sess_seq = spp.sess_seq
WHERE spp.completed_at > now() - interval '48 hours';

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
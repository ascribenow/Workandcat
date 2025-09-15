-- Production Ready Dashboard Monitoring Queries
-- Ready-to-run SQL for production monitoring

-- 1) Plan-Next latency & fallback
WITH base AS (
  SELECT processing_time_ms, COALESCE(planner_fallback,false) AS fb
  FROM session_pack_plan
  WHERE created_at > now() - interval '24 hours'
)
SELECT
  percentile_cont(0.50) WITHIN GROUP (ORDER BY processing_time_ms) AS p50_ms,
  percentile_cont(0.95) WITHIN GROUP (ORDER BY processing_time_ms) AS p95_ms,
  100.0*avg((fb)::int) AS fallback_rate_pct
FROM base;
-- Alert: p95 > 10,000 ms or fallback_rate > 5%

-- 2) Pack integrity (V2)
SELECT
  COUNT(*) FILTER (WHERE jsonb_typeof(pack_json)='object'
                   AND pack_json ? 'items'
                   AND jsonb_array_length(pack_json->'items')=12) AS packs_12,
  COUNT(*) FILTER (WHERE
      (SELECT COUNT(*) FROM jsonb_array_elements(pack_json->'items') e WHERE e->>'bucket'='easy')=3 AND
      (SELECT COUNT(*) FROM jsonb_array_elements(pack_json->'items') e WHERE e->>'bucket'='medium')=6 AND
      (SELECT COUNT(*) FROM jsonb_array_elements(pack_json->'items') e WHERE e->>'bucket'='hard')=3
  ) AS packs_363,
  COUNT(*) FILTER (WHERE
      (SELECT COUNT(*) FROM jsonb_array_elements(pack_json->'items') e WHERE (e->>'pyq_frequency_score')::float>=1.5)>=2 AND
      (SELECT COUNT(*) FROM jsonb_array_elements(pack_json->'items') e WHERE (e->>'pyq_frequency_score')::float>=1.0)>=2
  ) AS packs_meet_pyq
FROM session_pack_plan
WHERE created_at > now() - interval '7 days';
-- Alert: any count deviates from total packs created

-- 3) Resume/continuity health
SELECT COUNT(*) AS unserved_24h
FROM session_pack_plan
WHERE served_at IS NULL
  AND now()-created_at > interval '24 hours';
-- Alert: > 3

-- 4) Completion integrity (exactly 12 attempts)
SELECT COUNT(*) AS mismatches
FROM session_pack_plan spp
WHERE completed_at IS NOT NULL
AND 12 <> (
  SELECT COUNT(*)
  FROM attempt_events a
  WHERE a.user_id = spp.user_id AND a.sess_seq_at_serve = spp.sess_seq
);
-- Alert: mismatches > 0

-- 5) Idempotency integrity (should be zero duplicates)
SELECT user_id, sess_seq, COUNT(*) AS dup_count
FROM session_pack_plan
GROUP BY 1,2
HAVING COUNT(*) > 1;
-- Alert: any duplicates found

-- 6) Cost guard (planner/summarizer model & retries)
SELECT
  llm_model_used,
  SUM(COALESCE(retry_used,0)) AS retries,
  COUNT(*) AS sessions,
  100.0*SUM(COALESCE(retry_used,0))/COUNT(*) AS retry_rate_pct
FROM session_pack_plan
WHERE created_at > now()-interval '7 days'
GROUP BY 1 ORDER BY sessions DESC;
-- Alert: any model ≠ gpt-4o-mini; retry_rate > 5%
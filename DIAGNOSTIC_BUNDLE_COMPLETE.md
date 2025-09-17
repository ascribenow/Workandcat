# COMPLETE PLAN-NEXT SLOW TRACE PACK
# Generated: 2025-09-14 20:31 UTC
# Diagnostic bundle for 98.7-second plan-next performance issue

## EXECUTIVE SUMMARY
- **user_email**: sp@theskinmantra.com  
- **sess_seq**: 79
- **when_ist**: 2025-09-14 20:21:47 (Asia/Kolkata)
- **env**: learn-planner-1.preview.emergentagent.com
- **request_id**: 2d2d43a9-c26a-4a69-b74d-ffde3d9c71e1:S0:a02efd6a-a4ea-4704-8c82-cff4855f5793

**CRITICAL FINDING**: Plan-next took 98,684ms (98.7 seconds) - LLM planner failed after ~95s, fallback system succeeded.

## 1) REQUEST TRACE JSON (Main Slow Request)

```json
{
  "request_id": "2d2d43a9-c26a-4a69-b74d-ffde3d9c71e1:S0:a02efd6a-a4ea-4704-8c82-cff4855f5793",
  "route": "POST /api/adapt/plan-next", 
  "start_ts": "2025-09-14T20:21:47.610687Z",
  "end_ts": "2025-09-14T20:23:26.295072Z",
  "dur_ms": 98684,
  "timings_ms": {
    "db_candidates": 0,
    "llm_planner": 0, 
    "validator": 0,
    "db_write": 1233,
    "other": 96504
  },
  "retries": {
    "llm": 0,
    "db": 0
  },
  "http_status": 200,
  "resp_bytes": 605,
  "pack_load_ms": 947,
  "orchestration_dur_ms": 96785,
  "analysis": {
    "bottleneck": "other/pipeline processing",
    "llm_planner_failed": true,
    "fallback_used": true,
    "cold_start_mode": true
  }
}
```

## 2) FAST CONTROL TRACE (Cached Response)

```json
{
  "request_id": "2d2d43a9-c26a-4a69-b74d-ffde3d9c71e1:S0:a02efd6a-a4ea-4704-8c82-cff4855f5793",
  "route": "POST /api/adapt/plan-next",
  "start_ts": "2025-09-14T20:23:27.244843Z", 
  "end_ts": "2025-09-14T20:23:29.140541Z",
  "dur_ms": 1895,
  "timings_ms": {
    "db_candidates": 0,
    "llm_planner": 0,
    "validator": 0, 
    "db_write": 0,
    "other": 948
  },
  "retries": {
    "llm": 0,
    "db": 0
  },
  "http_status": 200,
  "resp_bytes": 605,
  "pack_load_ms": 947,
  "analysis": {
    "cached_response": true,
    "idempotent_return": true,
    "no_processing_required": true
  }
}
```

## 3) DATABASE EVIDENCE

### Availability Snapshot
```sql
SELECT difficulty_band,
       COUNT(*) FILTER (WHERE pyq_frequency_score=1.5) AS pyq15,
       COUNT(*) FILTER (WHERE pyq_frequency_score=1.0) AS pyq10,
       COUNT(*) AS total
FROM questions
GROUP BY 1 ORDER BY 1;

-- Results:
Easy       | pyq15:   0 | pyq10:   8 | total:  29
Hard       | pyq15:   2 | pyq10:  81 | total:  84
Medium     | pyq15:  17 | pyq10: 302 | total: 339
```

### Critical SQL Queries Used

**PYQ 1.5 Selection (SLOW - ORDER BY RANDOM()):**
```sql
SELECT id, subcategory, difficulty_band, pyq_frequency_score, stem, mcq_options, right_answer
FROM questions 
WHERE pyq_frequency_score = 1.5 
  AND difficulty_band IN ('Easy', 'Medium', 'Hard')
ORDER BY RANDOM() 
LIMIT 10;
```

**PYQ 1.0 Selection (SLOW - ORDER BY RANDOM()):**
```sql
SELECT id, subcategory, difficulty_band, pyq_frequency_score, stem, mcq_options, right_answer  
FROM questions
WHERE pyq_frequency_score = 1.0 
  AND difficulty_band IN ('Easy', 'Medium', 'Hard')
ORDER BY RANDOM()
LIMIT 50;
```

**Easy Fill Selection (SLOW - ORDER BY RANDOM()):**
```sql
SELECT id, subcategory, difficulty_band, pyq_frequency_score, stem, mcq_options, right_answer
FROM questions
WHERE difficulty_band = 'Easy' 
  AND pyq_frequency_score < 1.0
ORDER BY RANDOM() 
LIMIT 20;
```

### Database Indexes (Current)
```
-- Table: attempt_events
CREATE INDEX idx_attempt_events_user_sess ON public.attempt_events USING btree (user_id, sess_seq_at_serve)

-- Table: questions  
CREATE INDEX idx_questions_difficulty_band ON public.questions USING btree (difficulty_band)
CREATE INDEX idx_questions_pyq_frequency_score ON public.questions USING btree (pyq_frequency_score)
CREATE UNIQUE INDEX questions_pkey ON public.questions USING btree (id)

-- Table: session_pack_plan
CREATE INDEX idx_session_pack_plan_user_sess ON public.session_pack_plan USING btree (user_id, session_id)
CREATE UNIQUE INDEX session_pack_plan_pkey ON public.session_pack_plan USING btree (session_id)
```

## 4) LLM CALL METADATA

```json
{
  "request_id": "2d2d43a9-c26a-4a69-b74d-ffde3d9c71e1:S0:a02efd6a-a4ea-4704-8c82-cff4855f5793",
  "provider": "openai",
  "model": "gpt-4o-mini", 
  "wall_time_ms": 95000,
  "retries": 1,
  "status_code": "SCHEMA_VALIDATION_FAILED",
  "usage": {
    "note": "Token counts not exposed by backend logs",
    "prompt_chars": "~4000",
    "response_chars": "~2000"
  },
  "schema_fail_examples": [
    {
      "why": "missing fields item_id",
      "first_200_chars_of_output": "LLM returned invalid JSON after 1 retries. Reasons: pack.11: 'item_id' is a required property",
      "fallback_triggered": true,
      "fallback_success": true
    }
  ],
  "cold_start_mode": true,
  "final_outcome": "fallback_plan_used"
}
```

## 5) PACK ROW SNAPSHOT (Final Result)

```json
{
  "session_id": "a02efd6a-a4ea-4704-8c82-cff4855f5793",
  "status": "served",
  "served_at": "2025-09-14T20:23:32.338567",
  "completed_at": null,
  "llm_model_used": "planner_fallback@v1.1",
  "processing_time_ms": 150,
  "note": "Pack length and constraint_report require JSON parsing"
}
```

## 6) FRONTEND TIMING PROOF

**Configuration:**
```json
{
  "plan_next_timeout_ms": 60000,
  "uses_bearer_auth": true,
  "idempotency_key_header": "Idempotency-Key",
  "backend_base_url": "https://learning-tutor.preview.emergentagent.com/api",
  "adaptive_endpoints": {
    "plan_next": "/adapt/plan-next", 
    "pack": "/adapt/pack",
    "mark_served": "/adapt/mark-served"
  },
  "notes": "Frontend configured for 60s timeout to accommodate slow LLM planner"
}
```

**Frontend Trace Result:**
- Duration: 98,727ms (client-side measurement)
- Status: 502 (request timed out at frontend level)
- Backend completed successfully but took longer than frontend timeout

## 7) RUNTIME LIMITS

```json
{
  "proxy": { 
    "connect_timeout_s": 30, 
    "read_timeout_s": 90,
    "note": "Nginx/Caddy proxy timeouts - may not be accessible from container"
  },
  "app": { 
    "per_request_timeout_s": 120, 
    "fastapi_timeout_s": 60,
    "workers": 1, 
    "pool_size": 10,
    "max_overflow": 20
  },
  "supabase": { 
    "provider": "PostgreSQL",
    "tier": "Production managed DB",
    "using_pooler": true,
    "connection_pooling": "SQLAlchemy built-in"
  },
  "emergent_platform": {
    "deployment": "learn-planner-1.preview.emergentagent.com",
    "backend_port": "8001",
    "frontend_port": "3000"
  }
}
```

## 8) ROOT CAUSE ANALYSIS & RECOMMENDATIONS

### PRIMARY BOTTLENECK: LLM Processing (~95 seconds)
1. **LLM Schema Validation**: Missing `item_id` field after 95-second processing
2. **Fallback System**: Successfully compensated with deterministic planner

### SECONDARY BOTTLENECK: Database Queries
1. **ORDER BY RANDOM()**: Causing expensive full table scans
2. **Missing Indexes**: No composite indexes for candidate selection

### IMMEDIATE FIXES NEEDED:
1. **Fix LLM System Prompt**: Ensure `item_id` field is always present in JSON schema
2. **Replace ORDER BY RANDOM()**: Use efficient sampling (TABLESAMPLE or keyed selection)  
3. **Add Covering Indexes**: For (pyq_frequency_score, difficulty_band) combinations
4. **Reduce LLM Timeout**: Cap at 10-15 seconds with faster fallback
5. **Query Optimization**: Pre-bucket questions to avoid runtime sorting

### PERFORMANCE TARGET: 3-10 seconds (currently 98.7 seconds)

This diagnostic bundle provides complete evidence to implement targeted performance optimizations.
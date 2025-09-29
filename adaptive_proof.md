# Adaptive Proof - Technical Evidence for sp@theskinmantra.com

**User ID**: `2d2d43a9-c26a-4a69-b74d-ffde3d9c71e1`  
**Generated**: 2025-09-29  
**Status**: COMPREHENSIVE TECHNICAL VERIFICATION

---

## 1. Job Pipeline Proof (Last 48h)

### Overall Job Pipeline Status
```sql
SELECT job_type, status, COUNT(*)
FROM bg_jobs
WHERE created_at > NOW() - INTERVAL '2 days'
GROUP BY job_type, status
ORDER BY job_type, status;
```

### Your User-Specific Jobs (Last 20)
```sql
SELECT id, job_type, status, attempt_count, error_message,
       created_at, started_at, completed_at, session_id
FROM bg_jobs
WHERE user_id = '2d2d43a9-c26a-4a69-b74d-ffde3d9c71e1'
ORDER BY created_at DESC
LIMIT 20;
```

---

## 2. Adaptive Tables Changing

### Learner Notebook (Concept Mastery Tracking)
```sql
SELECT concept_norm, readiness, mastery_score, total_attempts, correct_attempts, last_seen_at
FROM learner_notebook
WHERE user_id = '2d2d43a9-c26a-4a69-b74d-ffde3d9c71e1'
ORDER BY last_seen_at DESC
LIMIT 30;
```

### Coverage Debt (Adaptive Focus Areas)  
```sql
SELECT subcategory, type_of_question, debt_score, debt_type, updated_at
FROM coverage_debt
WHERE user_id = '2d2d43a9-c26a-4a69-b74d-ffde3d9c71e1'
ORDER BY updated_at DESC
LIMIT 30;
```

---

## 3. Sessions + Attempts Verification

### Completed Sessions Count
```sql
SELECT COUNT(*) AS completed_sessions
FROM sessions
WHERE user_id = '2d2d43a9-c26a-4a69-b74d-ffde3d9c71e1' AND status='completed';
```

### Total Attempts Count
```sql
SELECT COUNT(*) AS attempts
FROM attempt_events
WHERE user_id = '2d2d43a9-c26a-4a69-b74d-ffde3d9c71e1';
```

---

## 4. Session Completion Job Enqueueing

### Recent Session Completions with Job Creation
```sql
SELECT s.session_id, s.completed_at, bj.job_type, bj.status, bj.created_at
FROM sessions s
LEFT JOIN bg_jobs bj ON (bj.session_id = s.session_id OR bj.user_id = s.user_id)
WHERE s.user_id = '2d2d43a9-c26a-4a69-b74d-ffde3d9c71e1' 
  AND s.status = 'completed'
  AND s.completed_at > NOW() - INTERVAL '7 days'
ORDER BY s.completed_at DESC, bj.created_at DESC
LIMIT 20;
```

---

## 5. Worker Status

### Background Worker Supervisor Status
```bash
supervisorctl status
```

### Active Job Processing
```sql
SELECT job_type, status, COUNT(*) as count
FROM bg_jobs
WHERE status IN ('queued', 'processing', 'completed')
  AND created_at > NOW() - INTERVAL '1 day'
GROUP BY job_type, status
ORDER BY job_type, status;
```

---

## 6. Next Session Pre-planned Adaptively

### Your Latest Sessions
```sql
SELECT session_id, status, created_at, completed_at
FROM sessions
WHERE user_id = '2d2d43a9-c26a-4a69-b74d-ffde3d9c71e1'
ORDER BY created_at DESC
LIMIT 2;
```

### Adaptive Question Selection in Recent Sessions
```sql
WITH latest_sessions AS (
  SELECT session_id
  FROM sessions
  WHERE user_id = '2d2d43a9-c26a-4a69-b74d-ffde3d9c71e1'
  ORDER BY created_at DESC
  LIMIT 2
)
SELECT spq.session_id, spq.position,
       spq.question_data->>'difficulty_band' AS band,
       spq.question_data->'core_concepts' AS concepts
FROM session_pack_questions spq
JOIN latest_sessions ls ON spq.session_id = ls.session_id
ORDER BY spq.session_id, spq.position;
```

---

## 7. Planner Uses Adaptive Signals

### Planner Decision Evidence
```sql
-- Check if planner considers learner_notebook data
SELECT ln.concept_norm, ln.readiness, ln.mastery_score,
       COUNT(spq.id) as times_selected_recently
FROM learner_notebook ln
LEFT JOIN session_pack_questions spq ON spq.question_data->'core_concepts' ? ln.concept_norm
LEFT JOIN sessions s ON s.session_id = spq.session_id
WHERE ln.user_id = '2d2d43a9-c26a-4a69-b74d-ffde3d9c71e1'
  AND (s.created_at > NOW() - INTERVAL '7 days' OR s.created_at IS NULL)
GROUP BY ln.concept_norm, ln.readiness, ln.mastery_score
ORDER BY ln.last_seen_at DESC
LIMIT 15;
```

---

## 8. Insight Caches Refresh

### Dashboard Insights Cache Status
```sql
SELECT last_updated_at, jsonb_typeof(all_time_insights) AS all_time_t,
       jsonb_typeof(recent_insights) AS recent_t
FROM user_dashboard_insights
WHERE user_id = '2d2d43a9-c26a-4a69-b74d-ffde3d9c71e1';
```

### Pre-Session Insights Cache Status
```sql
SELECT last_updated_at, jsonb_typeof(insight_card) AS card_t
FROM user_pre_session_insights
WHERE user_id = '2d2d43a9-c26a-4a69-b74d-ffde3d9c71e1';
```

---

## 9. No Stuck Duplicate Jobs

### Current Queued/Processing Jobs
```sql
SELECT id, job_type, status, session_id, created_at
FROM bg_jobs
WHERE user_id = '2d2d43a9-c26a-4a69-b74d-ffde3d9c71e1'
  AND status IN ('queued','processing')
ORDER BY created_at DESC
LIMIT 10;
```

---

## 10. Concrete Before→After Proof

### Most Recent Session Analysis
```sql
-- Get your most recent completed session
SELECT session_id, completed_at
FROM sessions
WHERE user_id = '2d2d43a9-c26a-4a69-b74d-ffde3d9c71e1'
  AND status = 'completed'
ORDER BY completed_at DESC
LIMIT 1;
```

### Adaptive State Changes (Before/After Session)
```sql
-- Learner notebook entries modified in last 48h (should show session impact)
SELECT concept_norm, readiness, mastery_score, total_attempts, correct_attempts, 
       last_seen_at, updated_at
FROM learner_notebook
WHERE user_id = '2d2d43a9-c26a-4a69-b74d-ffde3d9c71e1'
  AND updated_at > NOW() - INTERVAL '2 days'
ORDER BY updated_at DESC;
```

### Coverage Debt Evolution
```sql
-- Coverage debt changes in last 48h
SELECT subcategory, type_of_question, debt_score, debt_type, 
       updated_at, created_at
FROM coverage_debt
WHERE user_id = '2d2d43a9-c26a-4a69-b74d-ffde3d9c71e1'
  AND updated_at > NOW() - INTERVAL '2 days'
ORDER BY updated_at DESC;
```

---

**EXECUTION STATUS**: Running SQL queries...
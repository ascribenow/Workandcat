# Adaptive Learning Pipeline - Comprehensive Implementation Plan

**Date:** September 30, 2025  
**Status:** IN PROGRESS  
**Priority:** CRITICAL

---

## 📊 Current State Assessment (Truth Audit)

### Critical Findings

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| **Completed Sessions** | 11 | - | ✅ |
| **Sessions with Summaries** | 3 (27.3%) | 100% | 🚨 CRITICAL |
| **Orphaned Sessions** | 10 (90.9%) | 0% | 🚨 CRITICAL |
| **Concept Map Entries** | 3 concepts, 1 user | All sessions | 🚨 CRITICAL |
| **Session Progress Tracking** | 100% | 100% | ✅ |
| **Bad Jobs (NULL next_attempt)** | 0 | 0 | ✅ |
| **Type Consistency** | Mixed UUID/VARCHAR | Consistent | ⚠️ MEDIUM |
| **Job Success Rate (24h)** | 100% | 100% | ⚠️ FALSE POSITIVE |

### Root Cause: "Silent Success" Pattern

**Jobs report SUCCESS but don't write data** - This is the core issue identified in the architectural review.

**Why it happened:**
1. ✅ **FIXED 1hr ago**: Transaction aborts (duplicate keys, type mismatches)
2. ✅ **FIXED 1hr ago**: String format handling bug
3. 🚨 **ACTIVE**: No post-condition validation (jobs succeed even when writes fail)
4. 🚨 **ACTIVE**: 10 historical sessions need backfill

---

## 🎯 Implementation Strategy

### Phase 1: STOP THE BLEEDING (Hours 0-8)

**Goal:** Prevent future silent failures + backfill historical data

#### ✅ 1.1 Post-Conditions in SUMMARIZE_SESSION (DONE - 15 min ago)

**What was added:**
```python
# Verify session_summary_final exists
# Verify concept_alias_map_latest has concepts  
# Raise exception if verification fails → job will retry
```

#### 🔄 1.2 Post-Conditions in Other Handlers (NEXT - 30 min)

**Files:** `backend/services/simplified_job_handlers.py`

**Add to `handle_plan_next_session()`:**
```python
# POST-CONDITION: Verify session pack created
verify_pack = db.execute(text("""
    SELECT COUNT(*) FROM session_packs WHERE session_id = :pack_id
"""), {"pack_id": pack_id}).scalar()
if verify_pack == 0:
    raise Exception("POST-CONDITION FAILED: session_pack not created")
```

**Add to `handle_update_insights()`:**
```python
# POST-CONDITION: Verify insights cached
verify_cache = db.execute(text("""
    SELECT COUNT(*) FROM user_dashboard_insights 
    WHERE user_id = :user_id AND updated_at > :start_time
"""), {"user_id": user_id, "start_time": job_start}).scalar()
if verify_cache == 0:
    raise Exception("POST-CONDITION FAILED: insights not cached")
```

#### 🔄 1.3 Backfill Orphaned Sessions (CRITICAL - 2 hours)

**Create:** `backend/scripts/backfill_session_summaries.py`

**Purpose:** Re-process 10 sessions that were completed before fixes were applied

**Key features:**
- Finds completed sessions without summaries
- Re-enqueues SUMMARIZE_SESSION jobs
- Throttled (2 sec delay between jobs)
- Idempotent (can run multiple times)
- Progress tracking

**Run with:** `python3 /app/backend/scripts/backfill_session_summaries.py`

---

### Phase 2: DATA INTEGRITY (Hours 8-24)

#### 2.1 Type Standardization (2 hours)

**Problem:** Mixed UUID/VARCHAR types cause silent failures

**Current state:**
```
Table                      user_id type    session_id type
sessions                   uuid            varchar
bg_jobs                    varchar         varchar  
session_summary_final      varchar         varchar
concept_alias_map_latest   varchar         -
```

**Decision:** Standardize on VARCHAR with UUID format validation

**Why VARCHAR?**
- Less disruptive (bg_jobs already uses VARCHAR)
- Application-layer validation easier
- JSON serialization simpler

**Migration:** `backend/migrations/026_standardize_identifiers.sql`
```sql
-- Add CHECK constraints for UUID format
ALTER TABLE bg_jobs ADD CONSTRAINT check_user_id_uuid_format
CHECK (user_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$');

-- Repeat for other tables
```

#### 2.2 Foreign Key Constraints (1 hour)

**Add referential integrity:**
```sql
ALTER TABLE session_summary_final
ADD CONSTRAINT fk_summary_session
FOREIGN KEY (session_id) REFERENCES sessions(session_id::varchar)
ON DELETE CASCADE;
```

**Risk:** May fail if orphaned records exist → clean up first

---

### Phase 3: OBSERVABILITY (Hours 24-36)

#### 3.1 Health Metrics Infrastructure (2 hours)

**Create:** `backend/migrations/027_health_metrics.sql`

```sql
CREATE TABLE pipeline_health_metrics (
    metric_name VARCHAR(100) PRIMARY KEY,
    metric_value FLOAT,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB
);

-- Track key metrics
INSERT INTO pipeline_health_metrics VALUES
('summary_completion_rate', 0.0, NOW(), '{}'),
('orphaned_sessions_count', 0, NOW(), '{}'),
('concept_write_success_rate', 0.0, NOW(), '{}');
```

#### 3.2 Health Endpoint (2 hours)

**Create:** `backend/api/health.py`

```python
@app.get("/api/admin/pipeline-health")
async def get_pipeline_health():
    """Returns pipeline health dashboard"""
    return {
        "summary_completion_rate": "95.2%",
        "orphaned_sessions": 0,
        "job_success_rate_24h": "100%",
        "avg_summarize_latency_p95": "18.5s",
        "concept_map_growth": "+127 this week",
        "last_summary_timestamp": "2 minutes ago"
    }
```

#### 3.3 Outcome-Based SLIs (3 hours)

**Define and track:**

1. **Summary Completion SLI**
   - Metric: % of completed sessions with summaries within 5 minutes
   - Target: >95%
   - Alert: <90%

2. **Concept Write SLI**  
   - Metric: % of summaries with concepts that write to alias map
   - Target: >95%
   - Alert: <85%

3. **Job Latency SLI**
   - SUMMARIZE_SESSION P95: <30 seconds
   - PLAN_NEXT_SESSION P95: <10 seconds
   - UPDATE_INSIGHTS P95: <60 seconds

4. **Orphaned Session SLI**
   - Metric: Count of completed sessions without summaries
   - Target: <5
   - Alert: >10

**Implementation:** Update `bg_job_queue.py` to emit timing metrics

---

### Phase 4: PRODUCTION HARDENING (Hours 36-48)

#### 4.1 Configuration Centralization (2 hours)

**Create:** `backend/config/adaptive_learning_config.py`

**Centralize all hyperparameters:**
```python
class AdaptiveLearningConfig:
    # EMA for mastery scores
    EMA_ALPHA = 0.3
    
    # Debt decay
    DEBT_DECAY_RATE = 0.95
    DEBT_DECREASE_ON_PRACTICE = -0.1
    
    # Readiness thresholds
    WEAK_THRESHOLD = 0.4
    MODERATE_THRESHOLD = 0.7
    
    # Session pack config
    PACK_SIZE = 12
    DIFFICULTY_DISTRIBUTION = {"easy": 3, "medium": 6, "hard": 3}
    
    # Normalization (SINGLE SOURCE OF TRUTH)
    @staticmethod
    def normalize_concept(concept: str) -> str:
        return concept.lower().strip().replace(" ", "_")
```

**Add `config_version` to analytics tables for audit trail**

#### 4.2 Worker Deploy Hygiene (1 hour)

**Create:** `backend/scripts/deploy_workers.sh`

**Deployment checklist:**
1. Clear Python bytecode cache
2. Verify code changes (git diff)
3. Run health check
4. Rolling restart workers
5. Verify workers are processing
6. Monitor for 5 minutes

#### 4.3 Code Hash Verification (30 min)

**Add to worker startup:**
```python
import hashlib

def get_code_hash():
    files = ["services/simplified_job_handlers.py", "services/bg_job_queue.py"]
    hasher = hashlib.sha256()
    for f in files:
        with open(f, 'rb') as file:
            hasher.update(file.read())
    return hasher.hexdigest()

logger.info(f"Worker started with code hash: {get_code_hash()[:8]}")
```

---

## 📅 48-Hour Execution Timeline

### Day 1 (Hours 0-24)

| Time | Task | Owner | Status |
|------|------|-------|--------|
| 0-1h | Truth audit | ✅ | DONE |
| 1-2h | Add post-conditions to SUMMARIZE | ✅ | DONE |
| 2-3h | Add post-conditions to PLAN & UPDATE | 🔄 | IN PROGRESS |
| 3-4h | Create backfill script | 🔄 | NEXT |
| 4-8h | Run backfill (10 sessions) | ⏳ | PENDING |
| 8-12h | Type standardization migration | ⏳ | PENDING |
| 12-16h | Add foreign key constraints | ⏳ | PENDING |
| 16-20h | Test data integrity | ⏳ | PENDING |
| 20-24h | Deploy to production | ⏳ | PENDING |

### Day 2 (Hours 24-48)

| Time | Task | Owner | Status |
|------|------|-------|--------|
| 24-28h | Create health metrics table | ⏳ | PENDING |
| 28-32h | Implement health endpoint | ⏳ | PENDING |
| 32-36h | Add outcome SLIs | ⏳ | PENDING |
| 36-40h | Config centralization | ⏳ | PENDING |
| 40-44h | Worker deploy automation | ⏳ | PENDING |
| 44-48h | Final testing & docs | ⏳ | PENDING |

---

## ✅ Success Criteria

### After Phase 1 (8 hours):
- [ ] 0 orphaned sessions (currently 10)
- [ ] All handlers have post-condition checks
- [ ] Backfill script working

### After Phase 2 (24 hours):
- [ ] Type consistency across all tables
- [ ] Foreign key constraints enforced
- [ ] No data integrity violations

### After Phase 3 (36 hours):
- [ ] Health endpoint live at `/api/admin/pipeline-health`
- [ ] 4 SLIs tracked and alerting
- [ ] Metrics dashboard accessible

### After Phase 4 (48 hours):
- [ ] All config centralized
- [ ] Worker deployment automated
- [ ] Full observability stack operational

---

## 🚨 Risk Management

### Risk 1: Backfill Overwhelms Workers
**Probability:** Medium  
**Impact:** High  
**Mitigation:**
- Batch size: 10 sessions
- Delay: 2 seconds between jobs
- Monitor worker load during backfill

### Risk 2: Type Changes Break Existing Queries
**Probability:** Medium  
**Impact:** High  
**Mitigation:**
- Test with production data snapshot
- Keep old columns during transition period
- Add application-layer validation first

### Risk 3: Foreign Keys Fail on Orphaned Data
**Probability:** Low (after backfill)  
**Impact:** Medium  
**Mitigation:**
- Run backfill BEFORE adding foreign keys
- Clean up any remaining orphans
- Use ON DELETE CASCADE where appropriate

### Risk 4: Post-Conditions Cause Job Failures
**Probability:** High (initially)  
**Impact:** Low (desired behavior)  
**Mitigation:**
- This is GOOD - exposes real issues
- Monitor job failure rate
- Fix root causes as they surface

---

## 📊 Monitoring During Implementation

**Watch these metrics closely:**

1. **Worker Health**
   - CPU usage (should stay <70%)
   - Memory usage (should stay <80%)
   - Job processing rate

2. **Job Queue**
   - Queue depth (should stay <50)
   - Job success rate
   - Job latency percentiles

3. **Database**
   - Query performance (no slow queries >1s)
   - Connection pool usage
   - Lock contention

4. **Application**
   - API response times
   - Error rates
   - Session completion rates

---

## 🔄 Next Immediate Actions

**Right now (next 30 minutes):**
1. ✅ Review this implementation plan
2. 🔄 Get stakeholder approval for approach
3. 🔄 Begin Phase 1.2: Add post-conditions to remaining handlers
4. 🔄 Create backfill script

**After approval:**
5. Test backfill script with 1 session
6. Run full backfill for 10 orphaned sessions
7. Monitor results
8. Proceed to Phase 2

---

**Document Owner:** AI Development Team  
**Last Updated:** September 30, 2025 18:50 UTC  
**Next Review:** After Phase 1 completion (Hour 8)

# Stuck Running Jobs - Complete Solution

## Date: October 15, 2025
## Status: ✅ IMPLEMENTED & TESTED

---

## Problem Statement

Jobs can get stuck in "running" status if:
- **Worker crashes mid-processing**
- **Worker is forcefully killed** (SIGKILL)
- **Database connection is lost** during processing
- **Process hangs indefinitely** (deadlock, infinite loop)

This causes:
- ❌ Jobs never complete
- ❌ dedupe_key remains locked
- ❌ New jobs cannot be enqueued
- ❌ Manual intervention required

---

## Solution Overview

### Automatic Recovery System

1. **Detect:** Find jobs in "running" status for > 2 minutes
2. **Evaluate:** Check remaining attempts
3. **Action:**
   - If attempts < max_attempts: **Reset to "queued"** for retry
   - If attempts >= max_attempts: **Mark as "failed"** (exhausted)
4. **Periodic:** Run cleanup every 5 minutes automatically

---

## Implementation Details

### 1. Cleanup Method: `cleanup_stuck_running_jobs()`

**Location:** `/app/backend/services/bg_job_queue.py`

**Signature:**
```python
async def cleanup_stuck_running_jobs(
    self,
    timeout_minutes: int = 2
) -> Dict[str, int]:
    """
    Clean up jobs stuck in 'running' status for too long
    
    Returns:
        Dict with counts: {reset: int, failed: int}
    """
```

**Logic:**
```python
# Find stuck running jobs
SELECT id, job_type, user_id, attempts, max_attempts, started_at
FROM bg_jobs
WHERE status = 'running'
AND started_at < NOW() - INTERVAL '2 minutes'

For each stuck job:
    if attempts >= max_attempts:
        # Mark as failed (exhausted)
        UPDATE bg_jobs
        SET status = 'failed',
            completed_at = NOW(),
            error_message = 'Job stuck in running status...'
    else:
        # Reset to queued for retry
        backoff_minutes = min(2 ** attempts, 30)  # Exponential backoff
        UPDATE bg_jobs
        SET status = 'queued',
            started_at = NULL,
            next_attempt_at = NOW() + backoff_minutes,
            error_message = 'Reset from stuck running status'
```

**Features:**
- ✅ Exponential backoff (2, 4, 8, 16, 30 min)
- ✅ Preserves attempt count
- ✅ Logs detailed information
- ✅ Safe transaction handling

---

### 2. Periodic Cleanup Service

**Location:** `/app/backend/services/periodic_job_cleanup.py` (NEW)

**Features:**
- Runs every 5 minutes automatically
- Started on application startup
- Stopped on application shutdown
- Survives exceptions (continues running)

**Implementation:**
```python
class PeriodicJobCleanupService:
    def __init__(self):
        self.cleanup_interval = 300  # 5 minutes
    
    async def _cleanup_loop(self):
        while self.is_running:
            await asyncio.sleep(self.cleanup_interval)
            
            # Run cleanup
            result = await job_queue.cleanup_stuck_running_jobs(timeout_minutes=2)
            
            # Log results
            if result["reset"] > 0 or result["failed"] > 0:
                logger.info(f"Cleanup: {result['reset']} reset, {result['failed']} failed")
```

**Startup Integration:**
```python
# In server.py
@app.on_event("startup")
async def startup_event():
    from services.periodic_job_cleanup import periodic_cleanup_service
    await periodic_cleanup_service.start()
    logger.info("🧹 Periodic Job Cleanup: Service started")

@app.on_event("shutdown")
async def shutdown_event():
    from services.periodic_job_cleanup import periodic_cleanup_service
    await periodic_cleanup_service.stop()
    logger.info("⏹️ Periodic Job Cleanup: Service stopped")
```

---

## Test Results

### Test Suite: `/app/backend/scripts/test_stuck_running_jobs.py`

**Test 1: Cleanup Logic**

| Test Case | Attempts | Expected Action | Result |
|-----------|----------|----------------|--------|
| Job 1 | 2/6 | Reset to queued | ✅ PASSED |
| Job 2 | 6/6 | Mark as failed | ✅ PASSED |
| Job 3 | 5/6 | Reset to queued | ✅ PASSED |

**Output:**
```
🚨 Found 3 stuck running jobs (>2 min)
   ❌ Marked as FAILED: SUMMARIZE_SESSION (attempts: 6/6)
   🔄 Reset to QUEUED: SUMMARIZE_SESSION (attempts: 5/6, retry in 30 min)
   🔄 Reset to QUEUED: SUMMARIZE_SESSION (attempts: 2/6, retry in 4 min)

✅ Cleanup completed:
   Reset to queued: 2
   Marked as failed: 1
```

**Test 2: Interval Threshold**

| Test Case | Running Time | Expected Action | Result |
|-----------|--------------|----------------|--------|
| Job (1 min) | 1 minute | No action | ✅ PASSED |

**Output:**
```
✅ Cleanup completed:
   Reset to queued: 0
   Marked as failed: 0

✅ Job still in 'running' status (correctly not cleaned up)
```

---

## Configuration

### Timeouts

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **Stuck timeout** | 2 minutes | Normal jobs complete in < 30 seconds; 2 min is generous |
| **Cleanup interval** | 5 minutes | Balances responsiveness with system load |
| **Max backoff** | 30 minutes | Prevents excessive delays on repeated failures |

### Backoff Strategy

**Exponential backoff with cap:**
```
Attempt 1: 2 minutes
Attempt 2: 4 minutes
Attempt 3: 8 minutes
Attempt 4: 16 minutes
Attempt 5+: 30 minutes (capped)
```

This ensures:
- Quick retries for transient failures
- Slower retries for persistent issues
- Prevents overwhelming the system

---

## Behavior Examples

### Example 1: Worker Crash (Recoverable)

**Scenario:**
1. Worker starts processing SUMMARIZE_SESSION job
2. Worker crashes (SIGKILL) after 30 seconds
3. Job remains in "running" status

**Recovery:**
```
T+0:   Job starts (status: running, attempts: 1/6)
T+30s: Worker crashes
T+2m:  Periodic cleanup detects stuck job
T+2m:  Job reset to queued (attempts: 1/6, retry in 2 min)
T+4m:  Worker picks up job again
T+4m:  Job completes successfully
```

**Result:** ✅ Self-healed, no manual intervention

---

### Example 2: Persistent Failure (Exhausted)

**Scenario:**
1. Job keeps failing due to invalid data
2. Retried 6 times, all fail
3. Stuck on 6th attempt

**Recovery:**
```
T+0:    Job starts 6th attempt (status: running, attempts: 6/6)
T+30s:  Worker crashes or hangs
T+2m:   Periodic cleanup detects stuck job
T+2m:   Job marked as failed (attempts: 6/6)
        Error: "Job stuck in running status and exhausted all 6 attempts"
```

**Result:** ✅ Failed gracefully, dedupe_key released

---

### Example 3: Slow but Valid Processing

**Scenario:**
1. Job is processing a large dataset
2. Takes 1.5 minutes to complete
3. Still within timeout

**Recovery:**
```
T+0:     Job starts (status: running)
T+1.5m:  Still processing (< 2 min timeout)
T+1.5m:  Periodic cleanup runs, but job < 2 min old
T+1.5m:  No action taken (correctly)
T+1.8m:  Job completes successfully
```

**Result:** ✅ No interference with valid processing

---

## Monitoring & Logs

### Success Logs

**No stuck jobs:**
```
DEBUG: ✅ Periodic cleanup completed: No stuck jobs found
```

**Jobs cleaned:**
```
INFO: 🚨 Found 3 stuck running jobs (>2 min)
INFO:    ❌ Marked as FAILED: SUMMARIZE_SESSION (user: b223f5b0, attempts: 6/6)
INFO:    🔄 Reset to QUEUED: SUMMARIZE_SESSION (user: b223f5b0, attempts: 2/6, retry in 4 min)
INFO: 🧹 Stuck running jobs cleanup complete: 2 reset, 1 failed
```

### Error Logs

**Cleanup failure (non-fatal):**
```
ERROR: ❌ Failed to cleanup stuck running jobs: <error details>
```

**Periodic loop error:**
```
ERROR: ❌ Error in periodic cleanup loop: <error details>
```

---

## Database Queries for Monitoring

### Check for stuck running jobs:
```sql
SELECT job_type, COUNT(*) as stuck_count,
       MIN(started_at) as oldest_started,
       EXTRACT(EPOCH FROM (NOW() - MIN(started_at)))/60 AS minutes_stuck
FROM bg_jobs
WHERE status = 'running'
AND started_at < NOW() - INTERVAL '2 minutes'
GROUP BY job_type;
```

### View jobs that were reset:
```sql
SELECT job_type, user_id, attempts, max_attempts, error_message, created_at
FROM bg_jobs
WHERE status = 'queued'
AND error_message LIKE '%Reset from stuck running%'
ORDER BY created_at DESC
LIMIT 10;
```

### View jobs that were marked failed:
```sql
SELECT job_type, user_id, attempts, error_message, completed_at
FROM bg_jobs
WHERE status = 'failed'
AND error_message LIKE '%stuck in running status%'
ORDER BY completed_at DESC
LIMIT 10;
```

---

## Benefits

### Before Implementation:
- ❌ Stuck jobs require manual intervention
- ❌ dedupe_key remains locked indefinitely
- ❌ New jobs cannot be enqueued
- ❌ System requires monitoring and intervention

### After Implementation:
- ✅ Automatic recovery within 2-7 minutes
- ✅ dedupe_key automatically released
- ✅ New jobs can be enqueued
- ✅ System self-heals without intervention
- ✅ Failed jobs are properly marked (not lost)

---

## Edge Cases Handled

### 1. Race Condition: Job Completes During Cleanup
**Scenario:** Job completes at the same time cleanup runs

**Handling:**
- Cleanup queries for `status = 'running'`
- If job completes, status changes to 'succeeded'
- Cleanup UPDATE affects 0 rows
- No conflict

---

### 2. Worker Picks Up Job Right After Reset
**Scenario:** Job is reset to queued, worker immediately picks it up

**Handling:**
- Worker uses `FOR UPDATE SKIP LOCKED`
- Increments attempts counter
- Job processes normally
- No duplicate processing due to idempotency checks

---

### 3. Multiple Workers, Same Stuck Job
**Scenario:** Multiple cleanup processes run simultaneously

**Handling:**
- Each cleanup runs in separate transaction
- PostgreSQL serialization ensures only one UPDATE succeeds
- Other transactions see already-updated status
- No conflicts

---

### 4. Job Stuck at Max Attempts
**Scenario:** Job at 6/6 attempts gets stuck

**Handling:**
- Cleanup marks as 'failed' immediately
- dedupe_key is released
- New job with same dedupe_key can be created
- History is preserved (job not deleted)

---

## Complete Stuck Job Handling Matrix

| Job Status | Stuck Duration | Attempts | Action | Next Status | Next Attempt |
|------------|---------------|----------|--------|-------------|--------------|
| queued | > 2 min | Any | Delete | N/A | N/A |
| running | > 2 min | < max | Reset | queued | NOW + backoff |
| running | > 2 min | >= max | Fail | failed | N/A |
| running | < 2 min | Any | None | running | (no change) |
| succeeded | Any | Any | None | succeeded | (no change) |
| failed | Any | Any | None | failed | (no change) |

---

## Production Deployment

### Files Modified

1. **`/app/backend/services/bg_job_queue.py`**
   - Added `cleanup_stuck_running_jobs()` method

2. **`/app/backend/services/periodic_job_cleanup.py`** (NEW)
   - Periodic cleanup service

3. **`/app/backend/server.py`**
   - Integrated periodic cleanup into startup/shutdown

4. **`/app/backend/scripts/test_stuck_running_jobs.py`** (NEW)
   - Comprehensive test suite

### Deployment Checklist

- ✅ Code implemented and tested
- ✅ All tests passing (100%)
- ✅ Periodic service started on application startup
- ✅ Logging configured
- ✅ No breaking changes
- ✅ Backward compatible
- ✅ Documentation complete

---

## Rollback Plan

If issues arise, the feature can be disabled by:

1. **Stop periodic cleanup:**
   ```python
   # In server.py, comment out:
   await periodic_cleanup_service.start()
   ```

2. **Restart backend:**
   ```bash
   sudo supervisorctl restart backend
   ```

3. **Manual cleanup (if needed):**
   ```sql
   UPDATE bg_jobs
   SET status = 'queued', started_at = NULL
   WHERE status = 'running'
   AND started_at < NOW() - INTERVAL '10 minutes';
   ```

---

## Future Enhancements

### 1. Configurable Timeouts per Job Type
```python
STUCK_TIMEOUTS = {
    "SUMMARIZE_SESSION": 2,    # 2 minutes
    "PLAN_NEXT_SESSION": 5,    # 5 minutes (more complex)
    "UPDATE_INSIGHTS": 10       # 10 minutes (LLM calls)
}
```

### 2. Dead Letter Queue
Instead of marking as failed, move to separate table:
```sql
INSERT INTO dead_letter_queue (job_id, reason, payload)
SELECT id, 'stuck_running', ...
FROM bg_jobs
WHERE ...
```

### 3. Alerting
Send alerts when stuck job rate exceeds threshold:
```python
if result["reset"] + result["failed"] > 10:
    send_alert("High stuck job rate: investigate worker health")
```

### 4. Metrics Dashboard
- Stuck job count over time
- Reset vs failed ratio
- Average stuck duration
- Per-job-type breakdown

---

## Success Criteria

✅ **All Achieved:**
- Jobs stuck in "running" > 2 min are automatically cleaned
- Jobs with remaining attempts are reset to "queued"
- Jobs with exhausted attempts are marked as "failed"
- Cleanup runs every 5 minutes automatically
- System self-heals without manual intervention
- Idempotency prevents duplicate processing
- All tests passing (100%)

---

**Implementation Date:** October 15, 2025  
**Test Status:** ✅ ALL TESTS PASSED  
**Production Status:** ✅ DEPLOYED AND RUNNING  
**Monitoring:** Enabled via application logs

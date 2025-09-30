# DETAILED TECHNICAL IMPLEMENTATION PLAN
## Adaptive Learning Pipeline - Production Fixes

**Version:** 1.0  
**Date:** September 30, 2025  
**Estimated Duration:** 48 hours  
**Risk Level:** Medium-High

---

# PHASE 1: IMMEDIATE FIXES (Hours 0-8)

**Goal:** Stop silent failures and backfill historical data  
**Success Metric:** 0 orphaned sessions, all handlers validated

---

## Task 1.1: Post-Condition Validation - SUMMARIZE_SESSION ✅

**Status:** COMPLETED  
**Duration:** 30 minutes  
**File:** `backend/services/simplified_job_handlers.py`

### Implementation Details

**Code Added:**
```python
# POST-CONDITION: Verify critical writes actually happened
db.rollback()  # Close write transaction, start fresh read

# Verify session_summary_final exists
verify_summary = db.execute(text("""
    SELECT COUNT(*) FROM session_summary_final 
    WHERE user_id = :user_id AND session_id = :session_id
"""), {"user_id": user_id, "session_id": session_id}).scalar()

if verify_summary == 0:
    error_msg = f"POST-CONDITION FAILED: session_summary_final not written"
    logger.error(error_msg)
    raise Exception(error_msg)

# Verify concepts were written if concepts exist
if len(session_data.get("concept_alias_map_updated", [])) > 0:
    verify_concepts = db.execute(text("""
        SELECT COUNT(*) FROM concept_alias_map_latest 
        WHERE user_id = :user_id 
        AND first_seen_session_id = :session_id
    """), {"user_id": user_id, "session_id": session_id}).scalar()
    
    if verify_concepts == 0:
        error_msg = f"POST-CONDITION FAILED: No concepts written"
        logger.error(error_msg)
        raise Exception(error_msg)
```

**Testing:**
- ✅ Tested with manual job run
- ✅ Verified exceptions are raised on write failure
- ✅ Confirmed job retries on failure

---

## Task 1.2: Post-Condition Validation - PLAN_NEXT_SESSION

**Status:** PENDING  
**Duration:** 20 minutes  
**File:** `backend/services/simplified_job_handlers.py`

### Implementation Details

**Location:** After line ~370 in `handle_plan_next_session()`

**Code to Add:**
```python
async def handle_plan_next_session(job: Dict[str, Any]):
    """
    Handler for PLAN_NEXT_SESSION background jobs
    Generates personalized session pack based on user learning data
    """
    user_id = job.get("user_id")
    
    try:
        # Existing logic...
        pack_result = await generate_personalized_session_pack(user_id)
        pack_id = pack_result.get("pack_id")
        
        # Persist the pack
        await persist_session_pack(user_id, pack_id, pack_result)
        
        # ========== NEW: POST-CONDITION VALIDATION ==========
        # Verify the pack was actually written to database
        from database import get_db_session
        db = get_db_session()
        
        verify_pack = db.execute(text("""
            SELECT COUNT(*) FROM session_packs 
            WHERE session_id = :pack_id
        """), {"pack_id": pack_id}).scalar()
        
        if verify_pack == 0:
            error_msg = f"POST-CONDITION FAILED: session_pack not created for pack_id {pack_id[:8]}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        logger.info(f"✅ POST-CONDITION: Verified session pack {pack_id[:8]} exists in database")
        # ====================================================
        
        # Enqueue next job
        await job_queue.enqueue_job(
            job_type="UPDATE_INSIGHTS",
            user_id=user_id
        )
        
        return {"status": "success", "pack_id": pack_id}
        
    except Exception as e:
        logger.error(f"❌ PLAN_NEXT_SESSION failed: {e}")
        raise
```

**Testing Plan:**
```python
# Test script: backend/tests/test_plan_postcondition.py
import asyncio
from services.simplified_job_handlers import handle_plan_next_session

async def test_postcondition():
    job = {
        "id": "test-123",
        "user_id": "2d2d43a9-c26a-4a69-b74d-ffde3d9c71e1"
    }
    
    # Should succeed and create pack
    result = await handle_plan_next_session(job)
    assert result["status"] == "success"
    assert "pack_id" in result
    
    # Verify in database
    # ... verification logic
    
    print("✅ PLAN post-condition test passed")

asyncio.run(test_postcondition())
```

**Rollback:** Simply remove the post-condition block if issues arise

---

## Task 1.3: Post-Condition Validation - UPDATE_INSIGHTS

**Status:** PENDING  
**Duration:** 20 minutes  
**File:** `backend/services/simplified_job_handlers.py`

### Implementation Details

**Location:** After line ~320 in `handle_update_insights()`

**Code to Add:**
```python
async def handle_update_insights(job: Dict[str, Any]):
    """
    Handler for UPDATE_INSIGHTS background jobs
    Generates and caches adaptive insights for dashboard
    """
    user_id = job.get("user_id")
    job_start_time = datetime.now(timezone.utc)
    
    try:
        # Existing logic...
        user_data = await comprehensive_data_extractor.extract_complete_user_data(user_id)
        insights = await insight_generator_service.generate_comprehensive_insights(user_data)
        await insight_cache_service.store_comprehensive_insights(user_id, insights)
        
        # ========== NEW: POST-CONDITION VALIDATION ==========
        from database import get_db_session
        db = get_db_session()
        
        # Check if cache tables exist first
        table_exists = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'user_dashboard_insights'
            )
        """)).scalar()
        
        if table_exists:
            # Verify insights were cached
            verify_cache = db.execute(text("""
                SELECT COUNT(*) FROM user_dashboard_insights 
                WHERE user_id = :user_id 
                AND updated_at >= :job_start_time
            """), {
                "user_id": user_id, 
                "job_start_time": job_start_time
            }).scalar()
            
            if verify_cache == 0:
                error_msg = f"POST-CONDITION FAILED: insights not cached for user {user_id[:8]}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"✅ POST-CONDITION: Verified insights cached for user {user_id[:8]}")
        else:
            # Table doesn't exist yet - log warning but don't fail
            logger.warning(f"⚠️ user_dashboard_insights table not found - skipping cache verification")
        # ====================================================
        
        return {"status": "success", "insights_generated": True}
        
    except Exception as e:
        logger.error(f"❌ UPDATE_INSIGHTS failed: {e}")
        raise
```

**Testing Plan:**
```python
# Test script: backend/tests/test_insights_postcondition.py
import asyncio
from services.simplified_job_handlers import handle_update_insights

async def test_postcondition():
    job = {
        "id": "test-456",
        "user_id": "2d2d43a9-c26a-4a69-b74d-ffde3d9c71e1"
    }
    
    result = await handle_update_insights(job)
    assert result["status"] == "success"
    
    print("✅ UPDATE_INSIGHTS post-condition test passed")

asyncio.run(test_postcondition())
```

---

## Task 1.4: Create Backfill Script

**Status:** PENDING  
**Duration:** 1 hour  
**File:** `backend/scripts/backfill_session_summaries.py` (NEW)

### Implementation Details

**Full Script:**
```python
"""
Backfill script for orphaned sessions
Re-processes completed sessions that lack summaries

Usage:
    python3 backend/scripts/backfill_session_summaries.py --batch-size 10 --dry-run
    python3 backend/scripts/backfill_session_summaries.py --run
"""

import asyncio
import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.bg_job_queue import job_queue
from database import get_db_session
from sqlalchemy import text


class BackfillOrphanedSessions:
    """Backfill handler for sessions missing summaries"""
    
    def __init__(self, batch_size=10, delay_seconds=2, dry_run=False):
        self.batch_size = batch_size
        self.delay_seconds = delay_seconds
        self.dry_run = dry_run
        self.stats = {
            "found": 0,
            "enqueued": 0,
            "failed": 0,
            "skipped": 0
        }
    
    def find_orphaned_sessions(self):
        """
        Find completed sessions without summaries
        Returns: List of (session_id, user_id, created_at) tuples
        """
        db = get_db_session()
        
        result = db.execute(text("""
            SELECT 
                s.session_id, 
                s.user_id,
                s.created_at,
                s.questions_answered,
                s.questions_correct
            FROM sessions s
            WHERE s.status = 'completed'
            AND NOT EXISTS (
                SELECT 1 FROM session_summary_final ssf 
                WHERE ssf.session_id = s.session_id::varchar
                AND ssf.user_id = s.user_id::varchar
            )
            ORDER BY s.created_at ASC
            LIMIT :batch_size
        """), {"batch_size": self.batch_size}).fetchall()
        
        self.stats["found"] = len(result)
        return result
    
    async def enqueue_session(self, session_id, user_id):
        """
        Enqueue SUMMARIZE_SESSION job for a session
        Returns: job_id or None on failure
        """
        try:
            job_id = await job_queue.enqueue_job(
                job_type="SUMMARIZE_SESSION",
                user_id=str(user_id),
                session_id=str(session_id)
            )
            self.stats["enqueued"] += 1
            return job_id
        except Exception as e:
            self.stats["failed"] += 1
            print(f"  ❌ Failed to enqueue {session_id[:8]}: {e}")
            return None
    
    async def run_backfill(self):
        """
        Main backfill logic
        """
        print("=" * 80)
        print("BACKFILL ORPHANED SESSIONS")
        print("=" * 80)
        print(f"Batch size: {self.batch_size}")
        print(f"Delay: {self.delay_seconds}s between jobs")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE RUN'}")
        print("-" * 80)
        
        # Find orphaned sessions
        print("\n🔍 Finding orphaned sessions...")
        orphaned = self.find_orphaned_sessions()
        
        if not orphaned:
            print("✅ No orphaned sessions found!")
            return
        
        print(f"Found {len(orphaned)} orphaned sessions:\n")
        
        # Display sessions
        for idx, (session_id, user_id, created_at, answered, correct) in enumerate(orphaned, 1):
            print(f"{idx}. Session {session_id[:8]}...")
            print(f"   User: {user_id[:8]}...")
            print(f"   Created: {created_at}")
            print(f"   Questions: {answered} answered, {correct} correct")
        
        if self.dry_run:
            print("\n⚠️  DRY RUN - No jobs will be enqueued")
            print(f"Would enqueue {len(orphaned)} SUMMARIZE_SESSION jobs")
            return
        
        # Confirm
        print(f"\n⚠️  About to enqueue {len(orphaned)} jobs")
        confirm = input("Proceed? (yes/no): ")
        if confirm.lower() != 'yes':
            print("❌ Aborted by user")
            return
        
        # Enqueue jobs
        print(f"\n🚀 Enqueuing jobs with {self.delay_seconds}s throttle...\n")
        
        for idx, (session_id, user_id, created_at, _, _) in enumerate(orphaned, 1):
            job_id = await self.enqueue_session(session_id, user_id)
            
            if job_id:
                print(f"{idx}/{len(orphaned)} ✅ Session {session_id[:8]} → Job {job_id[:8]}")
            else:
                print(f"{idx}/{len(orphaned)} ❌ Session {session_id[:8]} → FAILED")
            
            # Throttle
            if idx < len(orphaned):
                await asyncio.sleep(self.delay_seconds)
        
        # Summary
        print("\n" + "=" * 80)
        print("BACKFILL COMPLETE")
        print("=" * 80)
        print(f"Found:    {self.stats['found']}")
        print(f"Enqueued: {self.stats['enqueued']}")
        print(f"Failed:   {self.stats['failed']}")
        print(f"Success:  {self.stats['enqueued']/self.stats['found']*100:.1f}%")
        print("\n💡 Monitor jobs at: bg_jobs table or worker logs")
        print("=" * 80)
    
    async def verify_backfill_results(self, wait_minutes=5):
        """
        Wait and verify that jobs completed successfully
        """
        print(f"\n⏳ Waiting {wait_minutes} minutes for jobs to process...")
        await asyncio.sleep(wait_minutes * 60)
        
        db = get_db_session()
        
        # Check remaining orphans
        remaining = db.execute(text("""
            SELECT COUNT(*) FROM sessions s
            WHERE s.status = 'completed'
            AND NOT EXISTS (
                SELECT 1 FROM session_summary_final ssf 
                WHERE ssf.session_id = s.session_id::varchar
            )
        """)).scalar()
        
        print(f"\n📊 Verification Results:")
        print(f"Remaining orphaned sessions: {remaining}")
        
        if remaining == 0:
            print("✅ ALL SESSIONS BACKFILLED SUCCESSFULLY!")
        else:
            print(f"⚠️  {remaining} sessions still orphaned - check job failures")


def main():
    parser = argparse.ArgumentParser(description='Backfill orphaned session summaries')
    parser.add_argument('--batch-size', type=int, default=10, help='Number of sessions to process')
    parser.add_argument('--delay', type=float, default=2.0, help='Delay between jobs (seconds)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without doing it')
    parser.add_argument('--verify', action='store_true', help='Wait and verify results after backfill')
    parser.add_argument('--verify-wait', type=int, default=5, help='Minutes to wait for verification')
    
    args = parser.parse_args()
    
    backfill = BackfillOrphanedSessions(
        batch_size=args.batch_size,
        delay_seconds=args.delay,
        dry_run=args.dry_run
    )
    
    # Run backfill
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(backfill.run_backfill())
    
    # Verify if requested
    if args.verify and not args.dry_run:
        loop.run_until_complete(backfill.verify_backfill_results(args.verify_wait))
    
    loop.close()


if __name__ == "__main__":
    main()
```

**Testing Plan:**
```bash
# 1. Dry run to see what would happen
cd /app/backend
python3 scripts/backfill_session_summaries.py --dry-run

# 2. Test with 1 session
python3 scripts/backfill_session_summaries.py --batch-size 1

# 3. Monitor job completion
tail -f /var/log/supervisor/bg_worker_1.out.log | grep SUMMARIZE

# 4. Check results
python3 << 'EOF'
import psycopg2
conn = psycopg2.connect("postgresql://...")
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM sessions WHERE status='completed' AND NOT EXISTS (SELECT 1 FROM session_summary_final ssf WHERE ssf.session_id = sessions.session_id::varchar)")
print(f"Remaining orphaned: {cursor.fetchone()[0]}")
cursor.close()
conn.close()
EOF

# 5. Full run with verification
python3 scripts/backfill_session_summaries.py --batch-size 10 --verify
```

**Rollback:** Delete enqueued jobs if issues arise
```sql
DELETE FROM bg_jobs 
WHERE job_type = 'SUMMARIZE_SESSION' 
AND status = 'queued'
AND created_at > NOW() - INTERVAL '10 minutes';
```

---

## Task 1.5: Execute Backfill

**Status:** PENDING  
**Duration:** 4 hours (includes monitoring)  
**Prerequisites:** Tasks 1.1, 1.2, 1.3, 1.4 complete

### Execution Plan

**Step 1: Pre-flight checks (15 min)**
```bash
# Check worker health
sudo supervisorctl status bg_workers:*

# Check job queue depth
psql $DATABASE_URL -c "SELECT COUNT(*) FROM bg_jobs WHERE status='queued';"

# Check database connections
psql $DATABASE_URL -c "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"

# Verify post-conditions are in place
grep -n "POST-CONDITION" /app/backend/services/simplified_job_handlers.py
```

**Step 2: Dry run (5 min)**
```bash
cd /app/backend
python3 scripts/backfill_session_summaries.py --dry-run --batch-size 10
# Review output, confirm 10 sessions would be processed
```

**Step 3: Test run with 1 session (15 min)**
```bash
python3 scripts/backfill_session_summaries.py --batch-size 1

# Monitor in another terminal
tail -f /var/log/supervisor/bg_worker_1.out.log | grep -E "(SUMMARIZE|POST-CONDITION)"

# Wait 2 minutes, then verify
psql $DATABASE_URL -c "
SELECT COUNT(*) as remaining_orphans
FROM sessions s
WHERE s.status = 'completed'
AND NOT EXISTS (
    SELECT 1 FROM session_summary_final ssf 
    WHERE ssf.session_id = s.session_id::varchar
);"
```

**Step 4: Full backfill (30 min)**
```bash
# Start monitoring dashboard in separate terminals

# Terminal 1: Worker logs
tail -f /var/log/supervisor/bg_worker_*.out.log | grep -E "(SUMMARIZE|POST-CONDITION|ERROR)"

# Terminal 2: Job status
watch -n 5 'psql $DATABASE_URL -c "SELECT job_type, status, COUNT(*) FROM bg_jobs WHERE created_at > NOW() - INTERVAL '\''1 hour'\'' GROUP BY job_type, status;"'

# Terminal 3: Run backfill
python3 scripts/backfill_session_summaries.py --batch-size 10 --verify --verify-wait 5
```

**Step 5: Verification (10 min)**
```bash
# Check orphaned sessions
psql $DATABASE_URL -c "
SELECT 
    COUNT(*) as total_completed,
    COUNT(CASE WHEN NOT EXISTS (SELECT 1 FROM session_summary_final ssf WHERE ssf.session_id = s.session_id::varchar) THEN 1 END) as orphaned,
    ROUND(100.0 * COUNT(CASE WHEN NOT EXISTS (SELECT 1 FROM session_summary_final ssf WHERE ssf.session_id = s.session_id::varchar) THEN 1 END) / COUNT(*), 1) as orphan_pct
FROM sessions s
WHERE s.status = 'completed';"

# Check concept map growth
psql $DATABASE_URL -c "
SELECT 
    COUNT(*) as total_concepts,
    COUNT(DISTINCT user_id) as users,
    MAX(last_updated) as latest_update
FROM concept_alias_map_latest;"

# Check job outcomes
psql $DATABASE_URL -c "
SELECT 
    job_type,
    status,
    COUNT(*) as count,
    AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_duration_sec
FROM bg_jobs
WHERE created_at > NOW() - INTERVAL '1 hour'
GROUP BY job_type, status
ORDER BY job_type, status;"
```

**Expected Results:**
- Orphaned sessions: 0 (down from 10)
- Concept map: 20-30 new concepts
- Job success rate: 100%
- All jobs complete in <30 seconds

**Rollback Plan:**
If backfill causes issues:
1. Stop new job processing: `sudo supervisorctl stop bg_workers:*`
2. Clear queued backfill jobs: `DELETE FROM bg_jobs WHERE job_type='SUMMARIZE_SESSION' AND status='queued' AND created_at > NOW() - INTERVAL '1 hour';`
3. Restart workers: `sudo supervisorctl start bg_workers:*`
4. Investigate issues in logs

---

## Phase 1 Completion Checklist

- [ ] Post-conditions added to all 3 handlers
- [ ] Backfill script created and tested
- [ ] Dry run completed successfully
- [ ] Test run (1 session) completed successfully
- [ ] Full backfill completed successfully
- [ ] Verification shows 0 orphaned sessions
- [ ] All workers healthy and processing normally
- [ ] No increase in error rates

**Success Criteria:**
- ✅ Orphaned sessions: 0
- ✅ All handlers have post-condition validation
- ✅ Backfill script reusable for future needs
- ✅ Job success rate: 100%

---

# PHASE 2: DATA INTEGRITY (Hours 8-24)

**Goal:** Fix type inconsistencies and add referential integrity  
**Success Metric:** Clean data model with FK constraints

---

## Task 2.1: Type Standardization Analysis

**Status:** PENDING  
**Duration:** 2 hours  
**Risk:** Medium

### Current State Analysis

**Database schema inspection:**
```sql
-- Check all identifier types
SELECT 
    table_name, 
    column_name, 
    data_type,
    udt_name
FROM information_schema.columns
WHERE column_name IN ('user_id', 'session_id')
AND table_schema = 'public'
ORDER BY table_name, column_name;
```

**Current state (from truth audit):**
```
Table                      user_id       session_id
sessions                   uuid          varchar
bg_jobs                    varchar       varchar
session_summary_final      varchar       varchar
concept_alias_map_latest   varchar       -
attempt_events             uuid          uuid
session_answers            uuid          uuid
users                      uuid          -
```

**Problems:**
1. Inconsistency between `sessions.user_id` (uuid) and `bg_jobs.user_id` (varchar)
2. Mix of uuid and varchar for session_id
3. No foreign key constraints
4. Type mismatches cause silent JOIN failures

### Decision: Standardize on VARCHAR with UUID Format Validation

**Rationale:**
1. **Less disruptive:** bg_jobs already uses VARCHAR
2. **JSON compatibility:** Easier serialization
3. **Flexibility:** Can handle edge cases
4. **Safety:** Add CHECK constraints for UUID format validation

**Alternative considered:** Standardize on UUID
- **Pros:** Type safety, smaller storage
- **Cons:** Requires migrating bg_jobs, complex casting everywhere
- **Decision:** Rejected due to disruption risk

### Implementation Strategy

**Option A: Add validation without changing types (RECOMMENDED)**
- Add CHECK constraints for UUID format
- Add explicit casts in application code
- Document type conversions
- **Risk:** Low
- **Duration:** 2 hours

**Option B: Migrate all to VARCHAR**
- Change uuid columns to varchar
- Update all application code
- **Risk:** High
- **Duration:** 8 hours

**Option C: Migrate all to UUID**
- Change varchar columns to uuid
- Update bg_jobs table schema
- **Risk:** Very High
- **Duration:** 12 hours

**RECOMMENDATION: Option A**

---

## Task 2.2: Add UUID Format Validation

**Status:** PENDING  
**Duration:** 1 hour  
**File:** `backend/migrations/026_add_uuid_validation.sql` (NEW)

### Implementation Details

**Migration Script:**
```sql
-- Migration: Add UUID format validation to identifier columns
-- This ensures data quality without changing column types

-- 1. Add UUID format validation function
CREATE OR REPLACE FUNCTION is_valid_uuid(value TEXT) 
RETURNS BOOLEAN AS $$
BEGIN
    RETURN value ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- 2. Add CHECK constraints to bg_jobs
ALTER TABLE bg_jobs 
ADD CONSTRAINT check_bg_jobs_user_id_uuid_format
CHECK (is_valid_uuid(user_id));

ALTER TABLE bg_jobs 
ADD CONSTRAINT check_bg_jobs_session_id_uuid_format
CHECK (session_id IS NULL OR is_valid_uuid(session_id));

-- 3. Add CHECK constraints to session_summary_final
ALTER TABLE session_summary_final
ADD CONSTRAINT check_summary_user_id_uuid_format
CHECK (is_valid_uuid(user_id));

ALTER TABLE session_summary_final
ADD CONSTRAINT check_summary_session_id_uuid_format
CHECK (is_valid_uuid(session_id));

-- 4. Add CHECK constraints to concept_alias_map_latest
ALTER TABLE concept_alias_map_latest
ADD CONSTRAINT check_concept_user_id_uuid_format
CHECK (is_valid_uuid(user_id));

-- 5. Verify all existing data passes validation
DO $$
DECLARE
    invalid_count INTEGER;
BEGIN
    -- Check bg_jobs
    SELECT COUNT(*) INTO invalid_count
    FROM bg_jobs
    WHERE NOT is_valid_uuid(user_id)
    OR (session_id IS NOT NULL AND NOT is_valid_uuid(session_id));
    
    IF invalid_count > 0 THEN
        RAISE EXCEPTION 'Found % invalid UUIDs in bg_jobs', invalid_count;
    END IF;
    
    -- Check session_summary_final
    SELECT COUNT(*) INTO invalid_count
    FROM session_summary_final
    WHERE NOT is_valid_uuid(user_id)
    OR NOT is_valid_uuid(session_id);
    
    IF invalid_count > 0 THEN
        RAISE EXCEPTION 'Found % invalid UUIDs in session_summary_final', invalid_count;
    END IF;
    
    RAISE NOTICE 'All UUID validations passed';
END $$;

-- 6. Add comments for documentation
COMMENT ON CONSTRAINT check_bg_jobs_user_id_uuid_format ON bg_jobs 
IS 'Ensures user_id is valid UUID format (varchar stored as UUID string)';

COMMENT ON CONSTRAINT check_summary_user_id_uuid_format ON session_summary_final
IS 'Ensures user_id is valid UUID format for foreign key compatibility';
```

**Rollback Script:**
```sql
-- Rollback: Remove UUID validation constraints

ALTER TABLE bg_jobs DROP CONSTRAINT IF EXISTS check_bg_jobs_user_id_uuid_format;
ALTER TABLE bg_jobs DROP CONSTRAINT IF EXISTS check_bg_jobs_session_id_uuid_format;
ALTER TABLE session_summary_final DROP CONSTRAINT IF EXISTS check_summary_user_id_uuid_format;
ALTER TABLE session_summary_final DROP CONSTRAINT IF EXISTS check_summary_session_id_uuid_format;
ALTER TABLE concept_alias_map_latest DROP CONSTRAINT IF EXISTS check_concept_user_id_uuid_format;

DROP FUNCTION IF EXISTS is_valid_uuid(TEXT);
```

**Testing:**
```bash
# 1. Apply migration
psql $DATABASE_URL -f backend/migrations/026_add_uuid_validation.sql

# 2. Test with valid UUID
psql $DATABASE_URL << 'EOF'
-- Should succeed
INSERT INTO bg_jobs (id, job_type, user_id, status, next_attempt_at)
VALUES (
    gen_random_uuid()::text,
    'TEST_JOB',
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    'queued',
    NOW()
);

-- Should fail
INSERT INTO bg_jobs (id, job_type, user_id, status, next_attempt_at)
VALUES (
    gen_random_uuid()::text,
    'TEST_JOB',
    'invalid-uuid',
    'queued',
    NOW()
);
-- Expected: ERROR: check constraint violated

-- Cleanup
DELETE FROM bg_jobs WHERE job_type = 'TEST_JOB';
EOF

# 3. Verify constraints exist
psql $DATABASE_URL -c "
SELECT 
    conname as constraint_name,
    conrelid::regclass as table_name
FROM pg_constraint
WHERE conname LIKE '%uuid_format%'
ORDER BY table_name, constraint_name;"
```

---

## Task 2.3: Add Type Conversion Helpers

**Status:** PENDING  
**Duration:** 1 hour  
**File:** `backend/utils/type_converters.py` (NEW)

### Implementation Details

**Helper Module:**
```python
"""
Type conversion utilities for UUID/VARCHAR handling
Ensures consistent type conversions across the application
"""

from typing import Union
from uuid import UUID


class TypeConversionError(Exception):
    """Raised when type conversion fails"""
    pass


def ensure_uuid_string(value: Union[str, UUID, None]) -> str:
    """
    Convert any UUID-like value to string format
    
    Args:
        value: UUID object, string, or None
        
    Returns:
        String representation of UUID
        
    Raises:
        TypeConversionError: If value is not a valid UUID
    """
    if value is None:
        raise TypeConversionError("Cannot convert None to UUID string")
    
    if isinstance(value, UUID):
        return str(value)
    
    if isinstance(value, str):
        # Validate format
        if not is_valid_uuid_format(value):
            raise TypeConversionError(f"Invalid UUID format: {value}")
        return value.lower()  # Normalize to lowercase
    
    raise TypeConversionError(f"Cannot convert {type(value)} to UUID string")


def is_valid_uuid_format(value: str) -> bool:
    """
    Check if string is valid UUID format
    
    Args:
        value: String to check
        
    Returns:
        True if valid UUID format, False otherwise
    """
    import re
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(uuid_pattern, value.lower()))


def safe_uuid_cast(value: Union[str, UUID, None]) -> Union[UUID, None]:
    """
    Safely cast string to UUID object
    
    Args:
        value: String or UUID to cast
        
    Returns:
        UUID object or None if conversion fails
    """
    if value is None:
        return None
    
    if isinstance(value, UUID):
        return value
    
    try:
        return UUID(value)
    except (ValueError, AttributeError):
        return None


# Database query helpers
def build_user_filter(user_id: Union[str, UUID]) -> tuple[str, str]:
    """
    Build SQL filter for user_id with proper type handling
    
    Args:
        user_id: User ID as string or UUID
        
    Returns:
        Tuple of (sql_fragment, converted_value)
        
    Example:
        sql, val = build_user_filter(user_id)
        query = f"SELECT * FROM table WHERE {sql}"
        result = db.execute(query, {"user_id": val})
    """
    user_id_str = ensure_uuid_string(user_id)
    
    # Return SQL that works for both uuid and varchar columns
    return "CAST(user_id AS TEXT) = :user_id", user_id_str


def build_session_filter(session_id: Union[str, UUID]) -> tuple[str, str]:
    """
    Build SQL filter for session_id with proper type handling
    
    Args:
        session_id: Session ID as string or UUID
        
    Returns:
        Tuple of (sql_fragment, converted_value)
    """
    session_id_str = ensure_uuid_string(session_id)
    return "CAST(session_id AS TEXT) = :session_id", session_id_str


# Usage example
if __name__ == "__main__":
    # Test conversions
    uuid_obj = UUID("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11")
    uuid_str = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
    
    assert ensure_uuid_string(uuid_obj) == uuid_str
    assert ensure_uuid_string(uuid_str) == uuid_str
    assert is_valid_uuid_format(uuid_str) == True
    assert is_valid_uuid_format("invalid") == False
    
    print("✅ Type conversion tests passed")
```

**Update application code to use helpers:**
```python
# Example: Update bg_job_queue.py
from utils.type_converters import ensure_uuid_string

async def enqueue_job(job_type: str, user_id: str, session_id: str = None):
    # Validate and normalize IDs
    user_id_str = ensure_uuid_string(user_id)
    session_id_str = ensure_uuid_string(session_id) if session_id else None
    
    # Rest of the logic...
```

**Testing:**
```python
# backend/tests/test_type_converters.py
import pytest
from uuid import UUID
from utils.type_converters import (
    ensure_uuid_string, 
    is_valid_uuid_format,
    TypeConversionError
)

def test_ensure_uuid_string_from_uuid():
    uuid_obj = UUID("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11")
    result = ensure_uuid_string(uuid_obj)
    assert result == "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"

def test_ensure_uuid_string_from_string():
    uuid_str = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
    result = ensure_uuid_string(uuid_str)
    assert result == uuid_str

def test_ensure_uuid_string_invalid():
    with pytest.raises(TypeConversionError):
        ensure_uuid_string("not-a-uuid")

def test_is_valid_uuid_format():
    assert is_valid_uuid_format("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11") == True
    assert is_valid_uuid_format("invalid") == False
    assert is_valid_uuid_format("") == False

# Run tests
pytest backend/tests/test_type_converters.py -v
```

---

## Task 2.4: Add Foreign Key Constraints

**Status:** PENDING  
**Duration:** 2 hours  
**File:** `backend/migrations/027_add_foreign_keys.sql` (NEW)

### Implementation Details

**CRITICAL: Must run AFTER backfill (Task 1.5) completes**

**Pre-flight checks:**
```sql
-- 1. Check for orphaned records in session_summary_final
SELECT COUNT(*) as orphaned_summaries
FROM session_summary_final ssf
WHERE NOT EXISTS (
    SELECT 1 FROM sessions s 
    WHERE s.session_id::varchar = ssf.session_id
);
-- Expected: 0

-- 2. Check for orphaned records in concept_alias_map_latest
SELECT COUNT(*) as orphaned_concepts
FROM concept_alias_map_latest cal
WHERE NOT EXISTS (
    SELECT 1 FROM users u 
    WHERE u.id::varchar = cal.user_id
);
-- Expected: 0

-- 3. Check for orphaned bg_jobs
SELECT COUNT(*) as orphaned_jobs
FROM bg_jobs bj
WHERE NOT EXISTS (
    SELECT 1 FROM users u 
    WHERE u.id::varchar = bj.user_id
);
-- Expected: Low number (jobs for deleted users)
```

**Migration Script:**
```sql
-- Migration: Add foreign key constraints for referential integrity
-- Prerequisites: 
--   1. Backfill completed (no orphaned sessions)
--   2. UUID validation constraints added
--   3. All orphaned records cleaned up

BEGIN;

-- 1. Clean up any orphaned records first
-- (Only if pre-flight checks found issues)

-- Clean orphaned session_summary_final records
DELETE FROM session_summary_final ssf
WHERE NOT EXISTS (
    SELECT 1 FROM sessions s 
    WHERE CAST(s.session_id AS VARCHAR) = ssf.session_id
);

-- Clean orphaned concept_alias_map_latest records
DELETE FROM concept_alias_map_latest cal
WHERE NOT EXISTS (
    SELECT 1 FROM users u 
    WHERE CAST(u.id AS VARCHAR) = cal.user_id
);

-- 2. Add foreign key: session_summary_final -> sessions
-- Note: Requires casting because sessions.session_id is VARCHAR but might be compared to UUID
ALTER TABLE session_summary_final
ADD CONSTRAINT fk_session_summary_session
FOREIGN KEY (session_id) 
REFERENCES sessions(session_id)
ON DELETE CASCADE
ON UPDATE CASCADE;

COMMENT ON CONSTRAINT fk_session_summary_session ON session_summary_final
IS 'Ensures every summary references a valid session. Cascade delete when session is removed.';

-- 3. Add index for FK performance
CREATE INDEX IF NOT EXISTS idx_session_summary_final_session_id 
ON session_summary_final(session_id);

-- 4. Add foreign key: concept_alias_map_latest -> users
-- Note: This assumes users.id exists and is the PK
ALTER TABLE concept_alias_map_latest
ADD CONSTRAINT fk_concept_map_user
FOREIGN KEY (user_id)
REFERENCES users(id::varchar)  -- Cast if users.id is UUID
ON DELETE CASCADE
ON UPDATE CASCADE;

COMMENT ON CONSTRAINT fk_concept_map_user ON concept_alias_map_latest
IS 'Ensures every concept belongs to a valid user. Cascade delete when user is removed.';

-- 5. Add index for FK performance
CREATE INDEX IF NOT EXISTS idx_concept_alias_map_user_id 
ON concept_alias_map_latest(user_id);

-- 6. Consider adding FK for bg_jobs -> users (optional, may have cleanup implications)
-- Note: Only add if you want to prevent jobs for non-existent users
-- This might fail if there are jobs for deleted users - clean those up first

-- Optional: Clean up bg_jobs for non-existent users
DELETE FROM bg_jobs bj
WHERE NOT EXISTS (
    SELECT 1 FROM users u 
    WHERE CAST(u.id AS VARCHAR) = bj.user_id
)
AND status IN ('succeeded', 'failed')
AND completed_at < NOW() - INTERVAL '30 days';

-- Add FK only if you want strict referential integrity for jobs
ALTER TABLE bg_jobs
ADD CONSTRAINT fk_bg_jobs_user
FOREIGN KEY (user_id)
REFERENCES users(id::varchar)
ON DELETE CASCADE  -- Warning: This will delete pending jobs if user is deleted
ON UPDATE CASCADE;

CREATE INDEX IF NOT EXISTS idx_bg_jobs_user_id ON bg_jobs(user_id);

-- 7. Verify constraints were added
SELECT 
    conname as constraint_name,
    conrelid::regclass as table_name,
    confrelid::regclass as references_table,
    pg_get_constraintdef(oid) as definition
FROM pg_constraint
WHERE contype = 'f'
AND conrelid::regclass::text IN (
    'session_summary_final',
    'concept_alias_map_latest',
    'bg_jobs'
)
ORDER BY table_name, constraint_name;

COMMIT;

-- Test: Try to insert invalid data (should fail)
-- This should raise FK violation error
INSERT INTO session_summary_final (user_id, session_id, concept_weights, created_at)
VALUES (
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    'non-existent-session-id-12345678',  -- Invalid session_id
    '[]',
    NOW()
);
-- Expected: ERROR: insert or update on table "session_summary_final" violates foreign key constraint
```

**Rollback Script:**
```sql
-- Rollback: Remove foreign key constraints

ALTER TABLE session_summary_final DROP CONSTRAINT IF EXISTS fk_session_summary_session;
ALTER TABLE concept_alias_map_latest DROP CONSTRAINT IF EXISTS fk_concept_map_user;
ALTER TABLE bg_jobs DROP CONSTRAINT IF EXISTS fk_bg_jobs_user;

DROP INDEX IF EXISTS idx_session_summary_final_session_id;
DROP INDEX IF EXISTS idx_concept_alias_map_user_id;
DROP INDEX IF EXISTS idx_bg_jobs_user_id;
```

**Testing Plan:**
```bash
# 1. Pre-flight checks
psql $DATABASE_URL -f backend/migrations/027_add_foreign_keys_preflight.sql

# 2. If checks pass, apply migration
psql $DATABASE_URL -f backend/migrations/027_add_foreign_keys.sql

# 3. Verify constraints
psql $DATABASE_URL << 'EOF'
SELECT 
    conname,
    conrelid::regclass as table,
    confrelid::regclass as ref_table
FROM pg_constraint
WHERE contype = 'f'
AND conrelid::regclass::text LIKE '%summary%' 
   OR conrelid::regclass::text LIKE '%concept%'
   OR conrelid::regclass::text = 'bg_jobs';
EOF

# 4. Test FK enforcement (should fail)
psql $DATABASE_URL << 'EOF'
INSERT INTO session_summary_final (user_id, session_id, concept_weights, created_at)
VALUES ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'fake-id-000000000000', '[]', NOW());
-- Expected: FK violation error
EOF

# 5. Monitor application for errors
tail -f /var/log/supervisor/backend.err.log | grep -i "foreign key"
```

**Risk Mitigation:**
- Run during low-traffic period
- Have rollback script ready
- Monitor application errors for 1 hour after deployment
- If errors occur, rollback immediately

---

## Task 2.5: Update Application Code for Type Safety

**Status:** PENDING  
**Duration:** 3 hours  

### Files to Update

#### A. Update `bg_job_queue.py`
```python
# Add at top
from utils.type_converters import ensure_uuid_string, TypeConversionError

# Update enqueue_job
async def enqueue_job(
    self, 
    job_type: str, 
    user_id: str, 
    session_id: str = None,
    **kwargs
) -> str:
    """Enqueue a background job with type-safe IDs"""
    
    try:
        # Validate and normalize IDs
        user_id_str = ensure_uuid_string(user_id)
        session_id_str = ensure_uuid_string(session_id) if session_id else None
        
        # Build dedupe key
        dedupe_key = f"u:{user_id_str}|"
        if session_id_str:
            dedupe_key += f"s:{session_id_str}|"
        dedupe_key += job_type
        
        # Rest of existing logic...
        
    except TypeConversionError as e:
        logger.error(f"Invalid ID format: {e}")
        raise ValueError(f"Invalid user_id or session_id format: {e}")
```

#### B. Update `simplified_job_handlers.py`
```python
# Add at top
from utils.type_converters import ensure_uuid_string

# Update each handler
async def run_simplified_summarizer(user_id: str, session_id: str):
    """Summarize session with type-safe IDs"""
    
    # Normalize IDs at entry point
    user_id = ensure_uuid_string(user_id)
    session_id = ensure_uuid_string(session_id)
    
    # Rest of existing logic...
```

#### C. Update `blueprint_sessions.py`
```python
# Add validation to API endpoints
from utils.type_converters import is_valid_uuid_format
from fastapi import HTTPException

@app.post("/api/session/complete")
async def complete_session(session_id: str, user_id: str):
    # Validate UUID format
    if not is_valid_uuid_format(session_id):
        raise HTTPException(400, "Invalid session_id format")
    if not is_valid_uuid_format(user_id):
        raise HTTPException(400, "Invalid user_id format")
    
    # Rest of existing logic...
```

**Testing:**
```python
# Test with pytest
# backend/tests/test_type_safety.py

import pytest
from fastapi.testclient import TestClient
from api.server import app

client = TestClient(app)

def test_complete_session_invalid_uuid():
    response = client.post(
        "/api/session/complete",
        json={
            "session_id": "invalid-uuid",
            "user_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
        }
    )
    assert response.status_code == 400
    assert "Invalid session_id format" in response.json()["detail"]

def test_complete_session_valid_uuid():
    response = client.post(
        "/api/session/complete",
        json={
            "session_id": "12345678-1234-1234-1234-123456789012",
            "user_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
        }
    )
    # Should not fail due to UUID validation
    assert response.status_code in [200, 404]  # 404 if session doesn't exist
```

---

## Phase 2 Completion Checklist

- [ ] Type standardization analysis complete
- [ ] UUID validation constraints added
- [ ] Type conversion helpers created and tested
- [ ] Foreign key constraints added
- [ ] Application code updated for type safety
- [ ] All tests passing
- [ ] No FK violation errors in logs
- [ ] Documentation updated

**Success Criteria:**
- ✅ All identifier columns have UUID format validation
- ✅ Foreign key constraints enforced
- ✅ Type conversion helpers used throughout codebase
- ✅ No silent type conversion failures

---

# PHASE 3: OBSERVABILITY (Hours 24-36)

**Goal:** Add comprehensive monitoring and health checks  
**Success Metric:** Real-time visibility into pipeline health

---

## Task 3.1: Create Health Metrics Infrastructure

**Status:** PENDING  
**Duration:** 2 hours  
**File:** `backend/migrations/028_health_metrics.sql` (NEW)

### Implementation Details

**Migration Script:**
```sql
-- Migration: Create pipeline health metrics infrastructure
-- Provides real-time visibility into adaptive learning pipeline

BEGIN;

-- 1. Create metrics table
CREATE TABLE IF NOT EXISTS pipeline_health_metrics (
    metric_name VARCHAR(100) PRIMARY KEY,
    metric_value NUMERIC,
    metric_type VARCHAR(20) CHECK (metric_type IN ('counter', 'gauge', 'percentage', 'duration')),
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    description TEXT
);

COMMENT ON TABLE pipeline_health_metrics 
IS 'Real-time health metrics for adaptive learning pipeline';

-- 2. Insert initial metrics
INSERT INTO pipeline_health_metrics (metric_name, metric_value, metric_type, description) VALUES
('summary_completion_rate', 0.0, 'percentage', 'Percentage of completed sessions with summaries'),
('orphaned_sessions_count', 0, 'gauge', 'Number of completed sessions without summaries'),
('concept_write_success_rate', 0.0, 'percentage', 'Percentage of summaries that write concepts'),
('job_success_rate_24h', 0.0, 'percentage', 'Job success rate in last 24 hours'),
('avg_summarize_latency_p95', 0.0, 'duration', 'P95 latency for SUMMARIZE_SESSION jobs (seconds)'),
('avg_plan_latency_p95', 0.0, 'duration', 'P95 latency for PLAN_NEXT_SESSION jobs (seconds)'),
('avg_insights_latency_p95', 0.0, 'duration', 'P95 latency for UPDATE_INSIGHTS jobs (seconds)'),
('concept_map_growth_7d', 0, 'counter', 'New concepts added in last 7 days'),
('active_users_7d', 0, 'gauge', 'Users with sessions in last 7 days'),
('jobs_queued', 0, 'gauge', 'Current number of queued jobs'),
('jobs_running', 0, 'gauge', 'Current number of running jobs'),
('last_summary_timestamp', 0, 'gauge', 'Epoch timestamp of most recent summary')
ON CONFLICT (metric_name) DO NOTHING;

-- 3. Create materialized view for orphaned sessions
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_orphaned_sessions AS
SELECT 
    s.session_id,
    s.user_id,
    s.created_at,
    s.questions_answered,
    s.questions_correct,
    EXTRACT(EPOCH FROM (NOW() - s.created_at))/3600 as hours_since_completion
FROM sessions s
WHERE s.status = 'completed'
AND NOT EXISTS (
    SELECT 1 FROM session_summary_final ssf 
    WHERE CAST(ssf.session_id AS VARCHAR) = CAST(s.session_id AS VARCHAR)
)
ORDER BY s.created_at DESC;

CREATE INDEX IF NOT EXISTS idx_mv_orphaned_sessions_user 
ON mv_orphaned_sessions(user_id);

COMMENT ON MATERIALIZED VIEW mv_orphaned_sessions
IS 'Fast lookup of sessions missing summaries. Refresh every 5 minutes.';

-- 4. Create materialized view for job performance
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_job_performance_24h AS
SELECT 
    job_type,
    status,
    COUNT(*) as job_count,
    ROUND(AVG(EXTRACT(EPOCH FROM (completed_at - started_at))), 2) as avg_duration_sec,
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (completed_at - started_at))), 2) as p95_duration_sec,
    ROUND(PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (completed_at - started_at))), 2) as p99_duration_sec
FROM bg_jobs
WHERE created_at > NOW() - INTERVAL '24 hours'
AND completed_at IS NOT NULL
GROUP BY job_type, status
ORDER BY job_type, status;

COMMENT ON MATERIALIZED VIEW mv_job_performance_24h
IS 'Job performance metrics for last 24 hours. Refresh every 5 minutes.';

-- 5. Create refresh function for materialized views
CREATE OR REPLACE FUNCTION refresh_health_metrics_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW mv_orphaned_sessions;
    REFRESH MATERIALIZED VIEW mv_job_performance_24h;
END;
$$ LANGUAGE plpgsql;

-- 6. Create function to update metrics
CREATE OR REPLACE FUNCTION update_pipeline_health_metrics()
RETURNS void AS $$
DECLARE
    v_total_completed INTEGER;
    v_with_summaries INTEGER;
    v_orphaned INTEGER;
    v_completion_rate NUMERIC;
    v_job_success_rate NUMERIC;
    v_concepts_7d INTEGER;
    v_active_users INTEGER;
BEGIN
    -- Calculate summary completion rate
    SELECT 
        COUNT(*) as total,
        COUNT(CASE WHEN EXISTS (
            SELECT 1 FROM session_summary_final ssf 
            WHERE CAST(ssf.session_id AS VARCHAR) = CAST(s.session_id AS VARCHAR)
        ) THEN 1 END) as with_summary
    INTO v_total_completed, v_with_summaries
    FROM sessions s
    WHERE s.status = 'completed';
    
    v_orphaned := v_total_completed - v_with_summaries;
    v_completion_rate := CASE 
        WHEN v_total_completed > 0 
        THEN (v_with_summaries::numeric / v_total_completed * 100)
        ELSE 100 
    END;
    
    UPDATE pipeline_health_metrics 
    SET metric_value = v_completion_rate, last_updated = NOW()
    WHERE metric_name = 'summary_completion_rate';
    
    UPDATE pipeline_health_metrics 
    SET metric_value = v_orphaned, last_updated = NOW()
    WHERE metric_name = 'orphaned_sessions_count';
    
    -- Calculate job success rate (24h)
    SELECT 
        CASE 
            WHEN COUNT(*) > 0 
            THEN (COUNT(CASE WHEN status = 'succeeded' THEN 1 END)::numeric / COUNT(*) * 100)
            ELSE 100 
        END
    INTO v_job_success_rate
    FROM bg_jobs
    WHERE created_at > NOW() - INTERVAL '24 hours'
    AND status IN ('succeeded', 'failed');
    
    UPDATE pipeline_health_metrics 
    SET metric_value = v_job_success_rate, last_updated = NOW()
    WHERE metric_name = 'job_success_rate_24h';
    
    -- Concept map growth (7 days)
    SELECT COUNT(*)
    INTO v_concepts_7d
    FROM concept_alias_map_latest
    WHERE last_updated > NOW() - INTERVAL '7 days';
    
    UPDATE pipeline_health_metrics 
    SET metric_value = v_concepts_7d, last_updated = NOW()
    WHERE metric_name = 'concept_map_growth_7d';
    
    -- Active users (7 days)
    SELECT COUNT(DISTINCT user_id)
    INTO v_active_users
    FROM sessions
    WHERE created_at > NOW() - INTERVAL '7 days';
    
    UPDATE pipeline_health_metrics 
    SET metric_value = v_active_users, last_updated = NOW()
    WHERE metric_name = 'active_users_7d';
    
    -- Job queue depth
    UPDATE pipeline_health_metrics 
    SET metric_value = (SELECT COUNT(*) FROM bg_jobs WHERE status = 'queued'),
        last_updated = NOW()
    WHERE metric_name = 'jobs_queued';
    
    UPDATE pipeline_health_metrics 
    SET metric_value = (SELECT COUNT(*) FROM bg_jobs WHERE status = 'running'),
        last_updated = NOW()
    WHERE metric_name = 'jobs_running';
    
    -- Last summary timestamp
    UPDATE pipeline_health_metrics 
    SET metric_value = (
        SELECT EXTRACT(EPOCH FROM MAX(created_at))
        FROM session_summary_final
    ),
    last_updated = NOW()
    WHERE metric_name = 'last_summary_timestamp';
    
END;
$$ LANGUAGE plpgsql;

-- 7. Create scheduled job for metric updates (using pg_cron if available)
-- Note: Requires pg_cron extension
-- If pg_cron not available, will need to call from application layer

-- Check if pg_cron is available
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'pg_cron') THEN
        CREATE EXTENSION IF NOT EXISTS pg_cron;
        
        -- Refresh metrics every 5 minutes
        PERFORM cron.schedule(
            'refresh-pipeline-health-metrics',
            '*/5 * * * *',  -- Every 5 minutes
            'SELECT update_pipeline_health_metrics()'
        );
        
        -- Refresh materialized views every 5 minutes
        PERFORM cron.schedule(
            'refresh-health-views',
            '*/5 * * * *',
            'SELECT refresh_health_metrics_views()'
        );
        
        RAISE NOTICE 'pg_cron scheduled jobs created';
    ELSE
        RAISE NOTICE 'pg_cron not available - metrics must be refreshed from application layer';
    END IF;
END $$;

-- 8. Initial metrics calculation
SELECT update_pipeline_health_metrics();
SELECT refresh_health_metrics_views();

COMMIT;

-- Verify installation
SELECT * FROM pipeline_health_metrics ORDER BY metric_name;
```

**Manual refresh script (if pg_cron not available):**
```python
# backend/scripts/refresh_health_metrics.py
"""
Manually refresh health metrics
Run this from cron or application scheduler
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import get_db_session
from sqlalchemy import text

def refresh_metrics():
    db = get_db_session()
    
    # Update metrics
    db.execute(text("SELECT update_pipeline_health_metrics()"))
    db.execute(text("SELECT refresh_health_metrics_views()"))
    db.commit()
    
    print("✅ Health metrics refreshed")

if __name__ == "__main__":
    refresh_metrics()
```

**Add to crontab:**
```bash
# Refresh every 5 minutes
*/5 * * * * cd /app/backend && python3 scripts/refresh_health_metrics.py >> /var/log/health_metrics.log 2>&1
```

---

## Task 3.2: Create Health Dashboard Endpoint

**Status:** PENDING  
**Duration:** 2 hours  
**File:** `backend/api/health.py` (NEW)

### Implementation Details

**API Endpoint:**
```python
"""
Health monitoring API for adaptive learning pipeline
Provides real-time health metrics and diagnostics
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Any
from datetime import datetime, timezone
from sqlalchemy import text
from database import get_db_session

router = APIRouter(prefix="/api/admin", tags=["health"])


@router.get("/pipeline-health")
async def get_pipeline_health(db = Depends(get_db_session)) -> Dict[str, Any]:
    """
    Get comprehensive pipeline health metrics
    
    Returns:
        Health dashboard data with metrics, alerts, and status
    """
    try:
        # Fetch all metrics
        metrics_result = db.execute(text("""
            SELECT 
                metric_name,
                metric_value,
                metric_type,
                last_updated,
                description
            FROM pipeline_health_metrics
            ORDER BY metric_name
        """)).fetchall()
        
        # Build metrics dict
        metrics = {}
        for name, value, mtype, updated, desc in metrics_result:
            metrics[name] = {
                "value": float(value) if value is not None else 0,
                "type": mtype,
                "last_updated": updated.isoformat() if updated else None,
                "description": desc
            }
        
        # Get orphaned sessions details
        orphaned_result = db.execute(text("""
            SELECT session_id, user_id, hours_since_completion
            FROM mv_orphaned_sessions
            ORDER BY hours_since_completion DESC
            LIMIT 5
        """)).fetchall()
        
        orphaned_sessions = [
            {
                "session_id": str(sid)[:8] + "...",
                "user_id": str(uid)[:8] + "...",
                "hours_ago": round(float(hours), 1)
            }
            for sid, uid, hours in orphaned_result
        ]
        
        # Get job performance
        job_perf_result = db.execute(text("""
            SELECT 
                job_type,
                status,
                job_count,
                avg_duration_sec,
                p95_duration_sec
            FROM mv_job_performance_24h
            ORDER BY job_type, status
        """)).fetchall()
        
        job_performance = {}
        for jtype, status, count, avg, p95 in job_perf_result:
            if jtype not in job_performance:
                job_performance[jtype] = {}
            job_performance[jtype][status] = {
                "count": count,
                "avg_duration": float(avg) if avg else 0,
                "p95_duration": float(p95) if p95 else 0
            }
        
        # Calculate overall health status
        health_status = calculate_health_status(metrics)
        
        # Generate alerts
        alerts = generate_alerts(metrics, orphaned_sessions)
        
        return {
            "status": health_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics,
            "orphaned_sessions": {
                "count": metrics.get("orphaned_sessions_count", {}).get("value", 0),
                "details": orphaned_sessions
            },
            "job_performance": job_performance,
            "alerts": alerts
        }
        
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch health metrics: {e}")


def calculate_health_status(metrics: Dict) -> str:
    """
    Calculate overall health status based on metrics
    
    Returns:
        "healthy", "degraded", or "critical"
    """
    # Critical conditions
    if metrics.get("orphaned_sessions_count", {}).get("value", 0) > 10:
        return "critical"
    if metrics.get("summary_completion_rate", {}).get("value", 100) < 80:
        return "critical"
    if metrics.get("job_success_rate_24h", {}).get("value", 100) < 85:
        return "critical"
    
    # Degraded conditions
    if metrics.get("orphaned_sessions_count", {}).get("value", 0) > 5:
        return "degraded"
    if metrics.get("summary_completion_rate", {}).get("value", 100) < 95:
        return "degraded"
    if metrics.get("avg_summarize_latency_p95", {}).get("value", 0) > 60:
        return "degraded"
    
    return "healthy"


def generate_alerts(metrics: Dict, orphaned: List) -> List[Dict]:
    """Generate alerts based on metrics"""
    alerts = []
    
    # Alert: Orphaned sessions
    orphan_count = metrics.get("orphaned_sessions_count", {}).get("value", 0)
    if orphan_count > 0:
        alerts.append({
            "level": "critical" if orphan_count > 10 else "warning",
            "message": f"{int(orphan_count)} sessions are missing summaries",
            "action": "Run backfill script: python3 backend/scripts/backfill_session_summaries.py"
        })
    
    # Alert: Low completion rate
    completion_rate = metrics.get("summary_completion_rate", {}).get("value", 100)
    if completion_rate < 95:
        alerts.append({
            "level": "critical" if completion_rate < 80 else "warning",
            "message": f"Summary completion rate is {completion_rate:.1f}% (target: >95%)",
            "action": "Check worker logs and job error messages"
        })
    
    # Alert: High latency
    summarize_p95 = metrics.get("avg_summarize_latency_p95", {}).get("value", 0)
    if summarize_p95 > 60:
        alerts.append({
            "level": "warning",
            "message": f"SUMMARIZE_SESSION P95 latency is {summarize_p95:.1f}s (target: <30s)",
            "action": "Check database query performance and worker resources"
        })
    
    # Alert: Job failures
    success_rate = metrics.get("job_success_rate_24h", {}).get("value", 100)
    if success_rate < 95:
        alerts.append({
            "level": "critical" if success_rate < 85 else "warning",
            "message": f"Job success rate is {success_rate:.1f}% in last 24h (target: >95%)",
            "action": "Check bg_jobs table for error messages"
        })
    
    return alerts


@router.get("/pipeline-health/metrics")
async def get_metrics_only(db = Depends(get_db_session)) -> Dict[str, Any]:
    """Get only the metrics (lighter endpoint)"""
    result = db.execute(text("""
        SELECT metric_name, metric_value, last_updated
        FROM pipeline_health_metrics
    """)).fetchall()
    
    return {
        metric: {
            "value": float(value) if value else 0,
            "updated": updated.isoformat() if updated else None
        }
        for metric, value, updated in result
    }


@router.post("/pipeline-health/refresh")
async def refresh_health_metrics(db = Depends(get_db_session)):
    """Manually trigger metrics refresh"""
    try:
        db.execute(text("SELECT update_pipeline_health_metrics()"))
        db.execute(text("SELECT refresh_health_metrics_views()"))
        db.commit()
        
        return {"status": "success", "message": "Health metrics refreshed"}
    except Exception as e:
        raise HTTPException(500, f"Failed to refresh metrics: {e}")


@router.get("/pipeline-health/orphaned-sessions")
async def get_orphaned_sessions_detail(db = Depends(get_db_session)) -> List[Dict]:
    """Get detailed list of orphaned sessions"""
    result = db.execute(text("""
        SELECT 
            session_id,
            user_id,
            created_at,
            questions_answered,
            questions_correct,
            hours_since_completion
        FROM mv_orphaned_sessions
        ORDER BY hours_since_completion DESC
    """)).fetchall()
    
    return [
        {
            "session_id": str(sid),
            "user_id": str(uid),
            "created_at": created.isoformat(),
            "questions_answered": answered,
            "questions_correct": correct,
            "hours_since_completion": round(float(hours), 1)
        }
        for sid, uid, created, answered, correct, hours in result
    ]
```

**Register router in main app:**
```python
# backend/api/server.py
from api.health import router as health_router

app = FastAPI()
app.include_router(health_router)
```

**Testing:**
```bash
# 1. Test health endpoint
curl -X GET "http://localhost:8001/api/admin/pipeline-health" | jq

# Expected response:
# {
#   "status": "healthy",
#   "timestamp": "2025-09-30T18:00:00Z",
#   "metrics": {...},
#   "orphaned_sessions": {"count": 0, "details": []},
#   "job_performance": {...},
#   "alerts": []
# }

# 2. Test metrics-only endpoint
curl -X GET "http://localhost:8001/api/admin/pipeline-health/metrics" | jq

# 3. Test manual refresh
curl -X POST "http://localhost:8001/api/admin/pipeline-health/refresh"

# 4. Test orphaned sessions detail
curl -X GET "http://localhost:8001/api/admin/pipeline-health/orphaned-sessions" | jq
```

---

## Task 3.3: Add SLI Tracking

**Status:** PENDING  
**Duration:** 3 hours  
**Files:** Multiple

### Implementation Details

**A. Update job queue to emit timing metrics**

File: `backend/services/bg_job_queue.py`

```python
# Add at top
import time

class SimplifiedJobQueue:
    
    async def process_job(self, job: Dict):
        """Process a single job with timing metrics"""
        job_id = job["id"]
        job_type = job["job_type"]
        
        # Start timing
        start_time = time.time()
        start_timestamp = datetime.now(timezone.utc)
        
        try:
            # Update to running
            await self.update_job_status(job_id, "running", started_at=start_timestamp)
            
            # Execute handler
            result = await self.route_to_handler(job)
            
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Update to succeeded with timing
            await self.update_job_status(
                job_id, 
                "succeeded", 
                completed_at=datetime.now(timezone.utc),
                metadata={"duration_ms": duration_ms}
            )
            
            # Emit SLI metric
            await self.emit_sli_metric(job_type, "success", duration_ms)
            
            logger.info(f"✅ Job {job_id[:8]} succeeded in {duration_ms}ms")
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            
            await self.update_job_status(
                job_id,
                "failed",
                error_message=str(e),
                completed_at=datetime.now(timezone.utc)
            )
            
            # Emit failure metric
            await self.emit_sli_metric(job_type, "failure", duration_ms)
            
            logger.error(f"❌ Job {job_id[:8]} failed: {e}")
    
    async def emit_sli_metric(self, job_type: str, outcome: str, duration_ms: int):
        """Emit SLI metric for monitoring"""
        try:
            from database import get_db_session
            db = get_db_session()
            
            # Insert into SLI tracking table
            db.execute(text("""
                INSERT INTO pipeline_sli_events (
                    event_type,
                    job_type,
                    outcome,
                    duration_ms,
                    timestamp
                ) VALUES (
                    'job_completion',
                    :job_type,
                    :outcome,
                    :duration_ms,
                    NOW()
                )
            """), {
                "job_type": job_type,
                "outcome": outcome,
                "duration_ms": duration_ms
            })
            db.commit()
            
        except Exception as e:
            logger.warning(f"Failed to emit SLI metric: {e}")
```

**B. Create SLI events table**

File: `backend/migrations/029_sli_tracking.sql`

```sql
-- Migration: SLI event tracking for outcome-based monitoring

BEGIN;

-- 1. Create SLI events table
CREATE TABLE IF NOT EXISTS pipeline_sli_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,  -- 'job_completion', 'summary_created', etc.
    job_type VARCHAR(50),
    outcome VARCHAR(20) NOT NULL,  -- 'success', 'failure'
    duration_ms INTEGER,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_sli_events_timestamp ON pipeline_sli_events(timestamp);
CREATE INDEX idx_sli_events_type_outcome ON pipeline_sli_events(event_type, outcome);
CREATE INDEX idx_sli_events_job_type ON pipeline_sli_events(job_type);

-- 2. Create SLI summary materialized view
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_sli_summary_24h AS
SELECT 
    job_type,
    COUNT(*) as total_events,
    COUNT(CASE WHEN outcome = 'success' THEN 1 END) as successes,
    COUNT(CASE WHEN outcome = 'failure' THEN 1 END) as failures,
    ROUND(100.0 * COUNT(CASE WHEN outcome = 'success' THEN 1 END) / COUNT(*), 2) as success_rate_pct,
    ROUND(AVG(duration_ms), 2) as avg_duration_ms,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_ms), 2) as p50_duration_ms,
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms), 2) as p95_duration_ms,
    ROUND(PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration_ms), 2) as p99_duration_ms
FROM pipeline_sli_events
WHERE timestamp > NOW() - INTERVAL '24 hours'
AND event_type = 'job_completion'
GROUP BY job_type
ORDER BY job_type;

-- 3. Create function to calculate SLIs
CREATE OR REPLACE FUNCTION calculate_slis()
RETURNS TABLE (
    sli_name VARCHAR,
    current_value NUMERIC,
    target_value NUMERIC,
    status VARCHAR,
    last_24h_trend VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    
    -- SLI 1: Summary Completion Rate
    WITH summary_completion AS (
        SELECT 
            'summary_completion_rate' as sli_name,
            COALESCE(
                100.0 * COUNT(CASE WHEN EXISTS (
                    SELECT 1 FROM session_summary_final ssf 
                    WHERE CAST(ssf.session_id AS VARCHAR) = CAST(s.session_id AS VARCHAR)
                ) THEN 1 END) / NULLIF(COUNT(*), 0),
                100.0
            ) as current_val,
            95.0 as target_val
        FROM sessions s
        WHERE s.status = 'completed'
        AND s.created_at > NOW() - INTERVAL '24 hours'
    ),
    
    -- SLI 2: Concept Write Success Rate
    concept_write AS (
        SELECT 
            'concept_write_success_rate' as sli_name,
            COALESCE(
                100.0 * COUNT(CASE WHEN EXISTS (
                    SELECT 1 FROM concept_alias_map_latest cal
                    WHERE cal.first_seen_session_id = ssf.session_id
                ) THEN 1 END) / NULLIF(COUNT(*), 0),
                100.0
            ) as current_val,
            90.0 as target_val
        FROM session_summary_final ssf
        WHERE ssf.created_at > NOW() - INTERVAL '24 hours'
    ),
    
    -- SLI 3: Job Success Rate
    job_success AS (
        SELECT 
            'job_success_rate_24h' as sli_name,
            success_rate_pct as current_val,
            95.0 as target_val
        FROM (
            SELECT 
                COALESCE(
                    100.0 * SUM(successes) / NULLIF(SUM(total_events), 0),
                    100.0
                ) as success_rate_pct
            FROM mv_sli_summary_24h
        ) sub
    ),
    
    -- SLI 4: SUMMARIZE_SESSION P95 Latency
    summarize_latency AS (
        SELECT 
            'summarize_p95_latency' as sli_name,
            COALESCE(p95_duration_ms / 1000.0, 0) as current_val,
            30.0 as target_val
        FROM mv_sli_summary_24h
        WHERE job_type = 'SUMMARIZE_SESSION'
    )
    
    SELECT 
        sli_name,
        ROUND(current_val, 2) as current_value,
        target_val as target_value,
        CASE 
            WHEN current_val >= target_val THEN 'OK'
            WHEN current_val >= target_val * 0.9 THEN 'WARNING'
            ELSE 'CRITICAL'
        END as status,
        'stable' as last_24h_trend  -- TODO: Calculate actual trend
    FROM (
        SELECT * FROM summary_completion
        UNION ALL
        SELECT * FROM concept_write
        UNION ALL
        SELECT * FROM job_success
        UNION ALL
        SELECT * FROM summarize_latency
    ) all_slis;
    
END;
$$ LANGUAGE plpgsql;

-- 4. Add SLI calculation to health metrics update
CREATE OR REPLACE FUNCTION update_pipeline_health_metrics_with_sli()
RETURNS void AS $$
BEGIN
    -- Call original function
    PERFORM update_pipeline_health_metrics();
    
    -- Refresh SLI view
    REFRESH MATERIALIZED VIEW mv_sli_summary_24h;
    
    -- Update SLI metrics in health table
    UPDATE pipeline_health_metrics phm
    SET 
        metric_value = sli.current_value,
        last_updated = NOW(),
        metadata = jsonb_build_object(
            'target', sli.target_value,
            'status', sli.status,
            'trend', sli.last_24h_trend
        )
    FROM calculate_slis() sli
    WHERE phm.metric_name = sli.sli_name;
    
END;
$$ LANGUAGE plpgsql;

COMMIT;

-- Test
SELECT * FROM calculate_slis();
```

**C. Add SLI endpoint**

File: `backend/api/health.py` (add to existing file)

```python
@router.get("/pipeline-health/slis")
async def get_slis(db = Depends(get_db_session)) -> Dict[str, Any]:
    """
    Get Service Level Indicators (SLIs)
    
    Returns current performance vs. targets
    """
    result = db.execute(text("""
        SELECT * FROM calculate_slis()
        ORDER BY sli_name
    """)).fetchall()
    
    slis = {}
    for name, current, target, status, trend in result:
        slis[name] = {
            "current": float(current),
            "target": float(target),
            "status": status,
            "trend": trend,
            "percentage_of_target": round(float(current) / float(target) * 100, 1)
        }
    
    # Overall SLI health
    critical_count = sum(1 for sli in slis.values() if sli["status"] == "CRITICAL")
    warning_count = sum(1 for sli in slis.values() if sli["status"] == "WARNING")
    
    overall_status = "OK"
    if critical_count > 0:
        overall_status = "CRITICAL"
    elif warning_count > 0:
        overall_status = "WARNING"
    
    return {
        "overall_status": overall_status,
        "slis": slis,
        "summary": {
            "ok": len(slis) - critical_count - warning_count,
            "warning": warning_count,
            "critical": critical_count
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
```

---

## Phase 3 Completion Checklist

- [ ] Health metrics table created
- [ ] Materialized views for fast queries
- [ ] Health dashboard API endpoint working
- [ ] SLI tracking infrastructure in place
- [ ] Job queue emitting timing metrics
- [ ] SLI calculation functions working
- [ ] Metrics refresh scheduled (cron or pg_cron)
- [ ] Documentation updated with monitoring guide

**Success Criteria:**
- ✅ Health dashboard accessible at `/api/admin/pipeline-health`
- ✅ 4 SLIs tracked and monitored
- ✅ Alerts generated for degraded conditions
- ✅ Metrics refresh every 5 minutes

---

# PHASE 4: PRODUCTION HARDENING (Hours 36-48)

**Goal:** Centralize configuration and automate deployments  
**Success Metric:** Production-ready deployment process

---

## Task 4.1: Centralize Adaptive Learning Configuration

**Status:** PENDING  
**Duration:** 2 hours  
**File:** `backend/config/adaptive_learning_config.py` (NEW)

### Implementation Details

**Configuration Module:**
```python
"""
Centralized configuration for adaptive learning algorithms

This module contains all hyperparameters and constants used in the
adaptive learning pipeline. Changing these values affects:
- Mastery score calculations
- Coverage debt decay
- Concept normalization
- Session pack generation

Version: 1.0
Last Updated: 2025-09-30
"""

from typing import Dict, List
import re


class AdaptiveLearningConfig:
    """
    Central configuration for adaptive learning system
    
    All constants and hyperparameters should be defined here
    to ensure consistency and auditability
    """
    
    # ==================== VERSION ====================
    CONFIG_VERSION = "1.0.0"
    
    # ==================== MASTERY SCORING ====================
    
    # Exponential Moving Average (EMA) for concept mastery
    # Higher alpha = more weight to recent performance
    # Range: 0.0 to 1.0
    EMA_ALPHA = 0.3
    
    # Mastery score initialization (for new concepts)
    INITIAL_MASTERY_SCORE = 0.5
    
    # Readiness thresholds
    WEAK_THRESHOLD = 0.4        # Below this = "Weak"
    MODERATE_THRESHOLD = 0.7    # 0.4-0.7 = "Moderate", Above = "Strong"
    
    # Score adjustments per correct/incorrect answer
    MASTERY_INCREASE_ON_CORRECT = 0.15
    MASTERY_DECREASE_ON_WRONG = -0.10
    
    # ==================== COVERAGE DEBT ====================
    
    # Daily decay rate for coverage debt
    # debt_new = debt_old * DECAY_RATE
    DEBT_DECAY_RATE = 0.95
    
    # Debt reduction when skill is practiced
    DEBT_DECREASE_ON_PRACTICE = -0.15
    
    # Initial debt for new skill pair
    INITIAL_DEBT_SCORE = 1.0
    
    # High debt threshold (prioritize in session planning)
    HIGH_DEBT_THRESHOLD = 0.7
    
    # ==================== CONCEPT NORMALIZATION ====================
    
    @staticmethod
    def normalize_concept(concept: str) -> str:
        """
        Normalize concept name to canonical form
        
        This is the SINGLE SOURCE OF TRUTH for concept normalization.
        Used for:
        - concept_alias_map_latest.semantic_id
        - learner_notebook.concept_norm
        - Deduplication and matching
        
        Rules:
        1. Convert to lowercase
        2. Strip leading/trailing whitespace
        3. Replace spaces with underscores
        4. Remove special characters (keep alphanumeric and underscore)
        5. Collapse multiple underscores
        
        Examples:
            "Time & Distance" -> "time_distance"
            "3D Mensuration" -> "3d_mensuration"
            "  Ratios / Proportions  " -> "ratios_proportions"
        
        Args:
            concept: Raw concept name
            
        Returns:
            Normalized concept identifier
        """
        if not concept:
            return "unknown"
        
        # Lowercase and strip
        normalized = concept.lower().strip()
        
        # Remove special characters (keep alphanumeric, spaces, underscores)
        normalized = re.sub(r'[^a-z0-9\s_]', '', normalized)
        
        # Replace spaces with underscores
        normalized = normalized.replace(' ', '_')
        
        # Collapse multiple underscores
        normalized = re.sub(r'_+', '_', normalized)
        
        # Remove leading/trailing underscores
        normalized = normalized.strip('_')
        
        return normalized or "unknown"
    
    # ==================== SESSION PACK GENERATION ====================
    
    # Total questions per session
    PACK_SIZE = 12
    
    # Difficulty distribution
    DIFFICULTY_DISTRIBUTION = {
        "easy": 3,
        "medium": 6,
        "hard": 3
    }
    
    # Concept targeting
    MIN_WEAK_CONCEPTS_IN_PACK = 2   # Target at least 2 weak concepts
    MAX_REPEAT_CONCEPT = 3           # Max questions per concept
    
    # Recency constraint
    MIN_DAYS_BEFORE_REPEAT = 3       # Don't repeat questions seen in last 3 days
    
    # ==================== JOB PROCESSING ====================
    
    # Background job configuration
    MAX_JOB_ATTEMPTS = 6
    JOB_TIMEOUT_SECONDS = 300  # 5 minutes
    
    # Backoff strategy for retries (minutes)
    RETRY_BACKOFF_SCHEDULE = [1, 2, 4, 8, 16, 30]
    
    # ==================== THRESHOLDS & LIMITS ====================
    
    # Session validation
    MIN_QUESTIONS_FOR_VALID_SESSION = 3
    MIN_SESSION_DURATION_SECONDS = 60
    
    # Insight generation
    MIN_SESSIONS_FOR_INSIGHTS = 2
    MIN_CONCEPTS_FOR_ANALYSIS = 3
    
    # ==================== FEATURE FLAGS ====================
    
    # Enable/disable features
    ENABLE_LLM_INSIGHTS = True
    ENABLE_CONCEPT_ALIAS_MAPPING = True
    ENABLE_COVERAGE_DEBT_TRACKING = True
    ENABLE_SESSION_PACK_PLANNING = True
    
    # ==================== VALIDATION ====================
    
    @classmethod
    def validate_config(cls) -> List[str]:
        """
        Validate configuration values
        
        Returns:
            List of validation errors (empty if all valid)
        """
        errors = []
        
        # Validate EMA alpha
        if not 0 <= cls.EMA_ALPHA <= 1:
            errors.append(f"EMA_ALPHA must be in [0, 1], got {cls.EMA_ALPHA}")
        
        # Validate thresholds
        if not 0 <= cls.WEAK_THRESHOLD < cls.MODERATE_THRESHOLD <= 1:
            errors.append(f"Invalid readiness thresholds: WEAK={cls.WEAK_THRESHOLD}, MODERATE={cls.MODERATE_THRESHOLD}")
        
        # Validate pack size
        pack_total = sum(cls.DIFFICULTY_DISTRIBUTION.values())
        if pack_total != cls.PACK_SIZE:
            errors.append(f"DIFFICULTY_DISTRIBUTION sum ({pack_total}) != PACK_SIZE ({cls.PACK_SIZE})")
        
        # Validate debt decay
        if not 0 < cls.DEBT_DECAY_RATE <= 1:
            errors.append(f"DEBT_DECAY_RATE must be in (0, 1], got {cls.DEBT_DECAY_RATE}")
        
        return errors
    
    @classmethod
    def get_config_snapshot(cls) -> Dict:
        """
        Get snapshot of current configuration for audit trail
        
        Returns:
            Dict of all config values
        """
        return {
            "version": cls.CONFIG_VERSION,
            "mastery": {
                "ema_alpha": cls.EMA_ALPHA,
                "weak_threshold": cls.WEAK_THRESHOLD,
                "moderate_threshold": cls.MODERATE_THRESHOLD,
                "initial_score": cls.INITIAL_MASTERY_SCORE
            },
            "debt": {
                "decay_rate": cls.DEBT_DECAY_RATE,
                "decrease_on_practice": cls.DEBT_DECREASE_ON_PRACTICE,
                "high_debt_threshold": cls.HIGH_DEBT_THRESHOLD
            },
            "session_pack": {
                "size": cls.PACK_SIZE,
                "difficulty_distribution": cls.DIFFICULTY_DISTRIBUTION
            },
            "feature_flags": {
                "llm_insights": cls.ENABLE_LLM_INSIGHTS,
                "concept_mapping": cls.ENABLE_CONCEPT_ALIAS_MAPPING,
                "debt_tracking": cls.ENABLE_COVERAGE_DEBT_TRACKING,
                "pack_planning": cls.ENABLE_SESSION_PACK_PLANNING
            }
        }


# Validate on import
_validation_errors = AdaptiveLearningConfig.validate_config()
if _validation_errors:
    raise ValueError(f"Invalid configuration:\n" + "\n".join(f"  - {e}" for e in _validation_errors))


# Convenience exports
EMA_ALPHA = AdaptiveLearningConfig.EMA_ALPHA
WEAK_THRESHOLD = AdaptiveLearningConfig.WEAK_THRESHOLD
MODERATE_THRESHOLD = AdaptiveLearningConfig.MODERATE_THRESHOLD
normalize_concept = AdaptiveLearningConfig.normalize_concept


if __name__ == "__main__":
    # Test configuration
    print("=== Adaptive Learning Configuration ===")
    print(f"Version: {AdaptiveLearningConfig.CONFIG_VERSION}")
    
    # Test normalization
    test_concepts = [
        "Time & Distance",
        "3D Mensuration",
        "  Ratios / Proportions  ",
        "Simple Interest"
    ]
    
    print("\n=== Concept Normalization Tests ===")
    for concept in test_concepts:
        normalized = AdaptiveLearningConfig.normalize_concept(concept)
        print(f"{concept:30} -> {normalized}")
    
    # Test validation
    errors = AdaptiveLearningConfig.validate_config()
    if errors:
        print(f"\n❌ Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))
    else:
        print("\n✅ Configuration validated successfully")
    
    # Show snapshot
    import json
    print("\n=== Configuration Snapshot ===")
    print(json.dumps(AdaptiveLearningConfig.get_config_snapshot(), indent=2))
```

**Add config version to analytics tables:**
```sql
-- Migration: Add config version tracking to analytics tables
ALTER TABLE session_summary_final 
ADD COLUMN config_version VARCHAR(20) DEFAULT '1.0.0';

ALTER TABLE learner_notebook 
ADD COLUMN config_version VARCHAR(20) DEFAULT '1.0.0';

ALTER TABLE coverage_debt 
ADD COLUMN config_version VARCHAR(20) DEFAULT '1.0.0';

COMMENT ON COLUMN session_summary_final.config_version 
IS 'Config version used to generate this summary (for audit trail)';
```

**Update code to use centralized config:**

File: `backend/services/simplified_job_handlers.py`

```python
# Replace hardcoded constants with imports
from config.adaptive_learning_config import (
    EMA_ALPHA,
    WEAK_THRESHOLD,
    MODERATE_THRESHOLD,
    normalize_concept,
    AdaptiveLearningConfig
)

# In update_learner_notebook():
def calculate_mastery_score(old_score, was_correct):
    """Calculate new mastery score using EMA"""
    adjustment = (
        AdaptiveLearningConfig.MASTERY_INCREASE_ON_CORRECT 
        if was_correct 
        else AdaptiveLearningConfig.MASTERY_DECREASE_ON_WRONG
    )
    
    # EMA formula: new = alpha * observation + (1-alpha) * old
    observation = old_score + adjustment
    new_score = EMA_ALPHA * observation + (1 - EMA_ALPHA) * old_score
    
    # Clamp to [0, 1]
    return max(0.0, min(1.0, new_score))

def get_readiness(mastery_score):
    """Convert mastery score to readiness label"""
    if mastery_score < WEAK_THRESHOLD:
        return "Weak"
    elif mastery_score < MODERATE_THRESHOLD:
        return "Moderate"
    else:
        return "Strong"

# In concept normalization:
for concept in concepts:
    semantic_id = normalize_concept(concept)
    # ...
```

---

## Task 4.2: Worker Deployment Automation

**Status:** PENDING  
**Duration:** 1 hour  
**File:** `backend/scripts/deploy_workers.sh` (NEW)

### Implementation Details

**Deployment Script:**
```bash
#!/bin/bash
# Safe worker deployment script
# Ensures clean deployments with verification

set -e  # Exit on error

echo "============================================"
echo "  TWELVR - Worker Deployment Script"
echo "============================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BACKEND_DIR="/app/backend"
LOG_DIR="/var/log/supervisor"
WORKER_NAMES="bg_workers:*"

# Step 1: Pre-flight checks
echo "1️⃣  Pre-flight checks..."
echo "   Checking Python syntax..."
cd $BACKEND_DIR
python3 -m py_compile services/simplified_job_handlers.py
python3 -m py_compile services/bg_job_queue.py
if [ $? -eq 0 ]; then
    echo -e "   ${GREEN}✅ Syntax check passed${NC}"
else
    echo -e "   ${RED}❌ Syntax errors found - aborting${NC}"
    exit 1
fi

# Step 2: Clear Python bytecode cache
echo ""
echo "2️⃣  Clearing Python bytecode cache..."
find $BACKEND_DIR -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find $BACKEND_DIR -type f -name "*.pyc" -delete 2>/dev/null || true
echo -e "   ${GREEN}✅ Cache cleared${NC}"

# Step 3: Show code changes (if git available)
echo ""
echo "3️⃣  Recent code changes:"
if command -v git &> /dev/null; then
    cd /app
    git diff HEAD~1 HEAD --stat 2>/dev/null || echo "   No git history available"
else
    echo "   Git not available - skipping"
fi

# Step 4: Check worker status before restart
echo ""
echo "4️⃣  Current worker status:"
sudo supervisorctl status $WORKER_NAMES

# Step 5: Rolling restart
echo ""
echo "5️⃣  Restarting workers..."
echo "   Stopping workers..."
sudo supervisorctl stop $WORKER_NAMES
sleep 2

echo "   Starting workers..."
sudo supervisorctl start $WORKER_NAMES
sleep 3

echo -e "   ${GREEN}✅ Workers restarted${NC}"

# Step 6: Verify workers are running
echo ""
echo "6️⃣  Verifying worker startup..."
WORKER_STATUS=$(sudo supervisorctl status $WORKER_NAMES | grep RUNNING | wc -l)
EXPECTED_WORKERS=2

if [ "$WORKER_STATUS" -eq "$EXPECTED_WORKERS" ]; then
    echo -e "   ${GREEN}✅ All $EXPECTED_WORKERS workers running${NC}"
else
    echo -e "   ${RED}❌ Only $WORKER_STATUS/$EXPECTED_WORKERS workers running${NC}"
    echo "   Worker status:"
    sudo supervisorctl status $WORKER_NAMES
    exit 1
fi

# Step 7: Check for immediate errors
echo ""
echo "7️⃣  Checking for startup errors..."
sleep 5
ERROR_COUNT=$(tail -100 $LOG_DIR/bg_worker_*.err.log 2>/dev/null | grep -i error | wc -l)

if [ "$ERROR_COUNT" -gt 0 ]; then
    echo -e "   ${YELLOW}⚠️  Found $ERROR_COUNT errors in logs (last 100 lines)${NC}"
    echo "   Recent errors:"
    tail -100 $LOG_DIR/bg_worker_*.err.log 2>/dev/null | grep -i error | tail -5
    echo ""
    echo -e "   ${YELLOW}Check logs with: tail -f $LOG_DIR/bg_worker_*.err.log${NC}"
else
    echo -e "   ${GREEN}✅ No errors detected${NC}"
fi

# Step 8: Verify workers are processing jobs
echo ""
echo "8️⃣  Verifying job processing..."
sleep 10

# Check if any jobs have been processed in last minute
RECENT_JOBS=$(cd $BACKEND_DIR && python3 << 'EOF'
import psycopg2
import os
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cursor = conn.cursor()
cursor.execute("""
    SELECT COUNT(*) 
    FROM bg_jobs 
    WHERE started_at > NOW() - INTERVAL '1 minute'
    OR completed_at > NOW() - INTERVAL '1 minute'
""")
count = cursor.fetchone()[0]
print(count)
cursor.close()
conn.close()
EOF
)

if [ "$RECENT_JOBS" -gt 0 ]; then
    echo -e "   ${GREEN}✅ Workers are processing jobs ($RECENT_JOBS jobs in last minute)${NC}"
else
    echo -e "   ${YELLOW}⚠️  No jobs processed in last minute (may be normal if queue is empty)${NC}"
fi

# Step 9: Display worker logs
echo ""
echo "9️⃣  Recent worker logs:"
tail -20 $LOG_DIR/bg_worker_1.out.log | head -10

# Step 10: Summary
echo ""
echo "============================================"
echo -e "  ${GREEN}✅ DEPLOYMENT COMPLETE${NC}"
echo "============================================"
echo ""
echo "📊 Next steps:"
echo "   1. Monitor logs: tail -f $LOG_DIR/bg_worker_*.out.log"
echo "   2. Check health: curl localhost:8001/api/admin/pipeline-health"
echo "   3. Watch job queue: watch -n 5 'psql \$DATABASE_URL -c \"SELECT status, COUNT(*) FROM bg_jobs GROUP BY status\"'"
echo ""
echo "🔴 Rollback (if needed):"
echo "   sudo supervisorctl restart $WORKER_NAMES"
echo ""
```

**Make executable:**
```bash
chmod +x /app/backend/scripts/deploy_workers.sh
```

**Usage:**
```bash
# Deploy workers
cd /app/backend
./scripts/deploy_workers.sh

# Or from anywhere
bash /app/backend/scripts/deploy_workers.sh
```

---

## Task 4.3: Code Hash Verification

**Status:** PENDING  
**Duration:** 30 minutes  
**File:** `backend/services/bg_worker.py` (UPDATE)

### Implementation Details

**Add to worker startup:**
```python
# At top of file
import hashlib
from pathlib import Path

def calculate_code_hash(files: List[str]) -> str:
    """
    Calculate SHA256 hash of critical code files
    
    Args:
        files: List of file paths relative to backend/
        
    Returns:
        Hex digest of combined file hashes
    """
    hasher = hashlib.sha256()
    
    backend_dir = Path(__file__).parent.parent
    
    for file_path in sorted(files):  # Sort for consistency
        full_path = backend_dir / file_path
        
        if not full_path.exists():
            logger.warning(f"Code hash: File not found: {file_path}")
            continue
        
        with open(full_path, 'rb') as f:
            content = f.read()
            hasher.update(content)
    
    return hasher.hexdigest()


def get_current_code_hash() -> str:
    """Get hash of current worker code"""
    critical_files = [
        "services/simplified_job_handlers.py",
        "services/bg_job_queue.py",
        "services/bg_worker.py",
        "config/adaptive_learning_config.py"
    ]
    
    return calculate_code_hash(critical_files)


# In worker startup:
async def start_worker(worker_id: int):
    """Start background worker with code hash verification"""
    
    # Calculate and log code hash
    code_hash = get_current_code_hash()
    logger.info(f"🔒 Worker {worker_id} starting with code hash: {code_hash[:12]}...")
    
    # Store code hash in database for monitoring
    try:
        db = get_db_session()
        db.execute(text("""
            INSERT INTO worker_deployments (
                worker_id,
                code_hash,
                started_at,
                config_version
            ) VALUES (
                :worker_id,
                :code_hash,
                NOW(),
                :config_version
            )
        """), {
            "worker_id": worker_id,
            "code_hash": code_hash,
            "config_version": AdaptiveLearningConfig.CONFIG_VERSION
        })
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to log deployment: {e}")
    
    # Continue with normal worker startup...
    logger.info(f"🚀 Worker {worker_id} started and ready to process jobs")
    
    # Main loop
    await job_queue.worker_loop(worker_id)
```

**Create worker deployments table:**
```sql
-- Migration: Track worker deployments for debugging

CREATE TABLE IF NOT EXISTS worker_deployments (
    id SERIAL PRIMARY KEY,
    worker_id INTEGER,
    code_hash VARCHAR(64),
    config_version VARCHAR(20),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    stopped_at TIMESTAMPTZ
);

CREATE INDEX idx_worker_deployments_started ON worker_deployments(started_at DESC);

COMMENT ON TABLE worker_deployments 
IS 'Tracks worker restarts and code versions for debugging';
```

**Add endpoint to check worker versions:**
```python
# In backend/api/health.py

@router.get("/pipeline-health/workers")
async def get_worker_status(db = Depends(get_db_session)) -> List[Dict]:
    """Get status of all workers including code versions"""
    
    result = db.execute(text("""
        SELECT 
            worker_id,
            code_hash,
            config_version,
            started_at,
            EXTRACT(EPOCH FROM (NOW() - started_at))/3600 as uptime_hours
        FROM worker_deployments
        WHERE stopped_at IS NULL
        ORDER BY started_at DESC
    """)).fetchall()
    
    workers = []
    for wid, hash, config, started, uptime in result:
        workers.append({
            "worker_id": wid,
            "code_hash": hash[:12] + "...",
            "config_version": config,
            "started_at": started.isoformat(),
            "uptime_hours": round(float(uptime), 1)
        })
    
    # Check if all workers have same code hash
    unique_hashes = set(w["code_hash"] for w in workers)
    version_mismatch = len(unique_hashes) > 1
    
    return {
        "workers": workers,
        "total_workers": len(workers),
        "version_mismatch": version_mismatch,
        "warning": "Workers are running different code versions!" if version_mismatch else None
    }
```

---

## Phase 4 Completion Checklist

- [ ] Adaptive learning config module created
- [ ] All hardcoded constants replaced with config imports
- [ ] Config version added to analytics tables
- [ ] Worker deployment script created and tested
- [ ] Code hash verification implemented
- [ ] Worker deployment tracking table created
- [ ] Documentation updated

**Success Criteria:**
- ✅ All config centralized in single module
- ✅ Config validation on import
- ✅ Worker deployment automated and safe
- ✅ Code hash tracked for debugging
- ✅ Audit trail for config changes

---

# TESTING STRATEGY

## Unit Tests

**Create:** `backend/tests/test_adaptive_config.py`
```python
import pytest
from config.adaptive_learning_config import AdaptiveLearningConfig, normalize_concept

def test_config_validation():
    errors = AdaptiveLearningConfig.validate_config()
    assert len(errors) == 0, f"Config validation failed: {errors}"

def test_concept_normalization():
    assert normalize_concept("Time & Distance") == "time_distance"
    assert normalize_concept("3D Mensuration") == "3d_mensuration"
    assert normalize_concept("  Ratios / Proportions  ") == "ratios_proportions"

def test_ema_bounds():
    assert 0 <= AdaptiveLearningConfig.EMA_ALPHA <= 1

def test_pack_size_consistency():
    total = sum(AdaptiveLearningConfig.DIFFICULTY_DISTRIBUTION.values())
    assert total == AdaptiveLearningConfig.PACK_SIZE
```

**Run tests:**
```bash
cd /app/backend
pytest tests/ -v --tb=short
```

## Integration Tests

**Create:** `backend/tests/test_integration_backfill.py`
```python
import pytest
import asyncio
from services.bg_job_queue import job_queue

@pytest.mark.asyncio
async def test_summarize_job_with_postconditions():
    """Test that SUMMARIZE_SESSION job validates writes"""
    
    # Enqueue job for known completed session
    job_id = await job_queue.enqueue_job(
        job_type="SUMMARIZE_SESSION",
        user_id="test-user-id",
        session_id="test-session-id"
    )
    
    # Wait for processing
    await asyncio.sleep(10)
    
    # Check job status
    db = get_db_session()
    result = db.execute(text("""
        SELECT status, error_message 
        FROM bg_jobs 
        WHERE id = :job_id
    """), {"job_id": job_id}).fetchone()
    
    assert result[0] in ["succeeded", "failed"]
    
    if result[0] == "failed":
        # Should fail with post-condition error if writes didn't happen
        assert "POST-CONDITION FAILED" in result[1]
```

---

# ROLLBACK PROCEDURES

## Phase 1 Rollback

**If post-conditions cause issues:**
```python
# Remove post-condition blocks from simplified_job_handlers.py
# Lines to remove: 196-229 (the POST-CONDITION block)

# Restart workers
sudo supervisorctl restart bg_workers:*
```

**If backfill causes problems:**
```sql
-- Stop workers
sudo supervisorctl stop bg_workers:*

-- Clear queued backfill jobs
DELETE FROM bg_jobs 
WHERE job_type = 'SUMMARIZE_SESSION'
AND status = 'queued'
AND created_at > NOW() - INTERVAL '1 hour';

-- Restart workers
sudo supervisorctl start bg_workers:*
```

## Phase 2 Rollback

**Remove UUID validation:**
```bash
psql $DATABASE_URL -f backend/migrations/026_add_uuid_validation_rollback.sql
```

**Remove foreign keys:**
```bash
psql $DATABASE_URL -f backend/migrations/027_add_foreign_keys_rollback.sql
```

## Phase 3 Rollback

**Remove health infrastructure:**
```sql
DROP TABLE IF EXISTS pipeline_health_metrics CASCADE;
DROP MATERIALIZED VIEW IF EXISTS mv_orphaned_sessions CASCADE;
DROP MATERIALIZED VIEW IF EXISTS mv_job_performance_24h CASCADE;
DROP TABLE IF EXISTS pipeline_sli_events CASCADE;
DROP FUNCTION IF EXISTS update_pipeline_health_metrics CASCADE;
```

**Remove health endpoint:**
```python
# Comment out in backend/api/server.py
# app.include_router(health_router)
```

## Phase 4 Rollback

**Revert to hardcoded constants:**
```python
# In simplified_job_handlers.py
# Replace imports with:
EMA_ALPHA = 0.3
WEAK_THRESHOLD = 0.4
MODERATE_THRESHOLD = 0.7

def normalize_concept(concept: str) -> str:
    return concept.lower().strip().replace(" ", "_")
```

---

# APPROVAL REQUIRED

**Review this detailed technical plan and approve to proceed with:**

1. ✅ **Phase 1:** Post-conditions + Backfill (Hours 0-8)
2. ✅ **Phase 2:** Type standardization + Foreign keys (Hours 8-24)
3. ✅ **Phase 3:** Observability + SLI tracking (Hours 24-36)
4. ✅ **Phase 4:** Config centralization + Deployment automation (Hours 36-48)

**Questions for approval:**
- Should I proceed with all 4 phases or specific phases only?
- Do you want to review after each phase completion?
- Any specific concerns about type standardization approach (VARCHAR vs UUID)?
- Should health dashboard be admin-only or public?

---

**Last Updated:** September 30, 2025 19:00 UTC  
**Document Version:** 1.0  
**Status:** AWAITING APPROVAL

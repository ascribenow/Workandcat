# Admin Dashboard "Fix & Regenerate Pack" Button - Complete Documentation

## What Does the Fix Button Do?

The "Fix & Regenerate Pack" button (endpoint: `/api/admin/fix-user-jobs`) performs a **4-step automated repair workflow** for users experiencing session or job issues.

---

## Step-by-Step Process:

### **STEP 1: Delete Exhausted Jobs**
```sql
DELETE FROM bg_jobs
WHERE user_id = :user_id
AND attempts >= max_attempts
```

**What it does:**
- Finds jobs that have exceeded their retry limit (exhausted)
- **DELETES** these jobs permanently from the queue
- These jobs are blocking the dedupe key and preventing new jobs from being enqueued

**Example:**
- If a PLAN_NEXT_SESSION job failed 6 times (max_attempts = 6)
- It becomes "exhausted" and blocks new PLAN_NEXT_SESSION jobs
- Fix button deletes it, freeing the dedupe key

**Does it kill enqueued jobs?**
- ❌ NO - Only kills jobs that are EXHAUSTED (failed max times)
- ✅ YES - But only dead jobs that were blocking the system

---

### **STEP 2: Cancel Stuck Jobs**
```sql
UPDATE bg_jobs
SET status = 'failed',
    error_message = 'Auto-cancelled: stuck in running state for > 10 minutes'
WHERE user_id = :user_id
AND status = 'running'
AND started_at < (NOW() - 10 minutes)
```

**What it does:**
- Finds jobs that started running but got stuck for >10 minutes
- Changes their status from 'running' to 'failed'
- Does NOT delete them (keeps for audit trail)

**Example:**
- A SUMMARIZE_SESSION job started at 10:00 AM
- At 10:15 AM, it's still marked as 'running' (hung/crashed)
- Fix button marks it as 'failed' and adds error message

**Does it kill enqueued jobs?**
- ❌ NO - Only marks stuck RUNNING jobs as failed
- Does not touch 'queued' jobs

---

### **STEP 3: Fix Sessions with Empty Packs**
```sql
-- Find sessions with no questions
SELECT s.session_id, s.sess_seq
FROM sessions s
WHERE s.user_id = :user_id
AND s.status IN ('planned', 'active')
AND NOT EXISTS (
    SELECT 1 FROM session_pack_questions spq
    WHERE spq.session_id::text = s.session_id::text
)
```

**What it does:**
- Finds sessions that exist but have no questions (empty packs)
- For each empty session:
  1. Calls `gather_user_learning_data(user_id)` to get learner state
  2. Calls `generate_personalized_session_pack(user_id, learning_data)` to create pack
  3. Inserts the pack into `session_packs` table
  4. Inserts all 12 questions into `session_pack_questions` table
- This is **synchronous** - happens immediately during the button click

**Example:**
- User has Session #8 in status 'active'
- But session_pack_questions table is empty for this session
- Fix button generates a fresh pack with 12 questions and inserts them

**Does it kill enqueued jobs?**
- ❌ NO - This step doesn't touch jobs at all
- Just generates packs for broken sessions

---

### **STEP 4: Enqueue New PLAN_NEXT_SESSION Job (If Needed)**
```sql
-- Check if user has a valid pre-pack
SELECT EXISTS (
    SELECT 1 
    FROM sessions s
    JOIN session_pack_questions spq ON s.session_id::text = spq.session_id::text
    WHERE s.user_id = :user_id
    AND s.status IN ('planned', 'active')
    GROUP BY s.session_id
    HAVING COUNT(spq.position) >= 12
)
```

**What it does:**
- Checks if user has a valid pre-generated pack ready
- If NO valid pack exists:
  - Enqueues a NEW PLAN_NEXT_SESSION job
  - This job will generate a fresh pack for the next session
- If valid pack EXISTS:
  - Skips enqueuing (no need)

**Example:**
- User completed all sessions and has no pre-pack
- Fix button enqueues PLAN_NEXT_SESSION to generate one
- Job runs in background and creates pack within ~10 seconds

**Does it kill enqueued jobs?**
- ❌ NO - This step CREATES a new job, doesn't kill existing ones

---

## Summary Table: What Gets Killed?

| Job Status | Action Taken | Reason |
|------------|--------------|--------|
| **queued** (normal) | ❌ NOT touched | Waiting to run, should process normally |
| **queued** (exhausted) | ✅ DELETED | Failed max times, blocking dedupe key |
| **running** (<10 min) | ❌ NOT touched | Actively processing |
| **running** (>10 min) | ⚠️ Marked as failed | Stuck/hung, needs cleanup |
| **succeeded** | ❌ NOT touched | Already completed |
| **failed** (normal) | ❌ NOT touched | Already failed, kept for audit |

---

## Does the Fix Button Kill Enqueued Jobs?

**Answer: Only specific ones**

✅ **YES - It DELETES:**
- Exhausted jobs (attempts >= max_attempts)
- These are jobs that failed multiple times and are blocking new jobs

❌ **NO - It DOES NOT KILL:**
- Normal queued jobs waiting to run
- Running jobs under 10 minutes old
- Succeeded jobs
- Failed jobs (for audit trail)

---

## When Should You Use the Fix Button?

**Use it when:**
1. ✅ User has exhausted jobs blocking new sessions
2. ✅ User has stuck jobs running forever (>10 min)
3. ✅ User has empty session packs (session exists but no questions)
4. ✅ User has no pre-pack and can't start next session

**Don't use it when:**
1. ❌ User has normal queued jobs processing
2. ❌ User has jobs running under 10 minutes (let them finish)
3. ❌ User just completed a session (wait for automatic processing)

---

## What Happens After Clicking Fix?

**Immediate (Synchronous):**
1. Exhausted jobs deleted (instant)
2. Stuck jobs marked as failed (instant)
3. Empty sessions get packs generated (2-5 seconds per session)

**Background (Asynchronous):**
4. New PLAN_NEXT_SESSION job enqueued (if needed)
5. Job worker picks it up within seconds
6. Pack generation happens (~10-20 seconds)
7. User has fresh pre-pack ready

---

## Response Example:

```json
{
  "success": true,
  "message": "Fixed user sp@theskinmantra.com",
  "actions_taken": [
    "Deleted 1 exhausted jobs",
    "Cancelled 0 stuck jobs",
    "Found 0 sessions with empty packs",
    "Enqueued new PLAN_NEXT_SESSION job"
  ],
  "deleted_jobs_count": 1,
  "stuck_jobs_cancelled": 0,
  "empty_sessions_fixed": 0,
  "new_job_id": "abc123...",
  "user_email": "sp@theskinmantra.com"
}
```

---

## Safety Mechanisms:

1. **Idempotency Check:** Won't create duplicate packs if one already exists
2. **Transaction Safety:** All DB operations are within transactions
3. **Error Handling:** If one step fails, others still execute
4. **Audit Trail:** Keeps failed jobs for debugging (doesn't delete)
5. **Session Validation:** Only fixes sessions in 'planned' or 'active' state

---

## Key Differences from Manual Job Cleanup:

| Action | Fix Button | Manual Cleanup |
|--------|-----------|----------------|
| Delete exhausted jobs | ✅ Automatic | Must write SQL |
| Cancel stuck jobs | ✅ Automatic | Must identify manually |
| Fix empty packs | ✅ Generates packs | Must run scripts |
| Enqueue new jobs | ✅ Smart detection | Must trigger manually |
| All-in-one | ✅ Yes | ❌ Multiple steps |

---

## Conclusion:

The Fix button is a **surgical tool** that:
- ✅ Cleans up dead/exhausted jobs blocking the system
- ✅ Fixes stuck jobs that hung
- ✅ Repairs broken sessions with missing questions
- ✅ Ensures user has a pre-pack ready

It does **NOT** indiscriminately kill all enqueued jobs. It only removes problematic jobs that are already failed or blocking the system.


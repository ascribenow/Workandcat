# 🔍 Adaptive Session Flow - Complete Analysis

## Executive Summary

**Critical Issue Identified:** The system has **TWO SEPARATE SESSION COMPLETION ENDPOINTS** that can lead to inconsistent behavior:
1. `/api/session/complete` (blueprint_sessions.py) - ✅ **WORKS** - Triggers background jobs
2. `/mark-completed` (session_lifecycle.py) - ⚠️ **DEPRECATED** - Also triggers background jobs but redundant

**Root Cause:** Frontend might be calling wrong endpoint or not calling completion at all.

---

## 📊 Complete Adaptive Session Flow

### **PHASE 1: Session Start**

#### Entry Point: `POST /api/session/start`
**File:** `backend/api/blueprint_sessions.py` (Lines 61-251)

**Flow:**
```
1. User Authentication & Validation
   └─> validate_canonical_uuid() - Ensure valid UUID format
   └─> Check auth_user_id matches request user_id

2. Access Control Check
   ├─> Get user from database
   ├─> Check subscription level (Pro/Free)
   └─> For Free Tier:
       ├─> Check session availability via FreeTierSessionService
       ├─> Enforce 5 initial + 2/week limits
       └─> Block if limit exceeded (403 error)

3. Insights Cache Check (Optional)
   └─> If insights >4 hours old:
       └─> Enqueue UPDATE_INSIGHTS job

4. Session Creation/Retrieval
   ├─> Call blueprint_planner.plan_session()
   └─> Uses pre-packed session if available
       └─> Otherwise creates new session on-the-fly

5. Calculate Session Number
   └─> Count completed sessions + 1

6. Check for Resume Logic
   └─> If session exists with 'active'/'planned' status:
       └─> Resume from saved position
   └─> Else: Start from position 1

7. Return Response
   └─> Session ID, questions, status, position
```

**Key Functions:**
- `start_session()` - Main entry point
- `BlueprintSessionPlanner.plan_session()` - Session creation
- `free_tier_service.get_user_session_status()` - Access control

**Database Tables Updated:**
- `sessions` - Creates/updates session record
- `session_packs` - Links to pre-packed questions
- Potentially triggers `UPDATE_INSIGHTS` job

---

### **PHASE 2: Question Serving**

#### Entry Points:
- `GET /api/session/questions/{session_id}` - Get all 12 questions at once
- `GET /api/session/question/{session_id}/{position}` - Get single question

**File:** `backend/api/blueprint_sessions.py` (Lines 292-438)

**Flow:**
```
1. Validate session_id UUID format
2. Retrieve questions from database via:
   └─> BlueprintSessionPlanner._get_session_questions()
3. Format questions for frontend
4. Sort by position (1-12)
5. Return with metadata
```

**Key Tables:**
- `session_pack_questions` - Stores question position mappings
- `questions` - Question content, options, answers

---

### **PHASE 3: Answer Submission**

#### Entry Point: `POST /api/session/submit`
**File:** `backend/api/blueprint_sessions.py` (Lines 440-711)

**Flow:**
```
1. Validate UUIDs (session_id, auth_user_id)
2. Validate position (1-12)
3. Retrieve session questions
4. Find question at specified position
5. Check if answer is correct
6. Store answer in TWO tables:
   ├─> session_answers - User responses
   └─> attempt_events - For analytics/dashboard
7. Update session progress (real-time):
   └─> questions_answered, questions_correct, questions_skipped, current_position
8. Fetch solution feedback
9. Return result with solution
```

**Key Database Operations:**
```sql
-- Insert/Update session_answers
INSERT INTO session_answers (session_id, position, question_id, user_answer, is_correct, ...)
ON CONFLICT (session_id, position) DO UPDATE ...

-- Insert/Update attempt_events
INSERT INTO attempt_events (user_id, session_id, question_id, was_correct, skipped, ...)
ON CONFLICT (user_id, session_id, sess_seq_at_serve) DO UPDATE ...

-- Real-time progress update
UPDATE sessions 
SET questions_answered = X, questions_correct = Y, questions_skipped = Z, current_position = N
WHERE session_id = ...
```

**Tables Updated:**
- `session_answers` - User responses
- `attempt_events` - Analytics events
- `sessions` - Real-time progress

---

### **PHASE 4: Session Completion** ⚠️ **CRITICAL SECTION**

#### **TWO ENDPOINTS EXIST:**

#### **Option A: PRIMARY ENDPOINT** ✅ **RECOMMENDED**
**Endpoint:** `POST /api/session/complete`
**File:** `backend/api/blueprint_sessions.py` (Lines 873-1065)

**Complete Flow:**
```
1. Validate UUIDs
2. Retrieve all answers from session_answers table
3. Calculate final statistics:
   ├─> Total questions
   ├─> Answered questions (non-empty user_answer)
   ├─> Skipped questions (empty user_answer)
   ├─> Correct answers
   └─> Accuracy percentage

4. IDEMPOTENT CHECK:
   └─> Query sessions table for existing completion
   └─> If already completed:
       ├─> Return existing correlation_id
       └─> Skip background job enqueue (idempotent)
   └─> Else (first completion):
       ├─> Generate new correlation_id
       ├─> Update sessions table:
           ├─> status = 'completed'
           ├─> completed_at = NOW()
           ├─> questions_answered, questions_correct, questions_skipped
           └─> correlation_id
       └─> Commit transaction

5. Check for 5th Session Email:
   └─> If user completed exactly 5 sessions:
       └─> Send free tier transition email

6. BACKGROUND JOB PIPELINE:
   └─> If session was just completed (not idempotent):
       ├─> Import job_queue
       └─> Enqueue SUMMARIZE_SESSION job:
           ├─> job_type: "SUMMARIZE_SESSION"
           ├─> user_id
           ├─> session_id
           └─> correlation_id (for tracing)
       └─> Set bg_jobs_enqueued = True

7. Return Response:
   ├─> success: true
   ├─> session_completed: true
   ├─> correlation_id
   ├─> background_jobs_enqueued
   └─> summary (stats, accuracy, trace_url)
```

**Key Code (Lines 1010-1038):**
```python
if existing_session and existing_session[0] == 'completed':
    # Already completed - skip job enqueue (idempotent)
    logger.info(f"Session {session_id[:8]} already completed, skipping job enqueue")
    bg_jobs_enqueued = True
else:
    # First completion - enqueue background jobs
    from services.bg_job_queue import job_queue
    
    summarization_job_id = await job_queue.enqueue_job(
        job_type="SUMMARIZE_SESSION",
        user_id=auth_user_id,
        session_id=session_id,
        correlation_id=correlation_id
    )
    bg_jobs_enqueued = True
    logger.info(f"🚀 Enqueued SUMMARIZE_SESSION job {summarization_job_id[:8]}")
```

---

#### **Option B: LEGACY ENDPOINT** ⚠️ **POTENTIALLY PROBLEMATIC**
**Endpoint:** `POST /mark-completed`
**File:** `backend/api/session_lifecycle.py` (Lines 26-39)

**Flow:**
```
1. Extract session_id from payload
2. Call mark_session_completed() function
3. Return {"ok": True}
```

**Calls:** `services.session_completion.mark_session_completed()` (Lines 70-215)

**This Function's Flow:**
```
1. Update sessions table:
   └─> completed_at = COALESCE(completed_at, NOW())
   └─> status = 'completed' if not already

2. Update session_pack_plan table (legacy):
   └─> completed_at timestamp

3. DUPLICATE JOB ENQUEUE LOGIC (Lines 119-148):
   ├─> Check if SUMMARIZE_SESSION job already exists
   └─> If not: Enqueue job

4. DUPLICATE JOB ENQUEUE LOGIC AGAIN (Lines 167-202):
   ├─> Check if SUMMARIZE_SESSION job exists (AGAIN!)
   └─> If not: Enqueue job using asyncio.new_event_loop()

5. Return True
```

**⚠️ PROBLEMS WITH THIS ENDPOINT:**
- **Duplicate logic** - Enqueues job TWICE in same function
- **No idempotent protection** - Can enqueue multiple jobs for same session
- **Legacy patterns** - Updates session_pack_plan (deprecated table?)
- **Complex asyncio handling** - Creates new event loop (can cause issues)
- **Less comprehensive** - Doesn't calculate final stats like Option A

---

### **PHASE 5: Background Job Pipeline** 🚀

#### **Job 1: SUMMARIZE_SESSION**
**Handler:** `services.simplified_job_handlers.handle_summarize_session()`

**Flow:**
```
1. Extract session data and user info
2. Retrieve all attempt_events for session
3. Generate session summary using LLM:
   ├─> Performance metrics
   ├─> Topic-wise breakdown
   ├─> Strengths & weaknesses
   └─> Recommendations

4. Store in session_summary_final table
5. Update learner_notebook with concepts
6. **CHAIN NEXT JOB:**
   └─> Enqueue PLAN_NEXT_SESSION job
       └─> Same user_id
       └─> Same correlation_id

7. Return success
```

**Tables Updated:**
- `session_summary_final` - Session summaries
- `learner_notebook` - Concept mastery tracking

**Next Job Triggered:** `PLAN_NEXT_SESSION`

---

#### **Job 2: PLAN_NEXT_SESSION**
**Handler:** `services.simplified_job_handlers.handle_plan_next_session()`

**Flow:**
```
1. Analyze user's learning history
2. Select 12 questions using adaptive algorithm:
   ├─> 3 Easy (confidence building)
   ├─> 6 Medium (skill development)
   └─> 3 Hard (challenge)

3. Apply constraints:
   ├─> No repeat questions
   ├─> Topic coverage
   ├─> Difficulty progression
   └─> PYQ frequency balance

4. Create session pack:
   ├─> Insert into session_packs table
   └─> Insert 12 questions into session_pack_questions

5. **CHAIN NEXT JOB:**
   └─> Enqueue UPDATE_INSIGHTS job
       └─> Refresh dashboard insights

6. Return success
```

**Tables Updated:**
- `session_packs` - New session pack
- `session_pack_questions` - 12 question mappings

**Next Job Triggered:** `UPDATE_INSIGHTS`

---

#### **Job 3: UPDATE_INSIGHTS**
**Handler:** `services.simplified_job_handlers.handle_update_insights()`

**Flow:**
```
1. Aggregate user performance data
2. Generate personalized insights:
   ├─> Strengths by topic
   ├─> Areas needing improvement
   ├─> Progress trends
   └─> Motivational messages

3. Store in user_dashboard_insights table
4. Set cache timestamp

5. Return success (END OF CHAIN)
```

**Tables Updated:**
- `user_dashboard_insights` - User insights cache

---

## 🔍 Problem Analysis: Why Background Jobs Aren't Triggering

### **Hypothesis 1: Frontend Not Calling Completion Endpoint**

**Evidence:**
- Users manually completed sessions but no background jobs found
- Both users (twelvrhelp@gmail.com, jainved33@gmail.com) had this issue
- Sessions marked as completed in database but no job history

**Likely Cause:**
```
Frontend might be:
1. Not calling ANY completion endpoint
2. Only updating local state
3. Relying on real-time updates from /submit endpoint
4. Assuming completion happens automatically after Q12
```

**Investigation Needed:**
- Check frontend code for session completion logic
- Search for POST calls to /complete or /mark-completed
- Check if there's automatic completion after position 12

---

### **Hypothesis 2: Using Wrong Endpoint**

**If using `/mark-completed` (legacy endpoint):**

**Problems:**
1. Duplicate job enqueue logic (2 attempts in same function)
2. Race conditions with asyncio.new_event_loop()
3. No proper idempotent protection
4. Can fail silently

**Code Issues (session_completion.py, Lines 119-202):**
```python
# FIRST ATTEMPT (Lines 119-148)
existing_job = db_check.execute(...)
if not existing_job:
    job_id = await job_queue.enqueue_job(...)

# SECOND ATTEMPT (Lines 167-202) - DUPLICATE!
existing_job = db.execute(...)
if not existing_job:
    loop = asyncio.new_event_loop()  # ⚠️ Can cause issues
    job_id = loop.run_until_complete(job_queue.enqueue_job(...))
```

**This can cause:**
- Multiple jobs for same session
- Event loop conflicts
- Job queue corruption
- Silent failures

---

### **Hypothesis 3: Dedupe Key Blocking**

**Dedupe Key Format:**
```python
dedupe_key = f"u:{user_id}|s:{session_id}|SUMMARIZE_SESSION"
```

**Potential Issue:**
- If old job exists with same dedupe key but exhausted retries
- New jobs can't be created due to UNIQUE constraint
- ON CONFLICT DO UPDATE resets the old job
- But if old job has attempts >= max_attempts, worker won't pick it up

**Solution Already Identified:**
- Need to clean up old exhausted jobs
- Or improve dedupe key specificity

---

### **Hypothesis 4: Idempotent Logic Too Aggressive**

**In `/api/session/complete` (Lines 1014-1017):**
```python
if existing_session and existing_session[0] == 'completed':
    logger.info("Session already completed, skipping job enqueue (idempotent)")
    bg_jobs_enqueued = True  # ⚠️ Assumes jobs were enqueued before
```

**Problem:**
- If session was marked completed by OTHER means (manual DB update?)
- Or completed via legacy endpoint that failed to enqueue jobs
- This endpoint will skip job enqueue thinking it already happened
- But jobs might never have been created!

**Fix Needed:**
- Check if jobs ACTUALLY exist before skipping
- Don't just assume jobs were enqueued

---

## 🔧 Identified Issues & Conflicts

### **Issue 1: Dual Completion Endpoints** ⚠️ **HIGH PRIORITY**

**Conflict:**
```
/api/session/complete (blueprint_sessions.py)
    vs
/mark-completed (session_lifecycle.py)
```

**Problems:**
- Confusion about which endpoint to use
- Different behavior (one comprehensive, one legacy)
- Frontend might be using wrong one
- Can cause duplicate job enqueue attempts

**Resolution:**
- **Deprecate** `/mark-completed` endpoint
- **Standardize** on `/api/session/complete`
- **Update** frontend to use correct endpoint
- **Add** endpoint routing documentation

---

### **Issue 2: Duplicate Job Enqueue Logic** ⚠️ **HIGH PRIORITY**

**Location:** `session_completion.py`, Lines 119-148 and 167-202

**Problem:**
```python
# Job enqueue attempt #1
try:
    logger.info("Enqueueing SUMMARIZE_SESSION job...")
    job_id = await job_queue.enqueue_job(...)
except Exception as e:
    logger.warning("Post-completion summarizer failed")

# Job enqueue attempt #2 (DUPLICATE!)
try:
    existing_job = db.execute(...)
    if not existing_job:
        loop = asyncio.new_event_loop()
        job_id = loop.run_until_complete(job_queue.enqueue_job(...))
except Exception as job_error:
    logger.error("CRITICAL: Failed to enqueue job")
```

**Consequences:**
- Can create duplicate jobs
- Race conditions between two attempts
- Event loop conflicts
- Confusing logs

**Resolution:**
- Remove duplicate logic
- Keep only ONE enqueue attempt
- Use proper async/await pattern
- Remove asyncio.new_event_loop() hack

---

### **Issue 3: Weak Idempotent Protection** ⚠️ **MEDIUM PRIORITY**

**Location:** `blueprint_sessions.py`, Lines 1014-1017

**Problem:**
```python
if existing_session and existing_session[0] == 'completed':
    # Assumes jobs were enqueued previously
    bg_jobs_enqueued = True  # ⚠️ ASSUMPTION!
```

**Better Approach:**
```python
if existing_session and existing_session[0] == 'completed':
    # CHECK if jobs actually exist
    job_check = db.execute("""
        SELECT id FROM bg_jobs 
        WHERE user_id = :user_id AND session_id = :session_id 
        AND job_type = 'SUMMARIZE_SESSION'
    """)
    
    if job_check.fetchone():
        bg_jobs_enqueued = True  # Jobs exist
    else:
        # Session completed but no jobs - ENQUEUE THEM!
        job_id = await job_queue.enqueue_job(...)
        bg_jobs_enqueued = True
```

---

### **Issue 4: Exhausted Jobs Blocking New Ones** ⚠️ **MEDIUM PRIORITY**

**Problem:**
- Old job with attempts >= max_attempts
- Dedupe key prevents new job creation
- ON CONFLICT DO UPDATE resets fields but keeps old ID
- Worker sees attempts >= max_attempts and skips it

**Example from logs:**
```
Job a543024e: queued, attempts: 6/6
Status: queued
Next Attempt: 2025-10-08 21:38:43 (future date due to backoff)
```

**Resolution Options:**
1. Auto-delete exhausted jobs after 3 days
2. Reset attempts on ON CONFLICT
3. Make dedupe key more specific (include date/timestamp)
4. Check for exhausted jobs before ON CONFLICT

---

## 💡 Recommendations

### **Immediate Actions** (This Week)

1. **Identify Which Endpoint Frontend Uses**
   ```bash
   # Search frontend code
   grep -r "session/complete\|mark-completed" frontend/src/
   ```

2. **Add Monitoring to Completion Endpoint**
   ```python
   logger.critical(f"🚨 SESSION COMPLETION CALLED: {session_id[:8]}")
   ```

3. **Check Frontend Session Completion Logic**
   - Is it called automatically after Q12?
   - Is it called manually by user?
   - Is there error handling?

4. **Add Health Check for Job Pipeline**
   ```python
   @router.get("/session/completion-health/{session_id}")
   async def check_completion_health(session_id: str):
       # Check if session completed
       # Check if SUMMARIZE_SESSION job exists
       # Check if PLAN_NEXT_SESSION job exists
       # Return diagnostic info
   ```

---

### **Short-term Fixes** (This Month)

1. **Deprecate Legacy Endpoint**
   - Add deprecation warning to `/mark-completed`
   - Redirect to `/api/session/complete`
   - Update all frontend calls

2. **Remove Duplicate Job Enqueue Logic**
   - Keep only one attempt in session_completion.py
   - Remove asyncio.new_event_loop() pattern
   - Simplify error handling

3. **Strengthen Idempotent Protection**
   - Actually check if jobs exist
   - Don't just assume based on session status
   - Enqueue jobs if missing

4. **Add Completion Diagnostics**
   - Log every completion attempt
   - Track which endpoint was called
   - Monitor job enqueue success rate
   - Alert on completion without job

---

### **Long-term Improvements** (Next Quarter)

1. **Cleanup System for Exhausted Jobs**
   ```python
   # Daily cleanup job
   DELETE FROM bg_jobs 
   WHERE status = 'failed' 
   AND attempts >= max_attempts 
   AND created_at < NOW() - INTERVAL '3 days'
   ```

2. **Improve Dedupe Key Specificity**
   ```python
   # Current
   dedupe_key = f"u:{user_id}|s:{session_id}|{job_type}"
   
   # Better
   dedupe_key = f"u:{user_id}|s:{session_id}|{job_type}|{date}"
   ```

3. **Add Fallback Mechanism**
   ```python
   # If session completed but no jobs after 5 minutes
   # Automatic recovery system enqueues jobs
   ```

4. **Better Monitoring Dashboard**
   - Show completion rate
   - Show job enqueue rate
   - Alert on discrepancies
   - Track completion-to-job lag

---

## 📋 Checklist for Debugging

### Frontend Investigation:
- [ ] Find session completion trigger in frontend code
- [ ] Verify which endpoint is being called
- [ ] Check if completion happens after Q12 automatically
- [ ] Test manual completion flow
- [ ] Add logging to track completion calls

### Backend Investigation:
- [ ] Add critical logs to both completion endpoints
- [ ] Monitor which endpoint is being hit
- [ ] Check job enqueue success rate
- [ ] Verify idempotent logic is working correctly
- [ ] Test duplicate completion calls

### Database Investigation:
- [ ] Query sessions without corresponding bg_jobs
- [ ] Find old exhausted jobs blocking dedupe keys
- [ ] Check for orphaned session packs
- [ ] Verify job chain completion rate

### Testing:
- [ ] Test complete session via `/api/session/complete`
- [ ] Test complete session via `/mark-completed`
- [ ] Test duplicate completion calls
- [ ] Test with exhausted jobs present
- [ ] Test job pipeline end-to-end

---

## 🎯 Root Cause Summary

**Most Likely Root Cause:**
Frontend is NOT calling session completion endpoint at all, or calling wrong endpoint that silently fails to enqueue jobs.

**Evidence:**
1. Sessions marked as completed in database
2. No background job history for those sessions
3. Manual trigger works perfectly
4. System infrastructure is healthy

**Next Step:**
**FIND AND FIX FRONTEND SESSION COMPLETION LOGIC**

---

## 📝 Files to Review

### Backend:
- `backend/api/blueprint_sessions.py` - Lines 873-1065 (Primary completion endpoint)
- `backend/api/session_lifecycle.py` - Lines 26-39 (Legacy endpoint)
- `backend/services/session_completion.py` - Lines 70-215 (Completion handler)
- `backend/services/bg_job_queue.py` - Job queue system
- `backend/services/simplified_job_handlers.py` - Job handlers

### Frontend:
- Search for: "session/complete", "mark-completed", "complete", "finish"
- Check session components
- Review session state management
- Find completion trigger logic

---


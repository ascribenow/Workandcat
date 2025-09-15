# 🚨 SESSION CONTINUITY DIAGNOSTIC PLAN - COMPREHENSIVE

## EXECUTIVE SUMMARY
**CRITICAL ISSUE**: Sessions load successfully but go BLANK midway during user interaction, making the platform completely unusable. Users cannot complete sessions or progress through questions.

**OBJECTIVE**: Identify the exact moment and cause of session blanking/dashboard redirect through comprehensive technical analysis.

---

## DIAGNOSTIC METHODOLOGY

### PHASE 1: COMPLETE USER JOURNEY TESTING
1. **Login → Dashboard Transition** (capture initial state)
2. **Session Start → Question Load** (timing and state monitoring)
3. **Question Interaction** (option selection, answer submission) 
4. **Question Progression** (next question loading)
5. **Session Midway Monitoring** (detect exact blank moment)
6. **Session Completion Attempt** (if reachable)
7. **Next Session Creation** (post-completion flow)

### PHASE 2: SESSION CONTINUITY PACK (Technical Deep-Dive)

## A) REPRO FACTS
- **user_email**: sp@theskinmantra.com
- **when_ist**: `YYYY-MM-DD HH:MM:SS` (Asia/Kolkata) 
- **session_id** (string) + resolved **sess_seq** (int)
- **App build/hash**: From page footer/HTML (main.[hash].js)
- **Browser + OS**: Captured from user agent

## B) FRONTEND CAPTURE (Export Files)

### 1. HAR Export
**File**: `session_continuity_har.har`
- Complete network traffic from Login → Start → Blank/Redirect
- All API calls, responses, timing data
- Network failures and status codes

### 2. Console Log Dump  
**File**: `console_logs_complete.txt`
- All console levels (log, warn, error, debug)
- Timestamps for correlation with user interactions
- Error stack traces and async failures

### 3. Storage Snapshots
**Files**: `storage_before_blank.json`, `storage_after_blank.json`
```js
// Capture right before and after blank/redirect
console.log('LS_BEFORE', JSON.stringify(localStorage, null, 2));
console.log('SS_BEFORE', JSON.stringify(sessionStorage, null, 2));
// ... interaction happens ...
console.log('LS_AFTER', JSON.stringify(localStorage, null, 2));
console.log('SS_AFTER', JSON.stringify(sessionStorage, null, 2));
```

### 4. Auth + Cookie Analysis
**File**: `auth_state.json`
- Cookie dump (name, domain, expiry)
- JWT exp claim (seconds since epoch)
- Token validation status
- Auth interceptor behavior

### 5. Service Worker Status
**File**: `service_worker_status.json`
```js
navigator.serviceWorker.getRegistrations().then(r=>
  console.log('SW_REGISTRATIONS', r.map(x=>x.active&&x.active.scriptURL))
);
caches.keys().then(keys => console.log('CACHE_KEYS', keys));
```

### 6. Route History Trace
**Implementation**: Add route monitoring
```js
import { useEffect } from "react";
import { useLocation, useNavigationType } from "react-router-dom";

export function useRouteTrace(rid) {
  const loc = useLocation(); const nav = useNavigationType();
  useEffect(() => {
    console.log(`[ROUTE] ${rid}`, { path: loc.pathname + loc.search, nav });
  }, [loc, nav]);
}
```

### 7. Global Error Hooks
**Implementation**: Add to app root
```js
window.onerror = (m, s, l, c, e) => console.error('[ONERROR]', { m, s, l, c, e });
window.onunhandledrejection = (e) => console.error('[UNHANDLED]', e.reason || e);
```

## C) FRONTEND CODE ANALYSIS

### 1. Route Guard/ProtectedRoute Logic
**File**: Extract from routing logic
- Redirect conditions
- Pack-missing handling
- Auth failure responses

### 2. Session Start Component
**File**: SessionSystem.js critical sections
- plan-next API calls
- pack fetch logic  
- mark-served implementation

### 3. Question Player Interaction
**File**: Question advancement and submit handlers
- Q1 → Q2 progression logic
- Answer submission error paths
- State management during transitions

### 4. API Client Interceptors
**File**: Auth/error interceptor implementation
- 401/403/409 handling logic
- Automatic redirect triggers
- Error response processing

### 5. useEffect Cleanup Logic
**File**: Component mounting/unmounting
- Pack clearing on mount/unmount
- Session state cleanup
- Memory leak prevention

## D) BACKEND API LOGS (Same X-Request-Id)

### API Call Tracing
**File**: `backend_api_trace.json`
- POST /api/adapt/plan-next (status, sess_seq, timings, planner_fallback)
- GET /api/adapt/pack (status, response size)
- POST /api/adapt/mark-served (status)
- Answer submit endpoint (immediately before blank)
- All 401/403/409/5xx responses with timing

### Session Creation Detection
**Query**: Check for duplicate session creation
```sql
SELECT sess_seq, created_at, status, served_at
FROM sessions 
WHERE user_id = '<USER_UUID>' 
ORDER BY created_at DESC LIMIT 10;
```

## E) DATABASE GROUND TRUTH

### Pack State Verification
**File**: `database_ground_truth.json`
```sql
-- Pack serving state
SELECT user_id, sess_seq, served_at, completed_at,
       jsonb_array_length(pack_json) AS pack_len,
       status, created_at
FROM session_pack_plan 
WHERE user_id = '<USER_UUID>' AND sess_seq = <SESS_SEQ>;

-- Attempt tracking  
SELECT COUNT(*) AS attempts_count, 
       MIN(created_at) as first_attempt,
       MAX(created_at) as last_attempt
FROM attempt_events 
WHERE user_id = '<USER_UUID>' AND sess_seq_at_serve = <SESS_SEQ>;

-- Recent session pattern
SELECT sess_seq, served_at, completed_at, status
FROM sessions 
WHERE user_id = '<USER_UUID>' 
ORDER BY sess_seq DESC LIMIT 5;
```

---

## ROOT CAUSE INVESTIGATION TARGETS

### Primary Suspects (To Confirm/Deny):
1. **Auth/Token Drift**: JWT expires → guard redirects to dashboard
2. **Wrong Redirect Condition**: `if (!pack) navigate('/')` triggers before pack loads
3. **Race/Duplicate Start**: Multiple plan-next calls → state invalidation  
4. **Pack Fetch Creates**: GET /pack accidentally triggers new session planning
5. **State Purge**: localStorage cleared on errors → loses session context
6. **Unhandled Submit Error**: Answer submission fails → ErrorBoundary renders blank
7. **Router Remount**: Component remounting due to changing props/keys

### Session State Corruption Patterns:
- Different first question between logins (indicates new sess_seq creation)
- Session state cleared during interaction
- API call failures triggering unexpected redirects
- React component remounting clearing local state

---

## IMMEDIATE SAFETY TOGGLES (Apply While Debugging)

### 1. No Auto-Redirect on Pack-Missing
```js
// Replace navigate('/') with error component
if (!pack) {
  return <div>Pack unavailable. <button onClick={retryPack}>Retry</button></div>;
  // NEVER navigate('/') 
}
```

### 2. Disable Duplicate Session Creation  
```js
// Frontend: Check if session already exists
if (currentSessionId && !isCompleted) {
  console.log('Session already active, not creating new one');
  return;
}
```

---

## DELIVERABLE

**Single File**: `SESSION_CONTINUITY_DIAGNOSTIC_COMPLETE.md`

**Contents**:
1. **Complete failure reproduction** with exact timing
2. **Technical artifacts** (HAR, logs, storage, database queries)
3. **Code analysis** of problematic functions
4. **Root cause identification** with evidence
5. **Targeted fix implementation** 
6. **End-to-end validation** proof

**Success Criteria**: Users can complete full 12-question sessions without interruption.

---

## EXECUTION PLAN

1. **Implement monitoring hooks** (route trace, error hooks)
2. **Execute complete user journey** with artifact capture
3. **Analyze failure patterns** and correlate with code
4. **Apply safety toggles** and targeted fixes
5. **Validate complete session experience** works end-to-end

**Timeline**: 2.5-3 hours for definitive resolution
**Outcome**: Fully functional platform with stable session experience

Ready to proceed with this comprehensive approach?
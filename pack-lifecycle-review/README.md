# Pack Lifecycle Review - Critical Files for Debugging Session Blank Issue

## ISSUE SUMMARY
- Sessions load successfully but go blank immediately after Submit Answer
- `currentPack` becomes empty causing premature session completion
- Platform unusable for real users

## FILES INCLUDED

### Frontend Components
- `frontend/src/components/SessionSystem.js` - Main session component with pack state management
- `frontend/src/components/Dashboard.js` - Contains redirect logic and session management  
- `frontend/src/components/AuthProvider.js` - API configuration and auth handling

### Frontend Utils  
- `frontend/src/utils/sessionMonitoring.js` - Route trace and error monitoring
- `frontend/src/utils/packHistoryRecorder.js` - Pack write recording instrumentation

### Backend Handlers
- `backend/handlers/get_adapt_pack.py` - GET /api/adapt/pack endpoint
- `backend/handlers/server.py` - POST /api/log/question-action and other endpoints

## MICRO-INSTRUMENTATIONS ADDED

### A) Pack Write Recorder
- Records every pack state change with timestamp, length, reason, and stack trace
- Available globally as `window.__packHistory`
- Logs: `[PACK_WRITE] reason: length=X, timestamp=ISO`

### B) Route Trace  
- Monitors all route changes in session component
- Logs: `[SESSION] pathname nav_type`

## GREP RESULTS

### Pack Clearing Patterns: ✅ NONE FOUND
- No suspicious pack clearing patterns detected

### Eager Redirects: ⚠️ 3 FOUND
```
src/components/SessionSystem.js:301:      if (!pack || pack.length === 0) {
src/components/SessionSystem.js:369:      if (!pack) {
src/components/SessionSystem.js:432:        if (!pack || pack.length === 0) {
```

### Root Component Keys: ✅ NONE FOUND  
- No problematic key props that could cause remounting

## ANALYSIS NEEDED

1. Review SessionSystem.js lines 301, 369, 432 for eager redirect issues
2. Check why `currentPack` state becomes empty despite being set with 12 items
3. Investigate React state update timing issues in pack lifecycle
4. Verify submit button error handling and response processing

## DEBUGGING DATA AVAILABLE

After implementing instrumentations and reproducing the issue:
- `window.__packHistory` will show exact pack state changes
- Console logs will show route changes and pack writes
- Error boundary will catch React crashes
- Comprehensive state monitoring will track timing issues
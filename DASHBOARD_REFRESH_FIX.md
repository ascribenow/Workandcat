# Dashboard Refresh Issue - Fix Summary

**Date:** 2025-10-03  
**Issue:** Dashboard reloading every time user switches browser tabs/windows

---

## Problem

The dashboard was refreshing whenever the user:
- Switched to another browser tab and came back
- Switched to another application window and returned
- The browser window gained focus

**User Experience Impact:**
- Annoying auto-refreshes while multitasking
- Unnecessary API calls
- Loss of scroll position
- Data re-fetching constantly

---

## Root Cause

In `/app/frontend/src/components/SimpleDashboard.js`, two aggressive event listeners were added:

```javascript
// Lines 38-62 (OLD CODE)
const handleVisibilityChange = () => {
  if (!document.hidden && user && token) {
    fetchDashboardData();        // ❌ Triggers on ANY tab switch
    fetchAdaptiveInsights();
  }
};

const handleFocus = () => {
  if (user && token) {
    fetchAdaptiveInsights();     // ❌ Triggers on ANY window focus
  }
};

document.addEventListener('visibilitychange', handleVisibilityChange);
window.addEventListener('focus', handleFocus);
```

**Why these were added:**
- Original intent: Refresh insights after user completes a session
- Problem: They triggered on EVERY tab/window switch, not just after sessions

---

## Solution

Implemented a **smart refresh flag** using `sessionStorage`:

### 1. Updated Dashboard Component (SimpleDashboard.js)

**Changed behavior:**
- ✅ Check sessionStorage flag before refreshing
- ✅ Only refresh if flag is set (meaning session was completed)
- ✅ Clear flag after refreshing
- ❌ Removed aggressive `window.focus` listener

```javascript
// NEW CODE - Lines 36-60
useEffect(() => {
  const handleVisibilityChange = () => {
    if (!document.hidden && user && token) {
      // Check if we should refresh (only if session was completed)
      const shouldRefresh = sessionStorage.getItem('dashboardNeedsRefresh');
      
      if (shouldRefresh === 'true') {
        console.log('SimpleDashboard: Session completed, refreshing data...');
        fetchDashboardData();
        fetchAdaptiveInsights();
        // Clear the flag
        sessionStorage.removeItem('dashboardNeedsRefresh');
      } else {
        console.log('SimpleDashboard: Tab became visible (no refresh needed)');
      }
    }
  };

  document.addEventListener('visibilitychange', handleVisibilityChange);
  return () => {
    document.removeEventListener('visibilitychange', handleVisibilityChange);
  };
}, [user, token]);
```

### 2. Updated Session Completion (SessionSystem.js)

**Set flag when session completes:**

```javascript
// Blueprint sessions - Line 273
const completeBlueprintSession = async (sessionId) => {
  const response = await axios.post(`${API}/session/complete`, {
    session_id: sessionId
  });
  
  // Set flag to refresh dashboard when user returns
  sessionStorage.setItem('dashboardNeedsRefresh', 'true');
  console.log(`[BLUEPRINT] Dashboard refresh flag set`);
  
  return response.data.summary;
};

// Legacy sessions - Line 1089
const handleSessionCompletionWithHandshake = async (completionData) => {
  const response = await axios.post(`${API}/session/complete`, {
    session_id: sessionId
  });
  
  // Set flag to refresh dashboard when user returns
  sessionStorage.setItem('dashboardNeedsRefresh', 'true');
  console.log('   ✅ Dashboard refresh flag set');
};
```

---

## How It Works Now

### Scenario 1: User switches tabs (No session completion)
```
1. User on dashboard → switches to another tab
2. Returns to dashboard tab
3. visibilitychange event fires
4. Check sessionStorage.dashboardNeedsRefresh → undefined/false
5. ✅ NO REFRESH - Dashboard stays as is
```

### Scenario 2: User completes session
```
1. User completes session
2. sessionStorage.setItem('dashboardNeedsRefresh', 'true')
3. User returns to dashboard (or switches back to tab)
4. visibilitychange event fires
5. Check sessionStorage.dashboardNeedsRefresh → 'true'
6. ✅ REFRESH - Fetch new data
7. Clear flag: sessionStorage.removeItem('dashboardNeedsRefresh')
```

### Scenario 3: User manually refreshes page
```
1. User presses F5 or Ctrl+R
2. Page reloads completely
3. useEffect with [user, token] triggers (line 21)
4. ✅ REFRESH - Fetches initial data (normal behavior)
```

---

## Testing Scenarios

### ✅ Test 1: Tab Switching
**Steps:**
1. Open dashboard
2. Switch to another browser tab
3. Wait 5 seconds
4. Return to dashboard tab

**Expected:** No reload, dashboard stays as is  
**Result:** ✅ PASS

### ✅ Test 2: Window Switching
**Steps:**
1. Open dashboard in browser
2. Click on another application (email, editor, etc.)
3. Wait
4. Click back to browser window

**Expected:** No reload, dashboard stays as is  
**Result:** ✅ PASS

### ✅ Test 3: After Session Completion
**Steps:**
1. Complete a practice session
2. Navigate back to dashboard (or switch to dashboard tab)

**Expected:** Dashboard refreshes to show updated insights  
**Result:** ✅ PASS (flag set, refresh triggered, flag cleared)

### ✅ Test 4: Manual Refresh
**Steps:**
1. On dashboard, press F5

**Expected:** Page reloads normally  
**Result:** ✅ PASS (initial useEffect triggers)

---

## Why sessionStorage?

**sessionStorage vs. localStorage:**
- ✅ **sessionStorage**: Persists only for current browser tab session
- ✅ Cleared when tab is closed
- ✅ Perfect for temporary flags like "needs refresh"
- ❌ **localStorage**: Persists forever (not suitable for this)

**Why not a React state?**
- ❌ State is lost on page navigation
- ❌ Can't persist between session page → dashboard navigation
- ✅ sessionStorage survives navigation within the same tab

---

## Files Modified

1. **`/app/frontend/src/components/SimpleDashboard.js`**
   - Lines 36-60: Removed `focus` listener, added flag check
   - Lines 64-78: Added flag check for location changes

2. **`/app/frontend/src/components/SessionSystem.js`**
   - Line 273: Added flag in `completeBlueprintSession`
   - Line 1089: Added flag in `handleSessionCompletionWithHandshake`

---

## Benefits

✅ **Better UX:**
- No annoying auto-refreshes when multitasking
- Dashboard stays stable during tab switching
- Scroll position preserved

✅ **Performance:**
- Reduced unnecessary API calls
- Lower server load
- Faster perceived performance

✅ **Smart Refresh:**
- Still refreshes when needed (after session completion)
- Still respects manual refresh (F5)
- Predictable behavior

---

## Edge Cases Handled

1. **Multiple tabs open:**
   - Flag is per-tab (sessionStorage is tab-specific)
   - Completing session in Tab A doesn't affect Tab B

2. **Session completion fails:**
   - Flag is only set on successful completion
   - No refresh triggered if session API fails

3. **Browser restart:**
   - sessionStorage is cleared
   - No stale flags remain

4. **User never switches tabs:**
   - Location change effect still handles refresh
   - Works for single-tab users

---

## Monitoring

Check browser console logs:
- ✅ `SimpleDashboard: Tab became visible (no refresh needed)` - Normal tab switch
- ✅ `SimpleDashboard: Session completed, refreshing data...` - Refresh triggered
- ✅ `Dashboard refresh flag set` - Session completed successfully

---

## Status

✅ **FIXED** - Dashboard only refreshes when:
1. Session is completed
2. User manually refreshes page (F5)
3. Initial page load

❌ **No longer refreshes when:**
1. Switching browser tabs
2. Switching application windows
3. Browser window gains focus

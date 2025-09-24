# Twelvr Blueprint Implementation - Detailed Phase Plan

## Overview
This document outlines the step-by-step implementation phases for the Twelvr Session System Blueprint, addressing all 12 critical deviations. Each phase includes specific tasks, files to create/modify, testing requirements, and approval checkpoints.

---

## PHASE 1: Database Schema Migration & Constraints
**Duration**: 2-3 days  
**Risk Level**: HIGH (Data integrity critical)

### Phase 1A: Schema Creation
**Tasks:**
1. Create migration script for new database schema
2. Add advisory lock support functions  
3. Create backup procedures
4. Test schema changes in isolation

**Files to Create:**
- `/app/backend/migrations/015_blueprint_schema.sql`
- `/app/backend/migrations/016_advisory_locks.sql` 
- `/app/backend/services/advisory_locks.py`

**Database Changes:**
```sql
-- New tables for blueprint architecture
CREATE TABLE session_packs (...);
CREATE TABLE session_pack_questions (...);
CREATE TABLE session_answers (...);

-- Enhanced sessions table
ALTER TABLE sessions ADD COLUMN current_position INTEGER DEFAULT 0;
ALTER TABLE sessions ADD COLUMN served_at TIMESTAMP;
ALTER TABLE sessions ADD COLUMN abandoned_at TIMESTAMP;

-- Critical constraints (Deviations #2, #4, #8)
ALTER TABLE sessions ADD CONSTRAINT sessions_status_check 
CHECK (status IN ('planned', 'active', 'completed', 'abandoned'));

CREATE UNIQUE INDEX idx_session_answers_unique_position 
ON session_answers(session_id, position);
```

**Testing Requirements:**
- [ ] Schema creates successfully on clean database
- [ ] All constraints enforce properly
- [ ] Advisory lock functions work under concurrent load
- [ ] Backup/restore procedures tested

### Phase 1B: Data Migration
**Tasks:**
1. Create data transformation scripts
2. Migrate existing adaptive_packs to new format
3. Convert current sessions to new position tracking
4. Validate data integrity

**Files to Create:**
- `/app/backend/migrations/migrate_existing_data.py`
- `/app/backend/migrations/validate_migration.py`

**Migration Process:**
1. Backup existing tables
2. Transform adaptive_packs → session_pack_questions with positions
3. Update session statuses and positions  
4. Validate no data loss
5. Create rollback scripts

**Testing Requirements:**
- [ ] Migration completes without data loss
- [ ] Position alignment correct (1-based in DB, proper mapping in code)
- [ ] All existing sessions can be resumed
- [ ] Rollback procedure tested

**⚠️ CHECKPOINT 1: Database schema and migration must be approved before proceeding**

---

## PHASE 2: Core Planning Engine Implementation
**Duration**: 3-4 days
**Risk Level**: MEDIUM (Algorithm complexity)

### Phase 2A: Advisory Lock System
**Tasks:**
1. Implement PostgreSQL advisory lock wrapper
2. Create user-specific lock management
3. Test concurrent planning prevention

**Files to Create:**
- `/app/backend/services/advisory_locks.py`
- `/app/backend/services/lock_manager.py`

**Code Structure:**
```python
class AdvisoryLockManager:
    async def acquire_planning_lock(self, user_id: str):
        """Deviation #3: Ensure only one planned session per user"""
        
    async def release_planning_lock(self, user_id: str):
        """Release planning lock safely"""
```

### Phase 2B: Blueprint Session Planner
**Tasks:**
1. Implement hard cap enforcement (Deviation #1)
2. Create PYQ rebalancing logic (Deviation #6)  
3. Apply intentional question ordering (Deviation #5)
4. Generate pack-level constraint reports (Deviation #7)

**Files to Create:**
- `/app/backend/services/blueprint_planner.py`
- `/app/backend/services/question_ordering.py`
- `/app/backend/services/constraint_validator.py`

**Core Algorithm Implementation:**
```python
class BlueprintSessionPlanner:
    async def plan_session(self, user_id: str) -> dict:
        """Main planning with all deviation fixes"""
        # Deviation #3: Advisory lock
        async with self.lock_manager.acquire_planning_lock(user_id):
            # Check existing planned session
            # Build candidate pools
            # Reserve PYQs with rebalancing (Deviation #6)
            # Apply hard caps (Deviation #1)  
            # Apply ordering pattern (Deviation #5)
            # Generate constraint report (Deviation #7)
```

**Testing Requirements:**
- [ ] Hard caps prevent constraint violations
- [ ] PYQ rebalancing maintains exact 3/6/3 distribution
- [ ] Question ordering follows E-M-M-E pattern
- [ ] Advisory locks prevent duplicate planning
- [ ] Constraint reports generated correctly

**⚠️ CHECKPOINT 2: Planning engine must pass all constraint tests before proceeding**

---

## PHASE 3: New API Endpoints  
**Duration**: 2-3 days
**Risk Level**: MEDIUM (API contract changes)

### Phase 3A: Session Management APIs
**Tasks:**
1. Create new session endpoints (Deviation #12)
2. Implement position equality guards (Deviation #10)
3. Add idempotency handling (Deviation #4)
4. Remove all polling logic (Deviation #9)

**Files to Create:**
- `/app/backend/api/blueprint_session.py`
- `/app/backend/services/session_manager.py` 
- `/app/backend/services/answer_processor.py`

**API Endpoints:**
```python
@router.get("/session/next")  
# Returns complete 12-question pack immediately (no polling)

@router.get("/session/current")
# Returns ordered questions for resumption (Deviation #10)  

@router.post("/session/answer")
# Position equality guard + idempotency (Deviations #4, #10)

@router.post("/session/complete")  
# Triggers summarization and pre-planning
```

### Phase 3B: Background Processing
**Tasks:**
1. Session completion processing
2. Next session pre-planning
3. Learning state updates
4. Telemetry integration

**Files to Create:**
- `/app/backend/services/session_completion.py`
- `/app/backend/services/learning_state.py`

**Testing Requirements:**
- [ ] /session/next returns sessions instantly (no timeouts)
- [ ] Position guards prevent sequence violations  
- [ ] Idempotency prevents duplicate answers
- [ ] Background tasks complete successfully
- [ ] All legacy /api/adapt/* routes return 404

**⚠️ CHECKPOINT 3: New APIs must pass integration tests before frontend changes**

---

## PHASE 4: Frontend Integration
**Duration**: 3-4 days  
**Risk Level**: MEDIUM (User experience impact)

### Phase 4A: New Session Component
**Tasks:**
1. Create BlueprintSessionSystem component
2. Remove all polling logic (Deviation #9)
3. Handle position synchronization (Deviation #2)
4. Implement error handling for position mismatches

**Files to Create:**
- `/app/frontend/src/components/BlueprintSessionSystem.js`
- `/app/frontend/src/components/SessionProgress.js`
- `/app/frontend/src/components/QuestionDisplay.js`

**Key Changes:**
```javascript
// Deviation #9: NO polling - instant session loading
const loadSession = async () => {
  // Try current session first, then next session
  // Both return immediately - no polling loops
};

// Deviation #10: Position equality validation  
const submitAnswer = async (questionId, position, answer) => {
  // Handle position mismatch errors gracefully
};
```

### Phase 4B: Dashboard Updates
**Tasks:**
1. Update Dashboard component to use new endpoints
2. Remove session planning complexity
3. Update session button behavior
4. Test seamless session transitions

**Files to Modify:**
- `/app/frontend/src/components/Dashboard.js`
- `/app/frontend/src/components/SimpleDashboard.js`

**Testing Requirements:**
- [ ] Sessions start instantly (< 1 second)
- [ ] Position tracking works correctly
- [ ] Session resumption functions properly
- [ ] Error messages clear and helpful
- [ ] No references to /api/adapt/* routes

**⚠️ CHECKPOINT 4: Frontend must work seamlessly with new backend before deployment**

---

## PHASE 5: Migration & Deployment
**Duration**: 1-2 days
**Risk Level**: HIGH (Production deployment)

### Phase 5A: Backward Compatibility Layer  
**Tasks:**
1. Create compatibility endpoints for gradual migration
2. Implement feature flags
3. Create deployment scripts
4. Test rollback procedures

**Files to Create:**
- `/app/backend/api/compatibility_layer.py`
- `/app/backend/services/feature_flags.py`
- `/app/deployment/blueprint_deployment.py`

### Phase 5B: Staged Deployment
**Tasks:**
1. Deploy to staging environment
2. Run full end-to-end tests
3. Performance testing under load
4. Monitor for 24 hours before production

**Deployment Steps:**
1. Deploy database migrations (off-peak)
2. Deploy backend with feature flag OFF
3. Deploy frontend with feature flag OFF  
4. Enable for 10% of users
5. Monitor and gradually increase to 100%
6. Remove compatibility layer after 1 week

**Testing Requirements:**
- [ ] All 12 deviations working correctly in staging
- [ ] Performance meets targets (< 1s session start)
- [ ] No data corruption during migration
- [ ] Rollback procedures tested and ready

### Phase 5C: Legacy Cleanup
**Tasks:**
1. Remove old API endpoints after 100% migration
2. Clean up unused database tables  
3. Update documentation
4. Archive old code

**Files to Remove:**
- `/app/backend/api/v2_adapt.py` 
- `/app/frontend/src/utils/smartPolling.js`
- All polling-related code

**⚠️ CHECKPOINT 5: Full production deployment must be approved after staging validation**

---

## Success Criteria & Testing Matrix

### Critical Tests for Each Deviation:
1. **Hard Cap**: Questions rejected when subcategory+type > 2
2. **Position Alignment**: 0-based/1-based mapping works correctly  
3. **Advisory Locks**: Concurrent planning properly serialized
4. **Idempotency**: Duplicate answers handled gracefully
5. **Question Ordering**: E-M-M-E pattern followed consistently
6. **PYQ Rebalancing**: Exact 3/6/3 maintained after PYQ selection
7. **Constraint Reporting**: Single pack-level report generated
8. **Status Naming**: Only planned/active/completed/abandoned used
9. **No Polling**: Zero polling/websocket code in final system
10. **Position Guards**: Out-of-sequence submissions rejected
11. **First Session**: Diagnostic pack behavior documented/tested
12. **Clean Endpoints**: Only /session/* routes functional

### Performance Targets:
- Session start time: < 1 second
- API response time: < 200ms average  
- Session completion rate: > 95%
- Zero timeout errors

### Rollback Triggers:
- Session start time > 3 seconds
- Error rate > 1%
- Data corruption detected
- User complaints > baseline

---

## Implementation Approval Request

**Phase 1 Ready for Approval:**
- Database schema migration scripts
- Advisory lock implementation  
- Data transformation procedures
- Testing and rollback plans

**Questions for Approval:**
1. Should we proceed with Phase 1 (Database Migration) first?
2. Do you want to review the migration scripts before execution?
3. Should we implement this in staging environment first?
4. Any specific constraints or requirements not covered?
5. What is your preferred timeline for each phase?

**Risk Mitigation:**
- All changes are backward compatible during transition
- Comprehensive rollback procedures for each phase
- Staged deployment with feature flags
- 24/7 monitoring during migration

**Ready to Proceed:** Phase 1 implementation can begin upon your approval.
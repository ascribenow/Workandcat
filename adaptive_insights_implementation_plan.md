# Twelvr Adaptive Insights - Detailed Technical Implementation Plan

## Overview
This document outlines the exact implementation steps for the "Proof of the Pudding" adaptive insights feature that will make adaptivity visible to learners through dashboard insights and pre-session cards.

## Phase 1: Database Schema & Indexing (1.5 hours)

### 1.1 Create Migration File
**File**: `/app/backend/migrations/022_adaptive_insights_cache.sql`

```sql
-- Cache table for dashboard insights (two sections)
CREATE TABLE IF NOT EXISTS user_dashboard_insights (
    user_id uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    all_time_insights jsonb NOT NULL,
    recent_insights jsonb NOT NULL, 
    last_updated_at timestamptz NOT NULL DEFAULT now()
);

-- Cache table for pre-session insight cards
CREATE TABLE IF NOT EXISTS user_pre_session_insights (
    user_id uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    insight_card jsonb NOT NULL,
    last_updated_at timestamptz NOT NULL DEFAULT now()
);

-- Debug table (optional) for storing raw slices
CREATE TABLE IF NOT EXISTS user_insight_debug (
    user_id uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    all_time_slice jsonb,
    recent_slice jsonb,
    pre_session_slice jsonb,
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_attempt_events_user_session ON attempt_events(user_id, session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user_status_completed ON sessions(user_id, status, completed_at);
CREATE INDEX IF NOT EXISTS idx_session_pack_questions_session ON session_pack_questions(session_id);
CREATE INDEX IF NOT EXISTS idx_learner_notebook_user_concept_updated ON learner_notebook(user_id, concept_norm, last_seen_at);
CREATE INDEX IF NOT EXISTS idx_coverage_debt_user_subcategory ON coverage_debt(user_id, subcategory, type_of_question);
```

### 1.2 Add SQLAlchemy Models
**File**: `/app/backend/database.py`

```python
class UserDashboardInsights(Base):
    __tablename__ = "user_dashboard_insights"
    
    user_id = Column(String(36), primary_key=True)
    all_time_insights = Column(JSON, nullable=False)
    recent_insights = Column(JSON, nullable=False)
    last_updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", foreign_keys=[user_id])

class UserPreSessionInsights(Base):
    __tablename__ = "user_pre_session_insights"
    
    user_id = Column(String(36), primary_key=True)
    insight_card = Column(JSON, nullable=False)
    last_updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", foreign_keys=[user_id])

class UserInsightDebug(Base):
    __tablename__ = "user_insight_debug"
    
    user_id = Column(String(36), primary_key=True)
    all_time_slice = Column(JSON, nullable=True)
    recent_slice = Column(JSON, nullable=True)
    pre_session_slice = Column(JSON, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", foreign_keys=[user_id])
```

## Implementation Timeline

| Phase | Description | Duration | Dependencies |
|-------|-------------|----------|--------------|
| 1 | Database Schema & Models | 1.5h | None |
| 2 | Data Extraction Service | 4h | Phase 1 |
| 3 | LLM Generation Service | 3h | Phase 2 |
| 4 | Cache Management Service | 2h | Phase 2, 3 |
| 5 | API Endpoints | 1.5h | Phase 4 |
| 6 | Background Job Integration | 2h | Phase 4, 5 |
| 7 | Frontend Integration | 3h | Phase 5 |
| 8 | Concept Normalization Check | 1h | Phase 2 |
| 9 | Testing & Optimization | 2h | All phases |

**Total Estimated Time: 20 hours**

## Key Success Criteria

1. **Dashboard Insights**: Two collapsible sections showing all-time journey and recent momentum
2. **Pre-Session Cards**: Compact insight cards before every session start  
3. **Performance**: All data extraction completes within 2 seconds
4. **Cache Hit Rate**: >80% of requests served from cache 
5. **LLM Fallbacks**: System never fails due to LLM unavailability
6. **Concept Integration**: All insights use normalized concept names
7. **Background Jobs**: Insights refresh automatically after session completion

This implementation plan provides the complete technical roadmap for delivering the "Proof of the Pudding" adaptive insights feature with all specified requirements.
# Twelvr Adaptive Insights - "Proof of the Pudding" Implementation Plan

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

## Phase 2: Data Extraction Service (4 hours)

### 2.1 Create Adaptive Insights Service
**File**: `/app/backend/services/adaptive_insights_service.py`

```python
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text, select, func, desc, asc
from database import SessionLocal, UserDashboardInsights, UserPreSessionInsights

logger = logging.getLogger(__name__)

class AdaptiveInsightsService:
    """Service for extracting adaptive learning insights from user data"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def build_all_time_slice(self, user_id: str) -> Dict[str, Any]:
        """Build all-time journey data slice"""
        db = SessionLocal()
        try:
            # Get overall accuracy progression (first vs latest session)
            overall_accuracy = self._get_overall_accuracy_progression(db, user_id)
            
            # Get concept journeys from learner_notebook
            concept_journeys = self._get_concept_journeys_all_time(db, user_id)
            
            # Get coverage analysis (relief vs rising debt)
            coverage_analysis = self._get_coverage_analysis_all_time(db, user_id)
            
            # Get PYQ totals and accuracy
            pyq_totals = self._get_pyq_totals(db, user_id)
            
            # Get consistency streaks
            streaks = self._get_consistency_streaks(db, user_id)
            
            return {
                "range_sessions": "all",
                "overall": overall_accuracy,
                "concepts_journey": concept_journeys,
                "coverage_alltime": coverage_analysis,
                "pyq_totals": pyq_totals,
                "streaks": streaks
            }
        finally:
            db.close()
    
    def build_recent_slice(self, user_id: str, window: int = 20) -> Dict[str, Any]:
        """Build recent momentum data slice (last N sessions)"""
        db = SessionLocal()
        try:
            # Get recent session IDs
            recent_sessions = self._get_recent_session_ids(db, user_id, window)
            
            # Get accuracy series for recent sessions
            accuracy_series = self._get_accuracy_series(db, user_id, recent_sessions)
            
            # Get concept shifts in recent period
            concept_shifts = self._get_concept_shifts_recent(db, user_id, recent_sessions)
            
            # Get coverage changes (relief vs rising)
            coverage_recent = self._get_coverage_analysis_recent(db, user_id, recent_sessions)
            
            # Get recent PYQ performance
            pyq_recent = self._get_pyq_performance_recent(db, user_id, recent_sessions)
            
            return {
                "range_sessions": window,
                "accuracy_series": accuracy_series,
                "concept_shifts_recent": concept_shifts,
                "coverage_recent": coverage_recent,
                "pyq_recent": pyq_recent
            }
        finally:
            db.close()
    
    def build_pre_session_slice(self, user_id: str, session_id: str, window: int = 5) -> Dict[str, Any]:
        """Build pre-session insight data slice (last 5 + today's preview)"""
        db = SessionLocal()
        try:
            # Get last 5 session accuracy trend
            recent_sessions = self._get_recent_session_ids(db, user_id, window)
            accuracy_series = self._get_accuracy_series(db, user_id, recent_sessions)
            
            # Get concept shifts in last 5 sessions
            concept_shifts = self._get_concept_shifts_recent(db, user_id, recent_sessions)
            
            # Get most significant coverage change
            coverage_change = self._get_top_coverage_change(db, user_id, recent_sessions)
            
            # Get today's session preview
            today_preview = self._get_session_preview(db, session_id)
            
            return {
                "window": window,
                "accuracy_series": accuracy_series,
                "concept_shifts": concept_shifts,
                "coverage_change": coverage_change,
                "today_preview": today_preview
            }
        finally:
            db.close()
    
    def _get_overall_accuracy_progression(self, db: Session, user_id: str) -> Dict[str, float]:
        """Get first vs latest session accuracy"""
        query = text("""
            WITH acc AS (
                SELECT s.session_id, s.completed_at,
                       AVG(CASE WHEN a.was_correct THEN 1 ELSE 0 END)::float AS acc
                FROM sessions s
                JOIN attempt_events a ON a.session_id = s.session_id
                WHERE s.user_id = :user_id AND s.status = 'completed'
                GROUP BY s.session_id, s.completed_at
                ORDER BY s.completed_at ASC
            )
            SELECT 
                (ARRAY(SELECT acc FROM acc ORDER BY completed_at ASC))[1] AS acc_start,
                (ARRAY(SELECT acc FROM acc ORDER BY completed_at DESC))[1] AS acc_now
        """)
        
        result = db.execute(query, {"user_id": user_id}).fetchone()
        if not result or result.acc_start is None:
            return {"acc_start": 0.0, "acc_now": 0.0}
        
        return {
            "acc_start": float(result.acc_start or 0.0),
            "acc_now": float(result.acc_now or 0.0)
        }
    
    def compute_focus_concepts_for_pack(self, session_id: str) -> List[str]:
        """Get top focus concepts from session pack questions"""
        db = SessionLocal()
        try:
            query = text("""
                SELECT spq.question_data
                FROM session_pack_questions spq
                WHERE spq.session_id = :session_id
            """)
            
            results = db.execute(query, {"session_id": session_id}).fetchall()
            
            concept_counts = {}
            for row in results:
                question_data = row.question_data
                if isinstance(question_data, dict) and 'core_concepts' in question_data:
                    core_concepts = question_data['core_concepts']
                    if isinstance(core_concepts, list):
                        for concept in core_concepts:
                            concept_counts[concept] = concept_counts.get(concept, 0) + 1
            
            # Return top 3 most frequent concepts
            sorted_concepts = sorted(concept_counts.items(), key=lambda x: x[1], reverse=True)
            return [concept for concept, count in sorted_concepts[:3]]
            
        finally:
            db.close()
    
    def extract_pyq_counts_for_pack(self, session_id: str) -> Dict[str, int]:
        """Get PYQ counts from session pack questions"""
        db = SessionLocal()
        try:
            query = text("""
                SELECT 
                    SUM(CASE WHEN (spq.question_data->>'pyq_frequency_score')::float >= 1.5 THEN 1 ELSE 0 END) AS pyq15_count,
                    SUM(CASE WHEN (spq.question_data->>'pyq_frequency_score')::float >= 1.0 
                                  AND (spq.question_data->>'pyq_frequency_score')::float < 1.5 THEN 1 ELSE 0 END) AS pyq10_count
                FROM session_pack_questions spq
                WHERE spq.session_id = :session_id
            """)
            
            result = db.execute(query, {"session_id": session_id}).fetchone()
            
            return {
                "pyq15_count": int(result.pyq15_count or 0),
                "pyq10_count": int(result.pyq10_count or 0)
            }
            
        finally:
            db.close()

# Global service instance
adaptive_insights_service = AdaptiveInsightsService()
```

## Phase 3: LLM Insight Generation Service (3 hours)

### 3.1 Create Insight Generator Service
**File**: `/app/backend/services/insight_generator_service.py`

```python
import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

# Import existing LLM utils
from llm_utils import call_llm_with_fallback

logger = logging.getLogger(__name__)

class InsightGeneratorService:
    """Service for generating LLM-powered adaptive insights with fallbacks"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def gen_all_time_markdown(self, slice_dict: Dict[str, Any]) -> str:
        """Generate all-time journey markdown with LLM + fallback"""
        try:
            prompt = self._build_all_time_prompt(slice_dict)
            response = call_llm_with_fallback(
                prompt=prompt,
                model_primary="gpt-4o",
                model_fallback="gemini-2.5-flash",
                max_tokens=300
            )
            
            if response and len(response.strip()) > 10:
                return response.strip()
            else:
                return self._fallback_all_time_markdown(slice_dict)
                
        except Exception as e:
            self.logger.error(f"LLM call failed for all-time insights: {e}")
            return self._fallback_all_time_markdown(slice_dict)
    
    def gen_recent_markdown(self, slice_dict: Dict[str, Any]) -> str:
        """Generate recent momentum markdown with LLM + fallback"""
        try:
            prompt = self._build_recent_prompt(slice_dict)
            response = call_llm_with_fallback(
                prompt=prompt,
                model_primary="gpt-4o", 
                model_fallback="gemini-2.5-flash",
                max_tokens=200
            )
            
            if response and len(response.strip()) > 10:
                return response.strip()
            else:
                return self._fallback_recent_markdown(slice_dict)
                
        except Exception as e:
            self.logger.error(f"LLM call failed for recent insights: {e}")
            return self._fallback_recent_markdown(slice_dict)
    
    def gen_pre_session_card(self, slice_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Generate pre-session card with LLM + fallback"""
        try:
            prompt = self._build_pre_session_prompt(slice_dict)
            response = call_llm_with_fallback(
                prompt=prompt,
                model_primary="gpt-4o",
                model_fallback="gemini-2.5-flash", 
                max_tokens=150
            )
            
            if response:
                try:
                    # Parse JSON response
                    card_data = json.loads(response.strip())
                    if self._validate_card_format(card_data):
                        return card_data
                except json.JSONDecodeError:
                    pass
            
            return self._fallback_pre_session_card(slice_dict)
            
        except Exception as e:
            self.logger.error(f"LLM call failed for pre-session card: {e}")
            return self._fallback_pre_session_card(slice_dict)
    
    def _build_all_time_prompt(self, slice_dict: Dict[str, Any]) -> str:
        """Build prompt for all-time insights"""
        return f"""Write an "All-Time Journey" section using ONLY the JSON provided below.
Include:
- 1 sentence on overall accuracy (start → now).
- 3–5 bullets for concept journeys (from → to) with deltas.
- 1 bullet for coverage relief and 1 for rising gaps.
- 1 sentence on cumulative PYQ counts and accuracy.
- Optional: 1 sentence for longest consistency streak.

Tone: coach-like, simple words, no jargon, no invented data.

JSON Data:
{json.dumps(slice_dict, indent=2)}

Response (markdown format):"""

# Global service instance
insight_generator_service = InsightGeneratorService()
```

## Phase 4: Cache Management Service (2 hours)

### 4.1 Create Insight Cache Service
**File**: `/app/backend/services/insight_cache_service.py`

```python
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from database import SessionLocal, UserDashboardInsights, UserPreSessionInsights, UserInsightDebug
from services.adaptive_insights_service import adaptive_insights_service
from services.insight_generator_service import insight_generator_service

logger = logging.getLogger(__name__)

class InsightCacheService:
    """Service for managing adaptive insights cache with TTL and refresh logic"""
    
    def __init__(self):
        self.cache_ttl_hours = 24
        self.logger = logging.getLogger(__name__)
    
    def get_dashboard_insights(self, user_id: str) -> Dict[str, Any]:
        """Get dashboard insights with cache-first strategy"""
        db = SessionLocal()
        try:
            # Check cache first
            cache_entry = db.query(UserDashboardInsights).filter(
                UserDashboardInsights.user_id == user_id
            ).first()
            
            # Determine if cache is fresh
            if cache_entry and self._is_cache_fresh(cache_entry.last_updated_at):
                return {
                    "all_time_markdown": cache_entry.all_time_insights.get("markdown", ""),
                    "recent_markdown": cache_entry.recent_insights.get("markdown", ""),
                    "last_updated_at": cache_entry.last_updated_at.isoformat()
                }
            
            # Cache is stale or missing - refresh synchronously
            return self.refresh_dashboard_cache(user_id)
            
        except Exception as e:
            self.logger.error(f"Error getting dashboard insights for user {user_id[:8]}: {e}")
            return self._empty_dashboard_response()
        finally:
            db.close()
    
    def get_pre_session_insight(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Get pre-session insight with cache-first strategy"""
        db = SessionLocal()
        try:
            # Check cache first
            cache_entry = db.query(UserPreSessionInsights).filter(
                UserPreSessionInsights.user_id == user_id
            ).first()
            
            # For pre-session, refresh daily or if no cache exists
            if cache_entry and self._is_cache_fresh(cache_entry.last_updated_at, hours=24):
                insight_card = cache_entry.insight_card
                insight_card["last_updated_at"] = cache_entry.last_updated_at.isoformat()
                return insight_card
            
            # Cache is stale or missing - refresh
            return self.refresh_pre_session_cache(user_id, session_id)
            
        except Exception as e:
            self.logger.error(f"Error getting pre-session insight for user {user_id[:8]}: {e}")
            return self._empty_pre_session_response()
        finally:
            db.close()

# Global service instance  
insight_cache_service = InsightCacheService()
```

## Phase 5: API Endpoints (1.5 hours)

### 5.1 Add Endpoints to Server
**File**: `/app/backend/server.py` (add these endpoints)

```python
from services.insight_cache_service import insight_cache_service

@app.get("/api/dashboard/adaptive-insights")
async def get_dashboard_adaptive_insights(user_id: str = Depends(get_current_user)):
    """Get adaptive insights for dashboard (all-time + recent momentum)"""
    try:
        insights = insight_cache_service.get_dashboard_insights(user_id)
        return insights
    except Exception as e:
        logger.error(f"Error getting dashboard insights for user {user_id[:8]}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load adaptive insights")

@app.get("/api/session/pre-session-insight")
async def get_pre_session_insight(
    session_id: Optional[str] = None,
    user_id: str = Depends(get_current_user)
):
    """Get pre-session insight card"""
    try:
        # If no session_id provided, try to get the latest planned session
        if not session_id:
            # Get user's latest planned session from session_packs
            db = SessionLocal()
            try:
                latest_pack = db.execute(text("""
                    SELECT session_id FROM session_packs 
                    WHERE user_id = :user_id 
                    ORDER BY created_at DESC 
                    LIMIT 1
                """), {"user_id": user_id}).fetchone()
                
                if latest_pack:
                    session_id = latest_pack.session_id
                else:
                    session_id = "preview-session"  # Fallback
            finally:
                db.close()
        
        insight_card = insight_cache_service.get_pre_session_insight(user_id, session_id)
        return insight_card
        
    except Exception as e:
        logger.error(f"Error getting pre-session insight for user {user_id[:8]}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load pre-session insight")
```

## Phase 6: Background Job Integration (2 hours)

### 6.1 Add Insight Update Job
**File**: `/app/backend/services/simplified_job_handlers.py` (add to existing file)

```python
from services.insight_cache_service import insight_cache_service

async def handle_update_insights(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Job C: UPDATE_INSIGHTS
    - Refresh dashboard insights cache
    - Refresh pre-session insights cache
    """
    user_id = job["user_id"]
    session_id = job.get("session_id")  # Optional
    
    try:
        logger.info(f"🔄 Starting UPDATE_INSIGHTS for user {user_id[:8]}")
        
        # Refresh dashboard cache
        dashboard_result = insight_cache_service.refresh_dashboard_cache(user_id)
        
        # Refresh pre-session cache if session_id provided
        pre_session_result = None
        if session_id:
            pre_session_result = insight_cache_service.refresh_pre_session_cache(user_id, session_id)
        
        logger.info(f"✅ UPDATE_INSIGHTS completed for user {user_id[:8]}")
        
        return {
            "success": True,
            "user_id": user_id,
            "session_id": session_id,
            "dashboard_updated": bool(dashboard_result),
            "pre_session_updated": bool(pre_session_result),
            "completed_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ UPDATE_INSIGHTS failed for user {user_id[:8]}: {e}")
        raise Exception(f"Insight update failed: {str(e)}")
```

### 6.2 Update Job Handler Registration
**File**: `/app/backend/services/bg_job_queue.py` (add to job handler mapping)

```python
# Add to existing job handler mapping
JOB_HANDLERS = {
    "SUMMARIZE_SESSION": handle_summarize_session,
    "PLAN_NEXT_SESSION": handle_personalized_planning,
    "UPDATE_INSIGHTS": handle_update_insights  # New handler
}
```

## Phase 7: Frontend Integration (3 hours)

### 7.1 Update Dashboard Component
**File**: `/app/frontend/src/components/Dashboard.js` (add adaptive insights section)

```javascript
// Add to existing imports
import { useState, useEffect } from 'react';
import { useAuth } from './AuthProvider';

// Add adaptive insights state
const [adaptiveInsights, setAdaptiveInsights] = useState(null);
const [insightsLoading, setInsightsLoading] = useState(false);

// Add fetch function
const fetchAdaptiveInsights = async () => {
  if (!isAuthenticated()) return;
  
  setInsightsLoading(true);
  try {
    const token = localStorage.getItem('cat_prep_token');
    const response = await fetch(`${API}/dashboard/adaptive-insights`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (response.ok) {
      const insights = await response.json();
      setAdaptiveInsights(insights);
    } else {
      console.error('Failed to fetch adaptive insights');
    }
  } catch (error) {
    console.error('Error fetching adaptive insights:', error);
  } finally {
    setInsightsLoading(false);
  }
};

// Add to useEffect
useEffect(() => {
  if (isAuthenticated()) {
    // ... existing dashboard data fetching ...
    fetchAdaptiveInsights();
  }
}, [isAuthenticated]);

// Add adaptive insights section to render
const renderAdaptiveInsights = () => {
  if (insightsLoading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="space-y-2">
            <div className="h-4 bg-gray-200 rounded w-full"></div>
            <div className="h-4 bg-gray-200 rounded w-5/6"></div>
            <div className="h-4 bg-gray-200 rounded w-4/6"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!adaptiveInsights) return null;

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Adaptive Insights</h3>
        <span className="text-xs text-gray-500">
          Updated {new Date(adaptiveInsights.last_updated_at).toLocaleDateString()}
        </span>
      </div>
      
      {/* All-Time Journey Section */}
      <div className="mb-6">
        <button 
          className="flex items-center justify-between w-full text-left"
          onClick={() => setAllTimeExpanded(!allTimeExpanded)}
        >
          <h4 className="text-md font-medium text-gray-800 flex items-center">
            <span className="mr-2">🏁</span>
            All-Time Journey
          </h4>
          <svg 
            className={`w-4 h-4 transform transition-transform ${allTimeExpanded ? 'rotate-180' : ''}`}
            fill="none" stroke="currentColor" viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        
        {allTimeExpanded && (
          <div className="mt-3 pl-6 prose prose-sm max-w-none">
            <div dangerouslySetInnerHTML={{ 
              __html: markdownToHtml(adaptiveInsights.all_time_markdown) 
            }} />
          </div>
        )}
      </div>

      {/* Recent Momentum Section */}
      <div>
        <button 
          className="flex items-center justify-between w-full text-left"
          onClick={() => setRecentExpanded(!recentExpanded)}
        >
          <h4 className="text-md font-medium text-gray-800 flex items-center">
            <span className="mr-2">📈</span>
            Recent Momentum
          </h4>
          <svg 
            className={`w-4 h-4 transform transition-transform ${recentExpanded ? 'rotate-180' : ''}`}
            fill="none" stroke="currentColor" viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        
        {recentExpanded && (
          <div className="mt-3 pl-6 prose prose-sm max-w-none">
            <div dangerouslySetInnerHTML={{ 
              __html: markdownToHtml(adaptiveInsights.recent_markdown) 
            }} />
          </div>
        )}
      </div>
    </div>
  );
};

// Add expansion state
const [allTimeExpanded, setAllTimeExpanded] = useState(true);  // Expanded by default for new users
const [recentExpanded, setRecentExpanded] = useState(true);   // Expanded for active users

// Simple markdown to HTML converter (basic)
const markdownToHtml = (markdown) => {
  return markdown
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')  // Bold
    .replace(/^\* (.*)/gm, '<li>$1</li>')              // List items
    .replace(/\n/g, '<br>')                            // Line breaks
    .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>');       // Wrap lists
};
```

### 7.2 Update Session Start Component
**File**: `/app/frontend/src/components/SessionSystem.js` (add pre-session insight modal)

```javascript
// Add pre-session insight state
const [preSessionInsight, setPreSessionInsight] = useState(null);
const [showPreSessionModal, setShowPreSessionModal] = useState(false);

// Add fetch function
const fetchPreSessionInsight = async () => {
  try {
    const token = localStorage.getItem('cat_prep_token');
    const response = await fetch(`${API}/session/pre-session-insight`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (response.ok) {
      const insight = await response.json();
      setPreSessionInsight(insight);
      setShowPreSessionModal(true);
    }
  } catch (error) {
    console.error('Error fetching pre-session insight:', error);
  }
};

// Modify session start flow to show insight first
const handleStartSession = async () => {
  // First fetch and show pre-session insight
  await fetchPreSessionInsight();
  // Modal will show, user clicks "Start Session" to proceed
};

// Pre-session insight modal
const renderPreSessionModal = () => {
  if (!showPreSessionModal || !preSessionInsight) return null;
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
        <div className="text-center mb-4">
          <h2 className="text-xl font-bold text-gray-900 mb-2">
            {preSessionInsight.title}
          </h2>
        </div>
        
        <div className="space-y-4 mb-6">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <p className="text-blue-800 text-sm">
              {preSessionInsight.progress}
            </p>
          </div>
          
          {preSessionInsight.way_forward && preSessionInsight.way_forward.length > 0 && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-3">
              <p className="text-green-800 text-sm font-medium mb-2">Way Forward:</p>
              <ul className="text-green-700 text-sm space-y-1">
                {preSessionInsight.way_forward.map((item, index) => (
                  <li key={index}>• {item}</li>
                ))}
              </ul>
            </div>
          )}
          
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
            <p className="text-yellow-800 text-sm">
              <strong>Today:</strong> {preSessionInsight.today}
            </p>
          </div>
        </div>
        
        <div className="flex space-x-3">
          <button
            onClick={() => setShowPreSessionModal(false)}
            className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={() => {
              setShowPreSessionModal(false);
              startActualSession();  // Proceed with session start
            }}
            className="flex-1 px-4 py-2 bg-[#9ac026] text-white rounded-lg hover:bg-[#8bb024]"
          >
            Start Session
          </button>
        </div>
      </div>
    </div>
  );
};

// Add to render
{renderPreSessionModal()}
```

## Phase 8: Core Concepts Integration Verification (1 hour)

### 8.1 Verify Concept Normalization
**File**: Check if `/app/backend/services/simplified_job_handlers.py` uses concept normalization

```python
# Verify this function exists and is called
def normalize_concept_via_alias_map(user_id: str, raw_concept: str) -> str:
    """Normalize concept using user's alias map"""
    # Implementation should exist - verify it's being used
    pass

# Check if concept normalization is used in session summarization
# Look for calls to concept_alias_map_latest table updates
```

### 8.2 Add Missing Concept Normalization (if needed)
**File**: `/app/backend/services/adaptive_insights_service.py` (add concept normalization helper)

```python
def _normalize_concepts(self, user_id: str, concepts: List[str]) -> List[str]:
    """Normalize concepts using alias map"""
    db = SessionLocal()
    try:
        normalized = []
        for concept in concepts:
            # Query concept_alias_map_latest for normalization
            query = text("""
                SELECT concept_norm 
                FROM concept_alias_map_latest 
                WHERE user_id = :user_id AND concept_raw = :concept_raw
            """)
            
            result = db.execute(query, {
                "user_id": user_id,
                "concept_raw": concept
            }).fetchone()
            
            if result:
                normalized.append(result.concept_norm)
            else:
                normalized.append(concept)  # Fallback to raw concept
        
        return normalized
    finally:
        db.close()
```

## Phase 9: Testing & Optimization (2 hours)

### 9.1 Create Test Script
**File**: `/app/backend/test_adaptive_insights.py`

```python
"""Test script for adaptive insights functionality"""
import asyncio
from services.adaptive_insights_service import adaptive_insights_service
from services.insight_generator_service import insight_generator_service
from services.insight_cache_service import insight_cache_service

async def test_adaptive_insights():
    """Test complete adaptive insights flow"""
    test_user_id = "test-user-uuid"
    test_session_id = "test-session-uuid"
    
    print("🧪 Testing Adaptive Insights System")
    
    try:
        # Test 1: Data extraction
        print("\n1. Testing data extraction...")
        all_time_slice = adaptive_insights_service.build_all_time_slice(test_user_id)
        print(f"✅ All-time slice: {len(all_time_slice)} keys")
        
        recent_slice = adaptive_insights_service.build_recent_slice(test_user_id, window=20)
        print(f"✅ Recent slice: {len(recent_slice)} keys")
        
        pre_session_slice = adaptive_insights_service.build_pre_session_slice(test_user_id, test_session_id, window=5)
        print(f"✅ Pre-session slice: {len(pre_session_slice)} keys")
        
        # Test 2: LLM generation
        print("\n2. Testing insight generation...")
        all_time_markdown = insight_generator_service.gen_all_time_markdown(all_time_slice)
        print(f"✅ All-time markdown: {len(all_time_markdown)} characters")
        
        recent_markdown = insight_generator_service.gen_recent_markdown(recent_slice)
        print(f"✅ Recent markdown: {len(recent_markdown)} characters")
        
        pre_session_card = insight_generator_service.gen_pre_session_card(pre_session_slice)
        print(f"✅ Pre-session card: {list(pre_session_card.keys())}")
        
        # Test 3: Cache operations
        print("\n3. Testing cache operations...")
        dashboard_insights = insight_cache_service.refresh_dashboard_cache(test_user_id)
        print(f"✅ Dashboard cache updated: {list(dashboard_insights.keys())}")
        
        pre_session_insights = insight_cache_service.refresh_pre_session_cache(test_user_id, test_session_id)
        print(f"✅ Pre-session cache updated: {list(pre_session_insights.keys())}")
        
        print("\n🎉 All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_adaptive_insights())
```

### 9.2 Performance Testing
**File**: `/app/backend/test_performance.py`

```python
"""Performance test for adaptive insights queries"""
import time
from services.adaptive_insights_service import adaptive_insights_service

def test_query_performance():
    """Test query performance with different user profiles"""
    test_users = [
        "new-user-uuid",      # New user with few sessions
        "active-user-uuid",   # Active user with 50+ sessions  
        "power-user-uuid"     # Power user with 100+ sessions
    ]
    
    for user_id in test_users:
        print(f"\n📊 Testing performance for {user_id}")
        
        # Test all-time slice performance
        start_time = time.time()
        all_time_slice = adaptive_insights_service.build_all_time_slice(user_id)
        all_time_duration = time.time() - start_time
        print(f"All-time slice: {all_time_duration:.3f}s")
        
        # Test recent slice performance
        start_time = time.time()
        recent_slice = adaptive_insights_service.build_recent_slice(user_id, window=20)
        recent_duration = time.time() - start_time
        print(f"Recent slice: {recent_duration:.3f}s")
        
        # Test pre-session slice performance
        start_time = time.time()
        pre_session_slice = adaptive_insights_service.build_pre_session_slice(user_id, "test-session", window=5)
        pre_session_duration = time.time() - start_time
        print(f"Pre-session slice: {pre_session_duration:.3f}s")
        
        total_duration = all_time_duration + recent_duration + pre_session_duration
        print(f"Total extraction time: {total_duration:.3f}s")
        
        if total_duration > 2.0:
            print("⚠️ Performance warning: Query time > 2s")
        else:
            print("✅ Performance acceptable")

if __name__ == "__main__":
    test_query_performance()
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

## Technical Architecture

### Data Flow
```
Session Completion → Background Jobs → Data Extraction → LLM Generation → Cache Update → API Response → Frontend Display
```

### Cache Strategy
- **Dashboard**: 24h TTL, refresh after session completion
- **Pre-Session**: Daily refresh or when new pack created
- **Fallbacks**: Always return last good cache on LLM failure

### Core Concepts Integration
- **Normalization**: Use `concept_alias_map_latest` for semantic grouping
- **Journeys**: Track readiness changes at concept level
- **Coverage**: Map debt pairs to primary concepts
- **Preview**: Extract focus concepts from actual session packs

This implementation plan provides the complete technical roadmap for delivering the "Proof of the Pudding" adaptive insights feature with all specified requirements.
# Twelvr Session System - Technical Analysis & Documentation

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Database Schema](#database-schema)
3. [Session Planning System](#session-planning-system)
4. [Session Display & Execution](#session-display--execution)
5. [Session Summarization](#session-summarization)
6. [Notebook & Allied Functions](#notebook--allied-functions)
7. [API Endpoints Reference](#api-endpoints-reference)
8. [Frontend Components](#frontend-components)
9. [Data Flow Diagrams](#data-flow-diagrams)
10. [Current Issues & Recommendations](#current-issues--recommendations)

---

## Architecture Overview

### High-Level System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Dashboard     │    │ Session Planner │    │ Session Engine  │
│   (Frontend)    │───▶│   (Backend)     │───▶│   (Frontend)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Progress APIs   │    │ Adaptive Engine │    │ Question Logger │
│   (Backend)     │    │   (Backend)     │    │   (Backend)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Session Summary │    │ Coverage System │    │    Notebook     │
│   (Backend)     │    │   (Backend)     │    │   (Frontend)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Technology Stack
- **Frontend**: React.js with hooks, Axios for HTTP requests
- **Backend**: FastAPI (Python), PostgreSQL database
- **Session Management**: JWT-based authentication, localStorage for client state
- **Real-time Features**: Smart polling with exponential backoff

---

## Database Schema

### Core Tables

#### 1. Sessions Table
```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    session_type VARCHAR(50) DEFAULT 'adaptive',
    status VARCHAR(50) DEFAULT 'created', -- created, started, completed, abandoned
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    total_questions INTEGER DEFAULT 12,
    questions_answered INTEGER DEFAULT 0,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### 2. Question Actions Log
```sql
CREATE TABLE question_actions (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES sessions(id),
    question_id UUID NOT NULL,
    action VARCHAR(50) NOT NULL, -- submit, skip, doubt
    user_answer TEXT,
    is_correct BOOLEAN,
    timestamp TIMESTAMP DEFAULT NOW(),
    data JSONB -- Additional metadata
);
```

#### 3. Session Progress Tracking
```sql
CREATE TABLE session_progress (
    session_id UUID PRIMARY KEY REFERENCES sessions(id),
    user_id UUID NOT NULL,
    current_question_index INTEGER DEFAULT 0,
    total_questions INTEGER DEFAULT 12,
    last_question_id UUID,
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### 4. Adaptive Packs
```sql
CREATE TABLE adaptive_packs (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES sessions(id),
    user_id UUID NOT NULL,
    pack_data JSONB, -- Array of question objects
    served_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'prepared', -- prepared, served, consumed
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### 5. Coverage Ledger
```sql
CREATE TABLE coverage_ledger (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    item_id UUID NOT NULL,
    subcategory VARCHAR(255),
    difficulty_band VARCHAR(50),
    exposure_count INTEGER DEFAULT 0,
    last_seen TIMESTAMP,
    performance_score FLOAT DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Session Planning System

### 1. Entry Point: Dashboard Session Initiation

**Frontend Component**: `Dashboard.js`
```javascript
// Location: /app/frontend/src/components/Dashboard.js
// Function: startSession()

const startSession = async () => {
  // 1. Check for incomplete sessions
  const incompleteSession = await checkForIncompleteSession();
  
  // 2. If no incomplete session, start new planning
  if (!incompleteSession) {
    const result = await planSessionWithPolling({
      api: configuredAxios,
      userId: user.id,
      lastSessionId: null,
      idempotencyKey: generateIdempotencyKey(),
      budgetMs: 75000,
      baseDelay: 1000,
      maxDelay: 8000,
      timeoutPerRequest: 8000,
      treat404AsPreparingMs: 65000
    });
  }
};
```

### 2. Session Planning API

**Backend Endpoint**: `/api/adapt/plan-next`
**File**: `/app/backend/api/v2_adapt.py`

```python
@router.post("/plan-next")
async def plan_next_session(
    request: PlanNextRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Plan the next adaptive session for a user
    - Analyzes user's coverage data
    - Generates optimized question selection
    - Creates session pack asynchronously
    """
    
    # 1. Validate input and idempotency
    session_id = request.next_session_id
    user_id = request.user_id
    
    # 2. Check for existing session
    existing_pack = get_existing_pack(db, user_id, session_id)
    if existing_pack:
        return {"status": "ready", "session_id": session_id}
    
    # 3. Trigger async background planning
    background_tasks.add_task(
        plan_session_background,
        user_id=user_id,
        session_id=session_id,
        last_session_id=request.last_session_id,
        db_url=get_db_url()
    )
    
    return {"status": "planning", "session_id": session_id}
```

### 3. Background Planning Logic

**Function**: `plan_session_background()`
```python
async def plan_session_background(user_id: str, session_id: str, last_session_id: str, db_url: str):
    """
    Background task for session planning
    """
    # 1. Get user's coverage data
    coverage_data = get_user_coverage_ledger(db, user_id)
    
    # 2. Generate question selection recipe
    selection_recipe = generate_selection_recipe(coverage_data)
    
    # 3. Execute deterministic picker
    selected_questions = execute_deterministic_picker(
        recipe=selection_recipe,
        difficulty_distribution={
            "Easy": 3,
            "Medium": 6, 
            "Hard": 3
        },
        pyq_constraints=get_pyq_constraints()
    )
    
    # 4. Create and store pack
    pack_data = create_session_pack(selected_questions)
    store_adaptive_pack(db, user_id, session_id, pack_data)
    
    # 5. Update coverage expectations
    update_coverage_ledger(db, user_id, selected_questions)
```

### 4. Smart Polling System

**Frontend Utility**: `/app/frontend/src/utils/smartPolling.js`
```javascript
class SmartPoller {
  constructor(api, endpoint, params, options) {
    this.api = api;
    this.endpoint = endpoint;
    this.params = params;
    this.budgetMs = options.budgetMs || 60000;
    this.baseDelay = options.baseDelay || 1000;
    this.maxDelay = options.maxDelay || 8000;
  }
  
  async poll() {
    let attempts = 0;
    const startTime = Date.now();
    
    while (Date.now() - startTime < this.budgetMs) {
      try {
        const response = await this.api.get(this.endpoint, { params: this.params });
        
        if (response.status === 200) {
          return { success: true, data: response.data, attempts };
        }
        
        if (response.status === 404) {
          // Treat as "still preparing"
          await this.delay(this.calculateDelay(attempts));
          attempts++;
          continue;
        }
        
      } catch (error) {
        if (error.response?.status === 404) {
          await this.delay(this.calculateDelay(attempts));
          attempts++;
          continue;
        }
        throw error;
      }
    }
    
    return { success: false, error: "Polling timeout", attempts };
  }
}
```

---

## Session Display & Execution

### 1. Session System Component

**Frontend Component**: `/app/frontend/src/components/SessionSystem.js`

#### Key State Variables:
```javascript
const [sessionId, setSessionId] = useState(null);
const [currentQuestion, setCurrentQuestion] = useState(null);
const [currentPack, setCurrentPack] = useState([]);
const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
const [sessionProgress, setSessionProgress] = useState(null);
const [userAnswer, setUserAnswer] = useState('');
const [showResult, setShowResult] = useState(false);
const [result, setResult] = useState(null);
```

### 2. Pack Fetching Logic

**API Endpoint**: `/api/adapt/pack`
```javascript
const fetchPackSafe = async (userId, sessionId, retryCount = 0) => {
  try {
    const res = await fetch(`${API}/adapt/pack?user_id=${userId}&session_id=${sessionId}`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('cat_prep_token')}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (!res.ok) {
      if (res.status === 404 && retryCount < 3) {
        // Pack not ready yet, retry with exponential backoff
        await new Promise(resolve => setTimeout(resolve, (retryCount + 1) * 1000));
        return await fetchPackSafe(userId, sessionId, retryCount + 1);
      }
      throw new Error(`Pack fetch failed: ${res.status}`);
    }
    
    const data = await res.json();
    return data?.pack || [];
  } catch (error) {
    console.error('Pack fetch error:', error);
    return null;
  }
};
```

### 3. Question Serving Logic

**Function**: `serveQuestionFromPack()`
```javascript
const serveQuestionFromPack = (questionIndex) => {
  const livePack = currentPackRef.current;
  
  if (!livePack || questionIndex >= livePack.length) {
    // Session completion
    handleAdaptiveSessionCompletion();
    return;
  }
  
  const packItem = livePack[questionIndex];
  
  // Map pack item to question format
  const question = {
    id: packItem.id,                    // Correct field mapping
    stem: packItem.stem,                // Question text
    options: {
      a: packItem.option_a || 'Option A',
      b: packItem.option_b || 'Option B', 
      c: packItem.option_c || 'Option C',
      d: packItem.option_d || 'Option D'
    },
    has_image: false,
    subcategory: packItem.subcategory,
    difficulty_band: packItem.difficulty_band,
    right_answer: packItem.answer
  };
  
  setCurrentQuestion(question);
  setSessionProgress({
    current_question: questionIndex + 1,
    total_questions: livePack.length
  });
  
  // Track progress for resumption
  updateSessionProgress(questionIndex, question.id);
};
```

### 4. Answer Submission

**Frontend Function**: `submitAnswer()`
**Backend Endpoint**: `/api/log/question-action`

```javascript
const submitAnswer = async () => {
  const payload = {
    session_id: sessionId,
    question_id: currentQuestion?.id,    // Critical: Must match pack item.id
    action: 'submit',
    data: {
      user_answer: userAnswer,
      session_type: 'adaptive'
    },
    timestamp: new Date().toISOString()
  };
  
  const res = await fetch(`${API}/log/question-action`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${localStorage.getItem('cat_prep_token')}`
    },
    body: JSON.stringify(payload)
  });
  
  if (res.ok) {
    const responseData = await res.json();
    setResult(responseData.result);
    setShowResult(true);
  }
};
```

---

## Session Summarization

### 1. Session Completion Handler

**Frontend Function**: `handleAdaptiveSessionCompletion()`
```javascript
const handleAdaptiveSessionCompletion = async () => {
  try {
    // 1. Mark session as completed
    await axios.post(`${API}/sessions/mark-completed`, {
      session_id: sessionId
    });
    
    // 2. Clear session progress tracking
    await clearSessionProgress(sessionId);
    
    // 3. Trigger next session pre-planning
    await triggerNextSessionPreWarming();
    
    // 4. Call completion callback
    if (onSessionEnd) {
      onSessionEnd({
        completed: true,
        questionsCompleted: currentPack.length,
        totalQuestions: currentPack.length
      });
    }
  } catch (error) {
    console.error('Session completion failed:', error);
  }
};
```

### 2. Backend Session Completion

**API Endpoint**: `/api/sessions/mark-completed`
```python
@app.post("/sessions/mark-completed")
async def mark_session_completed(
    request: MarkCompletedRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a session as completed and update timestamps"""
    session_id = request.session_id
    
    # Update session status
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.user_id == current_user.id
    ).first()
    
    if session:
        session.status = 'completed'
        session.completed_at = datetime.now(timezone.utc)
        db.commit()
        
        # Trigger summary generation
        generate_session_summary.delay(session_id)
    
    return {"success": True}
```

### 3. Summary Generation Process

**Background Task**: `generate_session_summary()`
```python
@celery_app.task
def generate_session_summary(session_id: str):
    """Generate comprehensive session summary"""
    
    # 1. Get session data
    session = get_session_by_id(session_id)
    question_actions = get_session_question_actions(session_id)
    
    # 2. Calculate performance metrics
    summary_data = {
        "session_id": session_id,
        "total_questions": len(question_actions),
        "correct_answers": sum(1 for qa in question_actions if qa.is_correct),
        "accuracy": calculate_accuracy(question_actions),
        "time_spent": calculate_time_spent(session),
        "category_breakdown": generate_category_breakdown(question_actions),
        "difficulty_analysis": generate_difficulty_analysis(question_actions),
        "learning_insights": generate_learning_insights(question_actions),
        "next_focus_areas": identify_focus_areas(question_actions)
    }
    
    # 3. Store summary
    store_session_summary(session_id, summary_data)
    
    # 4. Update user's learning notebook
    update_learner_notebook(session.user_id, summary_data)
    
    return summary_data
```

---

## Notebook & Allied Functions

### 1. Learner Notebook Structure

**Database Table**: `learner_notebook`
```sql
CREATE TABLE learner_notebook (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    session_id UUID REFERENCES sessions(id),
    entry_type VARCHAR(50), -- summary, insight, milestone
    content JSONB,
    tags TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 2. Doubt System

**Frontend Component**: Integrated in `SessionSystem.js`
```javascript
const handleAskDoubt = async () => {
  try {
    const response = await axios.post(`${API}/doubts/ask`, {
      question_id: currentQuestion.id,
      session_id: sessionId,
      message: doubtMessage.trim()
    });
    
    if (response.data.success) {
      setMessageCount(response.data.message_count);
      setRemainingMessages(response.data.remaining_messages);
      await loadDoubtHistory();
    }
  } catch (error) {
    console.error('Doubt submission failed:', error);
  }
};
```

**Backend Endpoint**: `/api/doubts/ask`
```python
@router.post("/ask")
async def ask_doubt(
    request: DoubtRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Handle doubt submission with AI-powered responses"""
    
    # 1. Check message limits
    if user_exceeds_doubt_limit(current_user.id, db):
        raise HTTPException(400, "Daily doubt limit exceeded")
    
    # 2. Get question context
    question_context = get_question_context(request.question_id, db)
    
    # 3. Generate AI response
    ai_response = await generate_doubt_response(
        question_context=question_context,
        user_message=request.message,
        conversation_history=get_doubt_history(request.question_id, current_user.id, db)
    )
    
    # 4. Store conversation
    store_doubt_conversation(db, {
        "question_id": request.question_id,
        "session_id": request.session_id,
        "user_id": current_user.id,
        "user_message": request.message,
        "ai_response": ai_response
    })
    
    return {
        "success": True,
        "response": ai_response,
        "remaining_messages": get_remaining_doubt_messages(current_user.id, db)
    }
```

---

## API Endpoints Reference

### Session Management
```
POST /api/adapt/plan-next          # Plan next session
GET  /api/adapt/pack               # Get session pack
POST /api/adapt/mark-served        # Mark pack as served
POST /api/sessions/mark-started    # Mark session started
POST /api/sessions/mark-completed  # Mark session completed
```

### Progress Tracking  
```
GET  /api/session-progress/{session_id}           # Get session progress
POST /api/session-progress/update                # Update progress
GET  /api/session-progress/current/{user_id}     # Get current session
DELETE /api/session-progress/{session_id}        # Clear progress
```

### Question & Answer Logging
```
POST /api/log/question-action      # Log question action (submit/skip)
GET  /api/sessions/last-completed-id # Get last completed session
POST /api/sessions/report-broken-image # Report image issues
```

### Dashboard & Analytics
```
GET  /api/dashboard/simple-taxonomy     # Get basic session stats  
GET  /api/dashboard/categorized-taxonomy # Get categorized breakdown
GET  /api/dashboard/mastery            # Get mastery data
GET  /api/dashboard/progress           # Get detailed progress
GET  /api/user/session-limit-status    # Get session limits
```

### Doubt System
```
POST /api/doubts/ask                   # Submit doubt
GET  /api/doubts/{question_id}/history # Get doubt history
```

---

## Frontend Components

### Component Hierarchy
```
App
├── AuthProvider (Context)
├── Dashboard
│   ├── SimpleDashboard
│   ├── SessionStatus
│   └── Navigation
├── SessionSystem
│   ├── SessionErrorBoundary
│   ├── MathRenderer
│   └── DoubtModal
└── DashboardErrorBoundary
```

### Key Component Files
- `/app/frontend/src/components/Dashboard.js` - Main dashboard interface
- `/app/frontend/src/components/SessionSystem.js` - Session execution engine
- `/app/frontend/src/components/SimpleDashboard.js` - Progress visualization
- `/app/frontend/src/components/AuthProvider.js` - Authentication context
- `/app/frontend/src/utils/smartPolling.js` - Polling utility

---

## Data Flow Diagrams

### Session Creation Flow
```
Dashboard Click → Check Incomplete → Plan Session → Poll Pack → Serve Questions
     ↓                ↓                 ↓            ↓           ↓
User Intent → Progress API → Adaptive Engine → Pack Ready → Question Display
```

### Question Answering Flow  
```
User Selection → Submit Answer → Log Action → Calculate Result → Show Feedback → Next Question
      ↓              ↓            ↓            ↓              ↓           ↓
   Frontend → Question Logger → Coverage Update → Result Engine → UI Update → Progress Track
```

### Session Completion Flow
```
Last Question → Mark Complete → Generate Summary → Update Notebook → Pre-plan Next
      ↓             ↓              ↓               ↓              ↓
 Session End → Status Update → Background Task → Learning Data → Next Session
```

---

## Current Issues & Recommendations

### 1. Pack Data Structure Issues
**Current Problem**: Field mapping inconsistencies between pack data and frontend expectations
- Pack uses `packItem.id` but frontend expected `packItem.item_id`
- Pack uses `packItem.stem` but frontend expected `packItem.why`

**Fix Applied**: 
```javascript
// Fixed mapping in serveQuestionFromPack()
id: packItem.id,           // Was: packItem.item_id
stem: packItem.stem,       // Was: packItem.why
```

### 2. Async Session Planning
**Current Behavior**: 202 response with background processing
**Issue**: Frontend polling can timeout if planning takes too long

**Recommendation**: 
- Implement WebSocket notifications for pack readiness
- Add progress indicators for planning stages
- Implement pack caching for faster subsequent sessions

### 3. Error Handling
**Current State**: Added error boundaries and promise rejection handling
**Areas for Improvement**:
- More granular error classification
- User-friendly error messages
- Automatic retry mechanisms

### 4. Performance Optimizations
**Database Queries**:
- Add indexes on frequently queried fields
- Implement query result caching
- Optimize coverage ledger updates

**Frontend**:
- Implement pack prefetching
- Add question preloading
- Optimize re-renders with useMemo/useCallback

### 5. Session State Management
**Current Issues**:
- Multiple sources of truth for session state
- Complex state synchronization between components
- Session resumption logic complexity

**Recommendations**:
- Centralize session state in Context API
- Implement state machine pattern for session lifecycle
- Add comprehensive session state persistence

---

## Field Mappings Reference

### Pack Item Structure (Backend)
```json
{
  "id": "uuid-string",
  "stem": "Question text content", 
  "option_a": "First option",
  "option_b": "Second option", 
  "option_c": "Third option",
  "option_d": "Fourth option",
  "answer": "correct_answer_text",
  "subcategory": "category_name",
  "difficulty_band": "Easy|Medium|Hard"
}
```

### Question Object Structure (Frontend)
```javascript
{
  id: packItem.id,
  stem: packItem.stem,
  options: {
    a: packItem.option_a,
    b: packItem.option_b,
    c: packItem.option_c, 
    d: packItem.option_d
  },
  subcategory: packItem.subcategory,
  difficulty_band: packItem.difficulty_band,
  right_answer: packItem.answer
}
```

---

**Document Version**: 1.0  
**Last Updated**: September 24, 2025  
**Status**: Current Implementation Analysis
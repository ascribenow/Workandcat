"""
CAT Preparation Platform Server v2.0 - Complete Rebuild
Comprehensive production-ready server with all advanced features
"""

from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Form, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, asc, func, case, text
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, date
from pathlib import Path
from dotenv import load_dotenv
import os
import uuid
import logging
import json
import asyncio
import random
import shutil
import mimetypes
from docx import Document
import io
from google_drive_utils import GoogleDriveImageFetcher

# Import our modules
from database import (
    get_async_compatible_db, init_database, User, Question, Topic, Attempt, Mastery, Plan, PlanUnit, Session,
    PYQIngestion, PYQPaper, PYQQuestion, QuestionOption, AsyncSession
)
from auth_service import AuthService, UserCreate, UserLogin, TokenResponse, require_auth, require_admin, ADMIN_EMAIL
from llm_enrichment import LLMEnrichmentPipeline
from mcq_generator import MCQGenerator
from study_planner import StudyPlanner
from mastery_tracker import MasteryTracker
from background_jobs import start_background_processing, stop_background_processing

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL")
EMERGENT_LLM_KEY = os.getenv("EMERGENT_LLM_KEY")

# Initialize services
llm_pipeline = LLMEnrichmentPipeline(EMERGENT_LLM_KEY)
mcq_generator = MCQGenerator(EMERGENT_LLM_KEY)
study_planner = StudyPlanner()
mastery_tracker = MasteryTracker()

app = FastAPI(
    title="CAT Preparation Platform v2.0",
    version="2.0.0", 
    description="Complete production-ready CAT preparation platform with advanced AI features"
)

# Image upload configuration
UPLOAD_DIR = Path(__file__).parent / "uploads" / "images"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB

# Mount static files for serving uploaded images
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR.parent)), name="uploads")

api_router = APIRouter(prefix="/api")

# Pydantic Models for API

class QuestionCreateRequest(BaseModel):
    stem: str
    answer: Optional[str] = None  # Now optional since LLM can generate
    solution_approach: Optional[str] = None
    detailed_solution: Optional[str] = None
    hint_category: Optional[str] = None
    hint_subcategory: Optional[str] = None
    type_of_question: Optional[str] = None
    tags: List[str] = []
    source: str = "Admin"
    # Image support fields
    has_image: bool = False
    image_url: Optional[str] = None
    image_alt_text: Optional[str] = None

class SessionStart(BaseModel):
    plan_unit_ids: Optional[List[str]] = None
    target_minutes: Optional[int] = 30

class StudyPlanRequest(BaseModel):
    track: str = "Beginner"  # Default track since no diagnostic
    daily_minutes_weekday: int = 30
    daily_minutes_weekend: int = 60

class AttemptSubmission(BaseModel):
    question_id: str
    user_answer: str
    context: str = "daily"
    time_sec: Optional[int] = None
    hint_used: bool = False

# Core API Routes

@api_router.get("/")
async def root():
    return {
        "message": "CAT Preparation Platform v2.0",
        "admin_email": ADMIN_EMAIL,
        "features": [
            "Advanced LLM Enrichment",
            "Mastery Tracking",
            "90-Day Study Planning",
            "Real-time MCQ Generation",
            "PYQ Processing Pipeline"
        ]
    }

# Authentication Routes (from auth_service)
@api_router.post("/auth/register", response_model=TokenResponse)
async def register_user(user_data: UserCreate, db: AsyncSession = Depends(get_async_compatible_db)):
    auth_service = AuthService()
    return await auth_service.register_user_v2(user_data, db)

@api_router.post("/auth/login", response_model=TokenResponse)
async def login_user(login_data: UserLogin, db: AsyncSession = Depends(get_async_compatible_db)):
    auth_service = AuthService()
    return await auth_service.login_user_v2(login_data, db)

@api_router.get("/auth/me")
async def get_current_user_info(current_user: User = Depends(require_auth)):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_admin": current_user.is_admin,
        "created_at": current_user.created_at.isoformat()
    }

# Import adaptive session engine
from adaptive_session_engine import AdaptiveSessionEngine

# Initialize adaptive engine
adaptive_engine = AdaptiveSessionEngine()

@api_router.post("/sessions/adaptive/start")
async def start_adaptive_session(
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_async_compatible_db)
):
    """Start a new adaptive session with EWMA-based question selection"""
    try:
        # Get adaptively selected questions based on user mastery
        adaptive_questions = await adaptive_engine.get_adaptive_session_questions(
            db, str(current_user.id), target_count=15
        )
        
        if not adaptive_questions:
            raise HTTPException(status_code=404, detail="No suitable questions found for adaptive session")
        
        # Create session record
        session = Session(
            user_id=current_user.id,
            started_at=datetime.utcnow(),
            units=[q["id"] for q in adaptive_questions]  # Store question IDs
        )
        
        db.add(session)
        await db.flush()
        
        # Store session questions in a temporary way (could use Redis in production)
        session_questions = {
            str(session.id): {
                "questions": adaptive_questions,
                "current_index": 0,
                "total_questions": len(adaptive_questions),
                "user_id": str(current_user.id)
            }
        }
        
        # In a real system, this would be stored in Redis or session storage
        # For now, we'll get the first question immediately
        first_question = adaptive_questions[0]
        
        await db.commit()
        
        return {
            "session_id": str(session.id),
            "total_questions": len(adaptive_questions),
            "first_question": {
                "id": first_question["id"],
                "topic_name": first_question["topic_name"],
                "subcategory": first_question["subcategory"],
                "difficulty_band": first_question["difficulty_band"],
                "mastery_category": first_question["mastery_category"],
                "adaptive_score": first_question["adaptive_score"]
            },
            "adaptive_info": {
                "session_type": "adaptive",
                "based_on_mastery": True,
                "selection_algorithm": "EWMA-based"
            },
            "message": "Adaptive session started with mastery-based question selection"
        }
        
    except Exception as e:
        logger.error(f"Error starting adaptive session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/sessions/adaptive/{session_id}/next")
async def get_next_adaptive_question(
    session_id: str,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_async_compatible_db)
):
    """Get next question in adaptive session with full question data"""
    try:
        # Get session
        session_result = await db.execute(
            select(Session).where(Session.id == session_id, Session.user_id == current_user.id)
        )
        session = session_result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get adaptive questions again (in production, this would be cached)
        adaptive_questions = await adaptive_engine.get_adaptive_session_questions(
            db, str(current_user.id), target_count=15
        )
        
        if not adaptive_questions:
            return {"question": None, "session_complete": True}
        
        # For simplicity, return a random question from adaptive set
        # In production, you'd track session progress
        question_data = random.choice(adaptive_questions)
        
        # Get full question details
        question_result = await db.execute(
            select(Question).where(Question.id == question_data["id"])
        )
        question = question_result.scalar_one_or_none()
        
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        
        return {
            "question": {
                "id": str(question.id),
                "stem": question.stem,
                "subcategory": question.subcategory,
                "difficulty_band": question.difficulty_band,
                "type_of_question": question.type_of_question
            },
            "adaptive_info": {
                "mastery_score": question_data["mastery_score"],
                "mastery_category": question_data["mastery_category"],
                "adaptive_score": question_data["adaptive_score"],
                "topic_name": question_data["topic_name"],
                "selection_reason": f"Selected for {question_data['mastery_category']} mastery level"
            },
            "session_complete": False
        }
        
    except Exception as e:
        logger.error(f"Error getting next adaptive question: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Question Answer Submission

@api_router.post("/submit-answer")
async def submit_answer(
    attempt_data: AttemptSubmission,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_async_compatible_db)
):
    """Submit answer for a question"""
    try:
        # Get question to check correct answer
        result = await db.execute(select(Question).where(Question.id == attempt_data.question_id))
        question = result.scalar_one_or_none()
        
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        
        # Check if answer is correct
        is_correct = attempt_data.user_answer.strip().lower() == question.answer.strip().lower()
        
        # Create attempt record
        attempt = Attempt(
            user_id=current_user.id,
            question_id=attempt_data.question_id,
            attempt_no=1,  # Simple submission
            context=attempt_data.context,
            options={},  # Would store the actual options shown
            user_answer=attempt_data.user_answer,
            correct=is_correct,
            time_sec=attempt_data.time_sec or 0,
            hint_used=attempt_data.hint_used
        )
        
        db.add(attempt)
        await db.commit()
        
        # Update mastery tracking
        await mastery_tracker.update_mastery_after_attempt(db, attempt)
        
        # Return feedback
        return {
            "correct": is_correct,
            "message": "Answer submitted successfully",
            "attempt_id": str(attempt.id),
            "explanation": question.solution_approach if not is_correct else None
        }
        
    except Exception as e:
        logger.error(f"Error submitting answer: {e}")
        raise HTTPException(status_code=500, detail="Error submitting answer")

@api_router.post("/admin/init-topics")
async def init_basic_topics(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_compatible_db)
):
    """Initialize basic topics for testing"""
    try:
        # Check if topics already exist
        result = await db.execute(select(Topic).limit(1))
        existing_topic = result.scalar_one_or_none()
        
        if existing_topic:
            return {"message": "Topics already exist", "count": "existing"}
        
        # Create basic topics
        topics = [
            Topic(
                name="Arithmetic",
                slug="arithmetic",
                category="A",
                centrality=0.8
            ),
            Topic(
                name="Speed-Time-Distance",
                slug="speed-time-distance", 
                category="A",
                centrality=0.7
            ),
            Topic(
                name="General",
                slug="general",
                category="A", 
                centrality=0.5
            )
        ]
        
        for topic in topics:
            db.add(topic)
        
        await db.commit()
        
        return {
            "message": "Basic topics created successfully",
            "topics_created": len(topics),
            "topics": [{"name": t.name, "category": t.category} for t in topics]
        }
        
    except Exception as e:
        logger.error(f"Error initializing topics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/questions")
async def create_question(
    question_data: QuestionCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_async_compatible_db)
):
    """Create a new question with LLM enrichment"""
    try:
        # Find the appropriate topic for this question
        subcategory = question_data.hint_subcategory or "Time–Speed–Distance (TSD)"
        topic_result = await db.execute(
            select(Topic).where(Topic.name == subcategory)
        )
        topic = topic_result.scalar_one_or_none()
        
        if not topic:
            # If subcategory topic not found, try to find by parent category
            category = question_data.hint_category or "Arithmetic"
            topic_result = await db.execute(
                select(Topic).where(Topic.name == category, Topic.parent_id.is_(None))
            )
            parent_topic = topic_result.scalar_one_or_none()
            
            if parent_topic:
                topic = parent_topic
            else:
                raise HTTPException(status_code=400, detail=f"Topic not found for category: {category}, subcategory: {subcategory}")
        
        # Create basic question first including image fields
        question = Question(
            topic_id=topic.id,  # Set the topic_id
            subcategory=subcategory,
            type_of_question=question_data.type_of_question or '',
            stem=question_data.stem,
            answer=question_data.answer or "To be generated by LLM",  # Default if not provided
            solution_approach=question_data.solution_approach or "",
            detailed_solution=question_data.detailed_solution or "",
            tags=question_data.tags,
            source=question_data.source,
            # Auto-set has_image based on successful image download
            has_image=bool(question_data.image_url and question_data.image_url.strip()),
            image_url=question_data.image_url,
            image_alt_text=question_data.image_alt_text,
            is_active=False  # Will be activated after enrichment
        )
        
        db.add(question)
        await db.commit()
        
        # Queue enrichment as background task
        background_tasks.add_task(
            enrich_question_background,
            str(question.id),
            question_data.hint_category,
            question_data.hint_subcategory
        )
        
        return {
            "message": "Question created and queued for enrichment",
            "question_id": str(question.id),
            "status": "enrichment_queued"
        }
        
    except Exception as e:
        logger.error(f"Error creating question: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/questions")
async def get_questions(
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    difficulty: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_async_compatible_db)
):
    """Get questions with filtering"""
    try:
        query = select(Question).where(Question.is_active == True)
        
        if category:
            query = query.join(Question.topic).where(Topic.name == category)
        if subcategory:
            query = query.where(Question.subcategory == subcategory)
        if difficulty:
            query = query.where(Question.difficulty_band == difficulty)
        
        query = query.limit(limit).order_by(desc(Question.importance_index))
        
        result = await db.execute(query)
        questions = result.scalars().all()
        
        questions_data = []
        for q in questions:
            questions_data.append({
                "id": str(q.id),
                "stem": q.stem,
                "subcategory": q.subcategory,
                "difficulty_band": q.difficulty_band,
                "difficulty_score": float(q.difficulty_score) if q.difficulty_score else None,
                "importance_index": float(q.importance_index) if q.importance_index else None,
                "learning_impact": float(q.learning_impact) if q.learning_impact else None,
                # Image support fields
                "has_image": q.has_image,
                "image_url": q.image_url,
                "image_alt_text": q.image_alt_text,
                "created_at": q.created_at.isoformat()
            })
        
        return {"questions": questions_data}
        
    except Exception as e:
        logger.error(f"Error getting questions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Study Planning Routes

@api_router.post("/study-plan")
async def create_study_plan(
    plan_request: StudyPlanRequest,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_async_compatible_db)
):
    """Create personalized 90-day study plan"""
    try:
        # Use the provided track or default to Beginner
        track = plan_request.track or "Beginner"
        
        # Create plan
        plan = await study_planner.create_plan(
            db,
            str(current_user.id),
            track,
            plan_request.daily_minutes_weekday,
            plan_request.daily_minutes_weekend
        )
        
        return {
            "message": "Study plan created successfully",
            "plan_id": str(plan.id),
            "track": plan.track,
            "start_date": plan.start_date.isoformat(),
            "daily_minutes_weekday": plan.daily_minutes_weekday,
            "daily_minutes_weekend": plan.daily_minutes_weekend
        }
        
    except Exception as e:
        logger.error(f"Error creating study plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/study-plan/today")
async def get_today_plan(
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_async_compatible_db)
):
    """Get today's study plan units"""
    try:
        today = date.today()
        
        # Get active plan for user
        plan_result = await db.execute(
            select(Plan)
            .where(
                Plan.user_id == current_user.id,
                Plan.status == "active"
            )
            .order_by(desc(Plan.created_at))
            .limit(1)
        )
        plan = plan_result.scalar_one_or_none()
        
        if not plan:
            return {"plan_units": [], "message": "No active study plan found"}
        
        # Get plan units for today
        units_result = await db.execute(
            select(PlanUnit)
            .where(
                PlanUnit.plan_id == plan.id,
                PlanUnit.planned_for == today
            )
            .order_by(PlanUnit.created_at)
        )
        units = units_result.scalars().all()
        
        units_data = []
        for unit in units:
            units_data.append({
                "id": str(unit.id),
                "unit_kind": unit.unit_kind,
                "target_count": unit.target_count,
                "status": unit.status,
                "topic_id": str(unit.topic_id),
                "generated_payload": unit.generated_payload
            })
        
        return {"plan_units": units_data, "date": today.isoformat()}
        
    except Exception as e:
        logger.error(f"Error getting today's plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/sessions/report-broken-image")
async def report_broken_image(
    request: dict,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_async_compatible_db)
):
    """Report a question with broken image to block it from future sessions"""
    try:
        question_id = request.get('question_id')
        if not question_id:
            raise HTTPException(status_code=400, detail="Missing question_id")
        
        # Get the question
        result = await db.execute(select(Question).where(Question.id == question_id))
        question = result.scalar_one_or_none()
        
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        
        # Mark question as inactive due to broken image
        question.is_active = False
        
        # Add tag to indicate image issue
        current_tags = question.tags or []
        if "broken_image" not in current_tags:
            current_tags.append("broken_image")
            current_tags.append("needs_image_fix")
            question.tags = current_tags
        
        await db.commit()
        
        logger.warning(f"Question {question_id} marked as inactive due to broken image by user {current_user.email}")
        
        return {
            "message": "Question blocked from future sessions due to broken image",
            "question_id": question_id,
            "status": "blocked"
        }
        
    except Exception as e:
        logger.error(f"Error reporting broken image: {e}")
        raise HTTPException(status_code=500, detail="Failed to report broken image")

# Session Management Routes

@api_router.post("/session/start")
async def start_session(
    session_data: SessionStart,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_async_compatible_db)
):
    """Start a new study session"""
    try:
        session = Session(
            user_id=current_user.id,
            started_at=datetime.utcnow(),
            units=session_data.plan_unit_ids or []
        )
        
        db.add(session)
        await db.commit()
        
        return {
            "session_id": str(session.id),
            "started_at": session.started_at.isoformat(),
            "message": "Study session started"
        }
        
    except Exception as e:
        logger.error(f"Error starting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/session/{session_id}/next-question")
async def get_next_question(
    session_id: str,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_async_compatible_db)
):
    """Get next question for the session"""
    try:
        # Get session
        session_result = await db.execute(
            select(Session).where(Session.id == session_id, Session.user_id == current_user.id)
        )
        session = session_result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Try to use study planner to get next question
        next_question = await study_planner.get_next_question(db, str(current_user.id), session_id)
        
        # CRITICAL FIX: If study planner fails, use fallback question selection
        if not next_question:
            logger.warning(f"Study planner returned no questions for session {session_id}, using fallback selection")
            
            # Fallback: Get any available active question
            fallback_result = await db.execute(
                select(Question).where(
                    Question.is_active == True
                ).order_by(desc(Question.importance_index)).limit(1)
            )
            fallback_question = fallback_result.scalar_one_or_none()
            
            if fallback_question:
                next_question = {
                    "id": str(fallback_question.id),
                    "stem": fallback_question.stem,
                    "subcategory": fallback_question.subcategory,
                    "difficulty_band": fallback_question.difficulty_band,
                    "importance_index": float(fallback_question.importance_index) if fallback_question.importance_index else 0,
                    "unit_id": None,
                    "unit_kind": "fallback"
                }
                logger.info(f"Using fallback question {fallback_question.id} for session {session_id}")
            else:
                logger.error(f"No questions available at all for session {session_id}")
                return {"question": None, "message": "No more questions for this session"}
        
        # Generate MCQ options
        options = await mcq_generator.generate_options(
            next_question["stem"],
            next_question["subcategory"],
            next_question["difficulty_band"]
        )
        
        next_question["options"] = options
        
        return {"question": next_question}
        
    except Exception as e:
        logger.error(f"Error getting next question: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/session/{session_id}/submit-answer")
async def submit_session_answer(
    session_id: str,
    attempt_data: AttemptSubmission,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_async_compatible_db)
):
    """Submit answer during study session"""
    try:
        # Get question to check answer
        result = await db.execute(select(Question).where(Question.id == attempt_data.question_id))
        question = result.scalar_one_or_none()
        
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        
        # Check if answer is correct
        is_correct = attempt_data.user_answer.strip().lower() == question.answer.strip().lower()
        
        # Determine attempt number for this user-question pair
        existing_attempts = await db.execute(
            select(Attempt).where(
                Attempt.user_id == current_user.id,
                Attempt.question_id == attempt_data.question_id
            ).order_by(desc(Attempt.attempt_no)).limit(1)
        )
        last_attempt = existing_attempts.scalar_one_or_none()
        attempt_no = (last_attempt.attempt_no + 1) if last_attempt else 1
        
        # Create attempt
        attempt = Attempt(
            user_id=current_user.id,
            question_id=attempt_data.question_id,
            attempt_no=attempt_no,
            context="daily",
            options={},
            user_answer=attempt_data.user_answer,
            correct=is_correct,
            time_sec=attempt_data.time_sec,
            hint_used=attempt_data.hint_used
        )
        
        db.add(attempt)
        await db.commit()
        
        # Update mastery asynchronously
        await mastery_tracker.update_mastery_after_attempt(db, attempt)
        
        return {
            "correct": is_correct,
            "attempt_no": attempt_no,
            "solution_approach": question.solution_approach,
            "detailed_solution": question.detailed_solution,
            "video_url": question.video_url,
            "next_retry_in_days": study_planner.get_next_retry_interval(attempt_no, is_correct)
        }
        
    except Exception as e:
        logger.error(f"Error submitting session answer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Dashboard and Analytics Routes

@api_router.get("/dashboard/mastery")
async def get_mastery_dashboard(
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_async_compatible_db)
):
    """Get user's mastery dashboard with category and subcategory progress"""
    try:
        # Get mastery data by topic with parent topic information for category structure
        result = await db.execute(
            select(
                Mastery, 
                Topic.name.label('topic_name'),
                Topic.parent_id,
                func.coalesce(Topic.parent_id.is_(None), True).label('is_parent_topic')
            )
            .join(Topic, Mastery.topic_id == Topic.id)
            .where(Mastery.user_id == current_user.id)
            .order_by(Topic.name)
        )
        
        mastery_records = result.fetchall()
        mastery_data = []
        
        for mastery, topic_name, parent_id, is_parent_topic in mastery_records:
            # Get subcategory data for this topic
            subcategory_result = await db.execute(
                select(
                    Question.subcategory,
                    func.count(Attempt.id).label('attempts_count'),
                    func.avg(
                        case(
                            (Attempt.correct == True, 100),
                            else_=0
                        )
                    ).label('avg_accuracy')
                )
                .join(Attempt, Question.id == Attempt.question_id)
                .where(
                    Question.topic_id == mastery.topic_id,
                    Attempt.user_id == current_user.id
                )
                .group_by(Question.subcategory)
            )
            
            subcategories = []
            for subcat_data in subcategory_result.fetchall():
                if subcat_data.subcategory:  # Only include if subcategory exists
                    subcategories.append({
                        'name': subcat_data.subcategory,
                        'attempts_count': subcat_data.attempts_count or 0,
                        'mastery_percentage': float(subcat_data.avg_accuracy or 0)
                    })
            
            # Determine category with canonical taxonomy format
            category_name = topic_name
            canonical_category = "Unknown"
            
            if parent_id:
                # This is a child topic, get parent name and format as canonical category
                parent_result = await db.execute(
                    select(Topic.name, Topic.category).where(Topic.id == parent_id)
                )
                parent_record = parent_result.first()
                if parent_record:
                    parent_name, parent_category = parent_record
                    category_name = parent_name
                    # Format as canonical taxonomy
                    if parent_category == 'A':
                        canonical_category = "A-Arithmetic"
                    elif parent_category == 'B':
                        canonical_category = "B-Algebra"
                    elif parent_category == 'C':
                        canonical_category = "C-Geometry"
                    elif parent_category == 'D':
                        canonical_category = "D-Number System"
                    elif parent_category == 'E':
                        canonical_category = "E-Modern Math"
                    else:
                        # Fallback based on parent name
                        if 'arithmetic' in parent_name.lower() or 'percentage' in parent_name.lower():
                            canonical_category = "A-Arithmetic"
                        elif 'algebra' in parent_name.lower() or 'equation' in parent_name.lower():
                            canonical_category = "B-Algebra"
                        elif 'geometry' in parent_name.lower() or 'triangle' in parent_name.lower():
                            canonical_category = "C-Geometry"
                        elif 'number' in parent_name.lower() or 'divisib' in parent_name.lower():
                            canonical_category = "D-Number System"
                        elif 'modern' in parent_name.lower() or 'probability' in parent_name.lower():
                            canonical_category = "E-Modern Math"
                        else:
                            canonical_category = f"A-{parent_name}"  # Default to A- prefix
            else:
                # This is a main topic, determine canonical category from topic name
                topic_lower = topic_name.lower()
                if 'arithmetic' in topic_lower or 'percentage' in topic_lower or 'time' in topic_lower:
                    canonical_category = "A-Arithmetic"
                elif 'algebra' in topic_lower or 'equation' in topic_lower or 'progression' in topic_lower:
                    canonical_category = "B-Algebra"
                elif 'geometry' in topic_lower or 'triangle' in topic_lower or 'circle' in topic_lower:
                    canonical_category = "C-Geometry"
                elif 'number' in topic_lower or 'divisib' in topic_lower or 'hcf' in topic_lower:
                    canonical_category = "D-Number System"
                elif 'modern' in topic_lower or 'probability' in topic_lower or 'permutation' in topic_lower:
                    canonical_category = "E-Modern Math"
                else:
                    canonical_category = f"A-{topic_name}"  # Default with topic name
            
            mastery_data.append({
                'topic_name': topic_name,
                'category_name': canonical_category,  # Now formatted as A-Arithmetic, B-Algebra, etc.
                'mastery_percentage': float(mastery.mastery_pct * 100),  # Convert to percentage
                'accuracy_score': float(mastery.accuracy_easy * 100),  # Convert to percentage
                'speed_score': float(mastery.accuracy_med * 100),    # Convert to percentage  
                'stability_score': float(mastery.accuracy_hard * 100), # Convert to percentage
                'questions_attempted': int(mastery.exposure_score),
                'last_attempt_date': mastery.last_updated.isoformat() if mastery.last_updated else None,
                'subcategories': subcategories,
                'is_main_category': parent_id is None  # Flag to identify main categories
            })
        
        # Get detailed progress data
        detailed_progress = await get_detailed_progress_data(db, str(current_user.id))
        
        return {
            'mastery_by_topic': mastery_data,
            'total_topics': len(mastery_data),
            'detailed_progress': detailed_progress
        }
        
    except Exception as e:
        logger.error(f"Error fetching mastery dashboard: {e}")
        return {'mastery_by_topic': [], 'total_topics': 0}

async def get_detailed_progress_data(db: AsyncSession, user_id: str) -> List[Dict]:
    """Get detailed progress breakdown by category/subcategory/difficulty with FIXED category mapping"""
    try:
        # Query to get comprehensive progress data with PROPER category mapping
        progress_query = text("""
            SELECT 
                CASE 
                    WHEN t.category = 'A' THEN 'A-Arithmetic'
                    WHEN t.category = 'B' THEN 'B-Algebra' 
                    WHEN t.category = 'C' THEN 'C-Geometry'
                    WHEN t.category = 'D' THEN 'D-Number System'
                    WHEN t.category = 'E' THEN 'E-Modern Math'
                    ELSE COALESCE(t.category, 'Unknown')
                END as category,
                q.subcategory,
                COALESCE(q.type_of_question, 'General') as type_of_question,
                q.difficulty_band,
                COUNT(DISTINCT q.id) as total_questions,
                COUNT(DISTINCT CASE WHEN a.correct = true THEN a.question_id END) as solved_questions,
                AVG(CASE WHEN a.correct = true THEN 1.0 ELSE 0.0 END) as accuracy_rate,
                COALESCE(AVG(m.mastery_pct * 100), 0) as mastery_percentage
            FROM questions q
            JOIN topics t ON q.topic_id = t.id
            LEFT JOIN attempts a ON q.id = a.question_id AND a.user_id = :user_id
            LEFT JOIN mastery m ON t.id = m.topic_id AND m.user_id = :user_id
            WHERE q.is_active = true
            GROUP BY 
                CASE 
                    WHEN t.category = 'A' THEN 'A-Arithmetic'
                    WHEN t.category = 'B' THEN 'B-Algebra' 
                    WHEN t.category = 'C' THEN 'C-Geometry'
                    WHEN t.category = 'D' THEN 'D-Number System'
                    WHEN t.category = 'E' THEN 'E-Modern Math'
                    ELSE COALESCE(t.category, 'Unknown')
                END,
                q.subcategory, 
                COALESCE(q.type_of_question, 'General'), 
                q.difficulty_band
            ORDER BY category, q.subcategory, type_of_question, q.difficulty_band
        """)
        
        result = await db.execute(progress_query, {"user_id": user_id})
        progress_rows = result.fetchall()
        
        # Group by subcategory and organize by difficulty
        progress_map = {}
        
        for row in progress_rows:
            key = f"{row.category}_{row.subcategory}_{row.type_of_question}"
            
            if key not in progress_map:
                progress_map[key] = {
                    "category": row.category,
                    "subcategory": row.subcategory,
                    "question_type": row.type_of_question,
                    "easy_total": 0,
                    "easy_solved": 0,
                    "medium_total": 0,
                    "medium_solved": 0,
                    "hard_total": 0,
                    "hard_solved": 0,
                    "mastery_percentage": float(row.mastery_percentage or 0)
                }
            
            difficulty = row.difficulty_band or "Medium"
            total_questions = int(row.total_questions or 0)
            solved_questions = int(row.solved_questions or 0)
            
            if difficulty == "Easy":
                progress_map[key]["easy_total"] += total_questions
                progress_map[key]["easy_solved"] += solved_questions
            elif difficulty == "Hard":
                progress_map[key]["hard_total"] += total_questions
                progress_map[key]["hard_solved"] += solved_questions
            else:  # Medium or unknown
                progress_map[key]["medium_total"] += total_questions
                progress_map[key]["medium_solved"] += solved_questions
        
        # Sort by canonical category order
        sorted_progress = sorted(progress_map.values(), key=lambda x: (x["category"], x["subcategory"], x["question_type"]))
        
        return sorted_progress
        
    except Exception as e:
        logger.error(f"Error getting detailed progress data: {e}")
        return []


@api_router.get("/dashboard/progress")
async def get_progress_dashboard(
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_async_compatible_db)
):
    """Get progress dashboard data"""
    try:
        # Get recent sessions
        sessions_result = await db.execute(
            select(Session)
            .where(Session.user_id == current_user.id)
            .order_by(desc(Session.started_at))
            .limit(30)
        )
        sessions = sessions_result.scalars().all()
        
        # Calculate stats
        total_sessions = len(sessions)
        total_minutes = sum([s.duration_sec // 60 for s in sessions if s.duration_sec])
        
        # Get streak (consecutive days with sessions)
        streak = await calculate_study_streak(db, str(current_user.id))
        
        return {
            "total_sessions": total_sessions,
            "total_minutes": total_minutes,
            "current_streak": streak,
            "sessions_this_week": len([s for s in sessions if s.started_at > datetime.utcnow() - timedelta(days=7)])
        }
        
    except Exception as e:
        logger.error(f"Error getting progress dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Admin Routes

@api_router.get("/admin/export-questions-csv")
async def export_questions_csv(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_compatible_db)
):
    """Export all questions as CSV with all columns"""
    try:
        import csv
        import io
        from datetime import datetime
        
        # Get all questions with topic information
        result = await db.execute(
            select(Question, Topic.name.label('topic_name'))
            .join(Topic, Question.topic_id == Topic.id)
            .order_by(Question.created_at.desc())
        )
        
        questions_data = result.fetchall()
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header with all actual columns from the database
        header = [
            'id',
            'stem',
            'answer',
            'solution_approach',
            'detailed_solution', 
            'category',
            'subcategory',
            'difficulty_score',
            'difficulty_band',
            'frequency_band',
            'frequency_notes',
            'learning_impact',
            'learning_impact_band',
            'importance_index',
            'importance_band',
            'video_url',
            'tags',
            'source',
            'version',
            'is_active',
            'created_at'
        ]
        writer.writerow(header)
        
        # Write question data
        for question, topic_name in questions_data:
            row = [
                str(question.id),
                question.stem or '',
                question.answer or '',
                question.solution_approach or '',
                question.detailed_solution or '',
                topic_name or '',
                question.subcategory or '',
                float(question.difficulty_score) if question.difficulty_score else '',
                question.difficulty_band or '',
                question.frequency_band or '',
                question.frequency_notes or '',
                float(question.learning_impact) if question.learning_impact else '',
                question.learning_impact_band or '',
                float(question.importance_index) if question.importance_index else '',
                question.importance_band or '',
                question.video_url or '',
                ','.join(question.tags) if question.tags else '',
                question.source or '',
                question.version or 1,
                str(question.is_active),
                question.created_at.isoformat() if question.created_at else ''
            ]
            writer.writerow(row)
        
        # Prepare response
        output.seek(0)
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8')),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=cat_questions_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            }
        )
        
    except Exception as e:
        logger.error(f"Questions export error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to export questions: {str(e)}")

@api_router.post("/admin/upload-questions-csv")
async def upload_questions_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_compatible_db)
):
    """Upload questions from simplified CSV file with Google Drive image support"""
    try:
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be a CSV")
            
        # Read CSV content
        import csv
        import io
        content = await file.read()
        csv_data = content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_data))
        
        # Convert to list for processing
        csv_rows = list(csv_reader)
        
        # Validate CSV format - must have 'stem' column
        if not csv_rows:
            raise HTTPException(status_code=400, detail="CSV file is empty")
        
        first_row = csv_rows[0]
        if 'stem' not in first_row:
            raise HTTPException(status_code=400, detail="CSV must contain 'stem' column with question text")
        
        logger.info(f"Processing {len(csv_rows)} rows from simplified CSV with LLM auto-generation")
        
        # Process images from Google Drive URLs
        processed_rows = GoogleDriveImageFetcher.process_csv_image_urls(csv_rows, UPLOAD_DIR)
        
        questions_created = 0
        images_processed = 0
        
        for i, row in enumerate(processed_rows):
            # Extract data from simplified CSV row
            stem = row.get('stem', '').strip()
            
            # Image fields (processed by Google Drive utils)
            has_image = row.get('has_image', False)
            image_url = row.get('image_url', '').strip() if row.get('image_url') else None
            image_alt_text = row.get('image_alt_text', '').strip() if row.get('image_alt_text') else None
            
            # Auto-set has_image based on successful image download
            if image_url and image_url.startswith('/uploads/images/'):
                has_image = True  # Image was successfully downloaded and stored locally
            else:
                has_image = False  # No image or download failed
            
            if not stem:
                logger.warning(f"Row {i+1}: Skipping - missing question stem")
                continue  # Skip rows without stem
            
            # Find a default topic (LLM will classify properly during enrichment)
            topic_result = await db.execute(
                select(Topic).where(Topic.name == "General")
            )
            topic = topic_result.scalar_one_or_none()
            
            if not topic:
                # Create a default topic
                topic = Topic(
                    name="General",
                    description="Default topic for CSV uploads - will be reclassified by LLM"
                )
                db.add(topic)
                await db.flush()
            
            # Create question with minimal data - LLM will enrich everything
            question = Question(
                topic_id=topic.id,
                stem=stem,
                # LLM will generate these fields
                answer="To be generated by LLM",
                solution_approach="To be generated by LLM", 
                detailed_solution="To be generated by LLM",
                subcategory="To be classified by LLM",
                type_of_question="To be classified by LLM",
                tags=["csv_upload", "llm_pending"],
                source="CSV Upload - Simplified Format",
                # Image support fields
                has_image=has_image,
                image_url=image_url,
                image_alt_text=image_alt_text,
                # Set defaults for LLM to populate
                difficulty_band="Unrated",
                difficulty_score=0.5,  # Default medium difficulty
                learning_impact=0.5,   # Default medium impact
                importance_index=0.5,  # Default medium importance
                is_active=False  # Will be activated after LLM enrichment
            )
            
            db.add(question)
            questions_created += 1
            
            if has_image and image_url:
                images_processed += 1
                logger.info(f"Question {questions_created}: Created with image from Google Drive")
            
            # Queue for LLM enrichment (will happen in background)
            logger.info(f"Question {questions_created} queued for LLM auto-generation and classification")
            
        await db.commit()
        
        # Start background enrichment for all created questions
        logger.info("Starting background LLM enrichment for all uploaded questions...")
        
        # Get all questions created in this batch for enrichment
        recent_questions = await db.execute(
            select(Question).where(
                Question.source == "CSV Upload - Simplified Format",
                Question.is_active == False  # Only unprocessed questions
            ).order_by(desc(Question.created_at)).limit(len(processed_rows))
        )
        
        # Queue background enrichment tasks
        for question in recent_questions.scalars():
            # Use asyncio to run background enrichment (in production, use Celery or similar)
            asyncio.create_task(enrich_question_background(str(question.id)))
        
        logger.info(f"Simplified CSV upload completed: {questions_created} questions created, {images_processed} with images")
        
        return {
            "message": f"Successfully uploaded {questions_created} questions from simplified CSV",
            "questions_created": questions_created,
            "images_processed": images_processed,
            "csv_rows_processed": len(processed_rows),
            "llm_enrichment_status": "Questions queued for automatic LLM processing (answer generation, classification, difficulty analysis)",
            "note": "Questions will be automatically enriched with answers, categories, solutions, and difficulty ratings by the LLM system"
        }
        
    except Exception as e:
        logger.error(f"Simplified CSV upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload CSV: {str(e)}")

# Image Upload Endpoints

@api_router.post("/admin/image/upload")
async def upload_question_image(
    file: UploadFile = File(...),
    alt_text: Optional[str] = Form(None),
    current_user: User = Depends(require_admin),
):
    """Upload an image for a question"""
    try:
        # Validate file type
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
            )
        
        # Validate file size
        content = await file.read()
        if len(content) > MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {MAX_IMAGE_SIZE // (1024*1024)}MB"
            )
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        filename = f"{file_id}{file_extension}"
        file_path = UPLOAD_DIR / filename
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Generate URL for accessing the image
        image_url = f"/uploads/images/{filename}"
        
        logger.info(f"Image uploaded successfully: {filename} by {current_user.email}")
        
        return {
            "message": "Image uploaded successfully",
            "image_url": image_url,
            "filename": filename,
            "alt_text": alt_text,
            "file_size": len(content)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload image")

@api_router.delete("/admin/image/{filename}")
async def delete_question_image(
    filename: str,
    current_user: User = Depends(require_admin),
):
    """Delete an uploaded image"""
    try:
        file_path = UPLOAD_DIR / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Image not found")
        
        # Remove file
        file_path.unlink()
        
        logger.info(f"Image deleted: {filename} by {current_user.email}")
        
        return {"message": "Image deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting image: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete image")

# PYQ Upload Endpoints

@api_router.post("/admin/pyq/upload")
async def upload_pyq_document(
    file: UploadFile = File(...),
    year: int = Form(...),
    slot: Optional[str] = Form(None),
    source_url: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_compatible_db)
):
    """Upload PYQ document (Word or PDF) for processing"""
    try:
        # Support both PDF and Word documents as per specification
        allowed_extensions = ('.docx', '.doc', '.pdf')
        if not file.filename.endswith(allowed_extensions):
            raise HTTPException(
                status_code=400, 
                detail="Only Word documents (.docx, .doc) and PDF files (.pdf) are allowed"
            )
        
        # Store file
        file_content = await file.read()
        file_extension = file.filename.split('.')[-1]
        storage_key = f"pyq_{year}_{slot or 'unknown'}_{uuid.uuid4()}.{file_extension}"
        
        # Create ingestion record
        ingestion = PYQIngestion(
            upload_filename=file.filename,
            storage_key=storage_key,
            year=year,
            slot=slot,
            source_url=source_url,
            pages_count=None,
            ocr_required=False,
            ocr_status="not_needed",
            parse_status="queued"
        )
        
        db.add(ingestion)
        await db.commit()
        
        # Queue processing as background task
        if background_tasks:
            background_tasks.add_task(
                process_pyq_document,
                str(ingestion.id),
                file_content
            )
        
        return {
            "message": "PYQ document uploaded and queued for processing",
            "ingestion_id": str(ingestion.id),
            "status": "processing_queued"
        }
        
    except Exception as e:
        logger.error(f"Error uploading PYQ document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Admin Test Endpoints for Conceptual Frequency Analysis

@api_router.post("/admin/test/immediate-enrichment")
async def test_immediate_enrichment(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_compatible_db)
):
    """Test immediate LLM enrichment (not background task)"""
    try:
        # Get an inactive question
        result = await db.execute(
            select(Question).where(Question.is_active == False).limit(1)
        )
        test_question = result.scalar_one_or_none()
        
        if not test_question:
            # Create a test question
            from database import Topic
            topic_result = await db.execute(select(Topic).limit(1))
            topic = topic_result.scalar_one()
            
            test_question = Question(
                topic_id=topic.id,
                subcategory="Speed-Time-Distance",
                type_of_question="Average Speed",
                stem="A car travels 200 km in 4 hours. What is its average speed in km/h?",
                answer="To be generated by LLM",
                solution_approach="",
                detailed_solution="",
                is_active=False,
                source="Test"
            )
            db.add(test_question)
            await db.commit()
            await db.refresh(test_question)
        
        logger.info(f"🧪 Testing immediate enrichment for question: {test_question.id}")
        
        # Test immediate enrichment using simple LLM calls
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        # Step 1: Generate answer
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"test_{test_question.id}",
            system_message="You are a math expert. Given a question, provide only the numerical answer."
        ).with_model("claude", "claude-3-5-sonnet-20241022")
        
        user_message = UserMessage(text=f"Question: {test_question.stem}")
        answer_response = await chat.send_message(user_message)
        answer = answer_response.strip()
        
        # Step 2: Generate solution
        solution_chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"solution_{test_question.id}",
            system_message="You are a math tutor. Explain how to solve the given problem step by step."
        ).with_model("claude", "claude-3-5-sonnet-20241022")
        
        solution_message = UserMessage(text=f"Question: {test_question.stem}\nAnswer: {answer}\nProvide a step-by-step solution.")
        solution_response = await solution_chat.send_message(solution_message)
        
        # Update the question
        test_question.answer = answer[:100]  # Limit length
        test_question.solution_approach = "Speed = Distance / Time"
        test_question.detailed_solution = solution_response[:500]  # Limit length
        test_question.subcategory = "Speed-Time-Distance"
        test_question.type_of_question = "Average Speed Calculation"
        test_question.difficulty_score = 0.3  # Easy
        test_question.difficulty_band = "Easy"
        test_question.learning_impact = 60.0
        test_question.importance_index = 70.0
        test_question.frequency_band = "High"
        test_question.tags = ["test_enriched", "immediate_processing"]
        test_question.source = "LLM Test Generated"
        test_question.is_active = True
        
        await db.commit()
        
        return {
            "message": "Immediate enrichment completed successfully",
            "question_id": str(test_question.id),
            "enriched_data": {
                "answer": test_question.answer,
                "solution_approach": test_question.solution_approach,
                "detailed_solution": test_question.detailed_solution,
                "is_active": test_question.is_active
            }
        }
        
    except Exception as e:
        logger.error(f"Error in immediate enrichment test: {e}")
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")

@api_router.post("/admin/test/conceptual-frequency")
async def test_conceptual_frequency_analysis(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_compatible_db)
):
    """Test endpoint to manually trigger conceptual frequency analysis"""
    try:
        from conceptual_frequency_analyzer import ConceptualFrequencyAnalyzer
        
        # Initialize analyzer
        frequency_analyzer = ConceptualFrequencyAnalyzer(llm_pipeline)
        
        # Get a sample question
        result = await db.execute(
            select(Question).where(Question.is_active == True).limit(1)
        )
        test_question = result.scalar_one_or_none()
        
        if not test_question:
            raise HTTPException(status_code=404, detail="No active questions found for testing")
        
        logger.info(f"🧪 Testing conceptual frequency for question: {test_question.stem[:100]}...")
        
        # Run conceptual frequency analysis
        freq_result = await frequency_analyzer.calculate_conceptual_frequency(
            db, test_question, years_window=10
        )
        
        return {
            "message": "Conceptual frequency analysis test completed",
            "question_id": str(test_question.id),
            "question_stem": test_question.stem[:100] + "...",
            "analysis_results": freq_result
        }
        
    except Exception as e:
        logger.error(f"Error in conceptual frequency test: {e}")
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")

@api_router.post("/admin/test/time-weighted-frequency")
async def test_time_weighted_frequency_analysis(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_compatible_db)
):
    """Test time-weighted frequency analysis (20-year data, 10-year relevance)"""
    try:
        from time_weighted_frequency_analyzer import TimeWeightedFrequencyAnalyzer, CAT_ANALYSIS_CONFIG
        
        # Initialize time-weighted analyzer
        time_analyzer = TimeWeightedFrequencyAnalyzer(CAT_ANALYSIS_CONFIG)
        
        # Get sample temporal data for analysis
        current_year = datetime.now().year
        
        # Create sample yearly occurrence data (simulating 20 years of PYQ data)
        sample_yearly_occurrences = {
            2024: 8, 2023: 6, 2022: 7, 2021: 5, 2020: 9,  # Last 5 years (high relevance)
            2019: 4, 2018: 6, 2017: 8, 2016: 3, 2015: 5,  # Next 5 years (medium relevance) 
            2014: 2, 2013: 4, 2012: 3, 2011: 2, 2010: 1,  # Older data (lower relevance)
            2009: 2, 2008: 1, 2007: 1, 2006: 0, 2005: 1   # Very old data (minimal relevance)
        }
        
        sample_total_pyq_per_year = {year: 100 for year in sample_yearly_occurrences.keys()}  # Assume 100 questions per year
        
        # Run time-weighted analysis
        temporal_pattern = time_analyzer.create_temporal_pattern(
            concept_id="Time-Speed-Distance_Basic_Speed_Calculation",
            yearly_occurrences=sample_yearly_occurrences,
            total_pyq_count_per_year=sample_total_pyq_per_year
        )
        
        # Generate insights
        insights = time_analyzer.generate_frequency_insights(temporal_pattern)
        
        # Calculate different frequency metrics
        frequency_metrics = time_analyzer.calculate_time_weighted_frequency(
            sample_yearly_occurrences, sample_total_pyq_per_year
        )
        
        return {
            "message": "Time-weighted frequency analysis test completed",
            "config": {
                "total_data_years": CAT_ANALYSIS_CONFIG.total_data_years,
                "relevance_window_years": CAT_ANALYSIS_CONFIG.relevance_window_years,
                "decay_rate": CAT_ANALYSIS_CONFIG.decay_rate
            },
            "sample_data": {
                "yearly_occurrences": sample_yearly_occurrences,
                "data_span": f"{min(sample_yearly_occurrences.keys())}-{max(sample_yearly_occurrences.keys())}"
            },
            "temporal_pattern": {
                "concept_id": temporal_pattern.concept_id,
                "total_occurrences": temporal_pattern.total_occurrences,
                "relevance_window_occurrences": temporal_pattern.relevance_window_occurrences,
                "weighted_frequency_score": temporal_pattern.weighted_frequency_score,
                "trend_direction": temporal_pattern.trend_direction,
                "trend_strength": temporal_pattern.trend_strength,
                "recency_score": temporal_pattern.recency_score
            },
            "frequency_metrics": frequency_metrics,
            "insights": insights,
            "explanation": {
                "approach": "Uses 20 years of PYQ data but emphasizes last 10 years for relevance scoring",
                "weighting": "Recent years get exponentially higher weights in frequency calculation",
                "trend_analysis": "Detects if topic frequency is increasing, stable, or decreasing over time"
            }
        }
        
    except Exception as e:
        logger.error(f"Error in time-weighted frequency test: {e}")
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")

@api_router.post("/admin/run-enhanced-nightly") 
async def run_enhanced_nightly_processing(
    current_user: User = Depends(require_admin)
):
    """Manually trigger enhanced nightly processing with conceptual frequency analysis"""
    try:
        from enhanced_nightly_engine import EnhancedNightlyEngine
        
        # Initialize enhanced nightly engine with LLM support
        enhanced_engine = EnhancedNightlyEngine(llm_pipeline=llm_pipeline)
        
        logger.info("🌙 Starting manual enhanced nightly processing...")
        
        # Run the enhanced nightly processing
        result = await enhanced_engine.run_nightly_processing()
        
        return {
            "message": "Enhanced nightly processing completed",
            "success": True,
            "processing_results": result
        }
        
    except Exception as e:
        logger.error(f"Error in enhanced nightly processing: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@api_router.get("/admin/stats")
async def get_admin_stats(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_async_compatible_db)
):
    """Get admin dashboard statistics"""
    try:
        # Count various entities
        users_count = await db.scalar(select(func.count(User.id)))
        questions_count = await db.scalar(select(func.count(Question.id)))
        attempts_count = await db.scalar(select(func.count(Attempt.id)))
        active_plans_count = await db.scalar(select(func.count(Plan.id)).where(Plan.status == "active"))
        
        return {
            "total_users": users_count,
            "total_questions": questions_count,
            "total_attempts": attempts_count,
            "active_study_plans": active_plans_count,
            "admin_email": ADMIN_EMAIL
        }
        
    except Exception as e:
        logger.error(f"Error getting admin stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Background Tasks

async def enrich_question_background(question_id: str, hint_category: str = None, hint_subcategory: str = None):
    """Background task to enrich a question using complete LLM auto-generation"""
    try:
        async for db in get_async_compatible_db():
            # Get question
            result = await db.execute(select(Question).where(Question.id == question_id))
            question = result.scalar_one_or_none()
            
            if not question:
                logger.error(f"Question {question_id} not found for enrichment")
                return
            
            logger.info(f"Starting complete LLM auto-generation for question {question_id}")
            
            # Use the global LLM enrichment pipeline instance (has API key)
            enrichment_data = await llm_pipeline.enrich_question_completely(
                question.stem,
                image_url=question.image_url,
                hint_category=hint_category,
                hint_subcategory=hint_subcategory
            )
            
            # Update question with all generated data
            question.answer = enrichment_data["answer"]
            question.solution_approach = enrichment_data["solution_approach"] 
            question.detailed_solution = enrichment_data["detailed_solution"]
            question.subcategory = enrichment_data["subcategory"]
            question.type_of_question = enrichment_data["type_of_question"]
            question.difficulty_score = enrichment_data["difficulty_score"]
            question.difficulty_band = enrichment_data["difficulty_band"]
            question.learning_impact = enrichment_data["learning_impact"]
            question.importance_index = enrichment_data["importance_index"]
            question.frequency_band = enrichment_data["frequency_band"]
            question.tags = enrichment_data.get("tags", [])
            question.source = enrichment_data.get("source", "LLM Generated")
            
            # Find and update topic based on LLM classification
            topic_result = await db.execute(
                select(Topic).where(Topic.name == enrichment_data["subcategory"])
            )
            topic = topic_result.scalar_one_or_none()
            
            if not topic:
                # Try to find by category
                category_result = await db.execute(
                    select(Topic).where(Topic.category == enrichment_data.get("category", "A"))
                )
                topic = category_result.scalar_one_or_none()
                
                if not topic:
                    # Use a default topic if none found
                    default_result = await db.execute(
                        select(Topic).where(Topic.name == "Arithmetic")
                    )
                    topic = default_result.scalar_one_or_none()
            
            if topic:
                question.topic_id = topic.id
            
            question.is_active = True  # Activate after complete enrichment
            
            await db.commit()
            logger.info(f"✅ Question {question_id} enriched successfully with LLM auto-generation")
            break  # Exit the async for loop
            
    except Exception as e:
        logger.error(f"❌ Error in background enrichment for question {question_id}: {e}")
        # Mark question as failed enrichment but still make it active with placeholder content
        try:
            async for db in get_async_compatible_db():
                result = await db.execute(select(Question).where(Question.id == question_id))
                question = result.scalar_one_or_none()
                if question:
                    question.is_active = True  # Make active even if enrichment failed
                    question.tags = question.tags + ["enrichment_failed"] if question.tags else ["enrichment_failed"]
                    await db.commit()
                    logger.warning(f"⚠️ Question {question_id} activated with enrichment failure flag")
                break
        except Exception as commit_error:
            logger.error(f"Failed to mark question as enrichment failed: {commit_error}")

async def process_pyq_document(ingestion_id: str, file_content: bytes):
    """Background task to process PYQ document"""
    try:
        async for db in get_async_compatible_db():
            # Get ingestion record
            result = await db.execute(select(PYQIngestion).where(PYQIngestion.id == ingestion_id))
            ingestion = result.scalar_one_or_none()
            
            if not ingestion:
                logger.error(f"Ingestion {ingestion_id} not found")
                return
            
            # Update status
            ingestion.parse_status = "running"
            await db.commit()
            
            # Process Word document
            doc = Document(io.BytesIO(file_content))
            
            # Extract text
            full_text = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    full_text.append(paragraph.text.strip())
            
            document_text = "\n".join(full_text)
            
            # Use LLM to extract questions (simplified version)
            # In production, this would be more sophisticated
            
            # Create PYQ paper record
            pyq_paper = PYQPaper(
                year=ingestion.year,
                slot=ingestion.slot,
                source_url=ingestion.source_url,
                ingestion_id=ingestion.id
            )
            
            db.add(pyq_paper)
            await db.flush()
            
            # Update ingestion status
            ingestion.parse_status = "done"
            ingestion.completed_at = datetime.utcnow()
            ingestion.parse_log = f"Processed document with {len(full_text)} paragraphs"
            
            await db.commit()
            logger.info(f"PYQ document {ingestion_id} processed successfully")
            break  # Exit the async for loop
            
    except Exception as e:
        logger.error(f"Error processing PYQ document: {e}")
        # Update ingestion status to failed
        try:
            async for db in get_async_compatible_db():
                result = await db.execute(select(PYQIngestion).where(PYQIngestion.id == ingestion_id))
                ingestion = result.scalar_one_or_none()
                if ingestion:
                    ingestion.parse_status = "failed"
                    ingestion.parse_log = str(e)
                    await db.commit()
                break  # Exit the async for loop
        except:
            pass

# Utility Functions

async def calculate_study_streak(db: AsyncSession, user_id: str) -> int:
    """Calculate current study streak for a user"""
    try:
        # Get sessions ordered by date
        sessions_result = await db.execute(
            select(Session)
            .where(Session.user_id == user_id)
            .order_by(desc(Session.started_at))
        )
        sessions = sessions_result.scalars().all()
        
        if not sessions:
            return 0
        
        # Calculate consecutive days
        streak = 0
        current_date = datetime.utcnow().date()
        
        session_dates = set()
        for session in sessions:
            session_dates.add(session.started_at.date())
        
        # Count consecutive days backwards from today
        while current_date in session_dates:
            streak += 1
            current_date -= timedelta(days=1)
        
        return streak
        
    except Exception as e:
        logger.error(f"Error calculating streak: {e}")
        return 0

# Include router
app.include_router(api_router)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 CAT Preparation Platform v2.0 Starting...")
    
    # Initialize database
    init_database()
    logger.info("📊 SQLite Database initialized")
    
    # Note: Topic creation can be done manually via admin interface
    logger.info("✅ Startup complete - SQLite migration successful")
    
    # Create diagnostic set if needed - DISABLED
    # async for db in get_async_compatible_db():
    #     await diagnostic_system.create_diagnostic_set(db)
    #     break
    # logger.info("🎯 Diagnostic system initialized")
    
    # Start background job processing
    if EMERGENT_LLM_KEY:
        start_background_processing(EMERGENT_LLM_KEY)
        logger.info("⏰ Background job processing started")
    else:
        logger.warning("⚠️ Background jobs not started - missing EMERGENT_LLM_KEY")
    
    logger.info(f"📧 Admin Email: {ADMIN_EMAIL}")
    logger.info("✅ CAT Preparation Platform v2.0 Ready!")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 CAT Preparation Platform v2.0 Shutting down...")
    
    # Stop background job processing
    stop_background_processing()
    logger.info("⏰ Background job processing stopped")
    
    logger.info("✅ CAT Preparation Platform v2.0 Shutdown complete!")

async def create_initial_topics():
    """Create initial topic structure from canonical taxonomy"""
    try:
        async for db in get_async_compatible_db():
            # Check if topics already exist
            existing_topics = await db.execute(select(Topic).limit(1))
            if existing_topics.scalar_one_or_none():
                break  # Topics already created
            
            from llm_enrichment import CANONICAL_TAXONOMY
            
            # Create main categories and subcategories
            for category, subcategories in CANONICAL_TAXONOMY.items():
                # Create main category
                main_topic = Topic(
                    name=category,
                    slug=category.lower().replace(" ", "_").replace("&", "and"),
                    centrality=0.8  # Main categories are central
                )
                db.add(main_topic)
                await db.flush()  # Get ID
                
                # Create subcategories
                for subcategory, details in subcategories.items():
                    sub_topic = Topic(
                        name=subcategory,
                        parent_id=main_topic.id,
                        slug=subcategory.lower().replace(" ", "_").replace("–", "_").replace("(", "").replace(")", ""),
                        centrality=0.6  # Subcategories are moderately central
                    )
                    db.add(sub_topic)
            
            await db.commit()
            logger.info("Created initial topics from canonical taxonomy")
            break
            
    except Exception as e:
        logger.error(f"Error creating initial topics: {e}")
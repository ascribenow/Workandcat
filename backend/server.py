"""
CAT Preparation Platform Server v2.0 - Complete Rebuild
Comprehensive production-ready server with all advanced features
"""

from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Form, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, asc, func, case
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
from docx import Document
import io

# Import our modules
from database import (
    get_database, init_database, User, Question, Topic, Attempt, Mastery, Plan, PlanUnit, Session,
    PYQIngestion, PYQPaper, PYQQuestion, QuestionOption, Diagnostic
)
from auth_service import AuthService, UserCreate, UserLogin, TokenResponse, require_auth, require_admin, ADMIN_EMAIL
from llm_enrichment import LLMEnrichmentPipeline
from mcq_generator import MCQGenerator
from study_planner import StudyPlanner
from mastery_tracker import MasteryTracker
from background_jobs import start_background_processing, stop_background_processing
from diagnostic_system import DiagnosticSystem

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

api_router = APIRouter(prefix="/api")

# Pydantic Models for API

class QuestionCreateRequest(BaseModel):
    stem: str
    answer: str
    solution_approach: Optional[str] = None
    detailed_solution: Optional[str] = None
    hint_category: Optional[str] = None
    hint_subcategory: Optional[str] = None
    type_of_question: Optional[str] = None  # New canonical taxonomy field
    tags: List[str] = []
    source: str = "Admin"

class SessionStart(BaseModel):
    plan_unit_ids: Optional[List[str]] = None
    target_minutes: Optional[int] = 30

class StudyPlanRequest(BaseModel):
    track: str = "Beginner"  # Default track since no diagnostic
    daily_minutes_weekday: int = 30
    daily_minutes_weekend: int = 60

# Core API Routes

@api_router.get("/")
async def root():
    return {
        "message": "CAT Preparation Platform v2.0",
        "admin_email": ADMIN_EMAIL,
        "features": [
            "25-Question Diagnostic System",
            "Advanced LLM Enrichment",
            "Mastery Tracking",
            "90-Day Study Planning",
            "Real-time MCQ Generation",
            "PYQ Processing Pipeline"
        ]
    }

# Authentication Routes (from auth_service)
@api_router.post("/auth/register", response_model=TokenResponse)
async def register_user(user_data: UserCreate, db: AsyncSession = Depends(get_database)):
    auth_service = AuthService()
    return await auth_service.register_user_v2(user_data, db)

@api_router.post("/auth/login", response_model=TokenResponse)
async def login_user(login_data: UserLogin, db: AsyncSession = Depends(get_database)):
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

# Diagnostic System Routes

@api_router.post("/diagnostic/submit-answer")
async def submit_diagnostic_answer(
    attempt_data: AttemptSubmission,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_database)
):
    """Submit answer for a diagnostic question"""
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
            attempt_no=1,  # Diagnostic attempts are always attempt 1
            context=attempt_data.context,
            options={},  # Would store the actual options shown
            user_answer=attempt_data.user_answer,
            correct=is_correct,
            time_sec=attempt_data.time_sec,
            hint_used=attempt_data.hint_used
        )
        
        db.add(attempt)
        await db.commit()
        
        # Return feedback (but not solutions during diagnostic)
        return {
            "correct": is_correct,
            "message": "Answer submitted successfully",
            "attempt_id": str(attempt.id)
        }
        
    except Exception as e:
        logger.error(f"Error submitting diagnostic answer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/questions")
async def create_question(
    question_data: QuestionCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_database)
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
        
        # Create basic question first including type_of_question
        question = Question(
            topic_id=topic.id,  # Set the topic_id
            subcategory=subcategory,
            type_of_question=question_data.type_of_question or '',  # New canonical taxonomy field
            stem=question_data.stem,
            answer=question_data.answer,
            solution_approach=question_data.solution_approach or "",
            detailed_solution=question_data.detailed_solution or "",
            tags=question_data.tags,
            source=question_data.source,
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
    db: AsyncSession = Depends(get_database)
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
    db: AsyncSession = Depends(get_database)
):
    """Create personalized 90-day study plan"""
    try:
        # Get user's diagnostic result to determine track if not provided
        track = plan_request.track
        if not track:
            diagnostic_result = await db.execute(
                select(Diagnostic)
                .where(
                    Diagnostic.user_id == current_user.id,
                    Diagnostic.completed_at.isnot(None)
                )
                .order_by(desc(Diagnostic.completed_at))
                .limit(1)
            )
            diagnostic = diagnostic_result.scalar_one_or_none()
            
            if diagnostic and diagnostic.result:
                track = diagnostic.result.get("track_recommendation", "Beginner")
            else:
                track = "Beginner"  # Default if no diagnostic
        
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
    db: AsyncSession = Depends(get_database)
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

# Session Management Routes

@api_router.post("/session/start")
async def start_session(
    session_data: SessionStart,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_database)
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
    db: AsyncSession = Depends(get_database)
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
        
        # Use study planner to get next question
        next_question = await study_planner.get_next_question(db, str(current_user.id), session_id)
        
        if not next_question:
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
    db: AsyncSession = Depends(get_database)
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
    db: AsyncSession = Depends(get_database)
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
            
            # Determine if this is a main category or subcategory based on parent_id
            category_name = topic_name
            if parent_id:
                # This is a child topic, get parent name as category
                parent_result = await db.execute(
                    select(Topic.name).where(Topic.id == parent_id)
                )
                parent_name = parent_result.scalar_one_or_none()
                if parent_name:
                    category_name = parent_name
            
            mastery_data.append({
                'topic_name': topic_name,
                'category_name': category_name,  # Add category information
                'mastery_percentage': float(mastery.mastery_pct * 100),  # Convert to percentage
                'accuracy_score': float(mastery.accuracy_easy * 100),  # Convert to percentage
                'speed_score': float(mastery.accuracy_med * 100),    # Convert to percentage  
                'stability_score': float(mastery.accuracy_hard * 100), # Convert to percentage
                'questions_attempted': int(mastery.exposure_score),
                'last_attempt_date': mastery.last_updated.isoformat() if mastery.last_updated else None,
                'subcategories': subcategories,
                'is_main_category': parent_id is None  # Flag to identify main categories
            })
        
        return {
            'mastery_by_topic': mastery_data,
            'total_topics': len(mastery_data)
        }
        
    except Exception as e:
        logger.error(f"Error fetching mastery dashboard: {e}")
        return {'mastery_by_topic': [], 'total_topics': 0}

@api_router.get("/dashboard/progress")
async def get_progress_dashboard(
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_database)
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
    db: AsyncSession = Depends(get_database)
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
    db: AsyncSession = Depends(get_database)
):
    """Upload questions from CSV file"""
    try:
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be a CSV")
            
        # Read CSV content
        import csv
        import io
        content = await file.read()
        csv_data = content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_data))
        
        questions_created = 0
        for row in csv_reader:
            # Extract data from CSV row
            stem = row.get('stem', '').strip()
            answer = row.get('answer', '').strip()
            category = row.get('category', '').strip()
            subcategory = row.get('subcategory', '').strip()
            source = row.get('source', '').strip()
            
            if not stem or not answer:
                continue  # Skip rows without stem or answer
                
            # Find appropriate topic
            topic_result = await db.execute(
                select(Topic).where(Topic.name == subcategory)
            )
            topic = topic_result.scalar_one_or_none()
            
            if not topic:
                # Try to find by parent category
                topic_result = await db.execute(
                    select(Topic).where(Topic.name == category, Topic.parent_id.is_(None))
                )
                topic = topic_result.scalar_one_or_none()
                
            if not topic:
                # Create a default topic if none found
                topic = Topic(
                    name=subcategory or category or "General",
                    description=f"Auto-created from CSV upload"
                )
                db.add(topic)
                await db.flush()
            
            # Create question
            question = Question(
                topic_id=topic.id,
                stem=stem,
                answer=answer,
                solution_approach="",
                detailed_solution="",
                subcategory=subcategory or category or "General",
                type_of_question="",  # Empty for CSV uploads, can be enriched later
                tags=[],
                source=source or "CSV Upload",
                is_active=True
            )
            
            db.add(question)
            questions_created += 1
            
        await db.commit()
        
        return {
            "message": f"Successfully uploaded {questions_created} questions from CSV",
            "questions_created": questions_created
        }
        
    except Exception as e:
        logger.error(f"CSV upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload CSV: {str(e)}")

@api_router.post("/admin/pyq/upload")
async def upload_pyq_document(
    file: UploadFile = File(...),
    year: int = Form(...),
    slot: Optional[str] = Form(None),
    source_url: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_database)
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

@api_router.get("/admin/stats")
async def get_admin_stats(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_database)
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
    """Background task to enrich a question using LLM"""
    try:
        async with get_database() as db:
            # Get question
            result = await db.execute(select(Question).where(Question.id == question_id))
            question = result.scalar_one_or_none()
            
            if not question:
                logger.error(f"Question {question_id} not found for enrichment")
                return
            
            # Run enrichment
            enrichment_result = await llm_pipeline.enrich_question(
                question.stem,
                question.answer,
                question.source,
                hint_category,
                hint_subcategory
            )
            
            # Update question with enrichment data
            question.subcategory = enrichment_result["subcategory"]
            question.solution_approach = enrichment_result["solution_approach"]
            question.detailed_solution = enrichment_result["detailed_solution"]
            question.difficulty_score = enrichment_result["difficulty_score"]
            question.difficulty_band = enrichment_result["difficulty_band"]
            question.frequency_band = enrichment_result["frequency_band"]
            question.learning_impact = enrichment_result["learning_impact"]
            question.learning_impact_band = enrichment_result["learning_impact_band"]
            question.importance_index = enrichment_result["importance_index"]
            question.importance_band = enrichment_result["importance_band"]
            question.video_url = enrichment_result["video_url"]
            question.version += 1
            question.is_active = True  # Activate after enrichment
            
            await db.commit()
            logger.info(f"Question {question_id} enriched successfully")
            
    except Exception as e:
        logger.error(f"Error in background enrichment: {e}")

async def process_pyq_document(ingestion_id: str, file_content: bytes):
    """Background task to process PYQ document"""
    try:
        async with get_database() as db:
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
            
    except Exception as e:
        logger.error(f"Error processing PYQ document: {e}")
        # Update ingestion status to failed
        try:
            async with get_database() as db:
                result = await db.execute(select(PYQIngestion).where(PYQIngestion.id == ingestion_id))
                ingestion = result.scalar_one_or_none()
                if ingestion:
                    ingestion.parse_status = "failed"
                    ingestion.parse_log = str(e)
                    await db.commit()
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
    await init_database()
    logger.info("📊 Database initialized")
    
    # Create initial topics if needed
    await create_initial_topics()
    logger.info("📚 Topics initialized")
    
    # Create diagnostic set if needed
    async for db in get_database():
        await diagnostic_system.create_diagnostic_set(db)
        break
    logger.info("🎯 Diagnostic system initialized")
    
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
        async for db in get_database():
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
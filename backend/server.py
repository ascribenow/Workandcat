# server.py - Cleaned version without deleted table dependencies
# FastAPI server for Twelvr CAT Preparation Platform
# Removed: Session logic, Mastery tracking, Diagnostic system, Planning system

import os
import json
import uuid
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal

import bcrypt
import jwt
from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File, Form, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session as SQLSession
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, text, update, delete
from sqlalchemy.exc import IntegrityError
import aiofiles

# Import services (cleaned of deleted dependencies)
from mcq_validation_service import mcq_validation_service
from regular_enrichment_service import regular_questions_enrichment_service
from database import (
    get_async_compatible_db, get_database, init_database, User, Question, 
    PYQIngestion, PYQPaper, PYQQuestion, PrivilegedEmail, AsyncSession, SessionLocal,
    Subscription, PaymentTransaction, PaymentOrder, ReferralUsage
)
from datetime import datetime
from payment_service import PaymentService
from referral_service import ReferralService
from subscription_access_service import SubscriptionAccessService
from gmail_service import gmail_service

# Import enrichment services
from pyq_enrichment_service import pyq_enrichment_service
# from enhanced_enrichment_checker_service import enhanced_enrichment_checker_service  # File deleted during cleanup
from individual_enrichment_stages import stages_router

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Twelvr CAT Prep API - Cleaned Version", version="2.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Global services
payment_service = PaymentService()
referral_service = ReferralService()
subscription_service = SubscriptionAccessService()

# Static files
os.makedirs("/app/backend/uploads/images", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="/app/backend/uploads"), name="uploads")

# Include routers  
app.include_router(stages_router)

# Import and include adaptive session router
from api.adapt import router as adapt_router
from api.session_lifecycle import router as session_lifecycle_router
from api.doubts import router as doubts_router
from middleware.adaptive_gate import ensure_adaptive_enabled
app.include_router(
    adapt_router,
    dependencies=[Depends(ensure_adaptive_enabled)]
)
app.include_router(session_lifecycle_router, prefix="/api/sessions")
app.include_router(doubts_router, prefix="/api")

# In-memory logging store (for MVP - replace with database in production)
question_action_logs = []

# Pydantic models for requests
class LoginRequest(BaseModel):
    email: str
    password: str

class SignupRequest(BaseModel):
    email: str
    full_name: str
    password: str

class QuestionResponse(BaseModel):
    id: str
    stem: str
    right_answer: str
    category: str
    subcategory: str
    type_of_question: str
    difficulty_level: str
    difficulty_score: float
    concept_keywords: List[str]
    core_concepts: List[str]
    solution_method: str
    operations_required: List[str]
    has_image: bool
    image_url: Optional[str]
    snap_read: Optional[str]
    solution_approach: Optional[str]
    detailed_solution: Optional[str]
    principle_to_remember: Optional[str]

class QuestionActionLog(BaseModel):
    session_id: str
    question_id: str
    action: str  # skip, submit, correct, incorrect
    data: Dict[str, Any] = {}
    timestamp: str

# Authentication helpers
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, os.getenv("JWT_SECRET"), algorithm="HS256")
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, os.getenv("JWT_SECRET"), algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_admin_user(user_id: str = Depends(get_current_user)):
    db = SessionLocal()
    try:
        result = db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or not user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        return user
    finally:
        db.close()

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Twelvr API is running - cleaned version"}

# Authentication endpoints
@app.post("/api/auth/signup")
async def signup(signup_data: SignupRequest):
    db = SessionLocal()
    try:
        # Check if user exists
        result = db.execute(select(User).where(User.email == signup_data.email))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Hash password
        password_hash = bcrypt.hashpw(signup_data.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Generate referral code
        referral_code = referral_service.generate_referral_code(db)  # Remove await
        
        # Create user
        user = User(
            id=str(uuid.uuid4()),
            email=signup_data.email,
            full_name=signup_data.full_name,
            password_hash=password_hash,
            referral_code=referral_code
        )
        
        db.add(user)
        db.commit()  # Remove await
        
        # Create access token
        access_token = create_access_token(data={"sub": user.id})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "is_admin": user.is_admin,
                "adaptive_enabled": bool(user.adaptive_enabled)
            }
        }
    finally:
        db.close()

@app.post("/api/auth/login")
async def login(login_data: LoginRequest):
    db = SessionLocal()
    try:
        result = db.execute(select(User).where(User.email == login_data.email))
        user = result.scalar_one_or_none()
        
        if not user or not bcrypt.checkpw(login_data.password.encode('utf-8'), user.password_hash.encode('utf-8')):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        access_token = create_access_token(data={"sub": user.id})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "is_admin": user.is_admin,
                "adaptive_enabled": bool(user.adaptive_enabled)
            }
        }
    finally:
        db.close()

@app.get("/api/auth/me")
async def get_me(user_id: str = Depends(get_current_user)):
    db = SessionLocal()
    try:
        result = db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_admin": user.is_admin,
            "adaptive_enabled": bool(user.adaptive_enabled)
        }
    finally:
        db.close()

# Questions endpoints
@app.get("/api/questions")
async def get_questions(
    category: Optional[str] = None,
    limit: int = 50,
    user_id: str = Depends(get_current_user)
):
    db = SessionLocal()
    try:
        query = select(Question).where(Question.is_active == True)
        
        if category:
            query = query.where(Question.category == category)
        
        query = query.limit(limit)
        result = db.execute(query)
        questions = result.scalars().all()
        
        return [
            QuestionResponse(
                id=q.id,
                stem=q.stem or "",
                right_answer=q.right_answer or "",
                category=q.category or "",
                subcategory=q.subcategory or "",
                type_of_question=q.type_of_question or "",
                difficulty_level=q.difficulty_band or "",
                difficulty_score=float(q.difficulty_score or 0),
                concept_keywords=json.loads(q.concept_keywords) if q.concept_keywords and isinstance(q.concept_keywords, str) else (q.concept_keywords or []),
                core_concepts=json.loads(q.core_concepts) if q.core_concepts and isinstance(q.core_concepts, str) else (q.core_concepts or []),
                solution_method=q.solution_method or "",
                operations_required=json.loads(q.operations_required) if q.operations_required and isinstance(q.operations_required, str) else (q.operations_required or []),
                has_image=q.has_image or False,
                image_url=q.image_url,
                snap_read=q.snap_read,
                solution_approach=q.solution_approach,
                detailed_solution=q.detailed_solution,
                principle_to_remember=q.principle_to_remember
            ) for q in questions
        ]
    finally:
        db.close()

# User referral endpoints
@app.get("/api/user/referral-code")
async def get_user_referral_code(user_id: str = Depends(get_current_user)):
    async for db in get_database():
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not user.referral_code:
            # Generate referral code if not exists
            referral_code = await referral_service.generate_referral_code(db)
            user.referral_code = referral_code
            await db.commit()
        
        return {
            "referral_code": user.referral_code,
            "share_message": f"Use my referral code {user.referral_code} and get ₹500 off on Twelvr Pro subscription!"
        }

# Referral validation
@app.post("/api/referral/validate")
async def validate_referral_code(request: dict, user_id: str = Depends(get_current_user)):
    referral_code = request.get("referral_code")
    if not referral_code:
        raise HTTPException(status_code=400, detail="Referral code is required")
    
    async for db in get_database():
        result = await referral_service.validate_referral_code(db, referral_code, user_id)
        return result

# Payment endpoints
@app.get("/api/payments/config")
async def get_payment_config(user_id: str = Depends(get_current_user)):
    return await payment_service.get_payment_config()

@app.post("/api/payments/create-subscription")
async def create_subscription_payment(
    request: dict,
    user_id: str = Depends(get_current_user)
):
    async for db in get_database():
        plan_type = request.get("plan_type", "pro_regular")
        referral_code = request.get("referral_code")
        
        result = await payment_service.create_subscription_payment(
            db, user_id, plan_type, referral_code
        )
        return result

@app.post("/api/payments/create-order")
async def create_order_payment(
    request: dict,
    user_id: str = Depends(get_current_user)
):
    async for db in get_database():
        plan_type = request.get("plan_type", "pro_exclusive")
        referral_code = request.get("referral_code")
        
        result = await payment_service.create_order_payment(
            db, user_id, plan_type, referral_code
        )
        return result

@app.post("/api/payments/verify-payment")
async def verify_payment(request: dict, user_id: str = Depends(get_current_user)):
    async for db in get_database():
        result = await payment_service.verify_payment(db, request, user_id)
        return result

# Subscription endpoints
@app.get("/api/subscriptions/status")
async def get_subscription_status(user_id: str = Depends(get_current_user)):
    async for db in get_database():
        result = await subscription_service.get_user_subscription_status(db, user_id)
        return result

# Admin endpoints
@app.get("/api/admin/questions")
async def admin_get_questions(
    limit: int = 100,
    admin_user: User = Depends(get_current_admin_user)
):
    async for db in get_database():
        query = select(Question).limit(limit)
        result = await db.execute(query)
        questions = result.scalars().all()
        
        return [{
            "id": q.id,
            "stem": q.stem,
            "right_answer": q.right_answer,
            "category": q.category,
            "subcategory": q.subcategory,
            "is_active": q.is_active,
            "quality_verified": q.quality_verified
        } for q in questions]

# PYQ Admin endpoints
@app.get("/api/admin/pyq/questions")
async def admin_get_pyq_questions(
    year: Optional[int] = None,
    limit: int = 100,
    admin_user: User = Depends(get_current_admin_user)
):
    async for db in get_database():
        query = select(PYQQuestion)
        if year:
            query = query.where(PYQQuestion.year == year)
        query = query.limit(limit)
        
        result = await db.execute(query)
        questions = result.scalars().all()
        
        return [{
            "id": q.id,
            "stem": q.stem,
            "year": q.year,
            "category": q.category,
            "difficulty_score": float(q.difficulty_score or 0),
            "quality_verified": q.quality_verified
        } for q in questions]

@app.get("/api/admin/pyq/enrichment-status")
async def admin_get_pyq_enrichment_status(admin_user: User = Depends(get_current_admin_user)):
    async for db in get_database():
        result = await pyq_enrichment_service.get_enrichment_status(db)
        return result

@app.post("/api/admin/pyq/trigger-enrichment")
async def admin_trigger_pyq_enrichment(admin_user: User = Depends(get_current_admin_user)):
    async for db in get_database():
        result = await pyq_enrichment_service.trigger_manual_enrichment(db)
        return result

# Regular questions admin endpoints
@app.get("/api/admin/regular/enrichment-status")
async def admin_get_regular_enrichment_status(admin_user: User = Depends(get_current_admin_user)):
    db = SessionLocal()
    try:
        result = await regular_questions_enrichment_service.get_enrichment_status(db)
        return result
    finally:
        db.close()

@app.post("/api/admin/regular/trigger-enrichment")
async def admin_trigger_regular_enrichment(admin_user: User = Depends(get_current_admin_user)):
    db = SessionLocal()
    try:
        result = await regular_questions_enrichment_service.trigger_manual_enrichment(db)
        return result
    finally:
        db.close()

# CSV Upload endpoints
@app.post("/api/admin/upload-questions-csv")
async def upload_questions_csv(
    file: UploadFile = File(...),
    admin_user: User = Depends(get_current_admin_user)
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    async for db in get_database():
        # Save uploaded file
        file_path = f"/tmp/{file.filename}"
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Process CSV
        result = await regular_questions_enrichment_service.process_csv_upload(db, file_path, admin_user.id)
        return result

# NEW: PYQ Frequency Recalculation Endpoint
@app.post("/api/admin/recalculate-frequency-background")
async def recalculate_frequency_background(
    background_tasks: BackgroundTasks,
    admin_user: User = Depends(get_current_admin_user)
):
    """
    Background PYQ frequency recalculation for all quality-verified questions
    Uses the corrected logic that properly handles difficulty filtering
    """
    job_id = str(uuid.uuid4())
    
    # Add background task
    background_tasks.add_task(
        run_frequency_recalculation_job,
        job_id,
        admin_user.email
    )
    
    return {
        "success": True,
        "job_id": job_id,
        "message": "PYQ frequency recalculation started in background",
        "admin_email": admin_user.email,
        "estimated_time": "15-30 minutes for all questions"
    }

async def run_frequency_recalculation_job(job_id: str, admin_email: str):
    """
    Background job to recalculate PYQ frequency for all questions
    Uses batch processing with proper error handling
    """
    try:
        logger.info(f"🚀 Starting frequency recalculation job {job_id}")
        
        db = SessionLocal()
        total_questions = 0
        processed_count = 0
        updated_count = 0
        easy_count = 0
        hard_count = 0
        
        try:
            # Get all quality verified questions
            result = db.execute(
                select(Question).where(Question.quality_verified == True)
            )
            all_questions = result.scalars().all()
            total_questions = len(all_questions)
            
            logger.info(f"📊 Found {total_questions} quality verified questions to process")
            
            for i, question in enumerate(all_questions, 1):
                try:
                    logger.info(f"🔄 Processing {i}/{total_questions}: {question.id[:8]}...")
                    
                    # Prepare enrichment data for the corrected method
                    enrichment_data = {
                        'category': question.category,
                        'subcategory': question.subcategory,
                        'difficulty_score': float(question.difficulty_score or 0),
                        'core_concepts': question.core_concepts or [],
                        'problem_structure': question.problem_structure or [],
                        'concept_keywords': question.concept_keywords or []
                    }
                    
                    # Get current PYQ frequency
                    old_frequency = float(question.pyq_frequency_score or 0)
                    
                    # Run corrected PYQ frequency calculation
                    new_frequency = await regular_questions_enrichment_service._calculate_pyq_frequency_score_llm(
                        question.stem, enrichment_data
                    )
                    
                    # Track difficulty categories
                    if enrichment_data['difficulty_score'] <= 1.5:
                        easy_count += 1
                    else:
                        hard_count += 1
                    
                    # Update if different
                    if abs(new_frequency - old_frequency) > 0.01:  # Account for floating point precision
                        question.pyq_frequency_score = new_frequency
                        updated_count += 1
                        logger.info(f"   ✅ Updated: {old_frequency} → {new_frequency}")
                    else:
                        logger.info(f"   = No change: {old_frequency}")
                    
                    processed_count += 1
                    
                    # Commit every 10 questions to avoid losing progress
                    if processed_count % 10 == 0:
                        db.commit()
                        logger.info(f"   💾 Committed batch (processed: {processed_count})")
                        
                except Exception as e:
                    logger.error(f"❌ Error processing question {question.id[:8]}: {e}")
                    continue
            
            # Final commit
            db.commit()
            
            # Success notification
            success_message = f"""
🎉 FREQUENCY RECALCULATION COMPLETE!

📊 Summary:
• Total processed: {processed_count}/{total_questions}
• Questions updated: {updated_count}
• Easy questions (≤1.5): {easy_count}
• Hard questions (>1.5): {hard_count}
• Success rate: {(processed_count/total_questions)*100:.1f}%

Job ID: {job_id}
"""
            
            logger.info(success_message)
            
            # Send email notification
            await send_job_completion_email(admin_email, "PYQ Frequency Recalculation", success_message, True)
            
        except Exception as e:
            logger.error(f"❌ Frequency recalculation job failed: {e}")
            
            # Send failure email
            failure_message = f"""
❌ FREQUENCY RECALCULATION FAILED

Error: {str(e)}
Job ID: {job_id}
Processed: {processed_count}/{total_questions} questions

Please check the server logs for more details.
"""
            await send_job_completion_email(admin_email, "PYQ Frequency Recalculation Failed", failure_message, False)
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Critical error in frequency recalculation job {job_id}: {e}")

async def send_job_completion_email(admin_email: str, subject: str, message: str, success: bool):
    """Send email notification for job completion"""
    try:
        await gmail_service.send_email(
            to_email=admin_email,
            subject=f"Twelvr Admin - {subject}",
            body=message
        )
        logger.info(f"✅ Job completion email sent to {admin_email}")
    except Exception as e:
        logger.error(f"❌ Failed to send completion email: {e}")

# Enrichment checker endpoints - DISABLED (service deleted during cleanup)
# @app.post("/api/admin/enrich-checker/regular-questions")
# async def admin_enrich_checker_regular(admin_user: User = Depends(get_current_admin_user)):
#     async for db in get_database():
#         result = await enhanced_enrichment_checker_service.check_and_improve_regular_questions(db)
#         return result

# @app.post("/api/admin/enrich-checker/pyq-questions")
# async def admin_enrich_checker_pyq(admin_user: User = Depends(get_current_admin_user)):
#     async for db in get_database():
#         result = await enhanced_enrichment_checker_service.check_and_improve_pyq_questions(db)
#         return result

# Image upload endpoints
@app.post("/api/admin/image/upload")
async def upload_image(
    file: UploadFile = File(...),
    admin_user: User = Depends(get_current_admin_user)
):
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Only image files are allowed")
    
    # Save image
    file_id = str(uuid.uuid4())
    file_extension = file.filename.split('.')[-1]
    filename = f"{file_id}.{file_extension}"
    file_path = f"/app/backend/uploads/images/{filename}"
    
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    return {
        "filename": filename,
        "url": f"/uploads/images/{filename}"
    }

# Question Action Logging Endpoints
@app.post("/api/log/question-action")
async def log_question_action(
    log_data: QuestionActionLog,
    user_id: str = Depends(get_current_user)
):
    """Log question actions to database and return solution feedback for submit actions"""
    try:
        logger.info(f"📝 Logging action: {log_data.action} for question {log_data.question_id[:8]} by user {user_id[:8]}")
        
        # Store in database (attempt_events table)
        db = SessionLocal()
        try:
            # Get question details for attempt_events
            result = db.execute(select(Question).where(Question.id == log_data.question_id))
            question = result.scalar_one_or_none()
            
            if question:
                # Determine if answer was correct (for submit actions)
                user_answer = log_data.data.get('user_answer', '')
                was_correct = False
                skipped = log_data.action == 'skip'
                
                if log_data.action == 'submit' and user_answer:
                    # For better answer comparison, try multiple approaches
                    user_answer_clean = str(user_answer).strip().lower()
                    
                    # Approach 1: Direct comparison with stored right_answer
                    stored_answer_clean = str(question.right_answer).strip().lower() 
                    was_correct = user_answer_clean == stored_answer_clean
                    
                    # Approach 2: Check if user answer appears in the explanation (for descriptive answers)
                    if not was_correct and user_answer_clean in stored_answer_clean:
                        was_correct = True
                    
                    # Approach 3: Extract numerical answers (e.g., "5 days" vs "5")
                    if not was_correct:
                        import re
                        user_numbers = re.findall(r'\d+', user_answer_clean)
                        stored_numbers = re.findall(r'\d+', stored_answer_clean)
                        if user_numbers and stored_numbers:
                            # Check if any number from user matches any number from stored answer
                            was_correct = any(num in stored_numbers for num in user_numbers)
                    
                    # Approach 4: Check if the explanation confirms the user's answer is correct
                    if not was_correct and 'correct' in stored_answer_clean:
                        # Look for patterns like "5 days. The current answer is correct"
                        if user_answer_clean in stored_answer_clean and 'answer is correct' in stored_answer_clean:
                            was_correct = True
                    
                    logger.info(f"Answer comparison: user='{user_answer_clean}' vs stored='{stored_answer_clean[:100]}...' → {'CORRECT' if was_correct else 'INCORRECT'}")
                
                # Calculate response time (default to reasonable value if not provided)
                response_time_ms = log_data.data.get('time_taken', 60) * 1000  # Convert to milliseconds
                
                # Get sess_seq for this session
                sess_seq_result = db.execute(text("""
                    SELECT sess_seq FROM sessions 
                    WHERE user_id = :user_id AND session_id = :session_id 
                    LIMIT 1
                """), {
                    'user_id': user_id,
                    'session_id': log_data.session_id
                })
                sess_seq_row = sess_seq_result.fetchone()
                sess_seq_at_serve = sess_seq_row.sess_seq if sess_seq_row else 1
                
                # Insert into attempt_events
                db.execute(text("""
                    INSERT INTO attempt_events (
                        id, user_id, session_id, question_id, was_correct, skipped,
                        response_time_ms, created_at, difficulty_band, subcategory,
                        type_of_question, core_concepts, pyq_frequency_score, sess_seq_at_serve
                    ) VALUES (
                        :id, :user_id, :session_id, :question_id, :was_correct, :skipped,
                        :response_time_ms, :created_at, :difficulty_band, :subcategory,
                        :type_of_question, :core_concepts, :pyq_frequency_score, :sess_seq_at_serve
                    )
                """), {
                    'id': str(uuid.uuid4()),
                    'user_id': user_id,
                    'session_id': log_data.session_id,
                    'question_id': log_data.question_id,
                    'was_correct': was_correct,
                    'skipped': skipped,
                    'response_time_ms': response_time_ms,
                    'created_at': datetime.utcnow(),
                    'difficulty_band': question.difficulty_band,
                    'subcategory': question.subcategory,
                    'type_of_question': question.type_of_question,
                    'core_concepts': question.core_concepts,
                    'pyq_frequency_score': question.pyq_frequency_score,
                    'sess_seq_at_serve': sess_seq_at_serve
                })
                
                db.commit()
                logger.info(f"✅ Question action logged to database: {log_data.action} for question {log_data.question_id[:8]}")
                
                # If action is 'submit', return solution feedback
                if log_data.action == "submit":
                    return {
                        "success": True,
                        "message": f"Action '{log_data.action}' logged successfully",
                        "result": {
                            "correct": was_correct,
                            "status": "correct" if was_correct else "incorrect",
                            "message": "Correct answer!" if was_correct else "That's not quite right, but keep learning!",
                            "user_answer": user_answer,
                            "correct_answer": question.right_answer or "Not specified",
                            "solution_feedback": {
                                "snap_read": question.snap_read,
                                "solution_approach": question.solution_approach,
                                "detailed_solution": question.detailed_solution,
                                "principle_to_remember": question.principle_to_remember
                            },
                            "question_metadata": {
                                "subcategory": question.subcategory,
                                "difficulty_band": question.difficulty_band,
                                "type_of_question": question.type_of_question
                            }
                        }
                    }
                
                # For non-submit actions, return basic success response
                return {
                    "success": True,
                    "message": f"Action '{log_data.action}' logged successfully"
                }
            else:
                logger.warning(f"⚠️ Question {log_data.question_id} not found for logging")
                return {
                    "success": False,
                    "message": "Question not found"
                }
                
        finally:
            db.close()
        
    except Exception as e:
        logger.error(f"❌ Failed to log question action: {e}")
        raise HTTPException(status_code=500, detail="Failed to log action")

@app.get("/api/log/question-actions")
async def get_question_actions(
    session_id: Optional[str] = None,
    user_id: str = Depends(get_current_user)
):
    """Get question action logs for a user (optionally filtered by session)"""
    try:
        # Filter logs by user
        user_logs = [log for log in question_action_logs if log["user_id"] == user_id]
        
        # Filter by session if provided
        if session_id:
            user_logs = [log for log in user_logs if log["session_id"] == session_id]
        
        # Sort by timestamp (most recent first)
        user_logs.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return {
            "success": True,
            "logs": user_logs,
            "total_count": len(user_logs)
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get question actions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get action logs")

@app.get("/api/admin/log/question-actions")
async def admin_get_question_actions(
    limit: int = 100,
    admin_user: User = Depends(get_current_admin_user)
):
    """Admin endpoint to get all question action logs"""
    try:
        # Get most recent logs
        recent_logs = sorted(question_action_logs, key=lambda x: x["timestamp"], reverse=True)[:limit]
        
        # Calculate action statistics
        action_stats = {}
        for log in question_action_logs:
            action = log["action"]
            action_stats[action] = action_stats.get(action, 0) + 1
        
        return {
            "success": True,
            "logs": recent_logs,
            "total_count": len(question_action_logs),
            "action_statistics": action_stats,
            "available_actions": ["skip", "submit", "correct", "incorrect"]
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get admin question actions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get admin action logs")

# Temporary Session Endpoints (for frontend compatibility)
# These are minimal implementations - full session logic will be implemented later

@app.get("/api/sessions/last-completed-id")
async def get_last_completed_session_id(user_id: str, auth_user_id: str = Depends(get_current_user)):
    """Get the last completed session ID for a user"""
    try:
        # Security check
        if user_id != auth_user_id:
            raise HTTPException(status_code=403, detail="Cannot access other users' sessions")
        
        db = SessionLocal()
        try:
            result = db.execute(text("""
                SELECT session_id, sess_seq
                FROM sessions
                WHERE user_id = :user_id AND status = 'completed'
                ORDER BY sess_seq DESC
                LIMIT 1
            """), {'user_id': user_id}).fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail={"code": "NO_COMPLETED_SESSIONS"})
                
            return {
                "user_id": user_id,
                "session_id": result.session_id,
                "sess_seq": result.sess_seq
            }
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting last completed session: {e}")
        raise HTTPException(status_code=500, detail="Failed to get last completed session")

@app.get("/api/sessions/{session_id}/next-question")
async def get_next_question(
    session_id: str,
    user_id: str = Depends(get_current_user)
):
    """Temporary endpoint to get next question (random selection for now)"""
    try:
        db = SessionLocal()
        try:
            # Get a random active question
            result = db.execute(
                select(Question)
                .where(Question.is_active == True)
                .order_by(func.random())
                .limit(1)
            )
            question = result.scalar_one_or_none()
            
            if not question:
                return {"session_complete": True, "message": "No questions available"}
            
            # Create mock options from mcq_options if available
            options = {}
            if question.mcq_options:
                try:
                    mcq_data = json.loads(question.mcq_options) if isinstance(question.mcq_options, str) else question.mcq_options
                    options = mcq_data
                except:
                    # Fallback mock options
                    options = {
                        "a": "Option A",
                        "b": "Option B", 
                        "c": "Option C",
                        "d": "Option D"
                    }
            
            return {
                "question": {
                    "id": question.id,
                    "stem": question.stem,
                    "options": options,
                    "has_image": question.has_image,
                    "image_url": question.image_url,
                    "subcategory": question.subcategory,
                    "difficulty_band": question.difficulty_band
                },
                "session_progress": {
                    "current_question": 1,
                    "total_questions": 12
                }
            }
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Error getting next question: {e}")
        raise HTTPException(status_code=500, detail="Failed to get next question")

@app.post("/api/sessions/{session_id}/submit-answer")
async def submit_session_answer(
    session_id: str,
    request: dict,
    user_id: str = Depends(get_current_user)
):
    """Temporary endpoint to submit answer"""
    try:
        question_id = request.get("question_id")
        user_answer = request.get("user_answer")
        
        db = SessionLocal()
        try:
            # Get the question
            result = db.execute(select(Question).where(Question.id == question_id))
            question = result.scalar_one_or_none()
            
            if not question:
                raise HTTPException(status_code=404, detail="Question not found")
            
            # Check if answer is correct (simple comparison for now)
            is_correct = str(user_answer).strip().lower() == str(question.answer).strip().lower()
            
            return {
                "correct": is_correct,
                "status": "correct" if is_correct else "incorrect",
                "message": "Correct answer!" if is_correct else "That's not quite right.",
                "user_answer": user_answer,
                "correct_answer": question.answer,
                "solution_feedback": {
                    "snap_read": question.snap_read,
                    "solution_approach": question.solution_approach,
                    "detailed_solution": question.detailed_solution,
                    "principle_to_remember": question.principle_to_remember
                },
                "question_metadata": {
                    "subcategory": question.subcategory,
                    "difficulty_band": question.difficulty_band,
                    "type_of_question": question.type_of_question
                }
            }
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Error submitting answer: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit answer")

@app.post("/api/sessions/start")
async def start_session(request: dict, user_id: str = Depends(get_current_user)):
    """Temporary endpoint to start a new session"""
    try:
        # Generate session ID
        session_id = f"session_{uuid.uuid4()}"
        
        # Store basic session info in memory (replace with database in production)
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "started_at": datetime.utcnow().isoformat(),
            "status": "active",
            "total_questions": 12,
            "current_question": 0
        }
        
        # For now, we'll use a simple in-memory store
        if not hasattr(start_session, 'active_sessions'):
            start_session.active_sessions = {}
        start_session.active_sessions[session_id] = session_data
        
        return {
            "success": True,
            "session_id": session_id,
            "message": "Session started successfully",
            "session_metadata": {
                "total_questions": 12,
                "current_question": 0,
                "session_type": "practice",
                "phase_info": {
                    "current_session": 1
                }
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error starting session: {e}")
        raise HTTPException(status_code=500, detail="Failed to start session")

@app.get("/api/dashboard/simple-taxonomy")
async def get_simple_taxonomy(user_id: str = Depends(get_current_user)):
    """Get dashboard data with real session counts"""
    db = SessionLocal()
    try:
        # Count completed sessions for this user
        result = db.execute(text("""
            SELECT COUNT(*) as total_sessions
            FROM sessions 
            WHERE user_id = :user_id AND status = 'completed'
        """), {'user_id': user_id})
        completed_sessions = result.fetchone()
        
        # Get taxonomy data (questions attempted by category)
        result = db.execute(text("""
            SELECT 
                ae.subcategory,
                ae.difficulty_band,
                COUNT(*) as attempts,
                COUNT(CASE WHEN ae.was_correct = true THEN 1 END) as correct,
                COUNT(CASE WHEN ae.skipped = true THEN 1 END) as skipped
            FROM attempt_events ae
            WHERE ae.user_id = :user_id
            GROUP BY ae.subcategory, ae.difficulty_band
            ORDER BY ae.subcategory, ae.difficulty_band
        """), {'user_id': user_id})
        taxonomy_rows = result.fetchall()
        
        taxonomy_data = []
        for row in taxonomy_rows:
            taxonomy_data.append({
                "subcategory": row.subcategory,
                "difficulty_band": row.difficulty_band,
                "attempts": row.attempts,
                "correct": row.correct,
                "skipped": row.skipped,
                "accuracy": round((row.correct / row.attempts * 100) if row.attempts > 0 else 0, 1)
            })
        
        return {
            "total_sessions": completed_sessions.total_sessions if completed_sessions else 0,
            "taxonomy_data": taxonomy_data
        }
    finally:
        db.close()

@app.get("/api/user/session-limit-status")
async def get_session_limit_status(user_id: str = Depends(get_current_user)):
    """Temporary endpoint for session limit status"""
    return {
        "sessions_today": 0,
        "daily_limit": 10,
        "can_start_session": True,
        "remaining_sessions": 10
    }

@app.get("/api/dashboard/mastery")
async def get_dashboard_mastery(user_id: str = Depends(get_current_user)):
    """Get mastery data from database"""
    db = SessionLocal()
    try:
        # Get overall stats
        result = db.execute(text("""
            SELECT 
                COUNT(*) as total_attempts,
                COUNT(CASE WHEN was_correct = true THEN 1 END) as correct_answers,
                COUNT(CASE WHEN skipped = true THEN 1 END) as skipped_questions
            FROM attempt_events 
            WHERE user_id = :user_id
        """), {'user_id': user_id})
        stats = result.fetchone()
        
        total_attempts = stats.total_attempts if stats else 0
        correct_answers = stats.correct_answers if stats else 0
        accuracy_rate = round((correct_answers / total_attempts * 100) if total_attempts > 0 else 0.0, 1)
        
        return {
            "total_questions_attempted": total_attempts,
            "correct_answers": correct_answers,
            "accuracy_rate": accuracy_rate,
            "skipped_questions": stats.skipped_questions if stats else 0,
            "mastery_levels": []  # Can be expanded later
        }
    finally:
        db.close()

@app.get("/api/user/subscription-management")
async def get_subscription_management(user_id: str = Depends(get_current_user)):
    """Temporary endpoint for subscription management"""
    return {
        "active_subscription": None,
        "subscription_status": "inactive",
        "can_access_premium": False
    }

@app.get("/api/sessions/current-status")
async def get_current_session_status(user_id: str = Depends(get_current_user)):
    """Temporary endpoint for current session status"""
    try:
        # Check if we have any active sessions for this user
        if hasattr(start_session, 'active_sessions'):
            for session_id, session_data in start_session.active_sessions.items():
                if session_data["user_id"] == user_id and session_data["status"] == "active":
                    return {
                        "has_active_session": True,
                        "session_id": session_id,
                        "session_metadata": {
                            "total_questions": session_data["total_questions"],
                            "current_question": session_data["current_question"],
                            "started_at": session_data["started_at"]
                        }
                    }
        
        return {
            "has_active_session": False,
            "session_id": None,
            "message": "No active session found"
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting session status: {e}")
        return {
            "has_active_session": False,
            "session_id": None,
            "message": "Error checking session status"
        }

@app.get("/api/dashboard/progress")
async def get_dashboard_progress(user_id: str = Depends(get_current_user)):
    """Temporary endpoint for dashboard progress"""
    return {
        "total_questions_attempted": 0,
        "questions_correct": 0,
        "questions_incorrect": 0,
        "accuracy_percentage": 0.0,
        "progress_data": []
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
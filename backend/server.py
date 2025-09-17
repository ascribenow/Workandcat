# server.py - Cleaned version without deleted table dependencies
# FastAPI server for Twelvr CAT Preparation Platform
# Removed: Session logic, Mastery tracking, Diagnostic system, Planning system

import os
import json
import uuid
import asyncio
import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
# IST timezone imports
from utils.timezone_utils import now_ist, utc_to_ist, ist_to_utc
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
from api.session_progress import router as session_progress_router
# REMOVED: adaptive_gate middleware - system is now adaptive-only
app.include_router(adapt_router)  # No middleware needed - all users adaptive
app.include_router(session_lifecycle_router, prefix="/api/sessions")
app.include_router(doubts_router, prefix="/api")
app.include_router(session_progress_router, prefix="/api")

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
    expire = now_ist() + timedelta(hours=24)  # IST timezone
    to_encode.update({"exp": expire.timestamp()})  # Convert to timestamp for JWT
    encoded_jwt = jwt.encode(to_encode, os.getenv("JWT_SECRET"), algorithm="HS256")
    return encoded_jwt

def clean_answer_for_comparison(answer_text):
    """Clean answer text for comparison by removing MCQ prefixes and normalizing"""
    if not answer_text:
        return ""
    
    # Remove MCQ prefixes like "(A) ", "(B) ", etc.
    cleaned = str(answer_text).strip()
    cleaned = re.sub(r'^\([A-D]\)\s*', '', cleaned)  # Remove (A), (B), etc.
    
    # Convert to lowercase for case-insensitive comparison
    cleaned = cleaned.lower().strip()
    
    return cleaned

def answers_match(user_answer, stored_answer, stored_full_answer=None):
    """
    Enhanced answer matching logic for MCQ questions
    Handles multiple answer formats and comparison strategies
    """
    if not user_answer:
        return False
    
    # Clean both answers
    user_clean = clean_answer_for_comparison(user_answer)
    stored_clean = clean_answer_for_comparison(stored_answer) if stored_answer else ""
    stored_full_clean = clean_answer_for_comparison(stored_full_answer) if stored_full_answer else ""
    
    # Strategy 1: Direct match with canonical answer
    if user_clean == stored_clean:
        return True
    
    # Strategy 2: Direct match with full answer (if available)
    if stored_full_clean and user_clean == stored_full_clean:
        return True
    
    # Strategy 3: Check if user answer contains the canonical answer
    if stored_clean and stored_clean in user_clean:
        return True
    
    # Strategy 4: Check if canonical answer contains the user answer (for short answers)
    if stored_clean and user_clean in stored_clean:
        return True
    
    # Strategy 5: Extract key numeric/percentage values for comparison
    import re
    user_numbers = re.findall(r'\d+\.?\d*%?', user_clean)
    stored_numbers = re.findall(r'\d+\.?\d*%?', stored_clean)
    
    if user_numbers and stored_numbers:
        # Check if the main numeric values match
        if user_numbers[0] == stored_numbers[0]:
            return True
    
    return False

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
    db = SessionLocal()
    try:
        result = db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not user.referral_code:
            # Generate referral code if not exists
            referral_code = referral_service.generate_referral_code(db)
            user.referral_code = referral_code
            db.commit()
        
        return {
            "referral_code": user.referral_code,
            "share_message": f"Use my referral code {user.referral_code} and get ₹500 off on Twelvr Pro subscription!"
        }
    finally:
        db.close()

# Referral validation
@app.post("/api/referral/validate")
async def validate_referral_code(request: dict, user_id: str = Depends(get_current_user)):
    referral_code = request.get("referral_code")
    if not referral_code:
        raise HTTPException(status_code=400, detail="Referral code is required")
    
    db = SessionLocal()
    try:
        result = referral_service.validate_referral_code(db, referral_code, user_id)
        return result
    finally:
        db.close()

# Payment endpoints
@app.get("/api/payments/config")
async def get_payment_config(user_id: str = Depends(get_current_user)):
    try:
        config = payment_service.get_payment_methods_config()
        config["razorpay_key_id"] = os.getenv("RAZORPAY_KEY_ID")
        return config
    except Exception as e:
        logger.error(f"Payment config error: {e}")
        raise HTTPException(status_code=500, detail="Payment configuration error")

@app.post("/api/payments/create-subscription")
async def create_subscription_payment(
    request: dict,
    user_id: str = Depends(get_current_user)
):
    db = SessionLocal()
    try:
        plan_type = request.get("plan_type", "pro_regular")
        referral_code = request.get("referral_code")
        
        # Get user details
        user_result = db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        result = await payment_service.create_subscription(
            plan_type, user.email, user.full_name, user_id, None, referral_code
        )
        return result
    except Exception as e:
        logger.error(f"Subscription creation error: {e}")
        raise HTTPException(status_code=500, detail="Subscription creation failed")
    finally:
        db.close()

@app.post("/api/payments/create-order")
async def create_order_payment(
    request: dict,
    user_id: str = Depends(get_current_user)
):
    db = SessionLocal()
    try:
        plan_type = request.get("plan_type", "pro_exclusive")
        referral_code = request.get("referral_code")
        
        # Get user details
        user_result = db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        result = await payment_service.create_order(
            plan_type, user.email, user.full_name, user_id, None, referral_code
        )
        return result
    except Exception as e:
        logger.error(f"Order creation error: {e}")
        raise HTTPException(status_code=500, detail="Order creation failed")
    finally:
        db.close()

@app.post("/api/payments/verify-payment")
async def verify_payment(request: dict, user_id: str = Depends(get_current_user)):
    try:
        result = payment_service.verify_payment(
            request.get("razorpay_payment_id"),
            request.get("razorpay_order_id"),
            request.get("razorpay_signature"),
            user_id
        )
        return result
    except Exception as e:
        logger.error(f"Payment verification error: {e}")
        raise HTTPException(status_code=500, detail="Payment verification failed")

# Subscription endpoints
@app.get("/api/subscriptions/status")
async def get_subscription_status(user_id: str = Depends(get_current_user)):
    db = SessionLocal()
    try:
        # Get user email for subscription service
        user_result = db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        result = subscription_service.get_user_access_level(user_id, user.email, db)
        return result
    finally:
        db.close()

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

@app.get("/api/admin/privileged-users")
async def admin_get_privileged_users(admin_user: User = Depends(get_current_admin_user)):
    """Get all privileged users for admin dashboard"""
    db = SessionLocal()
    try:
        from database import PrivilegedEmail
        result = db.execute(select(PrivilegedEmail).order_by(PrivilegedEmail.created_at.desc()))
        privileged_users = result.scalars().all()
        
        # Also get user details for display
        privileged_data = []
        for priv_user in privileged_users:
            user_result = db.execute(select(User).where(User.email == priv_user.email))
            user = user_result.scalar_one_or_none()
            
            privileged_data.append({
                "id": priv_user.id,
                "email": priv_user.email,
                "added_by_admin": priv_user.added_by_admin,
                "created_at": utc_to_ist(priv_user.created_at).isoformat(),
                "notes": priv_user.notes,
                "user_exists": user is not None,
                "user_name": user.full_name if user else None,
                "user_id": user.id if user else None
            })
        
        return {
            "privileged_users": privileged_data,
            "total_count": len(privileged_data)
        }
    finally:
        db.close()

@app.post("/api/admin/privileged-users")
async def admin_add_privileged_user(
    request: dict,
    admin_user: User = Depends(get_current_admin_user)
):
    """Add a new privileged user"""
    email = request.get("email", "").strip().lower()
    notes = request.get("notes", "").strip()
    
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    
    db = SessionLocal()
    try:
        from database import PrivilegedEmail
        
        # Check if already exists
        existing = db.execute(select(PrivilegedEmail).where(PrivilegedEmail.email == email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already has privileged access")
        
        # Add new privileged user
        new_privileged = PrivilegedEmail(
            email=email,
            added_by_admin=admin_user.id,
            notes=notes or f"Added by admin {admin_user.email}"
        )
        
        db.add(new_privileged)
        db.commit()
        
        return {
            "success": True,
            "message": f"Privileged access granted to {email}",
            "privileged_user": {
                "id": new_privileged.id,
                "email": new_privileged.email,
                "notes": new_privileged.notes,
                "added_by": admin_user.email
            }
        }
    finally:
        db.close()

@app.delete("/api/admin/privileged-users/{privileged_id}")
async def admin_remove_privileged_user(
    privileged_id: str,
    admin_user: User = Depends(get_current_admin_user)
):
    """Remove privileged access for a user"""
    db = SessionLocal()
    try:
        from database import PrivilegedEmail
        
        # Find and delete
        privileged = db.execute(select(PrivilegedEmail).where(PrivilegedEmail.id == privileged_id))
        privileged_user = privileged.scalar_one_or_none()
        
        if not privileged_user:
            raise HTTPException(status_code=404, detail="Privileged user not found")
        
        email = privileged_user.email
        db.delete(privileged_user)
        db.commit()
        
        return {
            "success": True,
            "message": f"Privileged access removed for {email}"
        }
    finally:
        db.close()

@app.get("/api/admin/referral-dashboard")
async def get_admin_referral_dashboard(admin_user: User = Depends(get_current_admin_user)):
    """Get comprehensive referral dashboard for admin"""
    db = SessionLocal()
    try:
        # Overall referral statistics
        overall_stats = db.execute(text("""
            SELECT 
                COUNT(DISTINCT referral_code) as total_referral_codes_used,
                COUNT(*) as total_referral_usage,
                SUM(discount_amount) as total_discount_given,
                COUNT(CASE WHEN subscription_type = 'pro_regular' THEN 1 END) as pro_regular_uses,
                COUNT(CASE WHEN subscription_type = 'pro_exclusive' THEN 1 END) as pro_exclusive_uses
            FROM referral_usage
        """)).fetchone()
        
        # Top performing referral codes
        top_referrals = db.execute(text("""
            SELECT 
                ru.referral_code,
                u.full_name as referrer_name,
                u.email as referrer_email,
                COUNT(*) as total_uses,
                SUM(ru.discount_amount) as total_discount_given,
                (COUNT(*) * 50000) as cashback_due
            FROM referral_usage ru
            LEFT JOIN users u ON u.referral_code = ru.referral_code
            GROUP BY ru.referral_code, u.full_name, u.email
            ORDER BY total_uses DESC
            LIMIT 20
        """)).fetchall()
        
        # Recent referral activity (last 30 days)
        recent_activity = db.execute(text("""
            SELECT 
                ru.referral_code,
                u.full_name as referrer_name,
                ru.used_by_email,
                ru.subscription_type,
                ru.discount_amount,
                ru.created_at
            FROM referral_usage ru
            LEFT JOIN users u ON u.referral_code = ru.referral_code
            WHERE ru.created_at >= NOW() - INTERVAL '30 days'
            ORDER BY ru.created_at DESC
            LIMIT 50
        """)).fetchall()
        
        return {
            "overall_stats": {
                "total_referral_codes_used": overall_stats.total_referral_codes_used or 0,
                "total_referral_usage": overall_stats.total_referral_usage or 0,
                "total_discount_given": f"₹{(overall_stats.total_discount_given or 0):.2f}",
                "total_cashback_due": f"₹{(overall_stats.total_referral_usage or 0) * 500:.2f}",
                "pro_regular_uses": overall_stats.pro_regular_uses or 0,
                "pro_exclusive_uses": overall_stats.pro_exclusive_uses or 0
            },
            "top_referrals": [
                {
                    "referral_code": ref.referral_code,
                    "referrer_name": ref.referrer_name,
                    "referrer_email": ref.referrer_email,
                    "total_uses": ref.total_uses,
                    "total_discount_given": f"₹{ref.total_discount_given:.2f}",
                    "cashback_due": f"₹{ref.cashback_due:.2f}"
                }
                for ref in top_referrals
            ],
            "recent_activity": [
                {
                    "referral_code": activity.referral_code,
                    "referrer_name": activity.referrer_name,
                    "used_by_email": activity.used_by_email,
                    "subscription_type": activity.subscription_type,
                    "discount_amount": f"₹{activity.discount_amount:.2f}",
                    "date": utc_to_ist(activity.created_at).strftime("%Y-%m-%d %I:%M %p IST") if activity.created_at else None
                }
                for activity in recent_activity
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting referral dashboard: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving referral dashboard")
    finally:
        db.close()

@app.get("/api/admin/export-referral-data")
async def export_referral_data(admin_user: User = Depends(get_current_admin_user)):
    """Export referral data for admin analysis"""
    db = SessionLocal()
    try:
        # Get all referral usage data
        referral_data = db.execute(text("""
            SELECT 
                ru.referral_code,
                u.full_name as referrer_name,
                u.email as referrer_email,
                ru.used_by_email,
                ru.subscription_type,
                ru.discount_amount,
                ru.created_at
            FROM referral_usage ru
            LEFT JOIN users u ON u.referral_code = ru.referral_code
            ORDER BY ru.created_at DESC
        """)).fetchall()
        
        return {
            "export_data": [
                {
                    "referral_code": data.referral_code,
                    "referrer_name": data.referrer_name,
                    "referrer_email": data.referrer_email,
                    "used_by_email": data.used_by_email,
                    "subscription_type": data.subscription_type,
                    "discount_amount": data.discount_amount,
                    "created_at": utc_to_ist(data.created_at).isoformat() if data.created_at else None
                }
                for data in referral_data
            ],
            "total_records": len(referral_data),
            "export_timestamp": utc_to_ist(now_ist()).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error exporting referral data: {e}")
        raise HTTPException(status_code=500, detail="Error exporting referral data")
    finally:
        db.close()

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
        stored_answer = ""  # Initialize to avoid scope issues
        try:
            # For adaptive sessions, try to get question from pack data first
            question = None
            sess_seq_at_serve = 1
            
            # First, get sess_seq for this session
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
            
            # Try to get question from pack data (for adaptive sessions)
            pack_result = db.execute(text("""
                SELECT pack_json FROM session_pack_plan 
                WHERE user_id = :user_id AND session_id = :session_id 
                LIMIT 1
            """), {
                'user_id': user_id,
                'session_id': log_data.session_id
            })
            pack_row = pack_result.fetchone()
            
            if pack_row and pack_row.pack_json:
                # Look for the question in the pack data
                pack_data = pack_row.pack_json
                items = pack_data.get('items', [])
                
                for item in items:
                    if item.get('item_id') == log_data.question_id:
                        # Found the question in pack data - use answer field only
                        question = type('Question', (), {
                            'id': item.get('item_id'),
                            'answer': item.get('answer', ''),  # Use pack answer field only
                            'difficulty_band': item.get('bucket', 'Medium'),
                            'subcategory': item.get('subcategory', ''),
                            'type_of_question': item.get('pair', '').split(':')[0] if item.get('pair') else '',
                            'core_concepts': json.dumps(item.get('semantic_concepts', [])),
                            'pyq_frequency_score': item.get('pyq_frequency_score', 0),
                            'snap_read': item.get('snap_read'),
                            'solution_approach': item.get('solution_approach'), 
                            'detailed_solution': item.get('detailed_solution'),
                            'principle_to_remember': item.get('principle_to_remember')
                        })()
                        break
            
            # ADAPTIVE-ONLY: All questions must come from pack data
            # No fallback to database - ensures data consistency
            if not question:
                logger.warning(f"⚠️ Question {log_data.question_id} not found in pack data - adaptive session may be corrupted")
                return {
                    "success": False,
                    "message": "Question not found in current session pack",
                    "error": "QUESTION_NOT_IN_PACK"
                }
            
            if question:
                # Determine if answer was correct (for submit actions)
                user_answer = log_data.data.get('user_answer', '')
                was_correct = False
                skipped = log_data.action == 'skip'
                
                if log_data.action == 'submit' and user_answer:
                    # Clean both user answer and stored answer for accurate comparison
                    user_answer_clean = clean_answer_for_comparison(user_answer)
                    
                    # Use the correct answer field based on question source
                    # ONLY use answer field as per specification - never right_answer
                    stored_answer = getattr(question, 'answer', '') or ""
                    stored_answer_clean = clean_answer_for_comparison(stored_answer)
                    
                    # Use sophisticated answer matching with multiple strategies
                    was_correct = answers_match(user_answer, stored_answer)
                    
                    logger.info(f"Answer comparison: user='{user_answer}' (clean: '{user_answer_clean}') vs answer='{stored_answer}' (clean: '{stored_answer_clean}') → {'CORRECT' if was_correct else 'INCORRECT'}")
                
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
                    'created_at': ist_to_utc(now_ist()),
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
                            "correct_answer": stored_answer or "Not specified",
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
                
                # For skip actions, still log to attempt_events with minimal data
                if log_data.action == 'skip':
                    try:
                        db.execute(text("""
                            INSERT INTO attempt_events (
                                id, user_id, session_id, question_id, was_correct, skipped,
                                response_time_ms, created_at, sess_seq_at_serve
                            ) VALUES (
                                :id, :user_id, :session_id, :question_id, :was_correct, :skipped,
                                :response_time_ms, :created_at, :sess_seq_at_serve
                            )
                        """), {
                            'id': str(uuid.uuid4()),
                            'user_id': user_id,
                            'session_id': log_data.session_id,
                            'question_id': log_data.question_id,
                            'was_correct': False,
                            'skipped': True,
                            'response_time_ms': 1000,  # Default for skip
                            'created_at': ist_to_utc(now_ist()),
                            'sess_seq_at_serve': sess_seq_at_serve
                        })
                        db.commit()
                        logger.info(f"✅ Skip action logged with minimal data for question {log_data.question_id[:8]}")
                        
                        return {
                            "success": True,
                            "message": f"Action '{log_data.action}' logged successfully (question not found but skip recorded)"
                        }
                    except Exception as skip_error:
                        logger.error(f"❌ Failed to log skip action: {skip_error}")
                
                # For other actions when question not found, return partial success
                return {
                    "success": True,
                    "message": f"Action '{log_data.action}' logged successfully (question not found in database)",
                    "warning": "Question details not available"
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

# REMOVED: Legacy non-adaptive session endpoint - system is now adaptive-only

# REMOVED: Legacy non-adaptive answer submission endpoint - system is now adaptive-only

# REMOVED: Legacy session start endpoint - system now uses adaptive-only session creation

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

@app.get("/api/dashboard/categorized-taxonomy")
async def get_categorized_taxonomy(user_id: str = Depends(get_current_user)):
    """Get dashboard data with canonical CAT taxonomy structure (all 5 categories + subcategories)"""
    db = SessionLocal()
    try:
        # Count completed sessions for this user
        result = db.execute(text("""
            SELECT COUNT(*) as total_sessions
            FROM sessions 
            WHERE user_id = :user_id AND status = 'completed'
        """), {'user_id': user_id})
        completed_sessions = result.fetchone()
        
        # Define canonical CAT taxonomy structure (all 5 categories + subcategories)
        canonical_taxonomy = {
            "Arithmetic": [
                "Percentages", "Profit-Loss-Discount", "Simple and Compound Interest",
                "Ratios and Proportions", "Time-Speed-Distance", "Time-Work", 
                "Mixtures and Solutions", "Averages and Alligation"
            ],
            "Algebra": [
                "Linear Equations", "Quadratic Equations", "Inequalities", "Functions"
            ],
            "Geometry and Mensuration": [
                "Triangles", "Circles", "Coordinate Geometry", "Mensuration 2D", "Mensuration 3D"
            ],
            "Number Systems": [
                "Properties of Numbers", "Divisibility Rules", "Factors and Multiples", 
                "HCF and LCM", "Prime Numbers"
            ],
            "Modern Mathematics": [
                "Permutations and Combinations", "Probability", "Sequences and Series",
                "Logarithms", "Progressions"
            ]
        }
        
        # Get actual attempt data (EXCLUDING SKIPPED QUESTIONS as per requirement)
        result = db.execute(text("""
            SELECT 
                COALESCE(q.category, 'Uncategorized') as category,
                ae.subcategory,
                ae.difficulty_band,
                COUNT(*) as attempts,
                COUNT(CASE WHEN ae.was_correct = true THEN 1 END) as correct,
                ROUND(AVG(CASE WHEN ae.was_correct = true THEN 1.0 ELSE 0.0 END) * 100, 1) as accuracy
            FROM attempt_events ae
            LEFT JOIN questions q ON ae.question_id = q.id
            WHERE ae.user_id = :user_id 
              AND ae.subcategory IS NOT NULL 
              AND ae.skipped = false  -- EXCLUDE SKIPPED QUESTIONS
            GROUP BY COALESCE(q.category, 'Uncategorized'), ae.subcategory, ae.difficulty_band
        """), {'user_id': user_id})
        
        rows = result.fetchall()
        
        # Build actual attempt data dictionary for fast lookup
        actual_data = {}
        for row in rows:
            category = row.category
            subcategory = row.subcategory
            difficulty = row.difficulty_band
            attempts = row.attempts
            correct = row.correct
            accuracy = row.accuracy
            
            if category not in actual_data:
                actual_data[category] = {}
            if subcategory not in actual_data[category]:
                actual_data[category][subcategory] = {}
            
            actual_data[category][subcategory][difficulty] = {
                "attempts": attempts,
                "correct": correct,
                "accuracy": accuracy
            }
        
        # Build complete canonical structure with actual data + zeros for missing
        categories_array = []
        
        for category_name, subcategory_list in canonical_taxonomy.items():
            category_totals = {"total_easy": 0, "total_medium": 0, "total_hard": 0, "total_attempts": 0}
            subcategories_array = []
            
            for subcategory_name in subcategory_list:
                # Get actual data or default to zeros
                subcategory_data = {
                    "subcategory_name": subcategory_name,
                    "easy_attempts": 0,
                    "medium_attempts": 0,
                    "hard_attempts": 0,
                    "easy_correct": 0,
                    "medium_correct": 0,
                    "hard_correct": 0,
                    "easy_accuracy": 0,
                    "medium_accuracy": 0,
                    "hard_accuracy": 0,
                    "total_attempts": 0
                }
                
                # Fill with actual data if available
                if (category_name in actual_data and 
                    subcategory_name in actual_data[category_name]):
                    
                    subcat_actual = actual_data[category_name][subcategory_name]
                    
                    for difficulty in ["Easy", "Medium", "Hard"]:
                        if difficulty in subcat_actual:
                            attempts = subcat_actual[difficulty]["attempts"]
                            correct = subcat_actual[difficulty]["correct"]
                            accuracy = subcat_actual[difficulty]["accuracy"]
                            
                            if difficulty == "Easy":
                                subcategory_data["easy_attempts"] = attempts
                                subcategory_data["easy_correct"] = correct
                                subcategory_data["easy_accuracy"] = accuracy
                                category_totals["total_easy"] += attempts
                            elif difficulty == "Medium":
                                subcategory_data["medium_attempts"] = attempts
                                subcategory_data["medium_correct"] = correct
                                subcategory_data["medium_accuracy"] = accuracy
                                category_totals["total_medium"] += attempts
                            elif difficulty == "Hard":
                                subcategory_data["hard_attempts"] = attempts
                                subcategory_data["hard_correct"] = correct
                                subcategory_data["hard_accuracy"] = accuracy
                                category_totals["total_hard"] += attempts
                            
                            subcategory_data["total_attempts"] += attempts
                            category_totals["total_attempts"] += attempts
                
                subcategories_array.append(subcategory_data)
            
            # Add category to final structure
            categories_array.append({
                "category_name": category_name,
                "total_easy": category_totals["total_easy"],
                "total_medium": category_totals["total_medium"],
                "total_hard": category_totals["total_hard"],
                "total_attempts": category_totals["total_attempts"],
                "subcategories": subcategories_array
            })
        
        return {
            "total_sessions": completed_sessions.total_sessions if completed_sessions else 0,
            "categorized_data": categories_array,
            "total_categories": 5,  # Always 5 canonical categories
            "note": "Dashboard shows canonical CAT taxonomy. Zero values indicate unattended topics."
        }
    finally:
        db.close()

@app.get("/api/user/session-limit-status")
async def get_session_limit_status(user_id: str = Depends(get_current_user)):
    """Enhanced session limit status with free tier logic"""
    db = SessionLocal()
    try:
        # Get user details
        user_result = db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if user is privileged
        from database import PrivilegedEmail
        privileged_result = db.execute(select(PrivilegedEmail).where(PrivilegedEmail.email == user.email))
        is_privileged = privileged_result.scalar_one_or_none() is not None
        
        if is_privileged:
            return {
                "user_type": "privileged",
                "sessions_today": 0,
                "daily_limit": None,
                "can_start_session": True,
                "remaining_sessions": None,  # Unlimited
                "upgrade_prompt_needed": False,
                "message": "Privileged user - unlimited access"
            }
        
        # Check for active subscription
        subscription_access = subscription_service.get_user_access_level(user_id, user.email, db)
        
        if subscription_access["unlimited_sessions"]:
            return {
                "user_type": "premium",
                "plan_type": subscription_access["plan_type"],
                "sessions_today": 0,
                "daily_limit": None,
                "can_start_session": True,
                "remaining_sessions": None,  # Unlimited
                "upgrade_prompt_needed": False,
                "subscription_expires": subscription_access.get("expires_at"),
                "message": f"Premium user ({subscription_access['plan_type']}) - unlimited access"
            }
        
        # Free tier logic with carry forward
        try:
            from free_tier_session_service import free_tier_service
            free_tier_status = free_tier_service.get_user_session_status(user_id, user.email, db)
            
            return {
                "user_type": "free_tier",
                "sessions_today": 0,  # Not tracking daily, tracking by cycle
                "daily_limit": None,
                "can_start_session": free_tier_status["sessions_available"] > 0,
                "remaining_sessions": free_tier_status["sessions_available"],
                "upgrade_prompt_needed": free_tier_status["upgrade_prompt_needed"],
                "free_tier_info": {
                    "is_initial_period": free_tier_status["is_initial_period"],
                    "sessions_used_this_cycle": free_tier_status["sessions_used_this_cycle"],
                    "carry_forward_sessions": free_tier_status["carry_forward_sessions"],
                    "cycle_end_date": free_tier_status["cycle_end_date"],
                    "next_allocation_date": free_tier_status["next_allocation_date"],
                    "total_sessions_completed": free_tier_status.get("total_sessions_completed", 0)
                },
                "message": f"Free tier - {free_tier_status['sessions_available']} sessions available"
            }
        except ImportError as e:
            logger.error(f"Free tier service import error: {e}")
            # Fallback to basic free tier logic
            return {
                "user_type": "free_tier",
                "sessions_today": 0,
                "daily_limit": 10,
                "can_start_session": True,
                "remaining_sessions": 10,
                "upgrade_prompt_needed": False,
                "message": "Free tier - basic allocation (service loading...)"
            }
    finally:
        db.close()

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
    """Temporary endpoint for current session status - system now uses adaptive-only sessions"""
    try:
        # System is now adaptive-only, no legacy in-memory sessions
        return {
            "has_active_session": False,
            "session_id": None,
            "message": "No active session found - system uses adaptive sessions only"
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
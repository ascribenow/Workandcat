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
    async for db in get_database():
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or not user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        return user

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Twelvr API is running - cleaned version"}

# Authentication endpoints
@app.post("/api/auth/signup")
async def signup(signup_data: SignupRequest):
    async for db in get_database():
        # Check if user exists
        result = await db.execute(select(User).where(User.email == signup_data.email))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Hash password
        password_hash = bcrypt.hashpw(signup_data.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Generate referral code
        referral_code = await referral_service.generate_referral_code(db)
        
        # Create user
        user = User(
            id=str(uuid.uuid4()),
            email=signup_data.email,
            full_name=signup_data.full_name,
            password_hash=password_hash,
            referral_code=referral_code
        )
        
        db.add(user)
        await db.commit()
        
        # Create access token
        access_token = create_access_token(data={"sub": user.id})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "is_admin": user.is_admin
            }
        }

@app.post("/api/auth/login")
async def login(login_data: LoginRequest):
    async for db in get_database():
        result = await db.execute(select(User).where(User.email == login_data.email))
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
                "is_admin": user.is_admin
            }
        }

@app.get("/api/auth/me")
async def get_me(user_id: str = Depends(get_current_user)):
    async for db in get_database():
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_admin": user.is_admin
        }

# Questions endpoints
@app.get("/api/questions")
async def get_questions(
    category: Optional[str] = None,
    limit: int = 50,
    user_id: str = Depends(get_current_user)
):
    async for db in get_database():
        query = select(Question).where(Question.is_active == True)
        
        if category:
            query = query.where(Question.category == category)
        
        query = query.limit(limit)
        result = await db.execute(query)
        questions = result.scalars().all()
        
        return [
            QuestionResponse(
                id=q.id,
                stem=q.stem or "",
                right_answer=q.right_answer or "",
                category=q.category or "",
                subcategory=q.subcategory or "",
                type_of_question=q.type_of_question or "",
                difficulty_level=q.difficulty_level or "",
                difficulty_score=float(q.difficulty_score or 0),
                concept_keywords=q.concept_keywords or [],
                core_concepts=q.core_concepts or [],
                solution_method=q.solution_method or "",
                operations_required=q.operations_required or [],
                has_image=q.has_image or False,
                image_url=q.image_url,
                snap_read=q.snap_read,
                solution_approach=q.solution_approach,
                detailed_solution=q.detailed_solution,
                principle_to_remember=q.principle_to_remember
            ) for q in questions
        ]

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
    async for db in get_database():
        result = await regular_questions_enrichment_service.get_enrichment_status(db)
        return result

@app.post("/api/admin/regular/trigger-enrichment")
async def admin_trigger_regular_enrichment(admin_user: User = Depends(get_current_admin_user)):
    async for db in get_database():
        result = await regular_questions_enrichment_service.trigger_manual_enrichment(db)
        return result

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
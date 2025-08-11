from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
import os
import uuid
import logging
import json
from emergentintegrations.llm.chat import LlmChat, UserMessage
from docx import Document
import io

# Import our professional auth service
from auth_service import AuthService, User, UserCreate, UserLogin, TokenResponse, require_auth, require_admin, ADMIN_EMAIL

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# LLM Chat setup
llm_api_key = os.environ.get('EMERGENT_LLM_KEY')

# Initialize Auth Service
auth_service = AuthService()

# Canonical Taxonomy (Locked)
CANONICAL_TAXONOMY = {
    "Arithmetic": {
        "Time–Speed–Distance (TSD)": ["Basic TSD", "Relative Speed (opposite & same direction)", "Circular Track Motion", "Boats & Streams", "Trains", "Races & Games of Chase"],
        "Time & Work": ["Work–Time–Efficiency Basics", "Pipes & Cisterns (Inlet/Outlet)", "Work Equivalence (men/women/children/machines)"],
        "Ratio–Proportion–Variation": ["Simple Ratios", "Compound Ratios", "Direct & Inverse Variation", "Partnership Problems"],
        "Percentages": ["Basic Percentages", "Percentage Change (Increase/Decrease)", "Successive Percentage Change"],
        "Averages & Alligation": ["Basic Averages", "Weighted Averages", "Alligation Rule (Mixture of 2 or more entities)"],
        "Profit–Loss–Discount (PLD)": ["Basic PLD", "Successive PLD", "Marked Price & Cost Price Relations", "Discount Chains"],
        "Simple & Compound Interest (SI–CI)": ["Basic SI & CI", "Difference between SI & CI", "Fractional Time Period CI"],
        "Mixtures & Solutions": ["Replacement Problems", "Concentration Change", "Solid–Liquid–Gas Mixtures"]
    },
    "Algebra": {
        "Linear Equations": ["Two-variable systems", "Three-variable systems", "Special cases (dependent/inconsistent systems)"],
        "Quadratic Equations": ["Roots & Nature of Roots", "Sum & Product of Roots", "Maximum/Minimum values"],
        "Inequalities": ["Linear Inequalities", "Quadratic Inequalities", "Modulus/Absolute Value"],
        "Progressions": ["Arithmetic Progression (AP)", "Geometric Progression (GP)", "Harmonic Progression (HP)", "Mixed Progressions"],
        "Functions & Graphs": ["Types of Functions (linear, quadratic, polynomial, modulus, step)", "Transformations (shifts, reflections, stretches)", "Domain–Range", "Composition & Inverse Functions"],
        "Logarithms & Exponents": ["Basic Properties of Logs", "Change of Base Formula", "Solving Log Equations", "Surds & Indices"],
        "Special Algebraic Identities": ["Expansion & Factorisation", "Cubes & Squares", "Binomial Theorem (Basic)"]
    },
    "Geometry & Mensuration": {
        "Triangles": ["Properties (Angles, Sides, Medians, Bisectors)", "Congruence & Similarity", "Pythagoras & Converse", "Inradius, Circumradius, Orthocentre"],
        "Circles": ["Tangents & Chords", "Angles in a Circle", "Cyclic Quadrilaterals"],
        "Polygons": ["Regular Polygons", "Interior/Exterior Angles"],
        "Coordinate Geometry": ["Distance, Section Formula, Midpoint", "Equation of a Line", "Slope & Intercepts", "Circles in Coordinate Plane", "Parabola, Ellipse, Hyperbola (basic properties only)"],
        "Mensuration (2D & 3D)": ["Areas (triangle, rectangle, trapezium, circle, sector)", "Volumes (cube, cuboid, cylinder, cone, sphere, hemisphere)", "Surface Areas"],
        "Trigonometry in Geometry": ["Heights & Distances", "Basic Trigonometric Ratios"]
    },
    "Number System": {
        "Divisibility": ["Basic Divisibility Rules", "Factorisation of Integers"],
        "HCF–LCM": ["Euclidean Algorithm", "Product of HCF & LCM"],
        "Remainders & Modular Arithmetic": ["Basic Remainder Theorem", "Chinese Remainder Theorem", "Cyclicity of Remainders"],
        "Base Systems": ["Conversion between bases", "Arithmetic in different bases"],
        "Digit Properties": ["Sum of Digits, Last Digit Patterns", "Palindromes, Repetitive Digits"]
    },
    "Modern Math": {
        "Permutation–Combination (P&C)": ["Basic Counting Principles", "Circular Permutations", "Permutations with Repetition/Restrictions", "Combinations with Repetition/Restrictions"],
        "Probability": ["Classical Probability", "Conditional Probability", "Bayes' Theorem"],
        "Set Theory & Venn Diagrams": ["Union–Intersection", "Complement & Difference of Sets", "Problems on 2–3 sets"]
    }
}

app = FastAPI(title="CAT Preparation API", version="2.0.0", description="Professional CAT Prep Platform with Firebase Auth")

# Add CORS middleware immediately after app creation
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter(prefix="/api")

# Updated Models
class Question(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    options: Optional[List[str]] = None
    correct_answer: str
    explanation: str
    section: str = "QA"
    category: str
    sub_category: str
    difficulty_level: str  # Easy/Medium/Difficult
    importance_level: int  # 1-10
    frequency_band: str  # High/Medium/Low
    learning_impact_score: float
    question_type: str  # MCQ/NAT
    year: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None  # User ID who created the question

class QuestionCreate(BaseModel):
    text: str
    options: Optional[List[str]] = None
    correct_answer: str
    explanation: str
    category: str
    sub_category: str
    year: Optional[int] = None

class UserProgress(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    question_id: str
    attempted_at: datetime = Field(default_factory=datetime.utcnow)
    user_answer: str
    is_correct: Optional[bool] = None
    time_taken: int  # seconds
    
class StudyPlan(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    day: int  # 1-90
    date: datetime
    recommended_questions: List[str]  # question IDs
    completed_questions: List[str] = []
    score: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class PasswordResetRequest(BaseModel):
    email: EmailStr

# LLM Question Analysis
async def analyze_question_with_llm(question_text: str, category: str, sub_category: str) -> Dict[str, Any]:
    """Use LLM to analyze question and assign metadata"""
    try:
        chat = LlmChat(
            api_key=llm_api_key,
            session_id=f"question_analysis_{uuid.uuid4()}",
            system_message="""You are an expert CAT exam analyzer. Analyze the given quantitative aptitude question and provide exact metadata.

CANONICAL TAXONOMY CATEGORIES:
Arithmetic: Time–Speed–Distance (TSD), Time & Work, Ratio–Proportion–Variation, Percentages, Averages & Alligation, Profit–Loss–Discount (PLD), Simple & Compound Interest (SI–CI), Mixtures & Solutions

Algebra: Linear Equations, Quadratic Equations, Inequalities, Progressions, Functions & Graphs, Logarithms & Exponents, Special Algebraic Identities

Geometry & Mensuration: Triangles, Circles, Polygons, Coordinate Geometry, Mensuration (2D & 3D), Trigonometry in Geometry

Number System: Divisibility, HCF–LCM, Remainders & Modular Arithmetic, Base Systems, Digit Properties

Modern Math: Permutation–Combination (P&C), Probability, Set Theory & Venn Diagrams

RETURN ONLY A JSON with these exact keys:
{
  "difficulty_level": "Easy|Medium|Difficult",
  "importance_level": 1-10 integer,
  "frequency_band": "High|Medium|Low",
  "learning_impact_score": 0.0-10.0 float,
  "question_type": "MCQ|NAT"
}"""
        ).with_model("openai", "gpt-4o-mini")

        user_message = UserMessage(
            text=f"Question Text: {question_text}\nCategory: {category}\nSub-Category: {sub_category}\n\nAnalyze this question."
        )

        response = await chat.send_message(user_message)
        
        # Parse JSON response
        try:
            analysis = json.loads(response)
            return analysis
        except json.JSONDecodeError:
            # Fallback defaults
            return {
                "difficulty_level": "Medium",
                "importance_level": 5,
                "frequency_band": "Medium",
                "learning_impact_score": 5.0,
                "question_type": "MCQ"
            }
    except Exception as e:
        logging.error(f"LLM analysis error: {e}")
        return {
            "difficulty_level": "Medium",
            "importance_level": 5,
            "frequency_band": "Medium",
            "learning_impact_score": 5.0,
            "question_type": "MCQ"
        }

# Routes
@api_router.get("/")
async def root():
    return {"message": "CAT Preparation API v2.0", "admin_email": ADMIN_EMAIL}

@api_router.get("/taxonomy")
async def get_taxonomy():
    """Get canonical taxonomy"""
    return {"taxonomy": CANONICAL_TAXONOMY}

# Professional Authentication Routes
@api_router.post("/auth/register", response_model=TokenResponse)
async def register_user(user_data: UserCreate):
    """Register a new user with professional authentication"""
    return await auth_service.register_user(user_data)

@api_router.post("/auth/login", response_model=TokenResponse)
async def login_user(login_data: UserLogin):
    """Login user with professional authentication"""
    return await auth_service.login_user(login_data)

@api_router.post("/auth/password-reset")
async def request_password_reset(reset_data: PasswordResetRequest):
    """Request password reset"""
    return await auth_service.reset_password_request(reset_data.email)

@api_router.get("/auth/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(require_auth)):
    """Get current user information"""
    return current_user

# Legacy auth routes for backward compatibility
@api_router.post("/register")
async def legacy_register(user_data: UserCreate):
    """Legacy register endpoint"""
    return await register_user(user_data)

@api_router.post("/login") 
async def legacy_login(login_data: UserLogin):
    """Legacy login endpoint"""
    return await login_user(login_data)

# Question Management (Protected Routes)
@api_router.post("/questions")
async def create_question(question_data: QuestionCreate, current_user: User = Depends(require_auth)):
    """Create a new question (authenticated users only)"""
    # Validate category and sub-category
    if question_data.category not in CANONICAL_TAXONOMY:
        raise HTTPException(status_code=400, detail="Invalid category")
    if question_data.sub_category not in CANONICAL_TAXONOMY[question_data.category]:
        raise HTTPException(status_code=400, detail="Invalid sub-category")
    
    # Use LLM to analyze question
    analysis = await analyze_question_with_llm(
        question_data.text, 
        question_data.category, 
        question_data.sub_category
    )
    
    question = Question(
        text=question_data.text,
        options=question_data.options,
        correct_answer=question_data.correct_answer,
        explanation=question_data.explanation,
        category=question_data.category,
        sub_category=question_data.sub_category,
        year=question_data.year,
        created_by=current_user.id,
        **analysis
    )
    
    await db.questions.insert_one(question.model_dump())
    return {"message": "Question created successfully", "question": question}

@api_router.get("/questions")
async def get_questions(
    category: Optional[str] = None,
    sub_category: Optional[str] = None,
    difficulty: Optional[str] = None,
    limit: int = 50
):
    """Get questions (public access for practice)"""
    filter_query = {}
    if category:
        filter_query["category"] = category
    if sub_category:
        filter_query["sub_category"] = sub_category
    if difficulty:
        filter_query["difficulty_level"] = difficulty
    
    questions = await db.questions.find(filter_query).limit(limit).to_list(length=None)
    # Convert ObjectId to string for JSON serialization
    for question in questions:
        if "_id" in question:
            del question["_id"]
    return {"questions": questions}

@api_router.get("/questions/{question_id}")
async def get_question(question_id: str):
    """Get specific question"""
    question = await db.questions.find_one({"id": question_id})
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    if "_id" in question:
        del question["_id"]
    return {"question": question}

# Progress Tracking (Protected)
@api_router.post("/progress")
async def submit_answer(progress_data: UserProgress, current_user: User = Depends(require_auth)):
    """Submit answer (authenticated users only)"""
    # Ensure user can only submit for themselves
    if progress_data.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Can only submit answers for yourself")
    
    # Check if answer is correct
    question = await db.questions.find_one({"id": progress_data.question_id})
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    progress_data.is_correct = progress_data.user_answer == question["correct_answer"]
    
    await db.user_progress.insert_one(progress_data.model_dump())
    return {
        "message": "Answer submitted",
        "is_correct": progress_data.is_correct,
        "correct_answer": question["correct_answer"],
        "explanation": question["explanation"]
    }

@api_router.get("/progress/{user_id}")
async def get_user_progress(user_id: str, current_user: User = Depends(require_auth)):
    """Get user progress (users can only access their own progress, admins can access all)"""
    if user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")
    
    progress = await db.user_progress.find({"user_id": user_id}).to_list(length=None)
    
    # Remove ObjectId for JSON serialization
    for p in progress:
        if "_id" in p:
            del p["_id"]
    
    # Calculate stats
    total_questions = len(progress)
    correct_answers = sum(1 for p in progress if p["is_correct"])
    accuracy = (correct_answers / total_questions * 100) if total_questions > 0 else 0
    
    return {
        "progress": progress,
        "stats": {
            "total_questions": total_questions,
            "correct_answers": correct_answers,
            "accuracy": round(accuracy, 2)
        }
    }

# Study Plan Generation (Protected)
@api_router.post("/study-plan/{user_id}")
async def generate_study_plan(user_id: str, current_user: User = Depends(require_auth)):
    """Generate 90-day study plan (users can only generate for themselves)"""
    if user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")
    
    start_date = datetime.utcnow()
    
    # Generate plans for 90 days
    all_questions = await db.questions.find().to_list(length=None)
    
    for day in range(1, 91):
        plan_date = start_date + timedelta(days=day-1)
        
        # Simple algorithm: rotate through different categories and difficulties
        category_keys = list(CANONICAL_TAXONOMY.keys())
        target_category = category_keys[day % len(category_keys)]
        
        # Get questions for this category
        daily_questions = [q for q in all_questions if q["category"] == target_category][:5]
        question_ids = [q["id"] for q in daily_questions]
        
        study_plan = StudyPlan(
            user_id=user_id,
            day=day,
            date=plan_date,
            recommended_questions=question_ids
        )
        
        await db.study_plans.insert_one(study_plan.model_dump())
    
    return {"message": "90-day study plan generated successfully"}

@api_router.get("/study-plan/{user_id}")
async def get_study_plan(user_id: str, current_user: User = Depends(require_auth), day: Optional[int] = None):
    """Get study plan (users can only access their own)"""
    if user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")
    
    filter_query = {"user_id": user_id}
    if day:
        filter_query["day"] = day
    
    plans = await db.study_plans.find(filter_query).sort("day", 1).to_list(length=None)
    # Remove ObjectId for JSON serialization
    for plan in plans:
        if "_id" in plan:
            del plan["_id"]
    return {"study_plans": plans}

# Analytics (Protected)
@api_router.get("/analytics/{user_id}")
async def get_analytics(user_id: str, current_user: User = Depends(require_auth)):
    """Get detailed analytics (users can only access their own)"""
    if user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")
    
    progress = await db.user_progress.find({"user_id": user_id}).to_list(length=None)
    
    # Category-wise performance
    category_stats = {}
    for p in progress:
        question = await db.questions.find_one({"id": p["question_id"]})
        if question:
            cat = question["category"]
            if cat not in category_stats:
                category_stats[cat] = {"total": 0, "correct": 0}
            category_stats[cat]["total"] += 1
            if p["is_correct"]:
                category_stats[cat]["correct"] += 1
    
    # Calculate accuracy for each category
    for cat in category_stats:
        total = category_stats[cat]["total"]
        correct = category_stats[cat]["correct"]
        category_stats[cat]["accuracy"] = round((correct / total * 100) if total > 0 else 0, 2)
    
    return {
        "category_performance": category_stats,
        "total_questions_attempted": len(progress),
        "overall_accuracy": round(sum(1 for p in progress if p["is_correct"]) / len(progress) * 100 if progress else 0, 2)
    }

# Admin-only Routes
@api_router.post("/admin/upload-pyq")
async def upload_pyq(file: UploadFile = File(...), year: int = Form(...), current_user: User = Depends(require_admin)):
    """Upload PYQ as Word document (admin only)"""
    if not file.filename.endswith(('.docx', '.doc')):
        raise HTTPException(status_code=400, detail="Only Word documents are allowed")
    
    try:
        # Read the uploaded file
        contents = await file.read()
        
        # Parse Word document
        doc = Document(io.BytesIO(contents))
        
        # Extract text from document
        full_text = []
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                full_text.append(paragraph.text.strip())
        
        document_text = "\n".join(full_text)
        
        # Use LLM to extract questions from the document
        chat = LlmChat(
            api_key=llm_api_key,
            session_id=f"pyq_extraction_{uuid.uuid4()}",
            system_message="""You are an expert at extracting CAT exam questions from documents.

Extract all quantitative aptitude questions from the given text and return them as a JSON array.

For each question, determine the category and sub-category from this taxonomy:
- Arithmetic: Time–Speed–Distance (TSD), Time & Work, Ratio–Proportion–Variation, Percentages, Averages & Alligation, Profit–Loss–Discount (PLD), Simple & Compound Interest (SI–CI), Mixtures & Solutions
- Algebra: Linear Equations, Quadratic Equations, Inequalities, Progressions, Functions & Graphs, Logarithms & Exponents, Special Algebraic Identities
- Geometry & Mensuration: Triangles, Circles, Polygons, Coordinate Geometry, Mensuration (2D & 3D), Trigonometry in Geometry
- Number System: Divisibility, HCF–LCM, Remainders & Modular Arithmetic, Base Systems, Digit Properties
- Modern Math: Permutation–Combination (P&C), Probability, Set Theory & Venn Diagrams

Return JSON array with this structure:
[
  {
    "text": "question text",
    "options": ["option1", "option2", "option3", "option4"] or null,
    "correct_answer": "correct answer",
    "explanation": "explanation",
    "category": "category name",
    "sub_category": "sub-category name"
  }
]"""
        ).with_model("openai", "gpt-4o")

        user_message = UserMessage(text=f"Extract questions from this document:\n\n{document_text}")
        response = await chat.send_message(user_message)
        
        # Parse questions and save to database
        try:
            extracted_questions = json.loads(response)
            created_questions = []
            
            for q_data in extracted_questions:
                if isinstance(q_data, dict) and 'text' in q_data:
                    # Use LLM to analyze each question
                    analysis = await analyze_question_with_llm(
                        q_data['text'], 
                        q_data.get('category', 'Arithmetic'), 
                        q_data.get('sub_category', 'Basic TSD')
                    )
                    
                    question = Question(
                        text=q_data['text'],
                        options=q_data.get('options'),
                        correct_answer=q_data['correct_answer'],
                        explanation=q_data.get('explanation', ''),
                        category=q_data['category'],
                        sub_category=q_data['sub_category'],
                        year=year,
                        created_by=current_user.id,
                        **analysis
                    )
                    
                    await db.questions.insert_one(question.model_dump())
                    created_questions.append(question.id)
            
            return {
                "message": f"Successfully extracted and saved {len(created_questions)} questions",
                "question_ids": created_questions
            }
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="Failed to parse extracted questions")
            
    except Exception as e:
        logging.error(f"PYQ upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@api_router.get("/admin/users")
async def get_all_users(current_user: User = Depends(require_admin)):
    """Get all users (admin only)"""
    users = await db.users.find({}, {"password_hash": 0}).to_list(length=None)
    for user in users:
        if "_id" in user:
            del user["_id"]
    return {"users": users}

@api_router.get("/admin/stats")
async def get_admin_stats(current_user: User = Depends(require_admin)):
    """Get admin dashboard stats"""
    total_users = await db.users.count_documents({})
    total_questions = await db.questions.count_documents({})
    total_attempts = await db.user_progress.count_documents({})
    
    return {
        "total_users": total_users,
        "total_questions": total_questions,
        "total_attempts": total_attempts,
        "admin_email": ADMIN_EMAIL
    }

# Legacy routes for backward compatibility
@api_router.post("/upload-pyq")
async def legacy_upload_pyq(file: UploadFile = File(...), year: int = Form(...)):
    """Legacy PYQ upload (will check for admin via legacy auth)"""
    # This would need additional admin check logic for legacy compatibility
    # For now, we'll redirect to the admin route
    raise HTTPException(status_code=401, detail="Please use /api/admin/upload-pyq with proper authentication")

# Include router
app.include_router(api_router)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 CAT Preparation API v2.0 Started")
    logger.info(f"📧 Admin Email: {ADMIN_EMAIL}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
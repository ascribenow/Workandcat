from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
import os
import uuid
import logging
import json
import bcrypt
from emergentintegrations.llm.chat import LlmChat, UserMessage
from docx import Document
import io

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# LLM Chat setup
llm_api_key = os.environ.get('EMERGENT_LLM_KEY')

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

app = FastAPI()
api_router = APIRouter(prefix="/api")

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    password_hash: str
    is_admin: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    study_plan_start_date: Optional[datetime] = None

class UserCreate(BaseModel):
    email: str
    name: str
    password: str
    is_admin: bool = False

class UserLogin(BaseModel):
    email: str
    password: str

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
    is_correct: bool
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

# Auth helpers
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

# Routes
@api_router.get("/")
async def root():
    return {"message": "CAT Preparation API"}

@api_router.get("/taxonomy")
async def get_taxonomy():
    """Get canonical taxonomy"""
    return {"taxonomy": CANONICAL_TAXONOMY}

# User Management
@api_router.post("/register")
async def register_user(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user = User(
        email=user_data.email,
        name=user_data.name,
        password_hash=hash_password(user_data.password),
        is_admin=user_data.is_admin
    )
    
    await db.users.insert_one(user.model_dump())
    return {"message": "User registered successfully", "user_id": user.id}

@api_router.post("/login")
async def login_user(login_data: UserLogin):
    user = await db.users.find_one({"email": login_data.email})
    if not user or not verify_password(login_data.password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    return {
        "message": "Login successful",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "is_admin": user["is_admin"]
        }
    }

# Question Management
@api_router.post("/questions")
async def create_question(question_data: QuestionCreate):
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
    question = await db.questions.find_one({"id": question_id})
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    if "_id" in question:
        del question["_id"]
    return {"question": question}

# Progress Tracking
@api_router.post("/progress")
async def submit_answer(progress_data: UserProgress):
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
async def get_user_progress(user_id: str):
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

# Study Plan Generation
@api_router.post("/study-plan/{user_id}")
async def generate_study_plan(user_id: str):
    """Generate 90-day study plan for user"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    start_date = datetime.utcnow()
    
    # Update user's study plan start date
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"study_plan_start_date": start_date}}
    )
    
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
async def get_study_plan(user_id: str, day: Optional[int] = None):
    filter_query = {"user_id": user_id}
    if day:
        filter_query["day"] = day
    
    plans = await db.study_plans.find(filter_query).sort("day", 1).to_list(length=None)
    return {"study_plans": plans}

# PYQ Upload (Word Document)
@api_router.post("/upload-pyq")
async def upload_pyq(file: UploadFile = File(...), year: int = Form(...)):
    """Upload PYQ as Word document and extract questions"""
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

# Analytics
@api_router.get("/analytics/{user_id}")
async def get_analytics(user_id: str):
    """Get detailed analytics for user"""
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

# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
"""
SQLite Database Configuration and Models for CAT Preparation Platform
Migrated from PostgreSQL to SQLite for simplicity and reliability
"""

from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, Numeric, DateTime, Date, JSON, ForeignKey, Index, BigInteger, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import uuid
import os
from dotenv import load_dotenv

load_dotenv()

# SQLite Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cat_preparation.db")

# Create SQLite engine with optimized settings
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for debugging
    connect_args={
        "check_same_thread": False,  # Allow SQLite to work with FastAPI
        "timeout": 20,  # 20 second timeout for database locks
        "isolation_level": None,  # Use autocommit mode for better concurrency
    },
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,   # Recycle connections every hour
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Database Models adapted for SQLite

class Topic(Base):
    """Topics table - canonical taxonomy structure"""
    __tablename__ = "topics"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    section = Column(String(10), default='QA', nullable=False)
    name = Column(Text, nullable=False)
    parent_id = Column(String(36), ForeignKey('topics.id'), nullable=True)
    slug = Column(String(255), unique=True, nullable=False)
    centrality = Column(Numeric(3, 2), default=0.5)  # 0-1 for Learning Impact static
    category = Column(String(50))  # A, B, C, D, E for canonical taxonomy
    
    # Relationships
    parent = relationship("Topic", remote_side=[id])
    children = relationship("Topic", back_populates="parent")
    questions = relationship("Question", back_populates="topic")


class Question(Base):
    """Questions table - main question bank with LLM enrichment"""
    __tablename__ = "questions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    topic_id = Column(String(36), ForeignKey('topics.id'), nullable=False)
    subcategory = Column(Text, nullable=False)
    type_of_question = Column(String(150))  # Specific question type within subcategory
    
    # Core question content
    stem = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)  # canonical answer
    solution_approach = Column(Text, nullable=True)
    detailed_solution = Column(Text, nullable=True)
    
    # Image support
    has_image = Column(Boolean, default=False)
    image_url = Column(Text, nullable=True)
    image_alt_text = Column(Text, nullable=True)
    
    # LLM-computed scores
    difficulty_score = Column(Numeric(3, 2), nullable=True)  # 1-5
    difficulty_band = Column(String(20), nullable=True)  # Easy|Medium|Difficult
    frequency_band = Column(String(20), nullable=True)  # High|Medium|Low
    frequency_notes = Column(Text, nullable=True)
    learning_impact = Column(Numeric(5, 2), nullable=True)  # 0-100
    learning_impact_band = Column(String(20), nullable=True)
    importance_index = Column(Numeric(5, 2), nullable=True)  # 0-100
    importance_band = Column(String(20), nullable=True)
    
    # Enhanced conceptual frequency analysis fields
    frequency_score = Column(Numeric(5, 4), default=0.0)  # New enhanced frequency score
    pyq_conceptual_matches = Column(Integer, default=0)
    total_pyq_analyzed = Column(Integer, default=0)
    top_matching_concepts = Column(Text, default='[]')  # JSON string for SQLite
    frequency_analysis_method = Column(String(50), default='subcategory')
    frequency_last_updated = Column(DateTime, nullable=True)
    pattern_keywords = Column(Text, default='[]')  # JSON string for SQLite
    pattern_solution_approach = Column(Text, nullable=True)
    pyq_occurrences_last_10_years = Column(Integer, default=0)
    total_pyq_count = Column(Integer, default=0)
    
    # Metadata
    video_url = Column(Text, nullable=True)
    tags = Column(Text, default='[]')  # JSON string for SQLite
    source = Column(String(20), default='Admin')  # Admin|PYQ|Mock|AI_GEN
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    topic = relationship("Topic", back_populates="questions")
    question_options = relationship("QuestionOption", back_populates="question")
    attempts = relationship("Attempt", back_populates="question")


class QuestionOption(Base):
    """Question options - cache of last MCQ set shown"""
    __tablename__ = "question_options"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id = Column(String(36), ForeignKey('questions.id'), nullable=False)
    choice_a = Column(Text, nullable=True)
    choice_b = Column(Text, nullable=True)
    choice_c = Column(Text, nullable=True)
    choice_d = Column(Text, nullable=True)
    correct_label = Column(String(1), nullable=False)  # A|B|C|D
    generated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    question = relationship("Question", back_populates="question_options")


# PYQ (Previous Year Questions) Tables

class PYQIngestion(Base):
    """PYQ ingestions - raw file stage"""
    __tablename__ = "pyq_ingestions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    upload_filename = Column(Text, nullable=False)
    storage_key = Column(Text, nullable=False)
    year = Column(Integer, nullable=True)
    slot = Column(String(10), nullable=True)  # A|B|C
    source_url = Column(Text, nullable=True)
    pages_count = Column(Integer, nullable=True)
    ocr_required = Column(Boolean, default=False)
    ocr_status = Column(String(20), default='pending')  # queued|running|done|failed
    parse_status = Column(String(20), default='pending')  # queued|running|done|failed
    parse_log = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    papers = relationship("PYQPaper", back_populates="ingestion")


class PYQPaper(Base):
    """PYQ papers - normalized paper record"""
    __tablename__ = "pyq_papers"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    year = Column(Integer, nullable=False)
    slot = Column(String(10), nullable=True)
    source_url = Column(Text, nullable=True)
    ingested_at = Column(DateTime, default=datetime.utcnow)
    ingestion_id = Column(String(36), ForeignKey('pyq_ingestions.id'), nullable=False)
    
    # Relationships
    ingestion = relationship("PYQIngestion", back_populates="papers")
    questions = relationship("PYQQuestion", back_populates="paper")


class PYQQuestion(Base):
    """PYQ questions - normalized, taxonomy-mapped items"""
    __tablename__ = "pyq_questions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    paper_id = Column(String(36), ForeignKey('pyq_papers.id'), nullable=False)
    topic_id = Column(String(36), ForeignKey('topics.id'), nullable=False)
    subcategory = Column(Text, nullable=False)
    type_of_question = Column(String(150))  # Specific question type within subcategory
    stem = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    tags = Column(Text, default='[]')  # JSON string for SQLite
    confirmed = Column(Boolean, default=False)  # human-verified mapping
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    paper = relationship("PYQPaper", back_populates="questions")
    topic = relationship("Topic")


# User Management Tables

class User(Base):
    """Users table with spending controls"""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    password_hash = Column(Text, nullable=False)
    tz = Column(String(50), default='Asia/Kolkata')
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Spending Controls
    spending_limit_monthly = Column(Numeric(10, 2), default=10.0)  # Monthly spending limit in USD
    spending_limit_enabled = Column(Boolean, default=True)  # Enable/disable spending controls
    current_month_spending = Column(Numeric(10, 2), default=0.0)  # Current month's spending
    last_spending_reset = Column(Date, default=lambda: datetime.utcnow().date())  # Last reset date
    spending_notifications = Column(Boolean, default=True)  # Enable spending notifications
    spending_alert_threshold = Column(Numeric(3, 2), default=0.8)  # Alert at 80% of limit
    
    # Relationships
    diagnostics = relationship("Diagnostic", back_populates="user")
    attempts = relationship("Attempt", back_populates="user")
    mastery = relationship("Mastery", back_populates="user")
    plans = relationship("Plan", back_populates="user")
    sessions = relationship("Session", back_populates="user")
    usage_logs = relationship("UsageLog", back_populates="user")


class UsageLog(Base):
    """Track API usage and costs per user"""
    __tablename__ = "usage_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    service_type = Column(String(50), nullable=False)  # 'llm_enrichment', 'mcq_generation', 'session_analysis'
    api_provider = Column(String(50), nullable=False)  # 'openai', 'anthropic', 'emergent'
    model_used = Column(String(100), nullable=False)  # 'gpt-4o', 'claude-3', etc.
    tokens_used = Column(Integer, default=0)  # Total tokens consumed
    estimated_cost = Column(Numeric(10, 4), default=0.0)  # Estimated cost in USD
    operation_type = Column(String(100), nullable=False)  # 'question_enrichment', 'mcq_options', etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata = Column(Text, default='{}')  # JSON string for additional data
    
    # Relationships
    user = relationship("User", back_populates="usage_logs")


# Diagnostic System Tables

class DiagnosticSet(Base):
    """Diagnostic sets - fixed 25-Q Day-0 test"""
    __tablename__ = "diagnostic_sets"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    meta = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    questions = relationship("DiagnosticSetQuestion", back_populates="diagnostic_set")
    diagnostics = relationship("Diagnostic", back_populates="diagnostic_set")


class DiagnosticSetQuestion(Base):
    """Diagnostic set questions - fixed question order"""
    __tablename__ = "diagnostic_set_questions"
    
    set_id = Column(String(36), ForeignKey('diagnostic_sets.id'), primary_key=True)
    question_id = Column(String(36), ForeignKey('questions.id'), primary_key=True)
    seq = Column(Integer, nullable=False)  # question sequence in diagnostic
    
    # Relationships
    diagnostic_set = relationship("DiagnosticSet", back_populates="questions")
    question = relationship("Question")


class Diagnostic(Base):
    """Diagnostics - one per user per attempt"""
    __tablename__ = "diagnostics"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    set_id = Column(String(36), ForeignKey('diagnostic_sets.id'), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    result = Column(JSON, default=dict)  # per-topic accuracy/time; readiness band
    initial_capability = Column(JSON, default=dict)  # per sub-category & difficulty
    
    # Relationships
    user = relationship("User", back_populates="diagnostics")
    diagnostic_set = relationship("DiagnosticSet", back_populates="diagnostics")


# Attempt and Progress Tracking

class Attempt(Base):
    """Attempts - every user × question interaction"""
    __tablename__ = "attempts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    question_id = Column(String(36), ForeignKey('questions.id'), nullable=False)
    attempt_no = Column(Integer, nullable=False)  # 1, 2, 3
    context = Column(String(20), nullable=False)  # diagnostic|daily|sandbox
    options = Column(JSON, default=dict)  # the 4 choices shown
    user_answer = Column(Text, nullable=False)
    correct = Column(Boolean, nullable=False)
    time_sec = Column(Integer, nullable=False)
    hint_used = Column(Boolean, default=False)
    model_feedback = Column(Text, nullable=True)
    misconception_tag = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="attempts")
    question = relationship("Question", back_populates="attempts")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_attempts_user_question', 'user_id', 'question_id'),
        Index('idx_attempts_created_at', 'created_at'),
    )


class Mastery(Base):
    """Mastery - user × topic snapshots"""
    __tablename__ = "mastery"
    
    user_id = Column(String(36), ForeignKey('users.id'), primary_key=True)
    topic_id = Column(String(36), ForeignKey('topics.id'), primary_key=True)
    exposure_score = Column(Numeric(5, 2), default=0)
    accuracy_easy = Column(Numeric(3, 2), default=0)
    accuracy_med = Column(Numeric(3, 2), default=0)
    accuracy_hard = Column(Numeric(3, 2), default=0)
    efficiency_score = Column(Numeric(5, 2), default=0)
    mastery_pct = Column(Numeric(3, 2), default=0)  # 0-1
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="mastery")
    topic = relationship("Topic")


# Study Planning Tables

class Plan(Base):
    """Plans - 90-day engine plan"""
    __tablename__ = "plans"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    track = Column(String(20), nullable=False)  # Beginner|Intermediate|Good
    daily_minutes_weekday = Column(Integer, default=30)
    daily_minutes_weekend = Column(Integer, default=60)
    start_date = Column(Date, nullable=False)
    status = Column(String(20), default='active')  # active|paused|completed
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="plans")
    plan_units = relationship("PlanUnit", back_populates="plan")


class PlanUnit(Base):
    """Plan units - atomic day items"""
    __tablename__ = "plan_units"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id = Column(String(36), ForeignKey('plans.id'), nullable=False)
    planned_for = Column(Date, nullable=False)
    topic_id = Column(String(36), ForeignKey('topics.id'), nullable=False)
    unit_kind = Column(String(20), nullable=False)  # read|examples|practice|review|mock
    target_count = Column(Integer, default=1)
    generated_payload = Column(JSON, default=dict)  # question_ids
    status = Column(String(20), default='pending')  # pending|in_progress|done|skipped
    actual_stats = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    plan = relationship("Plan", back_populates="plan_units")
    topic = relationship("Topic")


# Session Management

class Session(Base):
    """Sessions - study session tracking"""
    __tablename__ = "sessions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    duration_sec = Column(Integer, nullable=True)
    units = Column(Text, default='[]')  # JSON string for SQLite compatibility
    notes = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="sessions")


class MasteryHistory(Base):
    """Store daily mastery history per user per subcategory (v1.3 requirement)"""
    __tablename__ = "mastery_history"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    subcategory = Column(String(100), nullable=False)
    mastery_score = Column(Numeric(3, 2))
    recorded_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes for efficient queries
    __table_args__ = (
        Index('idx_mastery_history_user_date', 'user_id', 'recorded_date'),
        Index('idx_mastery_history_subcategory', 'subcategory'),
    )


class PYQFiles(Base):
    """Track uploaded PYQ files and their processing status (v1.3 requirement)"""
    __tablename__ = "pyq_files"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(Text, nullable=False)
    year = Column(Integer)
    upload_date = Column(DateTime, default=datetime.utcnow)
    processing_status = Column(String(20), default="pending")
    file_size = Column(BigInteger)
    storage_path = Column(Text)
    file_metadata = Column(JSON)
    
    # Indexes for efficient queries
    __table_args__ = (
        Index('idx_pyq_files_year', 'year'),
        Index('idx_pyq_files_status', 'processing_status'),
    )


# Database utility functions

def get_db():
    """Get database session for FastAPI dependency injection"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_database():
    """Initialize database with tables"""
    Base.metadata.create_all(bind=engine)


# Dependency for FastAPI
def get_database():
    """Alternative database session getter"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Compatibility layer for async code migration
class AsyncSession:
    """Compatibility wrapper to help with async to sync migration"""
    def __init__(self, session):
        self._session = session
    
    def add(self, instance):
        return self._session.add(instance)
    
    async def commit(self):
        return self._session.commit()
    
    async def flush(self):
        return self._session.flush()
    
    async def execute(self, statement):
        return self._session.execute(statement)
    
    async def scalar(self, statement):
        return self._session.scalar(statement)
    
    def close(self):
        return self._session.close()
    
    async def refresh(self, instance):
        return self._session.refresh(instance)
    
    async def rollback(self):
        return self._session.rollback()


def get_async_compatible_db():
    """Get database session with async compatibility wrapper"""
    db = SessionLocal()
    try:
        yield AsyncSession(db)
    finally:
        db.close()
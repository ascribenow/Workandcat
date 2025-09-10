"""
PostgreSQL Database Configuration and Models for CAT Preparation Platform
Production-ready with managed PostgreSQL (Neon/Supabase)
"""

from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, Numeric, DateTime, Date, JSON, ForeignKey, Index, BigInteger, func, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, validates
from datetime import datetime
import uuid
import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Configure logger
logger = logging.getLogger(__name__)

# Production-ready PostgreSQL Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/cat_preparation")

# Detect database type for appropriate configuration
is_postgres = DATABASE_URL.startswith('postgresql://') or DATABASE_URL.startswith('postgres://')
is_sqlite = DATABASE_URL.startswith('sqlite:///')

if is_postgres:
    # PostgreSQL Configuration (Production)
    engine = create_engine(
        DATABASE_URL,
        echo=False,  # Set to True for debugging
        pool_size=10,  # Connection pool size
        max_overflow=20,  # Maximum overflow connections
        pool_pre_ping=True,  # Verify connections before use
        pool_recycle=3600,   # Recycle connections every hour
        connect_args={
            "sslmode": "require",  # Require SSL for security
            "application_name": "twelvr_cat_prep",
        }
    )
    print("🐘 Using PostgreSQL database (Production)")
else:
    # SQLite Configuration (Development fallback)
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        connect_args={
            "check_same_thread": False,
            "timeout": 20,
            "isolation_level": None,
        },
        pool_pre_ping=True,
        pool_recycle=3600,
    )
    print("📁 Using SQLite database (Development)")

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
    # questions relationship REMOVED as per requirements


class Question(Base):
    """Questions table - main question bank with LLM enrichment"""
    __tablename__ = "questions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # topic_id REMOVED as per requirements
    category = Column(String(100), nullable=True)  # Main category (Arithmetic, Algebra, etc.)
    subcategory = Column(Text, nullable=False)
    type_of_question = Column(String(150))  # Specific question type within subcategory
    
    # Core question content
    stem = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)  # canonical answer from CSV
    right_answer = Column(Text, nullable=True)  # Enhanced answer from LLM enrichment
    solution_approach = Column(Text, nullable=True)  # From CSV upload
    detailed_solution = Column(Text, nullable=True)  # From CSV upload
    principle_to_remember = Column(Text, nullable=True)  # From CSV upload
    snap_read = Column(Text, nullable=True)  # NEW: From CSV upload, display above solution_approach
    
    # Image support
    has_image = Column(Boolean, default=False)
    image_url = Column(Text, nullable=True)  # From CSV upload
    # image_alt_text REMOVED as per requirements
    
    # LLM-computed difficulty scores
    difficulty_score = Column(Numeric(3, 2), nullable=True)  # 1-5, populated by LLM enrichment
    difficulty_band = Column(String(20), nullable=True)  # Easy|Medium|Hard, populated by LLM enrichment
    # llm_difficulty_assessment_method REMOVED as per requirements
    # llm_assessment_attempts REMOVED as per requirements
    # last_llm_assessment_date REMOVED as per requirements
    # llm_assessment_error REMOVED as per requirements
    
    # Frequency & Impact scores
    frequency_band = Column(String(20), nullable=True)  # High|Medium|Low
    learning_impact = Column(Numeric(5, 2), nullable=True)  # 0-100
    learning_impact_band = Column(String(20), nullable=True)
    importance_index = Column(Numeric(5, 2), nullable=True)  # 0-100
    importance_band = Column(String(20), nullable=True)
    
    # Enhanced frequency analysis fields
    frequency_score = Column(Numeric(5, 4), default=0.0)  # Enhanced frequency score
    pyq_frequency_score = Column(Numeric(5, 4), default=0.0)  # PYQ frequency score
    pyq_conceptual_matches = Column(Integer, default=0)
    # total_pyq_analyzed REMOVED as per requirements
    top_matching_concepts = Column(Text, default='[]')  # JSON string for SQLite
    # frequency_analysis_method REMOVED as per requirements
    # frequency_last_updated REMOVED as per requirements
    # pyq_occurrences_last_10_years REMOVED as per requirements
    # total_pyq_count REMOVED as per requirements
    
    # MCQ Options (from CSV upload)
    mcq_options = Column(Text, nullable=True)  # From CSV upload
    
    # LLM enrichment fields (same logic as PYQ questions)
    quality_verified = Column(Boolean, default=False)  # Quality gate from LLM enrichment
    core_concepts = Column(Text, nullable=True)  # JSON: extracted mathematical concepts
    solution_method = Column(String(200), nullable=True)  # Primary solution approach from LLM
    concept_difficulty = Column(Text, nullable=True)  # JSON: difficulty indicators from LLM
    operations_required = Column(Text, nullable=True)  # JSON: mathematical operations from LLM
    problem_structure = Column(String(100), nullable=True)  # Structure pattern type from LLM
    concept_keywords = Column(Text, nullable=True)  # JSON: searchable keywords from LLM
    
    # Metadata
    source = Column(String(20), default='Admin')  # Admin|PYQ|Mock|AI_GEN
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships REMOVED as per requirements
    # topic = relationship("Topic", back_populates="questions") - REMOVED
    # question_options = relationship("QuestionOption", back_populates="question") - REMOVED  
    # attempts = relationship("Attempt", back_populates="question") - REMOVED

    @validates('difficulty_band')
    def validate_difficulty_band(self, key, difficulty_band):
        """Validate difficulty band values"""
        if difficulty_band is not None and difficulty_band not in ['Easy', 'Medium', 'Hard']:
            raise ValueError("Difficulty band must be Easy, Medium, or Hard")
        return difficulty_band

    # Removed is_active validator and ensure_llm_difficulty_assessment method as per requirements


# QuestionOption model REMOVED as per requirements - no more relationships

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
    """PYQ questions - enhanced with LLM enrichment and conceptual analysis"""
    __tablename__ = "pyq_questions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    paper_id = Column(String(36), ForeignKey('pyq_papers.id'), nullable=False)
    # topic_id REMOVED - PYQ questions don't need topic relationships
    category = Column(String(100), nullable=True)  # Main category (Arithmetic, Algebra, etc.)
    subcategory = Column(Text, nullable=False)
    type_of_question = Column(String(150))  # Specific question type within subcategory
    stem = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Enhanced PYQ fields for LLM enrichment and conceptual analysis
    is_active = Column(Boolean, default=False)  # Enable/disable for analysis
    difficulty_band = Column(String(20), nullable=True)  # Easy|Medium|Hard (LLM-assessed)
    difficulty_score = Column(Numeric(3, 2), nullable=True)  # 1-5 numeric scale
    quality_verified = Column(Boolean, default=False)  # Quality gate for reliability
    last_updated = Column(DateTime, nullable=True)  # Track processing dates
    concept_extraction_status = Column(String(50), default='pending')  # pending|completed|failed
    
    # Concept storage fields for advanced matching
    core_concepts = Column(Text, nullable=True)  # JSON: extracted mathematical concepts
    solution_method = Column(String(500), nullable=True)  # Primary solution approach (increased from 100)
    concept_difficulty = Column(Text, nullable=True)  # JSON: difficulty indicators
    operations_required = Column(Text, nullable=True)  # JSON: mathematical operations
    problem_structure = Column(String(50), nullable=True)  # Structure pattern type
    concept_keywords = Column(Text, nullable=True)  # JSON: searchable keywords
    
    # Relationships
    paper = relationship("PYQPaper", back_populates="questions")
    # topic relationship REMOVED as per requirements

    @validates('difficulty_band')
    def validate_difficulty_band(self, key, difficulty_band):
        """Validate difficulty band values for PYQ questions"""
        if difficulty_band is not None and difficulty_band not in ['Easy', 'Medium', 'Hard']:
            raise ValueError("PYQ difficulty band must be Easy, Medium, or Hard")
        return difficulty_band

    async def ensure_enhanced_pyq_enrichment(self, db_session, enhanced_enricher=None):
        """
        Ensure this PYQ question has complete enhanced enrichment
        Includes difficulty assessment and concept extraction
        """
        from datetime import datetime
        
        # Check if enhanced enrichment is needed
        if (self.concept_extraction_status != 'completed' or 
            self.difficulty_band is None or 
            not self.is_active):
            
            logger.info(f"🔄 Triggering enhanced PYQ enrichment for question {self.id}")
            
            if enhanced_enricher is None:
                from enhanced_pyq_enrichment_service import EnhancedPYQEnrichmentService
                enhanced_enricher = EnhancedPYQEnrichmentService()
            
            try:
                # Update status
                self.concept_extraction_status = 'processing'
                self.last_updated = datetime.utcnow()
                
                # Trigger Enhanced PYQ Enrichment
                enrichment_result = await enhanced_enricher.full_pyq_enrichment(self)
                
                if enrichment_result["success"]:
                    # Success - update status
                    self.concept_extraction_status = 'completed'
                    self.is_active = True
                    self.quality_verified = True
                    
                    logger.info(f"✅ Enhanced PYQ enrichment successful for question {self.id}")
                    
                    await db_session.commit()
                    return True
                    
                else:
                    # Failed - record error
                    self.concept_extraction_status = 'failed'
                    self.is_active = False
                    
                    logger.error(f"❌ Enhanced PYQ enrichment failed for question {self.id}: {enrichment_result.get('error')}")
                    await db_session.commit()
                    return False
                
            except Exception as e:
                # Exception - record failure
                self.concept_extraction_status = 'failed'
                self.is_active = False
                
                logger.error(f"❌ Enhanced PYQ enrichment exception for question {self.id}: {e}")
                await db_session.commit()
                return False
        
        return True  # Already has valid enrichment


# User Management Tables

class User(Base):
    """Users table"""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    password_hash = Column(Text, nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Referral system
    referral_code = Column(String(6), unique=True, nullable=True)  # 6-character alphanumeric referral code
    
    # Relationships
    diagnostics = relationship("Diagnostic", back_populates="user")
    attempts = relationship("Attempt", back_populates="user")
    mastery = relationship("Mastery", back_populates="user")
    plans = relationship("Plan", back_populates="user")
    sessions = relationship("Session", back_populates="user")
    coverage_tracking = relationship("StudentCoverageTracking", back_populates="user")


class ReferralUsage(Base):
    """Referral usage tracking table"""
    __tablename__ = "referral_usage"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    referral_code = Column(String(6), nullable=False)  # The referral code used
    used_by_user_id = Column(String(36), ForeignKey('users.id'), nullable=True)  # User who used the code (if registered)
    used_by_email = Column(String(255), nullable=False)  # Email of user who used the code
    discount_amount = Column(Integer, nullable=False, default=500)  # Discount amount in INR
    subscription_type = Column(String(50), nullable=False)  # pro_regular or pro_exclusive
    payment_reference = Column(String(255), nullable=True)  # Payment ID that triggered the usage recording
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    used_by_user = relationship("User", foreign_keys=[used_by_user_id])
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_referral_usage_code', 'referral_code'),
        Index('idx_referral_usage_email', 'used_by_email'),
        Index('idx_referral_usage_user', 'used_by_user_id'),
        # Ensure one referral code usage per email
        Index('idx_referral_usage_unique', 'used_by_email', 'referral_code', unique=True),
    )


# Payment and Subscription Tables

class Subscription(Base):
    """Subscriptions table - user subscription management"""
    __tablename__ = "subscriptions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    razorpay_subscription_id = Column(String(255), unique=True, nullable=True)
    plan_type = Column(String(50), nullable=False)  # pro_regular or pro_exclusive
    amount = Column(Integer, nullable=False)  # Amount in paise
    status = Column(String(20), default="active")  # active, paused, cancelled, expired
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False)
    auto_renew = Column(Boolean, default=False)
    paused_at = Column(DateTime, nullable=True)  # When subscription was paused
    paused_days_remaining = Column(Integer, nullable=True)  # Days remaining when paused
    pause_count = Column(Integer, default=0)  # Track number of times paused
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])


class PaymentOrder(Base):
    """Payment Orders table - Razorpay order tracking"""
    __tablename__ = "payment_orders"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    razorpay_order_id = Column(String(255), unique=True, nullable=False)
    plan_type = Column(String(50), nullable=False)  # pro_regular or pro_exclusive
    amount = Column(Integer, nullable=False)  # Amount in paise
    currency = Column(String(10), default="INR")
    status = Column(String(20), default="created")  # created, paid, failed, cancelled
    receipt = Column(String(255), nullable=True)
    notes = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])


class PaymentTransaction(Base):
    """Payment Transactions table - completed payment tracking"""
    __tablename__ = "payment_transactions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    razorpay_payment_id = Column(String(255), unique=True, nullable=False)
    razorpay_order_id = Column(String(255), nullable=False)
    amount = Column(Integer, nullable=False)  # Amount in paise
    currency = Column(String(10), default="INR")
    status = Column(String(20), nullable=False)  # captured, authorized, failed
    method = Column(String(50), nullable=True)  # card, upi, netbanking, wallet
    description = Column(Text, nullable=True)
    notes = Column(JSON, default=dict)
    fee = Column(Integer, nullable=True)
    tax = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])


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
    question_id = Column(String(36), nullable=False)  # Removed ForeignKey relationship as per requirements
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
    # question relationship REMOVED as per requirements
    
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


class TypeMastery(Base):
    """Type-level mastery tracking for three-phase adaptive system"""
    __tablename__ = "type_mastery"
    
    user_id = Column(String(36), ForeignKey('users.id'), primary_key=True)
    category = Column(String(100), primary_key=True)
    subcategory = Column(String(100), primary_key=True) 
    type_of_question = Column(String(100), primary_key=True)
    
    # Mastery metrics at type level
    total_attempts = Column(Integer, default=0)
    correct_attempts = Column(Integer, default=0)
    accuracy_rate = Column(Numeric(3, 2), default=0)  # 0-1
    avg_time_taken = Column(Numeric(6, 2), default=0)  # seconds
    mastery_score = Column(Numeric(3, 2), default=0)   # 0-1
    
    # Time-based tracking
    first_attempt_date = Column(DateTime, nullable=True)
    last_attempt_date = Column(DateTime, nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_user_category_subcategory_type', 'user_id', 'category', 'subcategory', 'type_of_question'),
        Index('idx_user_mastery_score', 'user_id', 'mastery_score'),
        Index('idx_category_subcategory_type', 'category', 'subcategory', 'type_of_question'),
    )


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
    status = Column(String(20), default='pending')  # pending|in_progress|done|skipped
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


class DoubtsConversation(Base):
    """Store doubt conversations between users and Twelvr AI for each question"""
    __tablename__ = "doubts_conversations"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    question_id = Column(String(36), ForeignKey('questions.id'), nullable=False)
    session_id = Column(String(36), ForeignKey('sessions.id'), nullable=True)  # Link to session if available
    message_count = Column(Integer, default=0)  # Track number of messages in conversation
    conversation_transcript = Column(Text, default='[]')  # JSON array of conversation messages
    gemini_token_usage = Column(Integer, default=0)  # Total tokens used by Gemini for this conversation
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_locked = Column(Boolean, default=False)  # Lock conversation after 10 messages
    
    # Relationships
    user = relationship("User")
    question = relationship("Question")
    session = relationship("Session")
    
    # Indexes for efficient queries
    __table_args__ = (
        Index('idx_doubts_user_question', 'user_id', 'question_id'),
        Index('idx_doubts_session', 'session_id'),
    )


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


class PrivilegedEmail(Base):
    __tablename__ = "privileged_emails"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    added_by_admin = Column(String, nullable=False)  # Admin user ID who added this email
    created_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(String, nullable=True)  # Optional notes about why this email is privileged


class StudentCoverageTracking(Base):
    """Student Coverage Tracking - tracks which subcategory::type combinations each student has seen"""
    __tablename__ = "student_coverage_tracking"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    subcategory_type_combination = Column(String(300), nullable=False)  # e.g., "Time-Speed-Distance::Basics"
    sessions_seen = Column(Integer, default=1)
    first_seen_session = Column(Integer, nullable=False)
    last_seen_session = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="coverage_tracking")
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint('user_id', 'subcategory_type_combination', name='uq_user_coverage_combination'),
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
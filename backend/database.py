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
# IST timezone support
from utils.timezone_utils import now_ist, ist_to_utc

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

# DELETED TABLE: Topic model removed as part of database cleanup


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
    
    # PYQ frequency analysis (single essential field only)
    pyq_frequency_score = Column(Numeric(5, 4), default=0.0)  # LLM-calculated: 0.5, 1.0, or 1.5
    # learning_impact REMOVED as per requirements
    # pyq_conceptual_matches REMOVED as per requirements
    
    # MCQ Options (from CSV upload)
    mcq_options = Column(Text, nullable=True)  # From CSV upload
    
    # LLM enrichment fields (same logic as PYQ questions)
    quality_verified = Column(Boolean, default=False)  # Quality gate from LLM enrichment
    answer_match = Column(Boolean, default=False)  # Semantic match between right_answer and answer
    concept_extraction_status = Column(String(50), default='pending')  # pending|completed|failed (SAME AS PYQ)
    core_concepts = Column(Text, nullable=True)  # JSON: extracted mathematical concepts
    solution_method = Column(String(200), nullable=True)  # Primary solution approach from LLM
    concept_difficulty = Column(Text, nullable=True)  # JSON: difficulty indicators from LLM
    operations_required = Column(Text, nullable=True)  # JSON: mathematical operations from LLM
    problem_structure = Column(String(100), nullable=True)  # Structure pattern type from LLM
    concept_keywords = Column(Text, nullable=True)  # JSON: searchable keywords from LLM
    
    # Metadata
    source = Column(String(20), default='Admin')  # Admin|PYQ|Mock|AI_GEN
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: ist_to_utc(now_ist()))
    
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
    created_at = Column(DateTime, default=lambda: ist_to_utc(now_ist()))
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
    created_at = Column(DateTime, default=lambda: ist_to_utc(now_ist()))
    
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
    created_at = Column(DateTime, default=lambda: ist_to_utc(now_ist()))
    
    # Referral system
    referral_code = Column(String(6), unique=True, nullable=True)  # 6-character alphanumeric referral code
    
    # Adaptive system feature flag
    adaptive_enabled = Column(Boolean, default=False, nullable=False)
    
    # Relationships - updated after database cleanup
    # diagnostics, attempts, mastery, plans, sessions, coverage_tracking relationships removed (tables deleted)


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
    created_at = Column(DateTime, default=lambda: ist_to_utc(now_ist()))
    
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
    created_at = Column(DateTime, default=lambda: ist_to_utc(now_ist()))
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
    created_at = Column(DateTime, default=lambda: ist_to_utc(now_ist()))
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
    created_at = Column(DateTime, default=lambda: ist_to_utc(now_ist()))
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])


# Diagnostic System Tables

# DELETED TABLE: DiagnosticSet model removed as part of database cleanup


# DELETED TABLE: DiagnosticSetQuestion model removed as part of database cleanup


# DELETED TABLE: Diagnostic model removed as part of database cleanup


# Attempt and Progress Tracking

# DELETED TABLE: Attempt model removed as part of database cleanup


# DELETED TABLE: Mastery model removed as part of database cleanup


# DELETED TABLE: TypeMastery model removed as part of database cleanup


# Study Planning Tables

# DELETED TABLE: Plan model removed as part of database cleanup


# DELETED TABLE: PlanUnit model removed as part of database cleanup


# Session Management

# DELETED TABLE: Session model removed as part of database cleanup


# DELETED TABLE: DoubtsConversation model removed - will be redesigned with new session logic


# DELETED TABLE: MasteryHistory model removed as part of database cleanup


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
    created_at = Column(DateTime, default=lambda: ist_to_utc(now_ist()))
    notes = Column(String, nullable=True)  # Optional notes about why this email is privileged


# DELETED TABLE: StudentCoverageTracking model removed as part of database cleanup


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
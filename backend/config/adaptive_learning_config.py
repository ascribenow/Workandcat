"""
Centralized Adaptive Learning Configuration
Single source of truth for all adaptive learning hyperparameters

This module replaces hardcoded constants scattered across the codebase
and provides validation, documentation, and audit trail support.

Version: 1.0.0
Last Updated: 2025-09-30
"""

from typing import Dict, Any, List
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

# ==============================================================================
# VERSION TRACKING
# ==============================================================================

CONFIG_VERSION = "1.0.0"
CONFIG_LAST_UPDATED = "2025-09-30"

# ==============================================================================
# CORE CONFIGURATION
# ==============================================================================

@dataclass
class AdaptiveLearningConfig:
    """
    Centralized configuration for adaptive learning system
    
    All hyperparameters are documented with their purpose and valid ranges.
    Changes to this configuration should be tracked in config_change_log table.
    """
    
    # ==========================================================================
    # SESSION CONFIGURATION
    # ==========================================================================
    
    session_questions_count: int = 12
    """Number of questions per session (fixed for Blueprint sessions)"""
    
    session_min_questions: int = 8
    """Minimum questions required to complete a session"""
    
    session_timeout_minutes: int = 60
    """Maximum time allowed per session (minutes)"""
    
    # ==========================================================================
    # MASTERY SCORING
    # ==========================================================================
    
    mastery_min_score: float = 0.0
    """Minimum mastery score (0.0 = complete beginner)"""
    
    mastery_max_score: float = 10.0
    """Maximum mastery score (10.0 = complete mastery)"""
    
    mastery_initial_score: float = 5.0
    """Initial mastery score for new concepts"""
    
    mastery_increase_correct: float = 1.0
    """Mastery increase when answering correctly"""
    
    mastery_decrease_incorrect: float = 0.5
    """Mastery decrease when answering incorrectly"""
    
    mastery_weak_threshold: float = 3.0
    """Below this threshold, concept is 'Weak'"""
    
    mastery_moderate_threshold: float = 7.0
    """Below this threshold, concept is 'Moderate', above is 'Strong'"""
    
    # ==========================================================================
    # READINESS CALCULATION
    # ==========================================================================
    
    readiness_levels: List[str] = field(default_factory=lambda: ["Weak", "Moderate", "Strong"])
    """Valid readiness levels for concepts"""
    
    readiness_weak_max: float = 3.0
    """Max mastery score for 'Weak' readiness"""
    
    readiness_moderate_max: float = 7.0
    """Max mastery score for 'Moderate' readiness"""
    
    # ==========================================================================
    # COVERAGE DEBT
    # ==========================================================================
    
    coverage_debt_initial: float = 1.0
    """Initial coverage debt for new concept pairs"""
    
    coverage_debt_decrease_served: float = 0.3
    """Debt decrease when concept pair is served"""
    
    coverage_debt_decay_rate: float = 0.05
    """Debt decay rate for unserved concepts (per session)"""
    
    coverage_debt_min: float = 0.0
    """Minimum coverage debt (fully covered)"""
    
    coverage_debt_max: float = 10.0
    """Maximum coverage debt (never served)"""
    
    # ==========================================================================
    # QUESTION SELECTION
    # ==========================================================================
    
    question_difficulty_bands: List[str] = field(default_factory=lambda: ["easy", "medium", "hard"])
    """Valid difficulty bands for questions"""
    
    question_pyq_weight: float = 0.7
    """Weight for PYQ frequency in selection (0.0-1.0)"""
    
    question_coverage_weight: float = 0.3
    """Weight for coverage debt in selection (0.0-1.0)"""
    
    question_dedup_lookback_sessions: int = 3
    """Number of recent sessions to check for question deduplication"""
    
    # ==========================================================================
    # ANCHOR SYSTEM (Skill-Based Selection)
    # ==========================================================================
    
    anchor_min_per_question: int = 2
    """Minimum anchors required per question"""
    
    anchor_max_per_question: int = 5
    """Maximum anchors to store per question"""
    
    anchor_confidence_threshold: float = 0.8
    """Minimum confidence for anchor to be considered valid"""
    
    # ==========================================================================
    # JOB PROCESSING
    # ==========================================================================
    
    job_max_attempts: int = 6
    """Maximum retry attempts for failed jobs"""
    
    job_backoff_base_minutes: int = 1
    """Base backoff time for job retries (exponential: 1, 2, 4, 8, 16, 30)"""
    
    job_backoff_max_minutes: int = 30
    """Maximum backoff time for job retries"""
    
    job_processing_timeout_seconds: int = 300
    """Maximum time for job processing (5 minutes)"""
    
    # ==========================================================================
    # NORMALIZATION RULES
    # ==========================================================================
    
    normalize_mastery_bounds: bool = True
    """Whether to clamp mastery scores to min/max bounds"""
    
    normalize_debt_bounds: bool = True
    """Whether to clamp coverage debt to min/max bounds"""
    
    normalize_readiness_mapping: bool = True
    """Whether to map mastery scores to readiness levels"""
    
    # ==========================================================================
    # VALIDATION
    # ==========================================================================
    
    def validate(self) -> List[str]:
        """
        Validate configuration for consistency and valid ranges
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Session validation
        if self.session_questions_count < self.session_min_questions:
            errors.append(f"session_questions_count ({self.session_questions_count}) must be >= session_min_questions ({self.session_min_questions})")
        
        if self.session_timeout_minutes <= 0:
            errors.append(f"session_timeout_minutes must be positive")
        
        # Mastery validation
        if self.mastery_min_score >= self.mastery_max_score:
            errors.append(f"mastery_min_score must be < mastery_max_score")
        
        if not (self.mastery_min_score <= self.mastery_initial_score <= self.mastery_max_score):
            errors.append(f"mastery_initial_score must be between min and max")
        
        if self.mastery_weak_threshold >= self.mastery_moderate_threshold:
            errors.append(f"mastery_weak_threshold must be < mastery_moderate_threshold")
        
        # Readiness validation
        if self.readiness_weak_max >= self.readiness_moderate_max:
            errors.append(f"readiness_weak_max must be < readiness_moderate_max")
        
        # Coverage debt validation
        if self.coverage_debt_min >= self.coverage_debt_max:
            errors.append(f"coverage_debt_min must be < coverage_debt_max")
        
        if self.coverage_debt_decrease_served < 0:
            errors.append(f"coverage_debt_decrease_served must be non-negative")
        
        if self.coverage_debt_decay_rate < 0 or self.coverage_debt_decay_rate > 1:
            errors.append(f"coverage_debt_decay_rate must be between 0 and 1")
        
        # Question selection validation
        question_weight_sum = self.question_pyq_weight + self.question_coverage_weight
        if not (0.99 <= question_weight_sum <= 1.01):  # Allow small floating point error
            errors.append(f"question_pyq_weight + question_coverage_weight must sum to 1.0 (got {question_weight_sum})")
        
        # Anchor validation
        if self.anchor_min_per_question > self.anchor_max_per_question:
            errors.append(f"anchor_min_per_question must be <= anchor_max_per_question")
        
        if not (0 <= self.anchor_confidence_threshold <= 1):
            errors.append(f"anchor_confidence_threshold must be between 0 and 1")
        
        # Job validation
        if self.job_max_attempts <= 0:
            errors.append(f"job_max_attempts must be positive")
        
        if self.job_backoff_base_minutes <= 0:
            errors.append(f"job_backoff_base_minutes must be positive")
        
        if self.job_backoff_max_minutes < self.job_backoff_base_minutes:
            errors.append(f"job_backoff_max_minutes must be >= job_backoff_base_minutes")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization"""
        return {
            "version": CONFIG_VERSION,
            "last_updated": CONFIG_LAST_UPDATED,
            "session": {
                "questions_count": self.session_questions_count,
                "min_questions": self.session_min_questions,
                "timeout_minutes": self.session_timeout_minutes
            },
            "mastery": {
                "min_score": self.mastery_min_score,
                "max_score": self.mastery_max_score,
                "initial_score": self.mastery_initial_score,
                "increase_correct": self.mastery_increase_correct,
                "decrease_incorrect": self.mastery_decrease_incorrect,
                "weak_threshold": self.mastery_weak_threshold,
                "moderate_threshold": self.mastery_moderate_threshold
            },
            "readiness": {
                "levels": self.readiness_levels,
                "weak_max": self.readiness_weak_max,
                "moderate_max": self.readiness_moderate_max
            },
            "coverage_debt": {
                "initial": self.coverage_debt_initial,
                "decrease_served": self.coverage_debt_decrease_served,
                "decay_rate": self.coverage_debt_decay_rate,
                "min": self.coverage_debt_min,
                "max": self.coverage_debt_max
            },
            "question_selection": {
                "difficulty_bands": self.question_difficulty_bands,
                "pyq_weight": self.question_pyq_weight,
                "coverage_weight": self.question_coverage_weight,
                "dedup_lookback_sessions": self.question_dedup_lookback_sessions
            },
            "anchors": {
                "min_per_question": self.anchor_min_per_question,
                "max_per_question": self.anchor_max_per_question,
                "confidence_threshold": self.anchor_confidence_threshold
            },
            "jobs": {
                "max_attempts": self.job_max_attempts,
                "backoff_base_minutes": self.job_backoff_base_minutes,
                "backoff_max_minutes": self.job_backoff_max_minutes,
                "processing_timeout_seconds": self.job_processing_timeout_seconds
            },
            "normalization": {
                "mastery_bounds": self.normalize_mastery_bounds,
                "debt_bounds": self.normalize_debt_bounds,
                "readiness_mapping": self.normalize_readiness_mapping
            }
        }

# ==============================================================================
# GLOBAL CONFIGURATION INSTANCE
# ==============================================================================

# Create and validate global configuration
_config = AdaptiveLearningConfig()
validation_errors = _config.validate()

if validation_errors:
    logger.error(f"❌ Configuration validation failed:")
    for error in validation_errors:
        logger.error(f"  - {error}")
    raise ValueError(f"Invalid configuration: {validation_errors}")
else:
    logger.info(f"✅ Adaptive learning configuration loaded (version {CONFIG_VERSION})")

# Export the validated configuration
config = _config

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def get_readiness_from_mastery(mastery_score: float) -> str:
    """
    Map mastery score to readiness level
    
    Args:
        mastery_score: Current mastery score (0.0-10.0)
        
    Returns:
        Readiness level: "Weak", "Moderate", or "Strong"
    """
    if mastery_score <= config.readiness_weak_max:
        return "Weak"
    elif mastery_score <= config.readiness_moderate_max:
        return "Moderate"
    else:
        return "Strong"


def normalize_mastery_score(score: float) -> float:
    """
    Normalize mastery score to valid range
    
    Args:
        score: Raw mastery score
        
    Returns:
        Normalized score clamped to [min_score, max_score]
    """
    if not config.normalize_mastery_bounds:
        return score
    
    return max(config.mastery_min_score, min(config.mastery_max_score, score))


def normalize_coverage_debt(debt: float) -> float:
    """
    Normalize coverage debt to valid range
    
    Args:
        debt: Raw coverage debt
        
    Returns:
        Normalized debt clamped to [min, max]
    """
    if not config.normalize_debt_bounds:
        return debt
    
    return max(config.coverage_debt_min, min(config.coverage_debt_max, debt))


def get_job_backoff_minutes(attempt: int) -> int:
    """
    Calculate exponential backoff time for job retry
    
    Args:
        attempt: Current attempt number (1-indexed)
        
    Returns:
        Backoff time in minutes
    """
    # Exponential backoff: 1, 2, 4, 8, 16, 30 (capped)
    backoff = config.job_backoff_base_minutes * (2 ** (attempt - 1))
    return min(backoff, config.job_backoff_max_minutes)

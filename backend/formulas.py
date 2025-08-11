"""
CAT Preparation Platform - Comprehensive Formula Implementation
Contains all scoring, difficulty, mastery, and assessment formulas
"""

import math
from typing import Dict, List, Tuple, Optional, Union
from datetime import datetime, timedelta
import numpy as np

# =====================================================
# DIFFICULTY LEVEL CALCULATION
# =====================================================

def calculate_difficulty_level(
    average_accuracy: float,
    average_time_seconds: float,
    attempt_count: int,
    topic_centrality: float
) -> Tuple[float, str]:
    """
    Calculate normalized difficulty level (0-1) based on 4 factors
    
    Args:
        average_accuracy: Mean accuracy across all attempts (0-1)
        average_time_seconds: Mean time taken in seconds
        attempt_count: Total number of attempts made
        topic_centrality: Topic importance in CAT (0-1)
    
    Returns:
        Tuple of (difficulty_score, difficulty_band)
    """
    # Factor 1: Accuracy Component (inverse relationship)
    accuracy_factor = max(0, 1 - average_accuracy)  # Lower accuracy = higher difficulty
    
    # Factor 2: Time Component (normalized to 0-1)
    # Assuming 300 seconds (5 minutes) as maximum expected time
    time_factor = min(1.0, average_time_seconds / 300.0)  # Higher time = higher difficulty
    
    # Factor 3: Attempt Volume Component (diminishing returns)
    # More attempts indicate difficulty in mastering
    volume_factor = min(0.3, math.log(max(1, attempt_count)) / 10.0)  # Cap at 0.3
    
    # Factor 4: Topic Centrality Component
    centrality_factor = topic_centrality * 0.2  # Weight topic importance
    
    # Combined Difficulty Score (weighted average)
    difficulty_score = (
        0.40 * accuracy_factor +      # Primary factor
        0.30 * time_factor +          # Secondary factor
        0.20 * volume_factor +        # Tertiary factor
        0.10 * centrality_factor      # Context factor
    )
    
    # Clamp to 0-1 range
    difficulty_score = max(0.0, min(1.0, difficulty_score))
    
    # Determine difficulty band
    if difficulty_score <= 0.33:
        difficulty_band = "Easy"
    elif difficulty_score <= 0.67:
        difficulty_band = "Medium"
    else:
        difficulty_band = "Hard"
    
    return difficulty_score, difficulty_band


# =====================================================
# FREQUENCY BAND DETERMINATION
# =====================================================

def calculate_frequency_band(
    appearance_count: int,
    total_papers: int,
    years_active: int
) -> Tuple[float, str]:
    """
    Calculate frequency score and band based on historical appearance
    
    Args:
        appearance_count: Number of times question/concept appeared
        total_papers: Total papers in the dataset
        years_active: Years the concept has been appearing
    
    Returns:
        Tuple of (frequency_score, frequency_band)
    """
    # Base frequency rate
    base_frequency = appearance_count / max(1, total_papers)
    
    # Yearly consistency factor
    consistency_factor = min(1.0, years_active / 10.0)  # Normalize to 10 years
    
    # Combined frequency score
    frequency_score = base_frequency * (0.8 + 0.2 * consistency_factor)
    
    # Clamp to 0-1 range
    frequency_score = max(0.0, min(1.0, frequency_score))
    
    # Determine frequency band
    if frequency_score <= 0.2:
        frequency_band = "Rare"
    elif frequency_score <= 0.6:
        frequency_band = "Regular"
    else:
        frequency_band = "High"
    
    return frequency_score, frequency_band


# =====================================================
# IMPORTANCE LEVEL CALCULATION
# =====================================================

def calculate_importance_level(
    topic_centrality: float,
    frequency_score: float,
    difficulty_score: float,
    syllabus_weight: float = 1.0
) -> Tuple[float, str]:
    """
    Calculate importance level based on centrality, frequency, and difficulty
    
    Args:
        topic_centrality: Topic importance in syllabus (0-1)
        frequency_score: How frequently concept appears (0-1)
        difficulty_score: Question difficulty (0-1)
        syllabus_weight: Official syllabus weightage (0-1)
    
    Returns:
        Tuple of (importance_score, importance_level)
    """
    # Weighted importance calculation
    importance_score = (
        0.35 * topic_centrality +     # Syllabus importance
        0.30 * frequency_score +      # Historical frequency
        0.20 * difficulty_score +     # Difficulty contribution
        0.15 * syllabus_weight        # Official weightage
    )
    
    # Clamp to 0-1 range
    importance_score = max(0.0, min(1.0, importance_score))
    
    # Determine importance level
    if importance_score <= 0.4:
        importance_level = "Low"
    elif importance_score <= 0.7:
        importance_level = "Medium"
    else:
        importance_level = "High"
    
    return importance_score, importance_level


# =====================================================
# LEARNING IMPACT SCORE (DYNAMIC)
# =====================================================

def calculate_learning_impact(
    difficulty_score: float,
    importance_score: float,
    user_mastery_level: float,
    days_until_exam: int,
    prerequisite_mastery: float = 1.0
) -> float:
    """
    Calculate dynamic learning impact based on user context and time constraints
    
    Args:
        difficulty_score: Question difficulty (0-1)
        importance_score: Question importance (0-1)
        user_mastery_level: Current user mastery in topic (0-1)
        days_until_exam: Days remaining until exam
        prerequisite_mastery: Mastery of prerequisite topics (0-1)
    
    Returns:
        Learning impact score (0-1)
    """
    # Base impact from difficulty and importance
    base_impact = (importance_score + difficulty_score) / 2.0
    
    # Mastery gap factor (higher impact if mastery is low)
    mastery_gap = 1 - user_mastery_level
    mastery_factor = mastery_gap * 0.8 + 0.2  # Ensure minimum impact
    
    # Time urgency factor
    if days_until_exam <= 30:
        urgency_factor = 1.0  # High urgency
    elif days_until_exam <= 60:
        urgency_factor = 0.8  # Medium urgency
    else:
        urgency_factor = 0.6  # Low urgency
    
    # Prerequisite readiness factor
    readiness_factor = 0.5 + 0.5 * prerequisite_mastery
    
    # Combined learning impact
    learning_impact = base_impact * mastery_factor * urgency_factor * readiness_factor
    
    # Clamp to 0-1 range
    return max(0.0, min(1.0, learning_impact))


# =====================================================
# CAPABILITY METRIC (DIAGNOSTIC SYSTEM)
# =====================================================

def calculate_capability_metric(
    correct_answers: int,
    total_questions: int,
    time_taken_seconds: int,
    difficulty_distribution: Dict[str, int],
    category_performance: Dict[str, float]
) -> Dict[str, Union[float, str]]:
    """
    Calculate comprehensive capability metric for diagnostic assessment
    
    Args:
        correct_answers: Number of correct answers
        total_questions: Total questions attempted
        time_taken_seconds: Total time taken
        difficulty_distribution: Count of questions by difficulty {"Easy": 5, "Medium": 15, "Hard": 5}
        category_performance: Performance by category {"Arithmetic": 0.8, "Algebra": 0.6, ...}
    
    Returns:
        Dictionary with capability metrics and track recommendation
    """
    # Base accuracy
    accuracy = correct_answers / max(1, total_questions)
    
    # Time efficiency (questions per minute)
    time_minutes = time_taken_seconds / 60.0
    efficiency = total_questions / max(1, time_minutes)
    
    # Difficulty-weighted accuracy
    weighted_score = 0.0
    total_weight = 0.0
    
    for diff_level, count in difficulty_distribution.items():
        if count > 0:
            weight = {"Easy": 1.0, "Medium": 1.5, "Hard": 2.0}.get(diff_level, 1.0)
            # Assume equal performance across difficulties for now
            weighted_score += weight * count * accuracy
            total_weight += weight * count
    
    difficulty_adjusted_accuracy = weighted_score / max(1, total_weight)
    
    # Category consistency (how balanced performance is across categories)
    performances = list(category_performance.values())
    if performances:
        category_std = np.std(performances)
        consistency_score = max(0, 1 - category_std)  # Lower std = higher consistency
    else:
        consistency_score = 0.5
    
    # Overall capability score
    capability_score = (
        0.40 * difficulty_adjusted_accuracy +  # Primary: Accuracy with difficulty weighting
        0.25 * min(1.0, efficiency / 2.0) +    # Time efficiency (normalized)
        0.20 * accuracy +                      # Raw accuracy
        0.15 * consistency_score               # Cross-category consistency
    )
    
    capability_score = max(0.0, min(1.0, capability_score))
    
    # Track recommendation
    if capability_score >= 0.75:
        track_recommendation = "Advanced"
    elif capability_score >= 0.55:
        track_recommendation = "Intermediate"
    else:
        track_recommendation = "Basic"
    
    return {
        "capability_score": capability_score,
        "accuracy": accuracy,
        "difficulty_adjusted_accuracy": difficulty_adjusted_accuracy,
        "time_efficiency": efficiency,
        "category_consistency": consistency_score,
        "track_recommendation": track_recommendation
    }


# =====================================================
# EWMA MASTERY TRACKING
# =====================================================

def calculate_ewma_mastery(
    current_mastery: float,
    new_performance: float,
    alpha: float = 0.6,
    time_decay_factor: float = 0.02,
    days_since_last_attempt: int = 0
) -> float:
    """
    Calculate Exponentially Weighted Moving Average (EWMA) mastery with time decay
    
    Args:
        current_mastery: Current mastery level (0-1)
        new_performance: New performance score (0-1) from latest attempt
        alpha: Learning rate (0-1, higher = more weight to recent performance)
        time_decay_factor: Daily decay rate for time-based forgetting
        days_since_last_attempt: Days since last practice
    
    Returns:
        Updated mastery score (0-1)
    """
    # Apply time-based decay
    decay_multiplier = math.exp(-time_decay_factor * days_since_last_attempt)
    decayed_mastery = current_mastery * decay_multiplier
    
    # EWMA calculation
    updated_mastery = alpha * new_performance + (1 - alpha) * decayed_mastery
    
    # Clamp to 0-1 range
    return max(0.0, min(1.0, updated_mastery))


# =====================================================
# PREPAREDNESS AMBITION (90th DAY VS T-1)
# =====================================================

def calculate_preparedness_ambition(
    current_mastery: Dict[str, float],
    target_mastery: Dict[str, float],
    days_remaining: int,
    study_intensity: float = 1.0
) -> Dict[str, float]:
    """
    Calculate daily learning requirements based on preparedness ambition
    Compares current state to 90th day target vs T-1 final state
    
    Args:
        current_mastery: Current mastery by topic {"Arithmetic": 0.6, ...}
        target_mastery: Target mastery by topic {"Arithmetic": 0.8, ...}
        days_remaining: Days until exam (T)
        study_intensity: Daily study intensity multiplier (0.5-2.0)
    
    Returns:
        Dictionary with daily requirements and progress metrics
    """
    total_gap = 0.0
    topic_priorities = {}
    
    for topic, current in current_mastery.items():
        target = target_mastery.get(topic, 0.8)  # Default target 80%
        gap = max(0, target - current)
        total_gap += gap
        
        # Calculate daily requirement
        if days_remaining > 0:
            daily_requirement = gap / days_remaining * study_intensity
        else:
            daily_requirement = gap  # Immediate requirement
        
        topic_priorities[topic] = {
            "current_mastery": current,
            "target_mastery": target,
            "mastery_gap": gap,
            "daily_requirement": daily_requirement,
            "priority_score": gap * target  # Gap weighted by importance
        }
    
    # Calculate overall metrics
    current_avg = sum(current_mastery.values()) / len(current_mastery) if current_mastery else 0
    target_avg = sum(target_mastery.values()) / len(target_mastery) if target_mastery else 0
    
    # Progress toward 90-day ambition vs current trajectory
    progress_ratio = current_avg / max(0.1, target_avg)  # Avoid division by zero
    
    return {
        "topic_priorities": topic_priorities,
        "total_mastery_gap": total_gap,
        "average_current_mastery": current_avg,
        "average_target_mastery": target_avg,
        "progress_ratio": progress_ratio,
        "days_remaining": days_remaining,
        "on_track": progress_ratio >= 0.8  # 80% of target indicates on track
    }


# =====================================================
# 25-QUESTION DIAGNOSTIC BLUEPRINT
# =====================================================

def get_diagnostic_blueprint() -> Dict[str, Dict]:
    """
    Returns the official 25-question diagnostic test blueprint
    Ensures proper coverage across categories and difficulty levels
    
    Returns:
        Dictionary with category distribution and difficulty requirements
    """
    return {
        "total_questions": 25,
        "category_distribution": {
            "A": {"count": 8, "name": "Arithmetic"},      # 32% - High weightage
            "B": {"count": 5, "name": "Algebra"},         # 20% - Medium weightage  
            "C": {"count": 6, "name": "Geometry & Mensuration"},  # 24% - High weightage
            "D": {"count": 3, "name": "Number System"},   # 12% - Low weightage
            "E": {"count": 3, "name": "Modern Math"}      # 12% - Low weightage
        },
        "difficulty_distribution": {
            "Easy": 8,      # 32% - Build confidence
            "Medium": 12,   # 48% - Core assessment
            "Hard": 5       # 20% - Differentiation
        },
        "subcategory_requirements": {
            # Ensure each category covers multiple subcategories
            "min_subcategories_per_category": 2,
            "max_questions_per_subcategory": 2
        },
        "time_allocation": {
            "total_minutes": 50,    # 2 minutes per question on average
            "easy_avg_minutes": 1.5,
            "medium_avg_minutes": 2.0,
            "hard_avg_minutes": 3.0
        }
    }


# =====================================================
# NAT FORMAT HANDLING
# =====================================================

def validate_nat_answer(
    user_answer: Union[str, float],
    correct_answer: Union[str, float],
    tolerance: float = 0.01,
    decimal_places: int = 2
) -> bool:
    """
    Validate Numerical Answer Type (NAT) responses with tolerance
    
    Args:
        user_answer: User's numerical input
        correct_answer: Correct numerical answer
        tolerance: Acceptable error margin (absolute or relative)
        decimal_places: Number of decimal places to consider
    
    Returns:
        Boolean indicating if answer is correct within tolerance
    """
    try:
        # Convert to float
        user_val = float(user_answer)
        correct_val = float(correct_answer)
        
        # Round to specified decimal places
        user_val = round(user_val, decimal_places)
        correct_val = round(correct_val, decimal_places)
        
        # Check absolute difference
        abs_diff = abs(user_val - correct_val)
        
        # Check relative difference for non-zero values
        if correct_val != 0:
            rel_diff = abs_diff / abs(correct_val)
            return abs_diff <= tolerance or rel_diff <= tolerance
        else:
            return abs_diff <= tolerance
            
    except (ValueError, TypeError):
        return False


# =====================================================
# ATTEMPT SPACING & MASTERY DECAY RULES
# =====================================================

def calculate_attempt_spacing(
    mastery_level: float,
    previous_attempts: int,
    days_since_last_attempt: int
) -> Dict[str, Union[int, bool]]:
    """
    Calculate optimal spacing between question attempts based on spaced repetition
    
    Args:
        mastery_level: Current mastery level (0-1)
        previous_attempts: Number of previous attempts
        days_since_last_attempt: Days since last attempt
    
    Returns:
        Dictionary with spacing recommendations
    """
    # Base intervals by mastery level (in days)
    if mastery_level >= 0.8:
        base_interval = 7  # Weekly for mastered topics
    elif mastery_level >= 0.6:
        base_interval = 3  # Every 3 days for good mastery
    elif mastery_level >= 0.4:
        base_interval = 1  # Daily for developing mastery
    else:
        base_interval = 0  # Immediate retry for poor mastery
    
    # Adjust based on previous attempts (spaced repetition)
    spacing_multiplier = min(2.0, 1.0 + 0.2 * previous_attempts)
    optimal_spacing = int(base_interval * spacing_multiplier)
    
    # Check if enough time has passed
    can_attempt = days_since_last_attempt >= optimal_spacing
    
    # Minimum wait time for retry
    min_wait_hours = max(1, optimal_spacing * 24) if optimal_spacing > 0 else 0
    
    return {
        "optimal_spacing_days": optimal_spacing,
        "can_attempt_now": can_attempt,
        "minimum_wait_hours": min_wait_hours,
        "next_optimal_date": days_since_last_attempt + optimal_spacing,
        "recommendation": "ready" if can_attempt else "wait"
    }


def apply_mastery_decay(
    current_mastery: float,
    days_inactive: int,
    topic_difficulty: float = 0.5,
    decay_rate: float = 0.02
) -> float:
    """
    Apply time-based mastery decay based on inactivity
    
    Args:
        current_mastery: Current mastery level (0-1)
        days_inactive: Days since last practice
        topic_difficulty: Topic difficulty (higher = faster decay)
        decay_rate: Base decay rate per day
    
    Returns:
        Decayed mastery level (0-1)
    """
    # Adjust decay rate based on topic difficulty
    adjusted_decay_rate = decay_rate * (1 + topic_difficulty)
    
    # Apply exponential decay
    decay_factor = math.exp(-adjusted_decay_rate * days_inactive)
    decayed_mastery = current_mastery * decay_factor
    
    # Ensure minimum retention (never completely forget)
    min_retention = 0.1 * current_mastery
    return max(min_retention, decayed_mastery)


# =====================================================
# UTILITY FUNCTIONS
# =====================================================

def normalize_score(score: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Normalize score to 0-1 range"""
    return max(min_val, min(max_val, score))


def weighted_average(values: List[float], weights: List[float]) -> float:
    """Calculate weighted average"""
    if not values or not weights or len(values) != len(weights):
        return 0.0
    
    weighted_sum = sum(v * w for v, w in zip(values, weights))
    weight_sum = sum(weights)
    
    return weighted_sum / weight_sum if weight_sum > 0 else 0.0
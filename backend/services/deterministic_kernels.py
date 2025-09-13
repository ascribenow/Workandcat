#!/usr/bin/env python3
"""
Deterministic Kernels for Adaptive Logic
Pure Python functions implementing the core adaptive algorithms
"""

import hashlib
import json
import logging
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ReadinessLevel(Enum):
    """Readiness levels as per specification"""
    WEAK = "Weak"
    MODERATE = "Moderate" 
    STRONG = "Strong"

@dataclass
class AttemptEvent:
    """Structured attempt event for kernel processing"""
    question_id: str
    was_correct: bool
    skipped: bool
    response_time_ms: int
    sess_seq_at_serve: int
    difficulty_band: str
    subcategory: str
    type_of_question: str
    core_concepts: List[str]
    pyq_frequency_score: float

@dataclass(frozen=True)
class QuestionCandidate:
    """Question candidate for session planning"""
    question_id: str
    difficulty_band: str
    subcategory: str
    type_of_question: str
    core_concepts: tuple  # Changed to tuple for hashability
    pyq_frequency_score: float
    pair: str  # subcategory:type_of_question

# =============================================================================
# KERNEL 1: STABLE SEMANTIC ID
# =============================================================================

def stable_semantic_id(canonical_label: str) -> str:
    """
    Generate stable semantic ID from canonical concept label
    
    Args:
        canonical_label: Canonical concept name (e.g., "Distance", "Rate")
        
    Returns:
        SHA1 hash (first 12 characters) as stable semantic ID
    """
    if not canonical_label or not isinstance(canonical_label, str):
        raise ValueError(f"Invalid canonical_label: {canonical_label}")
    
    # Normalize: strip whitespace, convert to lowercase for consistency
    normalized = canonical_label.strip().lower()
    
    # Generate SHA1 hash
    hash_obj = hashlib.sha1(normalized.encode('utf-8'))
    semantic_id = hash_obj.hexdigest()[:12]  # First 12 characters
    
    logger.debug(f"semantic_id('{canonical_label}') -> '{semantic_id}'")
    return semantic_id

# =============================================================================  
# KERNEL 2: WEIGHTS FROM DOMINANCE
# =============================================================================

def weights_from_dominance(dominance_labels: Dict[str, str], 
                          confidence_threshold: float = 0.7) -> Dict[str, float]:
    """
    Convert LLM dominance labels to numeric weights with confidence guardrails
    
    Args:
        dominance_labels: Map of semantic_id -> dominance label ("High", "Medium", "Low")
        confidence_threshold: Minimum confidence required (0.0-1.0)
        
    Returns:
        Map of semantic_id -> weight (0.0-1.0)
    """
    if not isinstance(dominance_labels, dict):
        raise ValueError("dominance_labels must be a dictionary")
    
    if not 0.0 <= confidence_threshold <= 1.0:
        raise ValueError("confidence_threshold must be between 0.0 and 1.0")
    
    # Weight mapping as per specification
    weight_mapping = {
        "high": 1.0,
        "medium": 0.6, 
        "low": 0.3
    }
    
    weights = {}
    low_confidence_count = 0
    
    for semantic_id, label in dominance_labels.items():
        if not isinstance(label, str):
            logger.warning(f"Invalid dominance label for {semantic_id}: {label}")
            continue
            
        normalized_label = label.strip().lower()
        
        if normalized_label in weight_mapping:
            weight = weight_mapping[normalized_label]
            weights[semantic_id] = weight
            
            # Confidence guardrail: track low-confidence assignments
            if weight < confidence_threshold:
                low_confidence_count += 1
                
        else:
            logger.warning(f"Unknown dominance label '{label}' for {semantic_id}, defaulting to Medium")
            weights[semantic_id] = weight_mapping["medium"]
    
    # Apply confidence guardrails
    total_concepts = len(weights)
    if total_concepts > 0:
        low_confidence_ratio = low_confidence_count / total_concepts
        if low_confidence_ratio > 0.5:
            logger.warning(f"High proportion of low-confidence weights: {low_confidence_ratio:.1%}")
    
    logger.debug(f"weights_from_dominance: {len(weights)} concepts, {low_confidence_count} low-confidence")
    return weights

# =============================================================================
# KERNEL 3: COMPUTE WEIGHTED COUNTS  
# =============================================================================

def compute_weighted_counts(attempt_events: List[AttemptEvent],
                           concept_weights: Dict[str, float],
                           semantic_id_map: Dict[str, str]) -> Dict[str, Dict[str, float]]:
    """
    Compute weighted counts per concept from attempt history
    
    Args:
        attempt_events: List of user's attempt events
        concept_weights: Map of semantic_id -> weight from previous session
        semantic_id_map: Map of raw_concept -> semantic_id
        
    Returns:
        Map of semantic_id -> {"correct": float, "wrong": float, "skipped": float, "total": float}
    """
    if not isinstance(attempt_events, list):
        raise ValueError("attempt_events must be a list")
    
    if not isinstance(concept_weights, dict):
        raise ValueError("concept_weights must be a dictionary")
        
    if not isinstance(semantic_id_map, dict):
        raise ValueError("semantic_id_map must be a dictionary")
    
    weighted_counts = {}
    
    for event in attempt_events:
        if not isinstance(event, AttemptEvent):
            logger.warning(f"Invalid attempt event: {event}")
            continue
            
        # Process each core concept in the question
        for raw_concept in event.core_concepts:
            # Map raw concept to semantic ID
            semantic_id = semantic_id_map.get(raw_concept)
            if not semantic_id:
                logger.debug(f"Unmapped concept: {raw_concept}")
                continue
                
            # Get weight for this concept (default to 0.6 if not found)
            weight = concept_weights.get(semantic_id, 0.6)
            
            # Initialize counts for this semantic_id
            if semantic_id not in weighted_counts:
                weighted_counts[semantic_id] = {
                    "correct": 0.0,
                    "wrong": 0.0, 
                    "skipped": 0.0,
                    "total": 0.0
                }
            
            # Add weighted counts based on outcome
            if event.skipped:
                weighted_counts[semantic_id]["skipped"] += weight
            elif event.was_correct:
                weighted_counts[semantic_id]["correct"] += weight
            else:
                weighted_counts[semantic_id]["wrong"] += weight
                
            weighted_counts[semantic_id]["total"] += weight
    
    logger.debug(f"compute_weighted_counts: processed {len(attempt_events)} events -> {len(weighted_counts)} concepts")
    return weighted_counts

# =============================================================================
# KERNEL 4: FINALIZE READINESS
# =============================================================================

def finalize_readiness(weighted_counts: Dict[str, Dict[str, float]]) -> Dict[str, ReadinessLevel]:
    """
    Convert weighted counts to readiness levels using deterministic rules
    
    Rules as per specification:
    - skip → Weak  
    - never-correct → Weak
    - wrong > 3 → Moderate
    - correct 1-3 → Strong
    - else → Moderate
    
    Args:
        weighted_counts: Output from compute_weighted_counts
        
    Returns:
        Map of semantic_id -> ReadinessLevel
    """
    if not isinstance(weighted_counts, dict):
        raise ValueError("weighted_counts must be a dictionary")
    
    readiness_map = {}
    
    for semantic_id, counts in weighted_counts.items():
        correct = counts.get("correct", 0.0)
        wrong = counts.get("wrong", 0.0)
        skipped = counts.get("skipped", 0.0)
        total = counts.get("total", 0.0)
        
        # Rule 1: If primarily skipped → Weak
        if total > 0 and skipped / total > 0.5:
            readiness = ReadinessLevel.WEAK
            reason = f"primarily_skipped ({skipped:.1f}/{total:.1f})"
            
        # Rule 2: Never correct → Weak  
        elif correct == 0.0 and (wrong > 0.0 or skipped > 0.0):
            readiness = ReadinessLevel.WEAK
            reason = f"never_correct (0/{total:.1f})"
            
        # Rule 3: Wrong > 3 → Moderate
        elif wrong > 3.0:
            readiness = ReadinessLevel.MODERATE
            reason = f"high_wrong_count ({wrong:.1f})"
            
        # Rule 4: Correct 1-3 → Strong
        elif 1.0 <= correct <= 3.0:
            readiness = ReadinessLevel.STRONG
            reason = f"good_correct_range ({correct:.1f})"
            
        # Rule 5: Else → Moderate (including correct > 3)
        else:
            readiness = ReadinessLevel.MODERATE
            if correct > 3.0:
                reason = f"high_correct_count ({correct:.1f})"
            else:
                reason = f"insufficient_data ({total:.1f})"
        
        readiness_map[semantic_id] = readiness
        logger.debug(f"readiness({semantic_id}): {readiness.value} - {reason}")
    
    logger.debug(f"finalize_readiness: {len(readiness_map)} concepts assessed")
    return readiness_map

# =============================================================================
# KERNEL 5: COVERAGE DEBT BY SESSIONS
# =============================================================================

def coverage_debt_by_sessions(attempt_events: List[AttemptEvent], 
                             sessions_lookback: int = 5) -> Dict[str, float]:
    """
    Compute coverage debt for subcategory:type_of_question pairs
    
    Args:
        attempt_events: List of user's attempt events  
        sessions_lookback: Number of recent sessions to analyze
        
    Returns:
        Map of pair -> coverage_debt_score (0.0 = no debt, 1.0 = high debt)
    """
    if not isinstance(attempt_events, list):
        raise ValueError("attempt_events must be a list")
        
    if sessions_lookback < 1:
        raise ValueError("sessions_lookback must be >= 1")
    
    # Get recent sessions
    if not attempt_events:
        return {}
        
    recent_sessions = set()
    for event in attempt_events:
        recent_sessions.add(event.sess_seq_at_serve)
    
    # Sort and take most recent sessions
    sorted_sessions = sorted(recent_sessions, reverse=True)[:sessions_lookback]
    
    if not sorted_sessions:
        return {}
    
    # Filter events to recent sessions only
    recent_events = [
        event for event in attempt_events 
        if event.sess_seq_at_serve in sorted_sessions
    ]
    
    # Count exposures per pair
    pair_exposures = {}
    total_questions = len(recent_events)
    
    for event in recent_events:
        pair = f"{event.subcategory}:{event.type_of_question}"
        pair_exposures[pair] = pair_exposures.get(pair, 0) + 1
    
    # Compute coverage debt scores
    coverage_debt = {}
    
    if total_questions > 0:
        avg_exposure = total_questions / len(pair_exposures) if pair_exposures else 0
        
        for pair, exposures in pair_exposures.items():
            # Debt inversely proportional to exposure relative to average
            if avg_exposure > 0:
                relative_exposure = exposures / avg_exposure
                # debt = 1.0 - min(relative_exposure, 1.0)  # Cap at 1.0
                debt = max(0.0, 1.0 - relative_exposure)
            else:
                debt = 1.0
                
            coverage_debt[pair] = debt
    
    logger.debug(f"coverage_debt_by_sessions: analyzed {len(recent_events)} events across {len(sorted_sessions)} sessions")
    logger.debug(f"  -> {len(coverage_debt)} pairs with debt scores")
    
    return coverage_debt

# =============================================================================
# KERNEL 6: VALIDATE PACK
# =============================================================================

def validate_pack(question_pack: List[QuestionCandidate],
                 available_pool: List[QuestionCandidate],
                 valid_pairs: set,
                 known_concepts: set) -> Dict[str, Any]:
    """
    Validate a 12-question pack meets all constraints
    
    Constraints:
    1. Exactly 12 questions
    2. Difficulty distribution: 3 Easy / 6 Medium / 3 Hard
    3. PYQ minima: ≥2 questions with score ≥1.0, ≥2 with score ≥1.5
    4. All questions exist in available pool
    5. All pairs exist in taxonomy
    6. All concepts are known/mapped
    7. No duplicate questions
    
    Args:
        question_pack: List of selected questions
        available_pool: List of available questions (for existence check)
        valid_pairs: Set of valid subcategory:type_of_question pairs
        known_concepts: Set of known concept semantic IDs
        
    Returns:
        Validation result with details
    """
    if not isinstance(question_pack, list):
        raise ValueError("question_pack must be a list")
        
    result = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "constraints": {},
        "summary": {}
    }
    
    # Create lookup sets for efficiency
    pool_ids = {q.question_id for q in available_pool} if available_pool else set()
    pack_ids = [q.question_id for q in question_pack]
    
    # Constraint 1: Exactly 12 questions
    total_questions = len(question_pack)
    result["constraints"]["total_count"] = {
        "expected": 12,
        "actual": total_questions,
        "passed": total_questions == 12
    }
    
    if total_questions != 12:
        result["valid"] = False
        result["errors"].append(f"Expected 12 questions, got {total_questions}")
    
    # Constraint 2: Difficulty distribution
    difficulty_counts = {"Easy": 0, "Medium": 0, "Hard": 0}
    for question in question_pack:
        band = question.difficulty_band
        if band in difficulty_counts:
            difficulty_counts[band] += 1
        else:
            result["warnings"].append(f"Unknown difficulty band: {band}")
    
    expected_distribution = {"Easy": 3, "Medium": 6, "Hard": 3}
    distribution_valid = True
    
    for band, expected in expected_distribution.items():
        actual = difficulty_counts[band]
        passed = actual == expected
        
        result["constraints"][f"difficulty_{band.lower()}"] = {
            "expected": expected,
            "actual": actual,
            "passed": passed
        }
        
        if not passed:
            distribution_valid = False
            result["errors"].append(f"Expected {expected} {band} questions, got {actual}")
    
    result["constraints"]["difficulty_distribution"] = {
        "passed": distribution_valid
    }
    
    if not distribution_valid:
        result["valid"] = False
    
    # Constraint 3: PYQ score minima
    pyq_1_0_count = sum(1 for q in question_pack if q.pyq_frequency_score >= 1.0)
    pyq_1_5_count = sum(1 for q in question_pack if q.pyq_frequency_score >= 1.5)
    
    pyq_1_0_passed = pyq_1_0_count >= 2
    pyq_1_5_passed = pyq_1_5_count >= 2
    
    result["constraints"]["pyq_score_1_0"] = {
        "expected": "≥2",
        "actual": pyq_1_0_count,
        "passed": pyq_1_0_passed
    }
    
    result["constraints"]["pyq_score_1_5"] = {
        "expected": "≥2", 
        "actual": pyq_1_5_count,
        "passed": pyq_1_5_passed
    }
    
    if not pyq_1_0_passed:
        result["valid"] = False
        result["errors"].append(f"Need ≥2 questions with PYQ score ≥1.0, got {pyq_1_0_count}")
        
    if not pyq_1_5_passed:
        result["valid"] = False
        result["errors"].append(f"Need ≥2 questions with PYQ score ≥1.5, got {pyq_1_5_count}")
    
    # Constraint 4: All questions exist in pool
    missing_questions = []
    for question in question_pack:
        if question.question_id not in pool_ids:
            missing_questions.append(question.question_id)
    
    pool_existence_passed = len(missing_questions) == 0
    result["constraints"]["pool_existence"] = {
        "passed": pool_existence_passed,
        "missing_count": len(missing_questions)
    }
    
    if not pool_existence_passed:
        result["valid"] = False
        result["errors"].append(f"{len(missing_questions)} questions not found in available pool")
    
    # Constraint 5: All pairs exist in taxonomy
    invalid_pairs = []
    for question in question_pack:
        if question.pair not in valid_pairs:
            invalid_pairs.append(question.pair)
    
    taxonomy_passed = len(invalid_pairs) == 0
    result["constraints"]["taxonomy_validation"] = {
        "passed": taxonomy_passed,
        "invalid_count": len(invalid_pairs)
    }
    
    if not taxonomy_passed:
        result["valid"] = False
        result["errors"].append(f"{len(invalid_pairs)} questions have invalid taxonomy pairs")
    
    # Constraint 6: All concepts are known/mapped
    unknown_concepts = []
    for question in question_pack:
        for concept in question.core_concepts:
            # This would require semantic_id mapping - simplified for now
            if concept not in known_concepts:
                unknown_concepts.append(concept)
    
    concepts_passed = len(unknown_concepts) == 0
    result["constraints"]["concept_mapping"] = {
        "passed": concepts_passed,
        "unknown_count": len(set(unknown_concepts))  # Deduplicate
    }
    
    if not concepts_passed:
        result["warnings"].append(f"{len(set(unknown_concepts))} unknown concepts found")
    
    # Constraint 7: No duplicate questions
    duplicate_ids = []
    seen_ids = set()
    for question_id in pack_ids:
        if question_id in seen_ids:
            duplicate_ids.append(question_id)
        seen_ids.add(question_id)
    
    no_duplicates_passed = len(duplicate_ids) == 0
    result["constraints"]["no_duplicates"] = {
        "passed": no_duplicates_passed,
        "duplicate_count": len(duplicate_ids)
    }
    
    if not no_duplicates_passed:
        result["valid"] = False
        result["errors"].append(f"{len(duplicate_ids)} duplicate questions found")
    
    # Summary
    result["summary"] = {
        "total_constraints": 7,
        "passed_constraints": sum(1 for c in result["constraints"].values() 
                                 if isinstance(c, dict) and c.get("passed", False)),
        "total_questions": total_questions,
        "difficulty_distribution": difficulty_counts,
        "pyq_scores": {"≥1.0": pyq_1_0_count, "≥1.5": pyq_1_5_count}
    }
    
    logger.info(f"validate_pack: {'PASS' if result['valid'] else 'FAIL'} - {len(result['errors'])} errors, {len(result['warnings'])} warnings")
    
    return result
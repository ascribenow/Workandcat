#!/usr/bin/env python3
"""
Difficulty Score Calculator for Twelvr Questions
New Formula: 0.25×Concepts + 0.50×Steps + 0.25×Operations
Bands: Easy(1.5-1.9), Medium(2.0-3.0), Hard(3.1-5.0)
"""

import re
import json
import logging
from typing import List, Tuple, Union

logger = logging.getLogger(__name__)

def parse_solution_steps(solution_method: str) -> int:
    """
    Parse solution_method to count steps
    
    Args:
        solution_method: The solution method text
        
    Returns:
        int: Number of steps (1-10)
    """
    if not solution_method or not isinstance(solution_method, str):
        return 2  # Default for missing/invalid data
    
    # Count step indicators
    step_patterns = [
        r'step\s*\d+',           # "Step 1", "step 2"
        r'\d+\.\s',              # "1. ", "2. "
        r'•\s',                  # bullet points  
        r'-\s',                  # dashes
        r'first|then|next|finally|after|subsequently', # sequence words
        r'calculate|find|determine|solve|apply',        # action words
    ]
    
    step_count = 0
    text_lower = solution_method.lower()
    
    for pattern in step_patterns:
        matches = re.findall(pattern, text_lower)
        step_count += len(matches)
    
    # If no patterns found, estimate from sentence count
    if step_count == 0:
        sentences = re.split(r'[.!?]+', solution_method)
        meaningful_sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
        step_count = max(2, min(len(meaningful_sentences), 8))
    
    # Apply reasonable bounds
    return max(1, min(step_count, 10))

def safe_parse_json_list(data: Union[str, List, None]) -> List:
    """
    Safely parse JSON string to list, handle various input types
    
    Args:
        data: JSON string, list, or None
        
    Returns:
        List: Parsed list or empty list
    """
    if data is None:
        return []
    
    if isinstance(data, list):
        return data
    
    if isinstance(data, str):
        try:
            parsed = json.loads(data)
            if isinstance(parsed, list):
                return parsed
            else:
                return []
        except (json.JSONDecodeError, TypeError):
            # Try simple comma-separated parsing as fallback
            if ',' in data:
                return [item.strip() for item in data.split(',') if item.strip()]
            return [data.strip()] if data.strip() else []
    
    return []

def calculate_difficulty_score_and_band(core_concepts: Union[str, List, None], 
                                      operations_required: Union[str, List, None], 
                                      steps_count: int) -> Tuple[float, str]:
    """
    Calculate difficulty score and band using the new formula
    
    Formula: 0.25×Concepts + 0.50×Steps + 0.25×Operations
    
    Args:
        core_concepts: List of core concepts (or JSON string)
        operations_required: List of operations (or JSON string)  
        steps_count: Number of solution steps
        
    Returns:
        Tuple[float, str]: (difficulty_score, difficulty_band)
    """
    try:
        # Parse inputs safely
        concepts_list = safe_parse_json_list(core_concepts)
        operations_list = safe_parse_json_list(operations_required)
        
        # Concept Layering (25% weight) - 1-5 scale
        # 1 point per concept, capped at 5
        concept_score = min(5, len(concepts_list)) if concepts_list else 1
        
        # Steps to Solve (50% weight) - 1-5 scale  
        if steps_count <= 2:
            steps_score = 2.0
        elif steps_count <= 4:
            steps_score = 3.0
        else:
            steps_score = 5.0
        
        # Operations Required (25% weight) - 1-5 scale
        # 1 point per operation, capped at 5
        ops_score = min(5, len(operations_list)) if operations_list else 1
        
        # Calculate composite score using specified weights
        difficulty_score = (0.25 * concept_score) + (0.50 * steps_score) + (0.25 * ops_score)
        
        # Determine band based on specified ranges
        if difficulty_score <= 1.9:
            band = "Easy"
        elif difficulty_score <= 3.0:
            band = "Medium"
        else:
            band = "Hard"
        
        # Round to 2 decimal places for consistency
        difficulty_score = round(difficulty_score, 2)
        
        logger.debug(f"Difficulty calculation: Concepts={len(concepts_list)}/{concept_score}, Steps={steps_count}/{steps_score}, Ops={len(operations_list)}/{ops_score} → Score={difficulty_score}, Band={band}")
        
        return difficulty_score, band
        
    except Exception as e:
        logger.error(f"Error in difficulty calculation: {e}")
        # Return safe defaults
        return 2.5, "Medium"

def get_difficulty_statistics(core_concepts: Union[str, List, None], 
                            operations_required: Union[str, List, None], 
                            steps_count: int) -> dict:
    """
    Get detailed statistics about difficulty calculation components
    
    Args:
        core_concepts: List of core concepts (or JSON string)
        operations_required: List of operations (or JSON string)
        steps_count: Number of solution steps
        
    Returns:
        dict: Detailed breakdown of calculation
    """
    concepts_list = safe_parse_json_list(core_concepts)
    operations_list = safe_parse_json_list(operations_required)
    
    concept_score = min(5, len(concepts_list)) if concepts_list else 1
    
    if steps_count <= 2:
        steps_score = 2.0
    elif steps_count <= 4:
        steps_score = 3.0
    else:
        steps_score = 5.0
    
    ops_score = min(5, len(operations_list)) if operations_list else 1
    
    difficulty_score = (0.25 * concept_score) + (0.50 * steps_score) + (0.25 * ops_score)
    
    if difficulty_score <= 1.9:
        band = "Easy"
    elif difficulty_score <= 3.0:
        band = "Medium"
    else:
        band = "Hard"
    
    return {
        "components": {
            "concepts": {
                "count": len(concepts_list),
                "score": concept_score,
                "weight": 0.25,
                "contribution": round(0.25 * concept_score, 2)
            },
            "steps": {
                "count": steps_count,
                "score": steps_score,
                "weight": 0.50,
                "contribution": round(0.50 * steps_score, 2)
            },
            "operations": {
                "count": len(operations_list),
                "score": ops_score,
                "weight": 0.25,
                "contribution": round(0.25 * ops_score, 2)
            }
        },
        "total_score": round(difficulty_score, 2),
        "difficulty_band": band,
        "band_ranges": {
            "Easy": "1.5 - 1.9",
            "Medium": "2.0 - 3.0", 
            "Hard": "3.1 - 5.0"
        }
    }

# Test function for validation
def test_difficulty_calculation():
    """Test the difficulty calculation with sample data"""
    test_cases = [
        {
            "name": "Simple Easy Question",
            "core_concepts": ["basic arithmetic"],
            "operations_required": ["addition"],
            "steps": 2,
            "expected_band": "Easy"
        },
        {
            "name": "Complex Hard Question", 
            "core_concepts": ["algebra", "geometry", "trigonometry", "calculus"],
            "operations_required": ["solve equations", "calculate areas", "apply theorems", "integrate", "differentiate"],
            "steps": 8,
            "expected_band": "Hard"
        },
        {
            "name": "Medium Question",
            "core_concepts": ["percentages", "ratios"],
            "operations_required": ["calculate percentage", "cross multiply"],
            "steps": 3,
            "expected_band": "Medium"
        }
    ]
    
    print("🧪 Testing Difficulty Calculator")
    print("=" * 50)
    
    for test in test_cases:
        score, band = calculate_difficulty_score_and_band(
            test["core_concepts"], 
            test["operations_required"], 
            test["steps"]
        )
        
        status = "✅" if band == test["expected_band"] else "❌"
        print(f"{status} {test['name']}: {band} ({score}) - Expected: {test['expected_band']}")
        
        stats = get_difficulty_statistics(test["core_concepts"], test["operations_required"], test["steps"])
        print(f"   Components: C={stats['components']['concepts']['contribution']}, S={stats['components']['steps']['contribution']}, O={stats['components']['operations']['contribution']}")
        print()

if __name__ == "__main__":
    test_difficulty_calculation()
"""
V2 Planner Contract - CANONICAL & ONLY SUPPORTED FORMAT

This is the FROZEN contract for all planner interactions.
NO legacy V1 parsing. NO adapters. NO compatibility layers.

V2 Philosophy:
- Planner ONLY reorders existing candidates (no membership changes)  
- Deterministic fallback is part of the spec (not emergency measure)
- Fast, indexed candidate selection replaces ORDER BY RANDOM()
- Single source of truth for all planner operations
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from enum import Enum

# V2 Contract - The ONLY supported planner response format
class V2PlannerResponse(BaseModel):
    """
    V2 Planner Response - CANONICAL CONTRACT
    
    The planner receives 12 candidate IDs and returns them in optimized order.
    - NO membership changes allowed (set(input_ids) == set(output_ids))  
    - NO additional fields beyond ordering
    - Timeout/failure → deterministic seeded fallback (not error)
    """
    version: str = Field("v2", description="Contract version - MUST be 'v2'")
    order: List[str] = Field(..., description="Exactly 12 UUIDs in optimized order")
    
    @validator('version')
    def version_must_be_v2(cls, v):
        if v != "v2":
            raise ValueError("Only version 'v2' is supported")
        return v
    
    @validator('order')
    def validate_order(cls, v):
        if len(v) != 12:
            raise ValueError("Order must contain exactly 12 UUIDs")
        if len(set(v)) != 12:
            raise ValueError("Order must contain 12 unique UUIDs")
        return v

# V2 Candidate Selection Result
class V2CandidateSelection(BaseModel):
    """V2 Candidate Pool - Light metadata for planner input"""
    ids: List[str] = Field(..., description="Exactly 12 selected candidate IDs")
    seed: int = Field(..., description="Deterministic seed for reproducibility")
    selection_meta: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('ids')
    def validate_ids(cls, v):
        if len(v) != 12:
            raise ValueError("Must select exactly 12 candidates")
        return v

# V2 Pack Assembly (Final Output)  
class V2PackItem(BaseModel):
    """V2 Pack Item - Full question data for frontend consumption"""
    item_id: str = Field(..., description="Question UUID")
    why: str = Field(..., description="Question stem/content")
    bucket: str = Field(..., description="Difficulty: easy|medium|hard")
    pair: str = Field(..., description="Subcategory:Type")
    pyq_frequency_score: float = Field(..., description="PYQ score: 0.5|1.0|1.5")
    semantic_concepts: List[str] = Field(default_factory=list)
    # V2 Frontend Compatibility Fields
    option_a: str = Field("Option A", description="MCQ Option A")
    option_b: str = Field("Option B", description="MCQ Option B") 
    option_c: str = Field("Option C", description="MCQ Option C")
    option_d: str = Field("Option D", description="MCQ Option D")
    answer: str = Field("", description="Clean correct answer (from answer field only)")
    subcategory: str = Field("Unknown", description="Question subcategory")
    difficulty_band: str = Field("Medium", description="Difficulty band")
    # Solution feedback fields for educational content
    snap_read: str = Field("", description="Quick overview")
    solution_approach: str = Field("", description="Step-by-step approach")
    detailed_solution: str = Field("", description="Complete solution")
    principle_to_remember: str = Field("", description="Key learning principle")

class V2Pack(BaseModel):
    """V2 Complete Pack - Ready for frontend consumption"""
    items: List[V2PackItem] = Field(..., description="Exactly 12 questions in order")
    meta: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('items')
    def validate_pack_size(cls, v):
        if len(v) != 12:
            raise ValueError("Pack must contain exactly 12 items")
        return v

# V2 Constraint Validation
class V2ConstraintReport(BaseModel):
    """V2 Constraint Validation Results"""
    met: List[str] = Field(default_factory=list, description="Constraints satisfied")
    violated: List[str] = Field(default_factory=list, description="Constraints violated") 
    planner_fallback: bool = Field(False, description="True if deterministic fallback used")
    processing_time_ms: int = Field(0, description="Total processing time")
    retry_used: int = Field(0, description="Number of retries used")
    llm_model_used: str = Field("", description="Model used for planning")

# V2 System Status
class PlannerStatus(str, Enum):
    """V2 Planner execution status"""
    SUCCESS = "success"
    TIMEOUT = "timeout" 
    SCHEMA_INVALID = "schema_invalid"
    MEMBERSHIP_VIOLATION = "membership_violation"
    FALLBACK_USED = "fallback_used"

# V2 Contract Validation Functions
def validate_membership_equality(input_ids: List[str], output_ids: List[str]) -> bool:
    """
    V2 CORE RULE: Planner cannot change membership
    Returns True if sets are identical, False otherwise
    """
    return set(input_ids) == set(output_ids)

def validate_pack_constraints(pack: V2Pack) -> V2ConstraintReport:
    """
    V2 Constraint validation - 3/6/3 distribution + PYQ minima
    """
    items = pack.items
    
    # Count by difficulty
    difficulty_counts = {"easy": 0, "medium": 0, "hard": 0}
    for item in items:
        bucket = item.bucket.lower()
        if bucket in difficulty_counts:
            difficulty_counts[bucket] += 1
    
    # Count PYQ requirements
    pyq_10_count = sum(1 for item in items if item.pyq_frequency_score >= 1.0)
    pyq_15_count = sum(1 for item in items if item.pyq_frequency_score >= 1.5)
    
    # Validate constraints
    met = []
    violated = []
    
    if difficulty_counts["easy"] == 3:
        met.append("easy_count_3")
    else:
        violated.append(f"easy_count_{difficulty_counts['easy']}_not_3")
    
    if difficulty_counts["medium"] == 6:
        met.append("medium_count_6") 
    else:
        violated.append(f"medium_count_{difficulty_counts['medium']}_not_6")
        
    if difficulty_counts["hard"] == 3:
        met.append("hard_count_3")
    else:
        violated.append(f"hard_count_{difficulty_counts['hard']}_not_3")
    
    if pyq_10_count >= 2:
        met.append("pyq_10_min_2")
    else:
        violated.append(f"pyq_10_count_{pyq_10_count}_less_than_2")
        
    if pyq_15_count >= 2:
        met.append("pyq_15_min_2")
    else:
        violated.append(f"pyq_15_count_{pyq_15_count}_less_than_2")
    
    return V2ConstraintReport(
        met=met,
        violated=violated
    )

# V2 Schema Definitions for LLM  
V2_PLANNER_SCHEMA = {
    "type": "object",
    "properties": {
        "version": {
            "type": "string", 
            "enum": ["v2"],
            "description": "Contract version - must be 'v2'"
        },
        "order": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 12,
            "maxItems": 12,
            "description": "Exactly 12 UUIDs in optimized learning order"
        }
    },
    "required": ["version", "order"],
    "additionalProperties": False
}

V2_PLANNER_PROMPT = """You are an expert adaptive learning planner. Your task is to reorder 12 question IDs for optimal learning progression.

CONSTRAINTS (NEVER VIOLATE):
- Return exactly 12 UUIDs in optimized order
- Do not add, remove, or change any IDs
- Prioritize adaptive learning principles

OUTPUT FORMAT (max 200 tokens):
{
  "version": "v2",
  "order": ["uuid-1", "uuid-2", ..., "uuid-12"]
}

Return ONLY valid JSON matching this exact format."""
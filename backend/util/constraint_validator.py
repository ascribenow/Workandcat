"""
Constraint Validation Utilities
Ensures hard constraints are never relaxed
"""

# Forbidden relaxations that should never occur
FORBIDDEN_RELAXATIONS = {"band_shape", "pyq_1.0", "pyq_1.5"}

def assert_no_forbidden_relaxations(constraint_report: dict):
    """
    Assert that no forbidden relaxations are present in constraint report
    
    Args:
        constraint_report: Dictionary containing constraint validation results
        
    Raises:
        ValueError: If forbidden relaxations are found
    """
    relaxed = {r.get("name") for r in constraint_report.get("relaxed", [])}
    illegal = relaxed & FORBIDDEN_RELAXATIONS
    if illegal:
        raise ValueError(f"FORBIDDEN_RELAXATION:{','.join(sorted(illegal))}")

def validate_pack_constraints(pack_data: list, constraint_report: dict):
    """
    Validate pack meets all hard constraints
    
    Args:
        pack_data: List of questions in the pack
        constraint_report: Constraint validation results
        
    Raises:
        ValueError: If constraints are violated
    """
    # Check forbidden relaxations first
    assert_no_forbidden_relaxations(constraint_report)
    
    # Validate pack shape (3-6-3)
    easy_count = sum(1 for item in pack_data if item.get("bucket") == "Easy")
    medium_count = sum(1 for item in pack_data if item.get("bucket") == "Medium") 
    hard_count = sum(1 for item in pack_data if item.get("bucket") == "Hard")
    
    if len(pack_data) != 12:
        raise ValueError(f"PACK_SIZE_VIOLATION: Expected 12 questions, got {len(pack_data)}")
    
    if easy_count != 3 or medium_count != 6 or hard_count != 3:
        raise ValueError(f"BAND_SHAPE_VIOLATION: Expected 3-6-3, got {easy_count}-{medium_count}-{hard_count}")
    
    # Validate PYQ minima (≥2 @ 1.0, ≥2 @ 1.5)
    pyq_10_count = sum(1 for item in pack_data 
                      if item.get("why", {}).get("pyq_frequency_score") == 1.0)
    pyq_15_count = sum(1 for item in pack_data 
                      if item.get("why", {}).get("pyq_frequency_score") == 1.5)
    
    if pyq_10_count < 2:
        raise ValueError(f"PYQ_1_0_VIOLATION: Expected ≥2 questions with PYQ score 1.0, got {pyq_10_count}")
    
    if pyq_15_count < 2:
        raise ValueError(f"PYQ_1_5_VIOLATION: Expected ≥2 questions with PYQ score 1.5, got {pyq_15_count}")

def validate_constraint_met_list(constraint_report: dict):
    """
    Validate that required constraints are in the 'met' list
    
    Args:
        constraint_report: Constraint validation results
        
    Raises:
        ValueError: If required constraints are not met
    """
    required_met = {"band_shape", "pyq_1.0", "pyq_1.5"}
    met_constraints = {c for c in constraint_report.get("met", [])}
    missing = required_met - met_constraints
    
    if missing:
        raise ValueError(f"REQUIRED_CONSTRAINTS_NOT_MET:{','.join(sorted(missing))}")
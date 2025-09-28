"""
Concept label mapping for human readability
"""

# Map concept_norm -> canonical_label for better UX
CONCEPT_LABELS = {
    # Time, Speed & Distance
    "Time-Speed-Distance": "Time, Speed & Distance",
    "Time-Speed-Distance:Relative Speed": "Relative Speed Problems",
    "Time-Speed-Distance:Train Problems": "Train Speed Problems",
    "Time-Speed-Distance:Boat Problems": "Boat & Stream Problems",
    
    # Arithmetic
    "Arithmetic": "Basic Arithmetic",
    "Arithmetic:Percentage": "Percentage Calculations",
    "Arithmetic:Ratio-Proportion": "Ratio & Proportion",
    "Arithmetic:Partnership": "Partnership Problems",
    "Arithmetic:Interest": "Simple & Compound Interest",
    
    # Algebra
    "Algebra": "Algebraic Problems",
    "Algebra:Linear Equations": "Linear Equations",
    "Algebra:Quadratic Equations": "Quadratic Equations",
    
    # Geometry
    "Geometry": "Geometry Problems",
    "Geometry:Area": "Area Calculations",
    "Geometry:Volume": "Volume & Surface Area",
    "Geometry:Coordinate": "Coordinate Geometry",
    
    # Mensuration
    "Mensuration 2D": "2D Mensuration",
    "Mensuration 2D:Area Rectangle": "Rectangle Area Problems",
    "Mensuration 2D:Area Circle": "Circle Area Problems",
    "Mensuration 3D": "3D Mensuration",
    
    # Number Systems
    "Number Systems": "Number Theory",
    "Number Systems:Prime Numbers": "Prime Number Problems",
    "Number Systems:Divisibility": "Divisibility Rules",
    
    # Probability
    "Probability": "Probability Problems",
    "Probability:Basic": "Basic Probability",
    "Probability:Conditional": "Conditional Probability",
    
    # Data Interpretation
    "Data Interpretation": "Data Analysis",
    "Data Interpretation:Tables": "Table Analysis",
    "Data Interpretation:Graphs": "Graph Analysis",
    
    # Logical Reasoning
    "Logical Reasoning": "Logic Problems",
    "Logical Reasoning:Sequences": "Number Sequences",
    "Logical Reasoning:Arrangements": "Arrangement Problems"
}

def get_concept_label(concept_norm: str) -> str:
    """
    Get human-readable label for concept_norm
    Fallback to concept_norm if no mapping exists
    """
    if not concept_norm:
        return "General Practice"
    
    return CONCEPT_LABELS.get(concept_norm, concept_norm)

def get_concept_labels(concept_norms: list) -> list:
    """Get labels for a list of concept_norms"""
    return [get_concept_label(concept) for concept in concept_norms]
#!/usr/bin/env python3
"""
Advanced Canonical Taxonomy Mapping Script
Uses intelligent mapping from the complete 129 canonical Types from CSV

This script analyzes question content and assigns proper canonical Types
based on question stem analysis and keyword matching.
"""

import sys
import os
sys.path.append('/app/backend')

from database import *
from llm_enrichment import CANONICAL_TAXONOMY
from sqlalchemy.orm import sessionmaker
import uuid
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Advanced Type mapping based on question content analysis
INTELLIGENT_TYPE_MAPPING = {
    # Time-Speed-Distance Types
    "time-speed-distance": {
        "basic": ["speed", "distance", "time", "km/h", "m/s", "calculate speed", "calculate distance", "calculate time"],
        "relative_speed": ["relative", "opposite direction", "same direction", "meet", "cross", "faster", "slower"],
        "circular_track": ["circular", "track", "round", "lap", "overtake", "meet again"],
        "boats_streams": ["boat", "stream", "current", "upstream", "downstream", "still water"],
        "trains": ["train", "platform", "bridge", "length", "cross", "tunnel"],
        "races": ["race", "start", "lead", "advantage", "meter start", "head start"]
    },
    
    # Percentages Types
    "percentages": {
        "basics": ["percent", "%", "percentage", "of", "is what percent"],
        "percentage_change": ["increase", "decrease", "rise", "fall", "change", "by what percent"],
        "successive_change": ["successive", "two", "first", "then", "overall", "net"]
    },
    
    # Profit-Loss-Discount Types
    "profit_loss": {
        "basics": ["profit", "loss", "cost price", "selling price", "cp", "sp", "gain"],
        "successive": ["successive", "two discounts", "first discount", "then"],
        "marked_price": ["marked price", "mp", "list price", "discount"],
        "discount_chains": ["chain", "series", "multiple discounts"]
    },
    
    # Linear Equations Types
    "linear_equations": {
        "two_variable": ["x", "y", "two variables", "system", "equation"],
        "three_variable": ["x", "y", "z", "three variables"],
        "dependent": ["dependent", "inconsistent", "infinite", "no solution"]
    },
    
    # Quadratic Equations Types
    "quadratic": {
        "roots": ["roots", "x²", "quadratic", "discriminant", "nature of roots"],
        "sum_product": ["sum of roots", "product of roots", "relationship"],
        "max_min": ["maximum", "minimum", "vertex", "parabola"]
    },
    
    # Geometry Types
    "triangles": {
        "properties": ["triangle", "angles", "sides", "median", "bisector"],
        "congruence": ["congruent", "similar", "similarity", "sss", "sas", "asa"],
        "pythagoras": ["right triangle", "hypotenuse", "pythagoras", "right angle"],
        "centers": ["incenter", "circumcenter", "centroid", "orthocenter"]
    },
    
    # Mensuration Types
    "mensuration_2d": {
        "area_triangle": ["area", "triangle", "base", "height"],
        "area_rectangle": ["area", "rectangle", "length", "width", "breadth"],
        "area_circle": ["area", "circle", "radius", "diameter", "π", "pi"],
        "area_trapezium": ["trapezium", "parallel sides"],
        "sector": ["sector", "arc", "central angle"]
    },
    
    "mensuration_3d": {
        "volume_cube": ["volume", "cube", "side"],
        "volume_cuboid": ["volume", "cuboid", "length", "breadth", "height"],
        "volume_cylinder": ["volume", "cylinder", "radius", "height"],
        "volume_cone": ["volume", "cone", "radius", "height"],
        "volume_sphere": ["volume", "sphere", "radius"],
        "surface_areas": ["surface area", "total surface", "curved surface"]
    },
    
    # Number System Types
    "number_properties": {
        "perfect_squares": ["square", "perfect square", "square root", "√"],
        "perfect_cubes": ["cube", "perfect cube", "cube root", "∛"]
    },
    
    "divisibility": {
        "basic_rules": ["divisible", "remainder", "factor", "multiple"],
        "factorization": ["factors", "prime", "composite", "factorize"]
    },
    
    # Probability Types
    "probability": {
        "classical": ["probability", "coin", "dice", "card", "favorable", "total"],
        "conditional": ["conditional", "given", "dependent", "independent"],
        "bayes": ["bayes", "theorem", "prior", "posterior"]
    },
    
    # Permutation-Combination Types
    "permutation_combination": {
        "basics": ["permutation", "combination", "arrange", "select", "nPr", "nCr"],
        "circular": ["circular", "round table", "circular arrangement"],
        "restrictions": ["restriction", "together", "apart", "specific position"]
    }
}

def analyze_question_content(stem: str, subcategory: str) -> str:
    """
    Analyze question stem to determine the most appropriate canonical Type
    """
    stem_lower = stem.lower()
    subcategory_lower = subcategory.lower().replace(' ', '_').replace('-', '_')
    
    # Map subcategory to type category
    if 'time' in subcategory_lower and 'speed' in subcategory_lower:
        type_category = "time-speed-distance"
    elif 'percentage' in subcategory_lower:
        type_category = "percentages"
    elif 'profit' in subcategory_lower or 'loss' in subcategory_lower:
        type_category = "profit_loss"
    elif 'linear' in subcategory_lower:
        type_category = "linear_equations"
    elif 'quadratic' in subcategory_lower:
        type_category = "quadratic"
    elif 'triangle' in subcategory_lower:
        type_category = "triangles"
    elif 'mensuration' in subcategory_lower and '2d' in subcategory_lower:
        type_category = "mensuration_2d"
    elif 'mensuration' in subcategory_lower and '3d' in subcategory_lower:
        type_category = "mensuration_3d"
    elif 'number' in subcategory_lower:
        type_category = "number_properties"
    elif 'divisibility' in subcategory_lower:
        type_category = "divisibility"
    elif 'probability' in subcategory_lower:
        type_category = "probability"
    elif 'permutation' in subcategory_lower or 'combination' in subcategory_lower:
        type_category = "permutation_combination"
    else:
        # Default analysis based on content
        type_category = "general"
    
    # Get type mappings for this category
    type_mappings = INTELLIGENT_TYPE_MAPPING.get(type_category, {})
    
    # Score each type based on keyword matches
    type_scores = {}
    for type_name, keywords in type_mappings.items():
        score = 0
        for keyword in keywords:
            if keyword.lower() in stem_lower:
                score += 1
        if score > 0:
            type_scores[type_name] = score
    
    # Return the highest scoring type
    if type_scores:
        best_type = max(type_scores, key=type_scores.get)
        # Convert to canonical format
        return convert_to_canonical_type(best_type, subcategory)
    
    # Fallback to subcategory-based mapping
    return get_canonical_type_for_subcategory(subcategory)

def convert_to_canonical_type(type_key: str, subcategory: str) -> str:
    """Convert internal type key to canonical taxonomy type"""
    
    # Mapping from analysis keys to canonical types
    canonical_mapping = {
        # Time-Speed-Distance
        "basic": "Basics",
        "relative_speed": "Relative Speed", 
        "circular_track": "Circular Track Motion",
        "boats_streams": "Boats and Streams",
        "trains": "Trains",
        "races": "Races",
        
        # Percentages
        "basics": "Basics",
        "percentage_change": "Percentage Change",
        "successive_change": "Successive Percentage Change",
        
        # Linear Equations
        "two_variable": "Two variable systems",
        "three_variable": "Three variable systems",
        "dependent": "Dependent and Inconsistent Systems",
        
        # Quadratic
        "roots": "Roots & Nature of Roots",
        "sum_product": "Sum and Product of Roots",
        "max_min": "Maximum and Minimum Values",
        
        # Triangles
        "properties": "Properties (Angles, Sides, Medians, Bisectors)",
        "congruence": "Congruence & Similarity",
        "pythagoras": "Pythagoras & Converse",
        "centers": "Inradius, Circumradius, Orthocentre",
        
        # Mensuration 2D
        "area_triangle": "Area Triangle",
        "area_rectangle": "Area Rectangle", 
        "area_circle": "Area Circle",
        "area_trapezium": "Area Trapezium",
        "sector": "Sector",
        
        # Mensuration 3D
        "volume_cube": "Volume Cubes",
        "volume_cuboid": "Volume Cuboid",
        "volume_cylinder": "Volume Cylinder",
        "volume_cone": "Volume Cone", 
        "volume_sphere": "Volume Sphere",
        "surface_areas": "Surface Areas",
        
        # Number Properties
        "perfect_squares": "Perfect Squares",
        "perfect_cubes": "Perfect Cubes",
        
        # Probability
        "classical": "Classical Probability",
        "conditional": "Conditional Probability",
        "bayes": "Bayes' Theorem",
        
        # Permutation-Combination
        "basics": "Basics",
        "circular": "Circular Permutations",
        "restrictions": "Permutations with Restrictions"
    }
    
    canonical_type = canonical_mapping.get(type_key, "Basics")
    
    # Validate against actual canonical taxonomy
    for category, subcats in CANONICAL_TAXONOMY.items():
        if subcategory in subcats:
            available_types = subcats[subcategory]
            if canonical_type in available_types:
                return canonical_type
            else:
                # Return first available type if mapping doesn't match
                return available_types[0]
    
    return "Basics"  # Ultimate fallback

def get_canonical_type_for_subcategory(subcategory: str) -> str:
    """Get the first canonical type available for a subcategory"""
    for category, subcats in CANONICAL_TAXONOMY.items():
        if subcategory in subcats:
            return subcats[subcategory][0]  # Return first available type
    
    return "Basics"  # Fallback

def update_questions_with_intelligent_types(db: Session):
    """Update all questions with intelligent canonical Type assignment"""
    logger.info("Starting intelligent canonical Type assignment...")
    
    questions = db.query(Question).all()
    total_updated = 0
    type_distribution = {}
    
    for question in questions:
        try:
            # Analyze question content to determine best canonical Type
            intelligent_type = analyze_question_content(
                question.stem or "",
                question.subcategory or ""
            )
            
            # Update question with intelligent Type
            question.type_of_question = intelligent_type
            type_distribution[intelligent_type] = type_distribution.get(intelligent_type, 0) + 1
            total_updated += 1
            
            if total_updated % 100 == 0:
                logger.info(f"Processed {total_updated} questions...")
                db.commit()  # Commit in batches
                
        except Exception as e:
            logger.error(f"Error processing question {question.id}: {e}")
            continue
    
    # Final commit
    db.commit()
    
    logger.info(f"✅ Updated {total_updated} questions with intelligent Types")
    logger.info(f"✅ Type distribution: {len(type_distribution)} unique types")
    
    # Show top types
    sorted_types = sorted(type_distribution.items(), key=lambda x: x[1], reverse=True)
    logger.info("✅ Top 10 Types assigned:")
    for type_name, count in sorted_types[:10]:
        logger.info(f"   - {type_name}: {count} questions")
    
    return len(type_distribution)

def main():
    """Run advanced canonical taxonomy mapping"""
    logger.info("🚀 Starting Advanced Canonical Taxonomy Mapping...")
    
    # Initialize database
    init_database()
    db = SessionLocal()
    
    try:
        # Update questions with intelligent Type assignment
        unique_types = update_questions_with_intelligent_types(db)
        
        # Validation
        if unique_types >= 20:  # Expect at least 20 different canonical types
            logger.info("🎉 Advanced Canonical Mapping SUCCESSFUL!")
            logger.info(f"✅ {unique_types} unique canonical Types assigned")
            logger.info("✅ Questions analyzed with content-based Type assignment") 
            logger.info("✅ Type-based session generation ready with diversity")
        else:
            logger.warning(f"⚠️ Only {unique_types} unique types assigned - may need more mapping")
            
    except Exception as e:
        logger.error(f"Advanced mapping failed: {e}")
        db.rollback()
        return 1
    finally:
        db.close()
    
    return 0

if __name__ == "__main__":
    exit(main())
#!/usr/bin/env python3
"""
Efficient Type Field Migration Script
Fixes the incomplete taxonomy triple migration using batch processing
"""

import sys
import os
sys.path.append('/app/backend')

from database import *
from llm_enrichment import CANONICAL_TAXONOMY
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import uuid
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simplified Type mapping for efficiency
TYPE_MAPPINGS = {
    "Speed Calculation": "Basics",
    "Basic TSD": "Basics", 
    "Percentage Problem": "Basics",
    "Percentage": "Basics",
    "Linear Equation": "Two variable systems",
    "Addition": "Perfect Squares",
    "Subtraction": "Perfect Squares",
    "Multiplication": "Perfect Squares", 
    "Division": "Perfect Squares",
    "Square": "Perfect Squares",
    "Square Root": "Perfect Squares",
    "Cube": "Perfect Cubes",
    "Area": "Area Rectangle",
    "Perimeter": "Area Rectangle",
    "Calculation": "Basics",
    "Basics": "Basics"
}

def get_canonical_type_for_subcategory(subcategory: str, legacy_type: str = None) -> str:
    """Get canonical type for a given subcategory"""
    # Find the subcategory in canonical taxonomy
    for category, subcats in CANONICAL_TAXONOMY.items():
        if subcategory in subcats:
            available_types = subcats[subcategory]
            
            # Use mapped legacy type if available
            if legacy_type and legacy_type in TYPE_MAPPINGS:
                canonical_type = TYPE_MAPPINGS[legacy_type]
                if canonical_type in available_types:
                    return canonical_type
            
            # Default to first available type
            return available_types[0]
    
    # Fallback
    return "Basics"

def update_questions_in_batches(db: Session):
    """Update all questions with canonical types in efficient batches"""
    logger.info("Updating questions with canonical types...")
    
    # Use raw SQL for efficiency
    update_queries = []
    
    # Get all questions that need type updates
    questions = db.query(Question).all()
    batch_size = 50
    total_updated = 0
    
    for i in range(0, len(questions), batch_size):
        batch = questions[i:i + batch_size]
        
        for question in batch:
            # Get canonical type for this question
            canonical_type = get_canonical_type_for_subcategory(
                question.subcategory, 
                question.type_of_question
            )
            
            # Update the question
            question.type_of_question = canonical_type
            total_updated += 1
        
        # Commit batch
        db.commit()
        
        if total_updated % 100 == 0:
            logger.info(f"Updated {total_updated} questions...")
    
    logger.info(f"✅ Updated {total_updated} questions with canonical types")

def update_pyq_questions_in_batches(db: Session):
    """Update PYQ questions with canonical types in efficient batches"""
    logger.info("Updating PYQ questions with canonical types...")
    
    pyq_questions = db.query(PYQQuestion).all()
    total_updated = 0
    
    for pyq_question in pyq_questions:
        # Get canonical type for this PYQ question
        canonical_type = get_canonical_type_for_subcategory(
            pyq_question.subcategory,
            pyq_question.type_of_question
        )
        
        # Update the PYQ question
        pyq_question.type_of_question = canonical_type
        total_updated += 1
    
    # Commit all PYQ updates
    db.commit()
    logger.info(f"✅ Updated {total_updated} PYQ questions with canonical types")

def validate_type_coverage(db: Session):
    """Validate that all questions have canonical types"""
    logger.info("Validating type coverage...")
    
    # Check Question coverage
    questions = db.query(Question).all()
    questions_with_types = len([q for q in questions if q.type_of_question])
    
    logger.info(f"✅ Questions with types: {questions_with_types}/{len(questions)}")
    
    # Check unique types
    unique_types = set()
    canonical_count = 0
    
    for question in questions:
        if question.type_of_question:
            unique_types.add(question.type_of_question)
            
            # Check if canonical
            for cat, subcats in CANONICAL_TAXONOMY.items():
                if question.subcategory in subcats:
                    if question.type_of_question in subcats[question.subcategory]:
                        canonical_count += 1
                        break
    
    logger.info(f"✅ Unique types: {len(unique_types)}")
    logger.info(f"✅ Canonical compliance: {canonical_count}/{len(questions)} ({canonical_count/len(questions)*100:.1f}%)")
    
    # Show sample types
    sample_types = list(unique_types)[:10]
    logger.info(f"✅ Sample types: {sample_types}")
    
    return canonical_count / len(questions) >= 0.95  # 95% threshold

def main():
    """Run efficient type migration"""
    logger.info("🚀 Starting Efficient Type Migration...")
    
    # Initialize database
    init_database()
    db = SessionLocal()
    
    try:
        # Step 1: Update questions with canonical types
        update_questions_in_batches(db)
        
        # Step 2: Update PYQ questions with canonical types
        update_pyq_questions_in_batches(db)
        
        # Step 3: Validate coverage
        success = validate_type_coverage(db)
        
        if success:
            logger.info("🎉 Efficient Type Migration SUCCESSFUL!")
            logger.info("✅ 95%+ canonical type coverage achieved")
            logger.info("✅ All questions have type_of_question field populated")
            logger.info("✅ PYQ questions updated with canonical types")
            logger.info("✅ Type-based session generation ready for testing")
        else:
            logger.error("❌ Migration validation failed - coverage below 95%")
            return 1
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        db.rollback()
        return 1
    finally:
        db.close()
    
    return 0

if __name__ == "__main__":
    exit(main())
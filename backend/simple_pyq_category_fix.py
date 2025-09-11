#!/usr/bin/env python3
"""
Simple PYQ Category Fix
Map common subcategories to their parent categories
"""

# Create subcategory to category mapping based on canonical taxonomy
SUBCATEGORY_TO_CATEGORY = {
    # Arithmetic subcategories
    "Time-Speed-Distance": "Arithmetic",
    "Time-Work": "Arithmetic", 
    "Ratios and Proportions": "Arithmetic",
    "Percentages": "Arithmetic",
    "Averages and Alligation": "Arithmetic",
    "Profit-Loss-Discount": "Arithmetic",
    "Simple and Compound Interest": "Arithmetic",
    "Mixtures and Solutions": "Arithmetic",
    
    # Algebra subcategories  
    "Linear Equations": "Algebra",
    "Quadratic Equations": "Algebra",
    "Inequalities": "Algebra",
    "Functions and Graphs": "Algebra",
    "Progressions": "Algebra",
    "Special Algebraic Identities": "Algebra",
    
    # Geometry and Mensuration subcategories
    "Circles": "Geometry and Mensuration",
    "Triangles": "Geometry and Mensuration", 
    "Mensuration 3D": "Geometry and Mensuration",
    
    # Number System subcategories
    "Number Properties": "Number System"
}

import sys
import os
sys.path.append('/app/backend')

from database import SessionLocal, PYQQuestion
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_pyq_categories_simple():
    """Simple fix for PYQ categories using direct mapping"""
    
    db = SessionLocal()
    try:
        updated_count = 0
        
        for subcategory, category in SUBCATEGORY_TO_CATEGORY.items():
            # Update all questions with this subcategory
            questions_updated = db.query(PYQQuestion).filter(
                PYQQuestion.subcategory == subcategory,
                PYQQuestion.category.is_(None)
            ).update(
                {PYQQuestion.category: category},
                synchronize_session=False
            )
            
            if questions_updated > 0:
                logger.info(f"✅ Updated {questions_updated} questions: {subcategory} → {category}")
                updated_count += questions_updated
        
        db.commit()
        logger.info(f"✅ Total updated: {updated_count} PYQ questions")
        
        # Verification
        verification = db.query(PYQQuestion).filter(
            PYQQuestion.category.isnot(None)
        ).limit(5).all()
        
        logger.info("🔍 Verification - Updated records:")
        for q in verification:
            logger.info(f"   {q.category} → {q.subcategory}")
            
        return updated_count
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        db.rollback()
        return 0
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("🔧 SIMPLE PYQ CATEGORY FIX")
    logger.info("=" * 50)
    
    updated = fix_pyq_categories_simple()
    
    logger.info("=" * 50)
    logger.info(f"📊 RESULT: Updated {updated} questions")
    
    if updated > 0:
        logger.info("🎉 PYQ category fix completed!")
    else:
        logger.error("❌ No updates made")
#!/usr/bin/env python3
"""
Fix PYQ Category Data
Populate missing category fields in PYQ questions based on subcategory mapping
"""

import sys
import os
sys.path.append('/app/backend')

from database import SessionLocal, PYQQuestion
from canonical_taxonomy_data import CANONICAL_TAXONOMY
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_subcategory_to_category_mapping():
    """Create mapping from subcategory to parent category"""
    mapping = {}
    for category, subcategories in CANONICAL_TAXONOMY.items():
        for subcategory in subcategories.keys():
            mapping[subcategory] = category
    return mapping

def fix_pyq_categories():
    """Fix missing category data in PYQ questions"""
    
    # Create subcategory to category mapping
    subcategory_mapping = create_subcategory_to_category_mapping()
    
    logger.info("🗄️ Created subcategory to category mapping:")
    for subcat, cat in list(subcategory_mapping.items())[:10]:  # Show first 10
        logger.info(f"   {subcat} → {cat}")
    
    db = SessionLocal()
    try:
        # Get all PYQ questions with missing categories
        pyq_questions = db.query(PYQQuestion).filter(
            PYQQuestion.category.is_(None),
            PYQQuestion.subcategory.isnot(None)
        ).all()
        
        logger.info(f"📊 Found {len(pyq_questions)} PYQ questions with missing categories")
        
        updated_count = 0
        mapping_failures = set()
        
        for question in pyq_questions:
            subcategory = question.subcategory.strip() if question.subcategory else None
            
            if subcategory and subcategory in subcategory_mapping:
                # Map subcategory to category
                category = subcategory_mapping[subcategory]
                question.category = category
                updated_count += 1
                
                if updated_count <= 10:  # Log first 10 updates
                    logger.info(f"   ✅ {question.id[:8]}... | {subcategory} → {category}")
                    
            elif subcategory:
                mapping_failures.add(subcategory)
        
        # Show mapping failures
        if mapping_failures:
            logger.warning(f"⚠️ Could not map {len(mapping_failures)} subcategories:")
            for subcat in sorted(mapping_failures):
                logger.warning(f"   - {subcat}")
        
        # Commit changes
        db.commit()
        logger.info(f"✅ Successfully updated {updated_count} PYQ questions with category data")
        
        # Verify the fix
        verification_query = db.query(PYQQuestion).filter(
            PYQQuestion.category.isnot(None),
            PYQQuestion.subcategory.isnot(None)
        ).limit(5).all()
        
        logger.info("🔍 Verification - Sample updated records:")
        for q in verification_query:
            logger.info(f"   {q.category} → {q.subcategory} | {q.stem[:50]}...")
            
        return updated_count, len(mapping_failures)
        
    except Exception as e:
        logger.error(f"❌ Error fixing PYQ categories: {e}")
        db.rollback()
        return 0, 0
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("🔧 FIXING PYQ CATEGORY DATA")
    logger.info("=" * 60)
    
    updated, failed = fix_pyq_categories()
    
    logger.info("=" * 60)
    logger.info(f"📊 SUMMARY:")
    logger.info(f"   ✅ Updated: {updated} questions")
    logger.info(f"   ❌ Failed: {failed} subcategories")
    
    if updated > 0:
        logger.info("🎉 PYQ category data fix completed successfully!")
        logger.info("   The new PYQ frequency score calculation should now work properly.")
    else:
        logger.error("❌ No updates made - check for errors above")
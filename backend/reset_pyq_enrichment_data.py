#!/usr/bin/env python3
"""
Reset PYQ Enrichment Data Script
Clears all existing enrichment data to prepare for re-enrichment with new canonical taxonomy
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_pyq_enrichment_data():
    """Reset all enrichment fields in pyq_questions table"""
    
    # Get database URL from environment
    MONGO_URL = os.environ.get('MONGO_URL')
    if not MONGO_URL:
        logger.error("❌ MONGO_URL environment variable not found")
        return False
    
    try:
        engine = create_engine(MONGO_URL)
        Session = sessionmaker(bind=engine)
        db = Session()
        
        logger.info("🚀 Starting PYQ enrichment data reset...")
        
        # Get current statistics
        total_questions = db.execute(text("SELECT COUNT(*) FROM pyq_questions")).scalar()
        enriched_questions = db.execute(text("""
            SELECT COUNT(*) FROM pyq_questions 
            WHERE concept_extraction_status = 'completed' 
            AND quality_verified = true
        """)).scalar()
        
        logger.info(f"📊 Before reset: {total_questions} total questions, {enriched_questions} enriched")
        
        # Reset all enrichment fields to initial state
        reset_query = text("""
            UPDATE pyq_questions SET
                category = NULL,
                subcategory = 'To be classified by LLM',
                type_of_question = 'To be classified by LLM',
                difficulty_band = NULL,
                difficulty_score = NULL,
                core_concepts = NULL,
                solution_method = NULL,
                concept_difficulty = NULL,
                operations_required = NULL,
                problem_structure = NULL,
                concept_keywords = NULL,
                quality_verified = false,
                concept_extraction_status = 'pending',
                last_updated = NOW()
            WHERE is_active = true
        """)
        
        result = db.execute(reset_query)
        affected_rows = result.rowcount
        
        # Commit the changes
        db.commit()
        
        # Verify the reset
        pending_questions = db.execute(text("""
            SELECT COUNT(*) FROM pyq_questions 
            WHERE concept_extraction_status = 'pending' 
            AND is_active = true
        """)).scalar()
        
        logger.info(f"✅ Reset completed!")
        logger.info(f"   Affected rows: {affected_rows}")
        logger.info(f"   Questions ready for re-enrichment: {pending_questions}")
        
        # Show sample of reset questions
        sample_questions = db.execute(text("""
            SELECT id, subcategory, type_of_question, concept_extraction_status, quality_verified
            FROM pyq_questions 
            WHERE is_active = true
            LIMIT 5
        """)).fetchall()
        
        logger.info("📋 Sample reset questions:")
        for q in sample_questions:
            logger.info(f"   {q[0][:8]}... | {q[1]} | {q[2]} | {q[3]} | QV:{q[4]}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Reset failed: {e}")
        if 'db' in locals():
            db.rollback()
        return False
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    success = reset_pyq_enrichment_data()
    if success:
        logger.info("🎉 PYQ enrichment data reset completed successfully!")
        logger.info("🚀 Ready for re-enrichment with new canonical taxonomy system!")
    else:
        logger.error("💥 PYQ enrichment data reset failed!")
        exit(1)
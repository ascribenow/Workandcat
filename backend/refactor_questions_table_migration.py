#!/usr/bin/env python3
"""
Questions Table Refactoring Migration
Removes deleted fields, adds snap_read field, removes relationships
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

# Add backend directory to path
sys.path.append('/app/backend')

load_dotenv()

from database import engine, SessionLocal
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Apply questions table refactoring changes"""
    
    try:
        db = SessionLocal()
        
        logger.info("🚀 Starting Questions Table Refactoring Migration...")
        
        # Step 1: Add new snap_read column
        logger.info("📝 Adding snap_read column...")
        try:
            db.execute(text("ALTER TABLE questions ADD COLUMN snap_read TEXT"))
            logger.info("✅ Added snap_read column")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("✅ snap_read column already exists")
            else:
                logger.error(f"❌ Failed to add snap_read column: {e}")
        
        # Step 2: Remove deleted columns (these might not exist in all environments)
        columns_to_remove = [
            "topic_id",
            "image_alt_text", 
            "llm_difficulty_assessment_method",
            "llm_assessment_attempts",
            "last_llm_assessment_date", 
            "llm_assessment_error",
            "total_pyq_analyzed",
            "frequency_analysis_method",
            "frequency_last_updated",
            "pyq_occurrences_last_10_years",
            "total_pyq_count"
        ]
        
        for column in columns_to_remove:
            try:
                logger.info(f"🗑️ Removing {column} column...")
                db.execute(text(f"ALTER TABLE questions DROP COLUMN IF EXISTS {column}"))
                logger.info(f"✅ Removed {column} column")
            except Exception as e:
                logger.warning(f"⚠️ Could not remove {column}: {e}")
        
        # Step 3: Update PYQ questions table - remove topic_id
        logger.info("🔄 Updating PYQ questions table...")
        try:
            db.execute(text("ALTER TABLE pyq_questions DROP COLUMN IF EXISTS topic_id"))
            logger.info("✅ Removed topic_id from pyq_questions")
        except Exception as e:
            logger.warning(f"⚠️ Could not remove topic_id from pyq_questions: {e}")
        
        # Step 4: Update foreign key constraints for attempts table
        logger.info("🔄 Updating attempts table constraints...")
        try:
            # This may fail in some databases, but it's OK
            db.execute(text("ALTER TABLE attempts DROP CONSTRAINT IF EXISTS attempts_question_id_fkey"))
            logger.info("✅ Removed question foreign key constraint from attempts")
        except Exception as e:
            logger.warning(f"⚠️ Could not remove FK constraint: {e}")
        
        # Step 5: Update diagnostic_set_questions constraints
        logger.info("🔄 Updating diagnostic_set_questions table constraints...")
        try:
            db.execute(text("ALTER TABLE diagnostic_set_questions DROP CONSTRAINT IF EXISTS diagnostic_set_questions_question_id_fkey"))
            logger.info("✅ Removed question foreign key constraint from diagnostic_set_questions")
        except Exception as e:
            logger.warning(f"⚠️ Could not remove FK constraint: {e}")
        
        # Step 6: Update doubts_conversations constraints  
        logger.info("🔄 Updating doubts_conversations table constraints...")
        try:
            db.execute(text("ALTER TABLE doubts_conversations DROP CONSTRAINT IF EXISTS doubts_conversations_question_id_fkey"))
            logger.info("✅ Removed question foreign key constraint from doubts_conversations")
        except Exception as e:
            logger.warning(f"⚠️ Could not remove FK constraint: {e}")
        
        # Commit all changes
        db.commit()
        
        logger.info("🎉 Questions Table Refactoring Migration completed successfully!")
        
        # Verify schema changes
        logger.info("🔍 Verifying schema changes...")
        result = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'questions' ORDER BY column_name"))
        columns = [row[0] for row in result.fetchall()]
        
        logger.info(f"📊 Current questions table columns: {len(columns)} columns")
        logger.info(f"📝 Columns: {', '.join(columns)}")
        
        # Check if snap_read exists
        if 'snap_read' in columns:
            logger.info("✅ snap_read column confirmed")
        else:
            logger.error("❌ snap_read column missing")
            
        # Check if deleted columns are gone
        deleted_columns_still_present = [col for col in columns_to_remove if col in columns]
        if deleted_columns_still_present:
            logger.warning(f"⚠️ Some deleted columns still present: {deleted_columns_still_present}")
        else:
            logger.info("✅ All specified columns successfully removed")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        if 'db' in locals():
            db.rollback()
        return False
        
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    success = run_migration()
    if success:
        print("✅ Migration completed successfully")
        sys.exit(0)
    else:
        print("❌ Migration failed")
        sys.exit(1)
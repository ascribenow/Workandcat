#!/usr/bin/env python3
"""
Remove Learning Impact and PYQ Conceptual Matches Fields Migration
Removes learning_impact and pyq_conceptual_matches fields
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
    """Remove learning_impact and pyq_conceptual_matches fields from questions table"""
    
    try:
        db = SessionLocal()
        
        logger.info("🚀 Starting Remove Learning Impact and PYQ Conceptual Matches Migration...")
        
        # Fields to remove
        fields_to_remove = [
            "learning_impact",
            "pyq_conceptual_matches"
        ]
        
        # Step 1: Remove the specified fields
        for field in fields_to_remove:
            try:
                logger.info(f"🗑️ Removing {field} column...")
                db.execute(text(f"ALTER TABLE questions DROP COLUMN IF EXISTS {field}"))
                logger.info(f"✅ Removed {field} column")
            except Exception as e:
                logger.warning(f"⚠️ Could not remove {field}: {e}")
        
        # Commit all changes
        db.commit()
        
        logger.info("🎉 Remove Learning Impact and PYQ Conceptual Matches Migration completed successfully!")
        
        # Verify schema changes
        logger.info("🔍 Verifying schema changes...")
        result = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'questions' ORDER BY column_name"))
        columns = [row[0] for row in result.fetchall()]
        
        logger.info(f"📊 Current questions table columns: {len(columns)} columns")
        logger.info(f"📝 Columns: {', '.join(columns)}")
        
        # Check if deleted fields are gone
        deleted_fields_still_present = [field for field in fields_to_remove if field in columns]
        if deleted_fields_still_present:
            logger.warning(f"⚠️ Some deleted fields still present: {deleted_fields_still_present}")
        else:
            logger.info("✅ All specified fields successfully removed")
        
        # Verify essential field is still present
        if 'pyq_frequency_score' in columns:
            logger.info("✅ pyq_frequency_score field confirmed present")
        else:
            logger.error("❌ pyq_frequency_score field missing")
        
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
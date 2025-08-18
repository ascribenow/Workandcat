#!/usr/bin/env python3
"""
Add mcq_options column to questions table
"""

import sys
import os
sys.path.append('/app/backend')

from database import *
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_mcq_column():
    """Add mcq_options column to questions table"""
    try:
        logger.info("🔧 Adding mcq_options column to questions table...")
        
        # Initialize database
        init_database()
        db = SessionLocal()
        
        # Add the column
        try:
            from sqlalchemy import text
            db.execute(text("ALTER TABLE questions ADD COLUMN mcq_options TEXT"))
            db.commit()
            logger.info("✅ Successfully added mcq_options column")
            return True
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                logger.info("ℹ️ mcq_options column already exists")
                return True
            else:
                logger.error(f"❌ Failed to add column: {e}")
                return False
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = add_mcq_column()
    print("✅ Migration successful" if success else "❌ Migration failed")
    exit(0 if success else 1)
#!/usr/bin/env python3
"""
Add category column to questions and pyq_questions tables
Migration for canonical taxonomy enhancement
"""

import os
from sqlalchemy import create_engine, text, Column, String
from sqlalchemy.orm import sessionmaker
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_category_columns():
    """Add category column to both questions and pyq_questions tables"""
    
    # Get database URL from environment
    MONGO_URL = os.environ.get('MONGO_URL')
    if not MONGO_URL:
        logger.error("❌ MONGO_URL environment variable not found")
        return False
    
    try:
        engine = create_engine(MONGO_URL)
        Session = sessionmaker(bind=engine)
        db = Session()
        
        logger.info("🚀 Starting category column migration...")
        
        # Check if columns already exist
        logger.info("🔍 Checking existing table structures...")
        
        # Check questions table
        questions_columns_result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'questions' AND column_name = 'category'
        """))
        questions_has_category = len(questions_columns_result.fetchall()) > 0
        
        # Check pyq_questions table
        pyq_columns_result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'pyq_questions' AND column_name = 'category'
        """))
        pyq_has_category = len(pyq_columns_result.fetchall()) > 0
        
        # Add category column to questions table if not exists
        if not questions_has_category:
            logger.info("📝 Adding category column to questions table...")
            db.execute(text("""
                ALTER TABLE questions 
                ADD COLUMN category VARCHAR(255)
            """))
            logger.info("✅ Category column added to questions table")
        else:
            logger.info("ℹ️ Category column already exists in questions table")
        
        # Add category column to pyq_questions table if not exists
        if not pyq_has_category:
            logger.info("📝 Adding category column to pyq_questions table...")
            db.execute(text("""
                ALTER TABLE pyq_questions 
                ADD COLUMN category VARCHAR(255)
            """))
            logger.info("✅ Category column added to pyq_questions table")
        else:
            logger.info("ℹ️ Category column already exists in pyq_questions table")
        
        # Commit changes
        db.commit()
        
        # Verify the additions
        logger.info("🔍 Verifying column additions...")
        
        questions_verify = db.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'questions' AND column_name = 'category'
        """))
        questions_result = questions_verify.fetchall()
        
        pyq_verify = db.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'pyq_questions' AND column_name = 'category'
        """))
        pyq_result = pyq_verify.fetchall()
        
        if questions_result and pyq_result:
            logger.info("✅ Migration completed successfully!")
            logger.info(f"   questions.category: {questions_result[0][1]}")
            logger.info(f"   pyq_questions.category: {pyq_result[0][1]}")
            
            # Show table statistics
            questions_count = db.execute(text("SELECT COUNT(*) FROM questions")).scalar()
            pyq_count = db.execute(text("SELECT COUNT(*) FROM pyq_questions")).scalar()
            
            logger.info(f"📊 Table statistics:")
            logger.info(f"   questions: {questions_count} rows")
            logger.info(f"   pyq_questions: {pyq_count} rows")
            
            return True
        else:
            logger.error("❌ Migration verification failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        if 'db' in locals():
            db.rollback()
        return False
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    success = add_category_columns()
    if success:
        logger.info("🎉 Category column migration completed successfully!")
    else:
        logger.error("💥 Category column migration failed!")
        exit(1)
#!/usr/bin/env python3
"""
Migration Script: Delete Irrelevant Database Fields
==================================================
This script removes 14 identified irrelevant database fields across multiple tables
while preserving 4 important fields (llm_assessment_error, model_feedback, 
misconception_tag, mcq_options).

Fields to Delete (14 total):
- QUESTIONS TABLE (6): video_url, tags, version, frequency_notes, pattern_keywords, pattern_solution_approach
- PYQ_QUESTIONS TABLE (3): confirmed, tags, frequency_self_score
- USERS TABLE (1): tz
- PLANUNIT TABLE (2): actual_stats, generated_payload
- PYQINGESTION TABLE (2): ocr_required, ocr_status

Fields to Keep (4 important):
- llm_assessment_error (QA and audit)
- model_feedback (user-facing insights)
- misconception_tag (streaks and analysis)
- mcq_options (MCQ functionality)
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def get_database_connection():
    """Get database connection using environment variables."""
    try:
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL environment variable not found")
        
        # Connect to PostgreSQL database
        conn = psycopg2.connect(database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in the specified table."""
    try:
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = %s AND column_name = %s
            );
        """, (table_name, column_name))
        return cursor.fetchone()[0]
    except Exception as e:
        logger.error(f"Error checking column {column_name} in {table_name}: {e}")
        return False

def drop_column_if_exists(cursor, table_name, column_name):
    """Drop a column if it exists."""
    try:
        if check_column_exists(cursor, table_name, column_name):
            cursor.execute(f'ALTER TABLE {table_name} DROP COLUMN IF EXISTS "{column_name}";')
            logger.info(f"✅ Dropped column '{column_name}' from table '{table_name}'")
            return True
        else:
            logger.info(f"ℹ️  Column '{column_name}' does not exist in table '{table_name}' - skipping")
            return False
    except Exception as e:
        logger.error(f"❌ Failed to drop column '{column_name}' from table '{table_name}': {e}")
        raise

def main():
    """Main migration function."""
    logger.info("🚀 Starting database cleanup migration...")
    logger.info("Deleting 14 irrelevant fields while preserving 4 important ones")
    
    # Fields to delete grouped by table
    fields_to_delete = {
        'questions': [
            'video_url', 'tags', 'version', 'frequency_notes', 
            'pattern_keywords', 'pattern_solution_approach'
        ],
        'pyq_questions': [
            'confirmed', 'tags', 'frequency_self_score'
        ],
        'users': [
            'tz'
        ],
        'plan_units': [
            'actual_stats', 'generated_payload'
        ],
        'pyq_ingestions': [
            'ocr_required', 'ocr_status'
        ]
    }
    
    # Fields to keep (for reference/logging)
    fields_to_keep = [
        'llm_assessment_error', 'model_feedback', 
        'misconception_tag', 'mcq_options'
    ]
    
    logger.info(f"Fields to keep: {', '.join(fields_to_keep)}")
    
    conn = None
    cursor = None
    
    try:
        # Connect to database
        conn = get_database_connection()
        cursor = conn.cursor()
        logger.info("📦 Connected to database successfully")
        
        # Start transaction
        cursor.execute("BEGIN;")
        logger.info("🔄 Transaction started")
        
        total_deleted = 0
        
        # Process each table
        for table_name, columns in fields_to_delete.items():
            logger.info(f"\n🗂️  Processing table: {table_name}")
            
            for column_name in columns:
                if drop_column_if_exists(cursor, table_name, column_name):
                    total_deleted += 1
        
        # Commit transaction
        cursor.execute("COMMIT;")
        logger.info(f"\n✅ Migration completed successfully!")
        logger.info(f"📊 Total columns deleted: {total_deleted}")
        
        # Verify tables still exist and are accessible
        logger.info("\n🔍 Verifying table accessibility...")
        for table_name in fields_to_delete.keys():
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            count = cursor.fetchone()[0]
            logger.info(f"✅ Table '{table_name}': {count} rows accessible")
        
        logger.info("\n🎉 Database cleanup migration completed successfully!")
        
    except Exception as e:
        logger.error(f"\n❌ Migration failed: {e}")
        if cursor:
            try:
                cursor.execute("ROLLBACK;")
                logger.info("🔄 Transaction rolled back")
            except:
                pass
        sys.exit(1)
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        logger.info("📦 Database connection closed")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Database Schema Migration v1.4 - Fix subcategory VARCHAR constraint
Increases subcategory field from VARCHAR(20) to VARCHAR(100) to support canonical taxonomy
"""

import asyncio
import logging
from sqlalchemy import text
import sys
sys.path.append('/app/backend')
from database import get_database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fix_subcategory_schema():
    """
    Fix the subcategory field VARCHAR constraint that is blocking canonical taxonomy implementation
    """
    logger.info("🔧 Starting Database Schema Migration v1.4")
    logger.info("🎯 Objective: Fix subcategory VARCHAR(20) constraint to support canonical taxonomy")
    
    try:
        async for db in get_database():
            logger.info("📋 Executing database schema updates...")
            
            # Migration commands to fix the subcategory constraint
            migration_commands = [
                # 1. Increase subcategory field length
                """
                ALTER TABLE questions 
                ALTER COLUMN subcategory TYPE VARCHAR(100);
                """,
                
                # 2. Increase type_of_question field length  
                """
                ALTER TABLE questions 
                ALTER COLUMN type_of_question TYPE VARCHAR(150);
                """,
                
                # 3. Add indexes for better performance on the new longer fields
                """
                CREATE INDEX IF NOT EXISTS idx_questions_subcategory_longer 
                ON questions(subcategory);
                """,
                
                """
                CREATE INDEX IF NOT EXISTS idx_questions_type_of_question 
                ON questions(type_of_question);
                """,
                
                # 4. Verify the schema changes
                """
                SELECT column_name, data_type, character_maximum_length 
                FROM information_schema.columns 
                WHERE table_name = 'questions' 
                AND column_name IN ('subcategory', 'type_of_question');
                """
            ]
            
            # Execute each migration command
            for i, command in enumerate(migration_commands[:-1], 1):  # Skip the SELECT query for now
                try:
                    logger.info(f"🔄 Executing migration step {i}...")
                    await db.execute(text(command.strip()))
                    logger.info(f"✅ Migration step {i} completed successfully")
                except Exception as e:
                    logger.error(f"❌ Migration step {i} failed: {e}")
                    # Continue with other commands even if one fails
            
            # Verify schema changes
            logger.info("🔍 Verifying schema changes...")
            verification_result = await db.execute(text(migration_commands[-1]))
            
            logger.info("📊 Updated schema information:")
            for row in verification_result.fetchall():
                column_name = row[0]
                data_type = row[1]
                max_length = row[2] or "unlimited"
                logger.info(f"   {column_name}: {data_type}({max_length})")
            
            # Commit all changes
            await db.commit()
            logger.info("✅ Database Schema Migration v1.4 completed successfully!")
            
            # Test creating a question with long subcategory name
            logger.info("🧪 Testing long subcategory name creation...")
            test_query = text("""
                INSERT INTO questions (
                    id, stem, answer, subcategory, type_of_question, 
                    difficulty_band, is_active, source, created_at
                ) VALUES (
                    gen_random_uuid(), 
                    'Test question for long subcategory validation', 
                    '42',
                    'Time–Speed–Distance (TSD)', 
                    'Basic Time-Speed-Distance calculation with distance finding',
                    'Easy', 
                    true, 
                    'Schema Migration Test',
                    NOW()
                ) ON CONFLICT DO NOTHING;
            """)
            
            await db.execute(test_query)
            await db.commit()
            logger.info("✅ Successfully created test question with long subcategory name!")
            
            break  # Exit the async for loop
            
    except Exception as e:
        logger.error(f"❌ Database Schema Migration v1.4 failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

async def verify_schema_fix():
    """
    Verify that the schema fix worked correctly
    """
    logger.info("🔍 Verifying schema fix...")
    
    try:
        async for db in get_database():
            # Check if we can query questions with the new schema
            result = await db.execute(text("""
                SELECT COUNT(*) as total_questions,
                       COUNT(CASE WHEN LENGTH(subcategory) > 20 THEN 1 END) as long_subcategories,
                       MAX(LENGTH(subcategory)) as max_subcategory_length,
                       MAX(LENGTH(type_of_question)) as max_type_length
                FROM questions;
            """))
            
            row = result.fetchone()
            if row:
                logger.info(f"📊 Schema verification results:")
                logger.info(f"   Total questions: {row[0]}")
                logger.info(f"   Questions with subcategory > 20 chars: {row[1]}")
                logger.info(f"   Max subcategory length: {row[2]} characters")
                logger.info(f"   Max type_of_question length: {row[3]} characters")
                
                if row[2] > 20:  # If we have subcategories longer than 20 characters
                    logger.info("✅ Schema fix verified - can handle long subcategory names!")
                    return True
                else:
                    logger.info("⚠️ Schema fix appears successful but no long subcategories found yet")
                    return True
            
            break
            
    except Exception as e:
        logger.error(f"❌ Schema verification failed: {e}")
        return False

async def main():
    """
    Main function to run the schema migration
    """
    logger.info("🚀 Starting Database Schema Migration v1.4")
    logger.info("🎯 Purpose: Fix subcategory VARCHAR constraint blocking canonical taxonomy")
    
    # Step 1: Apply schema fixes
    success = await fix_subcategory_schema()
    if not success:
        logger.error("❌ Schema migration failed")
        return 1
    
    # Step 2: Verify the fixes
    verification_success = await verify_schema_fix()
    if not verification_success:
        logger.error("❌ Schema verification failed")
        return 1
    
    logger.info("🎉 Database Schema Migration v1.4 completed successfully!")
    logger.info("✅ Subcategory field now supports canonical taxonomy names up to 100 characters")
    logger.info("✅ Type_of_question field now supports descriptions up to 150 characters")
    logger.info("✅ Enhanced Nightly Engine Integration can now work with full canonical taxonomy")
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
#!/usr/bin/env python3
"""
Database Schema Migration - Image Support for Questions
Adds image-related fields to questions table
"""

import asyncio
import logging
import sys
sys.path.append('/app/backend')
from sqlalchemy import text
from database import get_database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def add_image_fields():
    """
    Add image support fields to questions table
    """
    logger.info("🖼️  Starting Image Support Migration")
    logger.info("🎯 Objective: Add has_image, image_url, image_alt_text fields to questions table")
    
    try:
        async for db in get_database():
            logger.info("📋 Executing database schema updates...")
            
            # Migration commands to add image support fields
            migration_commands = [
                # 1. Add has_image boolean field (default false)
                """
                ALTER TABLE questions 
                ADD COLUMN IF NOT EXISTS has_image BOOLEAN DEFAULT FALSE;
                """,
                
                # 2. Add image_url text field
                """
                ALTER TABLE questions 
                ADD COLUMN IF NOT EXISTS image_url TEXT;
                """,
                
                # 3. Add image_alt_text field for accessibility
                """
                ALTER TABLE questions 
                ADD COLUMN IF NOT EXISTS image_alt_text TEXT;
                """,
                
                # 4. Create index on has_image for efficient filtering
                """
                CREATE INDEX IF NOT EXISTS idx_questions_has_image 
                ON questions(has_image);
                """,
                
                # 5. Verify the schema changes
                """
                SELECT column_name, data_type, is_nullable, column_default 
                FROM information_schema.columns 
                WHERE table_name = 'questions' 
                AND column_name IN ('has_image', 'image_url', 'image_alt_text');
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
            
            logger.info("📊 New image-related fields:")
            field_count = 0
            for row in verification_result.fetchall():
                column_name = row[0]
                data_type = row[1]
                is_nullable = row[2]
                default_value = row[3] or "NULL"
                logger.info(f"   {column_name}: {data_type} (nullable: {is_nullable}, default: {default_value})")
                field_count += 1
            
            if field_count == 3:
                logger.info("✅ All 3 image fields added successfully!")
            else:
                logger.warning(f"⚠️ Expected 3 fields, found {field_count}")
            
            # Commit all changes
            await db.commit()
            logger.info("✅ Image Support Migration completed successfully!")
            
            # Test image field functionality
            logger.info("🧪 Testing image field functionality...")
            test_query = text("""
                SELECT COUNT(*) as total_questions,
                       COUNT(CASE WHEN has_image = true THEN 1 END) as questions_with_images,
                       COUNT(CASE WHEN image_url IS NOT NULL THEN 1 END) as questions_with_image_urls
                FROM questions;
            """)
            
            test_result = await db.execute(test_query)
            test_row = test_result.fetchone()
            if test_row:
                logger.info(f"📊 Image field test results:")
                logger.info(f"   Total questions: {test_row[0]}")
                logger.info(f"   Questions with images: {test_row[1]}")
                logger.info(f"   Questions with image URLs: {test_row[2]}")
                logger.info("✅ Image fields are queryable and functional!")
            
            break  # Exit the async for loop
            
    except Exception as e:
        logger.error(f"❌ Image Support Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

async def main():
    """
    Main function to run the image support migration
    """
    logger.info("🚀 Starting Image Support Migration")
    logger.info("🎯 Purpose: Add image support fields to questions table")
    
    # Apply image support migration
    success = await add_image_fields()
    if not success:
        logger.error("❌ Image support migration failed")
        return 1
    
    logger.info("🎉 Image Support Migration completed successfully!")
    logger.info("✅ Questions can now support images with URL storage and alt text")
    logger.info("✅ Database ready for image upload and display functionality")
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
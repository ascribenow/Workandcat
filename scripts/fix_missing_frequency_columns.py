#!/usr/bin/env python3
"""
CRITICAL DATABASE MIGRATION: Add All Missing Frequency Analysis Fields
Fixes the UndefinedColumnError for question creation
"""

import asyncio
import os
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not found")

ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

async def add_all_missing_frequency_fields():
    """Add all missing frequency analysis fields to questions table"""
    
    engine = create_async_engine(ASYNC_DATABASE_URL)
    
    try:
        async with engine.begin() as conn:
            logger.info("🔧 Starting comprehensive frequency fields migration...")
            
            # Get existing columns
            check_columns = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'questions' 
                ORDER BY column_name;
            """)
            
            result = await conn.execute(check_columns)
            existing_columns = [row.column_name for row in result.fetchall()]
            logger.info(f"📋 Found {len(existing_columns)} existing columns")
            
            # Define ALL frequency analysis columns that should exist
            required_columns = [
                # Basic frequency fields
                ("frequency_score", "NUMERIC(5, 4) DEFAULT 0.0"),
                ("pyq_occurrences_last_10_years", "INTEGER DEFAULT 0"),
                ("total_pyq_count", "INTEGER DEFAULT 0"),
                
                # Conceptual analysis fields  
                ("pyq_conceptual_matches", "INTEGER DEFAULT 0"),
                ("total_pyq_analyzed", "INTEGER DEFAULT 0"),
                ("top_matching_concepts", "TEXT[]"),
                ("frequency_analysis_method", "VARCHAR(50) DEFAULT 'subcategory'"),
                ("frequency_last_updated", "TIMESTAMP"),
                
                # Pattern analysis fields
                ("pattern_keywords", "TEXT[]"),
                ("pattern_solution_approach", "TEXT"),
            ]
            
            # Add missing columns one by one
            added_count = 0
            for column_name, column_definition in required_columns:
                if column_name not in existing_columns:
                    try:
                        alter_sql = text(f"""
                            ALTER TABLE questions 
                            ADD COLUMN {column_name} {column_definition};
                        """)
                        await conn.execute(alter_sql)
                        logger.info(f"✅ Added column: {column_name}")
                        added_count += 1
                    except Exception as e:
                        logger.error(f"❌ Failed to add column {column_name}: {e}")
                else:
                    logger.info(f"⏭️  Column already exists: {column_name}")
            
            # Create useful indexes
            indexes_to_create = [
                ("idx_questions_frequency_score", "frequency_score DESC"),
                ("idx_questions_conceptual_matches", "pyq_conceptual_matches DESC"),
                ("idx_questions_frequency_method", "frequency_analysis_method"),
                ("idx_questions_pyq_occurrences", "pyq_occurrences_last_10_years DESC")
            ]
            
            for index_name, index_definition in indexes_to_create:
                try:
                    create_index_sql = text(f"""
                        CREATE INDEX IF NOT EXISTS {index_name} 
                        ON questions({index_definition});
                    """)
                    await conn.execute(create_index_sql)
                    logger.info(f"✅ Created index: {index_name}")
                except Exception as e:
                    logger.error(f"❌ Failed to create index {index_name}: {e}")
            
            # Verify all columns exist now
            result = await conn.execute(check_columns)
            final_columns = [row.column_name for row in result.fetchall()]
            
            # Check how many required columns are now present
            present_required = [col for col, _ in required_columns if col in final_columns]
            missing_required = [col for col, _ in required_columns if col not in final_columns]
            
            logger.info(f"📊 Migration Results:")
            logger.info(f"   • Columns added this run: {added_count}")
            logger.info(f"   • Required columns present: {len(present_required)}/{len(required_columns)}")
            logger.info(f"   • Present: {present_required}")
            if missing_required:
                logger.warning(f"   • Still missing: {missing_required}")
            
            if len(present_required) == len(required_columns):
                logger.info("🎉 ALL frequency analysis columns are now present!")
            else:
                logger.warning(f"⚠️  Still missing {len(missing_required)} required columns")
            
            logger.info("🎉 Frequency fields migration completed!")
            
    except Exception as e:
        logger.error(f"❌ Critical error during migration: {e}")
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(add_all_missing_frequency_fields())
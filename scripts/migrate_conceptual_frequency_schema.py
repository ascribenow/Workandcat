#!/usr/bin/env python3
"""
Database Schema Migration: Enhanced Conceptual Frequency Support
Adds new columns to support LLM-powered conceptual frequency analysis
"""

import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

async def migrate_conceptual_frequency_schema():
    """Add conceptual frequency fields to questions table"""
    
    engine = create_async_engine(ASYNC_DATABASE_URL)
    
    try:
        async with engine.begin() as conn:
            logger.info("🔧 Starting conceptual frequency schema migration...")
            
            # Check if columns already exist
            check_columns = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'questions' 
                AND column_name IN (
                    'pyq_conceptual_matches', 
                    'total_pyq_analyzed', 
                    'top_matching_concepts',
                    'frequency_analysis_method',
                    'frequency_last_updated',
                    'pattern_keywords',
                    'pattern_solution_approach'
                );
            """)
            
            result = await conn.execute(check_columns)
            existing_columns = [row.column_name for row in result.fetchall()]
            logger.info(f"📋 Found existing columns: {existing_columns}")
            
            # Add new columns for conceptual frequency analysis
            new_columns = [
                ("pyq_conceptual_matches", "INTEGER DEFAULT 0"),
                ("total_pyq_analyzed", "INTEGER DEFAULT 0"), 
                ("top_matching_concepts", "TEXT[]"),
                ("frequency_analysis_method", "VARCHAR(50) DEFAULT 'subcategory'"),
                ("frequency_last_updated", "TIMESTAMP"),
                ("pattern_keywords", "TEXT[]"),
                ("pattern_solution_approach", "TEXT")
            ]
            
            for column_name, column_def in new_columns:
                if column_name not in existing_columns:
                    alter_sql = text(f"""
                        ALTER TABLE questions 
                        ADD COLUMN {column_name} {column_def};
                    """)
                    await conn.execute(alter_sql)
                    logger.info(f"✅ Added column: {column_name}")
                else:
                    logger.info(f"⏭️  Column already exists: {column_name}")
            
            # Create index for frequency analysis queries
            create_frequency_index = text("""
                CREATE INDEX IF NOT EXISTS idx_questions_frequency_analysis 
                ON questions(frequency_analysis_method, frequency_last_updated);
            """)
            await conn.execute(create_frequency_index)
            logger.info("✅ Created frequency analysis index")
            
            # Create index for conceptual matches
            create_conceptual_index = text("""
                CREATE INDEX IF NOT EXISTS idx_questions_conceptual_matches 
                ON questions(pyq_conceptual_matches DESC) 
                WHERE pyq_conceptual_matches > 0;
            """)
            await conn.execute(create_conceptual_index)
            logger.info("✅ Created conceptual matches index")
            
            logger.info("🎉 Conceptual frequency schema migration completed successfully!")
            
    except Exception as e:
        logger.error(f"❌ Error during migration: {e}")
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate_conceptual_frequency_schema())
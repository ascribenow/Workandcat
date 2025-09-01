#!/usr/bin/env python3
"""
Database Migration for Unified Enrichment Fields
Adds missing PYQ-style enrichment fields to regular questions table
"""

import os
import asyncio
import logging
from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def add_unified_enrichment_fields():
    """
    Add missing enrichment fields to questions table for unified approach
    """
    try:
        DATABASE_URL = os.getenv("DATABASE_URL")
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL not found in environment")
        
        # Convert to async driver
        if DATABASE_URL.startswith("postgresql://"):
            DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        engine = create_async_engine(DATABASE_URL)
        
        logger.info("🔧 Starting Unified Enrichment Fields Migration")
        logger.info("=" * 60)
        
        async with engine.begin() as conn:
            # Check existing schema first
            result = await conn.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'questions'
                ORDER BY column_name;
            """))
            
            existing_columns = {row.column_name for row in result}
            logger.info(f"📊 Found {len(existing_columns)} existing columns in questions table")
            
            # Define unified enrichment fields to add
            new_fields = {
                'core_concepts': 'TEXT',  # JSON: extracted mathematical concepts
                'solution_method': 'VARCHAR(100)',  # Primary solution approach  
                'concept_difficulty': 'TEXT',  # JSON: difficulty indicators
                'operations_required': 'TEXT',  # JSON: mathematical operations
                'problem_structure': 'VARCHAR(50)',  # Structure pattern type
                'concept_keywords': 'TEXT',  # JSON: searchable keywords
                'quality_verified': 'BOOLEAN DEFAULT FALSE',  # Quality gate for reliability
                'concept_extraction_status': 'VARCHAR(50) DEFAULT \'pending\'',  # pending|completed|failed
            }
            
            # Add missing fields
            fields_added = 0
            for field_name, field_type in new_fields.items():
                if field_name not in existing_columns:
                    try:
                        await conn.execute(text(f"""
                            ALTER TABLE questions 
                            ADD COLUMN {field_name} {field_type};
                        """))
                        fields_added += 1
                        logger.info(f"   ✅ Added field: {field_name} ({field_type})")
                    except Exception as field_error:
                        logger.warning(f"   ⚠️ Field {field_name} might already exist: {field_error}")
                else:
                    logger.info(f"   📋 Field already exists: {field_name}")
            
            # Create indexes for performance
            indexes_to_create = [
                "CREATE INDEX IF NOT EXISTS idx_questions_quality_verified ON questions(quality_verified);",
                "CREATE INDEX IF NOT EXISTS idx_questions_concept_extraction_status ON questions(concept_extraction_status);",
                "CREATE INDEX IF NOT EXISTS idx_questions_solution_method ON questions(solution_method);",
            ]
            
            for index_sql in indexes_to_create:
                try:
                    await conn.execute(text(index_sql))
                    logger.info(f"   📚 Created index: {index_sql.split('idx_')[1].split(' ')[0]}")
                except Exception as index_error:
                    logger.warning(f"   ⚠️ Index creation warning: {index_error}")
            
            await conn.commit()
            
        logger.info(f"✅ Migration completed successfully!")
        logger.info(f"📈 Fields added: {fields_added}")
        logger.info("🎯 Questions table now has unified enrichment fields")
        
        await engine.dispose()
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(add_unified_enrichment_fields())
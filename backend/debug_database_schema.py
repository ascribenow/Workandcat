#!/usr/bin/env python3
"""
Debug Database Schema - Check actual column existence
"""

import os
import logging
from sqlalchemy import create_engine, inspect, text
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_database_schema():
    """
    Debug actual database schema to identify column issues
    """
    try:
        DATABASE_URL = os.getenv("DATABASE_URL")
        if not DATABASE_URL:
            logger.error("DATABASE_URL not found in environment")
            return
        
        engine = create_engine(DATABASE_URL)
        inspector = inspect(engine)
        
        logger.info("🔍 DEBUGGING DATABASE SCHEMA")
        logger.info("=" * 50)
        
        # Check questions table columns
        logger.info("📊 QUESTIONS TABLE COLUMNS:")
        questions_columns = inspector.get_columns('questions')
        
        category_found = False
        pyq_frequency_found = False
        pyq_conceptual_matches_found = False
        
        for column in questions_columns:
            column_name = column['name']
            column_type = str(column['type'])
            nullable = column.get('nullable', True)
            
            if column_name == 'category':
                category_found = True
                logger.info(f"   ✅ CATEGORY: {column_name} ({column_type}) - Nullable: {nullable}")
            elif 'pyq_frequency' in column_name:
                pyq_frequency_found = True
                logger.info(f"   ✅ PYQ FREQ: {column_name} ({column_type}) - Nullable: {nullable}")
            elif 'pyq_conceptual' in column_name:
                pyq_conceptual_matches_found = True
                logger.info(f"   ✅ PYQ CONCEPT: {column_name} ({column_type}) - Nullable: {nullable}")
            elif column_name in ['id', 'stem', 'answer', 'subcategory', 'type_of_question']:
                logger.info(f"   📝 CORE: {column_name} ({column_type}) - Nullable: {nullable}")
        
        logger.info(f"\n🎯 CRITICAL FIELD STATUS:")
        logger.info(f"   Category column exists: {'✅ YES' if category_found else '❌ NO'}")
        logger.info(f"   PYQ frequency column exists: {'✅ YES' if pyq_frequency_found else '❌ NO'}")
        logger.info(f"   PYQ conceptual matches exists: {'✅ YES' if pyq_conceptual_matches_found else '❌ NO'}")
        
        # Check PYQ questions table columns
        try:
            logger.info("\n📊 PYQ_QUESTIONS TABLE COLUMNS:")
            pyq_questions_columns = inspector.get_columns('pyq_questions')
            
            year_found = False
            difficulty_band_found = False
            core_concepts_found = False
            
            for column in pyq_questions_columns:
                column_name = column['name']
                column_type = str(column['type'])
                nullable = column.get('nullable', True)
                
                if column_name == 'year':
                    year_found = True
                    logger.info(f"   📅 YEAR: {column_name} ({column_type}) - Nullable: {nullable}")
                elif 'difficulty_band' in column_name:
                    difficulty_band_found = True
                    logger.info(f"   ⚖️ DIFFICULTY: {column_name} ({column_type}) - Nullable: {nullable}")
                elif 'core_concepts' in column_name:
                    core_concepts_found = True
                    logger.info(f"   🧠 CONCEPTS: {column_name} ({column_type}) - Nullable: {nullable}")
                elif column_name in ['id', 'stem', 'paper_id', 'topic_id']:
                    logger.info(f"   📝 CORE: {column_name} ({column_type}) - Nullable: {nullable}")
            
            logger.info(f"\n🎯 PYQ ENRICHMENT FIELD STATUS:")
            logger.info(f"   Year column exists: {'✅ YES' if year_found else '❌ NO'}")
            logger.info(f"   Difficulty band exists: {'✅ YES' if difficulty_band_found else '❌ NO'}")
            logger.info(f"   Core concepts exists: {'✅ YES' if core_concepts_found else '❌ NO'}")
        
        except Exception as pyq_error:
            logger.error(f"❌ Error checking PYQ questions table: {pyq_error}")
        
        # Check actual data samples
        logger.info("\n🔬 DATA SAMPLES:")
        with engine.connect() as conn:
            # Check questions data
            questions_sample = conn.execute(text("SELECT id, stem, category, pyq_frequency_score, subcategory FROM questions LIMIT 3"))
            logger.info("   📊 QUESTIONS SAMPLE:")
            for row in questions_sample:
                logger.info(f"      ID: {row.id}")
                logger.info(f"      Stem: {row.stem[:50]}...")
                logger.info(f"      Category: {getattr(row, 'category', 'NOT FOUND')}")
                logger.info(f"      PYQ Frequency: {getattr(row, 'pyq_frequency_score', 'NOT FOUND')}")
                logger.info(f"      Subcategory: {row.subcategory}")
                logger.info("      ---")
        
        logger.info("✅ Database schema debugging completed")
        
    except Exception as e:
        logger.error(f"❌ Database schema debugging failed: {e}")

if __name__ == "__main__":
    debug_database_schema()
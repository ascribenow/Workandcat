#!/usr/bin/env python3
"""
PHASE 1 Migration: Add PYQ Frequency Score Column
Adds pyq_frequency_score column to questions table for enhanced selection
"""

import asyncio
import sys
import os

# Add the backend directory to Python path
backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend')
sys.path.insert(0, backend_dir)

from sqlalchemy import text
from database import init_database, get_async_compatible_db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_phase1_migration():
    """
    Add pyq_frequency_score column and update existing questions
    """
    try:
        logger.info("🚀 Starting PHASE 1 migration: PYQ Frequency Integration")
        
        # Initialize database
        await init_database()
        
        async for db in get_async_compatible_db():
            # Check if column already exists
            try:
                await db.execute(text("SELECT pyq_frequency_score FROM questions LIMIT 1"))
                logger.info("✅ pyq_frequency_score column already exists")
                
            except Exception:
                logger.info("➕ Adding pyq_frequency_score column to questions table")
                
                # Add the new column
                await db.execute(text("""
                    ALTER TABLE questions 
                    ADD COLUMN pyq_frequency_score DECIMAL(5,4) DEFAULT 0.5
                """))
                
                await db.commit()
                logger.info("✅ pyq_frequency_score column added successfully")
            
            # Update existing questions with default PYQ frequency scores based on subcategory
            logger.info("🔄 Updating existing questions with PYQ frequency estimates")
            
            # High frequency subcategories (based on CAT pattern analysis)
            high_freq_update = await db.execute(text("""
                UPDATE questions 
                SET pyq_frequency_score = 0.8
                WHERE subcategory IN (
                    'Time–Speed–Distance (TSD)',
                    'Percentages', 
                    'Profit–Loss–Discount (PLD)',
                    'Linear Equations',
                    'Triangles',
                    'Divisibility',
                    'Permutation–Combination (P&C)'
                ) AND pyq_frequency_score = 0.5
            """))
            
            # Medium frequency subcategories
            medium_freq_update = await db.execute(text("""
                UPDATE questions 
                SET pyq_frequency_score = 0.6
                WHERE subcategory IN (
                    'Time & Work',
                    'Ratio–Proportion–Variation',
                    'Averages & Alligation',
                    'Simple & Compound Interest (SI–CI)',
                    'Quadratic Equations',
                    'Circles',
                    'HCF–LCM',
                    'Probability'
                ) AND pyq_frequency_score = 0.5
            """))
            
            # Low frequency subcategories get default 0.5 (already set)
            
            await db.commit()
            
            # Get update counts
            high_count = high_freq_update.rowcount
            medium_count = medium_freq_update.rowcount
            
            logger.info(f"✅ Updated {high_count} questions to high frequency (0.8)")
            logger.info(f"✅ Updated {medium_count} questions to medium frequency (0.6)")
            
            # Get total question count for verification
            total_result = await db.execute(text("SELECT COUNT(*) FROM questions WHERE is_active = true"))
            total_questions = total_result.scalar()
            
            logger.info(f"📊 Total active questions in database: {total_questions}")
            
            # Verify the distribution
            freq_distribution = await db.execute(text("""
                SELECT 
                    CASE 
                        WHEN pyq_frequency_score >= 0.7 THEN 'High (≥0.7)'
                        WHEN pyq_frequency_score >= 0.4 THEN 'Medium (0.4-0.7)'
                        ELSE 'Low (<0.4)'
                    END as frequency_band,
                    COUNT(*) as count
                FROM questions 
                WHERE is_active = true
                GROUP BY 
                    CASE 
                        WHEN pyq_frequency_score >= 0.7 THEN 'High (≥0.7)'
                        WHEN pyq_frequency_score >= 0.4 THEN 'Medium (0.4-0.7)'
                        ELSE 'Low (<0.4)'
                    END
                ORDER BY count DESC
            """))
            
            logger.info("📈 PYQ Frequency Distribution:")
            for row in freq_distribution:
                logger.info(f"   {row[0]}: {row[1]} questions")
            
            logger.info("🎉 PHASE 1 migration completed successfully!")
            logger.info("🔗 PYQ frequency integration is now ready for enhanced question selection")
            
            return {
                'status': 'success',
                'high_frequency_updated': high_count,
                'medium_frequency_updated': medium_count,
                'total_questions': total_questions,
                'enhancement_level': 'phase_1_pyq_frequency_integration'
            }
            
    except Exception as e:
        logger.error(f"❌ PHASE 1 migration failed: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }

if __name__ == "__main__":
    result = asyncio.run(run_phase1_migration())
    
    if result['status'] == 'success':
        print("\n🎯 PHASE 1 MIGRATION SUMMARY:")
        print(f"✅ High frequency questions: {result['high_frequency_updated']}")
        print(f"✅ Medium frequency questions: {result['medium_frequency_updated']}")
        print(f"📊 Total questions processed: {result['total_questions']}")
        print("🚀 Enhanced 12-question selection system is now active!")
    else:
        print(f"\n❌ Migration failed: {result['error']}")
        sys.exit(1)
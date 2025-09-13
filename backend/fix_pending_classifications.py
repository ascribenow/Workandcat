#!/usr/bin/env python3
"""
Fix pending classifications and concept extraction status inconsistencies
"""

import sys
import asyncio
import logging
from database import SessionLocal, PYQQuestion
from sqlalchemy import select, and_
from pyq_enrichment_service import pyq_enrichment_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fix_pending_classifications():
    """Fix all questions with 'To be classified by LLM' and pending concept extraction"""
    
    db = SessionLocal()
    try:
        logger.info("🚀 Starting classification fix process...")
        
        # Get all questions that need classification
        questions_to_fix = db.execute(
            select(PYQQuestion)
            .where(
                and_(
                    PYQQuestion.subcategory == 'To be classified by LLM',
                    PYQQuestion.concept_extraction_status == 'pending'
                )
            )
        ).scalars().all()
        
        logger.info(f"📊 Found {len(questions_to_fix)} questions to fix")
        
        success_count = 0
        failed_count = 0
        
        for i, question in enumerate(questions_to_fix, 1):
            try:
                logger.info(f"🔄 Processing {i}/{len(questions_to_fix)}: {question.id[:12]}...")
                logger.info(f"   Current: {question.subcategory} | {question.type_of_question}")
                
                # Run full enrichment on this question
                result = await pyq_enrichment_service.enrich_single_question(question)
                
                if result and result.get('success'):
                    logger.info(f"   ✅ Successfully enriched question {question.id[:12]}")
                    success_count += 1
                    
                    # Refresh the question from DB to see updates
                    db.refresh(question)
                    logger.info(f"   📋 Updated: {question.subcategory} | {question.type_of_question}")
                    logger.info(f"   📈 Status: {question.concept_extraction_status}")
                    
                else:
                    logger.warning(f"   ❌ Failed to enrich question {question.id[:12]}")
                    failed_count += 1
                    
            except Exception as e:
                logger.error(f"   ❌ Error processing question {question.id[:12]}: {e}")
                failed_count += 1
        
        # Also fix any questions with inconsistent concept_extraction_status
        logger.info("\n🔍 Checking for concept extraction status inconsistencies...")
        
        inconsistent_questions = db.execute(
            select(PYQQuestion)
            .where(
                and_(
                    PYQQuestion.concept_extraction_status == 'pending',
                    PYQQuestion.core_concepts.isnot(None)
                )
            )
        ).scalars().all()
        
        logger.info(f"📊 Found {len(inconsistent_questions)} questions with status inconsistencies")
        
        for question in inconsistent_questions:
            try:
                logger.info(f"🔧 Fixing status for {question.id[:12]}...")
                question.concept_extraction_status = 'completed'
                db.commit()
                logger.info(f"   ✅ Updated status to 'completed'")
                success_count += 1
                
            except Exception as e:
                logger.error(f"   ❌ Error fixing status for {question.id[:12]}: {e}")
                failed_count += 1
        
        logger.info(f"\n🎉 Classification fix completed!")
        logger.info(f"   ✅ Successfully processed: {success_count}")
        logger.info(f"   ❌ Failed: {failed_count}")
        logger.info(f"   📊 Success rate: {(success_count/(success_count+failed_count))*100:.1f}%")
        
        return {
            'success': True,
            'processed': success_count + failed_count,
            'success_count': success_count,
            'failed_count': failed_count
        }
        
    except Exception as e:
        logger.error(f"❌ Critical error in fix process: {e}")
        return {'success': False, 'error': str(e)}
        
    finally:
        db.close()

async def main():
    """Main function"""
    result = await fix_pending_classifications()
    
    if result['success']:
        print(f"\n✅ Fix completed successfully!")
        print(f"   Processed: {result['processed']} questions")
        print(f"   Success: {result['success_count']}")
        print(f"   Failed: {result['failed_count']}")
    else:
        print(f"\n❌ Fix failed: {result['error']}")

if __name__ == "__main__":
    asyncio.run(main())
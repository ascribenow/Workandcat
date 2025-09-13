#!/usr/bin/env python3
"""
Proper fix for pending classifications using correct enrichment methods
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

async def fix_classifications_properly():
    """Fix all questions with 'To be classified by LLM' using proper enrichment"""
    
    db = SessionLocal()
    try:
        logger.info("🚀 Starting proper classification fix...")
        
        # Get all questions that need classification
        questions_to_fix = db.execute(
            select(PYQQuestion)
            .where(PYQQuestion.subcategory == 'To be classified by LLM')
        ).scalars().all()
        
        logger.info(f"📊 Found {len(questions_to_fix)} questions to fix")
        
        success_count = 0
        failed_count = 0
        
        for i, question in enumerate(questions_to_fix, 1):
            try:
                logger.info(f"🔄 Processing {i}/{len(questions_to_fix)}: {question.id[:12]}...")
                logger.info(f"   Current: {question.subcategory} | {question.type_of_question}")
                logger.info(f"   Status: {question.concept_extraction_status}")
                
                # Use the correct enrichment method
                enrichment_result = await pyq_enrichment_service.enrich_pyq_question(
                    question.stem, 
                    question.answer
                )
                
                if enrichment_result and enrichment_result.get('success'):
                    logger.info(f"   ✅ Enrichment successful")
                    
                    # Update the question with enrichment results
                    enriched_data = enrichment_result.get('data', {})
                    
                    # Update taxonomy fields
                    if 'subcategory' in enriched_data and enriched_data['subcategory'] != 'To be classified by LLM':
                        question.subcategory = enriched_data['subcategory']
                        logger.info(f"   📋 Updated subcategory: {enriched_data['subcategory']}")
                    
                    if 'type_of_question' in enriched_data and enriched_data['type_of_question'] != 'To be classified by LLM':
                        question.type_of_question = enriched_data['type_of_question']
                        logger.info(f"   📋 Updated type: {enriched_data['type_of_question']}")
                        
                    if 'category' in enriched_data:
                        question.category = enriched_data['category']
                        logger.info(f"   📋 Updated category: {enriched_data['category']}")
                    
                    # Update concept fields
                    if 'core_concepts' in enriched_data:
                        question.core_concepts = enriched_data['core_concepts']
                        logger.info(f"   🧠 Added core concepts")
                    
                    if 'concept_keywords' in enriched_data:
                        question.concept_keywords = enriched_data['concept_keywords']
                        logger.info(f"   🏷️ Added concept keywords")
                    
                    # Update other enrichment fields
                    for field_name, field_value in enriched_data.items():
                        if hasattr(question, field_name) and field_value is not None:
                            setattr(question, field_name, field_value)
                    
                    # Update status
                    question.concept_extraction_status = 'completed'
                    question.quality_verified = True
                    
                    # Commit changes
                    db.commit()
                    
                    success_count += 1
                    logger.info(f"   ✅ Successfully updated question {question.id[:12]}")
                    
                else:
                    logger.warning(f"   ❌ Enrichment failed for question {question.id[:12]}")
                    logger.warning(f"   Result: {enrichment_result}")
                    failed_count += 1
                    
            except Exception as e:
                logger.error(f"   ❌ Error processing question {question.id[:12]}: {e}")
                failed_count += 1
                db.rollback()  # Rollback on error
        
        logger.info(f"\n🎉 Classification fix completed!")
        logger.info(f"   ✅ Successfully processed: {success_count}")
        logger.info(f"   ❌ Failed: {failed_count}")
        
        if success_count + failed_count > 0:
            logger.info(f"   📊 Success rate: {(success_count/(success_count+failed_count))*100:.1f}%")
        
        return {
            'success': True,
            'processed': success_count + failed_count,
            'success_count': success_count,
            'failed_count': failed_count
        }
        
    except Exception as e:
        logger.error(f"❌ Critical error in fix process: {e}")
        db.rollback()
        return {'success': False, 'error': str(e)}
        
    finally:
        db.close()

async def fix_status_inconsistencies():
    """Fix questions with inconsistent concept_extraction_status"""
    
    db = SessionLocal()
    try:
        logger.info("🔍 Fixing concept extraction status inconsistencies...")
        
        # Find questions with concepts but pending status
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
        
        fixed_count = 0
        for question in inconsistent_questions:
            try:
                logger.info(f"🔧 Fixing status for {question.id[:12]}...")
                
                question.concept_extraction_status = 'completed'
                if question.subcategory != 'To be classified by LLM':
                    question.quality_verified = True
                
                db.commit()
                fixed_count += 1
                logger.info(f"   ✅ Updated status to 'completed'")
                
            except Exception as e:
                logger.error(f"   ❌ Error fixing status for {question.id[:12]}: {e}")
                db.rollback()
        
        logger.info(f"🔧 Fixed {fixed_count} status inconsistencies")
        return fixed_count
        
    finally:
        db.close()

async def main():
    """Main function"""
    
    # First fix the status inconsistencies
    fixed_status = await fix_status_inconsistencies()
    
    # Then fix the classifications
    result = await fix_classifications_properly()
    
    if result['success']:
        print(f"\n✅ All fixes completed successfully!")
        print(f"   Status fixes: {fixed_status}")
        print(f"   Classification fixes: {result['success_count']}")
        print(f"   Total processed: {result['processed']}")
        print(f"   Failed: {result['failed_count']}")
    else:
        print(f"\n❌ Fix failed: {result['error']}")

if __name__ == "__main__":
    asyncio.run(main())
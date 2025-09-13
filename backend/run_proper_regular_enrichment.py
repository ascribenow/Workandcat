#!/usr/bin/env python3
"""
Run proper regular questions enrichment service on all questions
This will check answer_match and run proper quality verification
"""

import sys
import asyncio
import logging
from database import SessionLocal, Question
from sqlalchemy import select, and_
from regular_enrichment_service import regular_questions_enrichment_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_proper_enrichment():
    """Run proper enrichment service on all regular questions"""
    
    db = SessionLocal()
    try:
        logger.info("🚀 Starting PROPER regular questions enrichment...")
        logger.info("This will run actual quality verification including answer_match checks")
        
        # Get all questions that have enrichment data but need proper verification
        questions_to_process = db.execute(
            select(Question)
            .where(
                and_(
                    Question.concept_extraction_status == 'completed',
                    Question.quality_verified == False,
                    Question.core_concepts.isnot(None)
                )
            )
        ).scalars().all()
        
        logger.info(f"📊 Found {len(questions_to_process)} questions needing proper quality verification")
        
        if len(questions_to_process) == 0:
            logger.info("✅ No questions need processing")
            return
        
        success_count = 0
        failed_count = 0
        
        for i, question in enumerate(questions_to_process, 1):
            try:
                logger.info(f"🔄 Processing {i}/{len(questions_to_process)}: {question.id[:8]}... | {question.subcategory}")
                
                # Run proper enrichment with quality verification
                enrichment_result = await regular_questions_enrichment_service.enrich_regular_question(
                    stem=question.stem,
                    current_answer=question.answer,  # CSV answer
                    snap_read=question.snap_read,
                    solution_approach=question.solution_approach,
                    detailed_solution=question.detailed_solution,
                    principle_to_remember=question.principle_to_remember,
                    mcq_options=question.mcq_options
                )
                
                if enrichment_result.get('success'):
                    enrichment_data = enrichment_result.get('enrichment_data', {})
                    
                    # Update enrichment fields
                    for field, value in enrichment_data.items():
                        if hasattr(question, field):
                            setattr(question, field, value)
                    
                    # Commit the changes
                    db.commit()
                    
                    # Check if quality verified
                    if enrichment_data.get('quality_verified'):
                        logger.info(f"   ✅ Quality verified: answer_match={enrichment_data.get('answer_match')}")
                        success_count += 1
                    else:
                        logger.info(f"   ⚠️ Enriched but quality verification failed: answer_match={enrichment_data.get('answer_match')}")
                        failed_count += 1
                
                else:
                    logger.error(f"   ❌ Enrichment failed: {enrichment_result.get('error')}")
                    failed_count += 1
                
                # Progress update
                if i % 10 == 0:
                    logger.info(f"📈 Progress: {i}/{len(questions_to_process)} processed")
                    
            except Exception as e:
                logger.error(f"   ❌ Error processing question {question.id[:8]}: {e}")
                failed_count += 1
                db.rollback()
        
        logger.info(f"\n🎉 PROPER ENRICHMENT COMPLETED!")
        logger.info(f"   ✅ Successfully quality verified: {success_count}")
        logger.info(f"   ⚠️ Failed quality verification: {failed_count}")
        logger.info(f"   📊 Success rate: {(success_count/(success_count+failed_count))*100:.1f}%")
        
        # Final status check
        total_questions = db.execute(select(Question)).scalars().all()
        verified_questions = [q for q in total_questions if q.quality_verified]
        
        logger.info(f"\n📊 FINAL STATUS:")
        logger.info(f"   Total questions: {len(total_questions)}")
        logger.info(f"   Quality verified: {len(verified_questions)} ({(len(verified_questions)/len(total_questions))*100:.1f}%)")
        
        return {
            'success': True,
            'processed': len(questions_to_process),
            'success_count': success_count,
            'failed_count': failed_count
        }
        
    except Exception as e:
        logger.error(f"❌ Critical error in proper enrichment: {e}")
        return {'success': False, 'error': str(e)}
        
    finally:
        db.close()

async def main():
    """Main function"""
    result = await run_proper_enrichment()
    
    if result.get('success'):
        print(f"\n✅ Proper enrichment completed successfully!")
        print(f"   Processed: {result['processed']} questions")
        print(f"   Quality verified: {result['success_count']}")
        print(f"   Failed verification: {result['failed_count']}")
    else:
        print(f"\n❌ Proper enrichment failed: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    asyncio.run(main())
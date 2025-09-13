#!/usr/bin/env python3
"""
Run quality verification in batches of 50 questions
Restart-safe and progress tracking
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

async def run_batched_quality_verification(batch_size=50):
    """Run quality verification in batches"""
    
    db = SessionLocal()
    try:
        logger.info(f"🚀 Starting BATCHED quality verification (batch size: {batch_size})")
        
        # Get total counts
        total_questions = db.execute(select(Question)).scalars().all()
        total_count = len(total_questions)
        
        # Find unprocessed questions (those without answer_match populated)
        unprocessed_questions = db.execute(
            select(Question)
            .where(Question.answer_match.is_(None))
            .limit(5000)  # Safety limit
        ).scalars().all()
        
        unprocessed_count = len(unprocessed_questions)
        processed_count = total_count - unprocessed_count
        
        logger.info(f"📊 BATCH STATUS:")
        logger.info(f"   Total Questions: {total_count}")
        logger.info(f"   Already Processed: {processed_count}")
        logger.info(f"   Remaining to Process: {unprocessed_count}")
        logger.info(f"   Batches Needed: {(unprocessed_count + batch_size - 1) // batch_size}")
        
        if unprocessed_count == 0:
            logger.info("✅ All questions already processed!")
            return {"status": "complete", "processed": 0}
        
        # Process in batches
        batch_num = 1
        total_success = 0
        total_failed = 0
        
        for i in range(0, unprocessed_count, batch_size):
            batch_questions = unprocessed_questions[i:i + batch_size]
            current_batch_size = len(batch_questions)
            
            logger.info(f"\n🔄 BATCH {batch_num}: Processing questions {i+1}-{i+current_batch_size} of {unprocessed_count}")
            
            batch_success = 0
            batch_failed = 0
            
            for j, question in enumerate(batch_questions, 1):
                try:
                    logger.info(f"   Processing {j}/{current_batch_size}: {question.id[:8]}... | {question.subcategory}")
                    
                    # Run enrichment with quality verification
                    enrichment_result = await regular_questions_enrichment_service.enrich_regular_question(
                        stem=question.stem,
                        current_answer=question.answer,
                        snap_read=question.snap_read,
                        solution_approach=question.solution_approach,
                        detailed_solution=question.detailed_solution,
                        principle_to_remember=question.principle_to_remember,
                        mcq_options=question.mcq_options
                    )
                    
                    if enrichment_result.get('success'):
                        enrichment_data = enrichment_result.get('enrichment_data', {})
                        
                        # Update all enrichment fields
                        for field, value in enrichment_data.items():
                            if hasattr(question, field):
                                setattr(question, field, value)
                        
                        # Quality verification status
                        if enrichment_data.get('quality_verified'):
                            logger.info(f"      ✅ Quality verified: answer_match={enrichment_data.get('answer_match')}")
                            batch_success += 1
                        else:
                            logger.info(f"      ⚠️ Quality failed: answer_match={enrichment_data.get('answer_match')}")
                            batch_failed += 1
                    else:
                        logger.error(f"      ❌ Enrichment failed: {enrichment_result.get('error')}")
                        batch_failed += 1
                        
                except Exception as e:
                    logger.error(f"      ❌ Error processing {question.id[:8]}: {e}")
                    batch_failed += 1
            
            # Commit batch
            try:
                db.commit()
                logger.info(f"✅ BATCH {batch_num} COMPLETED: {batch_success} verified, {batch_failed} failed")
            except Exception as e:
                logger.error(f"❌ Batch commit failed: {e}")
                db.rollback()
            
            total_success += batch_success
            total_failed += batch_failed
            batch_num += 1
            
            # Progress update
            processed_so_far = processed_count + (batch_num - 1) * batch_size
            progress_pct = (processed_so_far / total_count) * 100
            logger.info(f"📈 OVERALL PROGRESS: {processed_so_far}/{total_count} ({progress_pct:.1f}%)")
        
        logger.info(f"\n🎉 BATCHED PROCESSING COMPLETED!")
        logger.info(f"   Batches Processed: {batch_num - 1}")
        logger.info(f"   Total Success: {total_success}")
        logger.info(f"   Total Failed: {total_failed}")
        logger.info(f"   Success Rate: {(total_success/(total_success+total_failed))*100:.1f}%")
        
        return {
            "status": "success",
            "batches": batch_num - 1,
            "success_count": total_success,
            "failed_count": total_failed
        }
        
    except Exception as e:
        logger.error(f"❌ Critical error in batched processing: {e}")
        return {'status': 'error', 'error': str(e)}
        
    finally:
        db.close()

async def main():
    """Main function"""
    result = await run_batched_quality_verification(batch_size=50)
    
    if result.get('status') == 'success':
        print(f"\n✅ Batched quality verification completed!")
        print(f"   Batches: {result['batches']}")
        print(f"   Success: {result['success_count']}")
        print(f"   Failed: {result['failed_count']}")
    else:
        print(f"\n❌ Batched processing failed: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    asyncio.run(main())
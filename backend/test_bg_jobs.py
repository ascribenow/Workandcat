#!/usr/bin/env python3
"""
Test Background Job System
Quick test to verify the background job system is working
"""

import asyncio
import logging
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.bg_job_queue import job_queue
from services.bg_job_handlers import (
    handle_session_summarization,
    handle_personalized_planning,
    handle_concept_analysis,
    handle_coverage_update
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_bg_job_system():
    """Test the background job system"""
    
    logger.info("🧪 Testing Background Job System...")
    
    # Get a real user ID for testing
    from database import SessionLocal
    from sqlalchemy import text
    
    db = SessionLocal()
    try:
        result = db.execute(text('SELECT id FROM users LIMIT 1')).fetchone()
        if not result:
            logger.error("❌ No users found in database for testing")
            return False
        test_user_id = result[0]
        logger.info(f"Using test user: {test_user_id[:8]}...")
    except Exception as e:
        logger.error(f"❌ Failed to get test user: {e}")
        return False
    finally:
        db.close()
    
    # Register handlers
    job_queue.register_handler("session_summarization", handle_session_summarization)
    job_queue.register_handler("personalized_planning", handle_personalized_planning)
    job_queue.register_handler("concept_analysis", handle_concept_analysis)
    job_queue.register_handler("coverage_update", handle_coverage_update)
    
    # Test 1: Enqueue a test job
    logger.info("📋 Test 1: Enqueuing test job...")
    try:
        job_id = await job_queue.enqueue_job(
            job_type="coverage_update",
            job_data={
                "update_scope": "test",
                "test_mode": True
            },
            user_id=test_user_id
        )
        logger.info(f"✅ Test job enqueued successfully: {job_id}")
    except Exception as e:
        logger.error(f"❌ Failed to enqueue test job: {e}")
        return False
    
    # Test 2: Get queue stats
    logger.info("📊 Test 2: Getting queue stats...")
    try:
        stats = await job_queue.get_queue_stats()
        logger.info(f"✅ Queue stats: {stats}")
    except Exception as e:
        logger.error(f"❌ Failed to get queue stats: {e}")
        return False
    
    # Test 3: Process a single job (dry run)
    logger.info("⚙️ Test 3: Processing single job...")
    try:
        processed = await job_queue.process_single_job()
        if processed:
            logger.info("✅ Successfully processed a job")
        else:
            logger.info("ℹ️ No jobs available to process")
    except Exception as e:
        logger.error(f"❌ Failed to process job: {e}")
        return False
    
    logger.info("🎉 Background job system test completed successfully!")
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(test_bg_job_system())
        if success:
            logger.info("✅ All tests passed!")
            sys.exit(0)
        else:
            logger.error("❌ Some tests failed!")
            sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        sys.exit(1)
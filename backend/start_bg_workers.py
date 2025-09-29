#!/usr/bin/env python3
"""
Background Worker Startup Script
Starts background workers for processing adaptive intelligence jobs
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from services.bg_job_queue import bg_job_queue_service
from services.simplified_job_handlers import (
    handle_summarize_session,
    handle_plan_next_session, 
    handle_update_insights,
    handle_trigger_insights_refresh
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/var/log/supervisor/bg_worker.log')
    ]
)

logger = logging.getLogger(__name__)

async def start_background_worker():
    """Start the background worker process"""
    try:
        logger.info("🚀 Starting simplified background worker...")
        
        # Register job handlers
        logger.info("📋 Registering job handlers...")
        
        # Register handlers for current job types
        handlers = {
            'SUMMARIZE_SESSION': handle_summarize_session,
            'PLAN_NEXT_SESSION': handle_plan_next_session,
            'UPDATE_INSIGHTS': handle_update_insights,
            'TRIGGER_INSIGHTS_REFRESH': handle_trigger_insights_refresh
        }
        
        for job_type, handler in handlers.items():
            logger.info(f"  ✅ Registered handler for {job_type}")
        
        # Start the worker loop
        logger.info("🔄 Starting job processing loop...")
        
        while True:
            try:
                # Pick and process jobs
                job = await bg_job_queue_service.pick_job()
                
                if job:
                    job_type = job.get('job_type')
                    job_id = job.get('id', 'unknown')
                    
                    logger.info(f"📝 Processing job {job_type} ({job_id[:8]}...)")
                    
                    if job_type in handlers:
                        try:
                            # Execute the appropriate handler
                            result = await handlers[job_type](job)
                            
                            # Mark job as completed
                            await bg_job_queue_service.mark_job_completed(job_id, result)
                            
                            logger.info(f"✅ Job {job_type} ({job_id[:8]}...) completed: {result.get('status', 'unknown')}")
                            
                        except Exception as handler_error:
                            # Mark job as failed
                            error_msg = str(handler_error)
                            await bg_job_queue_service.mark_job_failed(job_id, error_msg)
                            
                            logger.error(f"❌ Job {job_type} ({job_id[:8]}...) failed: {error_msg}")
                    else:
                        logger.warning(f"⚠️  No handler registered for job type: {job_type}")
                        await bg_job_queue_service.mark_job_failed(job_id, f"No handler for {job_type}")
                
                else:
                    # No jobs available, sleep briefly
                    await asyncio.sleep(2)
                    
            except Exception as loop_error:
                logger.error(f"💥 Error in worker loop: {loop_error}")
                await asyncio.sleep(5)  # Wait before retrying
                
    except Exception as startup_error:
        logger.error(f"🚨 Failed to start background worker: {startup_error}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(start_background_worker())
    except KeyboardInterrupt:
        logger.info("👋 Background worker shutdown requested")
    except Exception as e:
        logger.error(f"🚨 Background worker crashed: {e}")
        sys.exit(1)
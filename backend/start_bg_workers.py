#!/usr/bin/env python3
"""
Simplified Background Workers - Two Jobs Only
SUMMARIZE_SESSION → PLAN_NEXT_SESSION
"""

import asyncio
import logging
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.bg_job_queue import job_queue

async def run_simplified_worker():
    """Run simplified worker - no complex management, just process jobs"""
    logger = logging.getLogger(__name__)
    logger.info("🚀 Starting simplified background worker...")
    
    try:
        # Simple worker loop - just start processing
        await job_queue.start_worker()
        
    except KeyboardInterrupt:
        logger.info("⌨️ Keyboard interrupt - stopping worker...")
        job_queue.stop_worker()
    except Exception as e:
        logger.error(f"❌ Worker error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Simple logging setup
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(run_simplified_worker())
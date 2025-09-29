#!/usr/bin/env python3
"""
Background Worker Startup Script
Starts background workers for processing adaptive intelligence jobs
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from services.bg_job_queue import job_queue

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
    """Start the background worker process using built-in job queue worker"""
    try:
        logger.info("🚀 Starting simplified background worker...")
        logger.info("🔄 Starting built-in job queue worker...")
        
        # Use the built-in worker from job_queue
        await job_queue.start_worker()
        
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
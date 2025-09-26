#!/usr/bin/env python3
"""
Background Workers Startup Script
Starts background workers for adaptive intelligence processing
"""

import asyncio
import logging
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.bg_worker_manager import run_standalone_workers

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('/var/log/bg_workers.log', mode='a')
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("🚀 Starting Twelvr Background Adaptive Intelligence Workers...")
    
    try:
        asyncio.run(run_standalone_workers())
    except KeyboardInterrupt:
        logger.info("⌨️ Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"❌ Critical error in background workers: {e}")
        sys.exit(1)
    
    logger.info("✅ Background workers stopped gracefully")
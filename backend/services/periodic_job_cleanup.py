"""
Periodic Job Cleanup Service

Runs background tasks to clean up stuck jobs:
- Stuck "running" jobs (> 2 minutes) - reset to queued or mark failed
- Runs every 5 minutes

This ensures the system self-heals when workers crash or hang.
"""

import asyncio
import logging
from services.bg_job_queue import job_queue

logger = logging.getLogger(__name__)

class PeriodicJobCleanupService:
    """Service to periodically clean up stuck jobs"""
    
    def __init__(self):
        self.is_running = False
        self.cleanup_interval = 300  # 5 minutes in seconds
        self.task = None
    
    async def start(self):
        """Start the periodic cleanup task"""
        if self.is_running:
            logger.warning("⚠️  Periodic job cleanup already running")
            return
        
        self.is_running = True
        self.task = asyncio.create_task(self._cleanup_loop())
        logger.info("🧹 Periodic job cleanup service started (runs every 5 minutes)")
    
    async def stop(self):
        """Stop the periodic cleanup task"""
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("⏹️  Periodic job cleanup service stopped")
    
    async def _cleanup_loop(self):
        """Main cleanup loop - runs every 5 minutes"""
        while self.is_running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                if not self.is_running:
                    break
                
                logger.info("🔍 Running periodic stuck job cleanup...")
                
                # Clean up stuck running jobs (> 2 minutes)
                result = await job_queue.cleanup_stuck_running_jobs(timeout_minutes=2)
                
                if result["reset"] > 0 or result["failed"] > 0:
                    logger.info(
                        f"✅ Periodic cleanup completed: "
                        f"{result['reset']} jobs reset, {result['failed']} jobs failed"
                    )
                else:
                    logger.debug("✅ Periodic cleanup completed: No stuck jobs found")
                
            except asyncio.CancelledError:
                logger.info("🛑 Periodic cleanup loop cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Error in periodic cleanup loop: {e}")
                # Continue running even if one iteration fails
                await asyncio.sleep(60)  # Wait 1 minute before retrying

# Global instance
periodic_cleanup_service = PeriodicJobCleanupService()

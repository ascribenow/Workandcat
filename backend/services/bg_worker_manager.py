"""
Background Worker Manager
Manages background worker processes for adaptive intelligence jobs
"""

import asyncio
import logging
import signal
import sys
from typing import List
from contextlib import asynccontextmanager

from services.bg_job_queue import job_queue
from services.bg_job_handlers import (
    handle_session_summarization,
    handle_personalized_planning, 
    handle_concept_analysis,
    handle_coverage_update
)

logger = logging.getLogger(__name__)

class BackgroundWorkerManager:
    """Manages multiple background workers for job processing"""
    
    def __init__(self, worker_count: int = 2):
        self.worker_count = worker_count
        self.workers: List[asyncio.Task] = []
        self.is_running = False
        self._setup_signal_handlers()
        self._register_job_handlers()
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"📡 Received signal {signum}, initiating graceful shutdown...")
            asyncio.create_task(self.stop_all_workers())
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    
    def _register_job_handlers(self):
        """Register job handlers with the job queue"""
        job_queue.register_handler("session_summarization", handle_session_summarization)
        job_queue.register_handler("personalized_planning", handle_personalized_planning)
        job_queue.register_handler("concept_analysis", handle_concept_analysis)
        job_queue.register_handler("coverage_update", handle_coverage_update)
        
        logger.info("✅ All job handlers registered successfully")
    
    async def start_workers(self):
        """Start all background workers"""
        if self.is_running:
            logger.warning("⚠️ Workers already running")
            return
        
        self.is_running = True
        logger.info(f"🚀 Starting {self.worker_count} background workers...")
        
        # Create worker tasks
        for i in range(self.worker_count):
            worker_task = asyncio.create_task(
                self._run_worker(worker_id=f"worker-{i+1}"),
                name=f"bg-worker-{i+1}"
            )
            self.workers.append(worker_task)
        
        logger.info(f"✅ {len(self.workers)} background workers started successfully")
    
    async def stop_all_workers(self):
        """Stop all background workers gracefully"""
        if not self.is_running:
            logger.info("⚠️ Workers not running")
            return
        
        logger.info("🛑 Stopping all background workers...")
        self.is_running = False
        
        # Stop the job queue workers
        job_queue.stop_worker()
        
        # Cancel all worker tasks
        for worker in self.workers:
            worker.cancel()
        
        # Wait for workers to finish
        if self.workers:
            try:
                await asyncio.gather(*self.workers, return_exceptions=True)
            except Exception as e:
                logger.error(f"❌ Error stopping workers: {e}")
        
        self.workers.clear()
        logger.info("✅ All background workers stopped")
    
    async def _run_worker(self, worker_id: str):
        """Run a single background worker"""
        logger.info(f"🔄 Worker {worker_id} started")
        
        try:
            # Start the worker loop
            await job_queue.start_worker()
        except asyncio.CancelledError:
            logger.info(f"🔄 Worker {worker_id} cancelled gracefully")
        except Exception as e:
            logger.error(f"❌ Worker {worker_id} crashed: {e}")
        finally:
            logger.info(f"🔄 Worker {worker_id} finished")
    
    async def get_worker_status(self) -> dict:
        """Get status of all workers"""
        active_workers = sum(1 for worker in self.workers if not worker.done())
        
        queue_stats = await job_queue.get_queue_stats()
        
        return {
            "manager_running": self.is_running,
            "total_workers": len(self.workers),
            "active_workers": active_workers,
            "queue_stats": queue_stats,
            "worker_details": [
                {
                    "name": worker.get_name(),
                    "done": worker.done(),
                    "cancelled": worker.cancelled(),
                    "exception": str(worker.exception()) if worker.done() and worker.exception() else None
                }
                for worker in self.workers
            ]
        }
    
    async def restart_failed_workers(self):
        """Restart any failed workers"""
        if not self.is_running:
            return
        
        failed_workers = [w for w in self.workers if w.done() and not w.cancelled()]
        
        if failed_workers:
            logger.warning(f"🔄 Restarting {len(failed_workers)} failed workers")
            
            # Remove failed workers
            for worker in failed_workers:
                self.workers.remove(worker)
            
            # Start replacement workers
            for i, worker in enumerate(failed_workers):
                worker_id = f"worker-restart-{i+1}"
                new_worker = asyncio.create_task(
                    self._run_worker(worker_id=worker_id),
                    name=worker_id
                )
                self.workers.append(new_worker)
            
            logger.info(f"✅ {len(failed_workers)} workers restarted")

# Global worker manager instance
worker_manager = BackgroundWorkerManager()

# Context manager for startup/shutdown
@asynccontextmanager
async def lifespan_manager():
    """Context manager for application lifespan events"""
    # Startup
    logger.info("🚀 Starting background worker manager...")
    try:
        await worker_manager.start_workers()
        yield
    finally:
        # Shutdown
        logger.info("🛑 Shutting down background worker manager...")
        await worker_manager.stop_all_workers()

# Standalone worker script
async def run_standalone_workers():
    """Run workers as a standalone process"""
    logger.info("🚀 Starting standalone background workers...")
    
    try:
        await worker_manager.start_workers()
        
        # Keep running until interrupted
        while worker_manager.is_running:
            await asyncio.sleep(10)
            
            # Check for failed workers and restart
            await worker_manager.restart_failed_workers()
            
    except KeyboardInterrupt:
        logger.info("⌨️ Keyboard interrupt received")
    except Exception as e:
        logger.error(f"❌ Standalone worker error: {e}")
    finally:
        await worker_manager.stop_all_workers()

if __name__ == "__main__":
    # Run as standalone script
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(run_standalone_workers())
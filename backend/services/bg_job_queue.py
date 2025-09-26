"""
Background Job Queue System
Handles job queuing, processing, retry logic with exponential backoff
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Callable, List
from enum import Enum

from database import SessionLocal
from sqlalchemy import text, select
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

class JobStatus(Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class JobType(Enum):
    SESSION_SUMMARIZATION = "session_summarization"
    PERSONALIZED_PLANNING = "personalized_planning"
    CONCEPT_ANALYSIS = "concept_analysis"
    COVERAGE_UPDATE = "coverage_update"

class BackgroundJobQueue:
    """Background job queue with retry logic and exponential backoff"""
    
    def __init__(self):
        self.job_handlers: Dict[str, Callable] = {}
        self.worker_id = f"worker-{uuid.uuid4().hex[:8]}"
        self.is_running = False
        self.poll_interval = 1.0  # 1 second polling as specified
        
    def register_handler(self, job_type: str, handler: Callable):
        """Register a job handler function"""
        self.job_handlers[job_type] = handler
        logger.info(f"✅ Registered handler for job type: {job_type}")
    
    async def enqueue_job(
        self, 
        job_type: str, 
        job_data: Dict[str, Any],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        max_attempts: int = 6,
        deduplicate: bool = True
    ) -> int:
        """
        Enqueue a background job for processing with deduplication
        
        Args:
            deduplicate: If True, prevent duplicate jobs for same user/session/type
            
        Returns:
            Job ID for tracking
        """
        db = SessionLocal()
        try:
            # Check for existing jobs if deduplication is enabled
            if deduplicate and user_id:
                existing_check_sql = """
                    SELECT id FROM bg_jobs 
                    WHERE user_id = :user_id 
                      AND job_type = :job_type 
                      AND status IN ('queued', 'processing')
                """
                params = {"user_id": user_id, "job_type": job_type}
                
                if session_id:
                    existing_check_sql += " AND session_id = :session_id"
                    params["session_id"] = session_id
                else:
                    existing_check_sql += " AND session_id IS NULL"
                
                existing_job = db.execute(text(existing_check_sql), params).fetchone()
                
                if existing_job:
                    logger.info(f"🔄 Duplicate job prevented for {job_type}, user {(user_id or 'N/A')[:8]}, existing job: {existing_job.id}")
                    return existing_job.id
            
            # Insert job with retry configuration
            result = db.execute(text("""
                INSERT INTO bg_jobs (
                    job_type, job_data, user_id, session_id, 
                    max_attempts, created_at, next_attempt_at
                ) VALUES (
                    :job_type, :job_data, :user_id, :session_id,
                    :max_attempts, :created_at, :next_attempt_at
                ) RETURNING id
            """), {
                "job_type": job_type,
                "job_data": json.dumps(job_data),
                "user_id": user_id,
                "session_id": session_id,
                "max_attempts": max_attempts,
                "created_at": datetime.now(timezone.utc),
                "next_attempt_at": datetime.now(timezone.utc)
            })
            
            job_id = result.scalar()
            db.commit()
            
            logger.info(f"📋 Enqueued job {job_id}: {job_type} for user {(user_id or 'N/A')[:8]}")
            return job_id
            
        except IntegrityError as e:
            # Handle unique constraint violations gracefully
            db.rollback()
            if "unique" in str(e).lower():
                logger.info(f"🔄 Duplicate job prevented by constraint for {job_type}, user {(user_id or 'N/A')[:8]}")
                # Try to find the existing job
                existing_job = db.execute(text("""
                    SELECT id FROM bg_jobs 
                    WHERE user_id = :user_id AND job_type = :job_type 
                      AND status IN ('queued', 'processing')
                    ORDER BY created_at DESC LIMIT 1
                """), {"user_id": user_id, "job_type": job_type}).fetchone()
                return existing_job.id if existing_job else -1
            else:
                logger.error(f"❌ Failed to enqueue job {job_type}: {e}")
                raise
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Failed to enqueue job {job_type}: {e}")
            raise
        finally:
            db.close()
    
    async def get_next_job(self) -> Optional[Dict[str, Any]]:
        """
        Get next available job using FOR UPDATE SKIP LOCKED for safe concurrent processing
        
        Returns:
            Job data dict or None if no jobs available
        """
        db = SessionLocal()
        try:
            # Use advisory lock pattern for safe job picking
            result = db.execute(text("""
                UPDATE bg_jobs 
                SET status = 'processing', 
                    started_at = :started_at,
                    worker_id = :worker_id,
                    attempt_count = attempt_count + 1
                WHERE id = (
                    SELECT id FROM bg_jobs 
                    WHERE status IN ('queued', 'failed') 
                      AND next_attempt_at <= :now
                      AND attempt_count < max_attempts
                    ORDER BY created_at ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                RETURNING id, job_type, job_data, user_id, session_id, attempt_count, max_attempts
            """), {
                "started_at": datetime.now(timezone.utc),
                "worker_id": self.worker_id,
                "now": datetime.now(timezone.utc)
            })
            
            job_row = result.fetchone()
            if not job_row:
                return None
                
            db.commit()
            
            # Convert to dict for handler
            job_data = {
                "id": job_row.id,
                "job_type": job_row.job_type,
                "job_data": job_row.job_data if isinstance(job_row.job_data, dict) else json.loads(job_row.job_data or '{}'),
                "user_id": job_row.user_id,
                "session_id": job_row.session_id,
                "attempt_count": job_row.attempt_count,
                "max_attempts": job_row.max_attempts
            }
            
            logger.info(f"🎯 Picked job {job_data['id']}: {job_data['job_type']} (attempt {job_data['attempt_count']}/{job_data['max_attempts']})")
            return job_data
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Failed to get next job: {e}")
            return None
        finally:
            db.close()
    
    async def mark_job_completed(self, job_id: int, result: Dict[str, Any] = None):
        """Mark job as successfully completed"""
        db = SessionLocal()
        try:
            processing_duration = self._calculate_processing_duration(job_id)
            
            db.execute(text("""
                UPDATE bg_jobs 
                SET status = 'completed',
                    completed_at = :completed_at,
                    result = :result,
                    processing_duration_ms = :duration_ms
                WHERE id = :job_id
            """), {
                "job_id": job_id,
                "completed_at": datetime.now(timezone.utc),
                "result": json.dumps(result or {}),
                "duration_ms": processing_duration
            })
            
            db.commit()
            logger.info(f"✅ Job {job_id} completed successfully ({processing_duration}ms)")
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Failed to mark job {job_id} completed: {e}")
            raise
        finally:
            db.close()
    
    async def mark_job_failed(self, job_id: int, error_message: str, attempt_count: int, max_attempts: int):
        """Mark job as failed with retry logic"""
        db = SessionLocal()
        try:
            processing_duration = self._calculate_processing_duration(job_id)
            
            # Calculate next retry time with exponential backoff
            if attempt_count < max_attempts:
                # Exponential backoff: 1m → 2m → 4m → 8m → 16m → 30m (capped)
                backoff_minutes = min(2 ** (attempt_count - 1), 30)
                next_attempt_at = datetime.now(timezone.utc) + timedelta(minutes=backoff_minutes)
                new_status = 'failed'  # Will be picked up again for retry
                
                logger.warning(f"⚠️ Job {job_id} failed (attempt {attempt_count}/{max_attempts}), retry in {backoff_minutes}m: {error_message[:100]}")
            else:
                # Max attempts reached, permanently failed
                next_attempt_at = None
                new_status = 'failed'
                
                logger.error(f"❌ Job {job_id} permanently failed after {attempt_count} attempts: {error_message[:100]}")
            
            db.execute(text("""
                UPDATE bg_jobs 
                SET status = :status,
                    error_message = :error_message,
                    next_attempt_at = :next_attempt_at,
                    processing_duration_ms = :duration_ms
                WHERE id = :job_id
            """), {
                "job_id": job_id,
                "status": new_status,
                "error_message": error_message[:1000],  # Truncate long errors
                "next_attempt_at": next_attempt_at,
                "duration_ms": processing_duration
            })
            
            db.commit()
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Failed to mark job {job_id} as failed: {e}")
            raise
        finally:
            db.close()
    
    def _calculate_processing_duration(self, job_id: int) -> int:
        """Calculate processing duration for a job"""
        db = SessionLocal()
        try:
            result = db.execute(text("""
                SELECT EXTRACT(EPOCH FROM (NOW() - started_at)) * 1000 as duration_ms
                FROM bg_jobs WHERE id = :job_id
            """), {"job_id": job_id})
            
            row = result.fetchone()
            return int(row.duration_ms) if row and row.duration_ms else 0
            
        except Exception:
            return 0
        finally:
            db.close()
    
    async def process_single_job(self) -> bool:
        """
        Process a single job from the queue
        
        Returns:
            True if a job was processed, False if no jobs available
        """
        job = await self.get_next_job()
        if not job:
            return False
        
        job_id = job["id"]
        job_type = job["job_type"]
        
        try:
            # Get handler for this job type
            if job_type not in self.job_handlers:
                raise Exception(f"No handler registered for job type: {job_type}")
            
            handler = self.job_handlers[job_type]
            
            # Execute job handler
            start_time = time.time()
            result = await handler(job)
            processing_time = int((time.time() - start_time) * 1000)
            
            # Mark as completed
            await self.mark_job_completed(job_id, {
                "processing_time_ms": processing_time,
                "handler_result": result
            })
            
            return True
            
        except Exception as e:
            # Mark as failed with retry logic
            error_msg = f"Job handler failed: {str(e)}"
            await self.mark_job_failed(job_id, error_msg, job["attempt_count"], job["max_attempts"])
            return True
    
    async def start_worker(self):
        """Start the background worker loop"""
        self.is_running = True
        logger.info(f"🚀 Starting background worker {self.worker_id}")
        
        while self.is_running:
            try:
                # Process one job
                job_processed = await self.process_single_job()
                
                if not job_processed:
                    # No jobs available, wait before next poll
                    await asyncio.sleep(self.poll_interval)
                # If job was processed, immediately check for next job (no delay)
                
            except Exception as e:
                logger.error(f"❌ Worker {self.worker_id} error: {e}")
                await asyncio.sleep(self.poll_interval)
    
    def stop_worker(self):
        """Stop the background worker"""
        self.is_running = False
        logger.info(f"🛑 Stopping background worker {self.worker_id}")
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get job queue statistics for observability"""
        db = SessionLocal()
        try:
            result = db.execute(text("""
                SELECT 
                    status,
                    job_type,
                    COUNT(*) as count,
                    AVG(EXTRACT(EPOCH FROM (COALESCE(completed_at, NOW()) - created_at)) * 1000) as avg_duration_ms
                FROM bg_jobs 
                WHERE created_at > NOW() - INTERVAL '24 hours'
                GROUP BY status, job_type
                ORDER BY status, job_type
            """))
            
            stats = {}
            for row in result.fetchall():
                key = f"{row.status}_{row.job_type}"
                stats[key] = {
                    "count": row.count,
                    "avg_duration_ms": int(row.avg_duration_ms or 0)
                }
            
            # Get overall queue depth
            queue_depth = db.execute(text("""
                SELECT COUNT(*) FROM bg_jobs 
                WHERE status IN ('queued', 'failed') 
                AND next_attempt_at <= NOW()
                AND attempt_count < max_attempts
            """)).scalar()
            
            return {
                "queue_depth": queue_depth,
                "worker_id": self.worker_id,
                "stats_by_type": stats,
                "is_running": self.is_running
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get queue stats: {e}")
            return {"error": str(e)}
        finally:
            db.close()

# Global job queue instance
job_queue = BackgroundJobQueue()
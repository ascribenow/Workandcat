"""
Simplified Background Job Queue System
Three job types: SUMMARIZE_SESSION → PLAN_NEXT_SESSION → UPDATE_INSIGHTS
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from enum import Enum

from database import SessionLocal
from sqlalchemy import text
from utils.timezone_utils import now_ist

logger = logging.getLogger(__name__)

class JobType(Enum):
    SUMMARIZE_SESSION = "SUMMARIZE_SESSION"
    PLAN_NEXT_SESSION = "PLAN_NEXT_SESSION"
    UPDATE_INSIGHTS = "UPDATE_INSIGHTS"

class JobStatus(Enum):
    QUEUED = "queued"
    RUNNING = "running" 
    SUCCEEDED = "succeeded"
    FAILED = "failed"

class SimplifiedJobQueue:
    """Lean job queue - two job types only with dedupe_key idempotency"""
    
    def __init__(self):
        self.worker_id = f"worker-{uuid.uuid4().hex[:8]}"
        self.is_running = False
        self.poll_interval = 1.0  # 1 second polling
    
    async def cleanup_stuck_jobs(
        self,
        job_type: str,
        user_id: str,
        session_id: Optional[str] = None,
        queue_timeout_minutes: int = 2
    ) -> int:
        """
        Clean up jobs that are stuck in queue for too long
        
        Removes jobs that have been sitting in 'queued' status without being
        picked up by a worker for more than the specified timeout period.
        This prevents jobs from blocking new job creation when workers are down.
        
        Args:
            job_type: Type of job to clean
            user_id: User ID
            session_id: Session ID (optional, for session-specific jobs)
            queue_timeout_minutes: Minutes before considering a queued job as stuck (default: 2)
            
        Returns:
            Number of jobs deleted
        """
        db = SessionLocal()
        try:
            # Build cleanup query for stuck queued jobs
            if session_id:
                # For session-specific jobs (SUMMARIZE_SESSION)
                cleanup_query = text("""
                    DELETE FROM bg_jobs
                    WHERE user_id = :user_id
                    AND session_id = :session_id
                    AND job_type = :job_type
                    AND status = 'queued'
                    AND created_at < NOW() - INTERVAL ':timeout_minutes minutes'
                    RETURNING id, attempts, status, created_at
                """)
                params = {
                    "user_id": user_id,
                    "session_id": session_id,
                    "job_type": job_type,
                    "timeout_minutes": queue_timeout_minutes
                }
            else:
                # For user-level jobs (PLAN_NEXT_SESSION, UPDATE_INSIGHTS)
                cleanup_query = text("""
                    DELETE FROM bg_jobs
                    WHERE user_id = :user_id
                    AND job_type = :job_type
                    AND status = 'queued'
                    AND created_at < NOW() - INTERVAL ':timeout_minutes minutes'
                    RETURNING id, attempts, status, created_at
                """)
                params = {
                    "user_id": user_id,
                    "job_type": job_type,
                    "timeout_minutes": queue_timeout_minutes
                }
            
            result = db.execute(cleanup_query, params)
            deleted_jobs = result.fetchall()
            
            if deleted_jobs:
                db.commit()
                logger.warning(
                    f"🧹 Cleaned up {len(deleted_jobs)} stuck jobs for user {user_id[:8]}... "
                    f"job_type={job_type} (stuck in queue > {queue_timeout_minutes} min)"
                )
                for job in deleted_jobs:
                    logger.warning(f"   Deleted stuck job: {job[0]} (created: {job[3]})")
                return len(deleted_jobs)
            
            return 0
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Failed to cleanup stuck jobs: {e}")
            return 0
        finally:
            db.close()
    
    async def cleanup_exhausted_jobs(
        self,
        job_type: str,
        user_id: str,
        session_id: Optional[str] = None
    ) -> int:
        """
        Clean up exhausted jobs that could block dedupe key
        
        Removes jobs that have exhausted all retry attempts and are blocking
        new job creation due to dedupe key constraints.
        
        Args:
            job_type: Type of job to clean
            user_id: User ID
            session_id: Session ID (optional, for session-specific jobs)
            
        Returns:
            Number of jobs deleted
        """
        db = SessionLocal()
        try:
            # Build cleanup query based on dedupe key format
            if session_id:
                # For session-specific jobs (SUMMARIZE_SESSION)
                cleanup_query = text("""
                    DELETE FROM bg_jobs
                    WHERE user_id = :user_id
                    AND session_id = :session_id
                    AND job_type = :job_type
                    AND attempts >= max_attempts
                    AND status IN ('queued', 'failed')
                    RETURNING id, attempts, status, created_at
                """)
                params = {
                    "user_id": user_id,
                    "session_id": session_id,
                    "job_type": job_type
                }
            else:
                # For user-level jobs (PLAN_NEXT_SESSION, UPDATE_INSIGHTS)
                # Only clean jobs older than 3 days to avoid interfering with recent failures
                cleanup_query = text("""
                    DELETE FROM bg_jobs
                    WHERE user_id = :user_id
                    AND job_type = :job_type
                    AND attempts >= max_attempts
                    AND status IN ('queued', 'failed')
                    AND created_at < NOW() - INTERVAL '3 days'
                    RETURNING id, attempts, status, created_at
                """)
                params = {
                    "user_id": user_id,
                    "job_type": job_type
                }
            
            result = db.execute(cleanup_query, params)
            deleted_jobs = result.fetchall()
            
            if deleted_jobs:
                db.commit()
                logger.warning(f"🧹 Cleaned up {len(deleted_jobs)} exhausted {job_type} job(s) for user {user_id[:8]}")
                for job in deleted_jobs:
                    logger.warning(f"   - Job {str(job[0])[:8]}: {job[1]} attempts, status={job[2]}, created={job[3]}")
                return len(deleted_jobs)
            else:
                logger.debug(f"✅ No exhausted {job_type} jobs to clean for user {user_id[:8]}")
                return 0
                
        except Exception as e:
            logger.error(f"⚠️ Failed to cleanup exhausted jobs (non-fatal): {e}")
            db.rollback()
            return 0
        finally:
            db.close()
        
    async def enqueue_job(
        self, 
        job_type: str,
        user_id: str,
        session_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        max_attempts: int = 6
    ) -> str:
        """
        Enqueue background job with dedupe_key idempotency and correlation ID for tracing
        
        Args:
            job_type: Type of job (SUMMARIZE_SESSION, PLAN_NEXT_SESSION)
            user_id: User ID
            session_id: Session ID (optional)
            correlation_id: Correlation ID for end-to-end tracing (optional)
            max_attempts: Maximum retry attempts
            
        Returns:
            Job ID (UUID) for tracking
        """
        # PHASE 1 FIX: Cleanup exhausted jobs before enqueue to prevent dedupe key blocking
        try:
            deleted_count = await self.cleanup_exhausted_jobs(
                job_type=job_type,
                user_id=user_id,
                session_id=session_id
            )
            
            if deleted_count > 0:
                logger.info(f"🧹 Removed {deleted_count} blocking job(s) before enqueueing {job_type} for user {user_id[:8]}")
        except Exception as cleanup_error:
            # Cleanup is non-fatal - log error but continue with enqueue
            logger.warning(f"⚠️ Cleanup failed but continuing with enqueue: {cleanup_error}")
        
        # Generate correlation_id if not provided
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        # Generate dedupe_key for idempotency
        if session_id:
            dedupe_key = f"u:{user_id}|s:{session_id}|{job_type}"
        else:
            dedupe_key = f"u:{user_id}|{job_type}"
        
        db = SessionLocal()
        try:
            # Insert with ON CONFLICT to handle deduplication
            result = db.execute(text("""
                INSERT INTO bg_jobs (
                    job_type, user_id, session_id, correlation_id, dedupe_key, max_attempts, next_attempt_at
                ) VALUES (
                    :job_type, :user_id, :session_id, :correlation_id, :dedupe_key, :max_attempts, :next_attempt_at
                )
                ON CONFLICT (dedupe_key) DO UPDATE SET
                    next_attempt_at = EXCLUDED.next_attempt_at,
                    correlation_id = EXCLUDED.correlation_id,
                    status = 'queued',
                    started_at = NULL,
                    completed_at = NULL,
                    error_message = NULL
                RETURNING id
            """), {
                "job_type": job_type,
                "user_id": user_id,
                "session_id": session_id,
                "correlation_id": correlation_id,
                "dedupe_key": dedupe_key,
                "max_attempts": max_attempts,
                "next_attempt_at": now_ist()  # FIXED: Use IST
            })
            
            job_id = result.scalar()
            db.commit()
            
            logger.info(f"📋 Enqueued {job_type} job {str(job_id)[:8]} for user {user_id[:8]}")
            return str(job_id)
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Failed to enqueue {job_type}: {e}")
            raise
        finally:
            db.close()
    
    async def get_next_job(self) -> Optional[Dict[str, Any]]:
        """
        Get next job using FOR UPDATE SKIP LOCKED for safe concurrency
        """
        db = SessionLocal()
        try:
            result = db.execute(text("""
                UPDATE bg_jobs 
                SET status = 'running',
                    started_at = :started_at,
                    attempts = attempts + 1
                WHERE id = (
                    SELECT id FROM bg_jobs 
                    WHERE status IN ('queued', 'failed')
                      AND next_attempt_at <= :now
                      AND attempts < max_attempts
                    ORDER BY created_at ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                RETURNING id, job_type, user_id, session_id, attempts, max_attempts, correlation_id
            """), {
                "started_at": now_ist(),  # FIXED: Use IST
                "now": now_ist()  # FIXED: Use IST
            })
            
            job_row = result.fetchone()
            if not job_row:
                return None
            
            db.commit()
            
            return {
                "id": str(job_row.id),
                "job_type": job_row.job_type,
                "user_id": job_row.user_id,
                "session_id": job_row.session_id,
                "attempts": job_row.attempts,
                "max_attempts": job_row.max_attempts,
                "correlation_id": job_row.correlation_id
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Failed to get next job: {e}")
            return None
        finally:
            db.close()
    
    async def mark_job_succeeded(self, job_id: str, processing_duration_ms: int):
        """Mark job as successfully completed"""
        db = SessionLocal()
        try:
            db.execute(text("""
                UPDATE bg_jobs 
                SET status = 'succeeded', completed_at = :completed_at
                WHERE id = :job_id
            """), {
                "job_id": job_id,
                "completed_at": now_ist()  # FIXED: Use IST
            })
            db.commit()
            logger.info(f"✅ Job {job_id[:8]} succeeded ({processing_duration_ms}ms)")
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Failed to mark job {job_id[:8]} succeeded: {e}")
            raise
        finally:
            db.close()
    
    async def mark_job_failed(self, job_id: str, error_message: str, attempts: int, max_attempts: int):
        """Mark job as failed with exponential backoff retry"""
        db = SessionLocal()
        try:
            # Calculate next retry with exponential backoff: 1,2,4,8,16,30m (capped)
            if attempts < max_attempts:
                backoff_minutes = min(2 ** (attempts - 1), 30)
                next_attempt_at = now_ist() + timedelta(minutes=backoff_minutes)  # FIXED: Use IST
                new_status = 'failed'  # Will retry
                
                logger.warning(f"⚠️ Job {job_id[:8]} failed (attempt {attempts}/{max_attempts}), retry in {backoff_minutes}m")
            else:
                # Max attempts reached
                next_attempt_at = None
                new_status = 'failed'
                logger.error(f"❌ Job {job_id[:8]} permanently failed after {attempts} attempts")
            
            db.execute(text("""
                UPDATE bg_jobs 
                SET status = :status, error_message = :error_message, next_attempt_at = :next_attempt_at
                WHERE id = :job_id
            """), {
                "job_id": job_id,
                "status": new_status,
                "error_message": error_message[:1000],  # Truncate
                "next_attempt_at": next_attempt_at
            })
            
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Failed to mark job {job_id[:8]} failed: {e}")
            raise
        finally:
            db.close()
    
    async def process_single_job(self) -> bool:
        """Process one job from queue"""
        job = await self.get_next_job()
        if not job:
            return False
        
        job_id = job["id"]
        job_type = job["job_type"]
        
        try:
            start_time = time.time()
            
            # Import and call job handler
            if job_type == JobType.SUMMARIZE_SESSION.value:
                from services.simplified_job_handlers import handle_summarize_session
                await handle_summarize_session(job)
            elif job_type == JobType.PLAN_NEXT_SESSION.value:
                from services.simplified_job_handlers import handle_plan_next_session
                await handle_plan_next_session(job)
            elif job_type == JobType.UPDATE_INSIGHTS.value:
                from services.simplified_job_handlers import handle_update_insights
                await handle_update_insights(job)
            else:
                raise Exception(f"Unknown job type: {job_type}")
            
            processing_duration = int((time.time() - start_time) * 1000)
            await self.mark_job_succeeded(job_id, processing_duration)
            
            return True
            
        except Exception as e:
            error_msg = f"Job handler failed: {str(e)}"
            await self.mark_job_failed(job_id, error_msg, job["attempts"], job["max_attempts"])
            return True
    
    async def start_worker(self):
        """Start background worker loop"""
        self.is_running = True
        logger.info(f"🚀 Starting simplified background worker {self.worker_id}")
        
        while self.is_running:
            try:
                job_processed = await self.process_single_job()
                
                if not job_processed:
                    # No jobs available, poll after interval
                    await asyncio.sleep(self.poll_interval)
                # If job processed, immediately check for next (no delay)
                
            except Exception as e:
                logger.error(f"❌ Worker {self.worker_id} error: {e}")
                await asyncio.sleep(self.poll_interval)
    
    def stop_worker(self):
        """Stop background worker"""
        self.is_running = False
        logger.info(f"🛑 Stopping worker {self.worker_id}")
    
    async def get_queue_depth(self) -> int:
        """Get current queue depth for basic monitoring"""
        db = SessionLocal()
        try:
            result = db.execute(text("""
                SELECT COUNT(*) FROM bg_jobs 
                WHERE status IN ('queued', 'failed') 
                AND next_attempt_at <= NOW()
                AND attempts < max_attempts
            """))
            return result.scalar()
        except Exception as e:
            logger.error(f"❌ Failed to get queue depth: {e}")
            return 0
        finally:
            db.close()

# Global simplified job queue instance  
job_queue = SimplifiedJobQueue()
"""
Background Jobs API
Provides endpoints for monitoring and managing background jobs
"""

import logging
from typing import Optional
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from auth import get_current_user, get_current_admin_user
from database import SessionLocal, User
from sqlalchemy import text
from services.bg_job_queue import job_queue
from services.bg_worker_manager import worker_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bg-jobs", tags=["background_jobs"])

# Request/Response Models
class JobEnqueueRequest(BaseModel):
    job_type: str
    job_data: dict
    user_id: Optional[str] = None
    session_id: Optional[str] = None

@router.get("/status")
async def get_job_status(
    user_id: str = Depends(get_current_user)
):
    """
    Get background job processing status for the current user
    """
    try:
        db = SessionLocal()
        try:
            # Get user's recent jobs
            result = db.execute(text("""
                SELECT job_type, status, created_at, completed_at, 
                       attempt_count, error_message
                FROM bg_jobs 
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                LIMIT 10
            """), {"user_id": user_id})
            
            jobs = []
            for row in result.fetchall():
                jobs.append({
                    "job_type": row.job_type,
                    "status": row.status,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                    "attempt_count": row.attempt_count,
                    "has_error": bool(row.error_message)
                })
            
            # Get queue stats
            queue_stats = await job_queue.get_queue_stats()
            
            return JSONResponse({
                "success": True,
                "recent_jobs": jobs,
                "queue_info": {
                    "queue_depth": queue_stats.get("queue_depth", 0),
                    "worker_running": queue_stats.get("is_running", False)
                }
            })
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Failed to get job status for user {user_id[:8]}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get job status")

@router.get("/health")
async def get_background_jobs_health():
    """
    Health check for background job system (public endpoint)
    """
    try:
        # Get basic queue stats
        queue_stats = await job_queue.get_queue_stats()
        worker_status = await worker_manager.get_worker_status()
        
        # Determine overall health
        is_healthy = (
            worker_status.get("active_workers", 0) > 0 and
            queue_stats.get("queue_depth", 0) < 100  # Alert if queue is backing up
        )
        
        status_code = 200 if is_healthy else 503
        
        return JSONResponse({
            "status": "healthy" if is_healthy else "degraded",
            "background_jobs": "operational" if is_healthy else "issues_detected",
            "active_workers": worker_status.get("active_workers", 0),
            "queue_depth": queue_stats.get("queue_depth", 0),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, status_code=status_code)
        
    except Exception as e:
        logger.error(f"Background jobs health check failed: {e}")
        return JSONResponse({
            "status": "unhealthy",
            "background_jobs": "error",
            "error": str(e)[:100],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, status_code=503)

@router.post("/admin/enqueue")
async def admin_enqueue_job(
    request: JobEnqueueRequest,
    admin_user: User = Depends(get_current_admin_user)
):
    """
    Admin endpoint to manually enqueue a background job
    """
    try:
        job_id = await job_queue.enqueue_job(
            job_type=request.job_type,
            job_data=request.job_data,
            user_id=request.user_id,
            session_id=request.session_id
        )
        
        return JSONResponse({
            "success": True,
            "job_id": job_id,
            "job_type": request.job_type,
            "enqueued_by": admin_user.email
        })
        
    except Exception as e:
        logger.error(f"Admin job enqueue failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to enqueue job: {str(e)}")

@router.get("/admin/stats")
async def get_admin_job_stats(
    admin_user: User = Depends(get_current_admin_user),
    hours: int = Query(default=24, description="Hours of history to analyze")
):
    """
    Admin endpoint to get comprehensive job statistics
    """
    try:
        db = SessionLocal()
        try:
            # Get job statistics for the specified time period
            since = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            # Overall job counts by status and type
            result = db.execute(text("""
                SELECT 
                    job_type,
                    status,
                    COUNT(*) as count,
                    AVG(processing_duration_ms) as avg_duration_ms,
                    AVG(attempt_count) as avg_attempts
                FROM bg_jobs 
                WHERE created_at >= :since
                GROUP BY job_type, status
                ORDER BY job_type, status
            """), {"since": since})
            
            job_stats = {}
            for row in result.fetchall():
                key = f"{row.job_type}_{row.status}"
                job_stats[key] = {
                    "count": row.count,
                    "avg_duration_ms": int(row.avg_duration_ms or 0),
                    "avg_attempts": round(row.avg_attempts or 0, 2)
                }
            
            # Failed jobs with error details
            failed_jobs_result = db.execute(text("""
                SELECT job_type, error_message, COUNT(*) as error_count
                FROM bg_jobs
                WHERE created_at >= :since AND status = 'failed'
                GROUP BY job_type, error_message
                ORDER BY error_count DESC
                LIMIT 10
            """), {"since": since})
            
            error_patterns = []
            for row in failed_jobs_result.fetchall():
                error_patterns.append({
                    "job_type": row.job_type,
                    "error_message": row.error_message[:200] if row.error_message else "Unknown error",
                    "count": row.error_count
                })
            
            # Queue performance metrics
            queue_stats = await job_queue.get_queue_stats()
            worker_status = await worker_manager.get_worker_status()
            
            return JSONResponse({
                "success": True,
                "time_period_hours": hours,
                "job_statistics": job_stats,
                "error_patterns": error_patterns,
                "current_queue": {
                    "depth": queue_stats.get("queue_depth", 0),
                    "active_workers": worker_status.get("active_workers", 0),
                    "total_workers": worker_status.get("total_workers", 0)
                },
                "worker_details": worker_status.get("worker_details", [])
            })
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Admin job stats failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get job statistics: {str(e)}")

@router.post("/admin/retry-failed")
async def admin_retry_failed_jobs(
    admin_user: User = Depends(get_current_admin_user),
    job_type: Optional[str] = Query(default=None, description="Job type to retry (all if not specified)"),
    max_jobs: int = Query(default=10, description="Maximum number of jobs to retry")
):
    """
    Admin endpoint to retry failed jobs
    """
    try:
        db = SessionLocal()
        try:
            # Build query to find failed jobs
            base_query = """
                UPDATE bg_jobs 
                SET status = 'queued', 
                    next_attempt_at = NOW(),
                    error_message = NULL
                WHERE status = 'failed' 
                  AND attempt_count < max_attempts
            """
            
            params = {"max_jobs": max_jobs}
            
            if job_type:
                query = base_query + " AND job_type = :job_type ORDER BY created_at DESC LIMIT :max_jobs RETURNING id, job_type"
                params["job_type"] = job_type
            else:
                query = base_query + " ORDER BY created_at DESC LIMIT :max_jobs RETURNING id, job_type"
            
            result = db.execute(text(query), params)
            retried_jobs = result.fetchall()
            
            db.commit()
            
            return JSONResponse({
                "success": True,
                "retried_count": len(retried_jobs),
                "retried_jobs": [
                    {"id": row.id, "job_type": row.job_type} 
                    for row in retried_jobs
                ],
                "retried_by": admin_user.email
            })
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Admin retry failed jobs error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retry jobs: {str(e)}")

@router.get("/admin/queue")
async def get_admin_queue_view(
    admin_user: User = Depends(get_current_admin_user),
    status: Optional[str] = Query(default=None, description="Filter by job status"),
    limit: int = Query(default=50, description="Maximum number of jobs to return")
):
    """
    Admin endpoint to view current job queue
    """
    try:
        db = SessionLocal()
        try:
            # Build query based on filters
            base_query = """
                SELECT id, job_type, status, user_id, session_id,
                       created_at, started_at, completed_at, 
                       attempt_count, max_attempts, next_attempt_at,
                       error_message, processing_duration_ms
                FROM bg_jobs
            """
            
            params = {"limit": limit}
            where_conditions = []
            
            if status:
                where_conditions.append("status = :status")
                params["status"] = status
            
            if where_conditions:
                query = base_query + " WHERE " + " AND ".join(where_conditions)
            else:
                query = base_query
            
            query += " ORDER BY created_at DESC LIMIT :limit"
            
            result = db.execute(text(query), params)
            
            jobs = []
            for row in result.fetchall():
                jobs.append({
                    "id": row.id,
                    "job_type": row.job_type,
                    "status": row.status,
                    "user_id": row.user_id,
                    "session_id": row.session_id,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "started_at": row.started_at.isoformat() if row.started_at else None,
                    "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                    "attempt_count": row.attempt_count,
                    "max_attempts": row.max_attempts,
                    "next_attempt_at": row.next_attempt_at.isoformat() if row.next_attempt_at else None,
                    "has_error": bool(row.error_message),
                    "error_preview": row.error_message[:100] if row.error_message else None,
                    "processing_duration_ms": row.processing_duration_ms
                })
            
            return JSONResponse({
                "success": True,
                "jobs": jobs,
                "total_returned": len(jobs),
                "filters_applied": {
                    "status": status,
                    "limit": limit
                }
            })
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Admin queue view failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get queue view: {str(e)}")
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

from auth import get_current_user
from database import SessionLocal, User
from sqlalchemy import text
from services.bg_job_queue import job_queue
from services.bg_worker_manager import worker_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bg-jobs", tags=["background_jobs"])

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
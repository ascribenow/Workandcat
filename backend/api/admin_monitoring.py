"""
Admin Monitoring API - User & Job Status Dashboard
"""
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
import uuid

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text

from auth import get_current_user
from database import SessionLocal, get_database

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin_monitoring"])


class FixUserJobsRequest(BaseModel):
    user_id: str


def check_admin_access(user_id: str = Depends(get_current_user)) -> str:
    """Check if current user has admin access"""
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT is_admin FROM users WHERE id = :user_id
        """), {"user_id": user_id})
        
        user = result.fetchone()
        if not user or not user[0]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        return user_id
    finally:
        db.close()


@router.get("/users-monitoring")
async def get_users_monitoring(admin_user_id: str = Depends(check_admin_access)):
    """
    Get comprehensive monitoring data for all users
    Returns user info, session stats, job status, and pre-pack availability
    """
    try:
        db = SessionLocal()
        
        # Complex query to get all user data with stats
        result = db.execute(text("""
            WITH user_sessions AS (
                SELECT 
                    user_id,
                    COUNT(*) FILTER (WHERE status = 'completed') as sessions_completed,
                    MAX(created_at) FILTER (WHERE status = 'completed') as last_session_created,
                    MAX(session_id) FILTER (WHERE status IN ('active', 'planned')) as current_session_id
                FROM sessions
                GROUP BY user_id
            ),
            user_packs AS (
                SELECT 
                    sp.user_id,
                    COUNT(*) as available_packs
                FROM session_packs sp
                LEFT JOIN sessions s ON CAST(sp.session_id AS varchar) = CAST(s.session_id AS varchar)
                WHERE s.session_id IS NULL OR s.status IN ('planned', 'active')
                GROUP BY sp.user_id
            ),
            user_jobs AS (
                SELECT 
                    user_id,
                    COUNT(*) FILTER (WHERE status IN ('queued', 'running')) as jobs_enqueued,
                    COUNT(*) FILTER (WHERE status IN ('queued', 'failed') AND attempts >= max_attempts) as exhausted_jobs,
                    STRING_AGG(
                        DISTINCT CAST(job_type AS TEXT), ', '
                    ) FILTER (WHERE status IN ('queued', 'failed') AND attempts >= max_attempts) as failed_job_types
                FROM bg_jobs
                GROUP BY user_id
            )
            SELECT 
                u.id as user_id,
                u.email,
                u.full_name,
                COALESCE(us.sessions_completed, 0) as sessions_completed,
                us.last_session_created,
                us.current_session_id,
                COALESCE(up.available_packs, 0) > 0 as pre_pack_available,
                COALESCE(uj.jobs_enqueued, 0) as jobs_enqueued,
                COALESCE(uj.exhausted_jobs, 0) as exhausted_jobs,
                uj.failed_job_types
            FROM users u
            LEFT JOIN user_sessions us ON CAST(u.id AS varchar) = CAST(us.user_id AS varchar)
            LEFT JOIN user_packs up ON CAST(u.id AS varchar) = CAST(up.user_id AS varchar)
            LEFT JOIN user_jobs uj ON CAST(u.id AS varchar) = CAST(uj.user_id AS varchar)
            ORDER BY us.last_session_created DESC NULLS LAST, u.email ASC
        """))
        
        users = result.fetchall()
        
        # Format response
        users_data = []
        for user in users:
            users_data.append({
                "user_id": str(user[0]),
                "email": user[1],
                "name": user[2] or "N/A",
                "sessions_completed": int(user[3]),
                "last_session_created": user[4].isoformat() if user[4] else None,
                "current_session_id": str(user[5]) if user[5] else None,
                "pre_pack_available": bool(user[6]),
                "jobs_enqueued": int(user[7]),
                "exhausted_jobs": int(user[8]),
                "critical_issue": int(user[8]) > 0,  # Critical if any exhausted jobs
                "failed_job_type": user[9] if user[9] else None
            })
        
        db.close()
        
        logger.info(f"Admin monitoring data fetched: {len(users_data)} users")
        
        return JSONResponse({
            "success": True,
            "users": users_data,
            "total_count": len(users_data),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error fetching admin monitoring data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch monitoring data: {str(e)}")


@router.post("/fix-user-jobs")
async def fix_user_jobs(
    request: FixUserJobsRequest,
    admin_user_id: str = Depends(check_admin_access)
):
    """
    Fix exhausted jobs for a specific user:
    1. Delete all exhausted jobs (attempts >= max_attempts)
    2. Enqueue new PLAN_NEXT_SESSION job
    """
    try:
        user_id = request.user_id
        
        # Validate UUID format
        try:
            uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user_id format")
        
        db = SessionLocal()
        
        # Check if user exists
        user_check = db.execute(text("""
            SELECT email FROM users WHERE id = :user_id
        """), {"user_id": user_id})
        
        user = user_check.fetchone()
        if not user:
            db.close()
            raise HTTPException(status_code=404, detail="User not found")
        
        user_email = user[0]
        
        # Step 1: Find and delete exhausted jobs
        exhausted_result = db.execute(text("""
            DELETE FROM bg_jobs
            WHERE user_id = :user_id
            AND attempts >= max_attempts
            RETURNING id, job_type, attempts, max_attempts
        """), {"user_id": user_id})
        
        deleted_jobs = exhausted_result.fetchall()
        db.commit()
        
        logger.info(f"Deleted {len(deleted_jobs)} exhausted jobs for user {user_email}")
        
        # Step 2: Enqueue new PLAN_NEXT_SESSION job
        from services.bg_job_queue import job_queue
        import asyncio
        
        job_id = await job_queue.enqueue_job(
            job_type="PLAN_NEXT_SESSION",
            user_id=user_id,
            session_id=None,
            correlation_id=None,
            max_attempts=6
        )
        
        db.close()
        
        logger.info(f"Enqueued new PLAN_NEXT_SESSION job {job_id[:8]} for user {user_email}")
        
        return JSONResponse({
            "success": True,
            "message": f"Fixed jobs and triggered pack regeneration for {user_email}",
            "deleted_jobs_count": len(deleted_jobs),
            "new_job_id": job_id,
            "user_email": user_email
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fixing user jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fix user jobs: {str(e)}")


@router.get("/health")
async def admin_health(admin_user_id: str = Depends(check_admin_access)):
    """Health check for admin monitoring endpoints"""
    return JSONResponse({
        "status": "healthy",
        "service": "admin_monitoring",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

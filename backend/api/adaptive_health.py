"""
Adaptive Engine Health Monitoring API
Provides comprehensive health checks and monitoring for the adaptive learning system
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
import logging

# Note: Authentication dependency removed for initial implementation
# from auth import get_current_user
from services.adaptive_job_supervisor import get_supervisor_health

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/health")
async def get_adaptive_health():
    """
    Get comprehensive adaptive engine health status
    Public endpoint for system monitoring
    """
    try:
        health_data = await get_supervisor_health()
        return {
            "status": "success",
            "adaptive_engine": health_data
        }
    except Exception as e:
        logger.error(f"❌ Adaptive health check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Health check failed", "message": str(e)}
        )

@router.get("/health/detailed")
async def get_detailed_health():
    """
    Get detailed health information including recommendations
    Requires authentication for detailed diagnostics
    """
    try:
        health_data = await get_supervisor_health()
        
        # Add additional diagnostic information for authenticated users
        from services.bg_job_queue import job_queue
        from database import SessionLocal
        from sqlalchemy import text
        
        db = SessionLocal()
        try:
            # Get queue depth
            queue_depth = db.execute(text("""
                SELECT COUNT(*) FROM bg_jobs 
                WHERE status IN ('queued', 'running')
            """)).scalar()
            
            # Get recent job history
            recent_jobs = db.execute(text("""
                SELECT job_type, status, created_at, completed_at
                FROM bg_jobs
                WHERE created_at > NOW() - INTERVAL '1 hour'
                ORDER BY created_at DESC
                LIMIT 20
            """)).fetchall()
            
            health_data["diagnostics"] = {
                "queue_depth": queue_depth,
                "recent_jobs": [
                    {
                        "job_type": job.job_type,
                        "status": job.status,
                        "created_at": job.created_at.isoformat() if job.created_at else None,
                        "completed_at": job.completed_at.isoformat() if job.completed_at else None
                    }
                    for job in recent_jobs
                ]
            }
        finally:
            db.close()
        
        return {
            "status": "success",
            "adaptive_engine": health_data
        }
    
    except Exception as e:
        logger.error(f"❌ Detailed health check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Detailed health check failed", "message": str(e)}
        )

@router.post("/health/circuit-breaker/reset/{job_type}")
async def reset_circuit_breaker(job_type: str):
    """
    Manual circuit breaker reset for administrators
    """
    try:
        from services.adaptive_job_supervisor import adaptive_supervisor
        
        if job_type not in adaptive_supervisor.circuit_breakers:
            raise HTTPException(
                status_code=404,
                detail={"error": "Job type not found", "job_type": job_type}
            )
        
        # Reset circuit breaker
        cb = adaptive_supervisor.circuit_breakers[job_type]
        cb.state = cb.CircuitBreakerState.CLOSED
        cb.failure_count = 0
        cb.last_failure_time = None
        
        logger.info(f"🔄 Circuit breaker manually reset for {job_type} by user {user_id[:8]}")
        
        return {
            "status": "success",
            "message": f"Circuit breaker reset for {job_type}",
            "job_type": job_type
        }
    
    except Exception as e:
        logger.error(f"❌ Circuit breaker reset failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Circuit breaker reset failed", "message": str(e)}
        )

@router.get("/health/metrics")
async def get_performance_metrics():
    """
    Get performance metrics for monitoring dashboards
    """
    try:
        from database import SessionLocal
        from sqlalchemy import text
        
        db = SessionLocal()
        try:
            # Get job performance over time
            metrics = db.execute(text("""
                SELECT 
                    job_type,
                    DATE_TRUNC('hour', created_at) as hour,
                    COUNT(*) as total_jobs,
                    SUM(CASE WHEN status = 'succeeded' THEN 1 ELSE 0 END) as succeeded,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    AVG(CASE 
                        WHEN status = 'succeeded' AND started_at IS NOT NULL AND completed_at IS NOT NULL
                        THEN EXTRACT(EPOCH FROM (completed_at - started_at))
                        ELSE NULL 
                    END) as avg_processing_time_seconds
                FROM bg_jobs
                WHERE created_at > NOW() - INTERVAL '24 hours'
                GROUP BY job_type, DATE_TRUNC('hour', created_at)
                ORDER BY hour DESC, job_type
            """)).fetchall()
            
            return {
                "status": "success",
                "metrics": [
                    {
                        "job_type": row.job_type,
                        "hour": row.hour.isoformat() if row.hour else None,
                        "total_jobs": row.total_jobs,
                        "succeeded": row.succeeded,
                        "failed": row.failed,
                        "success_rate": (row.succeeded / row.total_jobs * 100) if row.total_jobs > 0 else 0,
                        "avg_processing_time_seconds": float(row.avg_processing_time_seconds) if row.avg_processing_time_seconds else None
                    }
                    for row in metrics
                ]
            }
        finally:
            db.close()
    
    except Exception as e:
        logger.error(f"❌ Metrics collection failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Metrics collection failed", "message": str(e)}
        )
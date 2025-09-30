"""
Enhanced health monitoring with root cause context
Replaces manual log tailing and psql queries with API-driven observability
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from sqlalchemy import text
from database import SessionLocal

router = APIRouter(prefix="/api/admin", tags=["health"])


@router.get("/pipeline-health")
async def get_pipeline_health() -> Dict[str, Any]:
    """
    Complete pipeline health with root cause context
    
    Replaces: Manual log tailing, psql queries
    
    Returns:
        - Overall health status (healthy/degraded/critical)
        - Real-time metrics (completion rate, job success rate, orphaned sessions)
        - Root cause context (top failing job types with error samples)
        - Active alerts (with persistence filtering)
    """
    db = SessionLocal()
    
    try:
        # Refresh metrics
        db.execute(text("SELECT update_pipeline_health_metrics()"))
        db.commit()
        
        # Fetch metrics
        metrics_result = db.execute(text("""
            SELECT metric_name, metric_value, metric_type, last_updated
            FROM pipeline_health_metrics
            ORDER BY metric_name
        """)).fetchall()
        
        metrics = {}
        for name, value, mtype, updated in metrics_result:
            metrics[name] = {
                "value": float(value) if value else 0,
                "type": mtype,
                "last_updated": updated.isoformat() if updated else None
            }
        
        # Get root cause context (top 3 failing job types)
        failing_jobs = db.execute(text("""
            SELECT 
                job_type,
                failure_count,
                affected_users,
                error_samples,
                first_failure,
                last_failure
            FROM mv_failing_job_types_30m
            LIMIT 3
        """)).fetchall()
        
        root_cause = []
        for jtype, count, users, errors, first, last in failing_jobs:
            root_cause.append({
                "job_type": jtype,
                "failure_count": count,
                "affected_users": users,
                "sample_errors": errors[:3] if errors else [],
                "time_range": {
                    "first": first.isoformat() if first else None,
                    "last": last.isoformat() if last else None
                }
            })
        
        # Get active alerts (with persistence filtering)
        alerts = db.execute(text("""
            SELECT alert_name, alert_level, first_seen, occurrences, context
            FROM pipeline_alerts
            WHERE is_active = TRUE
            AND (
                occurrences >= 3 
                OR EXTRACT(EPOCH FROM (NOW() - first_seen))/60 >= 15
            )
            ORDER BY 
                CASE alert_level 
                    WHEN 'critical' THEN 1 
                    WHEN 'warning' THEN 2 
                    ELSE 3 
                END,
                first_seen DESC
        """)).fetchall()
        
        alerts_list = []
        for name, level, first, occ, ctx in alerts:
            alerts_list.append({
                "name": name,
                "level": level,
                "first_seen": first.isoformat() if first else None,
                "occurrences": occ,
                "context": ctx if ctx else {}
            })
        
        # Calculate overall health status
        health_status = "healthy"
        
        # Check for critical conditions
        if any(a["level"] == "critical" for a in alerts_list):
            health_status = "critical"
        elif any(a["level"] == "warning" for a in alerts_list):
            health_status = "degraded"
        elif metrics.get("summary_completion_rate", {}).get("value", 100) < 80:
            health_status = "degraded"
        elif metrics.get("job_success_rate_24h", {}).get("value", 100) < 90:
            health_status = "degraded"
        elif metrics.get("orphaned_sessions_count", {}).get("value", 0) > 20:
            health_status = "degraded"
        
        return {
            "status": health_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics,
            "root_cause_context": {
                "top_failing_job_types": root_cause,
                "window": "last 30 minutes"
            },
            "alerts": alerts_list
        }
        
    except Exception as e:
        raise HTTPException(500, f"Error fetching pipeline health: {e}")
    finally:
        db.close()


@router.get("/pipeline-health/trace/{correlation_id}")
async def trace_pipeline(correlation_id: str):
    """
    Trace complete pipeline for a session
    Shows: SUMMARIZE → PLAN sequence with timing and status
    
    Args:
        correlation_id: UUID that ties together all jobs in a pipeline
        
    Returns:
        Complete pipeline trace with status, duration, and errors
    """
    db = SessionLocal()
    
    try:
        # Get all jobs for this correlation_id
        jobs = db.execute(text("""
            SELECT 
                id, job_type, status, created_at, started_at, completed_at,
                EXTRACT(EPOCH FROM (completed_at - started_at)) as duration_sec,
                error_message
            FROM bg_jobs
            WHERE correlation_id = :correlation_id
            ORDER BY created_at
        """), {"correlation_id": correlation_id}).fetchall()
        
        if not jobs:
            raise HTTPException(404, "No jobs found for this correlation_id")
        
        pipeline = []
        for job_id, jtype, status, created, started, completed, duration, error in jobs:
            pipeline.append({
                "job_id": str(job_id)[:8] + "...",
                "job_type": jtype,
                "status": status,
                "created_at": created.isoformat() if created else None,
                "started_at": started.isoformat() if started else None,
                "completed_at": completed.isoformat() if completed else None,
                "duration_seconds": round(float(duration), 2) if duration else None,
                "error": error[:200] if error else None
            })
        
        # Get session info if available
        session_info = db.execute(text("""
            SELECT session_id, user_id, status, created_at
            FROM sessions
            WHERE correlation_id = :correlation_id
            LIMIT 1
        """), {"correlation_id": correlation_id}).fetchone()
        
        session_data = None
        if session_info:
            session_data = {
                "session_id": str(session_info[0]),
                "user_id": str(session_info[1])[:8] + "...",
                "status": session_info[2],
                "created_at": session_info[3].isoformat() if session_info[3] else None
            }
        
        return {
            "correlation_id": correlation_id,
            "session": session_data,
            "pipeline": pipeline,
            "all_succeeded": all(j["status"] == "succeeded" for j in pipeline),
            "total_jobs": len(pipeline)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error tracing pipeline: {e}")
    finally:
        db.close()


@router.post("/pipeline-health/refresh")
async def refresh_health_metrics():
    """
    Manually refresh health metrics
    
    Replaces: Cron job
    Can be called periodically by Emergent scheduler or on-demand
    """
    db = SessionLocal()
    
    try:
        db.execute(text("SELECT update_pipeline_health_metrics()"))
        db.commit()
        
        return {
            "status": "success",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "message": "Health metrics refreshed successfully"
        }
        
    except Exception as e:
        raise HTTPException(500, f"Error refreshing metrics: {e}")
    finally:
        db.close()


@router.get("/pipeline-health/config-versions")
async def get_config_versions():
    """
    Check for mixed config versions across tables
    
    Useful for detecting deployment issues where different parts
    of the system are running different configurations
    """
    db = SessionLocal()
    
    try:
        # Check for mixed config versions (if config_version column exists)
        # This is a placeholder for when Phase 4 configuration management is implemented
        
        return {
            "status": "not_implemented",
            "message": "Configuration version tracking will be implemented in Phase 4"
        }
        
    except Exception as e:
        raise HTTPException(500, f"Error checking config versions: {e}")
    finally:
        db.close()

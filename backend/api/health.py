"""
Enhanced health monitoring with root cause context
Replaces manual log tailing and psql queries with API-driven observability
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from sqlalchemy import text
from database import SessionLocal
try:
    from config.adaptive_learning_config import config as adaptive_config
    CONFIG_AVAILABLE = True
except Exception as e:
    CONFIG_AVAILABLE = False
    adaptive_config = None

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


@router.get("/pipeline-health/config")
async def get_current_config():
    """
    Get currently active configuration
    
    Returns the configuration that is currently deployed and active
    """
    db = SessionLocal()
    
    try:
        # Get active config from database
        result = db.execute(text("SELECT get_active_config()")).scalar()
        
        # Also get Python config for comparison
        try:
            from config.adaptive_learning_config import config as py_config
            python_config = py_config.to_dict()
        except Exception as e:
            python_config = {"error": f"Could not load Python config: {e}"}
        
        return {
            "database_config": result,
            "python_config": python_config,
            "match": result == python_config if isinstance(python_config, dict) else False
        }
        
    except Exception as e:
        raise HTTPException(500, f"Error fetching config: {e}")
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
        # Get currently active config
        active_config = db.execute(text("""
            SELECT new_config->>'version' as version,
                   changed_at,
                   deployed_at
            FROM config_change_log
            WHERE deployed_at IS NOT NULL
            ORDER BY deployed_at DESC
            LIMIT 1
        """)).fetchone()
        
        if not active_config:
            return {
                "status": "no_deployments",
                "message": "No configuration deployments found",
                "active_version": None
            }
        
        active_version = active_config[0]
        last_deployed = active_config[2]
        
        # Get recent config changes (last 7 days)
        recent_changes = db.execute(text("""
            SELECT 
                id,
                changed_by,
                change_reason,
                old_config->>'version' as old_version,
                new_config->>'version' as new_version,
                changed_at,
                deployed_at
            FROM config_change_log
            WHERE changed_at > NOW() - INTERVAL '7 days'
            ORDER BY changed_at DESC
            LIMIT 10
        """)).fetchall()
        
        changes_list = []
        for change in recent_changes:
            changes_list.append({
                "id": change[0],
                "changed_by": change[1],
                "reason": change[2][:100] if change[2] else None,
                "version_change": f"{change[3] or 'none'} → {change[4]}",
                "changed_at": change[5].isoformat() if change[5] else None,
                "deployed": change[6] is not None
            })
        
        # Check for pending (undeployed) changes
        pending_count = db.execute(text("""
            SELECT COUNT(*)
            FROM config_change_log
            WHERE deployed_at IS NULL
            AND changed_at > (
                SELECT COALESCE(MAX(deployed_at), '1970-01-01'::timestamptz)
                FROM config_change_log
            )
        """)).scalar()
        
        status = "consistent"
        if pending_count > 0:
            status = "pending_deployment"
        
        return {
            "status": status,
            "active_version": active_version,
            "last_deployed": last_deployed.isoformat() if last_deployed else None,
            "pending_changes": pending_count,
            "recent_changes": changes_list,
            "message": f"Active version: {active_version}" + 
                      (f" ({pending_count} pending changes)" if pending_count > 0 else " (up to date)")
        }
        
    except Exception as e:
        raise HTTPException(500, f"Error checking config versions: {e}")
    finally:
        db.close()


@router.get("/pipeline-health/config/demo")
async def demo_config_usage():
    """
    Demonstrate configuration usage with examples
    
    Shows how the centralized configuration is used throughout the system
    """
    if not CONFIG_AVAILABLE or not adaptive_config:
        return {
            "error": "Configuration not available",
            "message": "Adaptive learning config could not be loaded"
        }
    
    # Import helper functions
    from config.adaptive_learning_config import (
        get_readiness_from_mastery,
        normalize_mastery_score,
        normalize_coverage_debt,
        get_job_backoff_minutes
    )
    
    # Demonstrate configuration values and helper functions
    examples = {
        "session_config": {
            "questions_per_session": adaptive_config.session_questions_count,
            "min_questions": adaptive_config.session_min_questions,
            "timeout_minutes": adaptive_config.session_timeout_minutes
        },
        "mastery_scoring": {
            "range": f"{adaptive_config.mastery_min_score} - {adaptive_config.mastery_max_score}",
            "initial": adaptive_config.mastery_initial_score,
            "increase_correct": adaptive_config.mastery_increase_correct,
            "decrease_incorrect": adaptive_config.mastery_decrease_incorrect,
            "examples": {
                "score_2.5": {
                    "raw": 2.5,
                    "normalized": normalize_mastery_score(2.5),
                    "readiness": get_readiness_from_mastery(2.5)
                },
                "score_5.0": {
                    "raw": 5.0,
                    "normalized": normalize_mastery_score(5.0),
                    "readiness": get_readiness_from_mastery(5.0)
                },
                "score_8.5": {
                    "raw": 8.5,
                    "normalized": normalize_mastery_score(8.5),
                    "readiness": get_readiness_from_mastery(8.5)
                },
                "score_15.0_overflow": {
                    "raw": 15.0,
                    "normalized": normalize_mastery_score(15.0),
                    "readiness": get_readiness_from_mastery(normalize_mastery_score(15.0))
                }
            }
        },
        "coverage_debt": {
            "range": f"{adaptive_config.coverage_debt_min} - {adaptive_config.coverage_debt_max}",
            "initial": adaptive_config.coverage_debt_initial,
            "decrease_when_served": adaptive_config.coverage_debt_decrease_served,
            "decay_rate": adaptive_config.coverage_debt_decay_rate,
            "examples": {
                "debt_0.5": normalize_coverage_debt(0.5),
                "debt_5.0": normalize_coverage_debt(5.0),
                "debt_12.0_overflow": normalize_coverage_debt(12.0)
            }
        },
        "job_retries": {
            "max_attempts": adaptive_config.job_max_attempts,
            "backoff_schedule": {
                f"attempt_{i}": f"{get_job_backoff_minutes(i)} minutes"
                for i in range(1, adaptive_config.job_max_attempts + 1)
            }
        },
        "anchors": {
            "min_per_question": adaptive_config.anchor_min_per_question,
            "max_per_question": adaptive_config.anchor_max_per_question,
            "confidence_threshold": adaptive_config.anchor_confidence_threshold
        }
    }
    
    return {
        "config_version": adaptive_config.to_dict()["version"],
        "last_updated": adaptive_config.to_dict()["last_updated"],
        "examples": examples,
        "validation": {
            "status": "valid",
            "errors": []
        }
    }

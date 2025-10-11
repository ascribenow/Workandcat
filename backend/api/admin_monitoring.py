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
async def fix_user_jobs(request: FixUserJobsRequest, admin_user_id: str = Depends(check_admin_access)):
    """
    Comprehensive fix for stuck jobs and empty packs
    
    Actions performed:
    1. Delete exhausted jobs (attempts >= max_attempts)
    2. Check for sessions with empty packs and regenerate them
    3. Cancel stuck jobs in 'running' state for > 10 minutes
    4. Enqueue new PLAN_NEXT_SESSION if no valid pack exists
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
        actions_taken = []
        
        # Step 1: Find and delete exhausted jobs
        exhausted_result = db.execute(text("""
            DELETE FROM bg_jobs
            WHERE user_id = :user_id
            AND attempts >= max_attempts
            RETURNING id, job_type, attempts, max_attempts
        """), {"user_id": user_id})
        
        deleted_jobs = exhausted_result.fetchall()
        db.commit()
        
        if deleted_jobs:
            actions_taken.append(f"Deleted {len(deleted_jobs)} exhausted jobs")
            logger.info(f"Deleted {len(deleted_jobs)} exhausted jobs for user {user_email}")
        
        # Step 2: Cancel stuck jobs (running for > 10 minutes)
        from datetime import datetime, timezone, timedelta
        ten_min_ago = datetime.now(timezone.utc) - timedelta(minutes=10)
        
        stuck_result = db.execute(text("""
            UPDATE bg_jobs
            SET status = 'failed',
                error_message = 'Auto-cancelled: stuck in running state for > 10 minutes'
            WHERE user_id = :user_id
            AND status = 'running'
            AND started_at < :ten_min_ago
            RETURNING id, job_type
        """), {"user_id": user_id, "ten_min_ago": ten_min_ago})
        
        stuck_jobs = stuck_result.fetchall()
        db.commit()
        
        if stuck_jobs:
            actions_taken.append(f"Cancelled {len(stuck_jobs)} stuck jobs")
            logger.info(f"Cancelled {len(stuck_jobs)} stuck jobs for user {user_email}")
        
        # Step 3: Check for sessions with empty packs and fix them
        empty_sessions_result = db.execute(text("""
            SELECT s.session_id, s.sess_seq
            FROM sessions s
            WHERE s.user_id = :user_id
            AND s.status IN ('planned', 'active')
            AND NOT EXISTS (
                SELECT 1 FROM session_pack_questions spq
                WHERE spq.session_id::text = s.session_id::text
            )
            ORDER BY s.sess_seq DESC
            LIMIT 5
        """), {"user_id": user_id})
        
        empty_sessions = empty_sessions_result.fetchall()
        
        if empty_sessions:
            actions_taken.append(f"Found {len(empty_sessions)} sessions with empty packs")
            logger.info(f"Found {len(empty_sessions)} sessions with empty packs for user {user_email}")
            
            # Import the fix script function
            import sys
            sys.path.insert(0, '/app/backend')
            from services.simplified_job_handlers import gather_user_learning_data, generate_personalized_session_pack
            import json
            from utils.timezone_utils import now_ist
            
            for session in empty_sessions:
                session_id = str(session[0])
                sess_seq = session[1]
                
                try:
                    # Close existing db connection before async operations
                    db.close()
                    
                    # Generate pack for this specific session
                    learning_data = await gather_user_learning_data(user_id)
                    session_pack = await generate_personalized_session_pack(user_id, learning_data)
                    
                    # Reopen db connection for inserts
                    db = SessionLocal()
                    
                    # Insert into session_packs
                    constraint_report = json.dumps({
                        "pack_type": session_pack["pack_type"],
                        "difficulty_distribution": session_pack["difficulty_distribution"],
                        "planning_strategy": session_pack["planning_strategy"],
                        "weak_concepts_targeted": session_pack["weak_concepts_targeted"],
                        "high_debt_pairs_addressed": session_pack["high_debt_pairs_addressed"]
                    })
                    
                    db.execute(text("""
                        INSERT INTO session_packs (
                            session_id, user_id, constraint_report, created_at
                        ) VALUES (
                            CAST(:session_id AS uuid), CAST(:user_id AS uuid), CAST(:constraint_report AS jsonb), :created_at
                        )
                        ON CONFLICT (session_id) DO UPDATE 
                        SET constraint_report = CAST(:constraint_report AS jsonb), created_at = :created_at
                    """), {
                        "session_id": session_id,
                        "user_id": user_id,
                        "constraint_report": constraint_report,
                        "created_at": now_ist()
                    })
                    
                    # Insert questions
                    questions = session_pack.get("questions", [])
                    for question in questions:
                        core_concepts = question.get("core_concepts", [])
                        if isinstance(core_concepts, str):
                            core_concepts = json.loads(core_concepts)
                        elif not isinstance(core_concepts, list):
                            core_concepts = list(core_concepts) if core_concepts else []
                        
                        question_data_json = json.dumps({
                            "id": question["id"],
                            "stem": question["stem"],
                            "answer": question["answer"],
                            "explanation": question.get("explanation", ""),
                            "option_a": question.get("option_a", ""),
                            "option_b": question.get("option_b", ""),
                            "option_c": question.get("option_c", ""),
                            "option_d": question.get("option_d", ""),
                            "difficulty_band": question["difficulty_band"],
                            "subcategory": question["subcategory"],
                            "type_of_question": question["type_of_question"],
                            "core_concepts": core_concepts,
                            "pyq_frequency_score": question.get("pyq_frequency_score", 0),
                            "snap_read": question.get("snap_read", ""),
                            "solution_approach": question.get("solution_approach", ""),
                            "detailed_solution": question.get("detailed_solution", ""),
                            "principle_to_remember": question.get("principle_to_remember", "")
                        })
                        
                        db.execute(text("""
                            INSERT INTO session_pack_questions (
                                session_id, position, question_id, question_data
                            ) VALUES (
                                CAST(:session_id AS uuid), :position, CAST(:question_id AS uuid), CAST(:question_data AS jsonb)
                            )
                            ON CONFLICT (session_id, position) DO UPDATE
                            SET question_data = CAST(:question_data AS jsonb)
                        """), {
                            "session_id": session_id,
                            "position": question["position"],
                            "question_id": question["id"],
                            "question_data": question_data_json
                        })
                    
                    db.commit()
                    actions_taken.append(f"Regenerated pack for Session #{sess_seq} ({len(questions)} questions)")
                    logger.info(f"Regenerated pack for session {session_id[:8]} (Session #{sess_seq})")
                    
                except Exception as pack_error:
                    logger.error(f"Failed to regenerate pack for session {session_id[:8]}: {pack_error}")
                    actions_taken.append(f"Failed to regenerate pack for Session #{sess_seq}: {str(pack_error)[:50]}")
        
        # Step 4: Check if user needs a new pack (no planned/active sessions with valid packs)
        has_valid_pack = db.execute(text("""
            SELECT EXISTS (
                SELECT 1 
                FROM sessions s
                JOIN session_pack_questions spq ON s.session_id::text = spq.session_id::text
                WHERE s.user_id = :user_id
                AND s.status IN ('planned', 'active')
                GROUP BY s.session_id
                HAVING COUNT(spq.position) >= 12
            )
        """), {"user_id": user_id}).scalar()
        
        job_id = None
        if not has_valid_pack:
            # Enqueue new PLAN_NEXT_SESSION job
            from services.bg_job_queue import job_queue
            
            job_id = await job_queue.enqueue_job(
                job_type="PLAN_NEXT_SESSION",
                user_id=user_id,
                session_id=None,
                correlation_id=None,
                max_attempts=6
            )
            
            actions_taken.append("Enqueued new PLAN_NEXT_SESSION job")
            logger.info(f"Enqueued new PLAN_NEXT_SESSION job {job_id[:8]} for user {user_email}")
        else:
            actions_taken.append("Valid pack already exists, no new job needed")
        
        try:
            db.close()
        except:
            pass  # db might already be closed
        
        return JSONResponse({
            "success": True,
            "message": f"Fixed user {user_email}",
            "actions_taken": actions_taken,
            "deleted_jobs_count": len(deleted_jobs),
            "stuck_jobs_cancelled": len(stuck_jobs) if stuck_jobs else 0,
            "empty_sessions_fixed": len(empty_sessions) if empty_sessions else 0,
            "new_job_id": job_id,
            "user_email": user_email
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fixing user jobs: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fix user jobs: {str(e)}")


@router.get("/health")
async def admin_health(admin_user_id: str = Depends(check_admin_access)):
    """Health check for admin monitoring endpoints"""
    return JSONResponse({
        "status": "healthy",
        "service": "admin_monitoring",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

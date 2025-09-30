"""
Admin task endpoints for operational tasks
Replaces manual scripts with API-driven operations
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict
import asyncio
import uuid
from datetime import datetime, timezone

from services.bg_job_queue import job_queue
from database import SessionLocal
from sqlalchemy import text

router = APIRouter(prefix="/api/admin/tasks", tags=["admin-tasks"])


class BackfillRequest(BaseModel):
    batch_size: int = 10
    per_user_limit: int = 3
    delay_seconds: float = 2.0
    dry_run: bool = False


class BackfillStatus(BaseModel):
    batch_id: str
    status: str
    sessions_found: int
    jobs_enqueued: int
    jobs_failed: int
    sessions_skipped: int
    started_at: datetime
    completed_at: Optional[datetime] = None


class BackfillManager:
    """Production-grade backfill with safety features"""
    
    def __init__(self, request: BackfillRequest):
        self.request = request
        self.batch_id = str(uuid.uuid4())
        self.started_at = datetime.now(timezone.utc)
        self.stats = {
            "found": 0,
            "enqueued": 0,
            "failed": 0,
            "skipped": 0
        }
    
    def find_orphaned_sessions_with_fairness(self) -> List[tuple]:
        """Find orphaned sessions with per-user fairness"""
        db = SessionLocal()
        
        all_orphaned = db.execute(text("""
            SELECT 
                s.session_id, 
                s.user_id,
                s.created_at,
                s.questions_answered,
                s.questions_correct
            FROM sessions s
            WHERE s.status = 'completed'
            AND NOT EXISTS (
                SELECT 1 FROM session_summary_final ssf 
                WHERE ssf.session_id = s.session_id::varchar
            )
            ORDER BY s.created_at ASC
        """)).fetchall()
        
        self.stats["found"] = len(all_orphaned)
        
        if not all_orphaned:
            return []
        
        # Apply per-user fairness
        user_counts = {}
        selected = []
        
        for session in all_orphaned:
            session_id, user_id, created_at, answered, correct = session
            user_id_str = str(user_id)
            
            if user_counts.get(user_id_str, 0) >= self.request.per_user_limit:
                self.stats["skipped"] += 1
                continue
            
            selected.append(session)
            user_counts[user_id_str] = user_counts.get(user_id_str, 0) + 1
            
            if len(selected) >= self.request.batch_size:
                break
        
        return selected
    
    async def execute_backfill(self) -> Dict:
        """Execute backfill with provenance tracking"""
        
        # Log start
        db = SessionLocal()
        try:
            db.execute(text("""
                INSERT INTO backfill_audit_log (
                    batch_id, started_at, batch_size, per_user_limit, status
                ) VALUES (:batch_id, :started_at, :batch_size, :per_user_limit, 'running')
            """), {
                "batch_id": self.batch_id,
                "started_at": self.started_at,
                "batch_size": self.request.batch_size,
                "per_user_limit": self.request.per_user_limit
            })
            db.commit()
        except Exception as e:
            # Table might not exist yet, continue anyway
            print(f"Warning: Could not log to backfill_audit_log: {e}")
        
        # Find sessions
        sessions = self.find_orphaned_sessions_with_fairness()
        
        if not sessions:
            try:
                db.execute(text("""
                    UPDATE backfill_audit_log 
                    SET status = 'completed', completed_at = NOW()
                    WHERE batch_id = :batch_id
                """), {"batch_id": self.batch_id})
                db.commit()
            except:
                pass
            
            return {
                "batch_id": self.batch_id,
                "message": "No orphaned sessions found",
                "stats": self.stats
            }
        
        if self.request.dry_run:
            return {
                "batch_id": self.batch_id,
                "message": "DRY RUN - No jobs enqueued",
                "would_process": len(sessions),
                "stats": self.stats
            }
        
        # Enqueue jobs
        for session_id, user_id, created_at, answered, correct in sessions:
            try:
                await job_queue.enqueue_job(
                    job_type="SUMMARIZE_SESSION",
                    user_id=str(user_id),
                    session_id=str(session_id),
                    metadata={
                        "backfill_batch_id": self.batch_id,
                        "backfill_started_at": self.started_at.isoformat(),
                        "source": "backfill_api"
                    }
                )
                self.stats["enqueued"] += 1
            except Exception as e:
                self.stats["failed"] += 1
                print(f"Failed to enqueue {session_id}: {e}")
            
            await asyncio.sleep(self.request.delay_seconds)
        
        # Log completion
        try:
            db.execute(text("""
                UPDATE backfill_audit_log 
                SET 
                    status = 'completed',
                    completed_at = NOW(),
                    sessions_found = :found,
                    jobs_enqueued = :enqueued,
                    jobs_failed = :failed,
                    sessions_skipped = :skipped
                WHERE batch_id = :batch_id
            """), {
                "batch_id": self.batch_id,
                "found": self.stats["found"],
                "enqueued": self.stats["enqueued"],
                "failed": self.stats["failed"],
                "skipped": self.stats["skipped"]
            })
            db.commit()
        except:
            pass
        
        return {
            "batch_id": self.batch_id,
            "message": "Backfill completed",
            "stats": self.stats
        }


@router.post("/backfill", response_model=Dict)
async def trigger_backfill(
    request: BackfillRequest,
    background_tasks: BackgroundTasks
):
    """
    Trigger backfill of orphaned sessions
    
    Replaces: python3 backend/scripts/backfill_session_summaries.py
    
    Usage:
        POST /api/admin/tasks/backfill
        {
            "batch_size": 10,
            "per_user_limit": 3,
            "dry_run": true
        }
    """
    manager = BackfillManager(request)
    
    if request.dry_run:
        # Execute synchronously for dry run
        result = await manager.execute_backfill()
        return result
    else:
        # Execute in background for real run
        background_tasks.add_task(manager.execute_backfill)
        
        return {
            "batch_id": manager.batch_id,
            "message": "Backfill started in background",
            "status_endpoint": f"/api/admin/tasks/backfill/{manager.batch_id}"
        }


@router.get("/backfill/{batch_id}", response_model=Dict)
async def get_backfill_status(batch_id: str):
    """Get status of a backfill batch"""
    db = get_db_session()
    
    try:
        result = db.execute(text("""
            SELECT 
                batch_id, status, sessions_found, jobs_enqueued,
                jobs_failed, sessions_skipped, started_at, completed_at
            FROM backfill_audit_log
            WHERE batch_id = :batch_id
        """), {"batch_id": batch_id}).fetchone()
        
        if not result:
            raise HTTPException(404, "Backfill batch not found")
        
        return {
            "batch_id": result[0],
            "status": result[1],
            "sessions_found": result[2] or 0,
            "jobs_enqueued": result[3] or 0,
            "jobs_failed": result[4] or 0,
            "sessions_skipped": result[5] or 0,
            "started_at": result[6].isoformat() if result[6] else None,
            "completed_at": result[7].isoformat() if result[7] else None
        }
    except Exception as e:
        raise HTTPException(500, f"Error fetching backfill status: {e}")


@router.get("/backfill-history", response_model=List[Dict])
async def get_backfill_history(limit: int = 10):
    """Get recent backfill history"""
    db = get_db_session()
    
    try:
        results = db.execute(text("""
            SELECT 
                batch_id, status, sessions_found, jobs_enqueued,
                jobs_failed, sessions_skipped, started_at, completed_at
            FROM backfill_audit_log
            ORDER BY started_at DESC
            LIMIT :limit
        """), {"limit": limit}).fetchall()
        
        return [
            {
                "batch_id": r[0],
                "status": r[1],
                "sessions_found": r[2] or 0,
                "jobs_enqueued": r[3] or 0,
                "jobs_failed": r[4] or 0,
                "sessions_skipped": r[5] or 0,
                "started_at": r[6].isoformat() if r[6] else None,
                "completed_at": r[7].isoformat() if r[7] else None
            }
            for r in results
        ]
    except Exception as e:
        return []


@router.get("/validate-schema")
async def validate_schema():
    """Verify database schema constraints are in place"""
    db = get_db_session()
    
    try:
        constraints = db.execute(text("""
            SELECT 
                conrelid::regclass as table_name,
                conname as constraint_name
            FROM pg_constraint
            WHERE conname LIKE '%uuid_format%'
            ORDER BY table_name
        """)).fetchall()
        
        return {
            "uuid_constraints": [
                {"table": str(c[0]), "constraint": c[1]}
                for c in constraints
            ],
            "total": len(constraints),
            "expected": 5
        }
    except Exception as e:
        return {
            "error": str(e),
            "uuid_constraints": [],
            "total": 0
        }


@router.get("/validate-foreign-keys")
async def validate_foreign_keys():
    """Verify foreign key constraints are validated"""
    db = get_db_session()
    
    try:
        fks = db.execute(text("""
            SELECT 
                conrelid::regclass as table_name,
                conname as constraint_name,
                confrelid::regclass as references_table,
                convalidated as is_validated
            FROM pg_constraint
            WHERE contype = 'f'
            AND conrelid::regclass::text IN (
                'session_summary_final',
                'concept_alias_map_latest'
            )
        """)).fetchall()
        
        return {
            "foreign_keys": [
                {
                    "table": str(fk[0]),
                    "constraint": fk[1],
                    "references": str(fk[2]),
                    "validated": fk[3]
                }
                for fk in fks
            ],
            "all_validated": all(fk[3] for fk in fks) if fks else False
        }
    except Exception as e:
        return {
            "error": str(e),
            "foreign_keys": [],
            "all_validated": False
        }

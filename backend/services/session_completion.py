"""
Session Completion Handler
Handles session completion events and updates timestamps
Includes post-session summarizer integration
"""

import logging
from datetime import datetime, timezone
from database import SessionLocal
from sqlalchemy import text
from services.summarizer import run_summarizer
from services.telemetry import telemetry_service

logger = logging.getLogger(__name__)

def utcnow():
    return datetime.now(timezone.utc)

def mark_session_started(user_id: str, session_id: str) -> bool:
    """
    Mark a session as started - idempotent served_at timestamp
    
    Args:
        user_id: User identifier 
        session_id: Session identifier
        
    Returns:
        True if update successful
    """
    db = SessionLocal()
    try:
        # Idempotent: only set if NULL
        result = db.execute(text("""
            UPDATE sessions 
            SET served_at = COALESCE(served_at, :served_at),
                status = CASE 
                    WHEN served_at IS NULL THEN 'served'
                    ELSE status 
                END
            WHERE session_id = :session_id AND user_id = :user_id
            RETURNING session_id
        """), {
            'user_id': user_id,
            'session_id': session_id,
            'served_at': datetime.utcnow()
        })
        
        updated = result.fetchone()
        if updated:
            db.commit()
            logger.info(f"✅ Session {session_id[:8]} marked as started for user {user_id[:8]}")
            if hasattr(telemetry_service, 'emit'):
                telemetry_service.emit("session_mark_started", {
                    "user_id": user_id, 
                    "session_id": session_id
                })
            return True
        else:
            logger.warning(f"⚠️ Session start failed - session not found")
            return False
            
    except Exception as e:
        db.rollback() 
        logger.error(f"Error marking session started {user_id}/{session_id}: {e}")
        return False
    finally:
        db.close()

def mark_session_completed(user_id: str, session_id: str) -> bool:
    """
    Mark a session as completed and trigger post-session analysis
    
    Args:
        user_id: User identifier
        session_id: Session identifier
        
    Returns:
        True if update successful
    """
    db = SessionLocal()
    try:
        # Idempotent completion stamp for sessions table with server-side timestamp
        result = db.execute(text("""
            UPDATE sessions
            SET completed_at = COALESCE(completed_at, NOW()),
                status = CASE 
                    WHEN completed_at IS NULL THEN 'completed'
                    ELSE status 
                END
            WHERE user_id = :user_id AND session_id = :session_id
            RETURNING session_id
        """), {
            'user_id': user_id,
            'session_id': session_id
        })
        
        session_updated = result.fetchone()

        # Idempotent completion stamp for session_pack_plan
        result = db.execute(text("""
            UPDATE session_pack_plan 
            SET completed_at = COALESCE(completed_at, :completed_at)
            WHERE user_id = :user_id AND session_id = :session_id 
            AND status = 'served'
            RETURNING user_id
        """), {
            'user_id': user_id,
            'session_id': session_id,
            'completed_at': datetime.utcnow()
        })
        
        pack_updated = result.fetchone()
        
        if session_updated or pack_updated:
            db.commit()
            logger.info(f"✅ Session {session_id[:8]} marked as completed for user {user_id[:8]}")
            
            # Post-session summarizer (non-fatal)
            try:
                logger.info(f"📊 Running post-completion summarizer for session {session_id[:8]}")
                import asyncio
                if asyncio.iscoroutinefunction(run_summarizer):
                    # Handle async call
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    summary_result = loop.run_until_complete(run_summarizer(user_id, session_id))
                    loop.close()
                else:
                    summary_result = run_summarizer(user_id, session_id)
                logger.info(f"✅ Post-completion summarizer succeeded for session {session_id[:8]}")
            except Exception as e:
                # Log error but don't fail the completion
                logger.warning(f"⚠️ Post-completion summarizer failed for session {session_id[:8]}: {e}")
                if hasattr(telemetry_service, 'emit'):
                    telemetry_service.emit("summarizer_error", {
                        "user_id": user_id,
                        "session_id": session_id, 
                        "error": str(e)
                    })
            
            # Emit completion telemetry
            if hasattr(telemetry_service, 'emit'):
                telemetry_service.emit("session_mark_completed", {
                    "user_id": user_id,
                    "session_id": session_id
                })
            
            return True
        else:
            logger.warning(f"⚠️ Session completion failed - session not found")
            return False
            
    except Exception as e:
        db.rollback()
        logger.error(f"Error marking session completed {user_id}/{session_id}: {e}")
        return False
    finally:
        db.close()
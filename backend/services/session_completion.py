"""
Session Completion Handler
Handles session completion events and updates timestamps
"""

import logging
from datetime import datetime
from database import SessionLocal
from sqlalchemy import text

logger = logging.getLogger(__name__)

def mark_session_completed(user_id: str, session_id: str) -> bool:
    """
    Mark a session as completed and update timestamps
    
    Args:
        user_id: User identifier
        session_id: Session identifier
        
    Returns:
        True if update successful
    """
    db = SessionLocal()
    try:
        # Update session_pack_plan completed_at
        result = db.execute(text("""
            UPDATE session_pack_plan 
            SET completed_at = :completed_at
            WHERE user_id = :user_id AND session_id = :session_id 
            AND status = 'served'
            RETURNING user_id
        """), {
            'user_id': user_id,
            'session_id': session_id,
            'completed_at': datetime.utcnow()
        })
        
        pack_updated = result.fetchone()
        
        # Update sessions table completed_at  
        result = db.execute(text("""
            UPDATE sessions
            SET completed_at = :completed_at,
                status = 'completed'
            WHERE session_id = :session_id AND user_id = :user_id
            RETURNING session_id
        """), {
            'user_id': user_id,
            'session_id': session_id,
            'completed_at': datetime.utcnow()
        })
        
        session_updated = result.fetchone()
        
        if pack_updated or session_updated:
            db.commit()
            logger.info(f"✅ Session {session_id[:8]} marked as completed for user {user_id[:8]}")
            return True
        else:
            logger.warning(f"⚠️ Session completion failed - session not found or wrong state")
            return False
            
    except Exception as e:
        db.rollback()
        logger.error(f"Error marking session completed {user_id}/{session_id}: {e}")
        return False
    finally:
        db.close()

def mark_session_started(user_id: str, session_id: str) -> bool:
    """
    Mark a session as started and update served_at timestamp
    
    Args:
        user_id: User identifier 
        session_id: Session identifier
        
    Returns:
        True if update successful
    """
    db = SessionLocal()
    try:
        result = db.execute(text("""
            UPDATE sessions 
            SET served_at = :served_at,
                status = 'served'
            WHERE session_id = :session_id AND user_id = :user_id
            AND status IN ('planned', 'created')
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
            return True
        else:
            logger.warning(f"⚠️ Session start failed - session not found or wrong state")
            return False
            
    except Exception as e:
        db.rollback() 
        logger.error(f"Error marking session started {user_id}/{session_id}: {e}")
        return False
    finally:
        db.close()
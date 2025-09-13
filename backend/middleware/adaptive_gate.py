"""
Adaptive Feature Gate Middleware
Protects /adapt/* endpoints with global and user-level flags
"""

import os
from fastapi import Request, HTTPException, Depends
from .auth import get_current_user
from database import SessionLocal, User
from sqlalchemy import select

# Global adaptive feature flag
ADAPTIVE_GLOBAL = os.getenv("ADAPTIVE_GLOBAL", "false").lower() == "true"

async def ensure_adaptive_enabled(request: Request, user_id: str = Depends(get_current_user)):
    """
    Middleware to ensure adaptive endpoints are enabled both globally and for user
    """
    # Only check /adapt/* endpoints
    if not request.url.path.startswith("/api/adapt/"):
        return user_id
    
    # Check global flag first
    if not ADAPTIVE_GLOBAL:
        raise HTTPException(
            status_code=403, 
            detail={"code": "ADAPTIVE_DISABLED_GLOBAL", "message": "Adaptive system globally disabled"}
        )
    
    # Check user-level flag
    db = SessionLocal()
    try:
        result = db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user or not user.adaptive_enabled:
            raise HTTPException(
                status_code=403,
                detail={"code": "ADAPTIVE_DISABLED_USER", "message": "Adaptive system not enabled for user"}
            )
        
        return user_id
        
    finally:
        db.close()
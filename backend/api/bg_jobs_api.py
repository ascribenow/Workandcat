"""
Simplified Background Jobs API
Minimal health endpoint only (to prevent 503 errors from removed endpoints)
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from services.bg_job_queue import job_queue

router = APIRouter(prefix="/api/bg-jobs", tags=["background_jobs"])

@router.get("/health")  
async def get_basic_health():
    """Minimal health endpoint - prevents 503 errors"""
    try:
        depth = await job_queue.get_queue_depth()
        return JSONResponse({
            "status": "healthy",
            "queue_depth": depth
        })
    except Exception as e:
        return JSONResponse({
            "status": "degraded", 
            "error": str(e)[:100]
        }, status_code=503)
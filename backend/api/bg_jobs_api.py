"""
Simplified Background Jobs API
Internal logging only - no public endpoints (as per simplified design)
"""

# This file is kept minimal - all monitoring moved to internal logging
# No public health/status endpoints needed for lean implementation
# Workers log directly to files for debugging

# If basic monitoring is needed, uncomment the minimal endpoint below:

# from fastapi import APIRouter
# from services.bg_job_queue import job_queue

# router = APIRouter(prefix="/api/bg-jobs", tags=["background_jobs"])

# @router.get("/internal-depth")  
# async def get_internal_queue_depth():
#     """Internal-only queue depth for basic monitoring"""
#     try:
#         depth = await job_queue.get_queue_depth()
#         return {"queue_depth": depth}
#     except Exception as e:
#         return {"error": str(e)}

# For now, rely on worker logs for all monitoring
#!/usr/bin/env python3
"""
Background Jobs Service - DISABLED
REASON: This file depends on deleted database tables (sessions, attempts, mastery, plans, topics)
STATUS: All functionality disabled until new session/adaptivity structure is implemented
"""

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BackgroundJobsManager:
    """
    Background Jobs Manager - DISABLED
    All functionality disabled due to deleted table dependencies
    """
    
    def __init__(self):
        logger.warning("⚠️ BackgroundJobsManager disabled - depends on deleted database tables")
        self.scheduler = None
        
    async def start_all_jobs(self):
        """All jobs disabled"""
        logger.info("🚫 Background jobs disabled - depends on deleted tables")
        return {"status": "disabled", "reason": "depends_on_deleted_tables"}
        
    async def stop_all_jobs(self):
        """All jobs disabled"""
        logger.info("🚫 Background jobs already disabled")
        return {"status": "disabled"}

# Global instance
background_jobs_manager = BackgroundJobsManager()
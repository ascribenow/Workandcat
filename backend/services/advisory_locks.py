"""
Advisory Lock Manager for Twelvr Blueprint
Addresses Deviation #3: Advisory lock integration in core planning flow
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional
import asyncpg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AdvisoryLockManager:
    """
    Manages PostgreSQL advisory locks for session planning
    Ensures only one planned session per user at a time (Deviation #3)
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.held_locks = set()  # Track locks held by this instance
    
    @asynccontextmanager
    async def acquire_planning_lock(self, user_id: str, timeout_seconds: int = 30):
        """
        CRITICAL: Acquire session planning lock for user (Deviation #3)
        
        Usage:
            async with lock_manager.acquire_planning_lock(user_id):
                # Only one instance can execute this block per user
                session = await plan_session(user_id)
        """
        lock_key = f"session_planning_{user_id}"
        acquired = False
        
        try:
            # Attempt to acquire the lock
            acquired = await self._acquire_lock(lock_key, timeout_seconds)
            
            if not acquired:
                raise LockAcquisitionError(
                    f"Could not acquire planning lock for user {user_id} within {timeout_seconds} seconds"
                )
            
            logger.info(f"Acquired planning lock for user {user_id}")
            yield
            
        except Exception as e:
            logger.error(f"Error in planning lock context for user {user_id}: {e}")
            raise
            
        finally:
            if acquired:
                await self._release_lock(lock_key)
                logger.info(f"Released planning lock for user {user_id}")
    
    async def _acquire_lock(self, lock_key: str, timeout_seconds: int) -> bool:
        """
        Acquire advisory lock using PostgreSQL function
        """
        try:
            result = await self.db.execute(
                text("SELECT acquire_advisory_lock(:lock_key, :timeout)"),
                {"lock_key": lock_key, "timeout": timeout_seconds}
            )
            
            acquired = result.scalar()
            
            if acquired:
                self.held_locks.add(lock_key)
                logger.debug(f"Successfully acquired lock: {lock_key}")
            else:
                logger.warning(f"Failed to acquire lock: {lock_key}")
            
            return acquired
            
        except Exception as e:
            logger.error(f"Error acquiring lock {lock_key}: {e}")
            return False
    
    async def _release_lock(self, lock_key: str) -> bool:
        """
        Release advisory lock using PostgreSQL function
        """
        try:
            result = await self.db.execute(
                text("SELECT release_advisory_lock(:lock_key)"),
                {"lock_key": lock_key}
            )
            
            released = result.scalar()
            
            if released and lock_key in self.held_locks:
                self.held_locks.remove(lock_key)
                logger.debug(f"Successfully released lock: {lock_key}")
            
            return released
            
        except Exception as e:
            logger.error(f"Error releasing lock {lock_key}: {e}")
            return False
    
    async def is_lock_held(self, lock_key: str) -> bool:
        """
        Check if a specific lock is currently held
        """
        try:
            result = await self.db.execute(
                text("SELECT is_advisory_lock_held(:lock_key)"),
                {"lock_key": lock_key}
            )
            
            return result.scalar() or False
            
        except Exception as e:
            logger.error(f"Error checking lock status {lock_key}: {e}")
            return False
    
    async def has_planned_session(self, user_id: str) -> bool:
        """
        Check if user already has a planned session (lock-safe)
        """
        try:
            result = await self.db.execute(
                text("SELECT has_planned_session(:user_id)"),
                {"user_id": user_id}
            )
            
            return result.scalar() or False
            
        except Exception as e:
            logger.error(f"Error checking planned session for user {user_id}: {e}")
            return False
    
    async def cleanup_expired_locks(self) -> int:
        """
        Clean up expired advisory locks
        Returns number of locks cleaned up
        """
        try:
            result = await self.db.execute(
                text("SELECT cleanup_expired_advisory_locks()")
            )
            
            cleaned_count = result.scalar() or 0
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired advisory locks")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired locks: {e}")
            return 0
    
    async def get_lock_status(self) -> list:
        """
        Get current advisory lock status for monitoring
        """
        try:
            result = await self.db.execute(
                text("SELECT * FROM get_advisory_lock_status()")
            )
            
            locks = []
            for row in result.fetchall():
                locks.append({
                    "lock_key": row.lock_key,
                    "user_id": str(row.user_id) if row.user_id else None,
                    "acquired_at": row.acquired_at,
                    "expires_at": row.expires_at,
                    "is_active": row.is_active,
                    "duration_minutes": row.duration_minutes
                })
            
            return locks
            
        except Exception as e:
            logger.error(f"Error getting lock status: {e}")
            return []
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Async context manager exit - cleanup any held locks
        """
        # Release any locks that are still held
        for lock_key in list(self.held_locks):
            await self._release_lock(lock_key)
        
        if exc_type:
            logger.error(f"AdvisoryLockManager exiting due to exception: {exc_val}")


class LockAcquisitionError(Exception):
    """
    Raised when advisory lock cannot be acquired within timeout
    """
    pass


class SessionPlanningLockManager:
    """
    Specialized lock manager for session planning operations
    High-level interface for blueprint session planning
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.lock_manager = AdvisoryLockManager(db_session)
    
    @asynccontextmanager
    async def ensure_single_planned_session(self, user_id: str):
        """
        DEVIATION #3: Ensure only one planned session per user
        
        This is the main entry point for session planning operations.
        Usage in BlueprintSessionPlanner:
        
        async with lock_manager.ensure_single_planned_session(user_id):
            existing = await get_planned_session(user_id)
            if existing:
                return existing
            # ... create new session
        """
        
        async with self.lock_manager.acquire_planning_lock(user_id):
            # Double-check for existing planned session within the lock
            has_planned = await self.lock_manager.has_planned_session(user_id)
            
            if has_planned:
                logger.info(f"User {user_id} already has a planned session")
            
            yield has_planned
    
    async def force_cleanup_user_locks(self, user_id: str) -> bool:
        """
        Force cleanup of locks for a specific user (emergency use)
        """
        lock_key = f"session_planning_{user_id}"
        
        try:
            return await self.lock_manager._release_lock(lock_key)
        except Exception as e:
            logger.error(f"Error force-cleaning lock for user {user_id}: {e}")
            return False


# Utility functions for lock management

async def create_lock_manager(db_session: AsyncSession) -> AdvisoryLockManager:
    """
    Factory function to create advisory lock manager
    """
    return AdvisoryLockManager(db_session)


async def periodic_lock_cleanup(db_session: AsyncSession):
    """
    Periodic cleanup function to be called by background tasks
    Can be scheduled to run every few minutes
    """
    lock_manager = AdvisoryLockManager(db_session)
    
    try:
        cleaned_count = await lock_manager.cleanup_expired_locks()
        logger.info(f"Periodic cleanup: removed {cleaned_count} expired locks")
        
        # Log current lock status
        locks = await lock_manager.get_lock_status()
        active_locks = [lock for lock in locks if lock['is_active']]
        
        if active_locks:
            logger.info(f"Current active locks: {len(active_locks)}")
            for lock in active_locks[:5]:  # Log first 5 for monitoring
                logger.debug(f"Active lock: {lock['lock_key']} (user: {lock['user_id']})")
    
    except Exception as e:
        logger.error(f"Error in periodic lock cleanup: {e}")


# Configuration constants
DEFAULT_PLANNING_TIMEOUT = 30  # seconds
MAX_PLANNING_TIMEOUT = 120     # seconds
LOCK_CLEANUP_INTERVAL = 300    # 5 minutes
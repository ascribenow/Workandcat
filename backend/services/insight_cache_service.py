import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from database import SessionLocal, UserDashboardInsights, UserPreSessionInsights, UserInsightDebug
from services.adaptive_insights_service import adaptive_insights_service
from services.insight_generator_service import insight_generator_service

# In-memory cache for ultra-fast responses (Redis alternative for small datasets)
_memory_cache = {}
_cache_timestamps = {}

def cleanup_memory_cache():
    """Clean up expired memory cache entries to prevent memory leaks"""
    from time import time
    current_time = time()
    expired_keys = []
    
    for key, timestamp in _cache_timestamps.items():
        # Remove entries older than 1 hour
        if current_time - timestamp > 3600:
            expired_keys.append(key)
    
    for key in expired_keys:
        _memory_cache.pop(key, None)
        _cache_timestamps.pop(key, None)
    
    if expired_keys:
        logger.info(f"Cleaned up {len(expired_keys)} expired memory cache entries")

logger = logging.getLogger(__name__)

class InsightCacheService:
    """Service for managing adaptive insights cache with TTL and refresh logic"""
    
    def __init__(self):
        self.cache_ttl_hours = 24
        self.logger = logging.getLogger(__name__)
        # Clean up memory cache on initialization
        cleanup_memory_cache()
    
    def get_dashboard_insights(self, user_id: str) -> Dict[str, Any]:
        """Get dashboard insights - BACKGROUND JOB ARCHITECTURE (fetch pre-computed JSON)"""
        from time import time
        start_time = time()
        
        # Level 1: In-memory cache (TARGET: <50ms)
        memory_key = f"dashboard:{user_id}"
        if memory_key in _memory_cache:
            memory_timestamp = _cache_timestamps.get(memory_key)
            if memory_timestamp and (time() - memory_timestamp) < 300:  # 5 minutes in-memory TTL
                memory_time = (time() - start_time) * 1000
                self.logger.debug(f"Memory cache hit for user {user_id[:8]} in {memory_time:.1f}ms")
                result = _memory_cache[memory_key].copy()
                result["source"] = "memory"
                result["cache_time_ms"] = memory_time
                return result
        
        # Level 2: Database cache - FETCH PRE-COMPUTED INSIGHTS ONLY
        db = SessionLocal()
        try:
            # Just fetch pre-computed insights (NO real-time computation)
            cache_entry = db.query(
                UserDashboardInsights.all_time_insights,
                UserDashboardInsights.recent_insights, 
                UserDashboardInsights.last_updated_at
            ).filter(
                UserDashboardInsights.user_id == user_id
            ).first()
            
            if cache_entry:
                cache_time = (time() - start_time) * 1000
                
                result = {
                    "all_time_markdown": cache_entry.all_time_insights.get("markdown", ""),
                    "recent_markdown": cache_entry.recent_insights.get("markdown", ""),
                    "last_updated_at": cache_entry.last_updated_at.isoformat(),
                    "source": "pre_computed",
                    "cache_time_ms": cache_time
                }
                
                # Store in memory cache for next time
                _memory_cache[memory_key] = result.copy()
                _cache_timestamps[memory_key] = time()
                
                self.logger.debug(f"Pre-computed insights fetched for user {user_id[:8]} in {cache_time:.1f}ms")
                return result
            
            # No pre-computed insights available - return placeholder
            # (Background job will eventually compute and store insights)
            placeholder = self._empty_dashboard_response()
            placeholder["source"] = "awaiting_background_job"
            placeholder["message"] = "Your adaptive insights are being generated. Please check back in a few minutes."
            
            self.logger.info(f"No pre-computed insights for user {user_id[:8]} - background job needed")
            return placeholder
            
        except Exception as e:
            self.logger.error(f"Error fetching dashboard insights for user {user_id[:8]}: {e}")
            fallback = self._empty_dashboard_response()
            fallback["source"] = "error"
            return fallback
        finally:
            db.close()
    
    def get_pre_session_insight(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Get pre-session insight with ULTRA-FAST memory + DB cache strategy"""
        from time import time
        start_time = time()
        
        # Level 1: In-memory cache (TARGET: <50ms)
        memory_key = f"pre_session:{user_id}"
        if memory_key in _memory_cache:
            memory_timestamp = _cache_timestamps.get(memory_key)
            if memory_timestamp and (time() - memory_timestamp) < 600:  # 10 minutes in-memory TTL
                memory_time = (time() - start_time) * 1000
                self.logger.debug(f"Pre-session memory cache hit for user {user_id[:8]} in {memory_time:.1f}ms")
                result = _memory_cache[memory_key].copy()
                result["source"] = "memory"
                result["cache_time_ms"] = memory_time
                return result
        
        # Level 2: Database cache 
        db = SessionLocal()
        try:
            cache_entry = db.query(UserPreSessionInsights).filter(
                UserPreSessionInsights.user_id == user_id
            ).first()
            
            # For pre-session, refresh daily or if no cache exists
            if cache_entry and self._is_cache_fresh(cache_entry.last_updated_at, hours=24):
                cache_time = (time() - start_time) * 1000
                
                insight_card = cache_entry.insight_card.copy()
                insight_card["last_updated_at"] = cache_entry.last_updated_at.isoformat()
                insight_card["source"] = "db_cache"
                insight_card["cache_time_ms"] = cache_time
                
                # Store in memory cache
                _memory_cache[memory_key] = insight_card.copy()
                _cache_timestamps[memory_key] = time()
                
                self.logger.debug(f"Pre-session DB cache hit for user {user_id[:8]} in {cache_time:.1f}ms")
                return insight_card
            
            # Level 3: Fresh generation
            fresh_time = time()
            result = self.refresh_pre_session_cache(user_id, session_id)
            result["generation_time_ms"] = (time() - fresh_time) * 1000
            
            # Store in memory cache
            _memory_cache[memory_key] = result.copy()
            _cache_timestamps[memory_key] = time()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting pre-session insight for user {user_id[:8]}: {e}")
            return self._empty_pre_session_response()
        finally:
            db.close()
    
    def refresh_dashboard_cache(self, user_id: str) -> Dict[str, Any]:
        """Refresh dashboard insights cache"""
        db = SessionLocal()
        try:
            self.logger.info(f"Refreshing dashboard cache for user {user_id[:8]}")
            
            # Track timing for observability
            start_time = datetime.now(timezone.utc)
            
            # Extract data slices
            all_time_slice = adaptive_insights_service.build_all_time_slice(user_id)
            all_time_slice["user_id"] = user_id  # Add for LLM cost control
            
            recent_slice = adaptive_insights_service.build_recent_slice(user_id, window=20)
            recent_slice["user_id"] = user_id  # Add for LLM cost control
            
            # Generate insights with LLM + fallbacks
            all_time_markdown = insight_generator_service.gen_all_time_markdown(all_time_slice)
            recent_markdown = insight_generator_service.gen_recent_markdown(recent_slice)
            
            # Log timing
            extraction_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self.logger.info(f"Dashboard insight extraction took {extraction_time:.3f}s for user {user_id[:8]}")
            
            # Prepare cache data
            all_time_insights = {
                "markdown": all_time_markdown,
                "data_slice": all_time_slice,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
            recent_insights = {
                "markdown": recent_markdown,  
                "data_slice": recent_slice,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Update cache with upsert
            now = datetime.now(timezone.utc)
            
            existing = db.query(UserDashboardInsights).filter(
                UserDashboardInsights.user_id == user_id
            ).first()
            
            if existing:
                existing.all_time_insights = all_time_insights
                existing.recent_insights = recent_insights
                existing.last_updated_at = now
            else:
                cache_entry = UserDashboardInsights(
                    user_id=user_id,
                    all_time_insights=all_time_insights,
                    recent_insights=recent_insights,
                    last_updated_at=now
                )
                db.add(cache_entry)
            
            # Store debug data
            self._store_debug_slices(db, user_id, all_time_slice, recent_slice, None)
            
            db.commit()
            
            return {
                "all_time_markdown": all_time_markdown,
                "recent_markdown": recent_markdown,
                "last_updated_at": now.isoformat()
            }
            
        except Exception as e:
            db.rollback()
            self.logger.error(f"Error refreshing dashboard cache for user {user_id[:8]}: {e}")
            return self._empty_dashboard_response()
        finally:
            db.close()
    
    def refresh_pre_session_cache(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Refresh pre-session insights cache"""
        db = SessionLocal()
        try:
            self.logger.info(f"Refreshing pre-session cache for user {user_id[:8]}")
            
            # Check if session pack exists - graceful degradation
            pack_exists = self._check_session_pack_exists(db, session_id)
            if not pack_exists:
                # Return graceful card when no pack exists
                return self._graceful_no_pack_response()
            
            # Track timing
            start_time = datetime.now(timezone.utc)
            
            # Extract pre-session data slice
            pre_session_slice = adaptive_insights_service.build_pre_session_slice(user_id, session_id, window=5)
            pre_session_slice["user_id"] = user_id  # Add for LLM cost control
            
            # Generate insight card with LLM + fallback
            insight_card = insight_generator_service.gen_pre_session_card(pre_session_slice)
            
            # Log timing
            extraction_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self.logger.info(f"Pre-session insight extraction took {extraction_time:.3f}s for user {user_id[:8]}")
            
            # Update cache with upsert
            now = datetime.now(timezone.utc)
            
            existing = db.query(UserPreSessionInsights).filter(
                UserPreSessionInsights.user_id == user_id
            ).first()
            
            if existing:
                existing.insight_card = insight_card
                existing.last_updated_at = now
            else:
                cache_entry = UserPreSessionInsights(
                    user_id=user_id,
                    insight_card=insight_card,
                    last_updated_at=now
                )
                db.add(cache_entry)
            
            # Store debug data
            self._store_debug_slices(db, user_id, None, None, pre_session_slice)
            
            db.commit()
            
            # Add timestamp to response
            insight_card["last_updated_at"] = now.isoformat()
            return insight_card
            
        except Exception as e:
            db.rollback()
            self.logger.error(f"Error refreshing pre-session cache for user {user_id[:8]}: {e}")
            return self._empty_pre_session_response()
        finally:
            db.close()
    
    def invalidate_pre_session_cache_for_new_pack(self, user_id: str, session_id: str):
        """Invalidate pre-session cache when new pack is created"""
        db = SessionLocal()
        try:
            self.logger.info(f"Invalidating pre-session cache for new pack: user {user_id[:8]}, session {session_id[:8]}")
            
            # Remove existing cache to force refresh on next request
            db.query(UserPreSessionInsights).filter(
                UserPreSessionInsights.user_id == user_id
            ).delete()
            
            db.commit()
            
        except Exception as e:
            db.rollback()
            self.logger.error(f"Error invalidating pre-session cache: {e}")
        finally:
            db.close()
    
    def _check_session_pack_exists(self, db: Session, session_id: str) -> bool:
        """Check if session pack exists for graceful degradation"""
        from sqlalchemy import text
        
        try:
            query = text("""
                SELECT 1 FROM session_pack_questions 
                WHERE session_id = :session_id 
                LIMIT 1
            """)
            
            result = db.execute(query, {"session_id": session_id}).fetchone()
            return result is not None
            
        except Exception as e:
            self.logger.error(f"Error checking session pack existence: {e}")
            return False
    
    def _graceful_no_pack_response(self) -> Dict[str, Any]:
        """Return graceful response when no session pack exists"""
        return {
            "title": "Prep in Progress 🔧",
            "progress": "We're preparing your personalized session.",
            "way_forward": ["Your adaptive session is being generated", "Check back in a moment"],
            "today": "Customized questions are being selected for your level.",
            "last_updated_at": datetime.now(timezone.utc).isoformat(),
            "source": "graceful_degradation"
        }
    
    def _is_cache_fresh(self, last_updated: datetime, hours: int = None) -> bool:
        """Check if cache is still fresh based on TTL - OPTIMIZED with edge case handling"""
        if not last_updated:
            return False
            
        try:
            ttl_hours = hours or self.cache_ttl_hours
            
            # Handle timezone-aware datetime properly
            if last_updated.tzinfo is None:
                last_updated = last_updated.replace(tzinfo=timezone.utc)
            
            cache_age = datetime.now(timezone.utc) - last_updated
            is_fresh = cache_age.total_seconds() < (ttl_hours * 3600)
            
            # Log cache age for debugging
            age_minutes = cache_age.total_seconds() / 60
            self.logger.debug(f"Cache age: {age_minutes:.1f}min, TTL: {ttl_hours}h, Fresh: {is_fresh}")
            
            return is_fresh
            
        except Exception as e:
            self.logger.warning(f"Cache freshness check failed: {e}")
            return False  # Treat as stale if calculation fails
    
    def _store_debug_slices(self, db: Session, user_id: str, all_time_slice: Dict = None, 
                           recent_slice: Dict = None, pre_session_slice: Dict = None):
        """Store raw data slices for debugging (optional, disabled in production)"""
        try:
            # Add debug toggle - can be disabled in production
            debug_enabled = True  # Set to False in production
            if not debug_enabled:
                return
                
            existing = db.query(UserInsightDebug).filter(
                UserInsightDebug.user_id == user_id
            ).first()
            
            now = datetime.now(timezone.utc)
            
            if existing:
                if all_time_slice is not None:
                    existing.all_time_slice = all_time_slice
                if recent_slice is not None:
                    existing.recent_slice = recent_slice
                if pre_session_slice is not None:
                    existing.pre_session_slice = pre_session_slice
                existing.updated_at = now
            else:
                debug_entry = UserInsightDebug(
                    user_id=user_id,
                    all_time_slice=all_time_slice,
                    recent_slice=recent_slice,
                    pre_session_slice=pre_session_slice,
                    updated_at=now
                )
                db.add(debug_entry)
                
        except Exception as e:
            self.logger.error(f"Error storing debug slices for user {user_id[:8]}: {e}")
    
    def _empty_dashboard_response(self) -> Dict[str, Any]:
        """Return empty dashboard response on error"""
        return {
            "all_time_markdown": "Welcome to your adaptive journey! Complete a few sessions to see insights.",
            "recent_markdown": "Your recent progress will appear here after completing sessions.",
            "last_updated_at": datetime.now(timezone.utc).isoformat()
        }
    
    def _empty_pre_session_response(self) -> Dict[str, Any]:
        """Return empty pre-session response on error"""
        return {
            "title": "Ready to Start 🚀",
            "progress": "Let's begin your learning session.",
            "way_forward": ["Focus on accuracy and understanding"],
            "today": "12 questions designed for your level.",
            "last_updated_at": datetime.now(timezone.utc).isoformat()
        }
    
    def get_cache_metrics(self) -> Dict[str, Any]:
        """Get cache metrics for observability"""
        db = SessionLocal()
        try:
            from sqlalchemy import text
            
            # Get cache statistics
            dashboard_count_query = text("SELECT COUNT(*) FROM user_dashboard_insights")
            pre_session_count_query = text("SELECT COUNT(*) FROM user_pre_session_insights")
            
            dashboard_count = db.execute(dashboard_count_query).scalar()
            pre_session_count = db.execute(pre_session_count_query).scalar()
            
            # Get cache age statistics
            now = datetime.now(timezone.utc)
            age_query = text("""
                SELECT 
                    AVG(EXTRACT(EPOCH FROM (:now - last_updated_at))) as avg_age_seconds,
                    MAX(EXTRACT(EPOCH FROM (:now - last_updated_at))) as max_age_seconds
                FROM user_dashboard_insights
            """)
            
            age_result = db.execute(age_query, {"now": now}).fetchone()
            
            return {
                "dashboard_cache_entries": dashboard_count,
                "pre_session_cache_entries": pre_session_count,
                "avg_cache_age_seconds": float(age_result.avg_age_seconds or 0),
                "max_cache_age_seconds": float(age_result.max_age_seconds or 0),
                "timestamp": now.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting cache metrics: {e}")
            return {"error": str(e)}
        finally:
            db.close()

# Global service instance  
insight_cache_service = InsightCacheService()